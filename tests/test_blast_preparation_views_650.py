"""Requested saved views: synthetic joins plus explicitly retained 102d RPS facts.

No native command is run. The RPS fixture reuses its recorded file identities
and auxiliary text; its selected-list association is controlled, as in 647.
"""
from copy import deepcopy
import json
from pathlib import Path

import jsonschema
import pytest

from gene_annotation_episode.blast_preparation_inputs import parse_blast_alias_document
from gene_annotation_episode.blast_utility_result_views import (
    DATABASE_FIELD_SCHEMA, NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA,
    PREPARATION_SCHEMA, SAVED_DATA_SCHEMA, blast_utility_fact_sources,
    project_blast_utility_result, projection_identifiers,
    validate_blast_utility_result_selector,
)
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.native_blast_utility_returns import NativeBLASTUtilityReturns
from test_blast_preparation_contracts_647 import MODES, operation
from test_blast_preparation_population_647 import (
    common, copy_input, database, occurrence, outcome, populate,
    profile_args_from_retained_success, projection,
)
from test_blast_utility_contracts_625 import inspection as legacy_inspection
from test_blast_utility_contracts_625 import operation as legacy_operation
from test_blast_utility_result_views_629 import (
    SOURCE, project as legacy_project, saved, selector, validate,
)


def list_inspection(*, count=1):
    """Hand-authored stored-ID count with a real typed file subject, no fake DB."""
    source = occurrence("ids", "identifier_list", b"synthetic opaque list", fmt="seqid_list_binary")
    output = occurrence("list-info", "stdout", b"synthetic list metadata", direction="output",
        fmt="blast_seqid_list_info_text", path="/attempt/stdout")
    field = {"field_name": "identifier_list_count", "value": count, "unit": "identifiers",
        "value_basis": "native_reported_exact", "native_lexeme": str(count),
        "occurrence_id": output["occurrence_id"], "line_number": 2, "json_pointer": None, "missing_reason": None}
    result = {"version": "blast_database_inspection_v2", "operation": operation("inspect_seqid_list"),
        "original_outcome": outcome(), "subject": {"kind": "identifier_list", "occurrence_id": "ids"},
        "database_bindings": [], "output_occurrence": output, "native_fields": [field],
        "completeness": "complete", "checks": [], "failures": []}
    return result, [source, output]


def alias_result(*, rc=0):
    """Controlled custody using the observed native LENGTH13 spelling."""
    source = occurrence("ids", "identifier_list", b"synthetic opaque list", fmt="seqid_list_binary")
    staged, receipt = copy_input(source)
    member, binding = database()
    raw = b'TITLE subset\nDBLIST /source/db\nSEQIDLIST /attempt/inputs/ids\nNSEQ 1\nLENGTH 13\n'
    alias = occurrence("alias", "alias_file", raw, direction="output", fmt="blast_alias_text",
        path="/attempt/out/subset.nal")
    return populate(**common(operation("create_subset_alias"), inputs=[source, staged, member], outputs=[alias],
        bindings=[binding], materializations=[receipt], documents=[parse_blast_alias_document(raw, occurrence=alias)],
        native_outcome=outcome(rc)))


def selected(result, selection, *, occurrences=None, prepared=None, saved_data=()):
    if occurrences is None:
        occurrences = result["inputs"] + result["outputs"]
    context = {"source_ref": SOURCE, "operation": result["operation"],
        "native_outcome": result["original_outcome"], "result": result,
        "prepared_database": prepared, "occurrences": occurrences, "selector": selection,
        "failures": [], "saved_data": list(saved_data)}
    return project_blast_utility_result(**context), context


def test_closed_versioned_schemas_are_detached_and_accept_v2_artifact_branches():
    for schema in (NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA, DATABASE_FIELD_SCHEMA,
                   PREPARATION_SCHEMA, SAVED_DATA_SCHEMA):
        jsonschema.Draft202012Validator.check_schema(schema)
    descriptors = blast_utility_fact_sources()
    descriptors["execution.blast_utility_preparation"]["report_schema"]["items"].clear()
    assert blast_utility_fact_sources()["execution.blast_utility_preparation"]["report_schema"]["items"]


