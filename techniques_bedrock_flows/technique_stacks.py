from aws_cdk import (
    App,
    Environment,
)
from stacks.model_invocation import FlowsModelInvocation
from stacks.prompt_templating import FlowsPromptTemplating
from stacks.sequential_chain import FlowsSequentialChain
from stacks.parallel_chain import FlowsParallelChain
from stacks.conditional_chain import FlowsConditionalChain
from stacks.map_chain import FlowsMapChain
import os


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
FlowsModelInvocation(
    app,
    "Techniques-Flows-ModelInvocation",
    env=env,
)
FlowsPromptTemplating(
    app,
    "Techniques-Flows-PromptTemplating",
    env=env,
)
FlowsSequentialChain(
    app,
    "Techniques-Flows-SequentialChain",
    env=env,
)
FlowsParallelChain(
    app,
    "Techniques-Flows-ParallelChain",
    env=env,
)
FlowsConditionalChain(
    app,
    "Techniques-Flows-ConditionalChain",
    env=env,
)
FlowsMapChain(
    app,
    "Techniques-Flows-Map",
    env=env,
)
app.synth()
