import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.webapp_stack import WebappStack
from stacks.blog_post_stack import BlogPostStack
from stacks.trip_planner_stack import TripPlannerStack
from stacks.story_writer_stack import StoryWriterStack
from stacks.movie_pitch_stack import MoviePitchStack
from stacks.meal_planner_stack import MealPlannerStack
from stacks.alarms_stack import AlarmsStack

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


def test_alarms_stack_synthesizes_properly():
    app = cdk.App()

    test_stack = AlarmsStack(
        app,
        "TestStack",
    )

    # Ensure the template synthesizes successfully
    Template.from_stack(test_stack)