def test_stored_list_count_uses_exact_file_subject_and_no_implicit_artifact_grants():
    result, rows = list_inspection()
    view, context = selected(result, selector(database_fields=["identifier_list_count"]), occurrences=rows)
    assert view["database_fields"] == [{"source_ref": SOURCE, "subject": result["subject"], **result["native_fields"][0]}]
    assert view["database_fields"][0]["value"] == 1
    assert view["status"]["state"] == "complete" and view["status"]["result_completeness"] == "complete"
    assert view["record_refs"] == [SOURCE] and view["artifacts"] == []
    assert projection_identifiers(view) == []
    assert NativeBLASTUtilityReturns._references({"execution.blast_utility_database_fields": view["database_fields"]}) == [SOURCE]
    assert validate(json.loads(json.dumps(view)), context) == view


@pytest.mark.parametrize("change", [
    lambda row: row.update(subject={"kind": "identifier_list", "occurrence_id": "other"}),
    lambda row: row.update(subject={"kind": "database", "database_key": "invented"}),
    lambda row: row.update(source_ref="source_elsewhere"),
    lambda row: row.update(occurrence_id="ids"),
])
def test_projection_rejects_well_typed_foreign_subject_source_or_native_locator(change):
    result, rows = list_inspection()
    view, context = selected(result, selector(database_fields=["identifier_list_count"]), occurrences=rows)
    change(view["database_fields"][0])
    with pytest.raises(ContractError):
        validate(view, context)


@pytest.mark.parametrize("change", [
    lambda result, rows: result["subject"].update(occurrence_id="other"),
    lambda result, rows: rows[0].update(native_format="text"),
    lambda result, rows: rows[0].update(role="database_file"),
    lambda result, rows: rows.pop(0),
])
def test_list_inspection_original_input_association_is_required(change):
    result, rows = list_inspection()
    change(result, rows)
    with pytest.raises(ContractError):
        selected(result, selector(database_fields=["identifier_list_count"]), occurrences=rows)


@pytest.mark.parametrize("external", [False, True])
def test_missing_original_list_preserves_qualified_native_count_without_input_grant(external):
    result, rows = list_inspection()
    qualification = {"stage": "capture", "code": "input_population_unavailable", "occurrence_id": None,
        "record_key": None, "line_number": None, "native_returncode": None}
    result["original_outcome"]["inventory_complete"] = False
    result["completeness"] = "unknown"
    result["failures"] = [] if external else [qualification]
    requested = selector(database_fields=["identifier_list_count"],
        artifacts=[{"direction": "input", "role": "identifier_list", "ordinal": 0}])
    context = {"source_ref": SOURCE, "operation": result["operation"], "native_outcome": result["original_outcome"],
        "result": result, "prepared_database": None, "occurrences": rows[1:], "selector": requested,
        "failures": [qualification] if external else [], "saved_data": []}
    view = project_blast_utility_result(**context)
    assert view["database_fields"][0]["value"] == 1
    assert view["database_fields"][0]["subject"] == {"kind": "identifier_list", "occurrence_id": "ids"}
    assert view["artifacts"] == [] and view["record_refs"] == [SOURCE]
    assert view["missing"][0]["reason"] == "artifact_unavailable"
    assert view["status"]["state"] == "partial" and not view["status"]["inventory_complete"]
    assert view["failures"] == [{"source_ref": SOURCE, **qualification}]
    assert validate(view, context) == view
    view["failures"] = []
    with pytest.raises(ContractError, match="inspection_subject_unavailable"):
        validate(view, context)


def test_inspection_missing_field_remains_missing_and_never_becomes_zero():
    result, rows = list_inspection()
    view, _ = selected(result, selector(database_fields=["identifier_list_count", "identifier_list_database_length"]),
        occurrences=rows)
    assert [row["value"] for row in view["database_fields"]] == [1]
    assert view["missing"] == [{"source_ref": SOURCE, "request": {"type": "database_field",
        "field_name": "identifier_list_database_length"}, "reason": "field_unavailable"}]
    assert view["status"]["state"] == "partial"


