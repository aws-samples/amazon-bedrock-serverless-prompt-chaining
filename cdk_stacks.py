from aws_cdk import (
    App,
    Environment,
)
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
import os


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
WebappStack(
    app,
    "PromptChaining-StreamlitWebapp",
    env=env,
    parent_domain="TODO FILL IN",
)
BlogPostStack(
    app,
    "PromptChaining-BlogPostDemo",
    env=env,
)
TripPlannerStack(
    app,
    "PromptChaining-TripPlannerDemo",
    env=env,
)
StoryWriterStack(
    app,
    "PromptChaining-StoryWriterDemo",
    env=env,
)
MoviePitchStack(
    app,
    "PromptChaining-MoviePitchDemo",
    env=env,
)
MealPlannerStack(
    app,
    "PromptChaining-MealPlannerDemo",
    env=env,
)
MostPopularRepoBedrockAgentStack(
    app,
    "PromptChaining-MostPopularRepoBedrockAgentsDemo",
    env=env,
)
MostPopularRepoLangchainStack(
    app,
    "PromptChaining-MostPopularRepoLangchainDemo",
    env=env,
)
AlarmsStack(
    app,
    "PromptChaining-Alarms",
    env=env,
)
app.synth()
