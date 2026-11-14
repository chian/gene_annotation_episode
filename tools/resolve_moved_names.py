"""Repair ``from gene_annotation_episode... import name`` statements whose
module or name has moved, by finding the one place each name is now defined.

A name is only re-pointed when exactly one candidate module defines it in the
preferred scope (the importing file's own axis first, then the shared root
modules). Anything ambiguous or not found is left untouched and reported, so
nothing is guessed.

Usage:
    python tools/resolve_moved_names.py --report runs/<run>/resolved.tsv <dir or file>...
"""
from __future__ import annotations

import argparse
import ast
import csv
import re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PACKAGE = REPO / "gene_annotation_episode"
ROOT = PACKAGE / "episodic_workflow" / "root"
AXIS = re.compile(r"^a1\d\d$")
SKIP = {"tests", "__pycache__", "fixtures"}


def dotted(path: Path) -> str:
    parts = path.relative_to(REPO).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def module_path(name: str) -> Path | None:
    base = REPO.joinpath(*name.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def bound_names(path: Path, cache: dict[Path, tuple[set[str], set[str]]]) -> tuple[set[str], set[str]]:
    """(names defined here, names merely imported here) at module top level."""
    if path not in cache:
        defined: set[str] = set()
        imported: set[str] = set()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            tree = ast.Module(body=[], type_ignores=[])
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    defined.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imported.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        cache[path] = (defined, imported)
    return cache[path]


def build_index(cache) -> dict[str, dict[str, list[Path]]]:
    """scope ('root' or an axis name) -> name -> modules defining it."""
    index: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for path in sorted(ROOT.rglob("*.py")):
        relative = path.relative_to(ROOT).parts
        if SKIP & set(relative):
            continue
        scope = relative[0] if AXIS.match(relative[0]) else "root"
        # Only modules directly in a scope or its library are shared definitions;
        # episode homes keep their own private names.
        depth_ok = len(relative) == 1 or (scope == "root" and relative[0] == "library" and len(relative) == 2) or (
            scope != "root" and (len(relative) == 2 or (relative[1] == "library" and len(relative) == 3)))
        if not depth_ok:
            continue
        for name in bound_names(path, cache)[0]:
            index[scope][name].append(path)
    for path in sorted(PACKAGE.glob("*.py")):
        for name in bound_names(path, cache)[0]:
            index["root"][name].append(path)
    return index


def choose(candidates: list[Path], old_module: str) -> Path | None:
    if len(candidates) == 1:
        return candidates[0]
    stem = old_module.split(".")[-1]
    same = [path for path in candidates if path.stem == stem]
    return same[0] if len(same) == 1 else None


def repair(path: Path, index, cache, report) -> None:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    relative = path.relative_to(REPO).parts
    axis = next((part for part in relative if AXIS.match(part)), None)
    lines = text.splitlines(keepends=True)
    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
            continue
        if node.module.split(".")[0] != "gene_annotation_episode" or node.module == "gene_annotation_episode":
            continue
        source = module_path(node.module)
        available = set().union(*bound_names(source, cache)) if source else set()
        groups: dict[str, list[str]] = defaultdict(list)
        changed = False
        unresolved = []
        for alias in node.names:
            item = alias.name + (f" as {alias.asname}" if alias.asname else "")
            if alias.name == "*" or alias.name in available:
                groups[node.module].append(item)
                continue
            if source and module_path(node.module + "." + alias.name):
                groups[node.module].append(item)  # a submodule import
                continue
            target = None
            for scope in ([axis] if axis else []) + ["root"]:
                candidates = index[scope].get(alias.name, [])
                if candidates:
                    target = choose(candidates, node.module)
                    break
            if target is None:
                unresolved.append(alias.name)
                groups[node.module].append(item)
            else:
                groups[dotted(target)].append(item)
                changed = True
        for name in unresolved:
            report.append((str(path.relative_to(REPO)), "unresolved", node.module, name))
        if changed:
            indent = re.match(r"\s*", lines[node.lineno - 1]).group(0)
            replacement = "".join(f"{indent}from {module} import {', '.join(items)}\n" for module, items in groups.items())
            edits.append((node.lineno, node.end_lineno, replacement))
            report.append((str(path.relative_to(REPO)), "repointed", node.module, ",".join(sorted(groups))))
    if not edits:
        return
    for first, last, replacement in sorted(edits, reverse=True):
        lines[first - 1:last] = [replacement]
    new_text = "".join(lines)
    try:
        ast.parse(new_text)
    except SyntaxError:
        report.append((str(path.relative_to(REPO)), "would_not_parse", "", ""))
        return
    path.write_text(new_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("paths", nargs="+")
    arguments = parser.parse_args()
    cache: dict = {}
    index = build_index(cache)
    report: list[tuple[str, str, str, str]] = []
    for raw in arguments.paths:
        base = (REPO / raw).resolve()
        files = [base] if base.is_file() else sorted(base.rglob("*.py"))
        for path in files:
            if "__pycache__" in path.parts or "fixtures" in path.parts:
                continue
            repair(path, index, cache, report)
    with open(arguments.report, "w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(("file", "outcome", "old_module", "detail"))
        writer.writerows(report)
    counts: dict[str, int] = defaultdict(int)
    for _, outcome, _, _ in report:
        counts[outcome] += 1
    print(dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
