import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    my_agent_color = event["agent"]
    input = event["input"]
    ingredients = input["ingredients"]

    prompt_parts = [
        f"""{HUMAN_PROMPT}You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{ingredients}
Suggest the tastiest dinner I can make at home with these ingredients and minimal additional ingredients.
Do not provide a full recipe, only provide a one or two sentence description of the meal, including a name for the meal.{AI_PROMPT}""",
    ]
    prompt = "\n".join(prompt_parts)

    request = {
        "prompt": prompt,
        "max_tokens_to_sample": 500,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))[
        "completion"
    ].strip()

    print("Prompt:")
    print(prompt)
    print("Response:")
    print(response_body)

    return {
        "meal": response_body,
        "agent": my_agent_color,
        "conversation": prompt + response_body,
    }