def test_empty_filter_inspection_keeps_selected_database_and_no_invented_count():
    member, binding = database()
    output = occurrence("filters", "stdout", b"\n", direction="output", path="/attempt/filters")
    result = {"version": "blast_database_inspection_v2", "operation": operation("show_filters"),
        "original_outcome": outcome(), "subject": {"kind": "database", "database_key": "db"},
        "database_bindings": [binding], "output_occurrence": output, "native_fields": [],
        "completeness": "unknown", "checks": [], "failures": []}
    view, context = selected(result, selector(database_fields=["database_sequence_count"],
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}]), occurrences=[member, output])
    assert view["database_fields"] == [] and view["status"]["state"] == "partial"
    assert view["missing"][0]["request"]["field_name"] == "database_sequence_count"
    # A well-typed zero is still unavailable under the unverified filter grammar.
    forged = {"source_ref": SOURCE, "subject": result["subject"], **list_inspection()[0]["native_fields"][0]}
    forged.update(field_name="database_sequence_count", value=0, unit="sequences", occurrence_id="filters")
    view["database_fields"] = [forged]; view["missing"] = []; view["status"]["state"] = "complete"
    with pytest.raises(ContractError, match="inspection_field_context"):
        validate(view, context)


def test_alias_length_and_selected_preparation_details_copy_the_common_values():
    result = alias_result()
    fields = ["kind", "detail", "database_bindings", "materializations", "dependencies"]
    view, context = selected(result, selector(database_fields=["database_residue_count"], preparation={"fields": fields}))
    assert view["database_fields"][0]["value"] == 13
    assert view["database_fields"][0]["value_basis"] == "native_reported"
    assert view["database_fields"][0]["database_key"] == "prepared"
    assert "subject" not in view["database_fields"][0]
    assert view["preparation"] == [{"source_ref": SOURCE, "database_key": "prepared",
        "fields": {key: result[key] for key in fields}}]
    assert view["preparation"][0]["fields"]["materializations"][0]["kind"] == "input_copy"
    assert view["record_refs"] == [SOURCE] and validate(view, context) == view
    view["preparation"][0]["fields"]["materializations"][0]["input_key"] = "changed-copy"
    assert result["materializations"][0]["input_key"] == "ids"


def test_standard_alias_manifest_uses_the_common_exact_closure_without_grants():
    result = alias_result()
    prepared = projection(result)
    view, _ = selected(result, selector(prepared_database=True), prepared=prepared)
    assert view["prepared_database"][0]["manifest"] == prepared["manifest"]
    assert prepared["manifest"]["preparation"]["method"] == "other_recorded"
    assert view["record_refs"] == [SOURCE]


@pytest.mark.parametrize("change", [
    lambda m: m["identity"].update(value="another"),
    lambda m: m["preparation"].update(method="makeblastdb"),
    lambda m: m["preparation"]["argv"].append("invented"),
    lambda m: m["files"].pop(),
    lambda m: m["files"][0].update(sha256="3" * 64),
    lambda m: m.update(native_paths=["/another/db"]),
    lambda m: m["preparation"]["source"].update(source_ref="other"),
])
def test_prepared_alias_manifest_cannot_change_identity_method_or_dependency_closure(change):
    result = alias_result()
    prepared = projection(result); change(prepared["manifest"])
    with pytest.raises(ContractError):
        selected(result, selector(prepared_database=True), prepared=prepared)


