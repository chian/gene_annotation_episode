"""Requested original artifacts when missing inputs prevent VDB qualification.

No parsed result, database metadata or preparation receipt is manufactured. The
existing common projector selects available captured facts; saved validation
checks those exact facts against the original capture and selected request.
"""
from __future__ import annotations

from pathlib import Path

from .blast_utility_result_views import project_blast_utility_result
from .domain import ContractError, canonical
from .native_blast_utility_acquisition import _validate_saved
from .native_blast_utility_contracts import finite_json_copy, native_blast_digest
from .native_blast_utility_result_worker import (
    captured_utility_observations, qualified_utility_context, unique_failures,
)
from .practical_execution_state import _immutable


VERSION = "native_blast_utility_capture_failure_publication_v1"
FILENAME = "capture-failure-publication.json"
QUALIFICATION_FAILURE = "native_blast_utility_input_population_unavailable"


def _require(condition, code):
    if not condition:
        raise ContractError("native_blast_utility_capture_failure_" + code)


def _publication(store, *, capture, selector, operational_failures):
    capture = _validate_saved(store, capture)
    _require(capture["bundle_validated"] and capture["source_ref"] is not None,
        "validated_capture_source_required")
    _require(capture["original_bundle"]["operation"]["version"] == "blast_utility_operation_v3",
        "vdb_operation_required")
    try:
        qualified_utility_context(capture)
    except ContractError as error:
        if str(error) != QUALIFICATION_FAILURE:
            raise
    else:
        _require(False, "missing_input_qualification_required")
    operational_failures = finite_json_copy(operational_failures)
    _require(bool(operational_failures) and unique_failures(operational_failures) == operational_failures,
        "operational_failures_required")
    facts = captured_utility_observations(capture)
    selection = facts["operation"]["parameters"]["database_selection"]
    explicit_list = selection["list_occurrence_id"] if selection["source"] == "dbs_file" else None
    # The original operation binds its dbs_file input directly. Other list
    # membership needs the missing full context, so its bytes remain retained
    # but unavailable for this return. This does not erase capture occurrences.
    available = [row for row in facts["occurrences"]
        if row["role"] != "database_list" or row["occurrence_id"] == explicit_list]
    projection = project_blast_utility_result(source_ref=capture["source_ref"],
        operation=facts["operation"], native_outcome=facts["native_outcome"],
        result=None, prepared_database=None, occurrences=available, selector=selector,
        failures=unique_failures([*facts["failures"], *operational_failures]),
        saved_data=[], context=None)
    return {"version": VERSION, "capture_sha256": native_blast_digest(capture),
        "source_ref": capture["source_ref"], "selector": finite_json_copy(selector),
        "operational_failures": operational_failures,
        "qualification_failure": QUALIFICATION_FAILURE, "projection": projection}


def publish_capture_failure(store, *, capture, selector, operational_failures, directory):
    publication = _publication(store, capture=capture, selector=selector,
        operational_failures=operational_failures)
    _immutable(Path(directory) / FILENAME, publication)
    return publication


def validate_capture_failure(store, *, capture, selector, operational_failures, publication):
    publication = finite_json_copy(publication)
    expected = _publication(store, capture=capture, selector=selector,
        operational_failures=operational_failures)
    _require(canonical(publication) == canonical(expected), "original_projection_conflict")
    return publication


__all__ = ["VERSION", "FILENAME", "QUALIFICATION_FAILURE",
    "publish_capture_failure", "validate_capture_failure"]
