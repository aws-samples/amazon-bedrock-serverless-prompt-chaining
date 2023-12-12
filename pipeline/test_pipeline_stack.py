import aws_cdk as cdk
from aws_cdk.assertions import Template

from pipeline_stack import PipelineStack


def test_pipeline_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = PipelineStack(app, "TestPipeline")

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)
