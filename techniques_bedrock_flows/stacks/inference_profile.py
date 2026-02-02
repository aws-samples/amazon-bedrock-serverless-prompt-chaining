from aws_cdk import Stack, aws_bedrock as bedrock
from constructs import Construct
import jsii


@jsii.implements(bedrock.IModel)
class InferenceProfile:
    def __init__(self, scope: Construct, id: str, inference_profile_id: str):
        self._inference_profile_id = inference_profile_id
        self._model_arn = f"arn:aws:bedrock:{Stack.of(scope).region}:{Stack.of(scope).account}:inference-profile/{inference_profile_id}"
        # Extract the foundation model ID from the inference profile ID
        # e.g., "global.anthropic.claude-haiku-4-5-20251001-v1:0" -> "anthropic.claude-haiku-4-5-20251001-v1:0"
        self._foundation_model_id = inference_profile_id.split(".", 1)[1] if "." in inference_profile_id else inference_profile_id

    @property
    @jsii.member(jsii_name="modelArn")
    def model_arn(self) -> str:
        return self._model_arn

    @property
    def model_id(self) -> str:
        return self._inference_profile_id

    def get_foundation_model_arn_pattern(self) -> str:
        """Returns the ARN pattern for IAM permissions that allows invoking the foundation model in any region."""
        return f"arn:aws:bedrock:*::foundation-model/{self._foundation_model_id}"
