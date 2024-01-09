import boto3
import os
import re
import uuid

bedrock_agent_client = boto3.client("bedrock-agent-runtime")

agent_id = os.environ.get("BEDROCK_AGENT_ID")
agent_alias_id = os.environ.get("BEDROCK_AGENT_ALIAS_ID")


def lookup_trending_repo_agent(event, context):
    session_id = str(uuid.uuid4())
    example_github_repo = "orgname/reponame"
    example_github_url = f"https://github.com/{example_github_repo}"
    repo_url = None

    for i in range(3):
        input_text = f"What is the top trending repository on GitHub today? Provide only the URL of the top GitHub repository as your answer. For example, if '{example_github_repo}' was the top trending repository, then '{example_github_url}' would be your answer."
        if i > 0:
            input_text = f"What is the URL of the top trending repository? For example, if '{example_github_repo}' was the top trending repository, then '{example_github_url}' would be your answer."

        response = bedrock_agent_client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            endSession=False,
            inputText=input_text,
        )

        print(f"Session ID: {session_id}")
        print(f"Request ID: {response['ResponseMetadata']['RequestId']}")

        chunks = []
        for event in response["completion"]:
            chunks.append(event["chunk"]["bytes"].decode("utf-8"))
        completion = " ".join(chunks)

        print(f"Completion: {completion}")

        # Find a URL in the response
        repo_match = re.search(r"https:\/\/github\.com(?:\/[^\s\/]+){2}", completion)
        if repo_match:
            url = repo_match.group(0)
            if example_github_url not in url:
                repo_url = url
                break
        print(f"Could not extract URL from response {completion}")

    if repo_url is None:
        raise Exception("Could not find URL from Bedrock Agent responses")

    return {
        "repo": repo_url,
    }


def summarize_repo_readme_agent(event, context):
    session_id = str(uuid.uuid4())

    response = bedrock_agent_client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        endSession=False,
        inputText=f"Please give me a brief description of the popular GitHub repository {event['repo']}, in 50 - 100 words.",
    )

    print(f"Session ID: {session_id}")
    print(f"Request ID: {response['ResponseMetadata']['RequestId']}")
    print(f"Repo: {event['repo']}")

    chunks = []
    for response_event in response["completion"]:
        chunks.append(response_event["chunk"]["bytes"].decode("utf-8"))
    completion = " ".join(chunks)

    print(f"Completion: {completion}")

    return {
        "repo": event["repo"],
        "summary": completion.strip(),
    }
