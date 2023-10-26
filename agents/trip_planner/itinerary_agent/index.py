import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    location = event["location"]
    hotels = event["hotels"]
    restaurants = event["restaurants"]
    activities = event["activities"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are a world-class travel agent and an expert on travel to {location}.
I am going on a weekend vacation to {location} (arriving Friday, leaving Sunday).

You previously recommended these hotels, inside <hotels></hotels> XML tags.
<hotels>
{hotels}
</hotels>

You previously recommended these restaurants, inside <restaurants></restaurants> XML tags.
<restaurants>
{restaurants}
</restaurants>

You previously recommended these activities, inside <activities></activities> XML tags.
<activities>
{activities}
</activities>

Please give me a daily itinerary for my three-day vacation, based on your previous recommendations.
The itinerary should include one hotel where I will stay for the duration of the vacation.
Each of the three days in the itinerary should have one activity, one restaurant for breakfast, one restaurant for lunch, and one restaurant for dinner.
Each entry in the itinerary should include a short description of your recommended hotel, activity, or restaurant.
The itinerary should be formatted in Markdown format.
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
        "itinerary": response_body.strip(),
        "location": location,
    }
