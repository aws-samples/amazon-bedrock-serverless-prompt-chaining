import streamlit as st

st.set_page_config(layout="wide")

st.title("Step Functions + Bedrock = ❤️")

"""
This site provides several demos to illustrate the potential for using Step Functions
to orchestrate complex Generative AI applications built on top of Bedrock through prompt chaining.
[Prompt chaining](https://docs.anthropic.com/claude/docs/prompt-chaining) is a technique for
building complex GenAI applications and accomplishing complex tasks with LLMs.
You construct well-known, well-defined subtasks as individual prompts and feed them to
the LLM in a pre-defined order or according to a set of defined rules.

Compared to some of the purpose-built prompt chaining frameworks we see emerging today, Step Functions
has several advantages out of the box as a way to chain together LLM prompts and agents.
* __Complex workflows__: The developer can declaratively define workflows using loops, map jobs, parallel jobs, conditions, and input/output manipulation.
* __Mixed chaining__: Workflows can chain together Lambda functions that act as LLM agents (for example, by calling Bedrock APIs)
along with more traditional bits of code in Lambda functions that don't talk to an LLM.
They can even chain LLM agents together with AWS service interactions, like querying data from Athena
or DynamoDB or putting messages onto an SQS queue.
* __Context passing__: Workflows can pass along well-defined, structured bits of context from step to step, such as previous LLM conversations and answers.
* __Reusable__: The agents in a workflow can be easily re-used in the same workflow or used to compose a new workflow, by simply re-using the same Lambda functions.
* __Observable__: The passed context and the inputs/outputs of each step are easily observable in the execution history of each executed workflow.
Metrics are emitted to CloudWatch for tracking execution success/failure and latency.
* __Retries__: Workflows can automatically retry individual steps in a workflow, improving the reliability of successfully
completing a workflow.
* __Serverless__: A serverless-first architecture removes the need for the developer to orchestrate scheduling compute for LLM agents when a new user request comes in.
* __Long running__: Workflows can be long-running (up to 1 year with up to 25,000 execution events).
Because the individual tasks are typically short-lived and can be automatically retried, the developer
does not need to build in any checkpointing to their system to deal with long-running applications dying in the middle.

In the context of this site, the following definitions apply:
* __Agent__ = A discrete set of one or more interactions with an LLM to accomplish a specific task.
This could be as simple as a single Bedrock InvokeModel API call with a static prompt;
it could be a single Bedrock API call that uses a prompt template to inject user input and other context into a more dynamic prompt;
or it could be a ReAct or Plan and Execute agent that enables the LLM to reason about a problem and invoke tools to call APIs and retrieve information related to the given prompt.  For this project, an agent runs entirely within a single Lambda function.
* __Workflow__ = A Step Functions state machine,
and more generally a statically-defined set of rules for the order in which agents run and what context they pass between each other.

The source code code for these demos can be found [here](https://github.com/aws-samples/amazon-bedrock-serverless-prompt-chaining).
"""
