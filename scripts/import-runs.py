#!/usr/bin/env python3
"""Turns an Apple Health export into a clean list of runs for The Couch Critics, and sends them to the lab.

    scripts/import-runs.py ~/Downloads/export.zip                    # just write runs.json and show a summary
    scripts/import-runs.py ~/Downloads/export.zip --send --staging   # ...and send them to staging.lab.ukdoshi.com
    scripts/import-runs.py ~/Downloads/export.zip --send             # ...and send them to lab.ukdoshi.com

Keeps only runs recorded by an Apple Watch (other apps write thinner copies of the same runs into Health), and
only the numbers a recap needs. GPS routes are never opened. Writes runs.json next to the export, so it stays
outside this repo, and prints a summary: counts only, never values. Sending is safe to repeat: the lab skips
runs it already has. The import key is read from AWS (profile "ukdoshi" unless AWS_PROFILE is set).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, iterparse

RUNNING = "HKWorkoutActivityTypeRunning"
METRES_PER = {"m": 1, "km": 1000, "mi": 1609.344}


def open_export(path: Path):
    if path.suffix == ".zip":
        archive = zipfile.ZipFile(path)
        name = next(n for n in archive.namelist() if n.endswith("/export.xml"))
        return archive.open(name)
    return path.open("rb")


def from_apple_watch(workout: Element) -> bool:
    device = workout.get("device", "")
    return "model:Watch" in device or "watch" in workout.get("sourceName", "").lower()


def iso(apple_date: str) -> str:
    """'2026-11-01 07:00:00 +1100' -> '2026-11-01T07:00:00+11:00'"""
    return datetime.strptime(apple_date, "%Y-%m-%d %H:%M:%S %z").isoformat()


def quantity(text: str | None) -> tuple[float, str] | None:
    """A value like '4200 cm' or '77 degF' as (4200.0, 'cm')."""
    match = re.match(r"(-?[\d.]+)\s*(\S*)", text or "")
    return (float(match.group(1)), match.group(2)) if match else None


def metres(text: str | None) -> int | None:
    q = quantity(text)
    return round(q[0] * {"cm": 0.01, "m": 1, "km": 1000, "ft": 0.3048}.get(q[1], 1)) if q else None


def celsius(text: str | None) -> float | None:
    q = quantity(text)
    return round((q[0] - 32) * 5 / 9 if q[1] == "degF" else q[0], 1) if q else None


def percent(text: str | None) -> int | None:
    q = quantity(text)
    return round(q[0] / 100 if q[0] > 100 else q[0]) if q else None  # some exports store 65% as "6500 %"


def to_run(workout: Element) -> dict:
    stats = {s.get("type", "").removeprefix("HKQuantityTypeIdentifier"): s for s in workout.iter("WorkoutStatistics")}
    meta = {m.get("key", "").removeprefix("HK"): m.get("value", "") for m in workout.iter("MetadataEntry")}
    minutes = float(workout.get("duration", 0)) * (1 if workout.get("durationUnit", "min") == "min" else 1 / 60)

    distance = stats.get("DistanceWalkingRunning")
    distance_m = (
        round(float(distance.get("sum")) * METRES_PER.get(distance.get("unit", "km"), 1000)) if distance is not None else None
    )
    heart = stats.get("HeartRate")
    heart_rate = (
        {k: round(float(heart.get(k))) for k in ("average", "minimum", "maximum") if heart.get(k)}
        if heart is not None
        else None
    )

    return {
        "start": iso(workout.get("startDate")),
        "time_zone": meta.get("TimeZone") or None,
        "duration_s": round(minutes * 60),
        "distance_m": distance_m,
        "heart_rate": heart_rate,
        "splits": splits(workout, distance_m),
        "elevation_gain_m": metres(meta.get("ElevationAscended")),
        "temperature_c": celsius(meta.get("WeatherTemperature")),
        "humidity_pct": percent(meta.get("WeatherHumidity")),
        "indoor": meta.get("IndoorWorkout") == "1",
    }


def splits(workout: Element, distance_m: int | None) -> dict | None:
    """The Watch marks each whole kilometre and each whole mile as 'segment' events, mixed together. Each split
    starts where the previous one in its own set ended, so following those chains separates the sets. Only the
    kilometre set is kept, and only when its length fits the distance, so recaps never mix units. Its last entry
    is the final part-kilometre."""
    segments = []
    for event in workout.iter("WorkoutEvent"):
        if event.get("type") == "HKWorkoutEventTypeSegment" and event.get("date"):
            factor = 60 if event.get("durationUnit", "min") == "min" else 1
            start = datetime.strptime(event.get("date"), "%Y-%m-%d %H:%M:%S %z").timestamp()
            segments.append((start, float(event.get("duration", 0)) * factor))
    if not segments or not distance_m:
        return None

    chains: list[list[tuple[float, float]]] = []
    for start, seconds in sorted(segments):
        # Join the set whose last split ended most recently before this one began (pauses only add gaps).
        ends = [(start - (c[-1][0] + c[-1][1]), c) for c in chains if c[-1][0] + c[-1][1] <= start + 2]
        if ends:
            min(ends, key=lambda e: e[0])[1].append((start, seconds))
        else:
            chains.append([(start, seconds)])

    for chain in chains:
        if abs(len(chain) - distance_m / 1000) <= 1:
            return {"unit": "km", "seconds": [round(s) for _, s in chain]}
    return None


def read_runs(path: Path) -> tuple[list[dict], Counter]:
    runs, skipped = {}, Counter()
    with open_export(path) as xml:
        events = iterparse(xml, events=("start", "end"))
        _, root = next(events)
        for event, elem in events:
            if event != "end" or elem.tag not in ("Workout", "Record", "ActivitySummary", "Correlation"):
                continue
            if elem.tag == "Workout" and elem.get("workoutActivityType") == RUNNING:
                if from_apple_watch(elem):
                    run = to_run(elem)
                    runs[run["start"]] = run  # one run per start time
                else:
                    skipped[elem.get("sourceName", "?")] += 1
            root.clear()  # the export can be hundreds of MB; drop each finished record to keep memory low
    return sorted(runs.values(), key=lambda r: r["start"]), skipped


def summary(runs: list[dict], skipped: Counter) -> None:
    print(f"Apple Watch runs kept: {len(runs)}")
    if runs:
        print(f"From {runs[0]['start'][:10]} to {runs[-1]['start'][:10]}")
    print("Skipped (copies from other apps):", ", ".join(f"{s}: {n}" for s, n in skipped.most_common()) or "none")
    print("\nHow many runs have each detail:")
    for field in ("distance_m", "heart_rate", "splits", "elevation_gain_m", "temperature_c", "humidity_pct", "time_zone"):
        print(f"  {field}: {sum(r[field] is not None for r in runs)}")
    print(f"  indoor runs: {sum(r['indoor'] for r in runs)}")
    units = Counter(r["splits"]["unit"] for r in runs if r["splits"])
    print("  split units:", ", ".join(f"{u}: {n}" for u, n in units.items()) or "none")


def send(runs: list[dict], staging: bool) -> None:
    site, secret = (
        ("staging.lab.ukdoshi.com", "ukdoshi-lab-staging/import-key") if staging else ("lab.ukdoshi.com", "ukdoshi-lab/import-key")
    )
    env = {**os.environ, "AWS_PROFILE": os.environ.get("AWS_PROFILE", "ukdoshi"), "AWS_REGION": "us-east-1"}
    key = subprocess.run(
        ["aws", "secretsmanager", "get-secret-value", "--secret-id", secret, "--query", "SecretString", "--output", "text"],
        env=env, capture_output=True, text=True,
    )
    if key.returncode != 0:
        sys.exit(f"Couldn't read the import key from AWS. Log in first: aws sso login --profile {env['AWS_PROFILE']}")

    added = already_had = 0
    for i in range(0, len(runs), 100):  # in batches, to keep each request small
        request = urllib.request.Request(
            f"https://{site}/api/runs",
            data=json.dumps({"runs": runs[i : i + 100]}).encode(),
            headers={"Content-Type": "application/json", "X-Import-Key": key.stdout.strip()},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        added += result["added"]
        already_had += result["already_had"]
    print(f"\nSent to {site}: {added} new, {already_had} already there")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("export", type=Path, help="export.zip (or export.xml) from the Health app")
    parser.add_argument("--send", action="store_true", help="send the runs to the lab (live unless --staging)")
    parser.add_argument("--staging", action="store_true", help="with --send: send to the staging copy")
    args = parser.parse_args()

    path = args.export.expanduser()
    runs, skipped = read_runs(path)
    out = path.with_name("runs.json")
    out.write_text(json.dumps({"runs": runs}, indent=2))
    summary(runs, skipped)
    print(f"\nWritten to {out} (outside the repo; contains your real run data)")
    if args.send:
        send(runs, args.staging)


if __name__ == "__main__":
    main()
