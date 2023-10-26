import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")
HUMAN_PROMPT = "\n\nHuman:"
AI_PROMPT = "\n\nAssistant:"


def handler(event, context):
    movie_description = event["movie_description"]
    movie_pitch = event["movie_pitch"]

    request = {
        "prompt": f"""{HUMAN_PROMPT}
You are an Oscar-winning screenwriter and you are pitching an idea for a new movie about {movie_description} to a major movie producer.

You previously pitched this short description for the movie, inside <pitch></pitch> XML tags.
<pitch>
{movie_pitch}
</pitch>

Now create a one-page movie pitch, based on your previous short description for the movie.
{AI_PROMPT}""",
        "max_tokens_to_sample": 2000,
        "temperature": 1,
    }

    response = bedrock_client.invoke_model(
        modelId="anthropic.claude-instant-v1",
        body=json.dumps(request),
    )

    response_body = json.loads(response["body"].read().decode("utf-8"))["completion"]

    return {
        "movie_pitch_one_pager": response_body.strip(),
        "movie_description": movie_description,
    }
