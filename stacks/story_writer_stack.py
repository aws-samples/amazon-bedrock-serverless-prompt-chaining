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
    get_anthropic_claude_invoke_chain,
    get_json_response_parser_step,
)


class StoryWriterStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: create characters
        characters_job = get_anthropic_claude_invoke_chain(
            self,
            "Generate Characters",
            prompt=sfn.JsonPath.format(
                """You are an award-winning fiction writer and you are writing a new story about {}.
Before writing the story, describe five characters that will be in the story.

Your response should be formatted as a JSON array, with each element in the array containing a "name" key for the character's name and a "description" key with the character's description.
An example of a valid response is below, inside <example></example> XML tags.
<example>
[
    \{
        "name": "Character 1",
        "description": "Description for character 1"
    \},
    \{
        "name": "Character 2",
        "description": "Description for character 2"
    \}
]
</example>
Do not include any other content outside of the JSON object.
""",
                sfn.JsonPath.string_at("$$.Execution.Input.story_description"),
            ),
            max_tokens_to_sample=512,
            include_previous_conversation_in_prompt=False,
        )

        parse_characters_step = get_json_response_parser_step(
            self,
            "Parse Characters",
            json_schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["name", "description"],
                    "additionalProperties": False,
                },
                "minItems": 5,
                "maxItems": 5,
                "uniqueItems": True,
            },
            output_key="characters",
            result_path="$.parsed_output",
        )

        # Agent #2: create character story arc
        character_story_job = get_anthropic_claude_invoke_chain(
            self,
            "Generate Character Story Arc",
            prompt=sfn.JsonPath.format(
                "Now describe what will happen in the story to {}, who you previously described as: {}.",
                sfn.JsonPath.string_at("$.character.name"),
                sfn.JsonPath.string_at("$.character.description"),
            ),
            max_tokens_to_sample=1024,
            include_previous_conversation_in_prompt=True,
        )

        merge_character_stories_lambda = lambda_python.PythonFunction(
            self,
            "MergeCharacterStoriesAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions/generic/merge_map_output",
            memory_size=256,
        )

        merge_character_stories_job = tasks.LambdaInvoke(
            self,
            "Merge Character Stories",
            lambda_function=merge_character_stories_lambda,
            result_selector={"model_outputs": sfn.JsonPath.object_at("$.Payload")},
        )

        # Agent #3: write the story
        story_job = get_anthropic_claude_invoke_chain(
            self,
            "Generate the Full Story",
            prompt=sfn.JsonPath.format(
                "Now write the short story about {}. Respond only with the story content.",
                sfn.JsonPath.string_at("$$.Execution.Input.story_description"),
            ),
            max_tokens_to_sample=2048,
            include_previous_conversation_in_prompt=True,
            pass_conversation=False,
        )

        select_story = sfn.Pass(
            self,
            "Select Story",
            parameters={
                "story": sfn.JsonPath.string_at("$.model_outputs.response"),
            },
        )

        # Hook the agents together into a workflow that contains a map
        chain = (
            characters_job.next(parse_characters_step)
            .next(
                sfn.Map(
                    self,
                    "Character Story Map",
                    items_path=sfn.JsonPath.string_at("$.parsed_output.characters"),
                    parameters={
                        "character.$": "$$.Map.Item.Value",
                        "model_outputs.$": "$.model_outputs",
                    },
                    max_concurrency=3,
                ).iterator(character_story_job)
            )
            .next(merge_character_stories_job)
            .next(story_job)
            .next(select_story)
        )

        sfn.StateMachine(
            self,
            "StoryWriterWorkflow",
            state_machine_name="PromptChainDemo-StoryWriter",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
