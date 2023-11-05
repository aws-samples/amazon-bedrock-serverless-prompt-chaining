import streamlit as st
import uuid
import json

import stepfn

st.set_page_config(layout="wide")

st.title("Story writer")

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


def execute_state_machine(story_description):
    input = {"story_description": story_description}
    execution_arn = stepfn.start_execution(
        "PromptChainDemo-StoryWriter",
        st.session_state.user_id,
        json.dumps(input),
    )
    st.session_state.story_writer_execution_arn = execution_arn
    return stepfn.poll_for_execution_completion(
        execution_arn, display_state_machine_status
    )


demo_col, behind_the_scenes_col = st.columns(spec=[1, 1], gap="large")

with behind_the_scenes_col:
    execution_status_container = st.empty()

    if "story_writer_execution_arn" in st.session_state:
        status_markdown = stepfn.describe_execution(
            st.session_state.story_writer_execution_arn
        )
        display_state_machine_status(status_markdown)
    else:
        display_no_state_machine_status()

    st.subheader("🔍 Step Functions state machine")
    st.image(image="/app/pages/workflow_images/story_writer.png")

with demo_col:
    st.subheader("🚀 Demo")

    with st.form("start_story_writer_demo_form"):
        st.info("Press Start to generate a story about your provided description.")
        story_description_text = st.text_input(
            "Enter a short description or genre for your story:", "The wild west"
        )
        started = st.form_submit_button("Start")
        if started:
            with st.spinner("Wait for it..."):
                if "story_writer_execution_arn" in st.session_state:
                    del st.session_state["story_writer_execution_arn"]
                display_no_state_machine_status()
                response = execute_state_machine(story_description_text)

                st.session_state.story_writer_execution_status = response["status"]
                if response["status"] == "SUCCEEDED":
                    output = json.loads(response["output"])
                    st.session_state.story = output["story"]

            if st.session_state.story_writer_execution_status == "SUCCEEDED":
                st.success("Done!")
                st.write(st.session_state.story)
            else:
                st.error("Your story could not be created. Please try again.")
