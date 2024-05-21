import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.webapp_stack import WebappStack
from stacks.blog_post_stack import BlogPostStack
from stacks.trip_planner_stack import TripPlannerStack
from stacks.story_writer_stack import StoryWriterStack
from stacks.movie_pitch_stack import MoviePitchStack
from stacks.meal_planner_stack import MealPlannerStack
from stacks.most_popular_repo_bedrock_agent_stack import (
    MostPopularRepoBedrockAgentStack,
)
from stacks.most_popular_repo_langchain_stack import (
    MostPopularRepoLangchainStack,
)
from stacks.alarms_stack import AlarmsStack
from techniques.stacks.model_invocation import ModelInvocation
from techniques.stacks.prompt_templating import PromptTemplating
from techniques.stacks.sequential_chain import SequentialChain
from techniques.stacks.parallel_chain import ParallelChain
from techniques.stacks.conditional_chain import ConditionalChain
from techniques.stacks.human_input_chain import HumanInputChain
from techniques.stacks.map_chain import MapChain
from techniques.stacks.aws_service_invocation import AwsServiceInvocationChain
from techniques.stacks.validation_chain import ValidationChain

# Note: the webapp stack and trip planner stack are not tested, because they do account lookups


def test_blogpost_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = BlogPostStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_storywriter_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = StoryWriterStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_moviepitch_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MoviePitchStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_mealplanner_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MealPlannerStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_mostpopularrepo_bedrockagents_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MostPopularRepoBedrockAgentStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_mostpopularrepo_langchain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MostPopularRepoLangchainStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_alarms_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = AlarmsStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_model_invocation_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ModelInvocation(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_prompt_templating_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = PromptTemplating(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_sequential_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = SequentialChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_parallel_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ParallelChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_conditional_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = ConditionalChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_human_input_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = HumanInputChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_map_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = MapChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)


def test_techniques_service_invocation_chain_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = AwsServiceInvocationChain(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)
