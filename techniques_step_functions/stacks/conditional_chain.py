from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class ConditionalChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        validate_input = tasks.BedrockInvokeModel(
            self,
            "Decide if input is a book",
            model=bedrock.FoundationModel.from_foundation_model_id(
                self,
                "Model",
                bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
            ),
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # As the model if the input is a book or not
                                    "text": sfn.JsonPath.format(
                                        """Does the following text in <text></text> XML tags refer to the name of a book?
<text>
{}
</text>
Start your response with an explanation of your reasoning, then provide a single 'yes' or 'no' indicating whether the text refers to a book.

Your response should be formatted as a JSON object.
An example of a valid response is below when the text does refer to a book, inside <example></example> XML tags.
<example>
\{
    "reasoning": "Brief reasons for why I believe the text refers to a book...",
    "is_book": "yes"
\}
</example>

Another example of a valid response is below when the text does NOT refer to a book, inside <example></example> XML tags.
<example>
\{
    "reasoning": "Brief reasons for why I believe the text does not refer to a book...",
    "is_book": "no"
\}
</example>
Do not include any other content other than the JSON object in your response. Do not include any XML tags in your response.""",
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

        model_response_to_array = sfn.Pass(
            self,
            "Parse Model Response",
            parameters={
                "decision": sfn.JsonPath.string_to_json(
                    sfn.JsonPath.string_at("$.Body.content[0].text")
                ),
            },
        )

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

        # Chain the steps together with a condition
        book_decision = (
            sfn.Choice(self, "Is it a book?")
            .when(
                sfn.Condition.string_equals("$.decision.is_book", "yes"),
                get_summary.next(write_an_advertisement),
            )
            .otherwise(sfn.Fail(self, "Input was not a book"))
        )
        chain = validate_input.next(model_response_to_array).next(book_decision)

        sfn.StateMachine(
            self,
            "ConditionalChainExample",
            state_machine_name="Techniques-ConditionalChain",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
        )
