"""Pure VDB branches of the common BLAST supporting-result contracts.

These contracts preserve supplied source relationships and native omissions.
They perform no acquisition, native execution, search-context construction or
scientific scoring. Source pointers identify evidence; they do not grant access
to its bytes or authenticate metadata content. Ports: 643/001 and 643/002.
"""
from __future__ import annotations

from copy import deepcopy

from .domain import ContractError
from .blast_preparation_contracts import DATABASE_DEPENDENCY_SCHEMA
from .native_blast_standard_database_contracts import (
    _absolute, _array, _copy, _nullable, _object, _schema,
)

_TEXT = {"type": "string"}
_STR = {"type": "string", "minLength": 1, "pattern": r"(?s).*\S.*"}
_INT = {"type": "integer", "minimum": 0}
_POS = {"type": "integer", "minimum": 1}
_BOOL = {"type": "boolean"}
_SHA = {"type": "string", "pattern": r"[0-9a-f]{64}"}
_NULL = {"type": "null"}


def _enum(text):
    return {"enum": text.split()}


def _unique(schema, **kwargs):
    return _array(schema, uniqueItems=True, **kwargs)


_IDENTITY = _object({"namespace": _STR, "value": _STR, "version": _nullable(_STR)})
_PROVENANCE = _object({"source_ref": _STR, "pointer": _TEXT})
_SELECTED_INPUT = _object({"kind": _enum("accession path alias"), "value": _STR})
_SOURCE_INPUT = _object({
    "ordinal": _INT, "selected_input": _SELECTED_INPUT, "binding_native_path": _STR,
    "dataset_key": _nullable(_STR), "dataset_type": _enum("sra csra wgs unknown"),
    "snapshot": _object({"release": _nullable(_STR), "snapshot_id": _nullable(_STR),
                         "manifest_sha256": _nullable(_SHA)}),
    "run_identifiers": _array(_IDENTITY), "source": _PROVENANCE,
})
VDB_MEMBER_SCHEMA = _object({
    "binding_key": _STR, "native_identifier": _STR, "dataset_key": _STR,
    "member_kind": _enum("read reference wgs_sequence unknown"),
    "member_identifier": _IDENTITY, "relationship": _enum("reported_origin catalog_membership"),
    "read_identity": _nullable(_object({"native_read_name": _STR, "spot_id": _nullable(_STR),
        "read_index": _nullable(_INT), "source": _PROVENANCE})),
    "reference_identity": _nullable(_object({"identifier": _IDENTITY,
        "full_length": _nullable(_POS), "sequence_sha256": _nullable(_SHA), "source": _PROVENANCE})),
    "sample_key": _nullable(_STR), "provenance": _PROVENANCE,
})
VDB_UTILITY_CONTEXT_SCHEMA = _object({
    "version": {"const": "blast_vdb_utility_context_v1"},
    "source_inputs": _array(_SOURCE_INPUT, minItems=1),
    "selection_kind": _nullable(_enum("entries all_native_sequences all_references")),
    "include_filtered_reads": _BOOL,
    "entry_identifier_bindings": _array(_object({"selector_ordinal": _INT,
        "identifier": _IDENTITY, "source": _PROVENANCE})),
    "member_bindings": _array(VDB_MEMBER_SCHEMA),
    "sample_links": _array(_object({"dataset_key": _STR, "link": _object({
        "sample_key": _STR, "sample_identifier": _IDENTITY,
        "biosample_identifier": _nullable(_IDENTITY), "source": _PROVENANCE})})),
    "declared_dependencies": _array(DATABASE_DEPENDENCY_SCHEMA),
})
_DATABASE_SELECTION = _object({"source": _enum("db dbs_file"),
    "inputs": _array(_object({"ordinal": _INT, "kind": _enum("path alias accession"),
        "value": _STR, "binding_native_path": _STR, "list_entry_ordinal": _nullable(_INT)}), minItems=1),
    "list_occurrence_id": _nullable(_STR)})
_SELECTOR = _object({"ordinal": _INT, "value": _STR})
_PATH_SECTION = _object({"kind": _enum("vdb vdb_alias blast_db_alias"),
    "header_line_number": _nullable(_POS), "presence": _enum("reported_empty reported_values not_reported")})
