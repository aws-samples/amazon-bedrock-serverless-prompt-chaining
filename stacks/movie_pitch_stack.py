from aws_cdk import (
    Duration,
    Stack,
    aws_bedrock as bedrock,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from collections import OrderedDict

from .util import (
    add_bedrock_retries,
    get_claude_instant_invoke_chain,
    CLAUDE_HUMAN_PROMPT,
    CLAUDE_AI_PROMPT,
)


class MoviePitchStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Step #1: Let the model generate various movie pitch options
        movie_pitch_generators = sfn.Parallel(self, "MoviePitches")

        temperature_settings = OrderedDict([("Red", 0), ("Blue", 0.5), ("Green", 1)])
        for temperature_name, temperature_value in temperature_settings.items():
            generate_pitch_format_prompt = sfn.Pass(
                self,
                f"Generate {temperature_name} Movie Pitch (Format Model Inputs)",
                parameters={
                    "prompt": sfn.JsonPath.format(
                        f"""{CLAUDE_HUMAN_PROMPT}You are an Oscar-winning screenwriter and you are pitching an idea for a new movie about {{}} to a major movie producer.
Give me your movie pitch in one paragraph.
Start with a tagline sentence that describes the movie as a whole, then follow with a synopsis of the story and the major characters.{CLAUDE_AI_PROMPT}""",
                        sfn.JsonPath.string_at("$$.Execution.Input.movie_description"),
                    ),
                    "max_tokens_to_sample": 1024,
                    "temperature": temperature_value,
                },
                result_path="$.model_inputs",
            )

            generate_next_pitch_format_prompt = sfn.Pass(
                self,
                f"Generate {temperature_name} Movie Pitch (Format Model Inputs For New Pitch)",
                parameters={
                    "prompt": sfn.JsonPath.format(
                        f"""{CLAUDE_HUMAN_PROMPT}You are an Oscar-winning screenwriter and you are pitching an idea for a new movie about {{}} to a major movie producer.
You previously pitched this idea for the movie, inside <previous_pitch></previous_pitch> XML tags. The movie producer rejected this idea and asked for a new idea.
<previous_pitch>
{{}}
</previous_pitch>
Give me your new movie pitch in one paragraph.
Start with a tagline sentence that describes the movie as a whole, then follow with a synopsis of the story and the major characters.{CLAUDE_AI_PROMPT}""",
                        sfn.JsonPath.string_at("$$.Execution.Input.movie_description"),
                        sfn.JsonPath.string_at(
                            f"$.pitches.pitch_{temperature_name.lower()}"
                        ),
                    ),
                    "max_tokens_to_sample": 1024,
                    "temperature": temperature_value,
                },
                result_path="$.model_inputs",
            )

            generate_pitch_invoke_model = tasks.BedrockInvokeModel(
                self,
                f"Generate {temperature_name} Movie Pitch (Invoke Model)",
                model=bedrock.FoundationModel.from_foundation_model_id(
                    self,
                    "Model",
                    bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_INSTANT_V1,
                ),
                body=sfn.TaskInput.from_json_path_at("$.model_inputs"),
                result_selector={
                    f"pitch_{temperature_name.lower()}": sfn.JsonPath.string_at(
                        "$.Body.completion"
                    )
                },
            )
            add_bedrock_retries(generate_pitch_invoke_model)

            choose_pitch_prompt = (
                sfn.Choice(self, f"Previous {temperature_name} pitch rejected?")
                .when(
                    sfn.Condition.is_present("$.pitches"),
                    generate_next_pitch_format_prompt.next(generate_pitch_invoke_model),
                )
                .otherwise(
                    generate_pitch_format_prompt.next(generate_pitch_invoke_model),
                )
            )

            movie_pitch_generators = movie_pitch_generators.branch(choose_pitch_prompt)

        merge_pitches = sfn.Pass(
            self,
            f"Merge Movie Pitches",
            parameters={
                f"pitches": sfn.JsonPath.json_merge(
                    sfn.JsonPath.json_merge(
                        sfn.JsonPath.object_at("$[0]"),
                        sfn.JsonPath.object_at("$[1]"),
                    ),
                    sfn.JsonPath.object_at("$[2]"),
                )
            },
        )

        # Step #2: Let the model choose the best movie pitch out of the generated set
        pitch_chooser_prompt = f"""{CLAUDE_HUMAN_PROMPT}You are a producer of Oscar-winning movies, and you are deciding on the next movie you will make.
Screenwriters previously pitched you on {len(temperature_settings)} movie ideas, and you need to pick one of the ideas."""
        pitch_chooser_prompt_arguments = []

        for i, temperature_name in enumerate(temperature_settings.keys()):
            pitch_key = temperature_name.lower()
            pitch_chooser_prompt += f"""

{i+1}. Movie pitch #{i+1} ({temperature_name}) is below, inside <{pitch_key}></{pitch_key}> XML tags.
<{pitch_key}>
{{}}
</{pitch_key}>"""
            pitch_chooser_prompt_arguments.append(
                sfn.JsonPath.string_at(f"$.pitches.pitch_{pitch_key}")
            )

        pitch_chooser_prompt += (
            "\n\nNow choose one of the movie pitches. The possible selections are:"
        )
        for i, temperature_name in enumerate(temperature_settings.keys()):
            pitch_chooser_prompt += f"\n({i+1}) Movie pitch {temperature_name}"

        pitch_chooser_prompt += f"{CLAUDE_AI_PROMPT} My choice is ("

        pitch_chooser_format_prompt = sfn.Pass(
            self,
            "Choose Best Movie Pitch (Format Model Inputs)",
            parameters={
                "pitches": sfn.JsonPath.object_at("$.pitches"),
                "model_inputs": {
                    "prompt": sfn.JsonPath.format(
                        pitch_chooser_prompt,
                        *pitch_chooser_prompt_arguments,
                    ),
                    "max_tokens_to_sample": 300,
                    "temperature": 0.3,
                },
            },
        )

        pitch_chooser_job = tasks.BedrockInvokeModel(
            self,
            "Choose Best Movie Pitch (Invoke Model)",
            model=bedrock.FoundationModel.from_foundation_model_id(
                self,
                "Model",
                bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_INSTANT_V1,
            ),
            body=sfn.TaskInput.from_json_path_at("$.model_inputs"),
            result_selector={"response": sfn.JsonPath.string_at("$.Body.completion")},
            result_path="$.model_outputs",
        )
        add_bedrock_retries(pitch_chooser_job)

        # Step #3: Let the human user decide whether to greenlight the movie pitch.
        # Create a task token so that the user can decide whether to accept the movie pitch or not.
        user_choice_lambda = lambda_python.PythonFunction(
            self,
            "UserProducerChoiceAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/movie_pitch/seek_user_input",
            timeout=Duration.seconds(5),
            memory_size=128,
        )
        user_choice_job = tasks.LambdaInvoke(
            self,
            "Pitch to the Movie Producer",
            lambda_function=user_choice_lambda,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object(
                {
                    "token": sfn.JsonPath.task_token,
                    "input": {
                        "movie_pitch": sfn.JsonPath.string_at("$.winning_movie_pitch"),
                    },
                }
            ),
            result_selector={
                "user_choice": sfn.JsonPath.string_at("$.Payload.user_choice")
            },
            result_path="$.user_choice_result",
        )

        start_user_choice_fork = sfn.Choice(self, "Select Model's Pitch Choice")
        for i, temperature_name in enumerate(temperature_settings.keys()):
            pitch_selector = sfn.Pass(
                self,
                f"Select {temperature_name} Pitch",
                parameters={
                    "pitches": sfn.JsonPath.object_at("$.pitches"),
                    "winning_movie_pitch": sfn.JsonPath.string_at(
                        f"$.pitches.pitch_{temperature_name.lower()}"
                    ),
                },
            )

            start_user_choice_fork = start_user_choice_fork.when(
                sfn.Condition.string_matches("$.model_outputs.response", f"{i+1}*"),
                pitch_selector.next(user_choice_job),
            )
        start_user_choice_fork = start_user_choice_fork.otherwise(
            sfn.Fail(
                self,
                "Handling Model's Pitch Choice Failed",
                cause="Unknown model pitch choice",
                error="Unknown model pitch choice",
            )
        )

        # Step #4: Develop the movie idea into a one-pager
        pitch_one_pager_job = get_claude_instant_invoke_chain(
            self,
            "Generate Movie Pitch One-Pager",
            prompt=sfn.JsonPath.format(
                """You are an Oscar-winning screenwriter and you are pitching an idea for a new movie about {} to a major movie producer.
You previously pitched this short description for the movie, inside <pitch></pitch> XML tags.
<pitch>
{}
</pitch>
Now create a one-page movie pitch, based on your previous short description for the movie.""",
                sfn.JsonPath.string_at("$$.Execution.Input.movie_description"),
                sfn.JsonPath.string_at("$.winning_movie_pitch"),
            ),
            max_tokens_to_sample=2048,
            include_previous_conversation_in_prompt=False,
        )

        select_movie_pitch = sfn.Pass(
            scope,
            "Select Movie Pitch",
            parameters={
                "movie_pitch_one_pager": sfn.JsonPath.string_at("$.output.response"),
            },
        )

        # Hook the agents together into a workflow
        handle_user_choice_fork = (
            sfn.Choice(self, "Greenlight?")
            .when(
                sfn.Condition.string_equals("$.user_choice_result.user_choice", "yes"),
                pitch_one_pager_job.next(select_movie_pitch),
            )
            .when(
                sfn.Condition.string_equals("$.user_choice_result.user_choice", "no"),
                movie_pitch_generators,
            )
            .otherwise(
                sfn.Fail(
                    self,
                    "Handling User Choice Failed",
                    cause="Unknown user choice",
                    error="Unknown user choice",
                )
            )
        )
        user_choice_job.next(handle_user_choice_fork)

        chain = (
            movie_pitch_generators.next(merge_pitches)
            .next(pitch_chooser_format_prompt)
            .next(pitch_chooser_job)
            .next(start_user_choice_fork)
        )

        sfn.StateMachine(
            self,
            "MoviePitchWorkflow",
            state_machine_name="PromptChainDemo-MoviePitch",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            # 1 hour to account for getting user feedback in the UI
            timeout=Duration.seconds(3600),
        )
