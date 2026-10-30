"""Capture only reviewed native-rate changes over the immutable 023 runtime."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "verification/literature_reference_evidence_2026-10-25_001"
ORIGIN = EVIDENCE / "literature_model_run_023/pin_001"
DESTINATION = EVIDENCE / "literature_model_run_024/pin_001"
EXPECTED_ORIGIN = "4f2233d6bae4e5078a157a514051b41fe320a4f43db6551efc95a89ff2a95ef7"
OWNED = {
    "gene_annotation_episode/literature_experimental_contracts.py",
    "gene_annotation_episode/literature_rate_calculations.py",
    "gene_annotation_episode/literature_rate_storage.py",
    "gene_annotation_episode/literature_episodes.py",
    "gene_annotation_episode/literature_experimental_prompt.py",
    "gene_annotation_episode/literature_rate_native_inputs.py",
    "tests/test_literature_parent_population_information.py",
    "tests/test_literature_rate_native_inputs.py",
    "tests/test_literature_rate_native_storage.py",
    "tests/test_literature_rate_native_integration.py",
}
NEW_TESTS = {name for name in OWNED if name.startswith("tests/")}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def verify(directory, manifest):
    paths = set()
    for row in manifest["files"]:
        relative = Path(row["pin_relative_path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) not in paths
        paths.add(str(relative))
        path = directory / relative
        assert not path.is_symlink()
        assert path.stat().st_size == row["size"] and sha(path) == row["sha256"], relative
    assert paths == {str(p.relative_to(directory)) for p in directory.rglob("*")
                     if p.is_file() and p != directory / "SOURCE_MANIFEST.json"}


def test_dependencies():
    pending, found = list(NEW_TESTS), set()
    while pending:
        relative = pending.pop()
        if relative in found:
            continue
        found.add(relative)
        tree = ast.parse((ROOT / relative).read_text())
        for node in ast.walk(tree):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                     else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if name.startswith("test_") and (ROOT / "tests" / (name + ".py")).is_file():
                    pending.append("tests/" + name + ".py")
    return found


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-hashes", type=Path, required=True)
    args = parser.parse_args()
    reviewed_path = args.reviewed_hashes.resolve()
    reviewed = json.loads(reviewed_path.read_bytes())
    assert set(reviewed) == OWNED
    origin_manifest = ORIGIN / "SOURCE_MANIFEST.json"
    assert sha(origin_manifest) == EXPECTED_ORIGIN
    prior = json.loads(origin_manifest.read_bytes())
    verify(ORIGIN, prior)
    old = {row["pin_relative_path"]: row for row in prior["files"]}
    for relative, row in reviewed.items():
        assert sha(ROOT / relative) == row["after"], relative
        assert old.get(relative, {}).get("sha256") == row["before"], relative
    tests = test_dependencies()
    for relative in tests - OWNED:
        assert relative in old, ("unreviewed_new_test_dependency", relative)
        assert sha(ROOT / relative) == old[relative]["sha256"], relative

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.mkdir(exist_ok=False)
    for relative in old:
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ORIGIN / relative, target)
    changes = []
    for relative in sorted(OWNED):
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        assert sha(target) == reviewed[relative]["after"]
        changes.append({"path": relative, "before": reviewed[relative]["before"],
                        "after": sha(target)})
    shutil.copyfile(origin_manifest, DESTINATION / "ORIGIN_MANIFEST_023.json")
    save_new(DESTINATION / "CHANGES_024.json", {
        "origin_manifest_sha256": EXPECTED_ORIGIN,
        "reviewed_hashes_path": str(reviewed_path),
        "reviewed_hashes_sha256": sha(reviewed_path),
        "changes": changes,
        "test_dependency_closure": sorted(tests),
        "source_job_models_controllers_and_generic_runner_changed": False,
        "amount027_modules_included": False,
    })
    files = []
    for path in sorted(DESTINATION.rglob("*")):
        if path.is_file():
            relative = str(path.relative_to(DESTINATION))
            files.append({"pin_relative_path": relative, "size": path.stat().st_size,
                          "sha256": sha(path), "prior_sha256": old.get(relative, {}).get("sha256"),
                          "origin": str(ROOT / relative) if relative in OWNED else
                          str(ORIGIN / relative) if relative in old else "coordinator024provenance"})
    manifest = {"version": "configured_literature_source_job_pin_024",
                "origin_root": str(ORIGIN), "origin_manifest_sha256": EXPECTED_ORIGIN,
                "files": files}
    save_new(DESTINATION / "SOURCE_MANIFEST.json", manifest)
    verify(DESTINATION, manifest)
    verify(ORIGIN, prior)
    assert not any("literature_amount_" in row["pin_relative_path"] for row in files)
    result = {"status": "captured_pinned_execution_pending", "pin": str(DESTINATION),
              "verified_files": len(files), "changes": changes,
              "pin_manifest_sha256": sha(DESTINATION / "SOURCE_MANIFEST.json"),
              "original_generic_runner_sha256": sha(DESTINATION / "runner/run_literature_source_job_019.py"),
              "old_pin_unchanged": True, "amount027_modules_included": False,
              "actual_model_delivery_proved": False}
    save_new(EVIDENCE / "NATIVE_RATE_PIN_CAPTURE_024.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "changes"}))


if __name__ == "__main__":
    main()
