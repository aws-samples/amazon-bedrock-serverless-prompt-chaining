from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .inference_profile import InferenceProfile


class ModelInvocation(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = InferenceProfile(
            self,
            "Model",
            "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        )

        get_summary = tasks.BedrockInvokeModel(
            self,
            "Generate Book Summary",
            # Choose the model to invoke
            model=model,
            # Provide the input to the model, including the prompt and inference properties
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The main prompt
                                    "text": "Write a 1-2 sentence summary for the book Pride & Prejudice.",
                                }
                            ],
                        }
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
            # Extract the response from the model as the result of the Step Functions execution
            output_path="$.Body.content[0].text",
        )

        state_machine = sfn.StateMachine(
            self,
            "ModelInvocationExample",
            state_machine_name="Techniques-ModelInvocation",
            definition_body=sfn.DefinitionBody.from_chainable(get_summary),
        )

        # Add IAM permission for the foundation model
        state_machine.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[model.get_foundation_model_arn_pattern()],
            )
        )
