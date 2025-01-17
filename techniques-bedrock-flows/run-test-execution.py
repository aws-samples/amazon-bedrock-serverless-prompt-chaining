import boto3
import json
import sys

client_runtime = boto3.client("bedrock-agent-runtime")
client_control_plane = boto3.client("bedrock-agent")
flows_paginator = client_control_plane.get_paginator("list_flows")
flow_aliases_paginator = client_control_plane.get_paginator("list_flow_aliases")


def main():
    demo_name = sys.argv[1]

    # Find the flow ID for the demo flow
    flow_name = f"Flows-{demo_name}"
    flow_id = None
    for page in flows_paginator.paginate():
        for flow in page["flowSummaries"]:
            if flow["name"] == flow_name:
                flow_id = flow["id"]
                break
        if flow_id:
            break
    if not flow_id:
        raise Exception(f"Could not find flow {flow_name}")

    # Find the flow alias ID for the alias named "live"
    flow_alias_id = None
    for page in flow_aliases_paginator.paginate(flowIdentifier=flow_id):
        for flow_alias in page["flowAliasSummaries"]:
            if flow_alias["name"] == "live":
                flow_alias_id = flow_alias["id"]
                break
        if flow_alias_id:
            break
    if not flow_alias_id:
        raise Exception(
            f"Could not find flow alias {flow_alias_id} for flow {flow_name}"
        )

    # Load the input data
    with open(f"test-inputs/{demo_name}.json", "r") as file:
        input_data = json.load(file)

    print(f"Invoking flow {flow_id} ({flow_name}) with alias {flow_alias_id} (live)")

    response = client_runtime.invoke_flow(
        flowIdentifier=flow_id,
        flowAliasIdentifier=flow_alias_id,
        inputs=[
            {
                "content": input_data,
                "nodeName": "Input",
                "nodeOutputName": "document",
            }
        ],
    )

    result = {}

    for event in response.get("responseStream"):
        result.update(event)

    if result["flowCompletionEvent"]["completionReason"] == "SUCCESS":
        print("Flow invocation was successful! The output of the flow is as follows:\n")
        print(result["flowOutputEvent"]["content"]["document"])

    else:
        raise Exception(
            "The flow invocation completed unsuccessfully because of the following reason:",
            result["flowCompletionEvent"]["completionReason"],
        )


if __name__ == "__main__":
    main()
