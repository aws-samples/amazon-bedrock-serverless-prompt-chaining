import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    meal = event["meal"]
    ingredients = event["ingredients"]

    prompt = f"""{HUMAN_PROMPT}
You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{ingredients}

You previously suggested this meal, inside <dinner></dinner> XML tags.
<dinner>
{meal}
</dinner>

Create a recipe for this meal, based on your previous meal suggestion and the ingredients I have on hand.
{AI_PROMPT}"""

    request = {
        "prompt": prompt,
        "max_tokens_to_sample": 2000,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    print("Prompt:")
    print(prompt)
    print("Response:")
    print(response_body)

    return {
        "recipe": response_body.strip(),
        "meal": meal,
        "ingredients": ingredients,
    }
