import boto3
import json


bedrock_client = boto3.client("bedrock-runtime")


def handler(event, context):
    print("Received event:")
    print(event)

    response = bedrock_client.invoke_model(
        modelId=event["ModelId"],
        body=json.dumps(event["Body"]),
    )

    # read the streaming body and replace with a string for serialization
    body = json.loads(response["body"].read().decode("utf-8"))
    response["body"] = body

    print("Returned response:")
    print(response)

    return response
