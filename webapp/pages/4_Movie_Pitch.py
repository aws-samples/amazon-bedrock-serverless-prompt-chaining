import streamlit as st
import uuid
import json
import time

import stepfn

st.set_page_config(layout="wide")

st.title("Movie pitch demo")

execution_status_container = None

# Populate a unique user ID to use for naming the Step Functions execution
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "previous_movie_pitches" not in st.session_state:
    st.session_state.previous_movie_pitches = []


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


def execute_state_machine(movie_description):
    input = {"movie_description": movie_description}
    execution_arn = stepfn.start_execution(
        "PromptChainDemo-MoviePitch",
        st.session_state.user_id,
        json.dumps(input),
    )
    st.session_state.movie_pitch_execution_arn = execution_arn
    return stepfn.poll_for_execution_task_token_or_completion(
        execution_arn, display_state_machine_status
    )


def continue_state_machine(task_result):
    stepfn.continue_execution(
        st.session_state.movie_pitch_task_token, {"Payload": task_result}
    )
    time.sleep(2)
    return stepfn.poll_for_execution_task_token_or_completion(
        st.session_state.movie_pitch_execution_arn, display_state_machine_status
    )


def handle_stepfn_response(response):
    if response["status"] == "SUCCEEDED":
        output = json.loads(response["output"])
        st.session_state.movie_pitch_one_pager = output["movie_pitch_one_pager"]
    elif response["status"] == "PAUSED":
        task_payload = response["task_payload"]
        st.session_state.movie_pitch_task_pitch = task_payload["input"]["movie_pitch"]
        st.session_state.movie_pitch_task_token = task_payload["token"]
    st.session_state.movie_pitch_execution_status = response["status"]


demo_col, behind_the_scenes_col = st.columns(spec=[1, 1], gap="large")

with behind_the_scenes_col:
    execution_status_container = st.empty()

    if "movie_pitch_execution_arn" in st.session_state:
        status_markdown = stepfn.describe_execution(
            st.session_state.movie_pitch_execution_arn
        )
        display_state_machine_status(status_markdown)
    else:
        display_no_state_machine_status()

    st.subheader("🔍 Behind the scenes")
    st.write(
        "This demo illustrates using varying temperature settings to generate multiple possible answers and choosing one. \
        The user acts as a 'movie producer' seeking movie pitches from screenwriters and gives some input on what the movie should be about. \
        A movie pitch generator agent runs three times in parallel using three different temperature settings to generate three movie pitches. \
        The next agent chooses which movie pitch among the three generated options should be presented to the 'movie producer' user."
    )
    st.write(
        "This demo also illustrates adding human user input into a workflow. \
        The workflow has a defined state at which a user decision is needed: \
        the 'movie producer' user needs to decide whether to 'greenlight' the presented movie pitch or reject it. \
        The workflow pauses while the demo UI asks the user for their decision. \
        When the UI provides the user's decision to the workflow, the workflow continues. \
        Depending on the user's decision, the workflow either moves forward to generate a longer movie pitch for the greenlit idea, \
        or loops back around to the beginning of the workflow to generate three new movie pitches."
    )
    st.image(image="/app/pages/workflow_images/movie_pitch.png")

with demo_col:
    st.subheader("🚀 Demo")

    # First, ask for the description or genre of the movie and start generating the movie pitch
    if "movie_pitch_description" not in st.session_state:
        with st.form("start_movie_pitch_demo_form"):
            st.info(
                "Press Start to generate a movie pitch from your provided description."
            )
            movie_description_text = st.text_input(
                "Enter a short description or genre for your movie:", "Cowboys in space"
            )
            started = st.form_submit_button("Start")
            if started:
                with st.spinner("Wait for it..."):
                    if "movie_pitch_execution_arn" in st.session_state:
                        del st.session_state["movie_pitch_execution_arn"]
                    display_no_state_machine_status()

                    st.session_state.movie_pitch_description = movie_description_text
                    response = execute_state_machine(movie_description_text)
                    handle_stepfn_response(response)
                    st.experimental_rerun()
    else:
        with st.expander("Movie description", expanded=True):
            st.info("You previously provided the following movie description:")
            st.write(st.session_state.movie_pitch_description)

    # Show the previous movie pitches that the user has already greenlit or not
    for i, previous_pitch in enumerate(st.session_state.previous_movie_pitches):
        with st.expander("Movie pitch #" + str(i + 1), expanded=True):
            st.info("The screenwriter previously pitched the following movie to you:")
            st.write(previous_pitch["movie_pitch"])
            if previous_pitch["user_choice"] == "yes":
                st.success("You chose to greenlight this movie!")
            else:
                st.warning(
                    "You chose not to greenlight this movie and to get a new pitch."
                )

    if "movie_pitch_execution_status" in st.session_state:
        # If there is a pending movie pitch, ask the user whether they want to greenlight the movie or not
        if st.session_state.movie_pitch_execution_status == "PAUSED":
            with st.form("decide_on_pitch_form"):
                st.info(
                    "You are a movie producer, and a screenwriter has come to you with the following short pitch."
                )
                st.write(st.session_state.movie_pitch_task_pitch)
                st.info(
                    "Do you want to greenlight this movie? If so, a longer one-pager movie pitch will be generated. If not, a new short pitch will be generated."
                )
                yes = st.form_submit_button("Yes, greenlight the movie!")
                no = st.form_submit_button("No, try again.")
                if yes or no:
                    with st.spinner("Wait for it..."):
                        result = {
                            "movie_description": st.session_state.movie_pitch_description,
                            "movie_pitch": st.session_state.movie_pitch_task_pitch,
                            "user_choice": "yes" if yes else "no",
                        }
                        response = continue_state_machine(result)
                        st.session_state.previous_movie_pitches.append(result)
                        handle_stepfn_response(response)
                        st.experimental_rerun()

        # If the workflow is complete, show the full movie pitch one-pager
        elif st.session_state.movie_pitch_execution_status == "SUCCEEDED":
            if "movie_pitch_one_pager" in st.session_state:
                with st.expander("Movie pitch one-pager", expanded=True):
                    st.success("Done! I look forward to seeing this movie get made!")
                    st.write(st.session_state.movie_pitch_one_pager)

        # Workflow failed
        else:
            st.error("Your movie pitch could not be created. Please try again.")
