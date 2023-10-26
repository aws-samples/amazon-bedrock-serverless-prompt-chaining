import streamlit as st
import uuid
import json

import stepfn

st.set_page_config(layout="wide")

st.title("Meal planner demo")

execution_status_container = None

# Populate a unique user ID to use for naming the Step Functions execution
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())


def display_state_machine_status(status_markdown):
    if execution_status_container:
        execution_status_container.empty()
        with execution_status_container.container():
            st.subheader("⚙️ Step Functions execution")
            st.markdown(status_markdown)


def display_no_state_machine_status():
    if execution_status_container:
        execution_status_container.empty()
        with execution_status_container.container():
            st.subheader("⚙️ Step Functions execution")
            st.write("Not started yet.")


def execute_state_machine(ingredients):
    input = {"ingredients": ingredients}
    execution_arn = stepfn.start_execution(
        "PromptChainDemo-MealPlanner",
        st.session_state.user_id,
        json.dumps(input),
    )
    st.session_state.meal_planner_execution_arn = execution_arn
    return stepfn.poll_for_execution_completion(
        execution_arn, display_state_machine_status
    )


demo_col, behind_the_scenes_col = st.columns(spec=[1, 1], gap="large")

with behind_the_scenes_col:
    execution_status_container = st.empty()

    if "meal_planner_execution_arn" in st.session_state:
        status_markdown = stepfn.describe_execution(
            st.session_state.meal_planner_execution_arn
        )
        display_state_machine_status(status_markdown)
    else:
        display_no_state_machine_status()

    st.subheader("🔍 Behind the scenes")
    st.write(
        "This demo illustrates using debate between two agents to improve the final answer. \
        When the user provides some ingredients they have on hand, multiple agents run in parallel to suggest the 'tastiest' meal the user can make. \
        Another agent scores the meal suggestions on a scale of 0 to 100 for 'tastiness'. \
        The agents then debate additional meal suggestions to attempt to improve their own score in comparison to the other agents. \
        A separate 'referee' agent determines if there is consensus among the agents about the tastiest meal, \
        and if not, the workflow loops back to the agents for another debate round. \
        A small code-only function chooses the highest-scoring meal (no LLM interaction), and a final agent generates a recipe for that meal."
    )
    st.image(image="/app/pages/workflow_images/meal_planner.png")

with demo_col:
    st.subheader("🚀 Demo")

    with st.form("start_meal_planner_demo_form"):
        st.info(
            "Press Start to generate a tasty dinner recipe using your provided ingredients."
        )
        ingredients_text = st.text_input(
            "Enter a few ingredients you have on hand:", "Chicken, Rice"
        )
        started = st.form_submit_button("Start")
        if started:
            with st.spinner("Wait for it..."):
                if "meal_planner_execution_arn" in st.session_state:
                    del st.session_state["meal_planner_execution_arn"]
                display_no_state_machine_status()
                response = execute_state_machine(ingredients_text)

                st.session_state.meal_planner_execution_status = response["status"]
                if response["status"] == "SUCCEEDED":
                    output = json.loads(response["output"])
                    st.session_state.recipe = output["recipe"]

            if st.session_state.meal_planner_execution_status == "SUCCEEDED":
                st.success("Done!")
                st.write(st.session_state.recipe)
            else:
                st.error("Your meal recipe could not be created. Please try again.")
