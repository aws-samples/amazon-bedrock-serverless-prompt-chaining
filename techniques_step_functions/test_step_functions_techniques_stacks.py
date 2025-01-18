import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.model_invocation import ModelInvocation
from stacks.prompt_templating import PromptTemplating
from stacks.sequential_chain import SequentialChain
from stacks.parallel_chain import ParallelChain
from stacks.conditional_chain import ConditionalChain
from stacks.human_input_chain import HumanInputChain
from stacks.map_chain import MapChain
from stacks.aws_service_invocation import (
    AwsServiceInvocationChain,
)
from stacks.validation_chain import ValidationChain


def test_techniques_step_functions_model_invocation_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ModelInvocation(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_prompt_templating_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = PromptTemplating(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_sequential_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = SequentialChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_parallel_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ParallelChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_conditional_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ConditionalChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_human_input_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = HumanInputChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_map_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MapChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_service_invocation_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = AwsServiceInvocationChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_step_functions_validation_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ValidationChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)
