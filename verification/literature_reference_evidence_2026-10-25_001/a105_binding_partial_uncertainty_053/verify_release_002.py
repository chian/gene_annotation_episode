"""Synthetic-only immutable release receipt; run once from the checkout root."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PATHS = (
    "gene_annotation_episode/literature_binding_interaction_calculations.py",
    "tests/test_literature_binding_interaction_calculations.py",
)
EXPECTED = (
    "26dffa5d6d9e4eb4b419f2243369344bebc6eee2c637a141edfaedb21cd3232e",
    "0ed1dd22a04fcb691e6ba848c029bf2343e4aac8781e281c2d2532450c493c79",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def load_tests():
    spec = importlib.util.spec_from_file_location("release053_tests", ROOT / PATHS[1])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    original = {path: (OUT / "baseline_001" / path).read_bytes() for path in PATHS}
    current = {path: (ROOT / path).read_bytes() for path in PATHS}
    assert [sha(original[path]) for path in PATHS] == list(EXPECTED)
    tests = load_tests()
    baseline = tests._baseline_module()
    comparisons = []
    for case_index, inputs in enumerate(tests._complete_baseline_cases()):
        for status in (None, "known", "estimated", "unknown"):
            model = None if status is None else tests.observation_model(inputs, status=status)
            old = baseline.populate_binding_interaction(inputs, model)
            new = tests.populate_binding_interaction(inputs, model)
            old_json = json.dumps(old, sort_keys=True, allow_nan=False)
            new_json = json.dumps(new, sort_keys=True, allow_nan=False)
            assert new == old and old_json == new_json
            comparisons.append({"case_index": case_index, "model_status": status,
                                "dictionary_equal": True, "serialized_bytes_equal": True,
                                "sha256": sha(old_json.encode()), "baseline_output": old,
                                "corrected_output": new})
    write_json("BASELINE_COMPARISON_002.json", {"synthetic_only": True,
               "complete_output_comparisons": len(comparisons), "comparisons": comparisons})

    old_functions = {n.name: n for n in ast.parse(original[PATHS[0]]).body if isinstance(n, ast.FunctionDef)}
    new_functions = {n.name: n for n in ast.parse(current[PATHS[0]]).body if isinstance(n, ast.FunctionDef)}
    tests.test_numeric_model_identity_and_relationship_code_is_unchanged_from_048()
    helpers = {}
    for name, node in old_functions.items():
        if name not in ("_uncertainty", "populate_binding_interaction"):
            old_dump, new_dump = ast.dump(node), ast.dump(new_functions[name])
            assert old_dump == new_dump
            helpers[name] = {"unchanged": True, "ast_sha256": sha(old_dump.encode())}
    normalized = deepcopy(new_functions["populate_binding_interaction"])
    additions = [n for n in normalized.body if isinstance(n, ast.Expr)
                 and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute)
                 and isinstance(n.value.func.value, ast.Name)
                 and n.value.func.value.id == "qualifications" and n.value.func.attr == "extend"
                 and len(n.value.args) == 1 and isinstance(n.value.args[0], ast.Call)
                 and isinstance(n.value.args[0].func, ast.Name)
                 and n.value.args[0].func.id == "_uncertainty_qualifications"]
    assert len(additions) == 1
    normalized.body.remove(additions[0])
    assert ast.dump(normalized) == ast.dump(old_functions["populate_binding_interaction"])
    write_json("AST_UNCHANGED_PROOF_002.json", {
        "all_old_functions_retained": set(old_functions) <= set(new_functions),
        "only_new_function": sorted(set(new_functions) - set(old_functions)),
        "unchanged_helpers": helpers,
        "populate_exact_after_removing_single_qualification_extend": True,
        "normalized_populate_ast_sha256": sha(ast.dump(normalized).encode()),
        "changed_validation_function": "_uncertainty",
    })

    command = [str(ROOT / ".venv/bin/python"), "-B", "-m", "pytest", "-p", "no:cacheprovider",
               "-q", "--tb=short", PATHS[1]]
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True)
    with (OUT / "TERMINAL_002.txt").open("x") as stream:
        stream.write("Command: " + " ".join(command) + "\n")
        stream.write(result.stdout)
        stream.write(result.stderr)
        stream.write("Exit code: " + str(result.returncode) + "\n")
    assert result.returncode == 0
    for path in PATHS:
        assert (ROOT / path).read_bytes() == current[path]
        assert (OUT / "baseline_001" / path).read_bytes() == original[path]
        destination = OUT / "snapshot_002" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(current[path])
    patch = "".join("".join(difflib.unified_diff(
        original[path].decode().splitlines(keepends=True), current[path].decode().splitlines(keepends=True),
        fromfile="a/" + path, tofile="b/" + path)) for path in PATHS)
    with (OUT / "FULL_PATCH_002.diff").open("x") as stream:
        stream.write(patch)
    artifacts = ["BASELINE_COMPARISON_002.json", "AST_UNCHANGED_PROOF_002.json",
                 "TERMINAL_002.txt", "FULL_PATCH_002.diff", "verify_release_002.py"]
    write_json("RELEASE_RECEIPT_002.json", {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthetic_only": True, "additive_correction_of_048": True,
        "production_files": {path: {"baseline_sha256": sha(original[path]),
            "released_sha256": sha(current[path]), "bytes": len(current[path]),
            "stable_through_terminal_run": True,
            "snapshot": "snapshot_002/" + path} for path in PATHS},
        "baseline_files_preserved_exact": True, "complete_output_comparisons": len(comparisons),
        "test_command": command, "test_exit_code": result.returncode,
        "test_result": result.stdout.strip().splitlines()[-1],
        "counts_overlap_not_additive": True,
        "artifact_sha256": {name: sha((OUT / name).read_bytes()) for name in artifacts},
        "source_papers_read": False, "native_adapter_run": False,
        "runtime_or_model_provider_run": False,
        "scope": "pure 048 partial-state correction; no new grader, axis, W05 or router",
    })
    print(json.dumps({"test_result": result.stdout.strip().splitlines()[-1],
                      "complete_output_comparisons": len(comparisons),
                      "released_sha256": {path: sha(current[path]) for path in PATHS}}))


if __name__ == "__main__":
    main()
