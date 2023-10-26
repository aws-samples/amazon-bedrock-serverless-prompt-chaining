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
    add_bedrock_retries,
    get_bedrock_iam_policy_statement,
    get_lambda_bundling_options,
)


class MealPlannerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: generate initial meal options from "red" and "blue" chefs
        initial_meal_generators = sfn.Parallel(
            self,
            "Meals",
            result_path="$.generated_meals",
        )

        meal_lambda = lambda_python.PythonFunction(
            self,
            f"MealAgent",
            entry="agents/meal_planner/meal_generator_agent",
            bundling=get_lambda_bundling_options(),
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        meal_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        red_agent_meal_job = tasks.LambdaInvoke(
            self,
            f"Initial Meal Idea (Red)",
            lambda_function=meal_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object(
                {
                    "agent": "red",
                    "input": sfn.JsonPath.object_at("$"),
                }
            ),
        )
        add_bedrock_retries(red_agent_meal_job)

        blue_agent_meal_job = tasks.LambdaInvoke(
            self,
            f"Initial Meal Idea (Blue)",
            lambda_function=meal_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object(
                {
                    "agent": "blue",
                    "input": sfn.JsonPath.object_at("$"),
                }
            ),
        )
        add_bedrock_retries(blue_agent_meal_job)

        initial_meal_generators = initial_meal_generators.branch(
            red_agent_meal_job
        ).branch(blue_agent_meal_job)

        # Agent #2: score the meals generated
        meal_scoring_lambda = lambda_python.PythonFunction(
            self,
            "MealScoringAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/meal_planner/meal_scoring_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        meal_scoring_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        meal_scoring_job = tasks.LambdaInvoke(
            self,
            "Score Meals",
            lambda_function=meal_scoring_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(meal_scoring_job)

        # Agent #3: generate new meal options from "red" and "blue" chefs via debate
        meal_debaters = sfn.Parallel(
            self,
            "MealDebaters",
            result_path="$.latest_debate_round",
        )

        meal_debater_lambda = lambda_python.PythonFunction(
            self,
            f"MealDebaterAgent",
            entry="agents/meal_planner/meal_debater_agent",
            bundling=get_lambda_bundling_options(),
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        meal_debater_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        red_agent_meal_debater_job = tasks.LambdaInvoke(
            self,
            f"Debate Meal (Red)",
            lambda_function=meal_debater_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object(
                {
                    "agent": "red",
                    "input": sfn.JsonPath.object_at("$"),
                }
            ),
        )
        add_bedrock_retries(red_agent_meal_debater_job)

        blue_agent_meal_debater_job = tasks.LambdaInvoke(
            self,
            f"Debate Meal (Blue)",
            lambda_function=meal_debater_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object(
                {
                    "agent": "blue",
                    "input": sfn.JsonPath.object_at("$"),
                }
            ),
        )
        add_bedrock_retries(blue_agent_meal_debater_job)

        meal_debaters = meal_debaters.branch(red_agent_meal_debater_job).branch(
            blue_agent_meal_debater_job
        )

        # Agent #4: determine if there is consensus or if we need another debate round
        meal_debate_referee_lambda = lambda_python.PythonFunction(
            self,
            "MealDebateRefereeAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/meal_planner/meal_debate_referee_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        meal_debate_referee_lambda.add_to_role_policy(
            get_bedrock_iam_policy_statement()
        )

        meal_debate_referee_job = tasks.LambdaInvoke(
            self,
            "Referee Meal Debate",
            lambda_function=meal_debate_referee_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(meal_debate_referee_job)

        # Agent #5: produce a final score for the final meal ideas from each chef
        final_meal_scoring_job = tasks.LambdaInvoke(
            self,
            "Score Final Meals",
            lambda_function=meal_scoring_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(final_meal_scoring_job)

        # Agent #6: choose the highest scoring meal
        meal_choose_winner_lambda = lambda_python.PythonFunction(
            self,
            "MealChooseAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/meal_planner/meal_choose_winner_agent",
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
        recipe_lambda = lambda_python.PythonFunction(
            self,
            "RecipeAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/meal_planner/recipe_generator",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        recipe_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        recipe_job = tasks.LambdaInvoke(
            self,
            "Generate Recipe",
            lambda_function=recipe_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(recipe_job)

        # Hook the agents together into a workflow
        meal_consensus_fork = (
            sfn.Choice(self, "Consensus reached?")
            .when(
                sfn.Condition.or_(
                    sfn.Condition.string_equals("$.consensus", "yes"),
                    sfn.Condition.string_equals(
                        "$.consensus", "max debate rounds reached"
                    ),
                ),
                final_meal_scoring_job.next(meal_choose_winner_job).next(recipe_job),
            )
            .when(
                sfn.Condition.string_equals("$.consensus", "no"),
                meal_scoring_job,
            )
        )
        chain = (
            initial_meal_generators.next(meal_scoring_job)
            .next(meal_debaters)
            .next(meal_debate_referee_job)
            .next(meal_consensus_fork)
        )

        sfn.StateMachine(
            self,
            "MealPlannerWorkflow",
            state_machine_name="PromptChainDemo-MealPlanner",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
