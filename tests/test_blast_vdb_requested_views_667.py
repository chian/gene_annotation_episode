"""Pure requested-view checks; controlled context is not production custody."""
from copy import deepcopy
import builtins
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import jsonschema
import pytest

from gene_annotation_episode import blast_utility_result_views as views
from gene_annotation_episode.blast_utility_contracts import validate_blast_utility_result
from gene_annotation_episode.blast_vdb_utility_inputs import parse_blast_vdb_extraction, parse_blast_vdb_inspection
from gene_annotation_episode.domain import ContractError
from test_blast_vdb_utility_inputs_663 import supplied, occurrence, identity, provenance, INFO, AUTHENTIC, STDOUT_SHA
from test_blast_utility_result_views_629 import (
    project as legacy_project, selected_sequences, selector as legacy_selector,
)
from test_blast_utility_contracts_625 import extraction, inspection, integrity


def legacy_reference():
    schemas = getattr(views, "_LEGACY_FACT_SCHEMAS", views._FACT_SCHEMAS)
    selected = [
        legacy_project(extraction(), selected_sequences(0))[0],
        legacy_project(extraction(), legacy_selector())[0],
        legacy_project(inspection(), legacy_selector(database_fields=[inspection()["native_fields"][0]["field_name"]], include_checks=True))[0],
        legacy_project(integrity(), legacy_selector(integrity={"fields": ["observed_checked_count"]}))[0],
    ]
    return {"selector_v1": getattr(views, "NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA",
                                  views.NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA),
            "projection_fields": views.PROJECTION_FIELDS, "fact_schemas": schemas, "examples": selected}


