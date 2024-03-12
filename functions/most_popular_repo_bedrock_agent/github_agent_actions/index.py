import re
import requests
from bs4 import BeautifulSoup
from github import Github, UnknownObjectException
import json


# Return the contents of the GitHub trending repositories page
def get_github_trending_page_agent_action():
    get_response = requests.get(
        "https://github.com/trending", headers={"User-Agent": "Mozilla/5.0"}
    )

    if get_response.status_code != 200:
        print(get_response)
        raise Exception("Could not retrieve GitHub Trending page")

    soup = BeautifulSoup(get_response.text, "html.parser")
    response = [
        "Here are the contents of the GitHub Trending Repositories page. The repositories on the page are ordered by popularity (the highest trending repository is first).",
    ]
    response += [
        re.sub(
            r"\n\s*\n",  # De-dupe newlines
            "\n",
            e.get_text(),
        )
        for e in soup.find_all("article", {"class": "Box-row"})
    ]
    return "\n".join(response)


# Return the contents of a repository's README file
def get_github_repository_readme_agent_action(input):
    repo_name = input.replace("https://github.com/", "")
    try:
        readme_content = (
            Github().get_repo(repo_name).get_readme().decoded_content.decode("utf-8")
        )
        if len(readme_content) > 10000:
            response = (
                f"Here are the first 10,000 characters of the README for {input}."
            )
            response += "\n" + readme_content[:10000]
        else:
            response = f"Here are the full contents of the README for {input}."
            response += "\n" + readme_content
        return response
    except UnknownObjectException:
        return f"Could not find a README for the repository {input}. It may not exist in the repository."


def handler(event, context):
    print(event)

    response_code = 200
    response_body = {}
    action = event["actionGroup"]
    api_path = event["apiPath"]

    try:
        if api_path == "/get_trending_github_repositories":
            body = get_github_trending_page_agent_action()
            response_body = {"contents": str(body)}
        elif api_path == "/get_github_repository_readme":
            params = event["parameters"]
            if not params:
                response_code = 400
                response_body = {"error": "Missing parameter: repo"}
            else:
                repo_params = [p for p in params if p["name"] == "repo"]
                if not repo_params:
                    response_code = 400
                    response_body = {"error": "Missing parameter: repo"}
                else:
                    repo_url = repo_params[0]["value"]
                    body = get_github_repository_readme_agent_action(repo_url)
                    response_body = {"contents": str(body)}
        else:
            response_code = 400
            response_body = {
                "error": f"{action}::{api_path} is not a valid API, try another one."
            }
    except Exception as e:
        response_code = 500
        response_body = {"error": str(e)}

    action_response = {
        "actionGroup": event["actionGroup"],
        "apiPath": event["apiPath"],
        "httpMethod": event["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": {"application/json": {"body": json.dumps(response_body)}},
    }

    api_response = {"messageVersion": "1.0", "response": action_response}
    print(api_response)

    return api_response
