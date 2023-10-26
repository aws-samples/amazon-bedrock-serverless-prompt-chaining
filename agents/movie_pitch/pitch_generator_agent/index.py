import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    movie_description = event["movie_description"]

    prompt_parts = [
        f"{HUMAN_PROMPT}You are an Oscar-winning screenwriter and you are pitching an idea for a new movie about {movie_description} to a major movie producer."
    ]

    if "movie_pitch" in event:
        prompt_parts.append(
            "You previously pitched this idea for the movie, inside <previous_pitch></previous_pitch> XML tags. The movie producer rejected this idea and asked for a new idea.",
            "<previous_pitch>",
            event["movie_pitch"],
            "</previous_pitch>",
            "Give me your new movie pitch in one paragraph.",
        )
    else:
        prompt_parts.append(
            "Give me your movie pitch in one paragraph.",
        )

    prompt_parts.append(
        f"Start with a tagline sentence that describes the movie as a whole, then follow with a synopsis of the story and the major characters.{AI_PROMPT}"
    )

    request = {
        "prompt": "\n".join(prompt_parts),
        "max_tokens_to_sample": 1024,
        "temperature": event["temperature"],
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    return {
        "movie_pitch": response_body.strip(),
        "movie_description": movie_description,
    }
