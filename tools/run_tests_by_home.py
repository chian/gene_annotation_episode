"""Run each tests directory on its own, deepest directories first.

Leaves of the episode tree are run before their parents, and the top-level
``tests/`` directory last. One row per unit is appended to the results table
as soon as that unit finishes, so an interrupted run can resume. A unit is a
tests directory, or with ``--per-file`` a single test file, which keeps one
file's crash or slowness from hiding the results of its neighbours.

``--match`` restricts the run to directories whose repository-relative path
starts with one of the given prefixes, so separate launcher slots can each
take a different branch of the tree.

Every unit must have an expected duration before anything is launched.
``--expect`` names a tab-separated table with ``directory`` and ``seconds``
columns; a ``results.tsv`` from an earlier run has that form. A unit without
an expectation stops the run before it starts. After each unit the runner
rewrites ``<run>/progress.json`` with the measured-to-expected ratio so far
and the remaining time rescaled by that ratio, so whoever is waiting knows
when to come back and which unit is overdue. Expectations never stop a test.

Usage (through the launcher):
    python tools/run_tests_by_home.py --run-dir runs/<run> --expect <table> [--per-file] [--match <prefix>...] [--units-file <list>] [--shard K/N]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TREE = REPO / "gene_annotation_episode" / "episodic_workflow"
FIELDS = ("directory", "tests", "passed", "failed", "errors", "skipped", "seconds", "exit_code")


def test_directories() -> list[Path]:
    found = [
        path for path in TREE.rglob("tests")
        if path.is_dir() and "fixtures" not in path.parts and any(path.glob("test_*.py"))
    ]
    found.sort(key=lambda path: (-len(path.parts), str(path)))
    return found + [REPO / "tests"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--expect", required=True)
    parser.add_argument("--per-file", action="store_true")
    parser.add_argument("--match", nargs="+")
    parser.add_argument("--units-file", help="run exactly the units listed in this file, one path per line, in that order")
    parser.add_argument("--shard", default="0/1", help="K/N: take every Nth unit starting at K")
    arguments = parser.parse_args()
    run_dir = (REPO / arguments.run_dir).resolve()
    table = run_dir / "results.tsv"
    done: set[str] = set()
    if table.is_file():
        with open(table, newline="") as handle:
            done = {row["directory"] for row in csv.DictReader(handle, delimiter="\t")}
    else:
        with open(table, "w", newline="") as handle:
            csv.writer(handle, delimiter="\t").writerow(FIELDS)
    units: list[Path] = []
    if arguments.units_file:
        units = [REPO / line.strip() for line in (REPO / arguments.units_file).read_text().splitlines() if line.strip()]
        missing = [str(unit) for unit in units if not unit.exists()]
        if missing:
            raise SystemExit(f"{len(missing)} listed units do not exist, first: {missing[0]}")
    for directory in [] if arguments.units_file else test_directories():
        relative = str(directory.relative_to(REPO))
        if arguments.match and not any(relative.startswith(prefix) for prefix in arguments.match):
            continue
        units.extend(sorted(directory.glob("test_*.py")) if arguments.per_file else [directory])
    shard, shards = (int(part) for part in arguments.shard.split("/"))
    selected = [(index, unit, str(unit.relative_to(REPO))) for index, unit in enumerate(units) if index % shards == shard]
    with open(REPO / arguments.expect, newline="") as handle:
        expected = {row["directory"]: float(row["seconds"]) for row in csv.DictReader(handle, delimiter="\t")}
    unplanned = [name for _, _, name in selected if name not in expected]
    if unplanned:
        raise SystemExit(f"no expected duration for {len(unplanned)} units, first: {unplanned[0]}")
    measured: dict[str, float] = {}
    run_started = time.time()

    def report(current: str | None) -> None:
        planned_done = sum(expected[name] for name in measured)
        actual_done = sum(measured.values())
        ratio = actual_done / planned_done if planned_done else 1.0
        remaining = sum(expected[name] for _, _, name in selected if name not in measured and name not in done)
        overdue = sorted(((round(measured[name] / expected[name], 1), name) for name in measured
                          if measured[name] > 3 * expected[name] and measured[name] > 60), reverse=True)
        (run_dir / "progress.json").write_text(json.dumps({
            "units_selected": len(selected), "units_finished_this_run": len(measured),
            "units_finished_earlier": sum(1 for _, _, name in selected if name in done),
            "expected_seconds_total": round(sum(expected[name] for _, _, name in selected)),
            "measured_seconds_so_far": round(actual_done), "expected_seconds_for_those": round(planned_done),
            "measured_to_expected_ratio": round(ratio, 2),
            "remaining_seconds_as_planned": round(remaining), "remaining_seconds_rescaled": round(remaining * ratio),
            "expected_finish": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + remaining * ratio)),
            "current_unit": current, "current_unit_expected_seconds": expected.get(current) if current else None,
            "current_unit_started": time.strftime("%Y-%m-%d %H:%M:%S") if current else None,
            "run_started": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run_started)),
            "units_over_three_times_expected": overdue[:20],
        }, indent=1))

    # Tests must not reach outside services. A stored service credential under
    # the real home directory let one test log in to a provider, so each run
    # gets an empty home, and HTTP(S) requests to anything but this machine are
    # sent to a closed local port.
    isolated = dict(os.environ)
    (run_dir / "home").mkdir(exist_ok=True)
    isolated["HOME"] = str(run_dir / "home")
    for name in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        isolated[name] = "http://127.0.0.1:9"
    isolated["no_proxy"] = isolated["NO_PROXY"] = "localhost,127.0.0.1,::1"

    for index, unit, name in selected:
        if name in done:
            continue
        report(name)
        junit = run_dir / "junit" / f"{index:04d}.xml"
        junit.parent.mkdir(parents=True, exist_ok=True)
        log = run_dir / "logs" / f"{index:04d}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        base_temp = run_dir / "tmp" / f"{index:04d}"
        started = time.monotonic()
        with open(log, "w") as output:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", name, "-v", "-p", "no:cacheprovider",
                 f"--basetemp={base_temp}", f"--junitxml={junit}"],
                cwd=REPO, stdout=output, stderr=subprocess.STDOUT, env=isolated,
            )
        seconds = round(time.monotonic() - started, 1)
        measured[name] = seconds
        # The launcher's supervisor re-walks the run directory every two seconds,
        # so test scratch files left behind slow every later unit.
        shutil.rmtree(base_temp, ignore_errors=True)
        # Inside the launcher every unit shares <run>/local-resources. The axes'
        # LocalResources copies stamp different ledger versions and refuse each
        # other's ledger, so one unit's ledger must not outlive the unit.
        shutil.rmtree(run_dir / "local-resources", ignore_errors=True)
        counts = {"tests": "", "failures": "", "errors": "", "skipped": ""}
        if junit.is_file():
            suite = ElementTree.parse(junit).getroot()
            suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
            counts = {key: int(suite.get(key, 0)) for key in counts}
        passed = ""
        if counts["tests"] != "":
            passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
        with open(table, "a", newline="") as handle:
            csv.writer(handle, delimiter="\t").writerow(
                (name, counts["tests"], passed, counts["failures"], counts["errors"], counts["skipped"], seconds, completed.returncode))
        report(None)
        print(f"{name}: tests={counts['tests']} passed={passed} failed={counts['failures']} errors={counts['errors']} skipped={counts['skipped']} {seconds}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
