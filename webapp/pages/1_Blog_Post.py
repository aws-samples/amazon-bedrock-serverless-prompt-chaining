import streamlit as st
import uuid
import json

import stepfn

st.set_page_config(layout="wide")

st.title("Blog post")

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


def execute_state_machine(novel):
    input = {"novel": novel}
    execution_arn = stepfn.start_execution(
        "PromptChainDemo-BlogPost",
        st.session_state.user_id,
        json.dumps(input),
    )
    st.session_state.blog_post_execution_arn = execution_arn
    return stepfn.poll_for_execution_completion(
        execution_arn, display_state_machine_status
    )


demo_col, behind_the_scenes_col = st.columns(spec=[1, 1], gap="large")

with behind_the_scenes_col:
    execution_status_container = st.empty()

    if "blog_post_execution_arn" in st.session_state:
        status_markdown = stepfn.describe_execution(
            st.session_state.blog_post_execution_arn
        )
        display_state_machine_status(status_markdown)
    else:
        display_no_state_machine_status()

    st.subheader("🔍 Behind the scenes")
    st.write(
        "This demo illustrates chaining multiple prompts together in a simple, sequential pipeline \
        to generate a blog post for a literature blog. \
        The previous prompts and LLM responses are carried forward and included in the next prompt."
    )
    st.image(image="/app/pages/workflow_images/blog_post.png")


with demo_col:
    st.subheader("🚀 Demo")
    with st.form("start_blog_post_demo_form"):
        st.info(
            "Press Start to generate a blog post about your provided novel, which will analyze the novel for your literature blog."
        )
        novel_text = st.text_input(
            "Enter a novel:", "Pride and Prejudice by Jane Austen"
        )
        started = st.form_submit_button("Start")
        if started:
            with st.spinner("Wait for it..."):
                if "blog_post_execution_arn" in st.session_state:
                    del st.session_state["blog_post_execution_arn"]
                display_no_state_machine_status()
                response = execute_state_machine(novel_text)

                st.session_state.blog_post_execution_status = response["status"]
                if response["status"] == "SUCCEEDED":
                    output = json.loads(response["output"])
                    st.session_state.blog_post_content = output

            if st.session_state.blog_post_execution_status == "SUCCEEDED":
                st.success("Done!")
                st.write(st.session_state.blog_post_content)
            else:
                st.error("The blog post could not be written. Please try again.")
