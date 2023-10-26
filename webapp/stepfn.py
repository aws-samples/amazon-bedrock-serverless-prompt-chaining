import boto3
import json
import time
import uuid


sfn_client = boto3.client("stepfunctions")
sts_client = boto3.client("sts")
default_region = boto3.session.Session().region_name


# Methods for displaying the state machine's execution history
def find_task_id(event, events_by_id):
    # The "Task" is the event where we first see the "Entered" state and which has a name
    if event["type"] == "WaitStateEntered":
        return {
            "task_id": event["id"],
            "task_name": "Wait a few seconds to avoid Bedrock throttling",
        }
    elif (
        "stateEnteredEventDetails" in event
        and "name" in event["stateEnteredEventDetails"]
    ):
        return {
            "task_id": event["id"],
            "task_name": event["stateEnteredEventDetails"]["name"],
        }
    else:
        # Go back through the event history until we find the original TaskStateEntered/WaitStateEntered event for this task
        previous_event_id = event["previousEventId"]
        if previous_event_id not in events_by_id:
            raise Exception(
                f"Could not find previous event {previous_event_id} for event {event['id']}"
            )
        return find_task_id(events_by_id[previous_event_id], events_by_id)


known_event_types = [
    "TaskStateEntered",
    "TaskScheduled",
    "TaskStarted",
    "TaskStartFailed",
    "TaskFailed",
    "TaskTimedOut",
    "TaskSucceeded",
    "WaitStateEntered",
    "WaitStateExited",
]


def get_task_status(event_type):
    if (
        event_type == "TaskStateEntered"
        or event_type == "TaskScheduled"
        or event_type == "TaskStarted"
        or event_type == "WaitStateEntered"
    ):
        return ":arrows_counterclockwise:"
    elif (
        event_type == "TaskStartFailed"
        or event_type == "TaskFailed"
        or event_type == "TaskTimedOut"
    ):
        return ":bangbang:"
    elif event_type == "TaskSucceeded" or event_type == "WaitStateExited":
        return ":white_check_mark:"
    raise Exception(f"Unknown event type {event_type}")


def get_workflow_status_icon(status):
    if status == "RUNNING":
        return ":arrows_counterclockwise:"
    elif status == "FAILED" or status == "TIMED_OUT" or status == "ABORTED":
        return ":bangbang:"
    elif status == "SUCCEEDED":
        return ":white_check_mark:"
    raise Exception(f"Unknown event type {status}")


def get_workflow_status_markdown(execution, execution_events):
    markdown = f"##### Status: {get_workflow_status_icon(execution['status'])} {execution['status'].title()}"
    markdown += f"\n\n##### Tasks"

    # Keep a dictionary of events: event ID -> event details
    events_by_id = {}
    for event in execution_events:
        events_by_id[event["id"]] = event

    # Keep a dictionary of tasks: task ID -> state (running, failed, succeeded) and name
    task_status = {}

    # Determine the state of each unique task and its unique task name
    for event in execution_events:
        if event["type"] not in known_event_types:
            continue
        task = find_task_id(event, events_by_id)
        status = get_task_status(event["type"])
        task_status[task["task_id"]] = {
            "task_id": task["task_id"],
            "task_name": task["task_name"],
            "task_status": status,
        }

    # Display the task status
    task_ids = list(task_status.keys())
    task_ids.sort()
    for task_id in task_ids:
        task = task_status[task_id]
        markdown += f"\n\n{task['task_status']} {task['task_name'].replace(' (Invoke Model)', '')}"

    return markdown


# Construct the state machine ARN by querying the region and account ID
def get_state_machine_arn(name, region=default_region, sts_client=sts_client):
    return f"arn:aws:states:{region}:{sts_client.get_caller_identity()['Account']}:stateMachine:{name}"


# Construct a unique execution name from the Streamlit session ID
def get_execution_name(session_id):
    return f"streamlit-{session_id}-{str(uuid.uuid4())[-12:]}"


def get_execution_arn(
    state_machine_name, execution_name, region=default_region, sts_client=sts_client
):
    return f"arn:aws:states:{region}:{sts_client.get_caller_identity()['Account']}:execution:{state_machine_name}:{execution_name}"


def start_execution(
    state_machine_name,
    session_id,
    input,
    client=sfn_client,
    region=default_region,
    sts_client=sts_client,
):
    response = client.start_execution(
        stateMachineArn=get_state_machine_arn(state_machine_name, region, sts_client),
        name=get_execution_name(session_id),
        input=input,
    )
    return response["executionArn"]


def continue_execution(task_token, task_output, client=sfn_client):
    client.send_task_success(
        taskToken=task_token,
        output=json.dumps(task_output),
    )


def describe_execution(execution_arn, client=sfn_client):
    execution = client.describe_execution(executionArn=execution_arn)
    execution_events = []
    paginator = client.get_paginator("get_execution_history")
    for page in paginator.paginate(
        executionArn=execution_arn, includeExecutionData=False
    ):
        execution_events += page["events"]
    return get_workflow_status_markdown(execution, execution_events)


def poll_for_execution_completion(execution_arn, callback_fn=None, client=sfn_client):
    while True:
        execution = client.describe_execution(executionArn=execution_arn)

        if callback_fn:
            execution_events = []
            paginator = client.get_paginator("get_execution_history")
            for page in paginator.paginate(
                executionArn=execution_arn, includeExecutionData=False
            ):
                execution_events += page["events"]
            callback_fn(get_workflow_status_markdown(execution, execution_events))

        if execution["status"] and execution["status"] != "RUNNING":
            return execution
        time.sleep(1)


def poll_for_execution_task_token_or_completion(
    execution_arn, callback_fn=None, client=sfn_client
):
    while True:
        # Check if execution is still running
        # When the execution is waiting on a task token, its status is still RUNNING.
        response = client.describe_execution(executionArn=execution_arn)

        if callback_fn:
            execution_events = []
            paginator = client.get_paginator("get_execution_history")
            for page in paginator.paginate(
                executionArn=execution_arn, includeExecutionData=False
            ):
                execution_events += page["events"]
            callback_fn(get_workflow_status_markdown(response, execution_events))

        if response["status"] and response["status"] != "RUNNING":
            return response

        # Check if execution is waiting on a task token
        response = client.get_execution_history(
            executionArn=execution_arn,
            reverseOrder=True,
            maxResults=1,
            includeExecutionData=True,
        )

        most_recent_event = response["events"][0]
        if (
            most_recent_event["type"] == "TaskSubmitted"
            and most_recent_event["taskSubmittedEventDetails"]["resource"]
            == "invoke.waitForTaskToken"
        ):
            output = json.loads(
                most_recent_event["taskSubmittedEventDetails"]["output"]
            )
            return {
                "status": "PAUSED",
                "task_payload": output["Payload"],
            }

        time.sleep(1)


def is_execution_completed(execution_arn, client=sfn_client):
    response = client.describe_execution(executionArn=execution_arn)
    return response["status"] and response["status"] != "RUNNING"
