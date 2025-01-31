from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_lambda_python_alpha as lambda_python,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct

from .util import (
    get_lambda_bundling_options,
    get_anthropic_claude_invoke_chain,
)


class TripPlannerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: suggest places to stay
        hotels_job = get_anthropic_claude_invoke_chain(
            self,
            "Suggest Hotels",
            prompt=sfn.JsonPath.format(
                """You are a world-class travel agent and an expert on travel to {}.
I am going on a weekend vacation to {}.
Please give me up to 5 suggestions for hotels for my vacation.""",
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
            ),
            max_tokens_to_sample=512,
            include_previous_conversation_in_prompt=False,
            pass_conversation=False,
        )

        # Agent #2: suggest places to eat
        restaurants_job = get_anthropic_claude_invoke_chain(
            self,
            "Suggest Restaurants",
            prompt=sfn.JsonPath.format(
                """You are a world-class travel agent and an expert on travel to {}.
I am going on a weekend vacation to {}.
Please give me suggestions for restaurants for my vacation, including up to 5 suggestions for breakfast, lunch, and dinner.""",
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
            ),
            max_tokens_to_sample=512,
            include_previous_conversation_in_prompt=False,
            pass_conversation=False,
        )

        # Agent #3: suggest places to visit
        activities_job = get_anthropic_claude_invoke_chain(
            self,
            "Suggest Activities",
            prompt=sfn.JsonPath.format(
                """You are a world-class travel agent and an expert on travel to {}.
I am going on a weekend vacation to {}.
Please give me up to 5 suggestions for activities to do or places to visit during my vacation.""",
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
            ),
            max_tokens_to_sample=512,
            include_previous_conversation_in_prompt=False,
            pass_conversation=False,
        )

        # Agent #4: form an itinerary
        itinerary_job = get_anthropic_claude_invoke_chain(
            self,
            "Create an Itinerary",
            prompt=sfn.JsonPath.format(
                """You are a world-class travel agent and an expert on travel to {}.
I am going on a weekend vacation to {} (arriving Friday, leaving Sunday).

You previously recommended these hotels, inside <hotels></hotels> XML tags.
<hotels>
{}
</hotels>

You previously recommended these restaurants, inside <restaurants></restaurants> XML tags.
<restaurants>
{}
</restaurants>

You previously recommended these activities, inside <activities></activities> XML tags.
<activities>
{}
</activities>

Please give me a daily itinerary for my three-day vacation, based on your previous recommendations.
The itinerary should include one hotel where I will stay for the duration of the vacation.
Each of the three days in the itinerary should have one activity, one restaurant for breakfast, one restaurant for lunch, and one restaurant for dinner.
Each entry in the itinerary should include a short description of your recommended hotel, activity, or restaurant.
The itinerary should be formatted in Markdown format.""",
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
                sfn.JsonPath.string_at("$$.Execution.Input.location"),
                sfn.JsonPath.string_at("$.hotels"),
                sfn.JsonPath.string_at("$.restaurants"),
                sfn.JsonPath.string_at("$.activities"),
            ),
            max_tokens_to_sample=512,
            include_previous_conversation_in_prompt=False,
            pass_conversation=False,
        )

        # Final step: Create the itinerary PDF
        pdf_bucket = s3.Bucket(
            self,
            "PdfBucket",
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="clean-up-itinerary-files",
                    expiration=Duration.days(1),
                    abort_incomplete_multipart_upload_after=Duration.days(1),
                    noncurrent_version_expiration=Duration.days(1),
                    noncurrent_versions_to_retain=5,
                )
            ],
        )

        weasyprint_layer = lambda_.LayerVersion.from_layer_version_arn(
            self,
            "WeasyprintLayer",
            layer_version_arn=ssm.StringParameter.value_for_string_parameter(
                self, parameter_name="WeasyprintLambdaLayer"
            ),
        )

        pdf_lambda = lambda_python.PythonFunction(
            self,
            "PdfCreator",
            runtime=lambda_.Runtime.PYTHON_3_12,  # This must be Python 3.12 for the Weasyprint layer
            entry="functions/trip_planner/pdf_creator",
            bundling=get_lambda_bundling_options(),
            environment={
                "PDF_BUCKET": pdf_bucket.bucket_name,
                "GDK_PIXBUF_MODULE_FILE": "/opt/lib/loaders.cache",
                "FONTCONFIG_PATH": "/opt/fonts",
                "XDG_DATA_DIRS": "/opt/lib",
            },
            timeout=Duration.seconds(30),
            memory_size=1024,
            layers=[weasyprint_layer],
        )

        pdf_bucket.grant_put(pdf_lambda)
        pdf_bucket.grant_read(pdf_lambda)

        pdf_job = tasks.LambdaInvoke(
            self,
            "Upload the Itinerary",
            lambda_function=pdf_lambda,
            output_path="$.Payload",
            payload=sfn.TaskInput.from_object(
                {
                    "location": sfn.JsonPath.string_at("$$.Execution.Input.location"),
                    "itinerary": sfn.JsonPath.string_at("$.model_outputs.response"),
                }
            ),
        )

        # Hook the agents together into a workflow that contains some parallel steps
        chain = (
            (
                sfn.Parallel(
                    self,
                    "Suggestions",
                    result_selector={
                        "hotels.$": "$[0].model_outputs.response",
                        "restaurants.$": "$[1].model_outputs.response",
                        "activities.$": "$[2].model_outputs.response",
                    },
                )
                .branch(hotels_job)
                .branch(restaurants_job)
                .branch(activities_job)
            )
            .next(itinerary_job)
            .next(pdf_job)
        )

        sfn.StateMachine(
            self,
            "TripPlannerWorkflow",
            state_machine_name="PromptChainDemo-TripPlanner",
            definition_body=sfn.DefinitionBody.from_chainable(chain),
            timeout=Duration.minutes(5),
        )
