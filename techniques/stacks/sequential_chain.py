from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class SequentialChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        get_summary = tasks.BedrockInvokeModel(
            self,
            "Generate Book Summary",
            # Choose the model to invoke
            model=bedrock.FoundationModel.from_foundation_model_id(
                self,
                "Model",
                bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
            ),
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

        write_an_advertisement = tasks.BedrockInvokeModel(
            self,
            "Generate Book Advertisement",
            model=bedrock.FoundationModel.from_foundation_model_id(
                self,
                "Model",
                bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
            ),
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
                            "role": sfn.JsonPath.string_at("$.Body.role"),
                            "content": sfn.JsonPath.string_at("$.Body.content"),
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

        # Chain the steps together
        chain = get_summary.next(write_an_advertisement)

        sfn.StateMachine(
            self,
            "SequentialChainExample",
            state_machine_name="Techniques-SequentialChain",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
        )