_PATH_RECORD = _object({"kind": _enum("vdb vdb_alias blast_db_alias"),
    "section_ordinal": _INT, "native_path_ordinal": _INT, "native_path": _STR,
    "line_number": _POS, "matched_dependency_ordinals": _unique(_INT)})
_VARIANTS = [
    ("extract_sequences", _object({"kind": {"const": "entries"}, "source": {"const": source},
        "selectors": _array(_SELECTOR, minItems=1),
        "batch_occurrence_id": _STR if source == "entry_batch" else _NULL}), _BOOL, "blast_vdb_cmd_table_v1")
    for source in ("entry", "entry_batch")
] + [
    ("extract_sequences", _object({"kind": {"const": kind}}),
     {"const": False} if kind == "all_references" else _BOOL, "blast_vdb_cmd_table_v1")
    for kind in ("all_native_sequences", "all_references")
] + [(mode, _NULL, {"const": False}, fmt) for mode, fmt in (
    ("info", "blast_vdb_info_text_v1"), ("paths", "blast_vdb_paths_text_v1"),
    ("paths_all", "blast_vdb_paths_text_v1"))]
VDB_OPERATION_SCHEMA = {"anyOf": [_object({
    "version": {"const": "blast_utility_operation_v3"}, "program": {"const": "blast_vdb_cmd"},
    "mode": {"const": mode}, "input_occurrence_ids": _unique(_STR),
    "database_key": _STR, "molecule": {"const": "dna"},
    "parameters": _object({"database_selection": _DATABASE_SELECTION, "line_length": _POS,
        "selection": selection, "include_filtered_reads": filtered, "output_format": {"const": fmt}}),
}) for mode, selection, filtered, fmt in _VARIANTS]}

# Each field name fixes its population; no count is a search denominator or a
# scientific confidence value. Native average remains reported, never derived.
_FIELD_TYPES = {
    "vdb_selected_inputs": (_array(_TEXT), "native_input_tokens", "Selected invocation strings."),
    "vdb_resolved_paths": (_array(_TEXT), "paths", "Resolved VDB selection."),
    "vdb_sequence_count": (_INT, "sequences", "Native GetVDBStats(m_allDbs) population."),
    "vdb_total_unclipped_bases": (_INT, "nt", "Same native population, reported (unclipped) label."),
    "vdb_longest_sequence_bases": (_INT, "nt", "Same native GetVDBStats population."),
    "vdb_average_sequence_bases": (_INT, "nt", "Native reported integer average in that population."),
    "vdb_csra_inputs": (_array(_TEXT), "paths", "Reported CSRA subset."),
    "vdb_reference_sequence_count": (_INT, "sequences", "CSRA reference population."),
    "vdb_reference_total_bases": (_INT, "nt", "CSRA reference population."),
}


def build_vdb_utility_schemas(base: dict) -> dict:
    """Build detached additive branches without changing any legacy schema."""
    occurrence = deepcopy(base["ArtifactOccurrence"])
    occurrence["properties"]["role"]["enum"] += ["entry_batch"]
    occurrence["properties"]["native_format"]["enum"] += [
        "blast_vdb_cmd_table_v1", "blast_vdb_info_text_v1", "blast_vdb_paths_text_v1"]
    primitive = deepcopy(base["NativeField"]["anyOf"][0]["properties"])
    fields = {"anyOf": [_object({**primitive, "field_name": {"const": name, "description": meaning},
        "value": _nullable(kind), "unit": {"const": unit}})
        for name, (kind, unit, meaning) in _FIELD_TYPES.items()]}
    context = _object({**deepcopy(VDB_UTILITY_CONTEXT_SCHEMA["properties"]),
        "dependency_database_bindings": _array(base["DatabaseBinding"])})
    extraction = deepcopy(base["SequenceExtraction"]["properties"])
    record = deepcopy(extraction["records"]["items"]["properties"])
    record.update({"vdb_member": _nullable(VDB_MEMBER_SCHEMA),
        "association": _enum("exact explicit unresolved not_applicable"),
        "native_oid": _NULL, "native_length_basis": {"const": "returned_sequence"},
        "requested_range": _NULL, "effective_range": _NULL, "molecule": {"const": "dna"}})
    additions = {"operation": VDB_OPERATION_SCHEMA, "output_occurrence": occurrence,
        "stderr_occurrence": occurrence, "operation_input_occurrences": _array(occurrence),
        "vdb_context": context}
    extraction.update({**additions, "version": {"const": "blast_sequence_extraction_v2"},
        "records": _array(_object(record)),
        "scope": _object({"kind": _enum("selected_entries all_native_sequences all_references")})})
    inspection = deepcopy(base["DatabaseInspection"]["properties"])
    inspection.update({**additions, "version": {"const": "blast_database_inspection_v3"},
        "native_fields": _array(fields), "path_sections": _array(_PATH_SECTION),
        "path_records": _array(_PATH_RECORD)})
    return deepcopy({"ArtifactOccurrence": occurrence, "NativeField": fields,
        "Operation": VDB_OPERATION_SCHEMA, "SequenceExtraction": _object(extraction),
        "DatabaseInspection": _object(inspection), "VDBUtilityContext": context,
        "VDBMember": VDB_MEMBER_SCHEMA})


