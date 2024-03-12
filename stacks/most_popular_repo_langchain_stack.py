from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

from .util import get_bedrock_iam_policy_statement, get_lambda_bundling_options


class MostPopularRepoLangchainStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: look up the highest trending repo on GitHub
        lookup_repo_lambda = lambda_python.PythonFunction(
            self,
            "LookupRepoAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions/most_popular_repo_langchain",
            handler="lookup_trending_repo_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=512,
        )
        lookup_repo_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        lookup_repo_job = tasks.LambdaInvoke(
            self,
            "Lookup Repo",
            lambda_function=lookup_repo_lambda,
            output_path="$.Payload",
        )

        # Agent #2: summarize the repo
        summarize_repo_lambda = lambda_python.PythonFunction(
            self,
            "SummarizeRepoAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions/most_popular_repo_langchain",
            handler="summarize_repo_readme_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=512,
        )
        summarize_repo_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        summarize_repo_job = tasks.LambdaInvoke(
            self,
            "Summarize Repo",
            lambda_function=summarize_repo_lambda,
            output_path="$.Payload",
        )

        # Hook the agents together into a sequential pipeline
        chain = lookup_repo_job.next(summarize_repo_job)

        sfn.StateMachine(
            self,
            "MostPopularRepoWorkflow",
            state_machine_name="PromptChainDemo-MostPopularRepoLangchain",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
