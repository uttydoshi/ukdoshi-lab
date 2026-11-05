import os
from functools import cache


@cache
def read_secret(env_var: str) -> str | None:
    """A Secrets Manager value, read once per Lambda start. The env var holds the secret's ARN or name;
    None when it isn't set (e.g. running locally without it)."""
    secret_id = os.environ.get(env_var)
    if not secret_id:
        return None
    import boto3  # provided by the Lambda runtime

    return boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]
