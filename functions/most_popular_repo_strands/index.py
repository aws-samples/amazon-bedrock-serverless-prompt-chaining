import re
import boto3
from botocore.config import Config
import os
from bs4 import BeautifulSoup
from github import Auth, Github, UnknownObjectException
import json
import requests

from strands import Agent, tool
from strands.models import BedrockModel

bedrock_client_config = Config(retries={"max_attempts": 6, "mode": "standard"})
secrets_client = boto3.client("secretsmanager")
github_token_secret_name = os.environ.get("GITHUB_TOKEN_SECRET")


### Tools ###
@tool
def get_trending_github_repositories(input: str) -> str:
    """Retrieves the GitHub Trending Repositories webpage.
    
    Use this when you need to get information about which repositories are 
    currently trending on GitHub. Provide an empty string as the input. 
    The output will be the text response of a GET request to the Trending 
    Repositories page.
    
    Args:
        input: Empty string (not used)
    """
    response = requests.get(
        "https://github.com/trending",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    soup = BeautifulSoup(response.text, "html.parser")
    response_text = [
        "Here is the contents of the GitHub Trending Repositories page, inside <trending></trending> XML tags. The repositories on the page are ordered by popularity (the highest trending repository is first).",
        "<trending>",
    ]
    response_text += [
        re.sub(
            r"\n\s*\n",  # De-dupe newlines
            "\n",
            e.get_text(),
        )
        for e in soup.find_all("article", {"class": "Box-row"})
    ]
    response_text += ["</trending>"]
    return "\n".join(response_text)


@tool
def get_github_repository_readme(input: str) -> str:
    """Retrieves the content of a GitHub repository's README file.
    
    Use this when you need to get information about a specific GitHub repository. 
    Provide the URL of the GitHub repository as the input. The output will be 
    the contents of the readme.
    
    Args:
        input: The URL of the GitHub repository
    """
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


### Agents ###
def lookup_trending_repo_agent(event, context):
    from pydantic import BaseModel, Field, field_validator
    
    class GitHubRepo(BaseModel):
        """GitHub repository URL"""
        url: str = Field(description="The full GitHub repository URL (e.g., https://github.com/owner/repo)")
        
        @field_validator("url")
        @classmethod
        def validate_github_url(cls, value: str) -> str:
            import re
            pattern = r"https:\/\/github\.com(?:\/[^\s\/]+){2}"
            if not re.match(pattern, value):
                raise ValueError(f"Invalid GitHub URL format: {value}. Must be https://github.com/owner/repo")
            if "github.com/orgname/reponame" in value:
                raise ValueError("Please provide a real repository URL, not the example URL")
            return value
    
    llm = BedrockModel(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0,
        max_tokens=256,
        boto_client_config=bedrock_client_config,
        streaming=False,
    )
    
    agent = Agent(
        model=llm,
        tools=[get_trending_github_repositories],
    )

    question = "What is the top trending repository on GitHub today? Provide only the URL."
    
    result = agent(question, structured_output_model=GitHubRepo)
    
    return {
        "repo": result.structured_output.url,
    }


def summarize_repo_readme_agent(event, context):
    llm = BedrockModel(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        temperature=0,
        max_tokens=500,
        boto_client_config=bedrock_client_config,
        streaming=False,
    )

    agent = Agent(
        model=llm,
        tools=[get_github_repository_readme],
    )
    
    question = f"Briefly describe the popular open source project {event['repo']} in 100 - 200 words."
    response = agent(question)
    
    return {
        "repo": event["repo"],
        "summary": str(response).strip(),
    }
