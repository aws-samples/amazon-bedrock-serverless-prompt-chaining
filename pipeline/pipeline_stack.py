from aws_cdk import (
    CfnOutput,
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
            branch="main",
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
                                "cdk deploy --app 'python3 pipeline_app.py' --require-approval=never",
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

        # Deploy examples
        deploy_examples_project = codebuild.PipelineProject(
            self,
            "DeployExamples",
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
                                "cd techniques_step_functions/",
                                "cdk deploy --app 'python3 technique_stacks.py' --all --require-approval=never",
                                "cd ../techniques_bedrock_flows/",
                                "cdk deploy --app 'python3 technique_stacks.py' --all --require-approval=never",
                            ]
                        },
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )
        deploy_examples_project.add_to_role_policy(
            iam.PolicyStatement(actions=["*"], resources=["*"])
        )
        deploy_examples_action = actions.CodeBuildAction(
            action_name="Deploy",
            project=deploy_examples_project,
            input=source_output,
        )

        deploy_examples_stage = pipeline.add_stage(
            stage_name="DeployExamples", actions=[deploy_examples_action]
        )

        test_examples = codebuild.PipelineProject(
            self,
            "TestExamples",
            build_spec=codebuild.BuildSpec.from_object_to_yaml(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                # Test Step Functions examples
                                "cd techniques_step_functions/",
                                "./run-test-execution.sh ModelInvocation",
                                "sleep 30",
                                "./run-test-execution.sh PromptTemplating",
                                "sleep 30",
                                "./run-test-execution.sh SequentialChain",
                                "sleep 30",
                                "./run-test-execution.sh ParallelChain",
                                "sleep 30",
                                "./run-test-execution.sh ConditionalChain",
                                # Don't test HumanInput in the pipeline because it relies on human input
                                # "sleep 30",
                                # "./run-test-execution.sh HumanInput",
                                "sleep 30",
                                "./run-test-execution.sh Map",
                                "sleep 30",
                                "./run-test-execution.sh AwsServiceInvocation",
                                "sleep 30",
                                "./run-test-execution.sh Validation",
                                # Test Bedrock Flows examples
                                "cd ../techniques_bedrock_flows/",
                                "python3 run-test-execution.py ModelInvocation",
                                "sleep 30",
                                "python3 run-test-execution.py PromptTemplating",
                                "sleep 30",
                                "python3 run-test-execution.py SequentialChain",
                                "sleep 30",
                                "python3 run-test-execution.py ParallelChain",
                                "sleep 30",
                                "python3 run-test-execution.py ConditionalChain",
                                "sleep 30",
                                "python3 run-test-execution.py Map",
                            ]
                        },
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )

        test_examples.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "states:StartExecution",
                    "states:DescribeExecution",
                    "bedrock:ListFlows",
                    "bedrock:ListFlowAliases",
                    "bedrock:InvokeFlow",
                ],
                resources=["*"],
            )
        )

        test_examples_action = actions.CodeBuildAction(
            action_name="Test",
            project=test_examples,
            input=source_output,
            type=actions.CodeBuildActionType.TEST,
            run_order=2,
        )
        deploy_examples_stage.add_action(test_examples_action)

        # Deploy demo app
        deploy_project = codebuild.PipelineProject(
            self,
            "DeployDemoApp",
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

        deploy_stage = pipeline.add_stage(
            stage_name="DeployDemoApp", actions=[deploy_action]
        )

        # Test each demo
        test_project = codebuild.PipelineProject(
            self,
            "TestDemoApp",
            build_spec=codebuild.BuildSpec.from_object_to_yaml(
                {
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                "./run-test-execution.sh BlogPost",
                                "sleep 30",
                                "./run-test-execution.sh TripPlanner",
                                "sleep 30",
                                "./run-test-execution.sh StoryWriter",
                                "sleep 30",
                                # Don't test MoviePitch in the pipeline because it relies on human input
                                # "./run-test-execution.sh MoviePitch",
                                # "sleep 30",
                                "./run-test-execution.sh MealPlanner",
                                "sleep 30",
                                "./run-test-execution.sh MostPopularRepoBedrockAgents",
                                "sleep 30",
                                "./run-test-execution.sh MostPopularRepoLangchain",
                            ]
                        },
                    },
                }
            ),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_5
            ),
        )

        test_project.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "states:StartExecution",
                    "states:DescribeExecution",
                ],
                resources=["*"],
            )
        )

        test_action = actions.CodeBuildAction(
            action_name="Test",
            project=test_project,
            input=source_output,
            type=actions.CodeBuildActionType.TEST,
            run_order=2,
        )
        deploy_stage.add_action(test_action)
