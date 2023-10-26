import json


def handler(event, context):
    ingredients = event["ingredients"]
    scores = event["scores"]
    meals = event["generated_meals"]

    # Find the highest score
    # Scores is a dictionary of agent color -> score
    highest_score = 0
    winning_meal = None
    for meal_entry in meals:
        agent_color = meal_entry["agent"]
        meal_description = meal_entry["meal"]

        if agent_color in scores:
            score = scores[agent_color]["score"]
            if score > highest_score:
                highest_score = score
                winning_meal = meal_description

    if not winning_meal:
        raise Exception("No winning meal found")

    return {"meal": winning_meal, "ingredients": ingredients}
