import hmac
import os
from functools import cache

# CloudFront adds this header, with a secret value, to every request it forwards to the API. API Gateway also has
# its own public address that skips CloudFront (and so the site password); requests there don't have the header.
HEADER = "x-origin-verify"


@cache
def expected_secret() -> str | None:
    """The secret CloudFront sends, read once from Secrets Manager. None when running locally (no secret set)."""
    arn = os.environ.get("ORIGIN_SECRET_ARN")
    if not arn:
        return None
    import boto3  # provided by the Lambda runtime

    return boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"]


def from_cloudfront(given: str | None) -> bool:
    expected = expected_secret()
    return expected is None or (given is not None and hmac.compare_digest(given, expected))
