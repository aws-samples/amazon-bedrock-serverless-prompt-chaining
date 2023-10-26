import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    story_description = event["story_description"]
    all_character_descriptions = event["characters"]
    character_name = event["character"]["name"]
    character_description = event["character"]["description"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are an award-winning fiction writer and you are writing a new story about {story_description}.

You previously decided the story would contain five characters. Here is your description of the characters, inside <characters></characters> XML tags.
<characters>
{json.dumps(all_character_descriptions, indent=2)}
</characters>

Before writing the story, describe what will happen in the story to {character_name}, who you previously described as: ${character_description}.
{AI_PROMPT}""",
        "max_tokens_to_sample": 1024,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    return {
        "character_name": character_name,
        "character_description": character_description,
        "character_story_arc": response_body.strip(),
        "story_description": story_description,
    }
