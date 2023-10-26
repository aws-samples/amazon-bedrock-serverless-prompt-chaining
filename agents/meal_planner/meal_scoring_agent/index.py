from num2words import num2words
import boto3
import json
import re


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def get_meal_description(i, entry):
    meal = entry["meal"]
    color = entry["agent"]
    return f"""
{i}. Contestant {color} prepared the following dish, inside <{color}></{color}> XML tags.
<{color}>
{meal}
</{color}>
"""


def get_meal_descriptions(event):
    return "\n".join(
        [
            get_meal_description(i + 1, entry)
            for i, entry in enumerate(event["generated_meals"])
        ]
    )


def get_score_format(event):
    return "\n".join(
        [
            f'Contestant {entry["agent"]}: {{brief reasons for contestant {entry["agent"]}\'s tastiness score}}. Score: {{contestant {entry["agent"]}\'s tastiness score}}'
            for entry in event["generated_meals"]
        ]
    )


def handler(event, context):
    # Merge in the latest conversation to each agent's short-term memory
    # Memory is stored as {"agent color": [convo, convo, ...], "other agent color": [convo, convo, ...]}
    result = {
        "memory": {},
        "ingredients": event["ingredients"],
        "generated_meals": event["generated_meals"],
    }
    result["debate_round_counter"] = (
        event["debate_round_counter"] if "debate_round_counter" in event else 0
    )
    if "memory" in event:
        result["memory"] = event["memory"]
    for entry in event["generated_meals"]:
        if entry["agent"] not in result["memory"]:
            result["memory"][entry["agent"]] = []
        result["memory"][entry["agent"]].append(entry["conversation"])

    # Generate scores
    prompt = f"""{HUMAN_PROMPT}
You are a world-class chef acting as a judge on a cooking competition TV show. On this show, you evaluate how tasty each contestant's meal is.
Multiple contestants are competing to prepare the tastiest dish using a set of ingredients.

{get_meal_descriptions(event)}

Score the tastiness of each contestant's dish using a number between 0 and 100.
Try to have a distinct tastiness score for each contestant.
Output the scores with 1 or 2 sentences explaining your reasoning, using the format of the following example in <format></format> XML tags.
<format>
{get_score_format(event)}
</format>
{AI_PROMPT}"""

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

    # Parse out the scores
    response_lines = response_body.split("\n")
    print(response_lines)
    scores = {}
    for line in response_lines:
        line = line.strip()
        if line == "":
            continue
        if line.startswith("Contestant "):
            parts = line.split(": ")
            agent_color = parts[0].replace("Contestant ", "").strip().lower()
            agent_score = int(parts[-1].strip())
            scores[agent_color] = {
                "score": agent_score,
                "reason": line.split(": ", 1)[1].strip(),
            }
        else:
            print(f"Unexpected line: {line}")
    result["scores"] = scores

    return result
