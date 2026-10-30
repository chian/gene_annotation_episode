"""Selected views of synthetic saved C records; no native execution or acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest

from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_utility_result_views import (
    FACT_SOURCES, IDENTIFIER_NAMESPACES, NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA,
    PREPARED_DATABASE_VERSION, PROJECTION_FIELDS, blast_utility_fact_sources,
    project_blast_utility_result, projection_identifiers,
    validate_blast_utility_fact_values, validate_blast_utility_projection,
    validate_blast_utility_result_selector,
)
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_blast_utility_returns import (
    NativeBLASTUtilityReturns, requested_sources,
)
from test_blast_utility_contracts_625 import (
    artifact_set, extraction, field, inspection, integrity, occurrence,
    operation, outcome, prepared_manifest,
)


SOURCE = "source_original_utility"


def selector(**changes):
    return {"version": "native_blast_utility_result_selector_v1", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None,
        "prepared_database": False, "include_checks": False, "artifacts": [], "saved_data": [], **changes}


def selected_sequences(*ordinals, fields=("normalized_sequence",)):
    return selector(sequences={"selector_ordinals": list(ordinals), "sequence_fields": list(fields)})


def retained(result):
    """Assign synthetic Store identities and distinct original slots, without IO."""
    result = deepcopy(result)
    if result["version"] == "blast_database_artifact_set_v1":
        rows = result["inputs"] + result["outputs"]
    else:
        rows = [occurrence("db-file", direction="input", role="database_file", fmt="blastdb_binary")]
        rows.extend([result["stdout_occurrence"], result["stderr_occurrence"]]
                    if result["version"] == "blast_database_integrity_v1" else [result["output_occurrence"]])
    ordinals = {}
    for row in rows:
        slot = row["direction"], row["role"]
        row["ordinal"] = ordinals.get(slot, 0)
        ordinals[slot] = row["ordinal"] + 1
        row["artifact_ref"] = "artifact_" + row["sha256"]
    return validate_blast_utility_result(result), rows


def project(result, selected, **kwargs):
    result, rows = retained(result)
    context = {"source_ref": SOURCE, "operation": result["operation"], "native_outcome": result["original_outcome"],
        "result": result, "prepared_database": None, "occurrences": rows,
        "selector": selected, "failures": [], "saved_data": [], **kwargs}
    return project_blast_utility_result(**context), context


def validate(projection, context):
    return validate_blast_utility_projection(projection, **{key: context[key] for key in
        ("source_ref", "operation", "native_outcome", "selector", "occurrences")})


def saved(kind, value):
    data = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    digest = hashlib.sha256(data).hexdigest()
    return {"source_ref": SOURCE, "kind": kind, "artifact_ref": "artifact_" + digest,
        "sha256": digest, "size_bytes": len(data), "schema": value["version"]}


def available_preparation(result):
    manifest = prepared_manifest()
    manifest.update(identity=result["identity"], native_paths=result["native_paths"],
        files=[{"path": row["native_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]}
               for row in result["outputs"] if row["role"] in {"database_file", "database_metadata"}])
    manifest["preparation"].update(software=result["software"], argv=result["argv"])
    receipt = manifest["preparation"]["receipt"]
    manifest["preparation"]["source"] = {"source_ref": receipt["artifact_ref"] or receipt["path"], "pointer": ""}
    return deepcopy({"status": "available", "manifest": manifest, "failures": []})


def test_public_schemas_are_closed_and_detached():
    jsonschema.Draft202012Validator.check_schema(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)
    assert set(PROJECTION_FIELDS) == {source.removeprefix("execution.blast_utility_") for source in FACT_SOURCES} | {"record_refs"}
    for source, descriptor in blast_utility_fact_sources().items():
        jsonschema.Draft202012Validator.check_schema(descriptor["report_schema"])
        assert descriptor["report_schema"]["x-source"] == source
    changed = blast_utility_fact_sources()
    changed["execution.blast_utility_status"]["report_schema"]["items"]["properties"].clear()
    assert blast_utility_fact_sources()["execution.blast_utility_status"]["report_schema"]["items"]["properties"]


def test_selected_sequence_copies_original_identity_length_coordinates_without_extra_bytes():
    value = extraction()
    value["operation"]["parameters"]["range"] = {"start_1based": 2, "end_1based": 5}
    row = value["records"][0]
    row.update(native_reported_length=12, requested_range={"start_1based": 2, "end_1based": 5},
               effective_range={"start_0based": 1, "end_exclusive": 5, "strand": "plus"})
    view, context = project(value, selected_sequences(0))
    selected = view["sequences"][0]
    assert selected["record_key"] == "out#/records/2" and selected["line_number"] == 4
    assert selected["native_reported_length"] == 12 and selected["returned_symbol_count"] == 4
    assert selected["effective_range"] == row["effective_range"]
    assert selected["sequences"] == {"normalized_sequence": "ACGT"}
    assert selected["native_identifier"] == "ALPHA" and selected["native_accession"] == "ALPHA.1"
    assert view["record_refs"] == [SOURCE] and view["artifacts"] == []
    assert view["status"]["result_completeness"] == "complete_selection"
    assert validate(json.loads(json.dumps(view)), context) == view
    selected["sequences"]["normalized_sequence"] = "changed"
    assert context["result"]["records"][0]["normalized_sequence"] == "ACGT"


def test_duplicate_requests_and_native_rows_are_preserved_without_ordinal_join():
    value = extraction()
    value["operation"]["parameters"]["selectors"] = [{"ordinal": i, "value": "ALPHA"} for i in range(2)]
    value["records"][0]["matched_selector_ordinals"] = [0, 1]
    duplicate = deepcopy(value["records"][0])
    duplicate.update(native_row_ordinal=5, line_number=7, record_key="out#/records/5")
    value["records"].append(duplicate)
    view, _ = project(value, selected_sequences(1))
    assert [row["record_key"] for row in view["sequences"]] == ["out#/records/2", "out#/records/5"]
    assert [row["selector_ordinals"] for row in view["sequences"]] == [[1], [1]]
    assert projection_identifiers(view, IDENTIFIER_NAMESPACES[0]) == ["out#/records/2", "out#/records/5"]
    assert projection_identifiers(view, IDENTIFIER_NAMESPACES[1]) == ["out"]


def test_empty_sequence_selection_returns_no_record_or_sequence():
    view, _ = project(extraction(), selected_sequences())
    assert view["sequences"] == [] and projection_identifiers(view) == []
    assert view["record_refs"] == [SOURCE] and view["status"]["state"] == "complete"


def test_unknown_length_and_coordinates_are_copied_without_repair():
    value = extraction()
    value["records"][0].update(native_reported_length=99, returned_symbol_count=None,
        effective_range=None, completeness="partial", failures=[{"stage": "validation",
            "code": "sequence_length_conflict", "occurrence_id": "out", "record_key": "out#/records/2",
            "line_number": 4, "native_returncode": None}])
    value["population_completeness"] = "partial_selection"
    view, _ = project(value, selected_sequences(0, fields=("original_sequence",)))
    assert view["sequences"][0]["native_reported_length"] == 99
    assert view["sequences"][0]["returned_symbol_count"] is None
    assert view["sequences"][0]["effective_range"] is None
    assert view["failures"][0]["code"] == "sequence_length_conflict"
    assert view["status"]["result_completeness"] == "partial_selection"


def test_missing_selection_preserves_present_sequence_and_failed_native_outcome():
    value = extraction()
    value["operation"]["parameters"]["selectors"].append({"ordinal": 1, "value": "MISSING"})
    value.update(missing_selector_ordinals=[1], population_completeness="partial_selection",
        original_outcome=outcome(state="failed", returncode=1))
    view, _ = project(value, selected_sequences(0, 1))
    assert len(view["sequences"]) == 1
    assert view["status"]["state"] == "partial" and view["status"]["native_state"] == "failed"
    assert view["missing"] == [{"source_ref": SOURCE, "request": {"type": "sequence_selector", "ordinal": 1},
                                "reason": "selection_unavailable"}]


def test_database_fields_keep_distinct_native_approximate_and_exact_observations():
    value = inspection()
    value["native_fields"] = [field(value=1200, native_lexeme="1.2K", value_basis="native_reported_approximate"),
        field(value=1234, native_lexeme="1234", line_number=2),
        field(field_name="database_title", value="unrequested", unit="text", native_lexeme="unrequested")]
    view, _ = project(value, selector(database_fields=["database_sequence_count"]))
    assert [row["value"] for row in view["database_fields"]] == [1200, 1234]
    assert [row["value_basis"] for row in view["database_fields"]] == ["native_reported_approximate", "native_reported_exact"]
    assert all(row["field_name"] == "database_sequence_count" for row in view["database_fields"])


def test_database_missing_field_has_no_fabricated_native_locator():
    view, _ = project(inspection(), selector(database_fields=["database_sequence_count", "database_bytes"]))
    assert len(view["database_fields"]) == 1 and view["status"]["state"] == "partial"
    assert view["missing"][0]["request"] == {"type": "database_field", "field_name": "database_bytes"}


def test_native_null_is_qualified_information_without_zero_or_missing_locator():
    value = inspection()
    value["native_fields"] = [field(value=None, native_lexeme=None, missing_reason="native_field_absent")]
    view, _ = project(value, selector(database_fields=["database_sequence_count"]))
    assert view["database_fields"][0]["value"] is None
    assert view["database_fields"][0]["missing_reason"] == "native_field_absent"
    assert view["missing"] == [] and view["status"]["state"] == "complete"


def test_integrity_selected_sample_keeps_unknown_count_and_seed():
    value = integrity()
    value.update(scope="selected_sample", observed_population_count=30)
    value["operation"]["parameters"].update(full=False, random_count=4)
    view, _ = project(value, selector(integrity={"fields": ["observed_checked_count", "realized_seed"]}))
    assert view["integrity"] == [{"source_ref": SOURCE, "database_key": "tiny", "scope": "selected_sample",
                                 "fields": {"observed_checked_count": None, "realized_seed": None}}]
    assert "observed_population_count" not in view["integrity"][0]["fields"]


def test_preparation_selected_fields_and_manifest_are_copies_not_artifact_grants():
    value, rows = retained(artifact_set())
    prepared = available_preparation(value)
    view, _ = project(value, selector(preparation={"fields": ["detail", "compatibility"]}, prepared_database=True),
                      prepared_database=prepared)
    assert view["preparation"][0]["fields"] == {"detail": value["detail"], "compatibility": "unverified"}
    assert view["prepared_database"][0]["manifest"] == prepared["manifest"]
    assert view["record_refs"] == [SOURCE]
    assert view["artifacts"] == []


@pytest.mark.parametrize("change", ["identity", "files", "argv", "receipt"])
def test_prepared_manifest_cannot_borrow_another_preparation(change):
    value, _ = retained(artifact_set())
    prepared = available_preparation(value)
    if change == "identity":
        prepared["manifest"]["identity"]["value"] = "other"
    elif change == "files":
        prepared["manifest"]["files"][0]["sha256"] = "c" * 64
    elif change == "argv":
        prepared["manifest"]["preparation"]["argv"].append("invented")
    else:
        prepared["manifest"]["preparation"]["source"]["source_ref"] = "other-receipt"
    with pytest.raises(ContractError, match="prepared_database"):
        project(value, selector(prepared_database=True), prepared_database=prepared)


def test_saved_data_selects_actual_result_and_manifest_schemas_only():
    value, _ = retained(artifact_set())
    prepared = available_preparation(value)
    descriptors = [saved("result", value), saved("prepared_database", prepared["manifest"])]
    view, _ = project(value, selector(saved_data=["prepared_database"]),
        prepared_database=prepared, saved_data=descriptors)
    assert view["saved_data"] == [descriptors[1]]
    assert view["saved_data"][0]["schema"] == PREPARED_DATABASE_VERSION
    assert view["record_refs"] == [SOURCE, descriptors[1]["artifact_ref"]]
    assert descriptors[0]["artifact_ref"] not in view["record_refs"]


def test_unavailable_prepared_manifest_cannot_have_a_saved_manifest_descriptor():
    value, _ = retained(artifact_set())
    prepared = {"status": "unavailable", "manifest": None, "failures": [{"stage": "projection",
        "code": "preparation_not_successful", "occurrence_id": None, "record_key": None,
        "line_number": None, "native_returncode": None}]}
    with pytest.raises(ContractError, match="saved_prepared_database_unavailable"):
        project(value, selector(saved_data=["prepared_database"]), prepared_database=prepared,
            saved_data=[saved("prepared_database", available_preparation(value)["manifest"])])


def test_unavailable_preparation_is_typed_and_does_not_suppress_original_failure():
    value, _ = retained(artifact_set())
    prepared = {"status": "unavailable", "manifest": None, "failures": [{"stage": "projection",
        "code": "preparation_not_successful", "occurrence_id": None, "record_key": None,
        "line_number": None, "native_returncode": None}]}
    view, _ = project(value, selector(prepared_database=True), prepared_database=prepared)
    assert view["prepared_database"][0]["status"] == "unavailable"
    assert view["missing"][0]["reason"] == "prepared_database_unavailable"
    assert view["failures"][0]["code"] == "preparation_not_successful"


def test_same_bytes_keep_separate_original_occurrences_and_one_explicit_byte_grant():
    value = integrity()
    view, _ = project(value, selector(artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0},
        {"direction": "output", "role": "stderr", "ordinal": 0}]))
    assert [row["occurrence_id"] for row in view["artifacts"]] == ["out", "err"]
    assert view["artifacts"][0]["artifact_ref"] == view["artifacts"][1]["artifact_ref"]
    assert len(view["record_refs"]) == 2


@pytest.mark.parametrize("failed,expected", [(False, "unavailable"), (True, "failed")])
def test_missing_result_keeps_specific_unfulfilled_requests(failed, expected):
    original, rows = retained(inspection())
    native = outcome(state="failed", returncode=1) if failed else original["original_outcome"]
    view = project_blast_utility_result(source_ref=SOURCE, operation=original["operation"], native_outcome=native,
        result=None, prepared_database=None, occurrences=rows, failures=[], saved_data=[],
        selector=selector(database_fields=["database_sequence_count"], include_checks=True))
    assert view["status"]["state"] == expected
    assert [row["request"]["type"] for row in view["missing"]] == ["database_field", "checks"]
    assert view["database_fields"] == [] and view["checks"] == []


def test_malformed_original_rows_keep_global_qualification_without_renumbering():
    value = extraction()
    value["population_completeness"] = "partial_selection"
    value["failures"] = [{"stage": "parse", "code": "native_row_invalid", "occurrence_id": "out",
        "record_key": "out#/records/0", "line_number": 1, "native_returncode": None}]
    view, _ = project(value, selected_sequences(0))
    assert view["sequences"][0]["record_key"] == "out#/records/2"
    assert view["failures"][0]["record_key"] == "out#/records/0"
    assert projection_identifiers(view, IDENTIFIER_NAMESPACES[0]) == ["out#/records/2"]


@pytest.mark.parametrize("changes", [
    {"sequences": {"selector_ordinals": [True], "sequence_fields": []}},
    {"sequences": {"selector_ordinals": [1], "sequence_fields": []}},
    {"sequences": {"selector_ordinals": [0, 0], "sequence_fields": []}},
    {"integrity": {"fields": []}}, {"database_fields": ["database_title"]},
    {"prepared_database": True}, {"extra": "not allowed"},
    {"artifacts": [{"direction": "output", "role": "stdout", "ordinal": True}]},
])
def test_invalid_selector_is_rejected_before_projection(changes):
    with pytest.raises(ContractError):
        validate_blast_utility_result_selector(selector(**changes), operation=operation())


@pytest.mark.parametrize("changes", [
    lambda view: view["record_refs"].append("artifact_" + "f" * 64),
    lambda view: view["sequences"][0].update(source_ref="source_other"),
    lambda view: view["sequences"][0].update(record_key="out#/records/99"),
    lambda view: view["sequences"][0].update(selector_ordinals=[1]),
    lambda view: view["sequences"][0]["sequences"].update(original_sequence="unrequested"),
    lambda view: view["status"].update(inventory_complete=False),
])
def test_projection_tampering_cannot_expand_selection(changes):
    view, context = project(extraction(), selected_sequences(0))
    changes(view)
    with pytest.raises(ContractError):
        validate(view, context)


def test_dropping_missing_rows_cannot_relabel_unfulfilled_selection_complete():
    view, context = project(inspection(), selector(database_fields=["database_bytes"]))
    view["missing"] = []
    view["status"]["state"] = "complete"
    with pytest.raises(ContractError, match="missing_population"):
        validate(view, context)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), (1, 2), {1: "bad"}, b"bytes"])
def test_non_json_or_nonfinite_facts_are_rejected(bad):
    view, _ = project(extraction(), selected_sequences(0))
    rows = view["sequences"]
    rows[0]["extra"] = bad
    with pytest.raises(ContractError):
        validate_blast_utility_fact_values("execution.blast_utility_sequences", rows)


def test_original_operation_outcome_and_occurrence_conflicts_are_rejected():
    _, context = project(extraction(), selected_sequences(0))
    context["occurrences"][1]["ordinal"] = 7
    # Original result object and external occurrences are detached here.
    context["result"] = deepcopy(context["result"])
    context["result"]["output_occurrence"]["ordinal"] = 0
    with pytest.raises(ContractError, match="occurrence_context"):
        project_blast_utility_result(**context)


def test_pure_projection_performs_no_file_network_or_process_work(monkeypatch):
    value, rows = retained(extraction())

    def forbidden(*args, **kwargs):
        raise AssertionError("pure projection attempted IO")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    view = project_blast_utility_result(source_ref=SOURCE, operation=value["operation"],
        native_outcome=value["original_outcome"], result=value, prepared_database=None,
        occurrences=rows, selector=selected_sequences(0), failures=[], saved_data=[])
    assert view["sequences"][0]["returned_symbol_count"] == 4


def test_parent_reference_forms_only_grant_explicit_selected_bytes():
    view, _ = project(extraction(), selected_sequences(0))
    values = {"execution.blast_utility_sequences": view["sequences"]}
    assert NativeBLASTUtilityReturns._references(values) == [SOURCE]
    source = "execution.blast_utility_sequences"
    schema = {"properties": {"selected": blast_utility_fact_sources()[source]["report_schema"]}}
    assert requested_sources(schema) == (source,)
    boundary = NativeBLASTUtilityReturns.__new__(NativeBLASTUtilityReturns)
    boundary._received_values = lambda context: {"groups": values, "references": [SOURCE], "handoffs": []}
    assert boundary.resolve_received(None, "out#/records/2", IDENTIFIER_NAMESPACES[0])
    assert not boundary.resolve_received(None, "out#/records/0", IDENTIFIER_NAMESPACES[0])
    assert boundary.resolve_received(None, "out", IDENTIFIER_NAMESPACES[1])
    assert not boundary.resolve_received(None, "db-file", IDENTIFIER_NAMESPACES[1])


def test_return_owner_hooks_and_frozen_subset_do_not_merge_producers():
    owner = SimpleNamespace(store=SimpleNamespace(db=None), run_id="run", native_blast_utility_results=object())
    boundary = NativeBLASTUtilityReturns(owner)
    assert boundary.results is owner.native_blast_utility_results
    view, _ = project(extraction(), selected_sequences(0))
    source = "execution.blast_utility_sequences"
    other = deepcopy(view["sequences"][0]); other["source_ref"] = "source_other"
    assert boundary._subset({source: view["sequences"]}, {source: [*view["sequences"], other]})
    assert not boundary._subset({source: [other]}, {source: view["sequences"]})
    assert not boundary._subset({source: view["sequences"] * 2}, {source: view["sequences"]})
