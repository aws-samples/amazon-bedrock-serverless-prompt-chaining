from aws_cdk import (
    Duration,
    aws_bedrock as bedrock,
    aws_iam as iam,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
import builtins
import typing
import jsii


@jsii.implements(lambda_python.ICommandHooks)
class CommandHooks:
    @jsii.member(jsii_name="beforeBundling")
    def before_bundling(self, input_dir: str, output_dir: str) -> list[str]:
        return []

    @jsii.member(jsii_name="afterBundling")
    def after_bundling(self, input_dir: str, output_dir: str) -> list[str]:
        return [
            f"cd {output_dir}",
            # Don't bundle weasyprint - we get this from a Lambda layer at runtime
            "rm -rf weasyprint",
        ]


def get_lambda_bundling_options():
    return lambda_python.BundlingOptions(
        asset_excludes=[".venv", ".mypy_cache", "__pycache__"],
        command_hooks=CommandHooks(),
    )


def get_bedrock_iam_policy_statement():
    return iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "bedrock:InvokeModel",
        ],
        resources=[
            "arn:aws:bedrock:*::foundation-model/anthropic.claude-instant-v1",
            "arn:aws:bedrock:*::foundation-model/anthropic.claude-v2",
        ],
    )


def add_bedrock_retries(task):
    task.add_retry(
        errors=["ThrottlingException"],
        interval=Duration.seconds(5),
        max_delay=Duration.seconds(15),
    )


def get_anthropic_claude_prepare_prompt_step(
    scope: Construct,
    id: builtins.str,
    prompt: builtins.str,
    include_previous_conversation_in_prompt: bool,
    initial_assistant_text: typing.Optional[str] = "",
):
    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    if initial_assistant_text:
        messages.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": initial_assistant_text}],
            }
        )

    format_prompt = sfn.Pass(
        scope,
        id + " (Prepare Prompt)",
        parameters={
            "messages": messages,
        },
        result_path="$.model_inputs",
    )
    if include_previous_conversation_in_prompt:
        insert_conversation = sfn.Pass(
            scope,
            id + " (Include Previous Messages)",
            parameters={
                "messages": sfn.JsonPath.array(
                    sfn.JsonPath.string_at("$.model_outputs.conversation"),
                    sfn.JsonPath.string_at("$.model_inputs.messages"),
                ),
            },
            result_path="$.model_inputs",
        )
        format_prompt = format_prompt.next(insert_conversation)
    return format_prompt


def get_anthropic_claude_invoke_model_step(
    scope: Construct,
    id: builtins.str,
    claude_model_id: bedrock.FoundationModelIdentifier = bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_INSTANT_V1,
    max_tokens_to_sample: typing.Optional[int] = 250,
    temperature: typing.Optional[float] = 1,
    flatten_messages: typing.Optional[bool] = False,
):
    invoke_model = tasks.BedrockInvokeModel(
        scope,
        id + " (Invoke Model)",
        model=bedrock.FoundationModel.from_foundation_model_id(
            scope,
            "Model",
            claude_model_id,
        ),
        body=sfn.TaskInput.from_object(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": (
                    sfn.JsonPath.object_at("$.model_inputs.messages[*][*]")
                    if flatten_messages
                    else sfn.JsonPath.object_at("$.model_inputs.messages")
                ),
                "max_tokens": max_tokens_to_sample,
                "temperature": temperature,
            }
        ),
        result_selector={
            "role": sfn.JsonPath.string_at("$.Body.role"),
            "content": sfn.JsonPath.string_at("$.Body.content"),
        },
        result_path="$.model_outputs",
    )
    add_bedrock_retries(invoke_model)
    return invoke_model


def get_anthropic_claude_extract_response_step(
    scope: Construct,
    id: builtins.str,
    prompt: builtins.str,
    initial_assistant_text: typing.Optional[str] = "",
    flatten_messages: typing.Optional[bool] = False,
    pass_conversation: typing.Optional[bool] = True,
):
    response_value = sfn.JsonPath.string_at("$.model_outputs.content[0].text")
    if initial_assistant_text:
        response_value = sfn.JsonPath.format(
            "{}{}", initial_assistant_text, response_value
        )

    extract_response_parameters = {
        "prompt": prompt,
        "response": response_value,
        "conversation": sfn.JsonPath.array(
            (
                sfn.JsonPath.string_at("$.model_inputs.messages[*][*]")
                if flatten_messages
                else sfn.JsonPath.string_at("$.model_inputs.messages")
            ),
            sfn.JsonPath.array(sfn.JsonPath.string_at("$.model_outputs")),
        ),
    }
    if not pass_conversation:
        extract_response_parameters.pop("conversation")

    extract_response = sfn.Pass(
        scope,
        id + " (Extract Model Response)",
        parameters=extract_response_parameters,
        result_path="$.model_outputs",
    )

    if pass_conversation:
        prepare_outputs = sfn.Pass(
            scope,
            id + " (Prepare Output)",
            parameters={
                "prompt": sfn.JsonPath.string_at("$.model_outputs.prompt"),
                "response": sfn.JsonPath.string_at("$.model_outputs.response"),
                "conversation": sfn.JsonPath.object_at(
                    "$.model_outputs.conversation[*][*]"
                ),
            },
            result_path="$.model_outputs",
        )
        extract_response = extract_response.next(prepare_outputs)

    return extract_response


def get_anthropic_claude_invoke_chain(
    scope: Construct,
    id: builtins.str,
    prompt: builtins.str,
    claude_model_id: bedrock.FoundationModelIdentifier = bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_INSTANT_V1,
    initial_assistant_text: typing.Optional[str] = "",
    include_initial_assistant_text_in_response: typing.Optional[bool] = True,
    max_tokens_to_sample: typing.Optional[int] = 250,
    temperature: typing.Optional[float] = 1,
    include_previous_conversation_in_prompt: typing.Optional[bool] = True,
    pass_conversation: typing.Optional[bool] = True,
):
    format_prompt = get_anthropic_claude_prepare_prompt_step(
        scope,
        id,
        prompt,
        include_previous_conversation_in_prompt=include_previous_conversation_in_prompt,
        initial_assistant_text=initial_assistant_text,
    )

    invoke_model = get_anthropic_claude_invoke_model_step(
        scope,
        id,
        claude_model_id=claude_model_id,
        max_tokens_to_sample=max_tokens_to_sample,
        temperature=temperature,
        flatten_messages=include_previous_conversation_in_prompt,
    )

    extract_response = get_anthropic_claude_extract_response_step(
        scope,
        id,
        prompt,
        initial_assistant_text=(
            initial_assistant_text if include_initial_assistant_text_in_response else ""
        ),
        flatten_messages=include_previous_conversation_in_prompt,
        pass_conversation=pass_conversation,
    )

    return format_prompt.next(invoke_model).next(extract_response)
