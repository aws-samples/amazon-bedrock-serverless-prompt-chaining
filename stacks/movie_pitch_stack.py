from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from collections import OrderedDict

from .util import (
    add_bedrock_retries,
    get_bedrock_iam_policy_statement,
    get_lambda_bundling_options,
)


class MoviePitchStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: generate movie pitch options
        movie_pitch_generators = sfn.Parallel(self, "MoviePitches")

        pitch_lambda = lambda_python.PythonFunction(
            self,
            f"PitchAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/movie_pitch/pitch_generator_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        pitch_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        temperature_settings = OrderedDict([("Low", 0), ("Medium", 0.5), ("High", 1)])
        for temperature_name, temperature_value in temperature_settings.items():
            pitch_job = tasks.LambdaInvoke(
                self,
                f"Generate Movie Pitch ({temperature_name})",
                lambda_function=pitch_lambda,
                payload=sfn.TaskInput.from_object(
                    {
                        "temperature": temperature_value,
                        "movie_description": sfn.JsonPath.string_at(
                            "$.movie_description"
                        ),
                    }
                ),
                output_path="$.Payload",
            )
            add_bedrock_retries(pitch_job)
            movie_pitch_generators = movie_pitch_generators.branch(pitch_job)

        # Agent #2: choose best one
        pitch_chooser_lambda = lambda_python.PythonFunction(
            self,
            "PitchChooserAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/movie_pitch/pitch_chooser_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        pitch_chooser_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        pitch_chooser_job = tasks.LambdaInvoke(
            self,
            "Choose Best Movie Pitch",
            lambda_function=pitch_chooser_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(pitch_chooser_job)

        # Next step: create a task token so that the user can decide whether to accept
        # the movie pitch or not.
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
                    "input.$": "$",
                }
            ),
            output_path="$.Payload",
        )

        # Agent #3: develop the movie idea into a one-pager
        pitch_one_pager_lambda = lambda_python.PythonFunction(
            self,
            "OnePagerPitchAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/movie_pitch/pitch_one_pager_generator",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        pitch_one_pager_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        pitch_one_pager_job = tasks.LambdaInvoke(
            self,
            "Generate Movie Pitch One-Pager",
            lambda_function=pitch_one_pager_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(pitch_one_pager_job)

        # Hook the agents together into a workflow
        user_choice_fork = (
            sfn.Choice(self, "Greenlight?")
            .when(
                sfn.Condition.string_equals("$.user_choice", "yes"), pitch_one_pager_job
            )
            .when(
                sfn.Condition.string_equals("$.user_choice", "no"),
                movie_pitch_generators,
            )
            .otherwise(
                sfn.Fail(
                    self,
                    "Job Failed",
                    cause="Unknown user choice",
                    error="Unknown user choice",
                )
            )
        )
        chain = (
            movie_pitch_generators.next(pitch_chooser_job)
            .next(user_choice_job)
            .next(user_choice_fork)
        )

        sfn.StateMachine(
            self,
            "MoviePitchWorkflow",
            state_machine_name="PromptChainDemo-MoviePitch",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            # 1 hour to account for getting user feedback in the UI
            timeout=Duration.seconds(3600),
        )
