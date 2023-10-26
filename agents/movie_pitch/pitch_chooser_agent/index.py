import boto3
import json
from num2words import num2words


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def get_pitch_description(i, entry):
    pitch = entry["movie_pitch"]
    num_word = num2words(i)
    return f"""
{i}. Movie pitch {num_word} is below, inside <{num_word}></{num_word}> XML tags.
<{num_word}>
{pitch}
</{num_word}>
"""


def get_pitch_descriptions(event):
    return "\n".join(
        [get_pitch_description(i + 1, entry) for i, entry in enumerate(event)]
    )


def get_pitch_choices(event):
    return "\n".join(
        [f"({i+1}) Movie pitch {num2words(i+1)}" for i, entry in enumerate(event)]
    )


def handler(event, context):
    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are a producer of Oscar-winning movies, and you are deciding on the next movie you will make.
Screenwriters previously pitched you on {len(event)} movie ideas, and you need to pick one of the ideas.

{get_pitch_descriptions(event)}

Now choose one of the movie pitches. The possible selections are:
{get_pitch_choices(event)}

{AI_PROMPT} My choice is (""",
        "max_tokens_to_sample": 300,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    # Completion should be in the format "1) Movie pitch one"
    choice = int(response_body.strip()[0]) - 1

    return event[choice]
