from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_sns as sns,
)
from constructs import Construct


class AlarmsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        alarms = []

        for name_suffix in [
            "BlogPost",
            "TripPlanner",
            "StoryWriter",
            "MoviePitch",
            "MealPlanner",
        ]:
            workflow = sfn.StateMachine.from_state_machine_name(
                self, f"{name_suffix}Workflow", f"PromptChainDemo-{name_suffix}"
            )

            alarm = cloudwatch.Alarm(
                self,
                f"{name_suffix}WorkflowFailures",
                alarm_name=f"PromptChainDemo-{name_suffix}-Workflow-Failures",
                threshold=1,
                evaluation_periods=1,
                metric=workflow.metric_failed(statistic=cloudwatch.Stats.SUM),
            )
            alarms.append(alarm)

        composite_alarm = cloudwatch.CompositeAlarm(
            self,
            f"CompositeAlarm",
            composite_alarm_name="PromptChainDemo-Composite-Alarm",
            alarm_rule=cloudwatch.AlarmRule.any_of(*alarms),
        )

        topic = sns.Topic(
            self,
            "PromptChainDemo-Notifications",
            topic_name="bedrock-serverless-prompt-chaining-notifications",
        )
        topic.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["SNS:Publish"],
                principals=[
                    iam.ServicePrincipal("codestar-notifications.amazonaws.com")
                ],
                resources=[
                    Stack.of(self).format_arn(
                        service="sns",
                        resource="bedrock-serverless-prompt-chaining-notifications",
                    )
                ],
            )
        )
        composite_alarm.add_alarm_action(cw_actions.SnsAction(topic))
