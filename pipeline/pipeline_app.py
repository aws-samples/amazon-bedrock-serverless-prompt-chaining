from aws_cdk import (
    App,
    Environment,
)
import os
from pipeline_stack import PipelineStack


app = App()
env = Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region="us-west-2")
PipelineStack(app, "PromptChainingPipeline", env=env)
app.synth()