def _require(condition, code):
    if not condition:
        raise ContractError("blast_utility_" + code)


def _validated(value, schema):
    try:
        value = _copy(value)
        _schema(value, schema)
    except RecursionError as error:
        raise ContractError("blast_utility_finite_json_required") from error
    except ValueError as error:
        code = str(error).removeprefix("native_blast_standard_database_")
        if code.startswith("schema:"):
            code = "schema_invalid"
        raise ContractError("blast_utility_" + code) from error
    return value


def _absolute_path(value):
    try:
        _absolute(value)
    except ValueError as error:
        raise ContractError("blast_utility_absolute_normalized_path_required") from error


def _token(value):
    return bool(value) and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value)


def validate_vdb_utility_operation(value: dict) -> dict:
    """Validate the seven exact parameter variants, retaining order/duplicates."""
    value = _validated(value, VDB_OPERATION_SCHEMA)
    p = value["parameters"]
    database = p["database_selection"]
    rows = database["inputs"]
    _require([r["ordinal"] for r in rows] == list(range(len(rows))), "vdb_input_ordinals")
    file = database["source"] == "dbs_file"
    _require((database["list_occurrence_id"] is not None) == file, "vdb_database_list_selection")
    for row in rows:
        _absolute_path(row["binding_native_path"])
        _require(_token(row["value"]), "vdb_database_token")
        if row["kind"] == "path":
            _absolute_path(row["value"])
            _require(row["value"] == row["binding_native_path"], "vdb_path_selection")
        _require((row["list_entry_ordinal"] is not None) == file, "vdb_database_list_location")
    if file:
        _require([r["list_entry_ordinal"] for r in rows] == list(range(len(rows))), "vdb_database_list_location")
    refs = [database["list_occurrence_id"]] if file else []
    selection = p["selection"]
    if selection is not None and selection["kind"] == "entries":
        selectors = selection["selectors"]
        _require([s["ordinal"] for s in selectors] == list(range(len(selectors))), "selector_ordinals")
        for selector in selectors:
            raw = selector["value"]
            _require(_token(raw) and raw.lower() != "all" and "," not in raw, "selector_value")
        if selection["source"] == "entry_batch":
            refs.append(selection["batch_occurrence_id"])
    _require(len(refs) == len(set(refs)), "dependency_role_conflict")
    _require(set(refs) <= set(value["input_occurrence_ids"]), "result_input_reference")
    return value


def _provenance(value):
    from .blast_utility_contracts import _pointer
    _pointer(value["pointer"])


def validate_vdb_member_relationships(value):
    """Relationships present in a supplied member; no sequence-ID inference."""
    kind, read, reference = value["member_kind"], value["read_identity"], value["reference_identity"]
    _require(read is None or kind == "read", "vdb_member_identity_kind")
    _require(reference is None or kind in {"reference", "wgs_sequence"}, "vdb_member_identity_kind")
    _provenance(value["provenance"])
    for identity in (read, reference):
        if identity is not None:
            _provenance(identity["source"])


