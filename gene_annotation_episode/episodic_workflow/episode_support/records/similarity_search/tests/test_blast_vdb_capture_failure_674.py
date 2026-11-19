"""Missing selected inputs preserve requested original bytes, in bounded529.

Native execution is controlled engineering data. These tests exercise actual
capture custody, result receipts, requested facts and immediate-parent admission.
"""
import asyncio
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search import native_blast_utility_capture_failure as failed
from gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.sequence_homology_evidence import native_blast_utility_result_worker as worker
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.similarity_search.sequence_homology_evidence import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence import native_blast_utility_contracts as contracts
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search import native_blast_utility_result_publication as publication
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import form_with_facts
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.execution_contracts import canonical

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.sequence_homology_evidence.tests.test_blast_vdb_native_context_668 import (
    controlled_capture, controlled_job, controlled_dependency_job,
)
import gene_annotation_episode.episodic_workflow.episode_support.jobs.similarity_search.native_blast_utility_worker_context as _scientific_native_blast_utility_result_worker


def result_selector(**changes):
    return {"version": "native_blast_utility_result_selector_v2", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None,
        "prepared_database": False, "include_checks": False, "artifacts": [],
        "saved_data": [], "paths": None, "vdb_context": False, **changes}


def sequence_selection(*ordinals, fields=(), sequence_fields=("normalized_sequence",), identity=False):
    return {"selection": {"kind": "selector_ordinals", "values": list(ordinals)},
        "record_fields": list(fields), "sequence_fields": list(sequence_fields),
        "include_vdb_identity": identity}


# The operational failure a caller records when parsing could not be prepared.
PREPARE_FAILURE = {'stage': 'parse', 'code': 'semantic_validation_unavailable', 'occurrence_id': None,
    'record_key': None, 'line_number': None, 'native_returncode': None}


def missing_capture(tmp_path, kind, *, native_returncode=0):
    if kind in {"dependency_list", "metadata_with_present_dependency_list"}:
        job = controlled_dependency_job(tmp_path, declaration="metadata")
    else:
        job = controlled_job(tmp_path, variant="entry_batch" if kind == "entry_batch" else "entry",
            database_source="dbs_file" if kind == "dbs_file" else "db")
    if kind in {"entry_batch", "dbs_file"}:
        role = "entry_batch" if kind == "entry_batch" else "database_list"
        omission = next(("input", row["role"], i) for i, row in enumerate(job["inputs"])
            if row["role"] == role)
    elif kind == "dependency_list":
        address = job["vdb_context_request"]["database_lists"][0]["selection"]
        db = next(d for d in [*job["databases"], *job["vdb_context_request"]["dependency_databases"]]
            if d["database_key"] == address["database_key"])
        path = db["manifest"]["files"][address["file_index"]]["path"]
        omission = next(("database", row["role"], i)
            for i, row in enumerate(contracts.database_file_selections(job))
            if row["original_path"] == path)
    else:
        omission = next(("database", row["role"], i)
            for i, row in enumerate(contracts.database_file_selections(job))
            if row["role"] == "metadata_manifest")
    store, capture = controlled_capture(tmp_path, job=job, omit=(omission,), returncode=native_returncode)
    with pytest.raises(ContractError, match="^" + failed.QUALIFICATION_FAILURE + "$"):
        _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)
    return store, capture


def selected_failure(store, capture, directory, *, selector=None):
    directory.mkdir(parents=True, exist_ok=True)
    selector = result_selector(sequences=sequence_selection(0), vdb_context=True,
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0},
            {"direction": "output", "role": "stderr", "ordinal": 0},
            {"direction": "output", "role": "preparation_receipt", "ordinal": 0}],
        saved_data=["result"]) if selector is None else selector
    problems = [deepcopy(PREPARE_FAILURE)]
    receipt = failed.publish_capture_failure(store, capture=capture, selector=selector,
        operational_failures=problems, directory=directory)
    return receipt, selector, problems


