import json


# This function receives the question that the agent workflow needs the user to answer,
# and the Step Functions task token that can be used to continue the agent workflow.
# While the agent workflow is waiting for the user to answer the question, the Step Functions
# execution will be paused.
#
# Typically this function would send the user question and the task token to some sort of
# backend API that handles conversation state. The UI would pull the conversation state
# from the backend API and present the question to the user. When the user answers, the UI
# would send the answer to the backend, and the backend would use the user answer and the
# task token to continue the agent workflow. The backend would also send task heartbeats
# to the Step Functions execution while the user session was active.
#
# For the purposes of this demo, this function is a no-op. The Streamlit server polls the
# Step Functions execution directly to get the question and task token, presents the user
# question in the UI, and then sends the user's answer and the task token to the Step Functions
# execution.
def handler(event, context):
    print(json.dumps(event, indent=2))

    return event
