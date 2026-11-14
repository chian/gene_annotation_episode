"""Original native protein result identities, issue handling and record accounting."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_return_values import FACT_SOURCES
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_receipts import ProteinQualifiedFiles, ProteinResultReceipt
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinFactGroups, ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import IssueCode, issue
from gene_annotation_episode.execution_contracts import canonical, digest
from typing import get_args


VERSION = "native_protein_structure_acquired_result_v1"
ORIGIN = {
    "content_location": "retained_complete_producer_bundle",
    "attempt_output_version": "original_producer_manifest_and_verified_file_digests",
    "window_consistency": "complete_files_matched_to_original_manifest",
    "completion_basis": "requested_acquisition_and_observed_successful_attempt",
}
_CODES = frozenset(get_args(IssueCode))


def _require(condition, code="original_commission_mismatch"):
    if not condition:
        raise ProteinStructureOperandError(issue(code, stage="authority", field="receipt"))


def _problem(error, *, stage="input", field="file_identity", role=None):
    if isinstance(error, ProteinStructureOperandError):
        return deepcopy(error.issue)
    code = str(error) if str(error) in _CODES else (
        "retained_artifact_missing" if isinstance(error, OSError) else "invalid_schema")
    return issue(code, stage=stage, field=field, artifact_role=role)


def _unique(rows):
    result, seen = [], set()
    for row in rows:
        key = canonical(row)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def _empty_files() -> ProteinQualifiedFiles:
    return {name: None for name in ProteinQualifiedFiles.__annotations__}


def _empty_facts() -> ProteinFactGroups:
    return {name: [] for name in FACT_SOURCES}


def _result_key(intent):
    return "protein_structure_result_receipt:" + digest({
        name: intent[name] for name in ("run_id", "episode_id", "operation_key")})


def _outcome(receipt: ProteinResultReceipt) -> dict:
    refs = receipt["publication"]["record_refs"]
    return {"status": "completed", "record_refs": deepcopy(refs),
            "changed_record_refs": deepcopy(refs), "result": deepcopy(receipt), "feedback": None}


