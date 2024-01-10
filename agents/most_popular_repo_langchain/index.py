import re
import boto3
from botocore.config import Config
from bs4 import BeautifulSoup
from github import Github, UnknownObjectException

from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain.llms import Bedrock
from langchain.tools import Tool
from langchain.utilities.requests import TextRequestsWrapper

bedrock_client = boto3.client(
    "bedrock-runtime", config=Config(retries={"max_attempts": 6, "mode": "standard"})
)


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
    repo_name = input.replace("https://github.com/", "")
    try:
        readme_content = (
            Github().get_repo(repo_name).get_readme().decoded_content.decode("utf-8")
        )
        if len(readme_content) > 10000:
            response = f"Here are the first 10,000 characters of the README for {input}, inside <readme></readme> XML tags."
            response += "\n<readme>"
            response += "\n" + readme_content[:10000]
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
    llm = Bedrock(
        model_id="anthropic.claude-v2",
        model_kwargs={
            "temperature": 0,
            "max_tokens_to_sample": 256,
        },
        client=bedrock_client,
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
    llm = Bedrock(
        model_id="anthropic.claude-v2",
        model_kwargs={
            "temperature": 0,
            "max_tokens_to_sample": 500,
        },
        client=bedrock_client,
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
