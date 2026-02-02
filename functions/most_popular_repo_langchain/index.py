import re
import boto3
from botocore.config import Config
import os
from bs4 import BeautifulSoup
from github import Auth, Github, UnknownObjectException
import json

from langchain.agents.initialize import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_community.chat_models.bedrock import BedrockChat
from langchain_community.utilities.requests import TextRequestsWrapper
from langchain_core.tools import Tool

bedrock_client_config = Config(retries={"max_attempts": 6, "mode": "standard"})
secrets_client = boto3.client("secretsmanager")
github_token_secret_name = os.environ.get("GITHUB_TOKEN_SECRET")


### Tools ###
def get_github_trending_page(input):
    requests_wrapper = TextRequestsWrapper(headers={"User-Agent": "Mozilla/5.0"})
    html = requests_wrapper.get("https://github.com/trending")
    soup = BeautifulSoup(html, "html.parser")
    response = [
        "Here is the contents of the GitHub Trending Repositories page, inside <trending></trending> XML tags. The repositories on the page are ordered by popularity (the highest trending repository is first).",
        "<trending>",
    ]
    response += [
        re.sub(
            r"\n\s*\n",  # De-dupe newlines
            "\n",
            e.get_text(),
        )
        for e in soup.find_all("article", {"class": "Box-row"})
    ]
    response += ["</trending>"]
    return "\n".join(response)


def get_github_repo_readme(input):
    github_token_secret_value = secrets_client.get_secret_value(
        SecretId=github_token_secret_name
    )
    github_token = json.loads(github_token_secret_value["SecretString"])["token"]
    github_client = Github(auth=Auth.Token(github_token))

    repo_name = input.replace("https://github.com/", "")
    try:
        readme_content = (
            github_client.get_repo(repo_name)
            .get_readme()
            .decoded_content.decode("utf-8")
        )
        if len(readme_content) > 5000:
            response = f"Here are the first 5,000 characters of the README for {input}, inside <readme></readme> XML tags."
            response += "\n<readme>"
            response += "\n" + readme_content[:5000]
        else:
            response = (
                f"Here is the README for {input}, inside <readme></readme> XML tags."
            )
            response += "\n<readme>"
            response += "\n" + readme_content
        response += "\n</readme>"
        return response
    except UnknownObjectException:
        return f"Could not find a README for the repository {input}. It may not exist in the repository."


def get_github_langchain_tools():
    return [
        Tool(
            name="get_trending_github_repositories",
            func=get_github_trending_page,
            description="Retrieves the GitHub Trending Repositories webpage. Use this when you need to get information about which repositories are currently trending on GitHub. Provide an empty string as the input. The output will be the text response of a GET request to the Trending Repositories page.",
        ),
        Tool(
            name="get_github_repository_readme",
            func=get_github_repo_readme,
            description="Retrieves the content of a GitHub repository's README file. Use this when you need to get information about a specific GitHub repository. Provide the URL of the GitHub repository as the input. The output will be the contents of the readme.",
        ),
    ]


### Agents ###
def lookup_trending_repo_agent(event, context):
    llm = BedrockChat(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_kwargs={
            "temperature": 0,
            "max_tokens": 256,
        },
        config=bedrock_client_config,
    )
    example_github_url = "https://github.com/orgname/reponame"
    repo_url = None

    previous_answers = []
    for i in range(3):
        agent = initialize_agent(
            get_github_langchain_tools(),
            llm,
            agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

        question = f"What is the top trending repository on GitHub today? Provide only the URL (for example, {example_github_url})."
        parsing_error = f'Check your output and make sure it conforms to my instructions! Ensure that you prefix your final answer with "Final Answer: ". Also ensure that you answer the original question: {question}'
        agent.handle_parsing_errors = parsing_error

        if len(previous_answers) > 0:
            question += f"\nYour previous answers to this question are below, inside <previous_answer></previous_answer> XML tags. I was not able to extract a GitHub repository URL for your responses."
            question += f"\n{parsing_error}"
            for previous_answer in previous_answers:
                question += (
                    f"\n<previous_answer>\n{previous_answer}\n</previous_answer>"
                )

        response = agent.run(question).strip()

        # Find a valid repo URL in the response
        repo_match = re.search(r"https:\/\/github\.com(?:\/[^\s\/]+){2}", response)
        if repo_match:
            url = repo_match.group(0)
            if example_github_url not in url:
                repo_url = url
                break
        print(f"Could not extract URL from response {response}")
        previous_answers.append(response)

    if repo_url is None:
        raise Exception("Could not find URL from Langchain agent responses")

    return {
        "repo": repo_url,
    }


def summarize_repo_readme_agent(event, context):
    llm = BedrockChat(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_kwargs={
            "temperature": 0,
            "max_tokens": 500,
        },
        config=bedrock_client_config,
    )

    agent = initialize_agent(
        get_github_langchain_tools(),
        llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
    )
    question = f"Briefly describe the popular open source project {event['repo']} in 100 - 200 words."
    agent.handle_parsing_errors = f'Check your output and make sure it conforms to my instructions! Ensure that you prefix your final answer with "Final Answer: ". Also ensure that you answer the original question: {question}'
    summary = agent.run(question)

    return {
        "repo": event["repo"],
        "summary": summary.strip(),
    }
