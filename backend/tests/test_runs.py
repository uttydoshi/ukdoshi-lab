from decimal import Decimal

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from app import runs
from app.main import app

client = TestClient(app)

# A made-up run, never real data.
RUN = {
    "start": "2026-11-01T07:00:00+11:00",
    "time_zone": "Australia/Sydney",
    "duration_s": 2656,
    "distance_m": 8200,
    "heart_rate": {"average": 152, "minimum": 98, "maximum": 171},
    "splits": {"unit": "km", "seconds": [324, 318, 321, 330, 336, 327, 318, 312, 65]},  # last: the final 0.2 km
    "elevation_gain_m": 42,
    "temperature_c": 25.5,
    "humidity_pct": 65,
    "indoor": False,
}


class FakeTable:
    """Just enough of a DynamoDB table: put_item honours "not already there", and floats are refused."""

    def __init__(self):
        self.items = {}

    def put_item(self, Item, ConditionExpression, ExpressionAttributeNames):
        assert not any(isinstance(v, float) for v in Item.values()), "DynamoDB needs Decimals"
        if Item["start"] in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[Item["start"]] = Item

    def scan(self, **kwargs):
        return {"Items": list(self.items.values())}


@pytest.fixture
def table(monkeypatch):
    table = FakeTable()
    monkeypatch.setattr(runs, "_table", lambda: table)
    monkeypatch.setattr(runs, "read_secret", lambda name: "import-key")
    return table


def post(body, key="import-key"):
    return client.post("/api/runs", json=body, headers={"X-Import-Key": key} if key else {})


def test_import_needs_the_key(table):
    assert post({"runs": [RUN]}, key=None).status_code == 403
    assert post({"runs": [RUN]}, key="guess").status_code == 403
    assert table.items == {}


def test_import_adds_new_runs_and_skips_ones_already_there(table):
    assert post({"runs": [RUN]}).json() == {"added": 1, "already_had": 0}
    later = {**RUN, "start": "2026-11-03T06:30:00+11:00"}
    assert post({"runs": [RUN, later]}).json() == {"added": 1, "already_had": 1}
    assert table.items[RUN["start"]]["temperature_c"] == Decimal("25.5")


def test_import_refuses_bad_runs(table):
    assert post({"runs": [{**RUN, "duration_s": 0}]}).status_code == 422
    assert post({"runs": [{**RUN, "splits": {"unit": "mi", "seconds": [500]}}]}).status_code == 422
    assert table.items == {}


def test_list_runs_newest_first(table):
    older = {**RUN, "start": "2026-10-01T07:00:00+10:00"}
    post({"runs": [older, RUN]})
    listed = client.get("/api/runs").json()["runs"]
    assert [r["start"] for r in listed] == [RUN["start"], older["start"]]
    assert listed[0] == RUN
