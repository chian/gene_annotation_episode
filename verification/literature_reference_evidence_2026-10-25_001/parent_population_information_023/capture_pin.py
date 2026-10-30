"""Capture reviewed parent-information changes without copying unrelated work."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "verification/literature_reference_evidence_2026-10-25_001"
ORIGIN = EVIDENCE / "literature_model_run_022/pin_001"
DESTINATION = EVIDENCE / "literature_model_run_023/pin_001"
EXPECTED_ORIGIN = "54370fd6a9744e2bb7e5a5fd6860bd057079a98cc8aa2ddb978fc8dd48b78684"
OWNED = {
    "gene_annotation_episode/literature_episodes.py": "f0133c6272edb46409dca7b32dcd44429d758b64d45c7eaba68dfb55c7303208",
    "gene_annotation_episode/literature_reference_parent_prompt.py": "b34f7317c8ae19d8426cacd5f332c8e2ed917ecdac0fd6df3b6b6e00782d98d2",
    "tests/test_literature_parent_population_information.py": "092d0408c3e9daa45e69643a85168843d2afaf22cdcd67a1deeddc4bc890405f",
    "verification/literature_reference_evidence_2026-10-25_001/parent_population_information_023/population_catalog_before.json": "cf6c09e480151012122c232641bad514bd4a2ab20ca4cc5a3af27f240e9a5faa",
}


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
        assert path.stat().st_size == row["size"] and sha(path) == row["sha256"]
    assert paths == {str(p.relative_to(directory)) for p in directory.rglob("*")
                     if p.is_file() and p != directory / "SOURCE_MANIFEST.json"}


def main():
    origin_manifest = ORIGIN / "SOURCE_MANIFEST.json"
    assert sha(origin_manifest) == EXPECTED_ORIGIN
    prior = json.loads(origin_manifest.read_bytes())
    verify(ORIGIN, prior)
    for relative, expected in OWNED.items():
        assert sha(ROOT / relative) == expected, relative

    # Include local test helpers recursively; never copy mutable production trees.
    pending = ["tests/test_literature_parent_population_information.py"]
    tests = set()
    while pending:
        relative = pending.pop()
        if relative in tests:
            continue
        tests.add(relative)
        tree = ast.parse((ROOT / relative).read_text())
        for node in ast.walk(tree):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module
                     else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if name.startswith("test_") and (ROOT / "tests" / (name + ".py")).is_file():
                    pending.append("tests/" + name + ".py")

    old = {row["pin_relative_path"]: row for row in prior["files"]}
    for relative in tests & old.keys():
        assert sha(ROOT / relative) == old[relative]["sha256"], relative
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.mkdir(exist_ok=False)
    for relative in old:
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ORIGIN / relative, target)
    changes = []
    for relative in sorted(set(OWNED) | (tests - old.keys())):
        target = DESTINATION / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
        changes.append({"path": relative, "before": old.get(relative, {}).get("sha256"),
                        "after": sha(target)})
    shutil.copyfile(origin_manifest, DESTINATION / "ORIGIN_MANIFEST_022.json")
    save_new(DESTINATION / "CHANGES_023.json", {
        "origin_manifest_sha256": EXPECTED_ORIGIN,
        "changes": changes,
        "production_changes": "Parent names/descriptions only; child catalog and execution unchanged.",
        "test_dependency_closure": sorted(tests),
        "source_job_models_controllers_and_generic_runner_changed": False,
    })
    files = []
    for path in sorted(DESTINATION.rglob("*")):
        if path.is_file():
            relative = str(path.relative_to(DESTINATION))
            files.append({"pin_relative_path": relative, "size": path.stat().st_size,
                          "sha256": sha(path), "prior_sha256": old.get(relative, {}).get("sha256"),
                          "origin": str(ROOT / relative) if relative in OWNED or relative in tests
                          else str(ORIGIN / relative) if relative in old else "coordinator023provenance"})
    manifest = {"version": "configured_literature_source_job_pin_023",
                "origin_root": str(ORIGIN), "origin_manifest_sha256": EXPECTED_ORIGIN,
                "files": files}
    save_new(DESTINATION / "SOURCE_MANIFEST.json", manifest)
    verify(DESTINATION, manifest)
    verify(ORIGIN, prior)
    changed_old = [row["path"] for row in changes if row["before"] is not None]
    assert changed_old == sorted(name for name in OWNED if name.startswith("gene_annotation_episode/"))
    result = {"status": "captured_after183_joined_checks_pinned_execution_pending",
              "pin": str(DESTINATION), "verified_files": len(files),
              "pin_manifest_sha256": sha(DESTINATION / "SOURCE_MANIFEST.json"),
              "changed_old_files": changed_old, "changes": changes,
              "original_generic_runner_sha256": sha(DESTINATION / "runner/run_literature_source_job_019.py"),
              "old_pin_unchanged": True, "actual_model_delivery_proved": False}
    save_new(EVIDENCE / "PARENT_POPULATION_PIN_CAPTURE_023.json", result)
    print(json.dumps({key: value for key, value in result.items() if key != "changes"}))


if __name__ == "__main__":
    main()
