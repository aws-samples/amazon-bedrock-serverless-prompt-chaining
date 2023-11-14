from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    aws_certificatemanager as acm,
    aws_cognito as cognito,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_elasticloadbalancingv2 as elb,
    aws_elasticloadbalancingv2_actions as elb_actions,
    aws_route53 as route53,
    aws_secretsmanager as secretsmanager,
    aws_stepfunctions as sfn,
)
from constructs import Construct


class WebappStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, parent_domain: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Set up load-balanced HTTPS Fargate service
        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=2,
        )

        domain_name = f"bedrock-serverless-prompt-chaining.{parent_domain}"
        hosted_zone = route53.HostedZone.from_lookup(
            self, "Zone", domain_name=parent_domain
        )
        certificate = acm.Certificate(
            self,
            "Cert",
            domain_name=domain_name,
            validation=acm.CertificateValidation.from_dns(hosted_zone=hosted_zone),
        )

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        image = ecs.ContainerImage.from_asset(".")

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "StreamlitService",
            cluster=cluster,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image, container_port=8501  # 8501 is the default Streamlit port
            ),
            public_load_balancer=True,
            domain_name=domain_name,
            domain_zone=hosted_zone,
            certificate=certificate,
        )

        # Configure Streamlit's health check
        fargate_service.target_group.configure_health_check(
            enabled=True, path="/_stcore/health", healthy_http_codes="200"
        )

        # Speed up deployments
        fargate_service.target_group.set_attribute(
            key="deregistration_delay.timeout_seconds",
            value="10",
        )

        # Grant access to start and query Step Functions exections
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
            workflow.grant_read(fargate_service.task_definition.task_role)
            workflow.grant_start_execution(fargate_service.task_definition.task_role)
            workflow.grant_task_response(fargate_service.task_definition.task_role)

        # Add Cognito for authentication
        cognito_domain_prefix = "bedrock-serverless-prompt-chaining-demo"
        user_pool = cognito.UserPool(
            self,
            "StreamlitUserPool",
            user_pool_name=cognito_domain_prefix,
            removal_policy=RemovalPolicy.DESTROY,
            account_recovery=cognito.AccountRecovery.NONE,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            sign_in_aliases=cognito.SignInAliases(email=True),
            self_sign_up_enabled=False,
            password_policy={
                "min_length": 12,
                "require_lowercase": False,
                "require_digits": False,
                "require_uppercase": False,
                "require_symbols": False,
            },
        )

        user_pool_domain = cognito.UserPoolDomain(
            self,
            "StreamlitUserPoolDomain",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=cognito_domain_prefix
            ),
        )

        user_pool_client = user_pool.add_client(
            "StreamlitAlbAppClient",
            user_pool_client_name="StreamlitAlbAuthentication",
            generate_secret=True,
            auth_flows=cognito.AuthFlow(user_password=True),
            o_auth=cognito.OAuthSettings(
                callback_urls=[
                    f"https://{domain_name}/oauth2/idpresponse",
                    f"https://{domain_name}",
                ],
                flows=cognito.OAuthFlows(authorization_code_grant=True),
                scopes=[cognito.OAuthScope.EMAIL],
                logout_urls=[f"https://{domain_name}"],
            ),
            prevent_user_existence_errors=True,
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
        )

        fargate_service.listener.add_action(
            "authenticate-rule",
            priority=1000,
            action=elb_actions.AuthenticateCognitoAction(
                next=elb.ListenerAction.forward(
                    target_groups=[fargate_service.target_group]
                ),
                user_pool=user_pool,
                user_pool_client=user_pool_client,
                user_pool_domain=user_pool_domain,
            ),
            conditions=[elb.ListenerCondition.host_headers([domain_name])],
        )

        # Let the load balancer talk to the OIDC provider
        lb_security_group = fargate_service.load_balancer.connections.security_groups[0]
        lb_security_group.add_egress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port(
                protocol=ec2.Protocol.TCP,
                string_representation="443",
                from_port=443,
                to_port=443,
            ),
            description="Outbound HTTPS traffic to the OIDC provider",
        )

        # Disallow accessing the load balancer URL directly
        cfn_listener: elb.CfnListener = fargate_service.listener.node.default_child
        cfn_listener.default_actions = [
            {
                "type": "fixed-response",
                "fixedResponseConfig": {
                    "statusCode": "403",
                    "contentType": "text/plain",
                    "messageBody": "This is not a valid endpoint!",
                },
            }
        ]
