import pytest
from fastapi.testclient import TestClient

from app import claude, recap, runs
from app.main import app
from tests.test_runs import RUN, FakeTable

client = TestClient(app)


def test_facts_write_every_number_out():
    assert recap.facts(runs.Run.model_validate(RUN)) == [
        "When: Sunday morning",
        "Time: 44:16",
        "Distance: 8.2 km",
        "Average pace: 5:24 per km",
        "Fastest kilometre: kilometre 8, in 5:12",
        "Slowest kilometre: kilometre 5, in 5:36",
        "Average heart rate: 152 bpm",
        "Highest heart rate: 171 bpm",
        "Climbing: 42 m",
        "Temperature: 26°C",
        "Humidity: 65%",
    ]


def test_the_last_part_kilometre_is_never_the_fastest_kilometre():
    # The made-up run's last split is a quick 1:05 for the final 0.2 km.
    assert not any("1:05" in f for f in recap.facts(runs.Run.model_validate(RUN)))


def test_facts_for_a_treadmill_run_skip_the_weather():
    run = runs.Run.model_validate({**RUN, "indoor": True, "splits": None, "duration_s": 3723})
    run_facts = recap.facts(run)
    assert "Where: indoors, on a treadmill" in run_facts
    assert "Time: 1:02:03" in run_facts
    assert not any(f.startswith(("Temperature", "Humidity", "Fastest")) for f in run_facts)


@pytest.fixture
def stored_run(monkeypatch):
    table = FakeTable()
    table.get_item = lambda Key: {"Item": table.items[Key["start"]]} if Key["start"] in table.items else {}
    monkeypatch.setattr(runs, "_table", lambda: table)
    runs.add(runs.Run.model_validate(RUN))


class FakeRecapsTable:
    """Just enough of the recaps table: items kept per run in the order written; floats are refused."""

    def __init__(self):
        self.items = []

    def put_item(self, Item):
        assert not any(isinstance(v, float) for v in Item.values()), "DynamoDB needs Decimals"
        self.items.append(Item)

    def query(self, KeyConditionExpression, ScanIndexForward, Limit):
        start = KeyConditionExpression.get_expression()["values"][1]
        mine = sorted((i for i in self.items if i["run_start"] == start), key=lambda i: i["written"])
        return {"Items": (mine[::-1] if not ScanIndexForward else mine)[:Limit]}


@pytest.fixture
def recaps(monkeypatch):
    table = FakeRecapsTable()
    monkeypatch.setattr(recap, "_table", lambda: table)
    return table


@pytest.fixture
def claude_calls(monkeypatch):
    """Answers like Claude would, counting the calls: the first line says which call it was."""
    calls = []

    def fake_ask_for(system, prompt, output):
        assert "Distance: 8.2 km" in prompt
        calls.append(prompt)
        return recap.Recap(lines=[recap.Line(speaker="Minnie", text=f"Take {len(calls)}. Where was my BALL?")])

    monkeypatch.setattr(claude, "ask_for", fake_ask_for)
    return calls


def test_recap_of_the_latest_run(stored_run, recaps, claude_calls):
    body = client.get("/api/recap").json()
    assert body["lines"] == [{"speaker": "Minnie", "text": "Take 1. Where was my BALL?"}]
    assert body["run_start"] == body["run"]["start"] == RUN["start"]
    assert "Distance: 8.2 km" in body["facts"]
    spans = body["trace"]["spans"]
    assert [(s["name"], s["kind"]) for s in spans] == [
        ("Recap", "request"),
        ("Fetch the run", "data"),
        ("Write out the facts", "code"),
        ("Write the recap", "llm"),
    ]
    assert spans[3]["note"] == "Minnie and Maverick, 1 line, 6 words"
    assert all(s["end"] is not None for s in spans)  # saved after the whole request had finished


def test_a_saved_recap_is_shown_again_with_its_trace(stored_run, recaps, claude_calls):
    first = client.get("/api/recap").json()
    again = client.get("/api/recap", params={"start": RUN["start"]}).json()
    assert len(claude_calls) == 1
    assert again["lines"] == first["lines"]
    assert again["written"] == first["written"]
    assert again["trace"] == first["trace"]


def test_a_run_is_only_ever_recapped_once(stored_run, recaps, claude_calls):
    client.get("/api/recap")
    client.get("/api/recap", params={"fresh": "true"})  # the option "Another take" used is gone
    assert len(claude_calls) == 1
    assert len(recaps.items) == 1


def test_recap_of_a_missing_run(stored_run):
    assert client.get("/api/recap", params={"start": "2020-01-01T00:00:00+00:00"}).status_code == 404


def test_recap_when_claude_is_unavailable(stored_run, recaps, monkeypatch):
    def unavailable(system, prompt, output):
        raise claude.ClaudeUnavailable("Claude declined to answer that.")

    monkeypatch.setattr(claude, "ask_for", unavailable)
    response = client.get("/api/recap")
    assert response.status_code == 503
    assert response.json() == {"detail": "Claude declined to answer that."}
    assert recaps.items == []