def test_retained_rps_details_and_additional_saved_manifest_keep_actual_versions():
    result = populate(**profile_args_from_retained_success())
    prepared = projection(result, "additional")
    descriptors = [saved("result", result), saved("prepared_database", prepared["manifest"])]
    view, context = selected(result, selector(preparation={"fields": ["kind", "detail"]},
        prepared_database=True, saved_data=["result", "prepared_database"]), prepared=prepared, saved_data=descriptors)
    detail = view["preparation"][0]["fields"]["detail"]
    native = detail["volumes"][0]["auxiliary_documents"][0]["rows"][0]
    assert native["sequence_length"] == 320 and native["karlin_k"] == pytest.approx(0.0375672)
    assert detail["profiles"][0]["disposition"] == "unknown"
    assert [row["schema"] for row in view["saved_data"]] == [
        "blast_database_artifact_set_v2", "native_blast_prepared_database_manifest_v1"]
    assert view["prepared_database"][0]["manifest"]["kind"] == "rps_profile"
    assert view["record_refs"] == [SOURCE, *[row["artifact_ref"] for row in descriptors]]
    assert view["artifacts"] == [] and validate(json.loads(json.dumps(view)), context) == view


def test_saved_prepared_descriptor_must_match_actual_standard_or_additional_version():
    result = alias_result(); prepared = projection(result)
    wrong = saved("prepared_database", prepared["manifest"])
    wrong["schema"] = "native_blast_prepared_database_manifest_v1"
    with pytest.raises(ContractError, match="saved_prepared_database_schema_conflict"):
        selected(result, selector(saved_data=["prepared_database"]), prepared=prepared, saved_data=[wrong])


def test_failed_native_preparation_can_be_fully_delivered_as_a_qualified_result():
    result = alias_result(rc=2)
    view, context = selected(result, selector(preparation={"fields": ["kind", "detail"]},
        artifacts=[{"direction": "output", "role": "alias_file", "ordinal": 0}]))
    assert view["status"]["state"] == "complete" and view["status"]["native_state"] == "failed"
    assert any(row["code"] == "native_nonzero_exit" and row["native_returncode"] == 2 for row in view["failures"])
    assert len(view["artifacts"]) == 1 and validate(view, context) == view


def test_unavailable_manifest_and_saved_manifest_have_specific_missing_requests():
    result = alias_result(rc=2); prepared = projection(result)
    view, _ = selected(result, selector(prepared_database=True, saved_data=["prepared_database"]), prepared=prepared)
    assert view["prepared_database"][0]["status"] == "unavailable"
    assert [row["reason"] for row in view["missing"]] == ["prepared_database_unavailable", "saved_data_unavailable"]
    assert any(row["code"] == "preparation_not_successful" for row in view["failures"])


def test_failed_result_cannot_borrow_successful_prepared_projection():
    with pytest.raises(ContractError, match="prepared_database_result_conflict"):
        selected(alias_result(rc=2), selector(prepared_database=True), prepared=projection(alias_result()))


def test_new_artifact_roles_keep_exact_selected_ordinals_and_reject_extra_grants():
    result = alias_result()
    view, context = selected(result, selector(artifacts=[{"direction": "input", "role": "identifier_list", "ordinal": 1}]))
    assert [row["occurrence_id"] for row in view["artifacts"]] == ["staged-ids"]
    assert view["record_refs"] == [SOURCE, result["inputs"][1]["artifact_ref"]]
    view["artifacts"].append({"source_ref": SOURCE, **result["outputs"][0]})
    with pytest.raises(ContractError, match="artifact_grant"):
        validate(view, context)


@pytest.mark.parametrize("mode", MODES)
def test_actual_worker_receipt_is_explicitly_selectable_for_every_new_pair(mode):
    receipt = occurrence("original-receipt", "preparation_receipt", b"synthetic sealed receipt",
        direction="output", fmt="json", path="/attempt/bundle.json")
    view = project_blast_utility_result(source_ref=SOURCE, operation=operation(mode), native_outcome=outcome(),
        result=None, prepared_database=None, occurrences=[receipt], failures=[], saved_data=[],
        selector=selector(artifacts=[{"direction": "output", "role": "preparation_receipt", "ordinal": 0}]))
    assert view["artifacts"] == [{"source_ref": SOURCE, **receipt}]
    assert view["record_refs"] == [SOURCE, receipt["artifact_ref"]]