def validate_vdb_context_relationships(value):
    """Internal closed-context relationships; the public port also binds selection."""
    inputs, members = value["source_inputs"], value["member_bindings"]
    _require([r["ordinal"] for r in inputs] == list(range(len(inputs))), "vdb_input_ordinals")
    datasets = {r["dataset_key"] for r in inputs if r["dataset_key"] is not None}
    _require(len({m["binding_key"] for m in members}) == len(members), "vdb_member_binding_identity")
    for row in inputs:
        _absolute_path(row["binding_native_path"])
        _provenance(row["source"])
    for row in value["entry_identifier_bindings"]:
        _provenance(row["source"])
    for row in value["sample_links"]:
        _require(row["dataset_key"] in datasets, "vdb_sample_dataset_reference")
        _provenance(row["link"]["source"])
    for member in members:
        validate_vdb_member_relationships(member)
        _require(member["dataset_key"] in datasets, "vdb_member_dataset_reference")
        if member["sample_key"] is not None:
            links = [r["link"] for r in value["sample_links"] if r["dataset_key"] == member["dataset_key"]
                     and r["link"]["sample_key"] == member["sample_key"]]
            identities = [{k: row[k] for k in ("sample_identifier", "biosample_identifier")} for row in links]
            _require(bool(identities) and all(i == identities[0] for i in identities), "vdb_member_sample_link")


def validate_vdb_utility_context(value: dict, *, operation: dict,
        database_binding: dict | None = None,
        operation_input_occurrences: list[dict] | None = None) -> dict:
    """Bind supplied source/view/member context to the exact selected operation.

    Without a database binding, this validates selection and internal links only.
    Captured metadata content and sample/representation links are authenticated by
    the original-context worker, not inferred by this pure contract.
    """
    from .blast_utility_contracts import SCHEMAS, validate_blast_utility_record as core
    value = _validated(value, SCHEMAS["VDBUtilityContext"])
    operation = validate_vdb_utility_operation(operation)
    validate_vdb_context_relationships(value)
    p = operation["parameters"]
    selection = p["selection"]
    kind = None if selection is None else selection["kind"]
    _require(value["selection_kind"] == kind and value["include_filtered_reads"] == p["include_filtered_reads"],
             "vdb_selected_view_conflict")
    original = p["database_selection"]["inputs"]
    _require(len(value["source_inputs"]) == len(original), "vdb_source_input_population")
    for row, selected in zip(value["source_inputs"], original):
        _require(row["ordinal"] == selected["ordinal"] and
            row["selected_input"] == {"kind": selected["kind"], "value": selected["value"]} and
            row["binding_native_path"] == selected["binding_native_path"], "vdb_source_input_conflict")
    if kind == "all_references":
        _require(any(r["dataset_type"] == "csra" for r in value["source_inputs"]), "vdb_csra_input_required")
    bindings = value["entry_identifier_bindings"]
    selectors = selection["selectors"] if kind == "entries" else []
    _require([b["selector_ordinal"] for b in bindings] == [s["ordinal"] for s in selectors], "vdb_entry_binding_population")
    for binding, selector in zip(bindings, selectors):
        _require(binding["identifier"]["value"] == selector["value"], "vdb_entry_binding_value")
    if database_binding is not None:
        database_binding = core("DatabaseBinding", database_binding)
        _require(database_binding["kind"] == "vdb" and database_binding["molecule"] in {"dna", "unknown"}, "database_kind_conflict")
        _require(database_binding["database_key"] == operation["database_key"], "result_database_key")
        _require(all(r["binding_native_path"] in database_binding["native_paths"] for r in original), "vdb_binding_native_path")
    dependency_bindings = [core("DatabaseBinding", b) for b in value["dependency_database_bindings"]]
    databases = ([database_binding] if database_binding is not None else []) + dependency_bindings
    by_database = {b["database_key"]: b for b in databases}
    _require(len(by_database) == len(databases), "duplicate_database_key")
    database_ids = [oid for b in databases for oid in b["occurrence_ids"]]
    _require(len(database_ids) == len(set(database_ids)), "duplicate_occurrence_identity")
    dependencies = value["declared_dependencies"]
    _require(len({d["ordinal"] for d in dependencies}) == len(dependencies), "vdb_dependency_ordinals")
    for dependency in dependencies:
        key = dependency["database_key"]
        # The optional primary binding is required to validate a dependency to it.
        _require(key in by_database, "vdb_dependency_database_reference")
        _require(dependency["native_path_index"] < len(by_database[key]["native_paths"]), "vdb_dependency_native_path")
        file = dependency["source"] in {"dblist_file", "vdblist_file"}
        _require((dependency["list_occurrence_id"] is not None) == file and
                 (dependency["list_entry_ordinal"] is not None) == file, "vdb_dependency_list_reference")
    if operation_input_occurrences is not None:
        rows = [core("ArtifactOccurrence", r) for r in operation_input_occurrences]
        ids = [r["occurrence_id"] for r in rows]
        database_ids = set(database_ids)
        _require(len(ids) == len(set(ids)) and not set(ids) & database_ids, "duplicate_occurrence_identity")
        _require(all(r["direction"] == "input" for r in rows), "vdb_operation_input_direction")
        _require(ids == [i for i in operation["input_occurrence_ids"] if i not in database_ids], "vdb_operation_input_population")
        by_id = {r["occurrence_id"]: r for r in rows}
        requested_files = [(p["database_selection"]["list_occurrence_id"], "database_list")]
        if kind == "entries":
            requested_files.append((selection["batch_occurrence_id"], "entry_batch"))
        for oid, role in requested_files:
            if oid is not None:
                _require(oid in by_id and by_id[oid]["role"] == role and by_id[oid]["native_format"] == "text",
                         "vdb_operation_input_role")
        for dependency in dependencies:
            oid = dependency["list_occurrence_id"]
            if oid is not None:
                _require(oid in by_id or oid in database_ids, "vdb_dependency_list_reference")
                if oid in by_id:
                    _require(by_id[oid]["role"] == "database_list" and by_id[oid]["native_format"] == "text",
                             "vdb_dependency_list_reference")
                # Database-side IDs have no descriptor in this pure result.
                # Their original role/list bytes must be authenticated by the
                # captured-context worker, without inventing another descriptor.
                if oid == p["database_selection"]["list_occurrence_id"]:
                    index = dependency["list_entry_ordinal"]
                    _require(index < len(original), "vdb_dependency_list_entry")
                    selected = original[index]
                    bound = by_database[dependency["database_key"]]["native_paths"][dependency["native_path_index"]]
                    _require(dependency["native_reference"] == selected["value"] and
                             bound == selected["binding_native_path"], "vdb_dependency_list_entry")
    return value


