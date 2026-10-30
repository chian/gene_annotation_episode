"""One bounded synthetic regression group; retain exact code identities."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FILES = ["gene_annotation_episode/literature_rate_storage.py", "gene_annotation_episode/literature_episodes.py",
    "tests/test_literature_cell_possession.py", "tests/test_literature_cell_possession_integration.py"]
SUITES = ["tests/test_literature_rate_storage.py", "tests/test_literature_rate_native_storage.py",
    "tests/test_literature_rate_episode_integration.py", "tests/test_literature_rate_native_integration.py",
    "tests/test_literature_optical_storage.py", "tests/test_literature_optical_integration.py",
    "tests/test_literature_cell_possession.py", "tests/test_literature_cell_possession_integration.py"]


def hashes(paths):
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}


def definitions(text):
    result = {}
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = ast.get_source_segment(text, node)
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + "." + child.name] = ast.get_source_segment(text, child)
    return result


def main():
    if (HERE / "FINAL_CHECKS_005.txt").exists() or (HERE / "FINAL_RECEIPT_005.json").exists():
        raise RuntimeError("Preserve existing final receipt; use a new numbered generation")
    baseline = json.loads((HERE / "BASELINE_SHA256.json").read_text())
    current = hashes(baseline)
    changed = [name for name in baseline if baseline[name] != current[name]]
    assert set(changed) == set(FILES[:2]), changed
    c7name = FILES[1]
    old_text = (HERE / "baseline" / c7name).read_text()
    new_text = (ROOT / c7name).read_text()
    old_defs, new_defs = definitions(old_text), definitions(new_text)
    assert set(old_defs) <= set(new_defs)
    changed_methods = [name for name in old_defs if old_defs[name] != new_defs[name]]
    assert set(changed_methods) == {"LiteratureEpisodes._rate_facts", "LiteratureEpisodes.validate_received_report"}
    patch = "".join("".join(difflib.unified_diff((HERE / "baseline" / name).read_text().splitlines(True),
        (ROOT / name).read_text().splitlines(True), fromfile="baseline/" + name, tofile=name)) for name in FILES[:2])
    (HERE / "IMPLEMENTATION_005.patch").write_text(patch)
    before = hashes([*baseline, *FILES[2:]])
    command = [sys.executable, "-m", "pytest", "-q", *SUITES]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    started = time.monotonic()
    with (HERE / "FINAL_CHECKS_005.txt").open("x") as output:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT)
    elapsed = time.monotonic() - started
    after = hashes(before)
    terminal = (HERE / "FINAL_CHECKS_005.txt").read_text().splitlines()[-1]
    receipt = {"generation": "005", "synthetic_only": True, "model_inference": False,
        "primary_source_reads": False, "command": command, "exit_code": completed.returncode,
        "elapsed_seconds": elapsed, "terminal_result": terminal,
        "source_hashes_before_and_after_equal": before == after, "owned_source_sha256": hashes(FILES),
        "changed_existing_literature_files": changed, "C7_changed_methods": changed_methods,
        "catalog_schemas_and_scientific_TASKs_unchanged": True,
        "optical_source_unchanged": baseline["gene_annotation_episode/literature_optical_storage.py"] ==
            after["gene_annotation_episode/literature_optical_storage.py"],
        "preserved_original_literature_files": len(baseline) - len(changed),
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "limits": ["Controlled synthetic fixtures and scripted shared-loop choices; no model-backed scientific claim.",
            "Separate C4 immutable synthetic-envelope fixture is not a detached worker launch.",
            "Historical pins/live runs and prior paper packets were not opened or mutated.",
            "No numerical formula, scientific TASK, typed schema, controller, observation or annotation-credit policy changes."]}
    (HERE / "FINAL_RECEIPT_005.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    assert before == after, "Shared source changed during verification"
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
