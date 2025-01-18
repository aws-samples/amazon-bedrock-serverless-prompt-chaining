from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class MapChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Generate a JSON array of book titles and authors
        get_books = tasks.BedrockInvokeModel(
            self,
            "Generate Books Array",
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
                                    "text": """Give me the titles and authors of 5 famous novels.
Your response should be formatted as a JSON array, with each element in the array containing a "title" key for the novel's title and an "author" key with the novel's author.
An example of a valid response is below, inside <example></example> XML tags.
<example>
[
    \{
        "title": "Title 1",
        "author": "Author 1"
    \},
    \{
        "title": "Title 2",
        "author": "Author 2"
    \}
]
</example>
Do not include any other content outside of the JSON object.""",
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
                "novels": sfn.JsonPath.string_to_json(
                    sfn.JsonPath.string_at("$.Body.content[0].text")
                ),
            },
        )

        get_summary = tasks.BedrockInvokeModel(
            self,
            "Generate Novel Summary",
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
                                    # The prompt is templated with the novel name as variable input,
                                    # which is provided by the previous step that generates a list of novels.
                                    # The input to the task could be:
                                    # {
                                    #     "title": "Pride and Prejudice",
                                    #     "author": "Jane Austen"
                                    # }
                                    "text": sfn.JsonPath.format(
                                        "Write a 1-2 sentence summary for the novel {} by {}.",
                                        sfn.JsonPath.string_at(
                                            "$.novel.title",
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$.novel.author",
                                        ),
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

        write_an_advertisement = tasks.BedrockInvokeModel(
            self,
            "Generate Bookstore Advertisement",
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
                                    # Inject the previous model output summarizing 5 novels into this prompt.
                                    "type": "text",
                                    "text": sfn.JsonPath.format(
                                        """Write a short advertisement for a bookstore that sells the following novels.
1. {}
2. {}
3. {}
4. {}
5. {}""",
                                        sfn.JsonPath.string_at(
                                            "$[0].Body.content[0].text"
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$[1].Body.content[0].text"
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$[2].Body.content[0].text"
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$[3].Body.content[0].text"
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$[4].Body.content[0].text"
                                        ),
                                    ),
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

        # Hook the agents together into a workflow that contains a map
        chain = (
            get_books.next(model_response_to_array)
            .next(
                sfn.Map(
                    self,
                    "Loop Through Novels",
                    items_path=sfn.JsonPath.string_at("$.novels"),
                    parameters={
                        "novel.$": "$$.Map.Item.Value",
                    },
                    max_concurrency=1,
                ).iterator(get_summary)
            )
            .next(write_an_advertisement)
        )

        sfn.StateMachine(
            self,
            "MapExample",
            state_machine_name="Techniques-Map",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
        )