def _result_context(value, modes):
    from .blast_utility_contracts import _occurrences, _outcome, validate_blast_utility_record as core
    op, binding, outcome = value["operation"], value["database_binding"], value["original_outcome"]
    validate_vdb_utility_operation(op)
    _require(op["mode"] in modes, "result_operation")
    _outcome(outcome)
    validate_vdb_utility_context(value["vdb_context"], operation=op, database_binding=binding,
        operation_input_occurrences=value["operation_input_occurrences"])
    out, stderr = value["output_occurrence"], value["stderr_occurrence"]
    occurrences = _occurrences([core("ArtifactOccurrence", occurrence)
        for occurrence in [*value["operation_input_occurrences"], out, stderr]])
    known = {oid for b in [binding, *value["vdb_context"]["dependency_database_bindings"]]
             for oid in b["occurrence_ids"]}
    _require(not known & occurrences.keys(), "duplicate_occurrence_identity")
    known.update(occurrences)
    _require(set(op["input_occurrence_ids"]) <= known, "result_input_reference")
    _require(out["direction"] == stderr["direction"] == "output" and stderr["role"] == "stderr"
             and stderr["native_format"] == "text", "vdb_output_stream")
    _require(out["native_format"] == op["parameters"]["output_format"], "vdb_output_format")
    codes = {f["code"] for f in value["failures"]}
    if outcome["state"] == "failed":
        _require(("native_nonzero_exit" if outcome["started"] else "native_start_failed") in codes,
                 "native_outcome_unqualified")
    if not outcome["writer_closed"]:
        _require("output_writer_not_closed" in codes, "capture_unqualified")
    if not outcome["inventory_complete"]:
        _require("output_inventory_incomplete" in codes, "capture_unqualified")
    for stream in (out, stderr):
        if stream["completeness"] != "complete":
            _require(any(f["code"] in {"output_completeness_unestablished", "output_missing"}
                         and f["occurrence_id"] == stream["occurrence_id"] for f in value["failures"]), "capture_unqualified")
    return known, known | {b["database_key"] for b in [binding, *value["vdb_context"]["dependency_database_bindings"]]}


