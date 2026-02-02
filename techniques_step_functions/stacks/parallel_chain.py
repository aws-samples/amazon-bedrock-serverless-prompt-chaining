from aws_cdk import (
    aws_iam as iam,
    Stack,
    aws_bedrock as bedrock,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .inference_profile import InferenceProfile


class ParallelChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = InferenceProfile(self, "Model", "global.anthropic.claude-haiku-4-5-20251001-v1:0")

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
        )

        get_target_audience = tasks.BedrockInvokeModel(
            self,
            "Generate Book's Target Audience",
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
                                    "text": "Describe the target audience for the book Pride & Prejudice.",
                                }
                            ],
                        }
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
        )

        write_an_advertisement = tasks.BedrockInvokeModel(
            self,
            "Write Book Advertisement",
            model=model,
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    # Inject the previous output from the model as past conversation,
                    # then add the new prompt that relies on previous output as context.
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The previous step's prompt.
                                    "text": "Write a 1-2 sentence summary for the book Pride & Prejudice.",
                                },
                            ],
                        },
                        {
                            # The previous step's model output
                            "role": sfn.JsonPath.string_at("$.summary.Body.role"),
                            "content": sfn.JsonPath.string_at("$.summary.Body.content"),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The previous step's prompt.
                                    "text": "Describe the target audience for the book Pride & Prejudice.",
                                },
                            ],
                        },
                        {
                            # The previous step's model output
                            "role": sfn.JsonPath.string_at("$.audience.Body.role"),
                            "content": sfn.JsonPath.string_at(
                                "$.audience.Body.content"
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The new prompt
                                    "text": "Now write a short advertisement for the novel.",
                                },
                            ],
                        },
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
            # Extract the final response from the model as the result of the Step Functions execution
            output_path="$.Body.content[0].text",
        )

        # Hook the steps together into a chain that contains some parallel steps
        chain = (
            sfn.Parallel(
                self,
                "Parallel Tasks",
                result_selector={
                    "summary.$": "$[0]",
                    "audience.$": "$[1]",
                },
            )
            .branch(get_summary)
            .branch(get_target_audience)
        ).next(write_an_advertisement)

        state_machine = sfn.StateMachine(
            self,
            "ParallelChainExample",
            state_machine_name="Techniques-ParallelChain",
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
