import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    story_description = event["story_description"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are an award-winning fiction writer and you are writing a new story about {story_description}.
Before writing the story, describe five characters that will be in the story.

Your response should be formatted as a JSON array, with each element in the array containing a "name" key for the character's name and a "description" key with the character's description.
An example of a valid response is below, inside <example></example> XML tags.
<example>
[
    {{
        "name": "Character 1",
        "description": "Description for character 1"
    }},
    {{
        "name": "Character 2",
        "description": "Description for character 2"
    }}
]
</example>
{AI_PROMPT}""",
        "max_tokens_to_sample": 512,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]
    completion = json.loads(response_body)

    return {
        "characters": completion,
        "story_description": story_description,
    }
