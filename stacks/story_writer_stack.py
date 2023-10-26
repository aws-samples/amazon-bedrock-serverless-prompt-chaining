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


class StoryWriterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: create characters
        characters_lambda = lambda_python.PythonFunction(
            self,
            "CharacterAgent",
            entry="agents/story_writer/characters_agent",
            bundling=get_lambda_bundling_options(),
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        characters_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        characters_job = tasks.LambdaInvoke(
            self,
            "Generate Characters",
            lambda_function=characters_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(characters_job)

        # Agent #2: create character story arc
        character_story_lambda = lambda_python.PythonFunction(
            self,
            "CharacterStoryAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/story_writer/character_story_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        character_story_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        character_story_job = tasks.LambdaInvoke(
            self,
            "Generate Character Story Arc",
            lambda_function=character_story_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(character_story_job)

        # Agent #3: write the story
        story_lambda = lambda_python.PythonFunction(
            self,
            "StoryAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/story_writer/story_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        story_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        story_job = tasks.LambdaInvoke(
            self,
            "Generate the Full Story",
            lambda_function=story_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(story_job)

        # Hook the agents together into a workflow that contains some loops
        chain = characters_job.next(
            sfn.Map(
                self,
                "Character Story Map",
                items_path=sfn.JsonPath.string_at("$.characters"),
                parameters={
                    "character.$": "$$.Map.Item.Value",
                    "characters.$": "$.characters",
                    "story_description.$": "$.story_description",
                },
                max_concurrency=3,
            ).iterator(character_story_job)
        ).next(story_job)

        sfn.StateMachine(
            self,
            "StoryWriterWorkflow",
            state_machine_name="PromptChainDemo-StoryWriter",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
