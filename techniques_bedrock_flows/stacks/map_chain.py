from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
)
from constructs import Construct
import json


class FlowsMapChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = bedrock.FoundationModel.from_foundation_model_id(
            self,
            "Model",
            bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
        )

        # Define the prompts
        get_books_prompt_content = """Give me the titles and authors of 5 famous novels.
Your response should be formatted as a JSON array, with each element in the array containing a "title" key for the novel's title and an "author" key with the novel's author.
An example of a valid response is below, inside <example></example> XML tags.
<example>
[
    {
        "title": "Title 1",
        "author": "Author 1"
    },
    {
        "title": "Title 2",
        "author": "Author 2"
    }
]
</example>
Do not include any other content outside of the JSON object."""

        get_summary_prompt_content = (
            "Write a 1-2 sentence summary for the novel {{title}} by {{author}}."
        )

        write_an_advertisement_prompt_content = """Write a short advertisement for a bookstore that sells the following novels.
1. {{bookOne}}
2. {{bookTwo}}
3. {{bookThree}}
4. {{bookFour}}
5. {{bookFive}}"""

        get_books_prompt = bedrock.CfnPrompt(
            self,
            "GetBooksPrompt",
            name="Flows-Map-GetBooks",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    # Configure the prompt
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=get_books_prompt_content,
                        )
                    ),
                    # Configure the model and inference settings
                    model_id=model.model_id,
                    inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            max_tokens=250,
                            temperature=1,
                        )
                    ),
                )
            ],
        )

        get_books_prompt_version = bedrock.CfnPromptVersion(
            self,
            "GetBooksPromptVersion",
            prompt_arn=get_books_prompt.attr_arn,
            # Description updates anytime the Prompt resource is updated,
            # so a new version is created when the Prompt changes
            description=f"Tracking prompt timestamp {get_books_prompt.attr_updated_at}",
        )
        # Ensure prompt is fully stabilized before creating a new version
        get_books_prompt_version.add_dependency(get_books_prompt)

        get_summary_prompt = bedrock.CfnPrompt(
            self,
            "GetSummaryPrompt",
            name="Flows-Map-GetSummary",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    # Configure the prompt
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=get_summary_prompt_content,
                            input_variables=[
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="title"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="author"
                                ),
                            ],
                        )
                    ),
                    # Configure the model and inference settings
                    model_id=model.model_id,
                    inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            max_tokens=250,
                            temperature=1,
                        )
                    ),
                )
            ],
        )

        get_summary_prompt_version = bedrock.CfnPromptVersion(
            self,
            "GetSummaryPromptVersion",
            prompt_arn=get_summary_prompt.attr_arn,
            # Description updates anytime the Prompt resource is updated,
            # so a new version is created when the Prompt changes
            description=f"Tracking prompt timestamp {get_summary_prompt.attr_updated_at}",
        )
        # Ensure prompt is fully stabilized before creating a new version
        get_summary_prompt_version.add_dependency(get_summary_prompt)

        write_an_advertisement_prompt = bedrock.CfnPrompt(
            self,
            "GetAdvertisementPrompt",
            name="Flows-Map-GetAdvertisement",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="TEXT",
                    # Configure the prompt, including the previous conversation
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        text=bedrock.CfnPrompt.TextPromptTemplateConfigurationProperty(
                            text=write_an_advertisement_prompt_content,
                            input_variables=[
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="bookOne"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="bookTwo"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="bookThree"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="bookFour"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="bookFive"
                                ),
                            ],
                        )
                    ),
                    # Configure the model and inference settings
                    model_id=model.model_id,
                    inference_configuration=bedrock.CfnPrompt.PromptInferenceConfigurationProperty(
                        text=bedrock.CfnPrompt.PromptModelInferenceConfigurationProperty(
                            max_tokens=250,
                            temperature=1,
                        )
                    ),
                )
            ],
        )

        write_an_advertisement_prompt_version = bedrock.CfnPromptVersion(
            self,
            "GetAdvertisementPromptVersion",
            prompt_arn=write_an_advertisement_prompt.attr_arn,
            # Description updates anytime the Prompt resource is updated,
            # so a new version is created when the Prompt changes
            description=f"Tracking prompt timestamp {write_an_advertisement_prompt.attr_updated_at}",
        )
        # Ensure prompt is fully stabilized before creating a new version
        write_an_advertisement_prompt_version.add_dependency(
            write_an_advertisement_prompt
        )

        # Set up Lambda function(s) for custom logic
        book_array_json_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                },
                "required": ["title", "author"],
                "additionalProperties": False,
            },
            "minItems": 5,
            "maxItems": 5,
            "uniqueItems": True,
        }

        book_array_json_parser_lambda = lambda_python.PythonFunction(
            self,
            "ParseJsonFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="functions/parse_json_response",
            memory_size=256,
            environment={
                "SCHEMA": json.dumps(book_array_json_schema),
            },
        )

        # Configure the flow's nodes and connections between nodes
        input_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Input",
            type="Input",
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="document",
                    type="String",
                )
            ],
        )

        get_books_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Generate_Books",
            type="Prompt",
            configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                prompt=bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                    source_configuration=bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                        resource=bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                            prompt_arn=get_books_prompt_version.attr_arn,
                        )
                    )
                )
            ),
            inputs=[
                # This input will be ignored, because the prompt is not templated
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="ignore",
                    type="String",
                    expression="$.data",
                )
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="modelCompletion",
                    type="String",
                )
            ],
        )

        parse_books_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Parse_Books_Array",
            type="LambdaFunction",
            configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                lambda_function=bedrock.CfnFlow.LambdaFunctionFlowNodeConfigurationProperty(
                    lambda_arn=book_array_json_parser_lambda.function_arn,
                ),
            ),
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="input",
                    type="String",
                    expression="$.data",
                )
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="functionResponse",
                    type="Array",
                )
            ],
        )

        books_iterator_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Books_Iterator",
            type="Iterator",
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="array",
                    type="Array",
                    expression="$.data",
                )
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="arrayItem",
                    type="Object",
                ),
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="arraySize",
                    type="Number",
                ),
            ],
        )

        books_collector_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Books_Collector",
            type="Collector",
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="arrayItem",
                    type="String",
                    expression="$.data",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="arraySize",
                    type="Number",
                    expression="$.data",
                ),
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="collectedArray",
                    type="Array",
                )
            ],
        )

        get_summary_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Generate_Book_Summary",
            type="Prompt",
            configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                prompt=bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                    source_configuration=bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                        resource=bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                            prompt_arn=get_summary_prompt_version.attr_arn,
                        )
                    )
                )
            ),
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="title",
                    type="String",
                    expression="$.data.title",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="author",
                    type="String",
                    expression="$.data.author",
                ),
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="modelCompletion",
                    type="String",
                )
            ],
        )

        write_an_advertisement_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Generate_Bookstore_Advertisement",
            type="Prompt",
            configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                prompt=bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                    source_configuration=bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                        resource=bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                            prompt_arn=write_an_advertisement_prompt_version.attr_arn,
                        )
                    )
                )
            ),
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="bookOne",
                    type="String",
                    expression="$.data[0]",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="bookTwo",
                    type="String",
                    expression="$.data[1]",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="bookThree",
                    type="String",
                    expression="$.data[2]",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="bookFour",
                    type="String",
                    expression="$.data[3]",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="bookFive",
                    type="String",
                    expression="$.data[4]",
                ),
            ],
            outputs=[
                bedrock.CfnFlow.FlowNodeOutputProperty(
                    name="modelCompletion",
                    type="String",
                )
            ],
        )

        output_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Output",
            type="Output",
            inputs=[
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="document",
                    type="String",
                    expression="$.data",
                ),
            ],
        )

        connections = [
            # Input -> Get Books
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([input_node.name, get_books_node.name]),
                type="Data",
                source=input_node.name,
                target=get_books_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=input_node.outputs[0].name,
                        target_input=get_books_node.inputs[0].name,
                    ),
                ),
            ),
            # Get Books -> Parse Books
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([get_books_node.name, parse_books_node.name]),
                type="Data",
                source=get_books_node.name,
                target=parse_books_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=get_books_node.outputs[0].name,
                        target_input=parse_books_node.inputs[0].name,
                    ),
                ),
            ),
            # Parse Books -> Books Iterator
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([parse_books_node.name, books_iterator_node.name]),
                type="Data",
                source=parse_books_node.name,
                target=books_iterator_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=parse_books_node.outputs[0].name,
                        target_input=books_iterator_node.inputs[0].name,
                    ),
                ),
            ),
            # Books Iterator -> Get Summary
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([books_iterator_node.name, get_summary_node.name])
                + "_Title",
                type="Data",
                source=books_iterator_node.name,
                target=get_summary_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=books_iterator_node.outputs[0].name,
                        target_input=get_summary_node.inputs[0].name,
                    ),
                ),
            ),
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([books_iterator_node.name, get_summary_node.name])
                + "_Author",
                type="Data",
                source=books_iterator_node.name,
                target=get_summary_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=books_iterator_node.outputs[0].name,
                        target_input=get_summary_node.inputs[1].name,
                    ),
                ),
            ),
            # Get Summary -> Books Collector
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([get_summary_node.name, books_collector_node.name]),
                type="Data",
                source=get_summary_node.name,
                target=books_collector_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=get_summary_node.outputs[0].name,
                        target_input=books_collector_node.inputs[0].name,
                    ),
                ),
            ),
            # Books Iterator -> Books Collector
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([books_iterator_node.name, books_collector_node.name]),
                type="Data",
                source=books_iterator_node.name,
                target=books_collector_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=books_iterator_node.outputs[1].name,
                        target_input=books_collector_node.inputs[1].name,
                    ),
                ),
            ),
        ]

        # Books Collector -> Write an Advertisement
        for i in range(0, 5):
            connections.append(
                bedrock.CfnFlow.FlowConnectionProperty(
                    name="_".join(
                        [books_collector_node.name, write_an_advertisement_node.name]
                    )
                    + f"_Book{i}",
                    type="Data",
                    source=books_collector_node.name,
                    target=write_an_advertisement_node.name,
                    configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                        data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                            source_output=books_collector_node.outputs[0].name,
                            target_input=write_an_advertisement_node.inputs[i].name,
                        ),
                    ),
                )
            )

        # Write an Advertisement -> Output
        connections.append(
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([write_an_advertisement_node.name, output_node.name]),
                type="Data",
                source=write_an_advertisement_node.name,
                target=output_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=write_an_advertisement_node.outputs[0].name,
                        target_input=output_node.inputs[0].name,
                    ),
                ),
            )
        )

        # Create a role for executing the flow
        # See https://docs.aws.amazon.com/bedrock/latest/userguide/flows-permissions.html
        bedrock_principal = iam.ServicePrincipal(
            "bedrock.amazonaws.com",
            conditions={
                "StringEquals": {"aws:SourceAccount": self.account},
                "ArnLike": {
                    "aws:SourceArn": f"arn:aws:bedrock:{self.region}:{self.account}:flow/*"
                },
            },
        )

        flow_execution_role = iam.Role(
            self,
            "BedrockFlowsServiceRole",
            assumed_by=bedrock_principal,
        )

        flow_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[model.model_arn],
            )
        )
        flow_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:RenderPrompt"],
                resources=[
                    f"{get_books_prompt.attr_arn}:*",
                    f"{get_summary_prompt.attr_arn}:*",
                    f"{write_an_advertisement_prompt.attr_arn}:*",
                ],
            )
        )
        flow_execution_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[book_array_json_parser_lambda.function_arn],
            )
        )

        # Create the flow
        flow = bedrock.CfnFlow(
            self,
            "Flow",
            name="Flows-Map",
            execution_role_arn=flow_execution_role.role_arn,
            definition=bedrock.CfnFlow.FlowDefinitionProperty(
                nodes=[
                    input_node,
                    get_books_node,
                    parse_books_node,
                    books_iterator_node,
                    get_summary_node,
                    books_collector_node,
                    write_an_advertisement_node,
                    output_node,
                ],
                connections=connections,
            ),
        )

        flow_version = bedrock.CfnFlowVersion(
            self,
            "FlowVersion",
            flow_arn=flow.attr_arn,
            # Description updates anytime the Flow resource is updated,
            # so a new version is created when the Flow changes
            description="Tracking flow timestamp " + flow.attr_updated_at,
        )
        # Ensure flow is fully stabilized before creating a new version
        flow_version.add_dependency(flow)

        flow_alias = bedrock.CfnFlowAlias(
            self,
            "FlowAlias",
            name="live",
            flow_arn=flow.attr_arn,
            routing_configuration=[
                bedrock.CfnFlowAlias.FlowAliasRoutingConfigurationListItemProperty(
                    flow_version=flow_version.attr_version,
                ),
            ],
        )
        # Ensure flow version is fully stabilized before updating the alias
        flow_alias.add_dependency(flow_version)
