"""Original source payloads from retained native capture examples.

These tests do not establish completed episode receipt or authorized delivery.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.protein_structure_contracts import issue
from gene_annotation_episode.protein_structure_publication import protein_structure_source_payload
from gene_annotation_episode.protein_structure_result_worker import validate_protein_structure_result_worker_result


FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_protein_structure_publication_2026-10-27_399/fixtures/capture_examples.json"


def example(name):
    return next(row for row in json.loads(FIXTURES.read_bytes()) if row["case"] == name)


def worker_result(case):
    file = next(row["observed"] for row in case["capture"]["files"] if row["declared"]["role"] == "native_result")
    return {"version": "protein_structure_result_worker_result_v1", "mode": "original_native_result",
        "operation": case["bundle"]["requested_job"]["native_protein_structure"]["request"]["operation"],
        "native_result_file": {"relative_path": "native-result.json", "file_identity": file},
        "sheet_file": None, "components_file": None, "state": "partial", "issues": []}


@pytest.mark.parametrize("name", ["inspection", "extraction", "comparison", "changed_native_bytes", "declared_absence", "nonzero_native_exit"])
def test_original_payload_preserves_actual_native_capture_and_fixed_fields(name):
    case = example(name)
    original = deepcopy(case)
    payload = protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=None)
    assert payload == {"provider": "episode.execution_result", "accession": "native_protein_structure_" + digest(case["bundle"]["identity"]),
        "uri": None, "artifact_ref": case["capture"]["bundle_file"]["artifact_ref"],
        "text_ref": None, "request_ref": None, "version": "native_protein_structure_bundle_v1",
        "retrieved_at": case["bundle"]["finished_at"],
        "auxiliary_artifact_refs": list(dict.fromkeys(row["observed"]["artifact_ref"]
            for row in case["capture"]["files"] if row["observed"] is not None))}
    assert case == original


def test_repeated_original_worker_identity_deduplicates_without_reordering_capture():
    case = example("inspection")
    plain = protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=None)
    with_worker = protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=worker_result(case))
    assert with_worker == plain


def test_missing_or_unvalidated_bundle_cannot_be_a_scientific_source():
    for field, value in (("bundle_file", None), ("original_plan", None), ("bundle_validated", False)):
        case = example("inspection")
        case["capture"][field] = value
        with pytest.raises(ValueError, match="capture_incomplete"):
            protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=None)


def test_bundle_identity_must_describe_exact_original_json_bytes():
    case = example("inspection")
    case["capture"]["bundle_file"]["byte_length"] += 1
    with pytest.raises(ValueError, match="input_digest_mismatch"):
        protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=None)


def test_different_worker_operation_cannot_change_source():
    case = example("inspection")
    worker = worker_result(example("extraction"))
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=worker)


def test_saved_recalculation_cannot_replace_original_source():
    case = example("comparison")
    worker = worker_result(case)
    worker.update(mode="saved_sheet_recalculation", native_result_file=None, state="unavailable",
        issues=[issue("retained_artifact_missing", stage="input", field="file_identity")])
    assert validate_protein_structure_result_worker_result(worker) == worker
    with pytest.raises(ValueError, match="original_commission_mismatch"):
        protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=worker)


def test_payload_builder_never_reads_or_reacquires_files(monkeypatch):
    case = example("inspection")
    worker = worker_result(case)
    def forbidden(*args, **kwargs):
        raise AssertionError("source payload builder attempted file I/O")
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    result = protein_structure_source_payload(bundle=case["bundle"], capture=case["capture"], worker_result=worker)
    assert result["artifact_ref"] == case["capture"]["bundle_file"]["artifact_ref"]
