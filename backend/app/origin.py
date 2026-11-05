import hmac

from app.secrets import read_secret

# CloudFront adds this header, with a secret value, to every request it forwards to the API. API Gateway also has
# its own public address that skips CloudFront (and so the site password); requests there don't have the header.
HEADER = "x-origin-verify"


def expected_secret() -> str | None:
    """The secret CloudFront sends. None when running locally (no secret set)."""
    return read_secret("ORIGIN_SECRET_ARN")


def from_cloudfront(given: str | None) -> bool:
    expected = expected_secret()
    return expected is None or (given is not None and hmac.compare_digest(given, expected))
