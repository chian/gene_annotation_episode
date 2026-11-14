"""Remove named test functions from test files.

Input is a tab-separated table with ``file`` and ``retire_test_names``
columns (comma-separated function names). Each named function is deleted
together with its decorators. A file whose named functions cannot all be
found is left untouched and reported.

Usage:
    python tools/remove_tests.py --table <verdicts.tsv> --report runs/<run>/removed.tsv
"""
from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def spans(tree: ast.Module, names: set[str]) -> dict[str, list[tuple[int, int]]]:
    found: dict[str, list[tuple[int, int]]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            found.setdefault(node.name, []).append((first, node.end_lineno or node.lineno))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--report", required=True)
    arguments = parser.parse_args()
    report = []
    with open(arguments.table, newline="") as handle:
        rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["verdict"] == "mixed"]
    for row in rows:
        path = REPO / row["file"]
        names = {name.strip().split("[")[0].split("::")[-1] for name in (row["retire_test_names"] or "").split(",") if name.strip()}
        if not path.is_file():
            report.append((row["file"], "file_missing", ""))
            continue
        if not names:
            report.append((row["file"], "no_names_listed", ""))
            continue
        text = path.read_text(encoding="utf-8")
        found = spans(ast.parse(text), names)
        missing = sorted(names - set(found))
        if missing:
            report.append((row["file"], "names_not_found", ",".join(missing)))
            continue
        lines = text.splitlines(keepends=True)
        doomed = set()
        for ranges in found.values():
            for first, last in ranges:
                doomed.update(range(first, last + 1))
        kept = [line for number, line in enumerate(lines, start=1) if number not in doomed]
        new_text = "".join(kept)
        try:
            ast.parse(new_text)
        except SyntaxError as error:
            report.append((row["file"], "would_not_parse", error.msg))
            continue
        path.write_text(new_text, encoding="utf-8")
        report.append((row["file"], "removed", ",".join(sorted(found))))
    with open(arguments.report, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(("file", "outcome", "detail"))
        writer.writerows(report)
    outcomes: dict[str, int] = {}
    for _, outcome, _ in report:
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
    print(outcomes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