@pytest.mark.parametrize("mode,kind", [("convert_gi_list", "identifier_list"), ("create_megablast_index", "megablast_index")])
def test_other_preparation_kind_details_remain_typed_and_prepared_manifest_unavailable(mode, kind):
    if mode == "convert_gi_list":
        source = occurrence("ids", "identifier_list")
        output = occurrence("binary", "identifier_list", direction="output", fmt="gi_list_binary", path="/attempt/out/ids.gil")
    else:
        source = occurrence("sequence", "sequence_input", b">s\nACGT\n", fmt="fasta")
        output = occurrence("index", "index_file", direction="output", fmt="blast_index_binary", path="/attempt/out/index.00.idx")
    result = populate(**common(operation(mode), inputs=[source], outputs=[output]))
    view, _ = selected(result, selector(preparation={"fields": ["kind", "detail"]}, prepared_database=True),
        prepared=projection(result))
    assert view["preparation"][0]["fields"] == {"kind": kind, "detail": result["detail"]}
    assert view["prepared_database"][0]["status"] == "unavailable"
    assert any(row["code"] == "semantic_validation_unavailable" for row in view["failures"])


@pytest.mark.parametrize("mode", MODES)
def test_exact_new_operation_pairs_admit_only_their_result_channel(mode):
    op = operation(mode)
    inspection = mode in {"inspect_seqid_list", "show_filters"}
    selection = selector(database_fields=["identifier_list_count"]) if inspection else selector(preparation={"fields": ["kind"]})
    assert validate_blast_utility_result_selector(selection, operation=op) == selection
    with pytest.raises(ContractError):
        validate_blast_utility_result_selector(selector(sequences={"selector_ordinals": [0], "sequence_fields": []}), operation=op)
    wrong = deepcopy(op); wrong["program"] = "blastdbcmd"
    with pytest.raises(ContractError):
        validate_blast_utility_result_selector(selection, operation=wrong)


@pytest.mark.parametrize("field", ["kind", "database_bindings", "materializations"])
def test_new_preparation_fields_are_not_retrofitted_to_legacy_operations(field):
    with pytest.raises(ContractError, match="preparation_fields_not_applicable"):
        validate_blast_utility_result_selector(selector(preparation={"fields": [field]}),
            operation=legacy_operation("create_sequence_database"))


def test_file_inspection_cannot_select_a_fabricated_database_artifact():
    with pytest.raises(ContractError, match="artifact_selection_not_applicable"):
        validate_blast_utility_result_selector(selector(artifacts=[
            {"direction": "input", "role": "database_file", "ordinal": None}]), operation=operation("inspect_seqid_list"))


def test_saved_result_version_must_agree_with_original_operation_on_replay():
    result, rows = list_inspection()
    view, context = selected(result, selector(saved_data=["result"]), occurrences=rows, saved_data=[saved("result", result)])
    view["saved_data"][0]["schema"] = "blast_database_inspection_v1"
    with pytest.raises(ContractError, match="saved_result_version"):
        validate(view, context)


def test_legacy_field_value_shape_and_selector_serialization_are_unchanged():
    selection = selector(database_fields=["database_sequence_count"])
    before = json.dumps(selection)
    view, context = legacy_project(legacy_inspection(), selection)
    assert view["database_fields"] == [{"source_ref": SOURCE, "database_key": "tiny",
        **context["result"]["native_fields"][0]}]
    assert "subject" not in view["database_fields"][0]
    assert json.dumps(validate_blast_utility_result_selector(selection, operation=context["operation"])) == before


def test_projection_and_prepared_validation_perform_no_io_or_native_parsing(monkeypatch):
    result = alias_result(); prepared = projection(result)

    def forbidden(*args, **kwargs):
        raise AssertionError("pure view attempted IO or native parsing")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("gene_annotation_episode.blast_preparation_inputs.parse_blast_alias_document", forbidden)
    view, _ = selected(result, selector(prepared_database=True, database_fields=["database_residue_count"]), prepared=prepared)
    assert view["database_fields"][0]["value"] == 13
    assert view["prepared_database"][0]["status"] == "available"
