from aws_cdk import (
    aws_iam as iam,
    Stack,
    aws_bedrock as bedrock,
    aws_sns as sns,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .inference_profile import InferenceProfile


class AwsServiceInvocationChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = InferenceProfile(self, "Model", "global.anthropic.claude-haiku-4-5-20251001-v1:0")

        get_summary = tasks.BedrockInvokeModel(
            self,
            "Generate Book Summary",
            # Choose the model to invoke
            model=model,
            # Provide the input to the model, including the templated prompt and inference properties
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The prompt is templated with the novel name as variable input.
                                    # The input to the Step Functions execution could be:
                                    # "Pride and Prejudice"
                                    "text": sfn.JsonPath.format(
                                        "Write a 1-2 sentence summary for the book {}.",
                                        sfn.JsonPath.string_at("$$.Execution.Input"),
                                    ),
                                }
                            ],
                        }
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
        )

        topic = sns.Topic(
            self, "Topic", display_name="Notifications about generated book summaries"
        )
        notify_me = tasks.SnsPublish(
            self,
            "Notify Me",
            topic=topic,
            message=sfn.TaskInput.from_object(
                {
                    "summary": sfn.JsonPath.string_at("$.Body.content[0].text"),
                    "book": sfn.JsonPath.string_at("$$.Execution.Input"),
                }
            ),
            result_path=sfn.JsonPath.DISCARD,
            output_path="$.Body.content[0].text",
        )

        chain = get_summary.next(notify_me)

        state_machine = sfn.StateMachine(
            self,
            "AwsServiceInvocationExample",
            state_machine_name="Techniques-AwsServiceInvocation",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
        )

        # Add IAM permission for the foundation model
        state_machine.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[model.get_foundation_model_arn_pattern()],
            )
        )
