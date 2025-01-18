from aws_cdk import (
    Stack,
    aws_bedrock as bedrock,
    aws_iam as iam,
)
from constructs import Construct


class ParallelChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = bedrock.FoundationModel.from_foundation_model_id(
            self,
            "Model",
            bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
        )

        # Define the prompts
        get_summary_prompt_content = (
            "Write a 1-2 sentence summary for the book Pride & Prejudice."
        )
        get_target_audience_prompt_content = (
            "Describe the target audience for the book Pride & Prejudice."
        )
        write_an_advertisement_prompt_content = (
            "Now write a short advertisement for the novel."
        )

        get_summary_prompt = bedrock.CfnPrompt(
            self,
            "GetSummaryPrompt",
            name="Flows-ParallelChain-GetSummary",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="CHAT",
                    # Configure the prompt
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        chat=bedrock.CfnPrompt.ChatPromptTemplateConfigurationProperty(
                            messages=[
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text=get_summary_prompt_content
                                        )
                                    ],
                                    role="user",
                                )
                            ],
                        ),
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

        get_target_audience_prompt = bedrock.CfnPrompt(
            self,
            "GetTargetAudiencePrompt",
            name="Flows-ParallelChain-GetTargetAudience",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="CHAT",
                    # Configure the prompt
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        chat=bedrock.CfnPrompt.ChatPromptTemplateConfigurationProperty(
                            messages=[
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text=get_target_audience_prompt_content
                                        )
                                    ],
                                    role="user",
                                )
                            ],
                        ),
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

        get_target_audience_prompt_version = bedrock.CfnPromptVersion(
            self,
            "GetTargetAudiencePromptVersion",
            prompt_arn=get_target_audience_prompt.attr_arn,
            # Description updates anytime the Prompt resource is updated,
            # so a new version is created when the Prompt changes
            description=f"Tracking prompt timestamp {get_target_audience_prompt.attr_updated_at}",
        )
        # Ensure prompt is fully stabilized before creating a new version
        get_target_audience_prompt_version.add_dependency(get_target_audience_prompt)

        write_an_advertisement_prompt = bedrock.CfnPrompt(
            self,
            "GetAdvertisementPrompt",
            name="Flows-ParallelChain-GetAdvertisement",
            default_variant="default",
            variants=[
                bedrock.CfnPrompt.PromptVariantProperty(
                    name="default",
                    template_type="CHAT",
                    # Configure the prompt, including the previous conversation
                    template_configuration=bedrock.CfnPrompt.PromptTemplateConfigurationProperty(
                        chat=bedrock.CfnPrompt.ChatPromptTemplateConfigurationProperty(
                            messages=[
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text=get_summary_prompt_content
                                        )
                                    ],
                                    role="user",
                                ),
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text="{{summary}}"
                                        ),
                                    ],
                                    role="assistant",
                                ),
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text=get_target_audience_prompt_content
                                        )
                                    ],
                                    role="user",
                                ),
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text="{{audience}}"
                                        ),
                                    ],
                                    role="assistant",
                                ),
                                bedrock.CfnPrompt.MessageProperty(
                                    content=[
                                        bedrock.CfnPrompt.ContentBlockProperty(
                                            text=write_an_advertisement_prompt_content
                                        )
                                    ],
                                    role="user",
                                ),
                            ],
                            input_variables=[
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="summary"
                                ),
                                bedrock.CfnPrompt.PromptInputVariableProperty(
                                    name="audience"
                                ),
                            ],
                        ),
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

        get_target_audience_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Get_Book_Target_Audience",
            type="Prompt",
            configuration=bedrock.CfnFlow.FlowNodeConfigurationProperty(
                prompt=bedrock.CfnFlow.PromptFlowNodeConfigurationProperty(
                    source_configuration=bedrock.CfnFlow.PromptFlowNodeSourceConfigurationProperty(
                        resource=bedrock.CfnFlow.PromptFlowNodeResourceConfigurationProperty(
                            prompt_arn=get_target_audience_prompt_version.attr_arn,
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

        write_an_advertisement_node = bedrock.CfnFlow.FlowNodeProperty(
            name="Generate_Book_Advertisement",
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
                    name="summary",
                    type="String",
                    expression="$.data",
                ),
                bedrock.CfnFlow.FlowNodeInputProperty(
                    name="audience",
                    type="String",
                    expression="$.data",
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
            # Input -> Get Summary
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([input_node.name, get_summary_node.name]),
                type="Data",
                source=input_node.name,
                target=get_summary_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=input_node.outputs[0].name,
                        target_input=get_summary_node.inputs[0].name,
                    ),
                ),
            ),
            # Input -> Get Target Audience
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join([input_node.name, get_target_audience_node.name]),
                type="Data",
                source=input_node.name,
                target=get_target_audience_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=input_node.outputs[0].name,
                        target_input=get_target_audience_node.inputs[0].name,
                    ),
                ),
            ),
            # Get Summary -> Write an Advertisement
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join(
                    [get_summary_node.name, write_an_advertisement_node.name]
                ),
                type="Data",
                source=get_summary_node.name,
                target=write_an_advertisement_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=get_summary_node.outputs[0].name,
                        target_input="summary",
                    ),
                ),
            ),
            # Get Target Audience -> Write an Advertisement
            bedrock.CfnFlow.FlowConnectionProperty(
                name="_".join(
                    [get_target_audience_node.name, write_an_advertisement_node.name]
                ),
                type="Data",
                source=get_target_audience_node.name,
                target=write_an_advertisement_node.name,
                configuration=bedrock.CfnFlow.FlowConnectionConfigurationProperty(
                    data=bedrock.CfnFlow.FlowDataConnectionConfigurationProperty(
                        source_output=get_target_audience_node.outputs[0].name,
                        target_input="audience",
                    ),
                ),
            ),
            # Write an Advertisement -> Output
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
            ),
        ]

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
                    f"{get_summary_prompt.attr_arn}:*",
                    f"{get_target_audience_prompt.attr_arn}:*",
                    f"{write_an_advertisement_prompt.attr_arn}:*",
                ],
            )
        )

        # Create the flow
        flow = bedrock.CfnFlow(
            self,
            "Flow",
            name="Flows-ParallelChain",
            execution_role_arn=flow_execution_role.role_arn,
            definition=bedrock.CfnFlow.FlowDefinitionProperty(
                nodes=[
                    input_node,
                    get_summary_node,
                    get_target_audience_node,
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
