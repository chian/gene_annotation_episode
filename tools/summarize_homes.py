"""Build the per-home summary table: test outcomes, retired and parked tests, and metrics.

Every episode home under ``episodic_workflow/root`` gets one row. A test file
is counted for the nearest home above it (so ``a101/library/tests`` counts for
``a101``); test files outside the tree are counted in a final ``(top-level
tests)`` row.

Inputs
    --homes     homes.json written by tools/verify_episode_homes.py
    --results   one or more run directories of tools/run_tests_by_home.py run
                per file; a later directory overrides an earlier one per file
    --retired   tab-separated file/test/reason table of retired tests
    --audit     the test audit verdict table (file, verdict, tests_total,
                tests_to_retire, ...); counted only where the retirement is
                visible on disk
    --parked    PARKED.tsv listing parked test files
    --collected a ``pytest --collect-only -q`` listing, used to size retired whole files

Usage:
    python tools/summarize_homes.py --homes <homes.json> --results <run>... --retired <tsv> \
        --audit <tsv> --parked <tsv> --collected <listing> --output <table.tsv>
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path("gene_annotation_episode/episodic_workflow/root")
OUTSIDE = "(top-level tests)"
COUNTS = ("test_files", "tests", "passed", "failed", "errors", "skipped", "no_report", "retired_tests", "parked_files")
METRICS = ("modules", "lines", "identical_copies", "mixin_width", "guard_sites")


def read_table(path: str) -> list[dict[str, str]]:
    with open(REPO / path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--homes", required=True)
    parser.add_argument("--results", nargs="+", required=True)
    parser.add_argument("--retired", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--parked", required=True)
    parser.add_argument("--collected", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()

    homes = json.loads((REPO / arguments.homes).read_text())
    names = {record["home"] for record in homes}

    def home_of(file: str) -> str:
        path = Path(file)
        if ROOT not in path.parents:
            return OUTSIDE
        for parent in path.relative_to(ROOT).parents:
            name = str(parent)
            if name in names:
                return name
        raise SystemExit(f"no home for {file}")

    rows: dict[str, Counter[str]] = defaultdict(Counter)

    latest: dict[str, dict[str, str]] = {}
    for run in arguments.results:
        for record in read_table(f"{run}/results.tsv"):
            if record["directory"].endswith(".py"):
                latest[record["directory"]] = record
    for file, record in latest.items():
        if not (REPO / file).is_file():
            continue  # retired after it was run
        row = rows[home_of(file)]
        row["test_files"] += 1
        if record["tests"] == "":
            row["no_report"] += 1
            continue
        for key in ("tests", "passed", "failed", "errors", "skipped"):
            row[key] += int(record[key])

    collected: Counter[str] = Counter()
    for line in (REPO / arguments.collected).read_text().splitlines():
        if "::" in line:
            collected[line.split("::")[0]] += 1

    for record in read_table(arguments.retired):
        whole = record["test"].strip() == "(whole file)"
        rows[home_of(record["file"])]["retired_tests"] += collected.get(record["file"], 1) if whole else 1
    for record in read_table(arguments.audit):
        present = (REPO / record["file"]).is_file()
        if record["verdict"] == "retire" and not present:
            rows[home_of(record["file"])]["retired_tests"] += int(record["tests_total"] or 0)
        elif record["verdict"] == "mixed" and present:
            names_removed = [name for name in record["retire_test_names"].split(",") if name.strip()]
            text = (REPO / record["file"]).read_text(encoding="utf-8")
            rows[home_of(record["file"])]["retired_tests"] += sum(
                1 for name in names_removed if f"def {name.strip().split('::')[-1]}(" not in text)
    for record in read_table(arguments.parked):
        rows[home_of(record["file"])]["parked_files"] += 1

    fields = ("home", "kind", "children", *COUNTS, *METRICS, "modules_failing_import")
    table = []
    for record in homes:
        row = rows.get(record["home"], Counter())
        table.append({
            "home": record["home"], "kind": record["kind"], "children": len(record["children"]),
            **{key: row[key] for key in COUNTS}, **{key: record[key] for key in METRICS},
            "modules_failing_import": len(record["import_failures"]),
        })
    outside = rows.get(OUTSIDE, Counter())
    table.append({"home": OUTSIDE, "kind": "", "children": "", **{key: outside[key] for key in COUNTS},
                  **{key: "" for key in METRICS}, "modules_failing_import": ""})
    with open(REPO / arguments.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(table)

    def total(key: str, chosen: list[dict]) -> int:
        return sum(int(row[key] or 0) for row in chosen)

    print(f"homes: {len(homes)}; rows written: {len(table)}")
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in table:
        head = row["home"].split("/")[0]
        groups[head if head.startswith("a1") else ("(shared root)" if row["home"] != OUTSIDE else OUTSIDE)].append(row)
    header = ("group", "homes", *COUNTS, "modules", "lines", "identical_copies", "guard_sites", "modules_failing_import")
    print("\t".join(header))
    for name in sorted(groups):
        chosen = groups[name]
        print("\t".join(str(value) for value in (
            name, len(chosen) if name != OUTSIDE else 0, *(total(key, chosen) for key in COUNTS),
            *(total(key, chosen) for key in ("modules", "lines", "identical_copies", "guard_sites", "modules_failing_import")))))
    print("\t".join(str(value) for value in (
        "TOTAL", len(homes), *(total(key, table) for key in COUNTS),
        *(total(key, table) for key in ("modules", "lines", "identical_copies", "guard_sites", "modules_failing_import")))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
