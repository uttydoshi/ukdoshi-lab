#!/usr/bin/env python3
"""Lists which details an Apple Health export holds for its runs: field names and counts only, never values.

    scripts/health-fields.py ~/Downloads/export.zip

Read-only. It reads the export where it is (keep it outside this repo), and never opens the GPS route files.
"""
import sys
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree.ElementTree import iterparse

RUNNING = "HKWorkoutActivityTypeRunning"


def open_export(path: Path):
    if path.suffix == ".zip":
        archive = zipfile.ZipFile(path)
        name = next(n for n in archive.namelist() if n.endswith("/export.xml"))
        return archive.open(name)
    return path.open("rb")


def short(name: str) -> str:
    for prefix in ("HKQuantityTypeIdentifier", "HKWorkoutEventType", "HK"):
        name = name.removeprefix(prefix)
    return name


def main(path: Path) -> None:
    runs = 0
    years = Counter()
    sources = Counter()
    fields = {"Workout details": Counter(), "Statistics": Counter(), "Extra details": Counter(), "Events": Counter()}
    segments_per_run = []
    with_route = 0

    with open_export(path) as xml:
        events = iterparse(xml, events=("start", "end"))
        _, root = next(events)
        for event, elem in events:
            if event != "end" or elem.tag not in ("Workout", "Record", "ActivitySummary", "Correlation"):
                continue
            if elem.tag == "Workout" and elem.get("workoutActivityType") == RUNNING:
                runs += 1
                years[elem.get("startDate", "")[:4]] += 1
                sources[elem.get("sourceName", "?")] += 1
                fields["Workout details"].update(k for k in elem.attrib if k not in ("sourceName", "sourceVersion", "device"))
                fields["Statistics"].update(short(s.get("type", "")) for s in elem.iter("WorkoutStatistics"))
                fields["Extra details"].update(short(m.get("key", "")) for m in elem.iter("MetadataEntry"))
                events = [short(e.get("type", "")) for e in elem.iter("WorkoutEvent")]
                fields["Events"].update(set(events))
                segments_per_run.append(events.count("Segment"))
                with_route += any(True for _ in elem.iter("WorkoutRoute"))
            root.clear()  # the export can be hundreds of MB; drop each finished record to keep memory low

    print(f"Runs found: {runs}")
    print("By year:", ", ".join(f"{y}: {n}" for y, n in sorted(years.items())))
    print("Recorded by:", ", ".join(f"{s}: {n}" for s, n in sources.most_common()))
    for title, counter in fields.items():
        print(f"\n{title} (how many runs have each):")
        for name, n in counter.most_common():
            print(f"  {name}: {n}")
    if segments_per_run:
        with_segments = [n for n in segments_per_run if n]
        print(f"\nRuns with splits (segment events): {len(with_segments)}")
    print(f"Runs with a GPS route (not opened): {with_route}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]).expanduser())
