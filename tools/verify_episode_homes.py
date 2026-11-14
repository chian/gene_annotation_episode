"""Check that episode homes load, working from the leaves of the tree upward.

An episode home is a directory under ``episodic_workflow/root`` holding an
``episode.py``. A home's own modules are the Python files beneath it that are
not inside a nested home or a ``tests`` directory. Each home is imported in its
own interpreter so one home's failure cannot hide or cause another's.

Usage (through the launcher, output under its run directory):
    python tools/verify_episode_homes.py --output runs/<run>/homes.json [--only leaf|parent]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "gene_annotation_episode" / "episodic_workflow" / "root"
SKIPPED_PARTS = {"tests", "__pycache__", "fixtures"}
GUARD = re.compile(r" is not None and | is None or |\.get\([^()]+, [^()]+\)|getattr\([^()]+,[^()]+,[^()]+\)| if .* is None else ")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mixin_width(home: Path) -> int:
    """Largest number of base classes on any class declared in episode.py."""
    tree = ast.parse((home / "episode.py").read_text(encoding="utf-8"))
    return max((len(node.bases) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)), default=0)


def find_homes() -> list[Path]:
    return sorted(
        path.parent
        for path in ROOT.rglob("episode.py")
        if not SKIPPED_PARTS & set(path.relative_to(ROOT).parts)
    )


def nearest_home_above(path: Path, homes: set[Path]) -> Path | None:
    """The closest enclosing home of ``path``, not counting ``path`` itself."""
    for parent in path.parents:
        if parent in homes:
            return parent
        if parent == ROOT:
            return None
    return None


def own_modules(home: Path, homes: set[Path]) -> list[Path]:
    return [
        path
        for path in sorted(home.rglob("*.py"))
        if not SKIPPED_PARTS & set(path.relative_to(home).parts)
        and nearest_home_above(path, homes) == home
    ]


def module_name(path: Path) -> str:
    parts = path.relative_to(REPO).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def import_home(names: list[str]) -> dict[str, str]:
    failures = {}
    for name in names:
        try:
            importlib.import_module(name)
        except BaseException:  # a module may raise SystemExit at import
            failures[name] = traceback.format_exc(limit=-3).strip()
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--only", choices=("leaf", "parent"))
    parser.add_argument("--import-names", nargs="*", help="internal: import these modules and print failures")
    arguments = parser.parse_args()
    if arguments.import_names is not None:
        print(json.dumps(import_home(arguments.import_names)))
        return 0

    homes = find_homes()
    home_set = set(homes)
    copies: dict[str, int] = {}
    for path in ROOT.rglob("*.py"):
        if "__pycache__" not in path.parts:
            key = digest(path)
            copies[key] = copies.get(key, 0) + 1
    records = []
    for home in homes:
        children = [other for other in homes if nearest_home_above(other, home_set) == home]
        kind = "parent" if children else "leaf"
        if arguments.only and kind != arguments.only:
            continue
        modules = own_modules(home, home_set)
        names = [module_name(path) for path in modules]
        completed = subprocess.run(
            [sys.executable, __file__, "--output", arguments.output, "--import-names", *names],
            capture_output=True, text=True, cwd=REPO,
        )
        if completed.returncode == 0:
            failures = json.loads(completed.stdout.strip().splitlines()[-1])
        else:
            failures = {"<interpreter>": completed.stderr[-2000:]}
        records.append({
            "home": str(home.relative_to(ROOT)) if home != ROOT else ".",
            "kind": kind,
            "children": [str(child.relative_to(ROOT)) for child in children],
            "modules": len(names),
            "lines": sum(len(path.read_text(encoding="utf-8").splitlines()) for path in modules),
            "identical_copies": sum(1 for path in modules if copies[digest(path)] > 1),
            "mixin_width": mixin_width(home),
            "guard_sites": sum(len(GUARD.findall(path.read_text(encoding="utf-8"))) for path in modules),
            "import_failures": failures,
        })
    Path(arguments.output).write_text(json.dumps(records, indent=1))
    failed = [record for record in records if record["import_failures"]]
    print(f"homes checked: {len(records)}; with import failures: {len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
