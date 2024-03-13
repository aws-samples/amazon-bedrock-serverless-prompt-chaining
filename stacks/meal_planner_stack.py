from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

from .util import (
    get_lambda_bundling_options,
    get_anthropic_claude_invoke_chain,
    get_json_response_parser_step,
)


class MealPlannerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        chefs = ["red", "blue"]

        # Agent #1: generate initial meal options from "red" and "blue" chefs
        meal_generator_prompt = sfn.JsonPath.format(
            """You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{}
Suggest the tastiest dinner I can make at home with these ingredients and minimal additional ingredients.
Do not provide a full recipe, only provide a one or two sentence description of the meal, including a name for the meal.""",
            sfn.JsonPath.string_at("$$.Execution.Input.ingredients"),
        )

        meal_generator_jobs = []
        meal_generator_result_selector = {}
        for i, chef in enumerate(chefs):
            generate_meal_job = get_anthropic_claude_invoke_chain(
                self,
                f"Initial Meal Idea ({chef.capitalize()})",
                prompt=meal_generator_prompt,
                max_tokens_to_sample=500,
                include_previous_conversation_in_prompt=False,
            )
            meal_generator_result_selector[f"{chef}_chef.$"] = f"$[{i}]"
            meal_generator_jobs.append(generate_meal_job)

        initial_meal_generators = sfn.Parallel(
            self,
            "Meals",
            result_selector=meal_generator_result_selector,
        )
        for job in meal_generator_jobs:
            initial_meal_generators = initial_meal_generators.branch(job)

        # Agent #2: score the meals generated
        initialize_debate = sfn.Pass(
            self,
            "Initialize Debate",
            parameters={"debate_round": 0},
            result_path="$.debate_state",
        )

        meal_scoring_prompt = f"""You are a world-class chef acting as a judge on a cooking competition TV show. On this show, you evaluate how tasty each contestant's meal is.
Multiple contestants are competing to prepare the tastiest dish using a set of ingredients.
"""
        meal_scoring_prompt_arguments = []

        for i, chef in enumerate(chefs):
            meal_key = f"{chef}_chef"
            meal_scoring_prompt += f"""
{i+1}. Contestant #{i+1} (Chef {chef.capitalize()}) prepared the following dish, inside <{meal_key}></{meal_key}> XML tags.
<{meal_key}>
{{}}
</{meal_key}>
"""
            meal_scoring_prompt_arguments.append(
                sfn.JsonPath.string_at(f"$.{meal_key}.model_outputs.response")
            )

        meal_scoring_prompt += """
Score the tastiness of each contestant's dish using a number between 0 and 100.
Try to have a distinct tastiness score for each contestant. Output 1 or 2 sentences explaining your reasoning for how you scored the contestant, and then output the score.

Your response should be formatted as a JSON object, with a key for each contestant and an object containing that contestant's score and your reasoning.
An example of a valid response is below, inside <example></example> XML tags.
<example>
\{"""
        for i, chef in enumerate(chefs):
            meal_key = f"{chef}_chef"
            meal_scoring_prompt += f"""
    "{meal_key}": \{{
        "score_reasoning": "Brief reasons for the score I assigned to Chef {chef.capitalize()}...",
        "score": {80 + i}
    \}}"""
            if i < len(chefs) - 1:
                meal_scoring_prompt += ","
        meal_scoring_prompt += """
\}
</example>
Do not include any other content outside of the JSON object.
"""

        meal_scoring_job = get_anthropic_claude_invoke_chain(
            self,
            "Score Meals",
            prompt=sfn.JsonPath.format(
                meal_scoring_prompt, *meal_scoring_prompt_arguments
            ),
            max_tokens_to_sample=500,
            include_previous_conversation_in_prompt=False,
        )

        meal_scores_json_schema = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
        for chef in chefs:
            meal_scores_json_schema["properties"][f"{chef}_chef"] = {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "score_reasoning": {"type": "string"},
                },
                "required": ["score", "score_reasoning"],
                "additionalProperties": False,
            }
            meal_scores_json_schema["required"].append(f"{chef}_chef")

        parse_meal_scores = get_json_response_parser_step(
            self,
            "Parse Meal Scores",
            json_schema=meal_scores_json_schema,
            output_key="scores",
            result_path="$.parsed_output",
        )

        # Agent #3: generate new meal options from "red" and "blue" chefs via debate
        meal_debater_jobs = []
        meal_debater_result_selector = {
            "debate_state": sfn.JsonPath.object_at("$[0].debate_state")
        }
        for i, chef in enumerate(chefs):
            meal_key = f"{chef}_chef"
            chef_name = chef.capitalize()
            prompt = ""
            prompt_arguments = []

            for other_i, other_chef in enumerate(chefs):
                if other_i == i:
                    continue
                other_meal_key = f"{other_chef}_chef"
                other_chef_name = other_chef.capitalize()
                prompt += f"""Another chef (Chef {other_chef_name}) suggested the following meal to me, inside <{other_chef_name}Dinner></{other_chef_name}Dinner> XML tags.
<{other_chef_name}Dinner>
{{}}
</{other_chef_name}Dinner>"""
                prompt_arguments.append(
                    sfn.JsonPath.string_at(f"$.{other_meal_key}.model_outputs.response")
                )

                prompt += f"""
Chef {other_chef_name}'s suggested meal was scored for tastiness on a scale of 0 to 100 and received the following score and score explanation, inside <{other_chef_name}Score></{other_chef_name}Score> XML tags.
<{other_chef_name}Score>
{{}}
{{}}
</{other_chef_name}Score>"""
                prompt_arguments.append(
                    sfn.JsonPath.string_at(
                        f"$.parsed_output.scores.{other_meal_key}.score"
                    )
                )
                prompt_arguments.append(
                    sfn.JsonPath.string_at(
                        f"$.parsed_output.scores.{other_meal_key}.score_reasoning"
                    )
                )

            prompt += f"""
You got the following tastiness score and score explanation for your own meal suggestion, inside <{chef_name}Score></{chef_name}Score> XML tags.
<{chef_name}Score>
{{}}
{{}}
</{chef_name}Score>
"""
            prompt_arguments.append(
                sfn.JsonPath.string_at(f"$.parsed_output.scores.{meal_key}.score")
            )
            prompt_arguments.append(
                sfn.JsonPath.string_at(
                    f"$.parsed_output.scores.{meal_key}.score_reasoning"
                )
            )

            prompt += """
Compare the other chefs' answers with yours and try to improve your own answer to be more tasty than theirs.
You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{}
Suggest the tastiest dinner I can make at home with these ingredients and minimal additional ingredients.
Do not provide a full recipe, only provide a one or two sentence description of the meal, including a name for the meal.
"""
            prompt_arguments.append(
                sfn.JsonPath.string_at("$$.Execution.Input.ingredients")
            )

            debate_meal_job = get_anthropic_claude_invoke_chain(
                self,
                f"Debate Meal Idea ({chef.capitalize()})",
                prompt=sfn.JsonPath.format(prompt, *prompt_arguments),
                max_tokens_to_sample=500,
                include_previous_conversation_in_prompt=True,
                input_json_path=f"$.{meal_key}.model_inputs",
                output_json_path=f"$.{meal_key}.model_outputs",
            )
            meal_debater_result_selector[f"{chef}_chef"] = sfn.JsonPath.object_at(
                f"$[{i}].{chef}_chef"
            )
            meal_debater_jobs.append(debate_meal_job)

        meal_debaters = sfn.Parallel(
            self,
            "MealDebaters",
            result_selector=meal_debater_result_selector,
            result_path="$.meal_debate_results",
        )
        for job in meal_debater_jobs:
            meal_debaters = meal_debaters.branch(job)

        debate_counter_params = {
            "debate_state": {
                "debate_round": sfn.JsonPath.math_add(
                    sfn.JsonPath.number_at("$.debate_state.debate_round"), 1
                )
            }
        }
        for chef in chefs:
            debate_counter_params[f"{chef}_chef"] = sfn.JsonPath.object_at(
                f"$.meal_debate_results.{chef}_chef"
            )
        increment_debate_counter = sfn.Pass(
            self,
            "Increment Debate Counter",
            parameters=debate_counter_params,
        )

        # Agent #4: determine if there is consensus or if we need another debate round
        referee_prompt = """You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
Multiple other chefs are working together to agree on the tastiest dinner I could make at home.
"""
        referee_prompt_arguments = []

        for i, chef in enumerate(chefs):
            meal_key = f"{chef}_chef"
            chef_name = chef.capitalize()
            referee_prompt += f"""
{i+1}. Meal suggestion from Chef {chef_name} is below, inside <{chef_name}></{chef_name}> XML tags.
<{chef_name}>
{{}}
</{chef_name}>
"""
            referee_prompt_arguments.append(
                sfn.JsonPath.string_at(f"$.{meal_key}.model_outputs.response")
            )

        referee_prompt += """
Do these chefs agree with each other on the tastiest meal I could make?
Answer no only if the chefs suggested very different meals.
Answer yes if the chefs suggested the same meal, similar meals, or meals that are a small variation of each other.
Start your response with an explanation of your reasoning, then provide a single 'yes' or 'no' indicating whether agreement has been reached.

Your response should be formatted as a JSON object. An example of a valid response is below when the chefs do agree, inside <example></example> XML tags.
<example>
\{
    "reasoning": "Brief reasons for why I believe the chefs have reached agreement...",
    "do_chefs_agree": "yes"
\}
</example>

Another example of a valid response is below when the chefs do not agree, inside <example></example> XML tags.
<example>
\{
    "reasoning": "Brief reasons for why I believe the chefs have not reached agreement...",
    "do_chefs_agree": "no"
\}
</example>
Do not include any other content outside of the JSON object.
"""

        meal_debate_referee_job = get_anthropic_claude_invoke_chain(
            self,
            "Referee Meal Debate",
            prompt=sfn.JsonPath.format(referee_prompt, *referee_prompt_arguments),
            max_tokens_to_sample=500,
            include_previous_conversation_in_prompt=False,
        )

        parse_referee_response = get_json_response_parser_step(
            self,
            "Parse Referee Response",
            json_schema={
                "type": "object",
                "properties": {
                    "reasoning": {"type": "string"},
                    "do_chefs_agree": {"type": "string", "enum": ["yes", "no"]},
                },
                "required": ["reasoning", "do_chefs_agree"],
                "additionalProperties": False,
            },
            output_key="consensus",
            result_path="$.referee_output",
        )

        # Agent #5: produce a final score for the final meal ideas from each chef
        final_meal_scoring_job = get_anthropic_claude_invoke_chain(
            self,
            "Score Final Meals",
            prompt=sfn.JsonPath.format(
                meal_scoring_prompt, *meal_scoring_prompt_arguments
            ),
            max_tokens_to_sample=500,
            include_previous_conversation_in_prompt=False,
        )

        parse_final_meal_scores = get_json_response_parser_step(
            self,
            "Parse Final Meal Scores",
            json_schema=meal_scores_json_schema,
            output_key="scores",
            result_path="$.parsed_output",
        )

        # Agent #6: choose the highest scoring meal
        meal_choose_winner_lambda = lambda_python.PythonFunction(
            self,
            "MealChooseAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions/meal_planner/meal_choose_winner_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        meal_choose_winner_job = tasks.LambdaInvoke(
            self,
            "Choose Winning Meal",
            lambda_function=meal_choose_winner_lambda,
            output_path="$.Payload",
        )

        # Agent #7: generate a recipe for the meal
        recipe_job = get_anthropic_claude_invoke_chain(
            self,
            "Generate Recipe",
            prompt=sfn.JsonPath.format(
                """You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{}

You previously suggested this meal, inside <dinner></dinner> XML tags.
<dinner>
{}
</dinner>

Create a recipe for this meal, based on your previous meal suggestion and the ingredients I have on hand.""",
                sfn.JsonPath.string_at("$$.Execution.Input.ingredients"),
                sfn.JsonPath.string_at("$.winning_meal"),
            ),
            max_tokens_to_sample=2000,
            include_previous_conversation_in_prompt=False,
            pass_conversation=False,
        )

        select_final_response = sfn.Pass(
            self,
            "Extract Recipe",
            parameters={
                "recipe": sfn.JsonPath.string_at("$.model_outputs.response"),
                "ingredients": sfn.JsonPath.string_at("$$.Execution.Input.ingredients"),
                "meal": sfn.JsonPath.string_at("$.winning_meal"),
            },
        )

        # Hook the agents together into a workflow
        meal_consensus_fork = (
            sfn.Choice(self, "Consensus reached?")
            .when(
                sfn.Condition.or_(
                    sfn.Condition.string_equals(
                        "$.referee_output.consensus.do_chefs_agree", "yes"
                    ),
                    sfn.Condition.number_greater_than_equals(
                        "$.debate_state.debate_round", 3
                    ),
                ),
                final_meal_scoring_job.next(parse_final_meal_scores)
                .next(meal_choose_winner_job)
                .next(recipe_job)
                .next(select_final_response),
            )
            .when(
                sfn.Condition.string_equals(
                    "$.referee_output.consensus.do_chefs_agree", "no"
                ),
                meal_scoring_job,
            )
            .otherwise(sfn.Fail(self, "Not a valid model response for consensus"))
        )
        chain = (
            initial_meal_generators.next(initialize_debate)
            .next(meal_scoring_job)
            .next(parse_meal_scores)
            .next(meal_debaters)
            .next(increment_debate_counter)
            .next(meal_debate_referee_job)
            .next(parse_referee_response)
            .next(meal_consensus_fork)
        )

        sfn.StateMachine(
            self,
            "MealPlannerWorkflow",
            state_machine_name="PromptChainDemo-MealPlanner",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
