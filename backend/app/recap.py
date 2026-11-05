"""The Couch Critics: Minnie and Maverick review a run, using only numbers the lab has written out for them."""

import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import Literal

import boto3
from boto3.dynamodb.conditions import Key
from pydantic import BaseModel

from app import claude, trace
from app.runs import Run

TABLE_NAME = os.environ.get("RECAPS_TABLE", "ukdoshi-lab-staging-recaps")

SYSTEM = """\
You write "The Couch Critics": short, funny run reviews by Utty's two toy poodles, who stayed home on the couch \
while Utty went for a run. The review is a chat between the two dogs. Use Australian/British spelling.

Minnie (she) is the boss. Bossy, extremely expressive and caring, and she dominates Maverick. Her ball \
obsession is off the charts and is her main joke: she brings the ball, stares at it, and demands it be thrown. \
She's a fussy eater who never eats before Maverick has. She wants cuddles when Utty comes home, but has a limit \
and runs off once she's had enough. She reads the stats and demands better.

Maverick (he) is the couch potato. Lazy, loyal, cheeky and a bit dim. He won't leave the couch even when \
everyone's outside, and after any walk he doesn't move for hours. He's jealous of any attention Minnie gets and \
pushes her off laps. He would lick a human forever, and pats are never enough.

Both are very loyal. They love rubs, pats, walks and humans, and get noisy when they see other dogs. When Utty \
puts runners on, they jump up hoping to come. When Utty gets back, they lick and ask for pats. They play \
together, sometimes share a bed, and growl at each other without ever hurting each other.

Rules for every review:
1. Only Minnie says numbers about the run, and only numbers from the run facts, written exactly as they appear \
there (for example "8.2 km" or "44:16"). Never work out, convert or round a number yourself.
2. Maverick never says a number, in digits or in words. He can be confused by Minnie's numbers \
("8.2 what? Treats?").
3. Each dog stays in character.
4. Playful, never shaming. No medical or health advice, and no judgement of whether a heart rate is good or bad, \
even if it looks unusual.
5. Four to six lines in total, starting with Minnie. Each line is one or two short sentences, to fit a phone \
screen. Use a few of the facts, not all of them.

The tone, as an example:
Minnie: You put the runners on. I brought you the BALL. You stepped OVER it. 8.2 km in 44:16, and not one \
throw. Unacceptable.
Maverick: I didn't get up. I'm still on the couch. I'm tired just hearing about it."""


class Line(BaseModel):
    speaker: Literal["Minnie", "Maverick"]
    text: str


class Recap(BaseModel):
    lines: list[Line]


class SavedRecap(BaseModel):
    """A recap as stored: what the dogs said, the facts they were given, and the trace of how it was written."""

    run_start: str
    written: str  # when, in UTC; with run_start, the recap's id
    facts: list[str]
    lines: list[Line]
    model: str
    trace: trace.Trace


def clock(seconds: int) -> str:
    """2656 -> '44:16', 3723 -> '1:02:03'"""
    hours, rest = divmod(round(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02}:{secs:02}" if hours else f"{minutes}:{secs:02}"


def part_of_day(hour: int) -> str:
    return "early morning" if hour < 7 else "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"


def facts(run: Run) -> list[str]:
    """The run as short facts, with every number already written the way the dogs must say it."""
    local = datetime.fromisoformat(run.start)
    lines = [f"When: {local:%A} {part_of_day(local.hour)}", f"Time: {clock(run.duration_s)}"]
    if run.indoor:
        lines.append("Where: indoors, on a treadmill")
    if run.distance_m:
        km = run.distance_m / 1000
        lines.append(f"Distance: {km:.1f} km")
        lines.append(f"Average pace: {clock(run.duration_s / km)} per km")
    times = run.splits.whole(run.distance_m) if run.splits and run.distance_m else []
    if len(times) > 1:
        fastest, slowest = times.index(min(times)), times.index(max(times))
        lines.append(f"Fastest kilometre: kilometre {fastest + 1}, in {clock(times[fastest])}")
        lines.append(f"Slowest kilometre: kilometre {slowest + 1}, in {clock(times[slowest])}")
    if run.heart_rate:
        lines.append(f"Average heart rate: {run.heart_rate.average} bpm")
        if run.heart_rate.maximum:
            lines.append(f"Highest heart rate: {run.heart_rate.maximum} bpm")
    if run.elevation_gain_m:
        lines.append(f"Climbing: {run.elevation_gain_m} m")
    if run.temperature_c is not None and not run.indoor:
        lines.append(f"Temperature: {round(run.temperature_c)}°C")
    if run.humidity_pct is not None and not run.indoor:
        lines.append(f"Humidity: {run.humidity_pct}%")
    return lines


def write(run: Run) -> tuple[list[str], Recap]:
    with trace.step("Write out the facts", "code") as span:
        run_facts = facts(run)
        span.note = f"{len(run_facts)} facts, every number written out in advance"
    prompt = "Run facts:\n" + "\n".join(f"- {f}" for f in run_facts) + "\n\nWrite the review."
    with trace.step("Write the recap", "llm") as span:
        review = claude.ask_for(SYSTEM, prompt, Recap)
        words = sum(len(line.text.split()) for line in review.lines)
        lines = len(review.lines)
        span.note = f"Minnie and Maverick, {lines} line{'' if lines == 1 else 's'}, {words} words"
    return run_facts, review


@lru_cache
def _table():
    return boto3.resource("dynamodb").Table(TABLE_NAME)


def save(run: Run, run_facts: list[str], review: Recap, recap_trace: trace.Trace) -> SavedRecap:
    saved = SavedRecap(
        run_start=run.start,
        written=datetime.now(UTC).isoformat(timespec="milliseconds"),
        facts=run_facts,
        lines=review.lines,
        model=claude.MODEL,
        trace=recap_trace,
    )
    # The trace is stored as JSON text, so its timings needn't become DynamoDB Decimals.
    item = saved.model_dump(mode="json") | {"trace": recap_trace.model_dump_json()}
    _table().put_item(Item=item)
    return saved


def latest(run_start: str) -> SavedRecap | None:
    """The run's newest recap, if it has one."""
    items = _table().query(KeyConditionExpression=Key("run_start").eq(run_start), ScanIndexForward=False, Limit=1)
    if not items["Items"]:
        return None
    item = items["Items"][0]
    return SavedRecap.model_validate(item | {"trace": trace.Trace.model_validate_json(item["trace"])})
