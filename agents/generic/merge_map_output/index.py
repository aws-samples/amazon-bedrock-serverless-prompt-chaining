def handler(event, context):
    conversation = event[0]["input"]["conversation"]

    for item_result in event:
        conversation += item_result["output"]["prompt"]
        conversation += item_result["output"]["response"]

    return {"conversation": conversation}
