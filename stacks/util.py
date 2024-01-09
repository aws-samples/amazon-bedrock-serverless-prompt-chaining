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

CLAUDE_HUMAN_PROMPT = """\n\nHuman:"""
CLAUDE_AI_PROMPT = """\n\nAssistant:"""


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


def get_claude_instant_invoke_chain(
    scope: Construct,
    id: builtins.str,
    prompt: builtins.str,
    max_tokens_to_sample: typing.Optional[int] = 250,
    temperature: typing.Optional[float] = 1,
    include_previous_conversation_in_prompt=True,
):
    model_prompt = sfn.JsonPath.format(
        f"{CLAUDE_HUMAN_PROMPT}{{}}{CLAUDE_AI_PROMPT}",
        prompt,
    )
    if include_previous_conversation_in_prompt:
        model_prompt = sfn.JsonPath.format(
            "{}{}",
            sfn.JsonPath.string_at("$.output.conversation"),
            model_prompt,
        )
    format_prompt = sfn.Pass(
        scope,
        id + " (Format Model Inputs)",
        parameters={
            "prompt": model_prompt,
            "max_tokens_to_sample": max_tokens_to_sample,
            "temperature": temperature,
        },
        result_path="$.model_inputs",
    )
    invoke_model = tasks.BedrockInvokeModel(
        scope,
        id + " (Invoke Model)",
        model=bedrock.FoundationModel.from_foundation_model_id(
            scope,
            "Model",
            bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_INSTANT_V1,
        ),
        body=sfn.TaskInput.from_json_path_at("$.model_inputs"),
        result_selector={"response": sfn.JsonPath.string_at("$.Body.completion")},
        result_path="$.model_outputs",
    )
    add_bedrock_retries(invoke_model)
    format_response = sfn.Pass(
        scope,
        id + " (Format Model Outputs)",
        parameters={
            "response": sfn.JsonPath.string_at("$.model_outputs.response"),
            "conversation": sfn.JsonPath.format(
                "{}{}",
                sfn.JsonPath.string_at("$.model_inputs.prompt"),
                sfn.JsonPath.string_at("$.model_outputs.response"),
            ),
        },
        result_path="$.output",
    )
    return format_prompt.next(invoke_model).next(format_response)
