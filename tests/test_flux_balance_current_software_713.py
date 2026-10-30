"""Pure bounded verification of029; a failed runtime selection stays failed."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest


ATTEMPT = Path(os.environ["HMMER529_ATTEMPT"]) if "HMMER529_ATTEMPT" in os.environ else None
pytestmark = pytest.mark.skipif(ATTEMPT is None, reason="application validators require bounded529")
PACKET = "verification/tool_graders_flux_balance_current_software_2026-10-29_713"
ORIGINAL = "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions"


@pytest.fixture(scope="module")
def preparation():
    root = ATTEMPT / "source_snapshot"
    spec = importlib.util.spec_from_file_location("fba_software_preparation_713", root / PACKET / "prepare_software.py")
    helper = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = helper
    spec.loader.exec_module(helper)
    selected = root / ORIGINAL / "cobra_json/selected-plan.json"
    original = json.loads(selected.read_bytes())
    destination = ATTEMPT / "prepared-software"
    result = helper.stage_flux_balance_current_software(selected_plan_path=selected,
        source_root=root, destination=destination)
    return helper, original, destination, result


def _diagnostic_candidate(original, receipt):
    # An in-memory pure-validator operand, never a selectable descriptor on
    # runtime failure. It retains the incompatible original runtime selection.
    value = deepcopy(original["requested_job"]["native_flux_balance"]["software"])
    value["module_root"] = receipt["module_root"]
    value["implementation_files"] = [deepcopy(row["prepared"]) for row in receipt["source_checks"]]
    return value


def _metadata_plans(original, software):
    from gene_annotation_episode.execution_contracts import digest
    from gene_annotation_episode.native_flux_balance_contracts import (
        ATTEMPT_DIRECTORY_NAME, bind_flux_balance_environment, flux_balance_environment,
        validate_flux_balance_run_plan,
    )
    v1 = deepcopy(original)
    v1["requested_job"]["native_flux_balance"]["software"] = deepcopy(software)
    v1["requested_job"]["environment"] = flux_balance_environment(software,
        attempt_directory=v1["attempt_directory"], lifecycle_directory=str(Path(v1["identity"]["execution_id"]).parent))
    v1["identity"]["requested_job_sha256"] = digest(v1["requested_job"])
    v1 = validate_flux_balance_run_plan(v1)
    v2 = deepcopy(v1)
    v2["version"] = "flux_balance_run_plan_v2"
    owner = v2["identity"]
    owner.update(run_id="metadata713", episode_id="pure-validator", operation_key="metadata-only")
    owner["attempt_id"] = digest(owner["operation_key"])
    lifecycle = ATTEMPT / "metadata-plan" / ".episode-operations" / digest({"run": owner["run_id"], "episode": owner["episode_id"]}) / owner["attempt_id"]
    owner["execution_id"] = str(lifecycle / "native.json")
    v2["attempt_directory"] = str(lifecycle / ATTEMPT_DIRECTORY_NAME)
    v2["environment_binding"] = bind_flux_balance_environment(v2["requested_job"],
        execution_id=owner["execution_id"], attempt_directory=v2["attempt_directory"], selection={
            "version": "flux_balance_execution_selection_v1",
            "environment_realization": "operation_scoped_tmp_and_cache_v1"})
    v2 = validate_flux_balance_run_plan(v2)
    assert {row["name"] for row in v2["environment_binding"]["relocations"]} == {
        "TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME", "PIP_CACHE_DIR"}
    assert v2["requested_job"] == v1["requested_job"]
    return v1, v2


def test_actual_original_runtime_and_current_source_metadata(preparation):
    from gene_annotation_episode.native_flux_balance_contracts import validate_flux_balance_software
    helper, original, destination, result = preparation
    receipt = result["receipt"]
    selected = original["requested_job"]["native_flux_balance"]["software"]
    assert not result["ready"] and not receipt["ready"]
    assert len(receipt["source_checks"]) == 7
    checks = receipt["reused_runtime_checks"]
    assert len(checks) == 1 + len(selected["runtime_files"]) + len(selected["solver_runtime_files"])
    assert [r["expected"] for r in checks] == [selected["python"], *selected["runtime_files"], *selected["solver_runtime_files"]]
    assert all(r["source_before"] == r["source_after"] and r["state"] == "matched" for r in receipt["source_checks"])
    files = sorted((destination / "module_root").rglob("*.py"))
    assert [p.name for p in files] == sorted(helper.REQUIRED_FILES)
    assert all(not p.stat().st_mode & 0o222 for p in files)
    assert all(helper.file_pin(row["prepared"]["path"]) == row["prepared"] for row in receipt["source_checks"])
    candidate = _diagnostic_candidate(original, receipt)
    assert {k for k in candidate if candidate[k] != selected[k]} == {"module_root", "implementation_files"}
    assert all(candidate[key] == selected[key] for key in helper.REUSED_FIELDS)
    checked = validate_flux_balance_software(candidate)
    assert checked == candidate
    v1, v2 = _metadata_plans(original, checked)
    failures = [row for row in checks if row["state"] != "matched"]
    if failures:
        assert receipt["status"] == "preparation_failed"
        assert result["software"] is None and receipt["software_file"] is None
        assert not (destination / "software.json").exists()
        assert len(receipt["failures"]) == len(failures)
        assert all(f["code"].startswith("original_runtime_pin_") for f in receipt["failures"])
    else:
        assert receipt["status"] == "staged_metadata_unvalidated" and not receipt["failures"]
        assert result["software"] == candidate
        assert helper.file_pin(destination / "software.json") == receipt["software_file"]
    sbml = json.loads((ATTEMPT / "source_snapshot" / ORIGINAL / "sbml/selected-plan.json").read_bytes())
    assert sbml["requested_job"]["native_flux_balance"]["software"] == selected
    counts = {state: sum(row["state"] == state for row in checks) for state in ("matched", "mismatched", "missing", "unreadable")}
    validation = {"version": "flux_balance_software_bounded_validation_v1", "ready": not failures,
        "readiness_meaning": "prepared_bytes_and_validated_metadata_only",
        "status": "runtime_selection_failed" if failures else "metadata_ready",
        "preparation_receipt_file": result["receipt_file"], "software_file": receipt["software_file"],
        "source_root": receipt["source_root"], "prepared_module_root": receipt["module_root"],
        "test_python": str(Path(sys.executable).resolve()), "selected_python": selected["python"],
        "original_runtime_check_counts": counts, "current_software_schema_valid": True,
        "current_plan_versions_metadata_valid": [v1["version"], v2["version"]],
        "validator_module_file": helper.file_pin(ATTEMPT / "source_snapshot/gene_annotation_episode/native_flux_balance_contracts.py"),
        "diagnostic_only_candidate_on_runtime_failure": bool(failures),
        "native_execution": "not_run", "scientific_worker": "not_run", "model_load": "not_run",
        "producer_importability": "not_verified_seven_file_selection_omits_transitive_package_imports"}
    helper.immutable_json(destination / "bounded-validation.json", validation)
    assert helper.file_pin(ATTEMPT / "source_snapshot" / ORIGINAL / "cobra_json/selected-plan.json") == receipt["selected_plan"]


def test_schema_detachment_and_rejection(preparation):
    from gene_annotation_episode.native_flux_balance_contracts import validate_flux_balance_software
    helper, original, _, result = preparation
    candidate = _diagnostic_candidate(original, result["receipt"])
    validated = validate_flux_balance_software(candidate)
    validated["dependency_roots"].append("/explicit-test-only")
    validated["implementation_files"][0]["sha256"] = "0" * 64
    assert candidate == _diagnostic_candidate(original, result["receipt"])
    incomplete = deepcopy(candidate)
    incomplete["implementation_files"].pop()
    with pytest.raises(ValueError, match="fba_implementation_closure_incomplete"):
        validate_flux_balance_software(incomplete)
    duplicate = deepcopy(candidate)
    duplicate["solver_runtime_files"].append(deepcopy(duplicate["python"]))
    with pytest.raises(ValueError, match="fba_duplicate_software_file"):
        validate_flux_balance_software(duplicate)
    absent = deepcopy(candidate)
    absent["runtime_files"] = []
    with pytest.raises(ValueError, match="fba_runtime_closure_incomplete"):
        validate_flux_balance_software(absent)
    assert all(candidate[field] == original["requested_job"]["native_flux_balance"]["software"][field] for field in helper.REUSED_FIELDS)


def test_conflicting_destination_never_rebinds(preparation):
    helper, _, destination, result = preparation
    before = helper.file_pin(destination / "preparation-receipt.json")
    with pytest.raises(helper.PreparationRefused, match="destination_not_empty_or_regular"):
        helper.stage_flux_balance_current_software(selected_plan_path=Path(result["receipt"]["selected_plan"]["path"]),
            source_root=ATTEMPT / "source_snapshot", destination=destination)
    assert helper.file_pin(destination / "preparation-receipt.json") == before


def test_controlled_pin_failures_preserve_selected_bytes(preparation, tmp_path):
    helper, _, _, _ = preparation
    matched = tmp_path / "matched"
    matched.write_bytes(b"explicit metadata fixture")
    pin = helper.file_pin(matched)
    missing = {**pin, "path": str(tmp_path / "missing")}
    changed = {**pin, "sha256": "0" * 64}
    original = {"python": pin, "runtime_files": [missing], "solver_runtime_files": [changed]}
    snapshot = deepcopy(original)
    rows = helper.check_reused_runtime(original)
    assert [row["state"] for row in rows] == ["matched", "missing", "mismatched"]
    assert rows[2]["expected"] == changed and rows[2]["observed"] == pin
    assert original == snapshot


def test_wrong_original_plan_has_retained_failure_and_no_descriptor(preparation, tmp_path):
    helper, _, _, _ = preparation
    selected = tmp_path / "selected-plan.json"
    selected.write_text('{"version":"deliberately-not-original688"}\n')
    destination = tmp_path / "failed-preparation"
    result = helper.stage_flux_balance_current_software(selected_plan_path=selected,
        source_root=ATTEMPT / "source_snapshot", destination=destination)
    assert result["receipt"]["failures"] == [{"code": "preparation_input_failure", "exception": "PreparationRefused", "detail": "exact_original688_plan_required"}]
    assert result["software"] is None and not result["ready"]
    assert (destination / "preparation-receipt.json").is_file()
    assert not (destination / "software.json").exists()
