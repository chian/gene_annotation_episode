"""Group the failures recorded by ``tools/run_tests_by_home.py`` runs.

Reads the junit reports of one or more run directories and writes one row per
(test module, test, first line of the message) with the number of failing
cases and the directories they failed in. Long hex strings are masked so the
same cause groups together.

Usage:
    python tools/summarize_test_failures.py --output runs/<run>/failure_groups.tsv runs/<run>...
"""
from __future__ import annotations

import argparse
import csv
import re
import xml.etree.ElementTree as ElementTree
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HEX = re.compile(r"[0-9a-f]{12,}")
PARAMETERS = re.compile(r"\[.*")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("runs", nargs="+")
    arguments = parser.parse_args()
    counts: Counter[tuple[str, str, str, str]] = Counter()
    places: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for run in arguments.runs:
        for report in sorted((REPO / run / "junit").glob("*.xml")):
            for case in ElementTree.parse(report).getroot().iter("testcase"):
                for outcome in case:
                    if outcome.tag not in ("failure", "error"):
                        continue
                    message = HEX.sub("H", (outcome.get("message") or "").split("\n")[0])[:160]
                    package, _, module = case.get("classname", "").rpartition(".tests.")
                    if not package:
                        package, module = "", case.get("classname", "")
                    key = (outcome.tag, module.split(".")[0], PARAMETERS.sub("", case.get("name", "")), message)
                    counts[key] += 1
                    places[key].add(package.replace("gene_annotation_episode.episodic_workflow.root.", "") or "tests")
    with open(REPO / arguments.output, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(("cases", "directories", "kind", "test_module", "test", "message", "directory_list"))
        for key, count in sorted(counts.items(), key=lambda item: (item[0][1], item[0][2], item[0][3])):
            writer.writerow((count, len(places[key]), *key, ",".join(sorted(places[key]))))
    by_message: Counter[str] = Counter()
    for key, count in counts.items():
        by_message[key[3]] += count
    print(f"failing cases: {sum(counts.values())}; groups: {len(counts)}; distinct messages: {len(by_message)}")
    for message, count in by_message.most_common(40):
        print(f"{count:6d}  {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
