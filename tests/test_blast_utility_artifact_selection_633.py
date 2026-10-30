"""Explicit artifact selection over synthetic saved facts; no native work."""
from copy import deepcopy
import pytest
from gene_annotation_episode.blast_utility_result_views import (
    project_blast_utility_result, validate_blast_utility_projection,
)
from gene_annotation_episode.domain import ContractError
from test_blast_utility_contracts_625 import occurrence, operation, outcome
from test_blast_utility_result_views_629 import selector


def context(artifacts):
    rows = []
    for key, role, ordinal in (("metadata-A", "database_metadata", 7),
            ("metadata-B", "database_metadata", 19),
            ("original-receipt", "preparation_receipt", 0),
            ("unrequested-binary", "database_file", 4)):
        row = occurrence(key, role=role, fmt="json" if role != "database_file" else "blastdb_binary")
        row.update(ordinal=ordinal, artifact_ref="artifact_" + row["sha256"])
        rows.append(row)
    return {"source_ref": "source_selected_original", "operation": operation("create_sequence_database"),
        "native_outcome": outcome(), "result": None, "prepared_database": None,
        "occurrences": rows, "selector": selector(artifacts=artifacts),
        "failures": [], "saved_data": []}


def validate(view, supplied):
    return validate_blast_utility_projection(view, **{key: supplied[key] for key in
        ("source_ref", "operation", "native_outcome", "selector", "occurrences")})


def test_parent_can_request_native_metadata_without_guessing_its_file_ordinals():
    supplied = context([{"direction": "output", "role": "database_metadata", "ordinal": None},
        {"direction": "output", "role": "preparation_receipt", "ordinal": 0}])
    view = project_blast_utility_result(**supplied)
    assert [(row["role"], row["ordinal"]) for row in view["artifacts"]] == [
        ("database_metadata", 7), ("database_metadata", 19), ("preparation_receipt", 0)]
    assert view["missing"] == []
    assert "unrequested-binary" not in [row["occurrence_id"] for row in view["artifacts"]]
    assert validate(view, supplied) == view
    forged = deepcopy(view)
    forged["artifacts"].append({"source_ref": supplied["source_ref"], **supplied["occurrences"][-1]})
    with pytest.raises(ContractError, match="grant_conflict"):
        validate(forged, supplied)


def test_overlapping_explicit_artifact_requests_do_not_duplicate_occurrences():
    supplied = context([{"direction": "output", "role": "database_metadata", "ordinal": 19},
        {"direction": "output", "role": "database_metadata", "ordinal": None}])
    view = project_blast_utility_result(**supplied)
    assert [row["ordinal"] for row in view["artifacts"]] == [19, 7]
    assert view["missing"] == []
    assert validate(view, supplied) == view


def test_absent_explicit_role_selection_is_missing_not_an_empty_success():
    requested = {"direction": "output", "role": "stderr", "ordinal": None}
    supplied = context([requested])
    view = project_blast_utility_result(**supplied)
    assert view["artifacts"] == []
    assert view["missing"] == [{"source_ref": supplied["source_ref"],
        "request": {"type": "artifact", "slot": requested}, "reason": "artifact_unavailable"}]
    assert view["status"]["state"] == "unavailable"
    assert validate(view, supplied) == view


def test_source_only_still_grants_no_original_receipt_or_other_artifacts():
    supplied = context([])
    view = project_blast_utility_result(**supplied)
    assert view["artifacts"] == []
    assert view["record_refs"] == [supplied["source_ref"]]


@pytest.mark.parametrize("kind", ["result", "prepared_database"])
def test_missing_saved_data_has_typed_failure_instead_of_helper_argument_collision(kind):
    supplied = context([])
    supplied["selector"]["saved_data"] = [kind]
    view = project_blast_utility_result(**supplied)
    assert view["saved_data"] == []
    assert view["missing"] == [{"source_ref": supplied["source_ref"],
        "request": {"type": "saved_data", "kind": kind}, "reason": "saved_data_unavailable"}]
    assert view["status"]["state"] == "unavailable"
    assert validate(view, supplied) == view
