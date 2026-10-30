"""Narrow follow-up for the failed counts fixture and partial result retention."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from gene_annotation_episode import native_blast_masking_result_publication as publication
from gene_annotation_episode import sequence_masking_calculations as calculations
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.sequence_masking_result_views import validate_masking_fact_values, validate_masking_result_selector
from test_native_blast_masking_results_616 import (
    POLICY, captured_fixture, inline_workers, prepared_fixture, publish, selector, slot,
    test_statistics_preserve_original_reference_rows_thresholds_and_absent_codes as check_statistics,
)


def test_corrected_native_counts_fixture_reaches_statistics_publication(tmp_path, monkeypatch):
    check_statistics(tmp_path, monkeypatch, "windowmasker_counts")


def test_valid_sheet_survives_calculator_failure_and_can_be_explicitly_returned(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    with patch.object(calculations, "calculate_sequence_masking_components", side_effect=ValueError("synthetic_calculator_failure")):
        store, _, _, _, prepared, source = prepared_fixture(tmp_path)
    assert not prepared["worker_completed"]
    assert prepared["sheet_artifact_ref"] is not None and prepared["calculations_artifact_ref"] is None
    assert any(f["code"] == "synthetic_calculator_failure" for f in prepared["failures"])
    result = publish(tmp_path, store, prepared, source, selector(saved_data=["sheet"]))
    assert result["status"]["state"] == "complete"
    assert result["record_refs"] == [source, prepared["sheet_artifact_ref"]]
    missing = publish(tmp_path, store, prepared, source, selector(quantities=["masked_positions"]), name="missing_components")
    assert missing["quantities"] == []
    assert missing["status"]["state"] == "unavailable"
    # A later, explicitly selected saved recalculation can repair missing derived
    # values without another native run or changing the original failed receipt.
    repaired = publish(tmp_path, store, prepared, source, selector(mode="saved_recalculation",
        saved_sheet_ref=prepared["sheet_artifact_ref"], quantities=["masked_positions"]), name="recalculated")
    assert repaired["status"]["state"] == "complete"
    assert [r["value"]["value"] for r in repaired["quantities"]] == [80, 0, 72]
    assert not publication.validate_prepared_masking_result(store, prepared)["worker_completed"]


def test_partial_native_parse_preserves_invalid_measurement_and_valid_records(tmp_path, monkeypatch):
    native = b">dup\n0 - 999\n>dup\n>tail\n0 - 71\n"
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, primary_bytes=native)
    result = publish(tmp_path, store, prepared, source, selector(quantities=["masked_positions"]))
    assert [r["value"]["value"] for r in result["quantities"]] == [None, 0, 72]
    assert result["status"]["state"] == "partial"
    assert any(f["code"] == "interval_out_of_bounds" for f in result["failures"])


def test_missing_native_output_and_empty_native_population_do_not_mean_zero(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path / "missing", monkeypatch, missing_output=True)
    result = publish(tmp_path, store, prepared, source, selector(quantities=["masked_positions"]), name="missing")
    assert result["quantities"] == [] and result["status"]["state"] == "unavailable"
    assert any(f["code"] == "native_blast_masking_missing_output" for f in result["failures"])
    store2, _, _, _, prepared2, source2 = prepared_fixture(tmp_path / "empty", monkeypatch, "dustmasker_empty")
    result2 = publish(tmp_path, store2, prepared2, source2, selector(quantities=["masked_positions"]), name="empty")
    assert result2["quantities"] == [] and result2["status"]["state"] == "unavailable"
    assert {"empty_input", "requested_input_population_unavailable"} <= {f["code"] for f in result2["failures"]}


def test_frozen_validation_survives_all_native_and_worker_directory_removal(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    choice = selector(quantities=["masked_fraction"], saved_data=["sheet", "calculations"])
    result = publish(tmp_path, store, prepared, source, choice)
    for name in ("fixture", "results", "projection"):
        shutil.rmtree(tmp_path / name)
    with patch.object(publication, "run_local_job", side_effect=AssertionError("launched")), \
         patch.object(calculations, "calculate_sequence_masking_components", side_effect=AssertionError("recalculated")), \
         patch.object(store, "artifact", side_effect=AssertionError("wrote")):
        assert publication.validate_masking_publication(store, source_ref=source, prepared=prepared, selector=choice, publication=result) == result


def test_changed_retained_sheet_is_rejected_before_any_worker(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    ref = prepared["sheet_artifact_ref"]
    sha = ref.removeprefix("artifact_")
    path = store.path / "artifacts" / sha[:2] / sha
    path.write_bytes(path.read_bytes() + b" ")
    with patch.object(publication, "run_local_job", side_effect=AssertionError("launched")):
        with pytest.raises(ContractError, match="measurement_conflict"):
            publish(tmp_path, store, prepared, source, selector(saved_data=["sheet"]))


def test_projection_worker_failure_is_retained_and_never_implicitly_restarted(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch)
    from gene_annotation_episode import sequence_masking_result_views as views
    choice = selector(quantities=["masked_positions"])
    with patch.object(views, "project_masking_result", side_effect=ValueError("synthetic_projection_failure")):
        with pytest.raises(ContractError, match="selected_projection_worker_failed"):
            publish(tmp_path, store, prepared, source, choice)
    with patch.object(publication, "run_local_job", side_effect=AssertionError("restarted")):
        with pytest.raises(ContractError, match="selected_projection_worker_failed"):
            publish(tmp_path, store, prepared, source, choice)
    receipt = json.loads((tmp_path / "projection/native-blast-masking-projection/failure.json").read_text())
    worker_receipt = json.loads(store.get_artifact(receipt["worker_receipt_artifact_ref"]))
    assert any(f["code"] == "synthetic_projection_failure" for f in worker_receipt["failures"])


def test_counts_selector_and_fact_version_invariants(tmp_path, monkeypatch):
    store, _, _, _, prepared, source = prepared_fixture(tmp_path, monkeypatch, "windowmasker_counts")
    for choice in [selector(quantities=["masked_positions"]), selector(saved_data=["sheet"]),
                   selector(artifacts=[slot("sequences", "input")])]:
        with pytest.raises(ContractError):
            validate_masking_result_selector(choice, operation=prepared["operation"])
    result = publish(tmp_path, store, prepared, source, selector(statistics_fields=["unit_length", "thresholds", "percentiles"], statistics_unit_codes=[0]))
    for column, bad_value in [("unit_length", True), ("thresholds", {"t_low": True, "t_extend": 126, "t_threshold": 126, "t_high": 126})]:
        bad = deepcopy(result["statistics"]); bad[0]["fields"][column] = bad_value
        with pytest.raises(ContractError):
            validate_masking_fact_values("execution.masking_statistics", bad)
    bad = deepcopy(result["statistics"]); bad[0]["fields"]["percentiles"][0]["percentage_lexeme"] = "9999"
    with pytest.raises(ContractError):
        validate_masking_fact_values("execution.masking_statistics", bad)
