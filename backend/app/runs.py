"""Runs from Apple Health (see scripts/import-runs.py), kept in a DynamoDB table keyed by start time."""

import hmac
import json
import os
from decimal import Decimal
from functools import lru_cache
from typing import Literal

import boto3
from botocore.exceptions import ClientError
from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field

from app.secrets import read_secret

TABLE_NAME = os.environ.get("RUNS_TABLE", "ukdoshi-lab-staging-runs")


class HeartRate(BaseModel):
    average: int
    minimum: int | None = None
    maximum: int | None = None


class Splits(BaseModel):
    unit: Literal["km"]
    seconds: list[int]


class Run(BaseModel):
    """One run: numbers only, never a GPS route."""

    start: str  # ISO 8601 with offset, e.g. 2026-11-01T07:00:00+11:00; also the run's id
    time_zone: str | None = None
    duration_s: int = Field(gt=0)
    distance_m: int | None = Field(default=None, gt=0)
    heart_rate: HeartRate | None = None
    splits: Splits | None = None
    elevation_gain_m: int | None = None
    temperature_c: float | None = None
    humidity_pct: int | None = None
    indoor: bool = False


class RunBatch(BaseModel):
    runs: list[Run] = Field(max_length=1000)


@lru_cache
def _table():
    return boto3.resource("dynamodb").Table(TABLE_NAME)


def add(run: Run) -> bool:
    """Stores a run unless one with the same start time is already there. True if it was new."""
    # DynamoDB wants Decimals, not floats.
    item = json.loads(run.model_dump_json(), parse_float=Decimal)
    try:
        _table().put_item(Item=item, ConditionExpression="attribute_not_exists(#s)", ExpressionAttributeNames={"#s": "start"})
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
    return True


def all_runs() -> list[Run]:
    """Every run, newest first. One person's runs are a few hundred items, so a scan is fine."""
    items, kwargs = [], {}
    while True:
        page = _table().scan(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            break
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return sorted((Run.model_validate(item) for item in items), key=lambda r: r.start, reverse=True)


def import_key_matches(x_import_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: only the import script (which reads the key from AWS) may add runs."""
    expected = read_secret("IMPORT_KEY_SECRET")
    if not expected or not x_import_key or not hmac.compare_digest(x_import_key, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Import key missing or wrong")
