from aws_cdk import (
    App,
    CfnOutput,
    Environment,
    Stack,
    aws_codestarconnections as connections,
    aws_codebuild as codebuild,
    aws_codepipeline as codepipeline,
    aws_codestarnotifications as notifications,
    aws_codepipeline_actions as actions,
    aws_iam as iam,
)
from constructs import Construct
import os


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        github_connection = connections.CfnConnection(
            self,
            "GitHubConnection",
            connection_name="bedrock-prompt-chain-repo",
            provider_type="GitHub",
        )
        CfnOutput(
            self,
            "CodeStarConnection",
            value=github_connection.attr_connection_arn,
            export_name="PromptChainCodeStarConnection",
        )

        pipeline = codepipeline.Pipeline(
            self,
            "Pipeline",
            pipeline_name="bedrock-serverless-prompt-chaining-demo",
            restart_execution_on_update=True,
        )

        notifications.CfnNotificationRule(
            self,
            "PipelineNotifications",
            name="bedrock-serverless-prompt-chaining-demo",
            detail_type="FULL",
            resource=pipeline.pipeline_arn,
            event_type_ids=["codepipeline-pipeline-pipeline-execution-failed"],
            targets=[
                notifications.CfnNotificationRule.TargetProperty(
                    target_type="SNS",
                    target_address=Stack.of(self).format_arn(
                        service="sns",
                        resource="bedrock-serverless-prompt-chaining-notifications",
                    ),
                )
            ],
        )

        # Pipeline source
        source_output = codepipeline.Artifact("SourceArtifact")
        source_action = actions.CodeStarConnectionsSourceAction(
            action_name="GitHubSource",
            owner="aws-samples",
            repo="amazon-bedrock-serverless-prompt-chaining",
            connection_arn=github_connection.attr_connection_arn,
            output=source_output,
        )
        pipeline.add_stage(stage_name="Source", actions=[source_action])

        # Update pipeline
        # This pipeline stage uses CodeBuild to self-mutate the pipeline by re-deploying the pipeline's CDK code
        # If the pipeline changes, it will automatically start again
        pipeline_project = codebuild.PipelineProject(
            self,
            "UpdatePipeline",
            build_spec=codebuild.BuildSpec.from_object_to_yaml(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "runtime-versions": {
                                "python": "3.x",
                                "nodejs": "latest",
                            },
                            "commands": [
                                "cd $CODEBUILD_SRC_DIR/pipeline",
                                "npm install -g aws-cdk",
                                "python3 -m venv .venv",
                                "source .venv/bin/activate",
                                "pip install -r requirements.txt",
                            ],
                        },
                        "build": {
                            "commands": [
                                "cdk deploy --app 'python3 pipeline_stack.py' --require-approval=never",
                            ]
                        },
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )

        pipeline_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudformation:*",
                    "codebuild:*",
                    "codepipeline:*",
                    "s3:*",
                    "kms:*",
                    "codestar-notifications:*",
                    "codestar-connections:*",
                    "iam:*",
                    "events:*",
                    "ssm:*",
                ],
                resources=["*"],
            )
        )

        pipeline_build_action = actions.CodeBuildAction(
            action_name="DeployPipeline",
            project=pipeline_project,
            input=source_output,
        )
        pipeline.add_stage(stage_name="SyncPipeline", actions=[pipeline_build_action])

        # Deploy
        deploy_project = codebuild.PipelineProject(
            self,
            "DeployProject",
            build_spec=codebuild.BuildSpec.from_object_to_yaml(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "runtime-versions": {
                                "python": "3.x",
                                "nodejs": "latest",
                            },
                            "commands": [
                                "npm install -g aws-cdk",
                                "python3 -m venv .venv",
                                "source .venv/bin/activate",
                                "pip install -r requirements.txt",
                            ],
                        },
                        "build": {
                            "commands": [
                                "cdk deploy --app 'python3 cdk_stacks.py' --all --require-approval=never",
                            ]
                        },
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )
        deploy_project.add_to_role_policy(
            iam.PolicyStatement(actions=["*"], resources=["*"])
        )
        deploy_action = actions.CodeBuildAction(
            action_name="Deploy", project=deploy_project, input=source_output
        )
        pipeline.add_stage(stage_name="Deploy", actions=[deploy_action])


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
PipelineStack(app, "PromptChainingPipeline", env=env)
app.synth()
