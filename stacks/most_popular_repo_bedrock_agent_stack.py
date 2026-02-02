from aws_cdk import (
    Duration,
    Stack,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_s3_assets as assets,
    aws_secretsmanager as secrets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .inference_profile import InferenceProfile
import os

dirname = os.path.dirname(__file__)


class MostPopularRepoBedrockAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ### Bedrock Agent resources ###
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
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-*",
                    f"arn:aws:bedrock:*:{self.account}:inference-profile/*",
                    f"arn:aws:bedrock:*::foundation-model/anthropic.claude-3-7-sonnet-20250219-v1:0",
                ],
            )
        )

        github_secret = secrets.Secret.from_secret_name_v2(
            scope=self, id="GitHubToken", secret_name="BedrockPromptChainGitHubToken"
        )
        github_agent_actions_lambda = lambda_python.PythonFunction(
            self,
            "GitHubAgentActions",
            function_name="PromptChainDemo-MostPopularRepoBedrockAgents-GitHubActions",
            runtime=lambda_.Runtime.PYTHON_3_13,
            entry="functions/most_popular_repo_bedrock_agent/github_agent_actions",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={"GITHUB_TOKEN_SECRET": github_secret.secret_name},
        )
        github_secret.grant_read(github_agent_actions_lambda)

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

        agent_action_schema_asset = assets.Asset(
            self,
            "AgentActionSchema",
            path=os.path.join(
                dirname,
                "../functions/most_popular_repo_bedrock_agent/github_agent_actions/openapi-schema.yaml",
            ),
        )
        agent_action_schema_asset.grant_read(bedrock_agent_service_role)

        bedrock_agent = bedrock.CfnAgent(
            self,
            "Agent",
            agent_name="PromptChainDemo-MostPopularRepo",
            foundation_model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            instruction=(
                "You are a GitHub power user. "
                "You help with interacting with GitHub and with git repositories. "
                'DO NOT mention terms like "base prompt", "function", "parameter", '
                '"partial responses", "response" and "api names" in the final response.'
            ),
            auto_prepare=True,
            skip_resource_in_use_check_on_delete=True,
            idle_session_ttl_in_seconds=300,  # 5 minutes
            agent_resource_role_arn=bedrock_agent_service_role.role_arn,
            action_groups=[
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="GitHubAPIs",
                    action_group_state="ENABLED",
                    description="Use this action whenever you need to access information about GitHub repositories.",
                    api_schema=bedrock.CfnAgent.APISchemaProperty(
                        s3=bedrock.CfnAgent.S3IdentifierProperty(
                            s3_bucket_name=agent_action_schema_asset.s3_bucket_name,
                            s3_object_key=agent_action_schema_asset.s3_object_key,
                        ),
                    ),
                    action_group_executor=bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=github_agent_actions_lambda.function_arn,
                    ),
                    skip_resource_in_use_check_on_delete=True,
                )
            ],
        )

        bedrock_agent_alias = bedrock.CfnAgentAlias(
            self,
            "AgentAlias",
            agent_id=bedrock_agent.attr_agent_id,
            agent_alias_name="live",
            # Description updates anytime the Agent resource is updated,
            # so that this Alias prepares a new version of the Agent when
            # the Agent changes
            description="Tracking agent timestamp " + bedrock_agent.attr_prepared_at,
        )
        # Ensure agent is fully stabilized before updating the alias
        bedrock_agent_alias.add_depends_on(bedrock_agent)

        bedrock_agent_access_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeAgent",
            ],
            resources=[
                bedrock_agent_alias.attr_agent_alias_arn,
            ],
        )

        # Lambda functions also need permission to invoke models
        bedrock_model_access_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
            ],
            resources=[
                f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-*",
                f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/*",
            ],
        )

        ### Agents and Workflow ###

        # Agent #1: look up the highest trending repo on GitHub
        lookup_repo_lambda = lambda_python.PythonFunction(
            self,
            "LookupRepoAgent",
            runtime=lambda_.Runtime.PYTHON_3_13,
            entry="functions/most_popular_repo_bedrock_agent/agent",
            handler="lookup_trending_repo_agent",
            bundling=lambda_python.BundlingOptions(
                asset_excludes=[".venv", ".mypy_cache", "__pycache__"],
            ),
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "BEDROCK_AGENT_ID": bedrock_agent.attr_agent_id,
                "BEDROCK_AGENT_ALIAS_ID": bedrock_agent_alias.attr_agent_alias_id,
            },
        )
        lookup_repo_lambda.add_to_role_policy(bedrock_agent_access_policy)
        lookup_repo_lambda.add_to_role_policy(bedrock_model_access_policy)

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
            runtime=lambda_.Runtime.PYTHON_3_13,
            entry="functions/most_popular_repo_bedrock_agent/agent",
            handler="summarize_repo_readme_agent",
            bundling=lambda_python.BundlingOptions(
                asset_excludes=[".venv", ".mypy_cache", "__pycache__"],
            ),
            timeout=Duration.minutes(2),
            memory_size=512,
            environment={
                "BEDROCK_AGENT_ID": bedrock_agent.attr_agent_id,
                "BEDROCK_AGENT_ALIAS_ID": bedrock_agent_alias.attr_agent_alias_id,
            },
        )
        summarize_repo_lambda.add_to_role_policy(bedrock_agent_access_policy)
        summarize_repo_lambda.add_to_role_policy(bedrock_model_access_policy)

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
            timeout=Duration.minutes(5),
        )
