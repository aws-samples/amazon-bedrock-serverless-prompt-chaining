from aws_cdk import (
    aws_iam as iam,
    Stack,
    aws_bedrock as bedrock,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
from .inference_profile import InferenceProfile
import json


class ValidationChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        model = InferenceProfile(self, "Model", "global.anthropic.claude-haiku-4-5-20251001-v1:0")

        # Generate a JSON array of book titles and authors
        get_books_prompt = """IMPORTANT: Your response must be ONLY a JSON array. Do not use markdown code blocks, backticks, or any formatting. Start your response directly with the opening bracket.

Give me the titles and authors of 5 famous novels.
Your response should be formatted as a JSON array, with each element in the array containing a "title" key for the novel's title and an "author" key with the novel's author.
An example of a valid response is below, inside <example></example> XML tags.
<example>
[
    \{
        "title": "Title 1",
        "author": "Author 1"
    },
    {
        "title": "Title 2",
        "author": "Author 2"
    }
]
</example>
Do not include any other content other than the JSON object in your response. Do not include any XML tags in your response. Do not wrap the JSON in markdown code blocks or backticks."""

        get_books = tasks.BedrockInvokeModel(
            self,
            "Generate Books Array",
            model=model,
            # Provide the input to the model, including the prompt and inference properties
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": get_books_prompt,
                                }
                            ],
                        }
                    ],
                    "max_tokens": 512,
                    "temperature": 1,
                }
            ),
        )

        # Parse the model's response and validate that it conforms to a JSON schema with custom code
        initialize_parse_attempt_counter = sfn.Pass(
            self,
            "Initialize Parsing Error Counter",
            parameters={
                "parse_error_count": 0,
            },
            result_path="$.error_state",
        )

        parser_lambda = lambda_python.PythonFunction(
            self,
            "ModelResponseValidationFunction",
            runtime=lambda_.Runtime.PYTHON_3_13,
            entry="functions/parse_json_response",
            memory_size=256,
        )

        json_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author": {"type": "string"},
                },
                "required": ["title", "author"],
                "additionalProperties": False,
            },
            "minItems": 5,
            "maxItems": 5,
            "uniqueItems": True,
        }

        parse_model_response = tasks.LambdaInvoke(
            self,
            "Parse Model Response",
            lambda_function=parser_lambda,
            payload=sfn.TaskInput.from_object(
                {
                    "response_string": sfn.JsonPath.string_at("$.Body.content[0].text"),
                    "json_schema": json_schema,
                }
            ),
            result_selector={
                "novels": sfn.JsonPath.object_at("$.Payload"),
            },
        )

        # If the parser throws a parsing error, prompt the LLM to fix the error and try again
        handle_parsing_error = sfn.Pass(
            self,
            "Handle Parsing Error",
            parameters={
                "parsed_error": sfn.JsonPath.string_to_json(
                    sfn.JsonPath.string_at("$.caught_error.Cause")
                ),
                "parse_error_count": sfn.JsonPath.math_add(
                    sfn.JsonPath.number_at("$.error_state.parse_error_count"), 1
                ),
            },
            result_path="$.error_state",
        )

        fix_json = tasks.BedrockInvokeModel(
            self,
            "Fix JSON",
            model=model,
            # Provide the input to the model, including the prompt and inference properties
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The original prompt.
                                    "text": get_books_prompt,
                                },
                            ],
                        },
                        {
                            # The previous step's model output
                            "role": sfn.JsonPath.string_at("$.Body.role"),
                            "content": sfn.JsonPath.string_at("$.Body.content"),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # New prompt asking the model to fix the previous output
                                    "text": sfn.JsonPath.format(
                                        f"""I attempted to validate your response against my JSON schema, but received the following error inside <error></error> XML tags.
<error>
{{}}

{{}}
</error>

Here is my JSON schema, inside <schema></schema> XML tags:
<schema>
{json.dumps(json_schema, indent=2).replace("{", chr(92) + "{").replace("}", chr(92) + "}")}
</schema>

Please try to fix errors in the JSON response you gave previously and return a new JSON response that complies with the JSON schema.
Do NOT include any explanation, comments, apology, or markdown style code-back-ticks.
Remember - only return a valid JSON object.""",
                                        sfn.JsonPath.string_at(
                                            "$.error_state.parsed_error.errorType"
                                        ),
                                        sfn.JsonPath.string_at(
                                            "$.error_state.parsed_error.errorMessage"
                                        ),
                                    ),
                                }
                            ],
                        },
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
        )

        # Only try to fix the JSON a few times, then give up and fail
        attempt_to_fix_json = handle_parsing_error.next(
            sfn.Choice(self, "Too many attempts to fix model response?")
            .when(
                sfn.Condition.number_less_than("$.error_state.parse_error_count", 3),
                fix_json.next(parse_model_response),
            )
            .otherwise(sfn.Fail(self, "Fail - too many attempts"))
        )

        parse_model_response.add_catch(
            handler=attempt_to_fix_json,
            errors=[sfn.Errors.TASKS_FAILED],
            result_path="$.caught_error",
        )

        chain = get_books.next(initialize_parse_attempt_counter).next(
            parse_model_response
        )

        state_machine = sfn.StateMachine(
            self,
            "ValidationExample",
            state_machine_name="Techniques-Validation",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
        )

        # Add IAM permission for the foundation model
        state_machine.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[model.get_foundation_model_arn_pattern()],
            )
        )
