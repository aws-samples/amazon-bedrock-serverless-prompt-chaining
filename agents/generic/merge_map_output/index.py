def handler(event, context):
    # Assume every map result contains 2 unique conversation entries (user prompt and assistant response),
    # and every map result has the same conversation history before that

    conversation = event[0]["model_outputs"]["conversation"][:-2]

    for item_result in event:
        conversation.extend(item_result["model_outputs"]["conversation"][-2:])

    return {"conversation": conversation}
