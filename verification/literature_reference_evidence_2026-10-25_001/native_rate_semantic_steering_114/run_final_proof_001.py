"""Retained synthetic engineering check; no scientific/model proof."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
PACKAGE = ROOT / "gene_annotation_episode"
OWNED = [PACKAGE / name for name in (
    "literature_experimental_prompt.py", "literature_reference_parent_prompt.py",
    "literature_episodes.py", "literature_rate_source_render.py")]
TESTS = [ROOT / "tests" / name for name in (
    "test_literature_rate_source_semantic_prompt.py",
    "test_literature_rate_source_semantic_integration.py")]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production():
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(PACKAGE.rglob("*.py"))}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


before = production()
write("PRODUCTION_PRE_001.json", before)
patches = []
for path in OWNED + TESTS:
    prior = OUT / (path.name + ".before")
    patches.extend(difflib.unified_diff(
        prior.read_text().splitlines(keepends=True) if prior.exists() else [],
        path.read_text().splitlines(keepends=True),
        fromfile=str(path.relative_to(ROOT)) + ".before" if prior.exists() else "/dev/null",
        tofile=str(path.relative_to(ROOT))))
(OUT / "FINAL_IMPLEMENTATION_002.patch").write_text("".join(patches))


def task_nodes(text):
    nodes = ast.parse(text).body
    return [ast.dump(n, include_attributes=False) for n in nodes
            if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_task")
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and "TASK" in t.id for t in n.targets))]


tasks = {}
for path in OWNED[:2]:
    old = task_nodes((OUT / (path.name + ".before")).read_text())
    new = task_nodes(path.read_text())
    assert old and old == new
    tasks[path.name] = {"task_builder_and_TASK_constants_AST_exact": True}
write("TASK_PRESERVATION_002.json", tasks)
code = pytest.main(["-q", *(str(p.relative_to(ROOT)) for p in TESTS),
    "--junitxml=" + str(OUT / "FINAL_TESTS_001.xml"), "--durations=5"])
after = production()
write("PRODUCTION_POST_001.json", after)
loaded = {}
for name, module in sorted(tuple(sys.modules.items())):
    raw = getattr(module, "__file__", None)
    if name.startswith("gene_annotation_episode") and raw:
        path = Path(raw).resolve()
        if path.suffix == ".py" and path.is_relative_to(ROOT):
            loaded[name] = {"path": str(path.relative_to(ROOT)), "sha256": digest(path)}
write("ACTUAL_IMPORTED_MODULES_001.json", loaded)
changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
owned_changed = [str(p.relative_to(ROOT)) for p in OWNED
                 if before.get(str(p.relative_to(ROOT))) != after.get(str(p.relative_to(ROOT))) ]
write("FINAL_PROOF_001.json", {"pytest_exit": int(code),
    "evidence_class": "constructed synthetic engineering delivery and first read-only replay; no scientific/model-backed proof",
    "owned_source_unchanged_during_tests": not owned_changed,
    "production_changes_during_tests": changes,
    "owned_files": {str(p.relative_to(ROOT)): digest(p) for p in OWNED + TESTS},
    "actual_imported_module_count": len(loaded), "paper_packets_read": False,
    "original_failed_fixture_logs_preserved": True})
if owned_changed:
    raise RuntimeError("Owned source changed during focused tests: " + repr(owned_changed))
raise SystemExit(code)
