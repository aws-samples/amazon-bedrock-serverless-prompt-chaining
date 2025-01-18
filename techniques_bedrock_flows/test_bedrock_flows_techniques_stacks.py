import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.model_invocation import FlowsModelInvocation
from stacks.prompt_templating import FlowsPromptTemplating
from stacks.sequential_chain import FlowsSequentialChain
from stacks.parallel_chain import FlowsParallelChain
from stacks.conditional_chain import FlowsConditionalChain
from stacks.map_chain import FlowsMapChain


def test_techniques_bedrock_flows_model_invocation_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsModelInvocation(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_bedrock_flows_prompt_templating_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsPromptTemplating(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_bedrock_flows_sequential_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsSequentialChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_bedrock_flows_parallel_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsParallelChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_bedrock_flows_conditional_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsConditionalChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_bedrock_flows_map_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = FlowsMapChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)
