from aws_cdk import (
    Duration,
    Stack,
    aws_stepfunctions as sfn,
)
from constructs import Construct

from .util import get_anthropic_claude_invoke_chain


class BlogPostStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: write book summary
        summary_job = get_anthropic_claude_invoke_chain(
            self,
            "Write a Summary",
            prompt=sfn.JsonPath.format(
                "Write a 1-2 sentence summary for the book {}.",
                sfn.JsonPath.string_at("$$.Execution.Input.novel"),
            ),
            include_previous_conversation_in_prompt=False,
        )

        # Agent #2: describe the plot
        plot_job = get_anthropic_claude_invoke_chain(
            self,
            "Describe the Plot",
            prompt=sfn.JsonPath.format(
                "Write a paragraph describing the plot of the book {}.",
                sfn.JsonPath.string_at("$$.Execution.Input.novel"),
            ),
        )

        # Agent #3: analyze key themes
        themes_job = get_anthropic_claude_invoke_chain(
            self,
            "Analyze Key Themes",
            prompt=sfn.JsonPath.format(
                "Write a paragraph analyzing the key themes of the book {}.",
                sfn.JsonPath.string_at("$$.Execution.Input.novel"),
            ),
        )

        # Agent #4: analyze writing style
        writing_style_job = get_anthropic_claude_invoke_chain(
            self,
            "Analyze Writing Style",
            prompt=sfn.JsonPath.format(
                "Write a paragraph discussing the writing style and tone of the book {}.",
                sfn.JsonPath.string_at("$$.Execution.Input.novel"),
            ),
        )

        # Agent #5: write the blog post
        blog_post_job = get_anthropic_claude_invoke_chain(
            self,
            "Write the Blog Post",
            prompt=sfn.JsonPath.format(
                (
                    'Combine your previous responses into a blog post titled "{} - A Literature Review" for my literature blog. '
                    "Start the blog post with an introductory paragraph at the beginning and a conclusion paragraph at the end. "
                    "The blog post should be five paragraphs in total."
                ),
                sfn.JsonPath.string_at("$$.Execution.Input.novel"),
            ),
            max_tokens_to_sample=1000,
            pass_conversation=False,
        )

        select_final_answer = sfn.Pass(
            self,
            "Select Final Answer",
            output_path="$.model_outputs.response",
        )

        # Hook the agents together into simple pipeline
        chain = (
            summary_job.next(plot_job)
            .next(themes_job)
            .next(writing_style_job)
            .next(blog_post_job)
            .next(select_final_answer)
        )

        sfn.StateMachine(
            self,
            "BlogPostWorkflow",
            state_machine_name="PromptChainDemo-BlogPost",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.seconds(300),
        )
