def handler(event, context):
    scores = event["parsed_output"]["scores"]

    # Find the highest score
    # Scores is a dictionary of chef key -> score
    highest_score = 0
    winning_chef = None
    for key, value in scores.items():
        score = value["score"]
        if score > highest_score:
            highest_score = score
            winning_chef = key

    if not winning_chef:
        raise Exception("No winning meal found")

    winning_meal = event[winning_chef]["model_outputs"]["response"]

    return {"winning_chef": winning_chef, "winning_meal": winning_meal}
