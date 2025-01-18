from aws_cdk import (
    App,
    Environment,
)
from stacks.model_invocation import ModelInvocation
from stacks.prompt_templating import PromptTemplating
from stacks.sequential_chain import SequentialChain
from stacks.parallel_chain import ParallelChain
from stacks.conditional_chain import ConditionalChain
from stacks.map_chain import MapChain
import os


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
ModelInvocation(
    app,
    "Techniques-Flows-ModelInvocation",
    env=env,
)
PromptTemplating(
    app,
    "Techniques-Flows-PromptTemplating",
    env=env,
)
SequentialChain(
    app,
    "Techniques-Flows-SequentialChain",
    env=env,
)
ParallelChain(
    app,
    "Techniques-Flows-ParallelChain",
    env=env,
)
ConditionalChain(
    app,
    "Techniques-Flows-ConditionalChain",
    env=env,
)
MapChain(
    app,
    "Techniques-Flows-Map",
    env=env,
)
app.synth()
