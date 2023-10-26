import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def get_character_description(character):
    return f"""
Name: {character["character_name"]}
Description: {character["character_description"]}
Story Arc: {character["character_story_arc"]}
"""


def get_character_descriptions(event):
    return "\n\n".join([get_character_description(character) for character in event])


def handler(event, context):
    # Event is an array of items that contain character_name, character_description, character_story_arc, and story_description keys
    story_description = event[0]["story_description"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are an award-winning fiction writer and you are writing a new short story about {story_description}.

You previously decided that the story would contain five characters, and you generated a description and story arc for each character.
Here is your description and story arc for each of the characters, inside <characters></characters> XML tags.
<characters>
{get_character_descriptions(event)}
</characters>

Now write the short story about {story_description}. Respond only with the story content.
{AI_PROMPT}""",
        "max_tokens_to_sample": 2048,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    return {
        "story_description": story_description,
        "story": response_body.strip(),
    }
