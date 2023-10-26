import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    my_agent_color = event["agent"]
    input = event["input"]
    my_agent_memory = input["memory"][my_agent_color]
    scores = input["scores"]
    ingredients = input["ingredients"]

    prompt_parts = [HUMAN_PROMPT]

    my_meal = None
    for entry in input["generated_meals"]:
        agent = entry["agent"]
        meal = entry["meal"]

        if agent == my_agent_color:
            my_meal = meal
        else:
            prompt_parts.append(
                f"""
Another chef (Chef {agent}) suggested the following meal to me, inside <{agent}Dinner></{agent}Dinner> XML tags.
<{agent}Dinner>
{meal}
</{agent}Dinner>
"""
            )
            if agent in scores:
                score = scores[agent]["reason"]
                prompt_parts.append(
                    f"""
Chef {agent}'s suggested meal was scored for tastiness on a scale of 0 to 100 and received the following score and score explanation, inside <{agent}Score></{agent}Score> XML tags.
<{agent}Score>
{score}
</{agent}Score>"""
                )

    if my_meal and my_agent_color in scores:
        score = scores[my_agent_color]["reason"]
        prompt_parts.append(
            f"""
You got the following tastiness score and score explanation for your own meal suggestion, inside <{my_agent_color}Score></{my_agent_color}Score> XML tags.
<{my_agent_color}Score>
{score}
</{my_agent_color}Score>
"""
        )

    prompt_parts.append(
        f"""
Compare the other chefs' answers with yours and try to improve your own answer to be more tasty than theirs.
You are a world-class chef and you help people to plan out tasty home-cooked meals that they can cook themselves.
I need help determining a tasty dinner I can make with the following ingredients I have on hand in my kitchen:
{ingredients}
Suggest the tastiest dinner I can make at home with these ingredients and minimal additional ingredients.
Do not provide a full recipe, only provide a one or two sentence description of the meal, including a name for the meal.{AI_PROMPT}
"""
    )

    prompt = "\n".join(prompt_parts)
    previous_conversation = "\n".join(my_agent_memory)

    request = {
        "prompt": previous_conversation + prompt,
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
    print(previous_conversation + prompt)
    print("Response:")
    print(response_body)

    return {
        "meal": response_body.strip(),
        "agent": my_agent_color,
        "conversation": prompt + response_body,
    }
