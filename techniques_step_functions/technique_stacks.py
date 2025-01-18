from aws_cdk import (
    App,
    Environment,
)
from stacks.model_invocation import ModelInvocation
from stacks.prompt_templating import PromptTemplating
from stacks.sequential_chain import SequentialChain
from stacks.parallel_chain import ParallelChain
from stacks.conditional_chain import ConditionalChain
from stacks.human_input_chain import HumanInputChain
from stacks.map_chain import MapChain
from stacks.aws_service_invocation import AwsServiceInvocationChain
from stacks.validation_chain import ValidationChain
import os


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
ModelInvocation(
    app,
    "Techniques-ModelInvocation",
    env=env,
)
PromptTemplating(
    app,
    "Techniques-PromptTemplating",
    env=env,
)
SequentialChain(
    app,
    "Techniques-SequentialChain",
    env=env,
)
ParallelChain(
    app,
    "Techniques-ParallelChain",
    env=env,
)
ConditionalChain(
    app,
    "Techniques-ConditionalChain",
    env=env,
)
HumanInputChain(
    app,
    "Techniques-HumanInput",
    env=env,
)
MapChain(
    app,
    "Techniques-Map",
    env=env,
)
AwsServiceInvocationChain(
    app,
    "Techniques-AwsServiceInvocation",
    env=env,
)
ValidationChain(
    app,
    "Techniques-Validation",
    env=env,
)
app.synth()