@pytest.mark.parametrize("kind", ["dependency_list", "metadata_with_present_dependency_list"])
def test_unqualified_database_list_is_missing_without_suppressing_available_stdout(tmp_path, kind):
    store, capture = missing_capture(tmp_path, kind)
    try:
        chosen = result_selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": 0},
            {"direction": "output", "role": "stdout", "ordinal": 0}])
        original = deepcopy(capture)
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure", selector=chosen)
        projection = receipt["projection"]
        assert [r["role"] for r in projection["artifacts"]] == ["stdout"]
        assert projection["missing"] == [{"version": "native_blast_utility_missing_fact_v2",
            "source_ref": capture["source_ref"], "request": {"type": "artifact", "slot": chosen["artifacts"][0]},
            "reason": "artifact_unavailable"}]
        assert capture == original
    finally:
        store.close()


def test_declared_dbs_file_bytes_stay_available_when_other_selected_metadata_is_missing(tmp_path):
    job = controlled_job(tmp_path, database_source="dbs_file")
    omission = next(("database", row["role"], i) for i, row in enumerate(contracts.database_file_selections(job))
        if row["role"] == "metadata_manifest")
    store, capture = controlled_capture(tmp_path, job=job, omit=(omission,))
    try:
        chosen = result_selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": 0}])
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure", selector=chosen)
        assert len(receipt["projection"]["artifacts"]) == 1
        assert receipt["projection"]["artifacts"][0]["occurrence_id"] == job["operation"]["parameters"]["database_selection"]["list_occurrence_id"]
        assert receipt["projection"]["missing"] == []
    finally:
        store.close()


def test_native_failure_is_preserved_with_available_requested_bytes(tmp_path):
    store, capture = missing_capture(tmp_path, "metadata", native_returncode=7)
    try:
        receipt, _, _ = selected_failure(store, capture, tmp_path / "failure")
        projection = receipt["projection"]
        assert projection["status"]["native_state"] == "failed"
        assert projection["status"]["state"] == "partial"
        assert [r["role"] for r in projection["artifacts"]] == ["stdout", "stderr", "preparation_receipt"]
        assert any(r["code"] == "native_nonzero_exit" and r["native_returncode"] == 7
            for r in projection["failures"])
    finally:
        store.close()


@pytest.mark.parametrize("field", ["capture_sha256", "source_ref", "selector", "operational_failures",
    "qualification_failure", "projection", "extra"])
def test_frozen_failure_publication_rejects_tampering(tmp_path, field):
    store, capture = missing_capture(tmp_path, "metadata")
    try:
        receipt, chosen, problems = selected_failure(store, capture, tmp_path / "failure")
        changed = deepcopy(receipt)
        if field == "projection":
            changed[field]["artifacts"].pop()
        elif field == "selector":
            changed[field]["artifacts"] = []
        elif field == "operational_failures":
            changed[field] = []
        else:
            changed[field] = "changed"
        with pytest.raises(ContractError, match="original_projection_conflict"):
            failed.validate_capture_failure(store, capture=capture, selector=chosen,
                operational_failures=problems, publication=changed)
    finally:
        store.close()


def test_qualified_or_invalid_capture_cannot_use_missing_input_route(tmp_path):
    store, capture = controlled_capture(tmp_path)
    try:
        with pytest.raises(ContractError, match="missing_input_qualification_required"):
            selected_failure(store, capture, tmp_path / "qualified")
        invalid = deepcopy(capture)
        invalid["artifacts"][0]["artifact_ref"] = "artifact_" + "0" * 64
        with pytest.raises(ContractError):
            selected_failure(store, invalid, tmp_path / "invalid")
        full = _scientific_native_blast_utility_result_worker.qualified_utility_context(capture)
        observed = _scientific_native_blast_utility_result_worker.captured_utility_observations(capture)
        assert observed == {key: full[key] for key in ("operation", "native_outcome", "occurrences", "failures")}
    finally:
        store.close()


