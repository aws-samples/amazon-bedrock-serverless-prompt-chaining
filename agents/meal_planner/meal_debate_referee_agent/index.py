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
{i}. Meal suggestion from chef {color} is below, inside <{color}></{color}> XML tags.
<{color}>
{meal}
</{color}>
"""


def get_meal_descriptions(event):
    # Event is an array of items that contain meal and ingredients keys
    return "\n".join(
        [
            get_meal_description(i + 1, entry)
            for i, entry in enumerate(event["latest_debate_round"])
        ]
    )


def handler(event, context):
    ingredients = event["ingredients"]

    prompt = f"""{HUMAN_PROMPT}
You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
Multiple other chefs are working together to agree on the tastiest dinner I could make at home.

{get_meal_descriptions(event)}

Do these {num2words(len(event))} chefs agree with each other on the tastiest meal I could make?
Answer no only if the chefs suggested very different meals.
Answer yes if the chefs suggested the same meal, similar meals, or meals that are a small variation of each other.
Start your response with an explanation. The last line in the response should be a single YES or NO indicating whether agreement has been reached.{AI_PROMPT}"""

    consensus = None
    last_answer = None
    for i in range(3):
        if last_answer:
            prompt += (
                f"{last_answer}{HUMAN_PROMPT}Please answer only yes or no.{AI_PROMPT}"
            )

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
        ]

        print("Prompt:")
        print(prompt)
        print("Response:")
        print(response_body)

        # Get the last line and last word of the completion, remove punctuation ("Yes!"), and convert to lower-case
        last_answer = response_body
        answer_value = re.sub(
            r"[^\w\s]",
            "",
            response_body.strip().split("\n")[-1].strip().split(" ")[-1].lower(),
        )
        if answer_value == "yes" or answer_value == "no":
            consensus = answer_value
            break

    if not consensus:
        consensus = "LLM did not determine consensus"

    meals_per_agent = {}
    for entry in event["latest_debate_round"]:
        meals_per_agent[entry["agent"]] = entry["meal"]

    # Count how many times we've been trying to seek consensus
    debate_round_counter = 1
    if "debate_round_counter" in event:
        debate_round_counter = event["debate_round_counter"] + 1

    if consensus != "yes" and debate_round_counter >= 3:
        consensus = "max debate rounds reached"

    return {
        "consensus": consensus,
        "debate_round_counter": debate_round_counter,
        "generated_meals": event["latest_debate_round"],
        "memory": event["memory"],
        "ingredients": ingredients,
    }
