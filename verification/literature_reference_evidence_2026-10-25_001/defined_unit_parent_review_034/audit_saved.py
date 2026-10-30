"""Independent saved-only audit of controlled034 and additive selector repair.

No original paper bytes are interpreted or copied. Only the original selected
sheet/request artifacts are available to reconstruction in the new workspace.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
CASE = BASE / "defined_unit_case_034"
PIN = BASE / "literature_model_run_030/pin_001"
sys.path.insert(0, str(PIN))
sys.dont_write_bytecode = True
from gene_annotation_episode.state import Store
from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
import gene_annotation_episode.literature_rate_native_inputs as native
import gene_annotation_episode.literature_rate_calculations as calculations
import gene_annotation_episode.literature_rate_storage as storage
from gene_annotation_episode.literature_experimental_contracts import validate_rate_extraction


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_snapshot(db):
    names = ("runtime_actions", "runtime_observations", "runtime_forms",
        "runtime_report_attempts", "literature_rate_operations",
        "literature_rate_source_received", "literature_rate_received")
    return {name: hashlib.sha256(json.dumps([list(row) for row in db.execute(
        "select * from " + name + " order by rowid")], separators=(",", ":")).encode()).hexdigest()
        for name in names}


def main():
    before = {str(path.relative_to(CASE)): sha(path) for path in CASE.rglob("*") if path.is_file()}
    manifest = json.loads((CASE / "FILE_MANIFEST.json").read_bytes())
    for item in manifest["files"]:
        assert sha(CASE / item["path"]) == item["sha256"]
        assert (CASE / item["path"]).stat().st_size == item["size"]
    correction = json.loads((CASE / "CENSORED_HASH_RECEIPT_003.json").read_bytes())
    for name, expected in correction["preserved_preexisting_file_hashes"].items():
        assert sha(CASE / name) == expected
    for item in correction["new_files"]:
        assert sha(CASE / item["path"]) == item["sha256"]
    old = json.loads((CASE / "CENSORED_SELECTION_002.json").read_bytes())
    new = json.loads((CASE / "CENSORED_SELECTION_003.json").read_bytes())
    reverted = deepcopy(new)
    reverted["arms"]["test"]["rate"]["number"] = old["arms"]["test"]["rate"]["number"]
    assert reverted == old and old != new
    verification = json.loads((CASE / "CENSORED_VERIFICATION_003.json").read_bytes())
    assert verification["selection_sha256"] == sha(CASE / "CENSORED_SELECTION_003.json")

    def forbidden(*args, **kwargs):
        raise AssertionError("saved-only audit forbids scientific source parsing/calculation")
    native.read_rate_source_inputs = forbidden
    calculations.populate_rate_contrast = forbidden
    storage.populate_rate_contrast = forbidden
    validate_rate_extraction(verification["extraction"])
    native.validate_native_selection(new, verification["extraction"])
    test = verification["sheet"]["cells"]["test_rate"]
    assert test["value"] is None and test["threshold"] == .01 and test["bound"] == "lt"
    assert verification["sheet"]["cells"]["rate_difference"]["value"] is None

    receipt = json.loads((CASE / "CONTROLLED_RECEIPT.json").read_bytes())
    source_state = CASE / "controlled_001/state"
    target = OUT / "saved_copy_001"
    target.mkdir(exist_ok=False)
    with sqlite3.connect((source_state / "state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as original:
        original.execute("begin")
        table_hashes = table_snapshot(original)
        counts = {name: original.execute("select count(*) from " + name).fetchone()[0]
                  for name in receipt["counts"]}
        assert counts == receipt["counts"]
        sheet_record = json.loads(original.execute("select data from records where id=?",
            (receipt["sheet_ref"],)).fetchone()[0])
        with sqlite3.connect(target / "state.sqlite3") as copied:
            original.backup(copied)
    copied_artifacts = []
    for ref in dict.fromkeys((sheet_record["artifact_ref"], sheet_record["request_ref"])):
        digest = ref.removeprefix("artifact_")
        relative = Path("artifacts") / digest[:2] / digest
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_state / relative, destination)
        assert sha(destination) == digest
        copied_artifacts.append(ref)
    forbidden_artifacts = {receipt["original_artifact_ref"], receipt["text_artifact_ref"]}
    assert not forbidden_artifacts.intersection(copied_artifacts)
    expected = json.loads((CASE / "CONTROLLED_RETURN.json").read_bytes())["requested_source_rate_cells"]
    with Store(target) as store:
        original_get = store.get_artifact
        reads = []
        def guarded(ref):
            assert ref in copied_artifacts and ref not in forbidden_artifacts
            reads.append(ref)
            return original_get(ref)
        store.get_artifact = guarded
        assert table_snapshot(store.db) == table_hashes
        repo = LiteratureRateRepository(store, receipt["summary"]["run_id"])
        saved = repo.read(receipt["sheet_ref"])
        assert saved == json.loads((CASE / "CONTROLLED_SAVED_SHEET.json").read_bytes())
        actual = repo.source_projection().project_cells([receipt["sheet_ref"]],
            permitted_record_refs=[receipt["sheet_ref"]], components=[row["component"] for row in expected])
        assert actual == expected
        forms = [json.loads(row[0]) for row in store.db.execute("select form from runtime_forms")]
        assert forms == [{"requested_source_rate_cells": expected}]
        received = [json.loads(row[0]) for row in store.db.execute("select cells from literature_rate_source_received")]
        assert received == [expected]
        assert table_snapshot(store.db) == table_hashes
    assert all(sha(CASE / name) == expected_hash for name, expected_hash in before.items())
    imported = []
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and name.split(".")[0] in {"gene_annotation_episode", "method_loop"}:
            path = Path(filename).resolve()
            assert path.is_relative_to(PIN)
            imported.append({"module": name, "path": str(path), "sha256": sha(path)})
    result = {"status": "passed", "utc": datetime.now(timezone.utc).isoformat(),
        "kind": "independent_saved_only_controlled_fixture_audit_not_actual_model_execution",
        "original_manifest_files_verified": len(manifest["files"]),
        "correction_preexisting_files_verified": len(correction["preserved_preexisting_file_hashes"]),
        "all_case_files_unchanged": len(before), "only_corrected_selector_path": "arms.test.rate.number",
        "saved_censored_selection_matches_saved_extraction": True,
        "source_parser_and_calculator_forbidden": True,
        "original_source_artifacts_not_copied_and_forbidden": sorted(forbidden_artifacts),
        "copied_artifacts": copied_artifacts, "actual_artifact_reads": sorted(set(reads)),
        "public_table_hashes_unchanged": table_hashes, "counts": counts,
        "original_form_and_received_projection_equal": True,
        "requested_cells": [{"component": row["component"], "value": row["value"],
            "unavailable_reason": row["unavailable_reason"]} for row in expected],
        "imports": imported, "pin_manifest_sha256": sha(PIN / "SOURCE_MANIFEST.json"),
        "script_sha256": sha(Path(__file__))}
    with (OUT / "RECEIPT.json").open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "passed", "case_files_unchanged": len(before),
        "source_artifacts_available": False, "table_hashes_unchanged": len(table_hashes),
        "requested_cells": len(expected), "counts": counts}))


if __name__ == "__main__":
    main()