def validate_vdb_sequence_extraction(value: dict) -> dict:
    """Validate a saved extraction, preserving native row gaps and omissions."""
    from .blast_database_extraction import normalize_blast_utility_sequence_symbols
    from .blast_utility_contracts import _VDB_SCHEMAS, _diagnostics
    value = _validated(value, _VDB_SCHEMAS["SequenceExtraction"])
    known, subjects = _result_context(value, {"extract_sequences"})
    out, selection = value["output_occurrence"], value["operation"]["parameters"]["selection"]
    _require(out["role"] in {"stdout", "extracted_sequences"}, "extraction_output")
    entries = selection["kind"] == "entries"
    _require(value["scope"]["kind"] == ("selected_entries" if entries else selection["kind"]), "vdb_extraction_scope")
    selectors = selection["selectors"] if entries else []
    ordinals = {s["ordinal"] for s in selectors}
    subjects.update(s["value"] for s in selectors)
    rows, matched = value["records"], set()
    keys = {r["record_key"] for r in rows}
    _require(len(keys) == len(rows), "duplicate_record_identity")
    native_ordinals = [r["native_row_ordinal"] for r in rows]
    _require(native_ordinals == sorted(set(native_ordinals)), "duplicate_native_row")
    subjects.update(keys)
    members = value["vdb_context"]["member_bindings"]
    for row in rows:
        _require(row["record_key"] == out["occurrence_id"] + "#/records/" + str(row["native_row_ordinal"]), "record_identity")
        _require(row["line_number"] == row["native_row_ordinal"] + 1, "vdb_record_line")
        selected = set(row["matched_selector_ordinals"])
        _require(selected <= ordinals, "selector_reference")
        exact = {s["ordinal"] for s in selectors if s["value"] in {row["native_identifier"], row["native_accession"]}}
        if not entries:
            _require(row["association"] == "not_applicable" and not selected, "vdb_enumeration_association")
        elif row["association"] == "exact":
            _require(bool(selected) and selected == exact, "exact_selector_association")
        elif row["association"] == "explicit":
            _require(bool(selected) and exact <= selected, "supplied_binding_conflict")
        else:
            _require(row["association"] == "unresolved" and not selected and not exact, "unresolved_selector_association")
        matched.update(selected)
        normalized, valid_count = normalize_blast_utility_sequence_symbols(row["original_sequence"], "dna")
        _require(row["normalized_sequence"] == normalized, "sequence_normalization")
        count, native_length = row["returned_symbol_count"], row["native_reported_length"]
        codes = {f["code"] for f in row["failures"]}
        if count is not None:
            _require(valid_count is not None and count == valid_count, "returned_sequence_count")
            _require(native_length is None or native_length == count, "native_length_unqualified")
            _require(not codes & {"sequence_symbol_invalid", "sequence_length_conflict"}, "qualified_sequence_count")
        else:
            _require(bool(codes), "missing_sequence_count_reason")
        if valid_count is None:
            _require("sequence_symbol_invalid" in codes, "returned_sequence_symbols")
        if valid_count is not None and native_length is not None and native_length != valid_count:
            _require("sequence_length_conflict" in codes, "native_length_unqualified")
        if row["completeness"] == "complete":
            _require(count is not None and not row["failures"], "complete_record_count")
        member = row["vdb_member"]
        candidates = [m for m in members if m["native_identifier"] == row["native_identifier"]]
        _require(member == (candidates[0] if len(candidates) == 1 else None), "vdb_member_record_binding")
        if len(candidates) > 1:
            _require(any(f["code"] == "supplied_binding_conflict" and f["stage"] == "association"
                and f["record_key"] == row["record_key"] and f["occurrence_id"] == out["occurrence_id"]
                and f["line_number"] == row["line_number"] for f in row["failures"]), "vdb_member_conflict_unqualified")
        _diagnostics(row, occurrences=known, subjects=subjects, record_keys=keys, outcome=value["original_outcome"])
    _require(set(value["missing_selector_ordinals"]) == ordinals - matched, "missing_selector_population")
    unexpected = {r["record_key"] for r in rows if entries and not r["matched_selector_ordinals"]}
    _require(set(value["unexpected_record_keys"]) == unexpected, "unexpected_record_population")
    if value["population_completeness"] == "complete_selection":
        outcome = value["original_outcome"]
        _require(not value["missing_selector_ordinals"] and not unexpected and not value["failures"] and
            all(r["completeness"] == "complete" for r in rows) and outcome["state"] == "succeeded" and
            outcome["writer_closed"] and outcome["inventory_complete"] and
            out["completeness"] == value["stderr_occurrence"]["completeness"] == "complete",
            "complete_selection_unestablished")
    _diagnostics(value, occurrences=known, subjects=subjects, record_keys=keys,
        malformed_prefix=out["occurrence_id"] + "#/records/", outcome=value["original_outcome"])
    return value


