from aws_cdk import (
    Duration,
    aws_iam as iam,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
)
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
