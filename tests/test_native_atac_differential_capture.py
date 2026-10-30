"""Role-preserving byte capture; controls do not establish episode authority."""
from pathlib import Path

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.native_file_capture import NativeFileCaptureError
from gene_annotation_episode.native_atac_differential_capture import capture_atac_native_files, validate_atac_native_capture
from gene_annotation_episode import native_atac_differential_driver as driver

from test_native_atac_differential_contracts import plan_fixture, path_for
from test_native_atac_differential_producer import mock_commands


def collect(store, plan):
    return capture_atac_native_files(store, original_plan=plan, source_action_receipt_ref="source_original_action",
        writer_closure_receipt_ref="source_terminal_quiescent", driver_started=True)


def test_complete_manifest_identical_content_roles_and_empty_files(tmp_path, monkeypatch):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    store = Store(tmp_path / "store")
    captured = collect(store, plan)
    assert len(captured["files"]) == len(plan["outputs"]) == 31
    assert all(r["outcome"] == "verified" for r in captured["files"])
    assert captured["driver_state"] == "succeeded"
    rows = {r["specification"]["file_key"]: r for r in captured["files"]}
    assert rows["input1"]["retained"]["file"] == rows["input2"]["retained"]["file"]
    assert rows["callpeak1.stdout"]["retained"]["file"]["sha256"] == rows["stderr"]["retained"]["file"]["sha256"]
    assert rows["callpeak1.stdout"]["retained"]["file"]["format"] != rows["stderr"]["retained"]["file"]["format"]
    assert rows["bdgdiff.common"]["retained"]["file"]["size_bytes"] == 89
    assert collect(store, plan) == captured


def test_bundle_absent_preserves_sealed_and_unsealed_occurrences(tmp_path, monkeypatch):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    path_for(plan, "bundle").unlink()
    path_for(plan, "bdgdiff.seal").unlink()
    path_for(plan, "bdgdiff.common").unlink()
    captured = collect(Store(tmp_path / "store"), plan)
    rows = {r["specification"]["file_key"]: r for r in captured["files"]}
    assert captured["bundle"] is None and captured["driver_state"] == "unknown"
    assert rows["callpeak1.signal"]["outcome"] == "verified"
    assert rows["bdgdiff.condition1"]["outcome"] == "unsealed"
    assert rows["bdgdiff.common"]["outcome"] == "unavailable"
    assert rows["bdgdiff.condition1"]["supplied_extent"] == "partial"


def test_changed_or_absent_declared_file_cannot_be_resealed(tmp_path, monkeypatch):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    path_for(plan, "callpeak1.signal").write_bytes(b"changed bytes")
    path_for(plan, "callpeak2.background").unlink()
    result = collect(Store(tmp_path / "store"), plan)
    rows = {r["specification"]["file_key"]: r for r in result["files"]}
    assert rows["callpeak1.signal"]["outcome"] == "digest_mismatch"
    assert rows["callpeak1.signal"]["declared"]["sha256"] != rows["callpeak1.signal"]["retained"]["file"]["sha256"]
    assert rows["callpeak2.background"]["outcome"] == "unavailable"
    assert rows["callpeak2.signal"]["outcome"] == "verified"


def test_partial_failure_absence_is_not_zero(tmp_path, monkeypatch):
    mock_commands(monkeypatch, fail_first=True)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    result = collect(Store(tmp_path / "store"), plan)
    rows = {r["specification"]["file_key"]: r for r in result["files"]}
    assert result["driver_state"] == "failed"
    assert rows["callpeak1.signal"]["outcome"] == "verified" and rows["callpeak1.signal"]["supplied_extent"] == "partial"
    assert rows["bdgdiff.common"]["outcome"] == "declared_absent"
    assert rows["bdgdiff.common"]["retained"] is None


def test_failed_producer_extent_survives_missing_individual_seal(tmp_path, monkeypatch):
    mock_commands(monkeypatch, fail_first=True)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    path_for(plan, "callpeak1.seal").unlink()
    result = collect(Store(tmp_path / "store"), plan)
    rows = {r["specification"]["file_key"]: r for r in result["files"]}
    assert rows["callpeak1.seal"]["outcome"] == "unavailable"
    assert rows["callpeak1.signal"]["outcome"] == "verified"
    assert rows["callpeak1.signal"]["producer_outcome"] == "failed"
    assert rows["callpeak1.signal"]["supplied_extent"] == "partial"


def test_storage_failure_is_not_native_absence(tmp_path, monkeypatch):
    from gene_annotation_episode import native_file_capture
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path / "run")
    driver.run_atac_differential_driver(plan)
    def broken(*args, **kwargs):
        raise NativeFileCaptureError("retained_artifact_unavailable")
    monkeypatch.setattr(native_file_capture, "capture_native_file", broken)
    with pytest.raises(NativeFileCaptureError, match="retained_artifact_unavailable"):
        collect(Store(tmp_path / "store"), plan)
