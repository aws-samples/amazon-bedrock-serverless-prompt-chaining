from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_s3 as s3,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class MostPopularRepoBedrockAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ### Setup for Bedrock Agent ###
        bedrock_agent_access_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeAgent",
            ],
            resources=[
                "*",
            ],
        )

        bedrock_agent_service_role = iam.Role(
            self,
            "BedrockAgentServiceRole",
            role_name="AmazonBedrockExecutionRoleForAgents_BedrockServerlessPromptChain",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        bedrock_agent_service_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                ],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-v2",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-v2:1",
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-instant-v1",
                ],
            )
        )

        bedrock_agent_api_schemas_bucket = s3.Bucket(
            self,
            "ApiSchemasBucket",
            bucket_name=f"serverless-prompt-chaining-{self.account}-{self.region}-agent-schemas",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )
        bedrock_agent_api_schemas_bucket.grant_read(bedrock_agent_service_role)

        github_agent_actions_lambda = lambda_python.PythonFunction(
            self,
            "GitHubAgentActions",
            function_name="PromptChainDemo-MostPopularRepoBedrockAgents-GitHubActions",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/most_popular_repo_bedrock_agent/github_agent_actions",
            timeout=Duration.seconds(60),
            memory_size=512,
        )
        bedrock_principal = iam.ServicePrincipal(
            "bedrock.amazonaws.com",
            conditions={
                "StringEquals": {"aws:SourceAccount": self.account},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock:{self.region}:{self.account}:agent/*"
                },
            },
        )
        github_agent_actions_lambda.grant_invoke(bedrock_principal)

        ### Agents and Workflow ###

        # Agent #1: look up the highest trending repo on GitHub
        lookup_repo_lambda = lambda_python.PythonFunction(
            self,
            "LookupRepoAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/most_popular_repo_bedrock_agent/agent",
            handler="lookup_trending_repo_agent",
            bundling=lambda_python.BundlingOptions(
                asset_excludes=[".venv", ".mypy_cache", "__pycache__"],
            ),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "BEDROCK_AGENT_ID": "INSERT BEDROCK AGENT ID HERE",
                "BEDROCK_AGENT_ALIAS_ID": "INSERT BEDROCK AGENT ALIAS ID HERE",
            },
        )
        lookup_repo_lambda.add_to_role_policy(bedrock_agent_access_policy)

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
            entry="agents/most_popular_repo_bedrock_agent/agent",
            handler="summarize_repo_readme_agent",
            bundling=lambda_python.BundlingOptions(
                asset_excludes=[".venv", ".mypy_cache", "__pycache__"],
            ),
            timeout=Duration.seconds(60),
            memory_size=512,
            environment={
                "BEDROCK_AGENT_ID": "INSERT BEDROCK AGENT ID HERE",
                "BEDROCK_AGENT_ALIAS_ID": "INSERT BEDROCK AGENT ALIAS ID HERE",
            },
        )
        summarize_repo_lambda.add_to_role_policy(bedrock_agent_access_policy)

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
            state_machine_name="PromptChainDemo-MostPopularRepoBedrockAgents",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