def test_legacy_reference_capture_and_preservation():
    value = json.dumps(legacy_reference(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    directory = Path(os.environ["HMMER529_ATTEMPT"])
    baseline = os.environ.get("HMMER_NATIVE_ORACLE_VDB_VIEW_BASELINE")
    if baseline:
        assert value == Path(baseline).read_text()
    (directory / ("legacy_views_after.json" if baseline else "legacy_views_before.json")).write_text(value)


SOURCE = "source_original_vdb667"


def selector(**changes):
    return {**legacy_selector(), "version": "native_blast_utility_result_selector_v2", "paths": None,
            "vdb_context": False, **changes}


def sequences(values=(0,), *, kind="selector_ordinals", fields=(), text=("normalized_sequence",), member=False, **changes):
    return selector(sequences={"selection": {"kind": kind, "values": None if values is None else list(values)},
        "record_fields": list(fields), "sequence_fields": list(text), "include_vdb_identity": member}, **changes)


def inputs(raw=b"A\ta\t4\tacgt\n", **kwargs):
    args = supplied(raw, **kwargs)
    args["database_binding"]["source_ref"] = SOURCE
    return args


def project_args(args, selection, raw=None):
    if raw is None:
        raw = b"A\ta\t4\tacgt\n"
    parser = parse_blast_vdb_extraction if args["operation"]["mode"] == "extract_sequences" else parse_blast_vdb_inspection
    result = parser(raw, **args)
    db = [occurrence(b"controlled database", oid="db-file", role="database_file", fmt="unknown", direction="input"),
          occurrence(b"controlled metadata", oid="db-manifest", role="database_manifest", fmt="json", direction="input")]
    for binding in args["vdb_context"]["dependency_database_bindings"]:
        db.extend(occurrence(oid.encode(), oid=oid, role="database_file", fmt="unknown", direction="input")
                  for oid in binding["occurrence_ids"])
    occurrences = [*db, *args["operation_input_occurrences"], args["occurrence"], args["stderr_occurrence"]]
    slots = {}
    for item in occurrences:
        slot = item["direction"], item["role"]
        item["ordinal"] = slots.get(slot, 0)
        slots[slot] = item["ordinal"] + 1
    context = {"operation": args["operation"], "native_outcome": args["outcome"], "occurrences": occurrences,
        "database_binding": args["database_binding"], "failures": [],
        "operation_input_occurrences": args["operation_input_occurrences"], "vdb_context": args["vdb_context"]}
    return {"source_ref": SOURCE, "operation": args["operation"], "native_outcome": args["outcome"], "result": result,
        "prepared_database": None, "occurrences": occurrences, "selector": selection,
        "failures": [], "saved_data": [], "context": context}


def project(raw=b"A\ta\t4\tacgt\n", selection=None, **kwargs):
    args = project_args(inputs(raw, **kwargs), selection or sequences(), raw)
    return views.project_blast_utility_result(**args), args


def validate(view, args):
    return views.validate_blast_utility_projection(view, **{key: args[key] for key in
        ("source_ref", "operation", "native_outcome", "selector", "occurrences", "context")})


def test_versions_closed_sources_and_reference_namespace_schemas():
    assert views.NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA["anyOf"] == [
        views.NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA, views.NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA]
    assert views.blast_utility_projection_fields(selector()) == (*views.PROJECTION_FIELDS, "paths", "path_sections", "vdb_context")
    assert views.blast_utility_projection_fields(legacy_selector()) == views.PROJECTION_FIELDS
    assert len(views.FACT_SOURCES) == 14 and len(views.IDENTIFIER_NAMESPACES) == 4
    jsonschema.Draft202012Validator.check_schema(views.NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)
    for name, descriptor in views.blast_utility_fact_sources().items():
        jsonschema.Draft202012Validator.check_schema(descriptor["report_schema"])
        assert descriptor["report_schema"]["x-source"] == name
    def references(node):
        if isinstance(node, dict):
            if node.get("format") == "reference":
                yield node["x-reference-namespace"]
            for child in node.values():
                yield from references(child)
        elif isinstance(node, list):
            for child in node:
                yield from references(child)
    assert list(references(views.VDB_CONTEXT_SCHEMA)) == ["execution_result"]
    assert list(references(views.SEQUENCE_V2_SCHEMA)).count("artifact") == 0
    changed = views.blast_utility_fact_sources()
    changed[views.FACT_PREFIX + "vdb_context"]["report_schema"]["items"]["properties"].clear()
    assert views.blast_utility_fact_sources()[views.FACT_PREFIX + "vdb_context"]["report_schema"]["items"]["properties"]


@pytest.mark.parametrize("selection", [
    sequences((1,)), sequences(None, kind="native_row_ordinals"),
    sequences(fields=("native_reported_length",)), selector(database_fields=["vdb_sequence_count"]),
    selector(paths={"kinds": ["vdb"], "native_path_ordinals": None, "include_sections": False}),
    selector(prepared_database=True), selector(saved_data=["prepared_database"]),
    selector(integrity={"fields": []}), selector(preparation={"fields": []}),
    selector(artifacts=[{"direction": "output", "role": "extracted_sequences", "ordinal": None}]),
    selector(artifacts=[{"direction": "input", "role": "entry_batch", "ordinal": None}]),
    selector(artifacts=[{"direction": "output", "role": "database_list", "ordinal": None}]),
])
def test_selector_rejects_unrequested_modes_fields_and_artifacts_before_capture(selection):
    with pytest.raises(ContractError):
        views.validate_blast_utility_result_selector(selection, operation=inputs()["operation"])


def test_selector_version_all_mode_and_paths_applicability():
    with pytest.raises(ContractError, match="selector_operation_version_conflict"):
        views.validate_blast_utility_result_selector(legacy_selector(), operation=inputs()["operation"])
    with pytest.raises(ContractError, match="selector_operation_version_conflict"):
        views.validate_blast_utility_result_selector(selector(), operation=extraction()["operation"])
    for kind in ("all_native_sequences", "all_references"):
        op = inputs(kind=kind)["operation"]
        for values in (None, [], [4, 0]):
            chosen = sequences(values, kind="native_row_ordinals")
            assert views.validate_blast_utility_result_selector(chosen, operation=op) == chosen
        with pytest.raises(ContractError):
            views.validate_blast_utility_result_selector(sequences(), operation=op)
    with pytest.raises(ContractError):
        views.validate_blast_utility_result_selector(selector(database_fields=["database_sequence_count"]), operation=inputs(mode="info")["operation"])
    with pytest.raises(ContractError):
        views.validate_blast_utility_result_selector(selector(paths={"kinds": ["vdb_alias"], "native_path_ordinals": [], "include_sections": True}),
                                                     operation=inputs(mode="paths")["operation"])


def test_duplicate_entries_keep_original_requested_ordinals_without_unselected_fields():
    view, args = project(selection=sequences((1, 0)), selectors=("A", "A", "absent"))
    row = view["sequences"][0]
    assert row["selector_ordinals"] == [1, 0] and row["record_key"] == "stdout#/records/0"
    assert row["fields"] == {} and row["sequences"] == {"normalized_sequence": "ACGT"}
    assert row["field_qualifications"] == [] and "vdb_identity" not in row
    assert view["checks"] == view["vdb_context"] == view["artifacts"] == view["saved_data"] == []
    assert view["record_refs"] == [SOURCE] and view["status"]["state"] == "complete"
    assert validate(json.loads(json.dumps(view)), args) == view
    assert set(view) == set(views.PROJECTION_V2_FIELDS)


@pytest.mark.parametrize("symbols,length,count,reason", [
    ("acgt", "4", 4, None), ("ACGU", "4", None, "sequence_symbol_invalid"),
    ("ACGX", "4", None, "sequence_symbol_invalid"), ("ACGT", "3", None, "sequence_length_conflict"),
    ("ACGT", "N/A", None, "native_row_invalid"), ("", "0", None, "sequence_symbol_invalid"),
])
def test_shared_native_values_and_null_qualifications(symbols, length, count, reason):
    raw = f"A\tN/A\t{length}\t{symbols}\n".encode()
    view, args = project(raw, sequences(fields=views.VDB_RECORD_FIELDS, text=views.SEQUENCE_FIELDS))
    row, original = view["sequences"][0], args["result"]["records"][0]
    assert row["fields"] == {key: original[key] for key in views.VDB_RECORD_FIELDS}
    assert row["sequences"] == {key: original[key] for key in views.SEQUENCE_FIELDS}
    assert row["fields"]["returned_symbol_count"] == count
    qualifications = {item["pointer"]: item["reason"] for item in row["field_qualifications"]}
    assert qualifications["/fields/native_oid"] == qualifications["/fields/native_accession"] == "native_not_reported"
    assert qualifications["/fields/requested_range"] == qualifications["/fields/effective_range"] == "not_applicable"
    if reason is not None:
        assert qualifications["/fields/returned_symbol_count"] == reason
    if length == "N/A":
        assert qualifications["/fields/native_reported_length"] == "native_row_invalid"
    assert view["status"]["state"] == "complete" and view["record_refs"] == [SOURCE]


@pytest.mark.parametrize("field,value", [("returned_symbol_count", 3), ("normalized_sequence", "WRONG"),
    ("matched_selector_ordinals", []), ("record_key", "other#/records/0"), ("line_number", 2)])
def test_projector_rejects_forged_retained_common_values(field, value):
    _, args = project()
    args["result"]["records"][0][field] = value
    with pytest.raises(ContractError):
        views.project_blast_utility_result(**args)


def test_projector_uses_shared_validation_and_never_reads_parses_or_executes(monkeypatch):
    import gene_annotation_episode.blast_database_extraction as shared
    import gene_annotation_episode.blast_vdb_utility_inputs as parsers
    _, args = project()
    original, calls = shared.normalize_blast_utility_sequence_symbols, []
    def observed(*values):
        calls.append(values)
        return original(*values)
    def forbidden(*unused, **kwargs):
        raise AssertionError("pure projection tried input/native access or parsing")
    with monkeypatch.context() as patch:
        patch.setattr(shared, "normalize_blast_utility_sequence_symbols", observed)
        for name in ("parse_blast_vdb_extraction", "parse_blast_vdb_inspection", "normalize_blast_vdb_extraction"):
            patch.setattr(parsers, name, forbidden)
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "read_text", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        view = views.project_blast_utility_result(**args)
        assert validate(view, args) == view
    assert calls == [("acgt", "dna")]


@pytest.mark.parametrize("kind", ["all_native_sequences", "all_references"])
def test_native_row_gaps_and_null_vs_empty_enumeration(kind):
    raw = b"A\ta\t4\tACGT\nmalformed\nB\tb\t4\tACGT\n"
    view, _ = project(raw, sequences((2, 1, 0), kind="native_row_ordinals"), kind=kind)
    assert [row["native_row_ordinal"] for row in view["sequences"]] == [0, 2]
    assert all(row["selector_ordinals"] == [] and row["association"] == "not_applicable" for row in view["sequences"])
    assert view["missing"] == [{"version": "native_blast_utility_missing_fact_v2", "source_ref": SOURCE,
        "request": {"type": "native_row", "ordinal": 1}, "reason": "selection_unavailable"}]
    assert any(row["record_key"] == "stdout#/records/1" and row["line_number"] == 2 for row in view["failures"])
    assert view["status"]["state"] == "partial"
    all_rows, _ = project(raw, sequences(None, kind="native_row_ordinals"), kind=kind)
    assert len(all_rows["sequences"]) == 2 and not all_rows["missing"]
    empty, args = project(b"", sequences(None, kind="native_row_ordinals"), kind=kind)
    assert empty["sequences"] == empty["missing"] == [] and empty["status"]["state"] == "complete"
    args["result"] = None; args["context"] = None
    absent = views.project_blast_utility_result(**args)
    assert absent["missing"][0]["request"] == {"type": "native_enumeration"}
    assert absent["missing"][0]["reason"] == "result_unavailable"
    args["selector"] = sequences((), kind="native_row_ordinals")
    assert views.project_blast_utility_result(**args)["missing"] == []


@pytest.mark.parametrize("state", ["failed", "incomplete"])
def test_partial_native_outcomes_keep_good_rows_and_delivery_state(state):
    raw = b"A\ta\t4\tACGT\nmalformed\nB\tb\t4\tACGT\n"
    args = inputs(raw, selectors=("A", "B"), stderr=b"Failed to retrieve requested item\n")
    args["outcome"].update(state=state, returncode=2 if state == "failed" else None,
        writer_closed=state == "failed", inventory_complete=state == "failed")
    if state == "incomplete":
        args["stderr_occurrence"]["completeness"] = "unknown"
    values = project_args(args, sequences((0, 1), include_checks=True), raw)
    view = views.project_blast_utility_result(**values)
    assert view["status"]["native_state"] == state and view["status"]["state"] == "complete"
    assert view["status"]["result_completeness"] == "partial_selection"
    assert [row["native_row_ordinal"] for row in view["sequences"]] == [0, 2]
    assert any(row["occurrence_id"] == "stderr" for row in view["failures"])


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_missing_streams_allow_failure_only_views_without_context_claims(stream):
    _, args = project(selection=sequences(vdb_context=True, include_checks=True))
    args["result"] = None; args["context"] = None
    args["occurrences"] = [row for row in args["occurrences"] if row["role"] != stream]
    args["failures"] = [{"stage": "capture", "code": "output_missing", "occurrence_id": None,
        "record_key": None, "line_number": None, "native_returncode": None}]
    view = views.project_blast_utility_result(**args)
    assert view["sequences"] == view["vdb_context"] == view["checks"] == []
    assert {row["request"]["type"] for row in view["missing"]} == {"sequence_selector", "vdb_context", "checks"}
    assert {row["reason"] for row in view["missing"]} == {"result_unavailable"}
    assert view["record_refs"] == [SOURCE]


def member_args(kind="reference", *, sample=True):
    args = inputs()
    context = args["vdb_context"]
    context["source_inputs"][0]["dataset_key"] = "dataset-a"
    member = {"binding_key": "explicit-member", "native_identifier": "A", "dataset_key": "dataset-a",
        "member_kind": kind, "member_identifier": identity("explicit-A"), "relationship": "catalog_membership",
        "read_identity": {"native_read_name": "supplied-read", "spot_id": None, "read_index": 0, "source": provenance()} if kind == "read" else None,
        "reference_identity": {"identifier": identity("reference-A"), "full_length": 19, "sequence_sha256": None,
            "source": provenance()} if kind in {"reference", "wgs_sequence"} else None,
        "sample_key": "shared-sample-key" if sample else None, "provenance": provenance()}
    context["member_bindings"] = [member]
    if sample:
        context["sample_links"] = [{"dataset_key": "dataset-a", "link": {"sample_key": "shared-sample-key",
            "sample_identifier": identity("supplied-sample-A"), "biosample_identifier": None, "source": provenance()}}]
    return args


@pytest.mark.parametrize("kind", ["read", "reference", "wgs_sequence", "unknown"])
def test_explicit_member_qualifications_preserve_read_zero_and_full_extent(kind):
    args = project_args(member_args(kind), sequences(fields=("returned_symbol_count",), member=True, vdb_context=True))
    view = views.project_blast_utility_result(**args)
    row = view["sequences"][0]
    assert row["fields"] == {"returned_symbol_count": 4}
    identity = row["vdb_identity"]
    assert identity["member"] == args["result"]["records"][0]["vdb_member"]
    qualifications = {q["pointer"]: q["reason"] for q in identity["qualifications"]}
    assert qualifications["/member/member_identifier/version"] == "not_supplied"
    assert qualifications["/sample_links/0/link/biosample_identifier"] == "not_supplied"
    if kind == "read":
        assert identity["member"]["read_identity"]["read_index"] == 0
        assert "/member/read_identity/read_index" not in qualifications
    if kind in {"reference", "wgs_sequence"}:
        assert identity["member"]["reference_identity"]["full_length"] == 19
        assert qualifications["/member/read_identity"] == "not_applicable"
    assert view["record_refs"] == [SOURCE]


def test_sample_join_uses_dataset_and_key_and_never_provenance_access_grants():
    args = member_args()
    source = args["vdb_context"]["source_inputs"][0]
    second = deepcopy(source); second.update(ordinal=1, dataset_key="dataset-b")
    args["vdb_context"]["source_inputs"].append(second)
    selected = deepcopy(args["operation"]["parameters"]["database_selection"]["inputs"][0]); selected["ordinal"] = 1
    args["operation"]["parameters"]["database_selection"]["inputs"].append(selected)
    original = args["vdb_context"]["sample_links"][0]
    original["link"]["source"]["source_ref"] = "artifact_" + "e" * 64
    other = deepcopy(original); other["dataset_key"] = "dataset-b"
    other["link"]["sample_identifier"]["value"] = "different-sample"
    args["vdb_context"]["sample_links"] = [original, other, deepcopy(original)]
    values = project_args(args, sequences(member=True, vdb_context=True))
    view = views.project_blast_utility_result(**values)
    assert view["sequences"][0]["vdb_identity"]["sample_links"] == [original, original]
    assert view["vdb_context"][0]["context"]["sample_links"] == [original, other, original]
    assert view["record_refs"] == [SOURCE]
    bad = deepcopy(view); bad["record_refs"].append(original["link"]["source"]["source_ref"])
    with pytest.raises(ContractError, match="reference_grant_conflict"):
        validate(bad, values)
    bad = deepcopy(view); bad["sequences"][0]["vdb_identity"]["sample_links"][0] = other
    with pytest.raises(ContractError):
        validate(bad, values)


def test_member_absence_and_conflicts_are_distinct_and_common_validation_authoritative():
    absent, _ = project(selection=sequences(member=True))
    assert absent["sequences"][0]["vdb_identity"]["qualifications"] == [
        {"pointer": "/member", "reason": "not_supplied"}, {"pointer": "/sample_links", "reason": "member_unresolved"}]
    args = member_args()
    duplicate = deepcopy(args["vdb_context"]["member_bindings"][0]); duplicate["binding_key"] = "second-binding"
    args["vdb_context"]["member_bindings"].append(duplicate)
    values = project_args(args, sequences(member=True))
    view = views.project_blast_utility_result(**values)
    assert view["sequences"][0]["vdb_identity"]["member"] is None
    assert view["sequences"][0]["vdb_identity"]["qualifications"][0]["reason"] == "supplied_binding_conflict"
    forged = deepcopy(values["result"])
    forged["records"][0]["failures"] = []
    with pytest.raises(ContractError, match="member_conflict_unqualified"):
        validate_blast_utility_result(forged)
    unique = project_args(member_args(), sequences(member=True))["result"]
    unique["records"][0]["vdb_member"] = None
    with pytest.raises(ContractError, match="member_record_binding"):
        validate_blast_utility_result(unique)


def test_database_fields_keep_native_average_zero_null_and_locators():
    view, args = project(INFO, selector(database_fields=list(views.VDB_DATABASE_FIELDS)), mode="info")
    expected = [{"source_ref": SOURCE, "database_key": "controlled-vdb", **row} for row in args["result"]["native_fields"]]
    assert view["database_fields"] == expected
    fields = {row["field_name"]: row for row in view["database_fields"]}
    assert fields["vdb_average_sequence_bases"]["value"] == 99
    assert fields["vdb_sequence_count"]["value"] == 1002 and fields["vdb_total_unclipped_bases"]["value"] == 100300
    assert fields["vdb_csra_inputs"]["value"] is None and not view["missing"]
    zero = INFO.replace(b"1,002 sequences; 100,300", b"0 sequences; 0").replace(b"99 bases", b"0 bases")
    result, _ = project(zero, selector(database_fields=["vdb_sequence_count", "vdb_average_sequence_bases"]), mode="info")
    assert [row["value"] for row in result["database_fields"]] == [0, 0]


PATHS = b"VDB(s): \n/supplied/tiny.vdb\nreported-native-token\nreported-native-token\nVDB Alias File(s): None\nBlats DB Alias File(s): \n/supplied/known.nal\n"


def path_selection(*, kinds=views.VDB_PATH_KINDS, ordinals=None, sections=True, **changes):
    return selector(paths={"kinds": list(kinds), "native_path_ordinals": ordinals, "include_sections": sections}, **changes)


def path_args():
    args = inputs(PATHS, mode="paths_all")
    args["vdb_context"]["declared_dependencies"] = [{"role": "database", "ordinal": 7, "database_key": "controlled-vdb",
        "native_path_index": 0, "native_reference": "chosen-alias", "source": "vdblist",
        "list_occurrence_id": None, "list_entry_ordinal": None}]
    return project_args(args, path_selection(), PATHS)


def test_paths_literal_duplicates_section_presence_dependency_ordinals_and_namespaces():
    args = path_args(); view = views.project_blast_utility_result(**args)
    assert [row["native_path_ordinal"] for row in view["paths"]] == [0, 1, 2, 3]
    assert [row["matched_dependency_ordinals"] for row in view["paths"]] == [[7], [], [], []]
    assert [row["presence"] for row in view["path_sections"]] == ["reported_values", "reported_empty", "reported_values"]
    assert view["paths"][1]["native_path"] == view["paths"][2]["native_path"] == "reported-native-token"
    assert view["vdb_context"] == [] and view["record_refs"] == [SOURCE]
    assert views.projection_identifiers(view, views.PREFIX + "path_record") == ["stdout#/path_records/" + str(i) for i in range(4)]
    assert views.projection_identifiers(view, views.PREFIX + "path_section") == ["stdout#/path_sections/" + str(i) for i in range(3)]
    assert views.projection_identifiers(view, views.PREFIX + "occurrence") == ["stdout"]
    assert views.projection_identifiers(view, "source") == []


def test_path_filters_intersect_and_sections_do_not_depend_on_selected_rows():
    args = path_args(); args["selector"] = path_selection(kinds=("blast_db_alias", "vdb_alias"), ordinals=[3])
    view = views.project_blast_utility_result(**args)
    assert [row["native_path_ordinal"] for row in view["paths"]] == [3]
    assert [row["section_ordinal"] for row in view["path_sections"]] == [1, 2]
    args["selector"] = path_selection(kinds=("vdb",), ordinals=[3, 999], sections=False)
    view = views.project_blast_utility_result(**args)
    assert view["paths"] == view["path_sections"] == []
    assert [row["request"] for row in view["missing"]] == [{"type": "path_row", "ordinal": 3}, {"type": "path_row", "ordinal": 999}]
    args["selector"] = path_selection(kinds=(), ordinals=[999])
    assert views.project_blast_utility_result(**args)["missing"] == []


def test_path_empty_population_is_delivered_and_missing_sections_are_qualified():
    raw = b"VDB(s): None\n"
    view, args = project(raw, path_selection(), mode="paths_all")
    assert [row["presence"] for row in view["path_sections"]] == ["reported_empty", "not_reported", "not_reported"]
    assert {tuple(row["request"].values()) for row in view["missing"]} == {
        ("path_population", "vdb_alias"), ("path_population", "blast_db_alias"),
        ("path_section", "vdb_alias"), ("path_section", "blast_db_alias")}
    assert {row["reason"] for row in view["missing"]} == {"field_unavailable"}
    args["selector"] = path_selection(kinds=("vdb",), sections=False)
    assert views.project_blast_utility_result(**args)["status"]["state"] == "complete"
    args["result"] = None; args["context"] = None
    missing = views.project_blast_utility_result(**args)
    assert missing["missing"][0]["request"] == {"type": "path_population", "kind": "vdb"}
    assert missing["missing"][0]["reason"] == "result_unavailable"


@pytest.mark.parametrize("mutation", [
    lambda v: v["paths"][0].update(path_ref="stdout#/path_records/9"),
    lambda v: v["paths"][0].update(occurrence_id="stderr"),
    lambda v: v["paths"][0].update(native_path="/different/path"),
    lambda v: v["paths"][0].update(matched_dependency_ordinals=[9]),
    lambda v: v["paths"][0].update(database_key="other-db"),
    lambda v: v["path_sections"][0].update(section_ref="stdout#/path_sections/3"),
    lambda v: v["path_sections"][0].update(presence="reported_empty"),
])
def test_path_reference_and_dependency_forgery_rejected(mutation):
    args = path_args(); view = views.project_blast_utility_result(**args)
    mutation(view)
    with pytest.raises(ContractError):
        validate(view, args)


@pytest.mark.parametrize("field", ["operation", "database_binding", "operation_input_occurrences", "vdb_context"])
def test_retained_result_cannot_substitute_original_qualified_context(field):
    _, args = project()
    if field == "operation":
        args["result"][field]["parameters"]["line_length"] = 81
    elif field == "database_binding":
        args["result"][field]["source_ref"] = "source_sibling"
    elif field == "operation_input_occurrences":
        args["result"][field].append(deepcopy(args["occurrences"][0]))
    else:
        args["result"][field]["source_inputs"][0]["source"]["pointer"] = "/other"
    with pytest.raises(ContractError):
        views.project_blast_utility_result(**args)


def test_context_required_for_parsed_records_and_deep_copy_for_selected_context():
    view, args = project(selection=selector(vdb_context=True))
    assert view["vdb_context"][0]["context"] == args["result"]["vdb_context"]
    assert view["sequences"] == [] and view["record_refs"] == [SOURCE]
    changed = deepcopy(args); changed["context"] = None
    with pytest.raises(ContractError, match="qualified_context_required"):
        views.project_blast_utility_result(**changed)
    assert any(q == {"pointer": "/source_inputs/0/dataset_key", "reason": "not_supplied"}
               for q in view["vdb_context"][0]["qualifications"])
    view["vdb_context"][0]["context"]["source_inputs"][0]["snapshot"]["release"] = "changed"
    assert args["result"]["vdb_context"]["source_inputs"][0]["snapshot"]["release"] is None
    with pytest.raises(ContractError):
        validate(view, args)


def test_selected_artifact_saved_result_only_grants_and_empty_selection():
    _, args = project(selection=selector(artifacts=[{"direction": "output", "role": "stdout", "ordinal": None}], saved_data=["result"]))
    payload = json.dumps(args["result"], sort_keys=True).encode()
    digest = hashlib.sha256(payload).hexdigest()
    args["saved_data"] = [{"source_ref": SOURCE, "kind": "result", "artifact_ref": "artifact_" + digest,
        "sha256": digest, "size_bytes": len(payload), "schema": "blast_sequence_extraction_v2"}]
    view = views.project_blast_utility_result(**args)
    assert view["record_refs"] == [SOURCE, args["result"]["output_occurrence"]["artifact_ref"], "artifact_" + digest]
    assert view["sequences"] == view["vdb_context"] == []
    args["selector"] = selector()
    empty = views.project_blast_utility_result(**args)
    assert empty["record_refs"] == [SOURCE] and empty["artifacts"] == empty["saved_data"] == []


@pytest.mark.parametrize("mutation", [
    lambda v: v["sequences"][0]["fields"].update(native_identifier="A"),
    lambda v: v["sequences"][0]["sequences"].update(original_sequence="acgt"),
    lambda v: v["sequences"][0].update(selector_ordinals=[1]),
    lambda v: v["sequences"][0].update(source_ref="source_sibling"),
    lambda v: v["sequences"][0].update(database_key="other"),
    lambda v: v["sequences"][0].update(field_qualifications=[{"pointer": "/fields/native_oid", "reason": "not_supplied"}]),
    lambda v: v["status"].update(native_state="failed"),
])
def test_unrequested_fields_wrong_original_sources_and_invented_qualifiers_reject(mutation):
    view, args = project()
    mutation(view)
    with pytest.raises(ContractError):
        validate(view, args)


def test_authentic_retained_two_rows_requested_values_only():
    raw = (AUTHENTIC / "stdout.bin").read_bytes()
    stderr = (AUTHENTIC / "stderr.bin").read_bytes()
    assert len(raw) == 594 and hashlib.sha256(raw).hexdigest() == STDOUT_SHA and stderr == b""
    names = ("gnl|SRA|ERR3487613.1.1", "gnl|SRA|ERR3487613.1.2")
    view, _ = project(raw, sequences((0, 1), fields=("native_reported_length", "native_length_basis", "returned_symbol_count"),
        member=True), selectors=names, stderr=stderr)
    assert [row["fields"]["native_reported_length"] for row in view["sequences"]] == [250, 250]
    assert [row["fields"]["returned_symbol_count"] for row in view["sequences"]] == [250, 250]
    assert all(row["vdb_identity"]["member"] is None for row in view["sequences"])
    assert view["record_refs"] == [SOURCE]


def test_selected_context_cannot_be_replaced_with_fabricated_missing():
    view, args = project(selection=selector(vdb_context=True))
    view["vdb_context"] = []
    view["missing"] = [{"version": "native_blast_utility_missing_fact_v2", "source_ref": SOURCE,
        "request": {"type": "vdb_context"}, "reason": "result_unavailable"}]
    view["status"]["state"] = "unavailable"
    with pytest.raises(ContractError, match="context_selection_conflict"):
        validate(view, args)


def test_fact_unions_reject_impossible_vdb_missing_names_and_section_indices():
    for request in ({"type": "database_field", "field_name": "database_sequence_count"},
                    {"type": "saved_data", "kind": "prepared_database"}):
        with pytest.raises(ContractError):
            views.validate_blast_utility_fact_values(views.FACT_PREFIX + "missing", [{
                "version": "native_blast_utility_missing_fact_v2", "source_ref": SOURCE,
                "request": request, "reason": "result_unavailable"}])
    args = path_args(); view = views.project_blast_utility_result(**args)
    row = view["path_sections"][1]
    row.update(section_ordinal=8, section_ref="stdout#/path_sections/8")
    with pytest.raises(ContractError, match="path_section_identity_conflict"):
        views.validate_blast_utility_fact_values(views.FACT_PREFIX + "path_sections", [row])


def test_declared_batch_list_and_original_bundle_artifacts_select_without_database_grants():
    args = inputs()
    batch = occurrence(b"A\n", oid="batch", role="entry_batch", fmt="text", direction="input")
    listing = occurrence(b"/supplied/tiny.vdb\n", oid="database-list", role="database_list", fmt="text", direction="input")
    args["operation"]["input_occurrence_ids"].extend(["batch", "database-list"])
    args["operation"]["parameters"]["selection"].update(source="entry_batch", batch_occurrence_id="batch")
    database = args["operation"]["parameters"]["database_selection"]
    database.update(source="dbs_file", list_occurrence_id="database-list")
    database["inputs"][0]["list_entry_ordinal"] = 0
    args["operation_input_occurrences"] = [batch, listing]
    chosen = selector(artifacts=[{"direction": "input", "role": "entry_batch", "ordinal": None},
        {"direction": "input", "role": "database_list", "ordinal": None},
        {"direction": "output", "role": "preparation_receipt", "ordinal": None}])
    values = project_args(args, chosen)
    bundle = occurrence(b"controlled bundle receipt", oid="bundle", role="preparation_receipt", fmt="json")
    values["occurrences"].append(bundle)
    view = views.project_blast_utility_result(**values)
    assert [row["occurrence_id"] for row in view["artifacts"]] == ["batch", "database-list", "bundle"]
    assert view["record_refs"] == [SOURCE, batch["artifact_ref"], listing["artifact_ref"], bundle["artifact_ref"]]
    assert view["vdb_context"] == view["sequences"] == []


def test_exact_accession_and_explicit_association_do_not_guess_identifier_aliases():
    raw = b"gnl|SRA|RUN.1.2\tSRA:RUN.1.2\t4\tACGT\n"
    args = inputs(raw, selectors=("RUN.1.2", "SRA:RUN.1.2", "SRA:RUN.1.2"))
    selected = sequences((2, 0, 1), fields=("native_identifier", "native_accession"), member=True)
    values = project_args(args, selected, raw)
    view = views.project_blast_utility_result(**values)
    assert view["sequences"][0]["selector_ordinals"] == [2, 1]
    assert view["sequences"][0]["vdb_identity"]["member"] is None
    assert view["missing"][0]["request"] == {"type": "sequence_selector", "ordinal": 0}
    values["result"] = parse_blast_vdb_extraction(raw, record_bindings=[
        {"native_row_ordinal": 0, "selector_ordinals": [0, 1, 2]}], **args)
    explicit = views.project_blast_utility_result(**values)
    assert explicit["sequences"][0]["association"] == "explicit"
    assert explicit["sequences"][0]["selector_ordinals"] == [2, 0, 1] and not explicit["missing"]


def test_paths_with_separate_declared_dependency_do_not_open_native_locations(monkeypatch):
    raw = b"VDB(s): \n/supplied/secondary.vdb\nunknown-bare-token\n"
    args = inputs(raw, mode="paths")
    dependency = deepcopy(args["database_binding"])
    dependency.update(database_key="secondary", occurrence_ids=["secondary-file"], native_paths=["/unused.vdb", "/supplied/secondary.vdb"])
    args["vdb_context"]["dependency_database_bindings"] = [dependency]
    args["vdb_context"]["declared_dependencies"] = [{"role": "database", "ordinal": 11,
        "database_key": "secondary", "native_path_index": 1, "native_reference": "supplied-alias", "source": "vdblist",
        "list_occurrence_id": None, "list_entry_ordinal": None}]
    values = project_args(args, path_selection(kinds=("vdb",), vdb_context=True), raw)
    def forbidden(*unused, **kwargs):
        raise AssertionError("native report path was opened")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "read_text", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        view = views.project_blast_utility_result(**values)
    assert [row["matched_dependency_ordinals"] for row in view["paths"]] == [[11], []]
    assert view["record_refs"] == [SOURCE]
    qualifications = view["vdb_context"][0]["qualifications"]
    assert {"pointer": "/declared_dependencies/0/list_occurrence_id", "reason": "not_applicable"} in qualifications
    assert {"pointer": "/dependency_database_bindings/0/identity/version", "reason": "not_supplied"} in qualifications
    forged = deepcopy(values); forged["result"]["path_records"][0]["matched_dependency_ordinals"] = [22]
    with pytest.raises(ContractError, match="path_dependency_reference"):
        views.project_blast_utility_result(**forged)


def test_empty_delivered_enumeration_still_partial_when_selected_artifact_missing():
    selection = sequences(None, kind="native_row_ordinals", artifacts=[{"direction": "output", "role": "diagnostics", "ordinal": 0}])
    view, _ = project(b"", selection, kind="all_native_sequences")
    assert view["sequences"] == [] and view["status"]["state"] == "partial"
    assert view["missing"][0]["reason"] == "artifact_unavailable"


def test_failure_only_context_still_rejects_malformed_input_occurrences_as_contract_failure():
    _, args = project(selection=selector())
    args["result"] = None
    args["context"]["operation_input_occurrences"] = [{"missing": "occurrence identity"}]
    with pytest.raises(ContractError):
        views.project_blast_utility_result(**args)


@pytest.mark.parametrize("dependency", [False, True])
def test_database_side_list_selection_uses_primary_or_declared_dependency_membership(dependency):
    args = inputs()
    binding = args["database_binding"]
    if dependency:
        binding = deepcopy(binding)
        binding.update(database_key="dependency", occurrence_ids=["dependency-file"])
        args["vdb_context"]["dependency_database_bindings"] = [binding]
    binding["occurrence_ids"].append("database-side-list")
    args["operation"]["input_occurrence_ids"].append("database-side-list")
    selected = selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": None}])
    assert views.validate_blast_utility_result_selector(selected, operation=args["operation"]) == selected
    values = project_args(args, selected)
    listing = occurrence(b"/supplied/tiny.vdb\n", oid="database-side-list", role="database_list", fmt="text", direction="input")
    if dependency:
        existing = next(row for row in values["occurrences"] if row["occurrence_id"] == "database-side-list")
        existing.clear(); existing.update(listing)
    else:
        values["occurrences"].append(listing)
    view = views.project_blast_utility_result(**values)
    assert view["artifacts"] == [{"source_ref": SOURCE, **listing}]
    assert view["record_refs"] == [SOURCE, listing["artifact_ref"]]
    assert values["context"]["operation_input_occurrences"] == values["result"]["operation_input_occurrences"] == []


@pytest.mark.parametrize("context_available", [False, True])
def test_unbound_database_list_cannot_grant_an_artifact(context_available):
    _, values = project(selection=selector())
    values["selector"] = selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": None}])
    listing = occurrence(b"undeclared list", oid="unbound-list", role="database_list", fmt="text", direction="input")
    values["occurrences"].append(listing)
    if not context_available:
        values["result"] = None; values["context"] = None
    with pytest.raises(ContractError):
        views.project_blast_utility_result(**values)


def test_declared_database_side_list_missing_capture_is_qualified_without_grant():
    _, values = project()
    values["result"] = None
    values["selector"] = selector(artifacts=[{"direction": "input", "role": "database_list", "ordinal": None}])
    values["context"]["vdb_context"]["declared_dependencies"] = [{"role": "database", "ordinal": 4,
        "database_key": "controlled-vdb", "native_path_index": 0, "native_reference": "/supplied/tiny.vdb",
        "source": "vdblist_file", "list_occurrence_id": "uncaptured-original-list", "list_entry_ordinal": 0}]
    view = views.project_blast_utility_result(**values)
    assert view["artifacts"] == [] and view["record_refs"] == [SOURCE]
    assert view["missing"][0]["reason"] == "artifact_unavailable"
    values["context"]["vdb_context"]["declared_dependencies"] = []
    with pytest.raises(ContractError, match="artifact_selection_not_applicable"):
        views.project_blast_utility_result(**values)
