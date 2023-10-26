import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    location = event["location"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are a world-class travel agent and an expert on travel to {location}.
I am going on a weekend vacation to {location}.
Please give me up to 5 suggestions for activities to do or places to visit during my vacation.
{AI_PROMPT}""",
        "max_tokens_to_sample": 512,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    return {
        "activities": response_body.strip(),
        "location": location,
    }