def validate_vdb_database_inspection(value: dict) -> dict:
    """Validate reported VDB populations and ordered flat path reports."""
    from .blast_utility_contracts import _VDB_SCHEMAS, _diagnostics, _fields
    value = _validated(value, _VDB_SCHEMAS["DatabaseInspection"])
    known, subjects = _result_context(value, {"info", "paths", "paths_all"})
    out, mode = value["output_occurrence"], value["operation"]["mode"]
    _require(out["role"] in {"stdout", "database_metadata"}, "inspection_output")
    fields, sections, paths = value["native_fields"], value["path_sections"], value["path_records"]
    if mode == "info":
        _require(not sections and not paths, "vdb_info_path_population")
        _fields(fields, {out["occurrence_id"]})
        seen = {}
        for row in fields:
            previous = seen.setdefault(row["field_name"], [])
            if previous:
                conflict = any((p["value"], p["unit"]) != (row["value"], row["unit"]) for p in previous)
                code = "database_metadata_conflict" if conflict else "duplicate_native_identity"
                _require(any(f["code"] == code for f in value["failures"]), "native_metadata_conflict_unqualified")
            previous.append(row)
    else:
        _require(not fields, "vdb_paths_native_fields")
        kinds = [s["kind"] for s in sections]
        _require(len(kinds) == len(set(kinds)), "vdb_path_section_identity")
        header_lines = [s["header_line_number"] for s in sections if s["header_line_number"] is not None]
        _require(header_lines == sorted(set(header_lines)), "vdb_path_section_order")
        native_ordinals = [p["native_path_ordinal"] for p in paths]
        _require(native_ordinals == sorted(set(native_ordinals)), "vdb_path_ordinals")
        _require([p["line_number"] for p in paths] == sorted({p["line_number"] for p in paths}), "vdb_path_line_order")
        for index, section in enumerate(sections):
            rows = [p for p in paths if p["section_ordinal"] == index]
            _require((section["header_line_number"] is None) == (section["presence"] == "not_reported"), "vdb_path_section_presence")
            _require(bool(rows) == (section["presence"] == "reported_values"), "vdb_path_section_population")
            if mode == "paths" and section["kind"] != "vdb":
                _require(section["presence"] == "not_reported", "vdb_top_level_path_sections")
        for row in paths:
            _require(row["section_ordinal"] < len(sections), "vdb_path_section_reference")
            section = sections[row["section_ordinal"]]
            _require(row["kind"] == section["kind"] and section["header_line_number"] is not None and
                     row["line_number"] > section["header_line_number"], "vdb_path_section_reference")
            later_headers = [s["header_line_number"] for s in sections[row["section_ordinal"] + 1:]
                             if s["header_line_number"] is not None]
            _require(not later_headers or row["line_number"] < later_headers[0], "vdb_path_section_reference")
            _require(row["native_path"].strip() != "None" and not any(c in row["native_path"] for c in "\0\n\r"), "vdb_path_value")
            context = value["vdb_context"]
            dependencies = {d["ordinal"]: d for d in context["declared_dependencies"]}
            databases = {b["database_key"]: b for b in [value["database_binding"], *context["dependency_database_bindings"]]}
            for ordinal in row["matched_dependency_ordinals"]:
                _require(ordinal in dependencies, "vdb_path_dependency_reference")
                dependency = dependencies[ordinal]
                bound_path = databases[dependency["database_key"]]["native_paths"][dependency["native_path_index"]]
                _require(row["native_path"] in {dependency["native_reference"], bound_path}, "vdb_path_dependency_match")
    if value["completeness"] == "complete":
        _require(out["completeness"] == value["stderr_occurrence"]["completeness"] == "complete"
                 and value["original_outcome"]["writer_closed"] and value["original_outcome"]["inventory_complete"],
                 "inspection_capture_completeness")
    _diagnostics(value, occurrences=known, subjects=subjects, outcome=value["original_outcome"])
    return value


__all__ = ["build_vdb_utility_schemas", "validate_vdb_utility_operation",
    "validate_vdb_utility_context", "validate_vdb_sequence_extraction", "validate_vdb_database_inspection"]
