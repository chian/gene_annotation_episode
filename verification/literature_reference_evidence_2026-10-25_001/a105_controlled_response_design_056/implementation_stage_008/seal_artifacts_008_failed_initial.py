"""Seal owned reader generation and verify previously accepted code artifacts."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OWNED = ["gene_annotation_episode/literature_controlled_response_inputs.py", "tests/test_literature_controlled_response_inputs.py"]


def digest(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def emit(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    previous = HERE.parent
    checks = {}
    for stage, receipt in [(previous / "reader_stage_007", "DELIVERY_007.json"), (previous / "pure_stage_003", "DELIVERY_006.json")]:
        original = json.loads((stage / receipt).read_text())
        for relative, expected in original["artifacts"].items():
            actual = digest(stage / relative)
            assert actual == expected, (stage, relative)
            checks[str((stage / relative).relative_to(ROOT))] = {**actual, "unchanged": True}
        for relative, expected in original.get("owned_new_paths", {}).items():
            actual = digest(ROOT / relative)
            assert actual == expected, relative
            checks[relative] = {**actual, "unchanged": True}
    dependencies = {}
    before = json.loads((HERE / "BEFORE_008.json").read_text())
    for value in before["modules"].values():
        relative = value["relative"]
        actual = digest(ROOT / relative)
        assert actual == {k:value[k] for k in ("sha256", "bytes")}, relative
        assert digest(HERE / "before" / relative) == actual
        dependencies[relative] = {"before": actual, "after": actual, "unchanged": True, "baseline": "BEFORE_008.json and full before snapshot"}
    # Older baseline copies are read-only accepted own code receipts, not a
    # scientific execution pin. They supply all remaining declared dependency
    # before identities, including the frozen pure calculator.
    for directory in [previous / "reader_stage_007/baseline_007", previous / "reader_stage_007/baseline_008"]:
        for snapshot in directory.rglob("*.py"):
            relative = str(snapshot.relative_to(directory))
            actual = digest(ROOT / relative)
            assert digest(snapshot) == actual, relative
            dependencies.setdefault(relative, {"before": actual, "after": actual, "unchanged": True, "baseline": str(snapshot.relative_to(ROOT))})
    pin_manifest = json.loads((HERE / "PIN_MANIFEST_008.json").read_text())
    for relative, expected in pin_manifest["original_files"].items():
        assert digest(ROOT / relative) == {k:expected[k] for k in ("sha256", "bytes")}, relative
    imports = json.loads((HERE / "ACTUAL_IMPORTS_008.json").read_text())
    assert imports["pytest_exitstatus"] == 0 and not imports["misplaced_package_imports"]
    owned = {}
    patch = []
    review = []
    parent_preliminary = previous.parent / "controlled_response_source_parent_review_056/reader008_preliminary_001"
    review_generation = {}
    for relative in OWNED:
        path = ROOT / relative
        owned[relative] = digest(path)
        target = HERE / "final_snapshot_008" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        patch.extend(difflib.unified_diff([], path.read_text().splitlines(keepends=True), fromfile="/dev/null", tofile=relative))
        preliminary = parent_preliminary / relative
        review_generation[relative] = {"parent_preliminary": digest(preliminary), "final": digest(path)}
        review.extend(difflib.unified_diff(preliminary.read_text().splitlines(keepends=True), path.read_text().splitlines(keepends=True), fromfile="parent_preliminary_001/" + relative, tofile=relative))
    with (HERE / "NEW_FILES_008.patch").open("x") as stream:
        stream.writelines(patch)
    with (HERE / "PARENT_REVIEW_DELTA_008.patch").open("x") as stream:
        stream.writelines(review)
    emit("DEPENDENCY_AFTER_008.json", {"scope": "Declared pure reader dependencies only; no claim of coherent unrelated shared runtime", "dependencies": dependencies,
        "all_unchanged": True, "accepted006_and007_verified_files": checks,
        "parent_preliminary_and_final_generations": review_generation})
    artifacts = {str(p.relative_to(HERE)):digest(p) for p in sorted(HERE.rglob("*")) if p.is_file()}
    emit("DELIVERY_008.json", {"status": "bounded_text_json_source_reader_delivered_pending_parent_review",
        "owned_new_paths": owned, "artifact_hashes": artifacts,
        "actual_terminal": "TERMINAL_008.json", "actual_stdout": "TERMINAL_STDOUT_008.txt",
        "test_result": "319 passed in 3.62s; exit0", "reader_test_cases": 69,
        "frozen006_and007_unchanged": True, "declared_existing_dependencies_unchanged": True,
        "source_fixture_origin": "Own invented synthetic007 text/structured covariance and test-authored variants; no papers",
        "source_searches_model_calls_episodes_observations": 0,
        "reader_calls_sheet_populator": False,
        "saved_consistency_is_independent_custody": False,
        "unfinished": ["Graph measured ordinates/rate wrapper integration", "Selected native execution/catalog/storage/C4", "Typed/admitted-subset/saved runtime reopening", "Actual primary-source scientific example"],
        "whole_A105_complete": False, "full_workload_complete": False,
        "approval_scope": "Only new reader/test plus additive008 artifacts; no other production/test/shared changes by this stage"})
    print(json.dumps({"owned": owned, "artifacts": len(artifacts), "frozen006_and007_verified": len(checks), "dependencies_unchanged": len(dependencies)}))


if __name__ == "__main__":
    main()
