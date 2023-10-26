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
    add_bedrock_retries,
    get_bedrock_iam_policy_statement,
    get_lambda_bundling_options,
)


class TripPlannerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Agent #1: suggest places to stay
        hotels_lambda = lambda_python.PythonFunction(
            self,
            "HotelsAgent",
            entry="agents/trip_planner/hotels_agent",
            bundling=get_lambda_bundling_options(),
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        hotels_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        hotels_job = tasks.LambdaInvoke(
            self,
            "Suggest Hotels",
            lambda_function=hotels_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(hotels_job)

        # Agent #2: suggest places to eat
        restaurants_lambda = lambda_python.PythonFunction(
            self,
            "RestaurantsAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/trip_planner/restaurants_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        restaurants_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        restaurants_job = tasks.LambdaInvoke(
            self,
            "Suggest Restaurants",
            lambda_function=restaurants_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(restaurants_job)

        # Agent #3: suggest places to visit
        activities_lambda = lambda_python.PythonFunction(
            self,
            "ActivitiesAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/trip_planner/activities_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        activities_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        activities_job = tasks.LambdaInvoke(
            self,
            "Suggest Activities",
            lambda_function=activities_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(activities_job)

        # Agent #4: form an itinerary
        itinerary_lambda = lambda_python.PythonFunction(
            self,
            "ItineraryAgent",
            runtime=lambda_.Runtime.PYTHON_3_9,
            entry="agents/trip_planner/itinerary_agent",
            bundling=get_lambda_bundling_options(),
            timeout=Duration.seconds(60),
            memory_size=256,
        )
        itinerary_lambda.add_to_role_policy(get_bedrock_iam_policy_statement())

        itinerary_job = tasks.LambdaInvoke(
            self,
            "Create an Itinerary",
            lambda_function=itinerary_lambda,
            output_path="$.Payload",
        )
        add_bedrock_retries(itinerary_job)

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
            runtime=lambda_.Runtime.PYTHON_3_8,  # This must be Python 3.8 for the Weasyprint layer
            entry="agents/trip_planner/pdf_creator",
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
        )

        # Hook the agents together into a workflow that contains some parallel steps
        chain = (
            (
                sfn.Parallel(
                    self,
                    "Suggestions",
                    result_selector={
                        "location.$": "$[0].location",
                        "hotels.$": "$[0].hotels",
                        "restaurants.$": "$[1].restaurants",
                        "activities.$": "$[2].activities",
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
            timeout=Duration.seconds(300),
        )
