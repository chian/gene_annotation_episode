"""Classify what each test function actually checks, by reading its source.

For every ``test_*`` function the audit collects signals from the function
body, from the helper functions and fixtures in the same file that it reaches,
and from module-level setup. It never imports or runs a test.

Signals
    product   calls code imported from the application packages
    asserts   number of assert statements and ``pytest.raises`` blocks reached
    hash      hashes bytes or compares against a recorded 64-hex digest
    source    parses or reads program source text instead of running it
    place     asserts where code lives (``__module__``, ``__file__``, path exists)
    old_copy  compares against saved copies of earlier source
    old_runs  reads output of earlier runs (``runs/`` or ``verification/``)
    stub      replaces attributes with monkeypatch or mock

Usage:
    python tools/audit_tests.py --output runs/<run>/test_audit.tsv <test dir or file>...
"""
from __future__ import annotations

import argparse
import ast
import csv
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRODUCT_PACKAGES = ("gene_annotation_episode", "method_loop")
HEX_DIGEST = re.compile(r"^[0-9a-f]{64}$")
OLD_COPY = re.compile(r"\.py\.source|\.py\.txt|\.source\b|original[a-z_]*\.(txt|py|json)|_original\b|prechange|baseline")
OLD_RUNS = re.compile(r"(^|[\"'/ ])(runs|verification)/")
SOURCE_READ = re.compile(r"\.py$|\.py[\"']")
SIGNALS = ("hash", "source", "place", "old_copy", "old_runs", "stub")


def dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


class Facts:
    """Signals found in one function or in module-level code."""

    def __init__(self) -> None:
        self.signals: set[str] = set()
        self.asserts = 0
        self.product_calls = 0
        self.dynamic_imports = 0
        self.local_calls: set[str] = set()
        self.names: set[str] = set()


def collect(body: list[ast.stmt], product_names: set[str]) -> Facts:
    facts = Facts()
    for statement in body:
        for node in ast.walk(statement):
            if isinstance(node, ast.Assert):
                facts.asserts += 1
            elif isinstance(node, ast.Name):
                facts.names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if node.attr in ("__module__", "__file__", "__qualname__", "__code__"):
                    facts.signals.add("place")
                if node.attr in ("exists", "is_file", "is_dir"):
                    facts.signals.add("place")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                if HEX_DIGEST.match(text):
                    facts.signals.add("hash")
                if OLD_COPY.search(text):
                    facts.signals.add("old_copy")
                if OLD_RUNS.search(text):
                    facts.signals.add("old_runs")
                if SOURCE_READ.search(text):
                    facts.signals.add("source")
            elif isinstance(node, ast.Call):
                name = dotted(node.func)
                root = name.split(".")[0]
                leaf = name.split(".")[-1]
                if root == "hashlib" or leaf in ("sha256", "sha1", "md5"):
                    facts.signals.add("hash")
                if name in ("ast.parse", "inspect.getsource", "inspect.getsourcelines", "ast.unparse", "ast.dump"):
                    facts.signals.add("source")
                if leaf in ("setattr", "setitem", "delattr", "patch", "MagicMock", "Mock") and root in (
                        "monkeypatch", "mock", "unittest", "patch", "MagicMock", "Mock"):
                    facts.signals.add("stub")
                if leaf == "raises" and root == "pytest":
                    facts.asserts += 1
                if leaf == "import_module":
                    facts.dynamic_imports += 1
                if root in product_names:
                    facts.product_calls += 1
                if isinstance(node.func, ast.Name):
                    facts.local_calls.add(node.func.id)
    return facts


def product_bindings(tree: ast.Module) -> set[str]:
    """Names in the module that refer to application code."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in PRODUCT_PACKAGES:
            names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in PRODUCT_PACKAGES:
                    names.add((alias.asname or alias.name).split(".")[0])
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Call, ast.Attribute)):
            source = ast.unparse(node.value)
            if "import_module" in source and any(package in source for package in PRODUCT_PACKAGES + ("ROOT", "PREFIX", "PACKAGE")):
                for target in node.targets:
                    names.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
    return names


def functions(tree: ast.Module) -> dict[str, ast.FunctionDef]:
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.setdefault(node.name, node)
    return found


def reach(name: str, facts: dict[str, Facts], defs: dict[str, ast.FunctionDef]) -> Facts:
    """Union of a test's own facts with every local helper and fixture it reaches."""
    total = Facts()
    pending = [name]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen or current not in facts:
            continue
        seen.add(current)
        own = facts[current]
        total.signals |= own.signals
        total.asserts += own.asserts
        total.product_calls += own.product_calls
        total.dynamic_imports += own.dynamic_imports
        pending.extend(own.local_calls | own.names)
        pending.extend(argument.arg for argument in defs[current].args.args)
    return total


def verdict(total: Facts) -> str:
    uses_product = total.product_calls > 0 or total.dynamic_imports > 0
    pins = total.signals & {"hash", "source", "place", "old_copy", "old_runs"}
    if total.asserts == 0:
        return "no_check"
    if pins and not uses_product:
        return "pins_only"
    if pins:
        return "pins_and_calls"
    if uses_product:
        return "calls_product"
    return "no_product_call"


def audit_file(path: Path) -> list[dict]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = product_bindings(tree)
    defs = functions(tree)
    facts = {name: collect(node.body, names) for name, node in defs.items()}
    rows = []
    for name, node in defs.items():
        if not name.startswith("test"):
            continue
        total = reach(name, facts, defs)
        rows.append({
            "file": str(path.relative_to(REPO)),
            "test": name,
            "line": node.lineno,
            "lines": (node.end_lineno or node.lineno) - node.lineno + 1,
            "verdict": verdict(total),
            "asserts": total.asserts,
            "product_calls": total.product_calls,
            "dynamic_imports": total.dynamic_imports,
            **{signal: int(signal in total.signals) for signal in SIGNALS},
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("paths", nargs="+")
    arguments = parser.parse_args()
    files: list[Path] = []
    for raw in arguments.paths:
        path = (REPO / raw).resolve()
        candidates = [path] if path.is_file() else sorted(path.rglob("test_*.py"))
        files.extend(c for c in candidates if "fixtures" not in c.parts and "__pycache__" not in c.parts)
    rows: list[dict] = []
    unparsed = []
    for path in sorted(set(files)):
        try:
            rows.extend(audit_file(path))
        except SyntaxError as error:
            unparsed.append(f"{path.relative_to(REPO)}: {error.msg}")
    fields = ["file", "test", "line", "lines", "verdict", "asserts", "product_calls", "dynamic_imports", *SIGNALS]
    with open(arguments.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"test files: {len(set(files))}; test functions: {len(rows)}; unparsed files: {len(unparsed)}")
    for line in unparsed:
        print("  unparsed:", line)
    for name, count in Counter(row["verdict"] for row in rows).most_common():
        print(f"  {name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
