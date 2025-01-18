from aws_cdk import (
    Duration,
    Stack,
    aws_bedrock as bedrock,
    aws_sns as sns,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct


class HumanInputChain(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        get_advertisement = tasks.BedrockInvokeModel(
            self,
            "Generate Advertisement",
            # Choose the model to invoke
            model=bedrock.FoundationModel.from_foundation_model_id(
                self,
                "Model",
                bedrock.FoundationModelIdentifier.ANTHROPIC_CLAUDE_3_HAIKU_20240307_V1_0,
            ),
            # Provide the input to the model, including the templated prompt and inference properties
            body=sfn.TaskInput.from_object(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # The prompt is templated with the novel name as variable input.
                                    # The input to the Step Functions execution could be:
                                    # "Pride and Prejudice"
                                    "text": sfn.JsonPath.format(
                                        "Write a short advertisement for the book {}.",
                                        sfn.JsonPath.string_at("$$.Execution.Input"),
                                    ),
                                }
                            ],
                        }
                    ],
                    "max_tokens": 250,
                    "temperature": 1,
                }
            ),
        )

        # Send the generated advertisement to a SNS topic.
        # The human receiving the notification is expected to approve or reject the advertisement.
        # The human's decision should be sent to the Step Functions execution using the task token.
        # aws stepfunctions send-task-success --task-output "{\"decision\": \"yes\"}" --task-token "AQB8A..."
        topic = sns.Topic(
            self, "Topic", display_name="Human input topic for techniques example"
        )
        publish_ad_for_approval = tasks.SnsPublish(
            self,
            "Get Approval For Advertisement",
            topic=topic,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            message=sfn.TaskInput.from_object(
                {
                    "advertisement": sfn.JsonPath.string_at("$.Body.content[0].text"),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
            result_path="$.human_input",
        )

        extract_ad = sfn.Pass(
            self,
            "Extract Advertisement",
            parameters={
                "advertisement": sfn.JsonPath.string_at("$.Body.content[0].text"),
            },
        )

        handle_user_decision = (
            sfn.Choice(self, "Is Advertisement Approved?")
            .when(
                # Human approved the ad - finish the Step Functions execution
                sfn.Condition.string_equals("$.human_input.decision", "yes"),
                extract_ad,
            )
            .when(
                # Human rejected the ad - loop back to generate a new ad
                sfn.Condition.string_equals("$.human_input.decision", "no"),
                get_advertisement,
            )
            .otherwise(
                sfn.Fail(
                    self,
                    "Invalid Advertisement Approval Value",
                    cause="Unknown user choice (decision must be yes or no)",
                    error="Unknown user choice (decision must be yes or no)",
                )
            )
        )

        chain = get_advertisement.next(publish_ad_for_approval).next(
            handle_user_decision
        )

        sfn.StateMachine(
            self,
            "HumanInputExample",
            state_machine_name="Techniques-HumanInput",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(10),
        )
