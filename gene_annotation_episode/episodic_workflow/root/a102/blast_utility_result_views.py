"""Pure requested views of retained BLAST utility records.

The shared utility records own native values and their validation. These views
copy selected values; they do not parse, calculate, read files or grant access
to artifacts merely mentioned by a provenance relationship.
"""
from __future__ import annotations

from copy import deepcopy

from .blast_utility_contracts import (
    SCHEMAS, validate_blast_utility_operation, validate_blast_utility_record as core,
    validate_blast_utility_result, blast_utility_record_name_for_version,
    blast_utility_result_version_for_operation, blast_utility_schema_for_version,
)
from .domain import ContractError
from .native_blast_standard_database_contracts import _copy, _schema


PREFIX = "native_blast_utility_"
FACT_PREFIX = "execution.blast_utility_"
IDENTIFIER_NAMESPACES = (PREFIX + "record", PREFIX + "occurrence",
                         PREFIX + "path_record", PREFIX + "path_section")
SEQUENCE_FIELDS = ("original_sequence", "normalized_sequence")
VDB_RECORD_FIELDS = ("native_oid", "native_identifier", "native_accession", "native_reported_length",
    "native_length_basis", "returned_symbol_count", "molecule", "requested_range", "effective_range")
VDB_DATABASE_FIELDS = ("vdb_selected_inputs", "vdb_resolved_paths", "vdb_sequence_count",
    "vdb_total_unclipped_bases", "vdb_longest_sequence_bases", "vdb_average_sequence_bases",
    "vdb_csra_inputs", "vdb_reference_sequence_count", "vdb_reference_total_bases")
VDB_PATH_KINDS = ("vdb", "vdb_alias", "blast_db_alias")
DATABASE_FIELDS = tuple(branch["properties"]["field_name"]["const"]
                       for branch in SCHEMAS["NativeField"]["anyOf"])
INTEGRITY_FIELDS = ("observed_checked_count", "observed_population_count",
                   "observed_sampled_oids", "realized_seed", "diagnostics")
PREPARATION_FIELDS = ("identity", "software", "argv", "native_paths", "dependencies",
                      "inventory_complete", "detail", "compatibility")
PREPARATION_V2_FIELDS = (*PREPARATION_FIELDS, "kind", "database_bindings", "materializations")
RESULT_VERSIONS = ("blast_sequence_extraction_v1", "blast_database_inspection_v1",
    "blast_database_integrity_v1", "blast_database_artifact_set_v1",
    "blast_database_inspection_v2", "blast_database_artifact_set_v2")
PREPARED_DATABASE_VERSION = "native_blast_standard_prepared_database_manifest_v1"
PREPARED_DATABASE_VERSIONS = (PREPARED_DATABASE_VERSION, "native_blast_prepared_database_manifest_v1")
_STR = {"type": "string", "minLength": 1}
_UINT = {"type": "integer", "minimum": 0}
_BOOL = {"type": "boolean"}
_SOURCE = {**_STR, "format": "reference", "x-reference-namespace": "execution_result"}
_ARTIFACT = {**_STR, "format": "reference", "x-reference-namespace": "artifact"}
_RECORD = {**_STR, "format": "reference", "x-reference-namespace": IDENTIFIER_NAMESPACES[0]}
_OCCURRENCE = {**_STR, "format": "reference", "x-reference-namespace": IDENTIFIER_NAMESPACES[1]}


def _object(properties, *, required=None):
    return {"type": "object", "properties": deepcopy(properties),
            "required": list(properties) if required is None else list(required),
            "additionalProperties": False}


def _array(items, *, unique=False, **kwargs):
    return {"type": "array", "items": deepcopy(items),
            **({"uniqueItems": True} if unique else {}), **kwargs}


def _nullable(schema):
    return {"anyOf": [deepcopy(schema), {"type": "null"}]}


def _enum(values):
    return {"enum": list(values)}


def _with_source(schema, **extra):
    return _object({"source_ref": _SOURCE, **extra, **schema["properties"]})


_SLOT_SCHEMA = _object({key: SCHEMAS["ArtifactOccurrence"]["properties"][key]
                        for key in ("direction", "role", "ordinal")})
_SLOT_SCHEMA["properties"]["ordinal"] = {**_nullable(_UINT), "description":
    "Select one original ordinal, or null explicitly for all occurrences of this direction and role."}
NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA = _object({
    "version": {"const": PREFIX + "result_selector_v1"},
    "sequences": _nullable(_object({"selector_ordinals": _array(_UINT, unique=True),
        "sequence_fields": _array(_enum(SEQUENCE_FIELDS), unique=True)})),
    "database_fields": _array(_enum(DATABASE_FIELDS), unique=True),
    "integrity": _nullable(_object({"fields": _array(_enum(INTEGRITY_FIELDS), unique=True)})),
    "preparation": _nullable(_object({"fields": _array(_enum(PREPARATION_V2_FIELDS), unique=True)})),
    "prepared_database": _BOOL, "include_checks": _BOOL,
    "artifacts": _array(_SLOT_SCHEMA, unique=True),
    "saved_data": _array(_enum(("result", "prepared_database")), unique=True),
})
NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA = _object({
    **NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA["properties"],
    "version": {"const": PREFIX + "result_selector_v2"},
    "sequences": _nullable(_object({
        "selection": {"anyOf": [
            _object({"kind": {"const": "selector_ordinals"}, "values": _array(_UINT, unique=True)}),
            _object({"kind": {"const": "native_row_ordinals"}, "values": _nullable(_array(_UINT, unique=True))})]},
        "record_fields": _array(_enum(VDB_RECORD_FIELDS), unique=True),
        "sequence_fields": _array(_enum(SEQUENCE_FIELDS), unique=True), "include_vdb_identity": _BOOL})),
    "paths": _nullable(_object({"kinds": _array(_enum(VDB_PATH_KINDS), unique=True),
        "native_path_ordinals": _nullable(_array(_UINT, unique=True)), "include_sections": _BOOL})),
    "vdb_context": _BOOL,
})
NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA = {"anyOf": [
    deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA),
    deepcopy(NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA)]}
STATUS_SCHEMA = _object({"source_ref": _SOURCE,
    "state": _enum(("complete", "partial", "failed", "unavailable")),
    "native_state": SCHEMAS["NativeOutcome"]["properties"]["state"],
    "writer_closed": _BOOL, "inventory_complete": _BOOL,
    "result_completeness": _nullable(_enum(("complete_selection", "partial_selection",
                                            "complete", "partial", "unknown")))})
_EXTRACTION_ROW = blast_utility_schema_for_version("blast_sequence_extraction_v1")["properties"]["records"]["items"]["properties"]
_SEQUENCE_KEYS = tuple(key for key in _EXTRACTION_ROW if key not in {
    "record_key", "matched_selector_ordinals", *SEQUENCE_FIELDS, "checks", "failures"})
SEQUENCE_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "record_key": _RECORD, "occurrence_id": _OCCURRENCE,
    "selector_ordinals": _array(_UINT, unique=True, minItems=1),
    **{key: _EXTRACTION_ROW[key] for key in _SEQUENCE_KEYS},
    "sequences": _object({key: _EXTRACTION_ROW[key] for key in SEQUENCE_FIELDS}, required=[])})
_INSPECTION_V2 = blast_utility_schema_for_version("blast_database_inspection_v2")["properties"]
DATABASE_FIELD_SCHEMA = {"anyOf": [
    *[_with_source(branch, database_key=_STR) for branch in SCHEMAS["NativeField"]["anyOf"]],
    *[_with_source(branch, subject=_INSPECTION_V2["subject"]) for branch in SCHEMAS["NativeField"]["anyOf"]]]}
_INTEGRITY = blast_utility_schema_for_version("blast_database_integrity_v1")["properties"]
INTEGRITY_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "scope": _INTEGRITY["scope"],
    "fields": _object({key: _INTEGRITY[key] for key in INTEGRITY_FIELDS}, required=[])})
_PREPARATION = blast_utility_schema_for_version("blast_database_artifact_set_v1")["properties"]
_PREPARATION_V2 = blast_utility_schema_for_version("blast_database_artifact_set_v2")["anyOf"]
PREPARATION_SCHEMA = {"anyOf": [
    _object({"source_ref": _SOURCE, "database_key": _STR,
        "fields": _object({key: _PREPARATION[key] for key in PREPARATION_FIELDS}, required=[])}),
    *[_object({"source_ref": _SOURCE, "database_key": _STR,
        "fields": _object({key: branch["properties"][key] for key in PREPARATION_V2_FIELDS}, required=[])})
      for branch in _PREPARATION_V2]]}
PREPARED_DATABASE_SCHEMA = _with_source(SCHEMAS["PreparedDatabaseProjection"], database_key=_STR)
CHECK_SCHEMA = _with_source(SCHEMAS["ValidationObservation"])
FAILURE_SCHEMA = _with_source(SCHEMAS["UtilityFailure"])
ARTIFACT_SCHEMA = _with_source(SCHEMAS["ArtifactOccurrence"])
ARTIFACT_SCHEMA["properties"]["occurrence_id"] = deepcopy(_OCCURRENCE)
ARTIFACT_SCHEMA["properties"]["artifact_ref"] = deepcopy(_ARTIFACT)
SAVED_DATA_SCHEMA = _object({"source_ref": _SOURCE,
    "kind": _enum(("result", "prepared_database")), "artifact_ref": _ARTIFACT,
    "sha256": SCHEMAS["ArtifactOccurrence"]["properties"]["sha256"], "size_bytes": _UINT,
    "schema": _enum((*RESULT_VERSIONS, *PREPARED_DATABASE_VERSIONS))})
_MISSING_REQUESTS = {
    "sequence_selector": {"ordinal": _UINT}, "database_field": {"field_name": _enum(DATABASE_FIELDS)},
    "integrity": {}, "preparation": {}, "prepared_database": {}, "checks": {},
    "artifact": {"slot": _SLOT_SCHEMA}, "saved_data": {"kind": _enum(("result", "prepared_database"))},
}
MISSING_SCHEMA = _object({"source_ref": _SOURCE,
    "request": {"anyOf": [_object({"type": {"const": kind}, **fields})
                           for kind, fields in _MISSING_REQUESTS.items()]},
    "reason": _enum(("result_unavailable", "selection_unavailable", "field_unavailable",
                     "artifact_unavailable", "saved_data_unavailable", "prepared_database_unavailable"))})
_FACT_SCHEMAS = {"status": STATUS_SCHEMA, "sequences": SEQUENCE_SCHEMA,
    "database_fields": DATABASE_FIELD_SCHEMA, "integrity": INTEGRITY_SCHEMA,
    "preparation": PREPARATION_SCHEMA, "prepared_database": PREPARED_DATABASE_SCHEMA,
    "checks": CHECK_SCHEMA, "failures": FAILURE_SCHEMA, "missing": MISSING_SCHEMA,
    "artifacts": ARTIFACT_SCHEMA, "saved_data": SAVED_DATA_SCHEMA}
PROJECTION_FIELDS = (*_FACT_SCHEMAS, "record_refs")
_LEGACY_FACT_SCHEMAS = deepcopy(_FACT_SCHEMAS)
PROJECTION_V2_FIELDS = (*PROJECTION_FIELDS, "paths", "path_sections", "vdb_context")
_VDB_EXTRACTION = blast_utility_schema_for_version("blast_sequence_extraction_v2")["properties"]
_VDB_ROW = _VDB_EXTRACTION["records"]["items"]["properties"]
_VDB_INSPECTION = blast_utility_schema_for_version("blast_database_inspection_v3")["properties"]
_QUALIFICATION = _object({"pointer": {"type": "string", "pattern": r"^(?:/(?:[^~/]|~[01])*)*$"},
    "reason": _enum(("not_supplied", "not_applicable", "native_not_reported", "native_row_invalid",
        "sequence_symbol_invalid", "sequence_length_conflict", "supplied_binding_conflict", "member_unresolved"))})
_QUALIFICATIONS = _array(_QUALIFICATION, unique=True)
_SAMPLE_LINK = SCHEMAS["VDBUtilityContext"]["properties"]["sample_links"]["items"]
SEQUENCE_V2_SCHEMA = _object({"version": {"const": PREFIX + "sequence_fact_v2"},
    "source_ref": _SOURCE, "database_key": _STR, "record_key": _RECORD, "occurrence_id": _OCCURRENCE,
    "native_row_ordinal": _UINT, "line_number": _VDB_ROW["line_number"],
    "selector_ordinals": _array(_UINT, unique=True), "scope": _VDB_EXTRACTION["scope"],
    "association": _VDB_ROW["association"], "completeness": _VDB_ROW["completeness"],
    "fields": _object({key: _VDB_ROW[key] for key in VDB_RECORD_FIELDS}, required=[]),
    "sequences": _object({key: _VDB_ROW[key] for key in SEQUENCE_FIELDS}, required=[]),
    "field_qualifications": _QUALIFICATIONS,
    "vdb_identity": _object({"member": _nullable(SCHEMAS["VDBMember"]),
        "sample_links": _array(_SAMPLE_LINK), "qualifications": _QUALIFICATIONS})},
    required=("version", "source_ref", "database_key", "record_key", "occurrence_id", "native_row_ordinal",
        "line_number", "selector_ordinals", "scope", "association", "completeness", "fields", "sequences",
        "field_qualifications"))
PATH_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR, "occurrence_id": _OCCURRENCE,
    "path_ref": {**_STR, "format": "reference", "x-reference-namespace": IDENTIFIER_NAMESPACES[2]},
    **_VDB_INSPECTION["path_records"]["items"]["properties"]})
PATH_SECTION_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR, "occurrence_id": _OCCURRENCE,
    "section_ref": {**_STR, "format": "reference", "x-reference-namespace": IDENTIFIER_NAMESPACES[3]},
    "section_ordinal": _UINT, **_VDB_INSPECTION["path_sections"]["items"]["properties"]})
VDB_CONTEXT_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "context": SCHEMAS["VDBUtilityContext"], "qualifications": _QUALIFICATIONS})
_VDB_MISSING_REQUESTS = {**{key: value for key, value in _MISSING_REQUESTS.items()
    if key not in {"integrity", "preparation", "prepared_database"}},
    "database_field": {"field_name": _enum(VDB_DATABASE_FIELDS)},
    "saved_data": {"kind": {"const": "result"}},
    "native_row": {"ordinal": _UINT}, "native_enumeration": {}, "path_row": {"ordinal": _UINT},
    "path_population": {"kind": _enum(VDB_PATH_KINDS)}, "path_section": {"kind": _enum(VDB_PATH_KINDS)},
    "vdb_context": {}}
MISSING_V2_SCHEMA = _object({"version": {"const": PREFIX + "missing_fact_v2"}, "source_ref": _SOURCE,
    "request": {"anyOf": [_object({"type": {"const": kind}, **fields}) for kind, fields in _VDB_MISSING_REQUESTS.items()]},
    "reason": MISSING_SCHEMA["properties"]["reason"]})
_VDB_SAVED_DATA_SCHEMA = _object({**SAVED_DATA_SCHEMA["properties"],
    "kind": {"const": "result"},
    "schema": _enum(("blast_sequence_extraction_v2", "blast_database_inspection_v3"))})
_FACT_SCHEMAS = {**_FACT_SCHEMAS,
    "sequences": {"anyOf": [deepcopy(SEQUENCE_SCHEMA), deepcopy(SEQUENCE_V2_SCHEMA)]},
    "missing": {"anyOf": [deepcopy(MISSING_SCHEMA), deepcopy(MISSING_V2_SCHEMA)]},
    "saved_data": {"anyOf": [deepcopy(SAVED_DATA_SCHEMA), _VDB_SAVED_DATA_SCHEMA]},
    "paths": PATH_SCHEMA, "path_sections": PATH_SECTION_SCHEMA, "vdb_context": VDB_CONTEXT_SCHEMA}


def _error(code):
    raise ContractError(PREFIX + code)


def _require(condition, code):
    if not condition:
        _error(code)


def _validated(value, schema):
    try:
        value = _copy(value)
        _schema(value, schema)
    except (ValueError, RecursionError) as error:
        raise ContractError(PREFIX + "result_schema_invalid") from error
    return value


def _text(value):
    _require(type(value) is str and bool(value) and "\0" not in value, "result_reference_invalid")


def _slot(row):
    return tuple(row[key] for key in ("direction", "role", "ordinal"))


def _slot_matches(selection, occurrence):
    return (selection["direction"] == occurrence["direction"]
        and selection["role"] == occurrence["role"]
        and (selection["ordinal"] is None or selection["ordinal"] == occurrence["ordinal"]))


def _selected_artifacts(selections, occurrences):
    """Explicit role selection keeps native ordinals and grants each occurrence once."""
    selected, seen = [], set()
    for selection in selections:
        for occurrence in occurrences:
            key = occurrence["occurrence_id"]
            if key not in seen and _slot_matches(selection, occurrence):
                selected.append(occurrence)
                seen.add(key)
    return selected


def _artifact_identity(row):
    _require(row["artifact_ref"] == "artifact_" + row["sha256"], "result_artifact_identity_conflict")


def _occurrences(values):
    _require(type(values) is list, "result_occurrence_list_required")
    result = [core("ArtifactOccurrence", value) for value in values]
    _require(len({_slot(row) for row in result}) == len(result)
             and len({row["occurrence_id"] for row in result}) == len(result), "result_occurrence_duplicate")
    by_ref, by_path = {}, {}
    for row in result:
        _artifact_identity(row)
        identity = row["sha256"], row["size_bytes"]
        _require(row["artifact_ref"] not in by_ref or by_ref[row["artifact_ref"]] == identity,
                 "result_artifact_identity_conflict")
        by_ref[row["artifact_ref"]] = identity
        if row["native_path"] is not None:
            _require(row["native_path"] not in by_path or by_path[row["native_path"]] == identity,
                     "result_artifact_path_conflict")
            by_path[row["native_path"]] = identity
    return result


def validate_blast_utility_result_selector(selector: dict, *, operation: dict) -> dict:
    """Validate an explicit selection against the original selected utility."""
    operation = validate_blast_utility_operation(operation)
    selector = _validated(selector, NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)
    if selector["version"] == PREFIX + "result_selector_v2":
        return _validate_vdb_selector(selector, operation)
    _require(operation["version"] != "blast_utility_operation_v3", "selector_operation_version_conflict")
    pair = operation["program"], operation["mode"]
    version = blast_utility_result_version_for_operation(operation)
    kind = blast_utility_record_name_for_version(version)
    if selector["sequences"] is not None:
        _require(kind == "SequenceExtraction", "sequence_selection_not_applicable")
        wanted = set(selector["sequences"]["selector_ordinals"])
        _require(wanted <= {row["ordinal"] for row in operation["parameters"]["selectors"]},
                 "sequence_selector_not_in_original_request")
    _require(not selector["database_fields"] or kind in {"DatabaseInspection", "DatabaseArtifactSet"},
             "database_fields_not_applicable")
    _require(selector["integrity"] is None or kind == "DatabaseIntegrity", "integrity_selection_not_applicable")
    _require(kind == "DatabaseArtifactSet" or (selector["preparation"] is None
        and not selector["prepared_database"] and "prepared_database" not in selector["saved_data"]),
        "preparation_selection_not_applicable")
    if selector["preparation"] is not None and version != "blast_database_artifact_set_v2":
        _require(set(selector["preparation"]["fields"]) <= set(PREPARATION_FIELDS),
                 "preparation_fields_not_applicable")
    database_inputs = {"database_file", "database_metadata", "database_manifest", "preparation_receipt",
                       "input_manifest", "offline_configuration"}
    inputs = ({"sequence_input", "taxid_map", "mask_input"}
              if pair == ("makeblastdb", "create_sequence_database") else database_inputs)
    outputs = {"stdout", "stderr", "diagnostics"}
    if pair == ("makeblastdb", "create_sequence_database"):
        outputs |= {"database_file", "database_metadata", "database_manifest", "preparation_receipt", "input_manifest"}
    elif pair == ("blastdbcmd", "extract_sequences"):
        outputs.add("extracted_sequences")
    elif pair in {("blastdbcmd", "info"), ("blastdbcmd", "metadata")}:
        outputs.add("database_metadata")
    elif operation["version"] == "blast_utility_operation_v2":
        inputs, added_outputs = _preparation_artifact_roles(operation, database_inputs)
        outputs |= added_outputs | {"preparation_receipt"}
    _require(all(row["role"] in (inputs if row["direction"] == "input" else outputs)
                 for row in selector["artifacts"]), "artifact_selection_not_applicable")
    return selector


def blast_utility_projection_fields(selector: dict) -> tuple[str, ...]:
    """Dispatch closed selector versions without enriching a legacy result."""
    selector = _validated(selector, NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA)
    return PROJECTION_V2_FIELDS if selector["version"] == PREFIX + "result_selector_v2" else PROJECTION_FIELDS


def _validate_vdb_selector(selector, operation):
    _require(operation["version"] == "blast_utility_operation_v3", "selector_operation_version_conflict")
    mode, parameters = operation["mode"], operation["parameters"]
    selected = selector["sequences"]
    if selected is not None:
        _require(mode == "extract_sequences", "sequence_selection_not_applicable")
        original, selection = parameters["selection"], selected["selection"]
        entries = original["kind"] == "entries"
        _require((selection["kind"] == "selector_ordinals") == entries, "sequence_selection_kind_conflict")
        if entries:
            _require(set(selection["values"]) <= {r["ordinal"] for r in original["selectors"]},
                     "sequence_selector_not_in_original_request")
        _require("native_reported_length" not in selected["record_fields"]
                 or "native_length_basis" in selected["record_fields"], "sequence_native_length_basis_required")
    _require(not selector["database_fields"] or mode == "info"
             and set(selector["database_fields"]) <= set(VDB_DATABASE_FIELDS), "database_fields_not_applicable")
    _require(selector["integrity"] is None, "integrity_selection_not_applicable")
    _require(selector["preparation"] is None and not selector["prepared_database"]
             and "prepared_database" not in selector["saved_data"], "preparation_selection_not_applicable")
    paths = selector["paths"]
    if paths is not None:
        _require(mode in {"paths", "paths_all"}, "path_selection_not_applicable")
        _require(mode == "paths_all" or set(paths["kinds"]) <= {"vdb"}, "path_kind_not_applicable")
    inputs = {"database_file", "database_metadata", "database_manifest", "preparation_receipt",
              "input_manifest", "offline_configuration", "database_list"}
    # An explicitly selected manifest file may also be a database-side list.
    # Its role is known only in the full qualified context, not this operation.
    if mode == "extract_sequences" and parameters["selection"].get("source") == "entry_batch":
        inputs.add("entry_batch")
    # The original sealed bundle is an existing receipt occurrence, not an
    # additional native product. Its bytes still require explicit selection.
    outputs = {"stdout", "stderr", "diagnostics", "preparation_receipt"}
    _require(all(row["role"] in (inputs if row["direction"] == "input" else outputs)
                 for row in selector["artifacts"]), "artifact_selection_not_applicable")
    return selector


def _preparation_artifact_roles(operation, database_inputs):
    """Role applicability for each original operation; selection grants bytes."""
    pair = operation["program"], operation["mode"]
    parameters = operation["parameters"]
    if pair in {("blastdb_aliastool", "convert_gi_list"), ("blastdb_aliastool", "convert_seqid_list")}:
        return ({"identifier_list"} | (database_inputs if operation["database_key"] is not None else set()),
                {"identifier_list"})
    if pair == ("blastdb_aliastool", "inspect_seqid_list"):
        return {"identifier_list"}, set()
    if pair == ("makembindex", "show_filters"):
        return database_inputs, set()
    if pair == ("makembindex", "create_megablast_index"):
        return ({"sequence_input"} if parameters["input_format"] == "fasta" else database_inputs,
                {"index_file", "statistics"})
    if pair == ("makeprofiledb", "create_profile_database"):
        return {"profile_list", "profile_input", "materialized_list", "taxid_map"}, {
            "database_file", "database_metadata", "alias_file", "profile_file"}
    if pair in {("blastdb_aliastool", "create_subset_alias"),
                ("blastdb_aliastool", "aggregate_databases"), ("blastdb_aliastool", "aggregate_volumes")}:
        return database_inputs | {"identifier_list", "database_list", "materialized_list"}, {
            "alias_file", "identifier_list", "database_file", "database_metadata"}
    _error("artifact_selection_not_applicable")


def blast_utility_fact_sources() -> dict:
    meanings = {
        "status": "Requested delivery, original native outcome and capture completeness are distinct.",
        "sequences": "Selected original extracted identities, sequences, native lengths and returned coordinates.",
        "database_fields": "Requested native database fields with exact source locators, units and qualifications.",
        "integrity": "Requested observed native integrity scope and measurements, never inferred coverage.",
        "preparation": "Requested original database preparation facts, without scientific confidence.",
        "prepared_database": "Explicitly requested existing prepared database manifest or qualified unavailability.",
        "checks": "Selected and relevant global original utility validation observations.",
        "failures": "Original typed utility failures and necessary qualifications.",
        "missing": "Exact requested selections unavailable from the retained utility result.",
        "artifacts": "Only explicitly selected original artifact occurrences and their byte identities.",
        "saved_data": "Only explicitly selected retained utility result or available prepared manifest artifacts.",
        "paths": "Selected literal native path rows and declared dependency ordinals; paths confer no byte access.",
        "path_sections": "Selected original path sections distinguish reported empty populations from absent reports.",
        "vdb_context": "Explicitly selected supplied VDB context and missing identity qualifications, without metadata byte grants.",
    }
    return {FACT_PREFIX + name: {"type": "array", "meaning": meanings[name],
        "report_schema": {**_array(schema), "x-source": FACT_PREFIX + name}}
        for name, schema in _FACT_SCHEMAS.items()}


FACT_SOURCES = blast_utility_fact_sources()


def validate_blast_utility_fact_values(source: str, values: list) -> list:
    """Validate closed typed facts; the return reader authenticates custody."""
    _require(type(source) is str and source in FACT_SOURCES, "unknown_fact_source")
    rows = _validated(values, FACT_SOURCES[source]["report_schema"])
    name = source.removeprefix(FACT_PREFIX)
    for row in rows:
        _text(row["source_ref"])
        if name in {"checks", "failures", "artifacts"}:
            kind = {"checks": "ValidationObservation", "failures": "UtilityFailure",
                    "artifacts": "ArtifactOccurrence"}[name]
            core(kind, {key: value for key, value in row.items() if key != "source_ref"})
        if name in {"artifacts", "saved_data"}:
            _artifact_identity(row)
        if name == "saved_data":
            _require((row["kind"] == "prepared_database") == (row["schema"] in PREPARED_DATABASE_VERSIONS),
                     "saved_data_schema_conflict")
        elif name == "database_fields":
            core("NativeField", {key: value for key, value in row.items()
                                 if key not in {"source_ref", "database_key", "subject"}})
        elif name == "sequences":
            _require(row["record_key"] == row["occurrence_id"] + "#/records/" + str(row["native_row_ordinal"]),
                     "sequence_record_identity_conflict")
            if row.get("version") == PREFIX + "sequence_fact_v2":
                _validate_vdb_sequence_fact(row)
            else:
                _require(row["association"] in {"exact", "explicit"}, "sequence_association_unresolved")
        elif name == "paths":
            _require(row["path_ref"] == row["occurrence_id"] + "#/path_records/" + str(row["native_path_ordinal"]),
                     "path_record_identity_conflict")
            _require(row["native_path"].strip() != "None" and not any(c in row["native_path"] for c in "\0\n\r"),
                     "path_record_value_invalid")
            _require(row["section_ordinal"] < len(VDB_PATH_KINDS), "path_section_identity_conflict")
        elif name == "path_sections":
            _require(row["section_ref"] == row["occurrence_id"] + "#/path_sections/" + str(row["section_ordinal"]),
                     "path_section_identity_conflict")
            _require((row["header_line_number"] is None) == (row["presence"] == "not_reported"),
                     "path_section_presence_conflict")
            _require(row["section_ordinal"] < len(VDB_PATH_KINDS), "path_section_identity_conflict")
        elif name == "vdb_context":
            from .blast_vdb_utility_contracts import validate_vdb_context_relationships
            validate_vdb_context_relationships(row["context"])
            _require(row["qualifications"] == _context_qualifications(row["context"]), "context_qualification_conflict")
        elif name == "prepared_database":
            projection = core("PreparedDatabaseProjection", {key: row[key] for key in ("status", "manifest", "failures")})
            _require(projection["manifest"] is None or projection["manifest"]["database_key"] == row["database_key"],
                     "prepared_database_key_conflict")
        elif name == "status":
            _require(not row["inventory_complete"] or row["writer_closed"], "status_inventory_conflict")
    return rows


def _requested(selector):
    if selector["version"] == PREFIX + "result_selector_v2":
        return _vdb_requested(selector)
    result = []
    if selector["sequences"] is not None:
        result += [{"type": "sequence_selector", "ordinal": value}
                   for value in selector["sequences"]["selector_ordinals"]]
    result += [{"type": "database_field", "field_name": name} for name in selector["database_fields"]]
    result += [{"type": name} for name in ("integrity", "preparation") if selector[name] is not None]
    if selector["prepared_database"]:
        result.append({"type": "prepared_database"})
    if selector["include_checks"]:
        result.append({"type": "checks"})
    result += [{"type": "artifact", "slot": row} for row in selector["artifacts"]]
    result += [{"type": "saved_data", "kind": kind} for kind in selector["saved_data"]]
    return result


def projection_identifiers(projection: dict, namespace=None) -> list[str]:
    """Enumerate only declared logical references present in selected facts."""
    if namespace not in (*IDENTIFIER_NAMESPACES, None):
        return []
    references = []
    if namespace in (None, IDENTIFIER_NAMESPACES[0]):
        references.extend(row["record_key"] for row in projection.get("sequences", []))
    if namespace in (None, IDENTIFIER_NAMESPACES[1]):
        references.extend(row["occurrence_id"] for field in ("sequences", "artifacts", "paths", "path_sections")
                          for row in projection.get(field, []))
    if namespace in (None, IDENTIFIER_NAMESPACES[2]):
        references.extend(row["path_ref"] for row in projection.get("paths", []))
    if namespace in (None, IDENTIFIER_NAMESPACES[3]):
        references.extend(row["section_ref"] for row in projection.get("path_sections", []))
    return list(dict.fromkeys(references))


def _state(projection, outcome):
    if not projection["missing"]:
        return "complete"
    useful = any(projection[name] for name in ("sequences", "database_fields", "integrity",
        "preparation", "prepared_database", "artifacts", "saved_data", "checks"))
    return "partial" if useful else "failed" if outcome["state"] == "failed" else "unavailable"


def _inspection_subject(operation, known, failures=()):
    """Bind a v2 subject to the original selection, without granting its bytes."""
    if (operation["program"], operation["mode"]) == ("blastdb_aliastool", "inspect_seqid_list"):
        key = operation["parameters"]["input_occurrence_id"]
        row = known.get(key)
        if row is None:
            _require(any(f["code"] in {"input_population_unavailable", "dependency_unavailable"}
                and f["occurrence_id"] is None for f in failures), "projection_inspection_subject_unavailable")
        else:
            _require(row["direction"] == "input" and row["role"] == "identifier_list"
                and row["native_format"] == "seqid_list_binary", "projection_inspection_subject_conflict")
        return {"kind": "identifier_list", "occurrence_id": key}
    _require((operation["program"], operation["mode"]) == ("makembindex", "show_filters"),
             "projection_inspection_operation_conflict")
    return {"kind": "database", "database_key": operation["database_key"]}


def validate_blast_utility_projection(projection: dict, *, source_ref: str, operation: dict,
                                     native_outcome: dict, selector: dict, occurrences: list,
                                     context: dict | None = None) -> dict:
    """Validate selected fields and reference grants, without replaying calculations."""
    _text(source_ref)
    operation = validate_blast_utility_operation(operation)
    outcome = core("NativeOutcome", native_outcome)
    selector = validate_blast_utility_result_selector(selector, operation=operation)
    if selector["version"] == PREFIX + "result_selector_v2":
        return _validate_vdb_projection(projection, source_ref=source_ref, operation=operation,
            native_outcome=outcome, selector=selector, occurrences=occurrences, context=context)
    result_version = blast_utility_result_version_for_operation(operation)
    result_kind = blast_utility_record_name_for_version(result_version)
    occurrences = _occurrences(occurrences)
    projection = _validated(projection, _object({
        **{name: schema if name == "status" else _array(schema) for name, schema in _LEGACY_FACT_SCHEMAS.items()},
        "record_refs": _array(_STR, unique=True)}))
    for name in _LEGACY_FACT_SCHEMAS:
        rows = [projection[name]] if name == "status" else projection[name]
        validate_blast_utility_fact_values(FACT_PREFIX + name, rows)
        _require(all(row["source_ref"] == source_ref for row in rows), "projection_source_conflict")
    status = projection["status"]
    _require(all(status[key] == outcome["state" if key == "native_state" else key]
                 for key in ("native_state", "writer_closed", "inventory_complete")), "projection_outcome_conflict")
    allowed_completeness = ({None, "complete_selection", "partial_selection", "unknown"}
        if result_kind == "SequenceExtraction" else {None, "complete", "partial", "unknown"}
        if result_kind == "DatabaseInspection" else {None})
    _require(status["result_completeness"] in allowed_completeness, "projection_completeness_conflict")
    expected_artifacts = [{"source_ref": source_ref, **row}
                          for row in _selected_artifacts(selector["artifacts"], occurrences)]
    _require(projection["artifacts"] == expected_artifacts, "projection_artifact_grant_conflict")
    saved_kinds = [row["kind"] for row in projection["saved_data"]]
    _require(saved_kinds == [kind for kind in selector["saved_data"] if kind in saved_kinds]
             and len(saved_kinds) == len(set(saved_kinds)), "projection_saved_data_selection_conflict")
    _require(all(row["schema"] == result_version for row in projection["saved_data"]
                 if row["kind"] == "result"), "projection_saved_result_version_conflict")
    _require(projection["record_refs"] == list(dict.fromkeys([source_ref,
        *[row["artifact_ref"] for row in projection["artifacts"]],
        *[row["artifact_ref"] for row in projection["saved_data"]]])), "projection_reference_grant_conflict")
    seen, chosen = set(), set()
    known_ids = {row["occurrence_id"] for row in occurrences}
    known = {row["occurrence_id"]: row for row in occurrences}
    selected = selector["sequences"]
    for row in projection["sequences"]:
        _require(selected is not None and row["record_key"] not in seen
            and row["occurrence_id"] in known_ids
            and row["selector_ordinals"] == [value for value in selected["selector_ordinals"]
                                             if value in row["selector_ordinals"]]
            and set(row["sequences"]) == set(selected["sequence_fields"]), "projection_sequence_selection_conflict")
        _require(row["database_key"] == operation["database_key"] and row["molecule"] == operation["molecule"]
            and row["requested_range"] == operation["parameters"]["range"], "projection_sequence_context_conflict")
        occurrence = known[row["occurrence_id"]]
        _require(occurrence["direction"] == "output" and occurrence["role"] in {"stdout", "extracted_sequences"}
            and occurrence["native_format"] == "blastdbcmd_tabular_v1", "projection_sequence_occurrence_conflict")
        seen.add(row["record_key"]); chosen.update(row["selector_ordinals"])
    for row in projection["database_fields"]:
        _require(row["field_name"] in selector["database_fields"] and row["occurrence_id"] in known_ids,
                 "projection_database_field_selection_conflict")
        if result_version == "blast_database_inspection_v2":
            _require(row.get("subject") == _inspection_subject(operation, known, projection["failures"]),
                     "projection_inspection_subject_conflict")
            occurrence = known[row["occurrence_id"]]
            _require((operation["program"], operation["mode"]) == ("blastdb_aliastool", "inspect_seqid_list")
                and row["field_name"].startswith("identifier_list_")
                and occurrence["direction"] == "output" and occurrence["role"] == "stdout"
                and occurrence["native_format"] == "blast_seqid_list_info_text",
                "projection_inspection_field_context_conflict")
        else:
            _require("database_key" in row, "projection_database_field_context_conflict")
    for name in ("integrity", "preparation"):
        rows = projection[name]
        _require(len(rows) <= 1 and (not rows or selector[name] is not None
            and set(rows[0]["fields"]) == set(selector[name]["fields"])), "projection_" + name + "_selection_conflict")
    _require(len(projection["prepared_database"]) <= 1 and
        (not projection["prepared_database"] or selector["prepared_database"]), "projection_prepared_selection_conflict")
    if result_kind in {"DatabaseIntegrity", "DatabaseInspection"} and result_version != "blast_database_inspection_v2":
        _require(all(row["database_key"] == operation["database_key"] for name in ("database_fields", "integrity")
                     for row in projection[name]), "projection_database_key_conflict")
    _require(not projection["checks"] or selector["include_checks"], "projection_unrequested_checks")
    for row in projection["checks"]:
        _require(set(row["evidence_occurrence_ids"]) <= known_ids, "projection_check_evidence_conflict")
    for row in projection["failures"]:
        _require(row["occurrence_id"] is None or row["occurrence_id"] in known_ids,
                 "projection_failure_occurrence_conflict")
        _require(row["native_returncode"] is None or row["native_returncode"] == outcome["returncode"],
                 "projection_failure_outcome_conflict")
    requests, missing = _requested(selector), []
    for row in projection["missing"]:
        _require(row["request"] in requests and row["request"] not in missing, "projection_missing_request_conflict")
        missing.append(row["request"])
    for request in requests:
        kind = request["type"]
        if kind == "sequence_selector":
            fulfilled = request["ordinal"] in chosen
        elif kind == "database_field":
            fulfilled = any(row["field_name"] == request["field_name"] for row in projection["database_fields"])
        elif kind == "artifact":
            fulfilled = any(_slot_matches(request["slot"], row) for row in occurrences)
        elif kind == "saved_data":
            fulfilled = request["kind"] in saved_kinds
        elif kind == "prepared_database":
            fulfilled = bool(projection[kind] and projection[kind][0]["status"] == "available")
        elif kind == "checks":
            _require(request not in missing or not projection["checks"], "projection_missing_checks_conflict")
            continue  # An available saved result may have zero checks.
        else:
            fulfilled = bool(projection[kind])
        _require(fulfilled != (request in missing), "projection_missing_population_conflict")
    _require(status["state"] == _state(projection, outcome), "projection_state_conflict")
    return projection


def _result_context(result, operation, outcome, occurrences, failures):
    if result is None:
        return None
    result = validate_blast_utility_result(result)
    _require(result["operation"] == operation and result["original_outcome"] == outcome, "result_original_context_conflict")
    _require(result["version"] == blast_utility_result_version_for_operation(operation), "result_operation_version_conflict")
    known = {row["occurrence_id"]: row for row in occurrences}
    if blast_utility_record_name_for_version(result["version"]) == "DatabaseArtifactSet":
        rows = result["inputs"] + result["outputs"]
    elif result["version"] == "blast_database_inspection_v2":
        _require(result["subject"] == _inspection_subject(operation, known, [*result["failures"], *failures]),
                 "result_inspection_subject_conflict")
        for binding in result["database_bindings"]:
            _require(set(binding["occurrence_ids"]) <= known.keys(), "result_database_occurrence_conflict")
        rows = [result["output_occurrence"]]
    else:
        binding = result["database_binding"]
        _require(set(binding["occurrence_ids"]) <= known.keys(), "result_database_occurrence_conflict")
        rows = ([result["stdout_occurrence"], result["stderr_occurrence"]]
                if result["version"] == "blast_database_integrity_v1" else [result["output_occurrence"]])
    _require(all(known.get(row["occurrence_id"]) == row for row in rows), "result_occurrence_context_conflict")
    return result


def _prepared_context(value, result, occurrences):
    if value is None:
        return None
    value = core("PreparedDatabaseProjection", value)
    _require(result is not None and blast_utility_record_name_for_version(result["version"]) == "DatabaseArtifactSet",
             "prepared_database_result_required")
    manifest = value["manifest"]
    if manifest is None:
        return value
    if result["version"] == "blast_database_artifact_set_v2":
        from .blast_database_preparation import project_prepared_blast_database
        preparation = manifest["preparation"]
        expected = project_prepared_blast_database(result,
            contract="standard" if manifest["version"] == PREPARED_DATABASE_VERSION else "additional",
            preparation_receipt=preparation["receipt"], input_manifest=preparation["input_manifest"],
            metadata_manifests=manifest["metadata_manifests"])
        _require(value == expected, "prepared_database_result_conflict")
        _prepared_descriptors(manifest, occurrences)
        return value
    _require(result["original_outcome"]["state"] == "succeeded" and result["inventory_complete"]
        and result["compatibility"] != "incompatible" and not result["failures"], "prepared_database_result_conflict")
    _require(all(manifest[key] == result[key] for key in ("database_key", "identity", "native_paths", "inventory_complete")),
             "prepared_database_identity_conflict")
    expected_kind = "blast_nucleotide_sequence" if result["operation"]["molecule"] == "dna" else "blast_protein_sequence"
    _require(manifest["kind"] == expected_kind and manifest["preparation"]["method"] == "makeblastdb"
        and all(manifest["preparation"][key] == result[key] for key in ("software", "argv")),
        "prepared_database_operation_conflict")
    files, paths = [], set()
    for row in result["outputs"]:
        if row["role"] in {"database_file", "database_metadata"} and row["native_path"] not in paths:
            files.append({"path": row["native_path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
            paths.add(row["native_path"])
    _require(manifest["files"] == files, "prepared_database_files_conflict")
    preparation = manifest["preparation"]
    receipt = preparation["receipt"]
    _require(preparation["source"] == {"source_ref": receipt["artifact_ref"] or receipt["path"], "pointer": ""},
             "prepared_database_receipt_source_conflict")
    _prepared_descriptors(manifest, occurrences)
    return value


def _prepared_descriptors(manifest, occurrences):
    preparation = manifest["preparation"]
    receipt = preparation["receipt"]
    descriptors = [receipt, *manifest["metadata_manifests"]]
    if preparation["input_manifest"] is not None:
        descriptors.append(preparation["input_manifest"])
    for descriptor in descriptors:
        matches = [row for row in occurrences if row["native_path"] == descriptor["path"] or
                   descriptor["artifact_ref"] is not None and row["artifact_ref"] == descriptor["artifact_ref"]]
        for row in matches:
            _require(row["native_path"] == descriptor["path"] and row["sha256"] == descriptor["sha256"]
                and row["size_bytes"] == descriptor["size_bytes"]
                and descriptor["artifact_ref"] in {None, row["artifact_ref"]}, "prepared_database_descriptor_conflict")


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def project_blast_utility_result(*, source_ref: str, operation: dict, native_outcome: dict,
        result: dict | None, prepared_database: dict | None, occurrences: list,
        selector: dict, failures: list, saved_data: list, context: dict | None = None) -> dict:
    """Copy requested original values, keeping absent selections explicit."""
    _text(source_ref)
    operation = validate_blast_utility_operation(operation)
    outcome = core("NativeOutcome", native_outcome)
    selector = validate_blast_utility_result_selector(selector, operation=operation)
    if selector["version"] == PREFIX + "result_selector_v2":
        return _project_vdb_result(source_ref=source_ref, operation=operation, native_outcome=outcome,
            result=result, prepared_database=prepared_database, occurrences=occurrences, selector=selector,
            failures=failures, saved_data=saved_data, context=context)
    occurrences = _occurrences(occurrences)
    _require(type(failures) is list, "result_failure_list_required")
    failures = [core("UtilityFailure", row) for row in failures]
    result = _result_context(result, operation, outcome, occurrences, failures)
    prepared = _prepared_context(prepared_database, result, occurrences)
    projection = {name: [] for name in _LEGACY_FACT_SCHEMAS if name != "status"}
    projection["status"] = {"source_ref": source_ref, "state": "unavailable", "native_state": outcome["state"],
        "writer_closed": outcome["writer_closed"], "inventory_complete": outcome["inventory_complete"],
        "result_completeness": None if result is None else result.get("population_completeness", result.get("completeness"))}

    def missing(request_type, reason, **fields):
        projection["missing"].append({"source_ref": source_ref,
            "request": {"type": request_type, **fields}, "reason": reason})

    selected_keys, checks, problems = set(), [], list(failures)
    database_key = result.get("database_key", operation["database_key"]) if result is not None else operation["database_key"]
    if result is not None:
        checks.extend(result["checks"]); problems.extend(result["failures"])
    selected = selector["sequences"]
    if selected is not None:
        matched = set()
        for row in [] if result is None else result["records"]:
            requested = [ordinal for ordinal in selected["selector_ordinals"] if ordinal in row["matched_selector_ordinals"]]
            if not requested:
                continue
            selected_keys.add(row["record_key"]); matched.update(requested)
            projection["sequences"].append({"source_ref": source_ref, "database_key": database_key,
                "record_key": row["record_key"], "occurrence_id": result["output_occurrence"]["occurrence_id"],
                "selector_ordinals": requested, **{key: deepcopy(row[key]) for key in _SEQUENCE_KEYS},
                "sequences": {key: deepcopy(row[key]) for key in selected["sequence_fields"]}})
            checks.extend(row["checks"]); problems.extend(row["failures"])
        for ordinal in selected["selector_ordinals"]:
            if ordinal not in matched:
                missing("sequence_selector", "result_unavailable" if result is None else "selection_unavailable", ordinal=ordinal)
    fields = [] if result is None else result.get("native_fields", result.get("native_metadata", []))
    field_subject = ({"subject": deepcopy(result["subject"])}
        if result is not None and result["version"] == "blast_database_inspection_v2" else {"database_key": database_key})
    projection["database_fields"] = [{"source_ref": source_ref, **field_subject, **deepcopy(row)}
        for row in fields if row["field_name"] in selector["database_fields"]]
    for name in selector["database_fields"]:
        if not any(row["field_name"] == name for row in fields):
            missing("database_field", "result_unavailable" if result is None else "field_unavailable", field_name=name)
    for name in ("integrity", "preparation"):
        if selector[name] is None:
            continue
        if result is None:
            missing(name, "result_unavailable")
        else:
            projection[name].append({"source_ref": source_ref, "database_key": database_key,
                **({"scope": result["scope"]} if name == "integrity" else {}),
                "fields": {key: deepcopy(result[key]) for key in selector[name]["fields"]}})
    if selector["prepared_database"]:
        if prepared is not None:
            projection["prepared_database"].append({"source_ref": source_ref, "database_key": database_key, **deepcopy(prepared)})
            problems.extend(prepared["failures"])
        if prepared is None or prepared["status"] == "unavailable":
            missing("prepared_database", "prepared_database_unavailable")
    for slot in selector["artifacts"]:
        if not any(_slot_matches(slot, row) for row in occurrences):
            missing("artifact", "artifact_unavailable", slot=slot)
    projection["artifacts"] = [{"source_ref": source_ref, **deepcopy(row)}
        for row in _selected_artifacts(selector["artifacts"], occurrences)]
    available = {}
    for row in validate_blast_utility_fact_values(FACT_PREFIX + "saved_data", saved_data):
        _require(row["source_ref"] == source_ref and row["kind"] not in available, "saved_data_context_conflict")
        if row["kind"] == "result":
            _require(result is not None and row["schema"] == result["version"], "saved_result_context_conflict")
        else:
            _require(prepared is not None and prepared["status"] == "available", "saved_prepared_database_unavailable")
            _require(row["schema"] == prepared["manifest"]["version"], "saved_prepared_database_schema_conflict")
        available[row["kind"]] = row
    for kind in selector["saved_data"]:
        if kind in available:
            projection["saved_data"].append(available[kind])
        else:
            missing("saved_data", "saved_data_unavailable", kind=kind)
    all_records = set() if result is None else {row["record_key"] for row in result.get("records", [])}
    if selector["include_checks"]:
        if result is None:
            missing("checks", "result_unavailable")
            checks = []
        projection["checks"] = [{"source_ref": source_ref, **deepcopy(row)} for row in _unique(checks)
            if not (set(row["subject_refs"]) & all_records) or set(row["subject_refs"]) & selected_keys]
    projection["failures"] = [{"source_ref": source_ref, **deepcopy(row)} for row in _unique(problems)
        if row["record_key"] is None or row["record_key"] in selected_keys or
        row["record_key"] not in all_records and row["stage"] in {"parse", "association"}]
    projection["record_refs"] = list(dict.fromkeys([source_ref,
        *[row["artifact_ref"] for row in projection["artifacts"]],
        *[row["artifact_ref"] for row in projection["saved_data"]]]))
    projection["status"]["state"] = _state(projection, outcome)
    return validate_blast_utility_projection(projection, source_ref=source_ref, operation=operation,
        native_outcome=outcome, selector=selector, occurrences=occurrences)


def _qualifications(rows):
    return sorted(_unique(rows), key=lambda row: (row["pointer"], row["reason"]))


def _qualification(pointer, reason="not_supplied"):
    return {"pointer": pointer, "reason": reason}


def _identity_qualifications(identity, pointer):
    return [_qualification(pointer + "/version")] if identity["version"] is None else []


def _member_qualifications(member, pointer, *, unknown=False):
    result = _identity_qualifications(member["member_identifier"], pointer + "/member_identifier")
    if unknown and member["member_kind"] == "unknown":
        result.append(_qualification(pointer + "/member_kind"))
    for key, kinds in (("read_identity", {"read"}), ("reference_identity", {"reference", "wgs_sequence"})):
        detail = member[key]
        prefix = pointer + "/" + key
        if detail is None:
            result.append(_qualification(prefix, "not_supplied" if member["member_kind"] in kinds else "not_applicable"))
        elif key == "read_identity":
            result.extend(_qualification(prefix + "/" + name) for name in ("spot_id", "read_index") if detail[name] is None)
        else:
            result.extend(_identity_qualifications(detail["identifier"], prefix + "/identifier"))
            result.extend(_qualification(prefix + "/" + name) for name in ("full_length", "sequence_sha256") if detail[name] is None)
    if member["sample_key"] is None:
        result.append(_qualification(pointer + "/sample_key"))
    return result


def _sample_qualifications(rows, pointer):
    result = []
    for index, row in enumerate(rows):
        prefix, link = pointer + "/" + str(index) + "/link", row["link"]
        result.extend(_identity_qualifications(link["sample_identifier"], prefix + "/sample_identifier"))
        if link["biosample_identifier"] is None:
            result.append(_qualification(prefix + "/biosample_identifier"))
        else:
            result.extend(_identity_qualifications(link["biosample_identifier"], prefix + "/biosample_identifier"))
    return result


def _context_qualifications(context):
    result = []
    for index, row in enumerate(context["source_inputs"]):
        prefix = "/source_inputs/" + str(index)
        if row["dataset_key"] is None:
            result.append(_qualification(prefix + "/dataset_key"))
        if row["dataset_type"] == "unknown":
            result.append(_qualification(prefix + "/dataset_type"))
        result.extend(_qualification(prefix + "/snapshot/" + key)
                      for key, value in row["snapshot"].items() if value is None)
        for n, identity in enumerate(row["run_identifiers"]):
            result.extend(_identity_qualifications(identity, prefix + "/run_identifiers/" + str(n)))
    if context["selection_kind"] is None:
        result.append(_qualification("/selection_kind", "not_applicable"))
    for index, binding in enumerate(context["entry_identifier_bindings"]):
        result.extend(_identity_qualifications(binding["identifier"], "/entry_identifier_bindings/" + str(index) + "/identifier"))
    for index, member in enumerate(context["member_bindings"]):
        result.extend(_member_qualifications(member, "/member_bindings/" + str(index), unknown=True))
    result.extend(_sample_qualifications(context["sample_links"], "/sample_links"))
    for index, binding in enumerate(context["dependency_database_bindings"]):
        for key in ("version", "release"):
            if binding["identity"][key] is None:
                result.append(_qualification("/dependency_database_bindings/" + str(index) + "/identity/" + key))
    for index, dependency in enumerate(context["declared_dependencies"]):
        for key in ("list_occurrence_id", "list_entry_ordinal"):
            if dependency[key] is None:
                result.append(_qualification("/declared_dependencies/" + str(index) + "/" + key, "not_applicable"))
    return _qualifications(result)


def _vdb_identity(member, links, *, member_reason="not_supplied"):
    if member is None:
        qualifications = [_qualification("/member", member_reason), _qualification("/sample_links", "member_unresolved")]
    else:
        qualifications = _member_qualifications(member, "/member")
        if not links:
            qualifications.append(_qualification("/sample_links"))
        qualifications.extend(_sample_qualifications(links, "/sample_links"))
    return {"member": deepcopy(member), "sample_links": deepcopy(links), "qualifications": _qualifications(qualifications)}


def _field_qualifications(fields, length_reason=None):
    reasons = {"native_oid": "native_not_reported", "native_accession": "native_not_reported",
        "native_reported_length": "native_row_invalid", "requested_range": "not_applicable",
        "effective_range": "not_applicable", "returned_symbol_count": length_reason}
    result = []
    for name, value in fields.items():
        if value is None:
            _require(reasons.get(name) is not None, "sequence_null_qualification_required")
            result.append(_qualification("/fields/" + name, reasons[name]))
    return _qualifications(result)


def _validate_vdb_sequence_fact(row):
    _require(row["line_number"] == row["native_row_ordinal"] + 1, "sequence_native_location_conflict")
    entries = row["scope"]["kind"] == "selected_entries"
    _require((entries and bool(row["selector_ordinals"]) and row["association"] in {"exact", "explicit"})
             or (not entries and not row["selector_ordinals"] and row["association"] == "not_applicable"),
             "sequence_association_unresolved")
    fields = row["fields"]
    _require("native_reported_length" not in fields or "native_length_basis" in fields, "sequence_native_length_basis_required")
    count_reasons = [q["reason"] for q in row["field_qualifications"] if q["pointer"] == "/fields/returned_symbol_count"]
    if "returned_symbol_count" in fields and fields["returned_symbol_count"] is None:
        _require(len(count_reasons) == 1 and count_reasons[0] in {
            "native_row_invalid", "sequence_symbol_invalid", "sequence_length_conflict"}, "sequence_null_qualification_required")
    _require(row["field_qualifications"] == _field_qualifications(fields, count_reasons[0] if count_reasons else None),
             "sequence_field_qualification_conflict")
    if "vdb_identity" in row:
        identity = row["vdb_identity"]
        member, links = identity["member"], identity["sample_links"]
        reason = "not_supplied"
        if member is None:
            reasons = [q["reason"] for q in identity["qualifications"] if q["pointer"] == "/member"]
            _require(len(reasons) == 1 and reasons[0] in {"not_supplied", "supplied_binding_conflict"} and not links,
                     "sequence_member_qualification_conflict")
            reason = reasons[0]
        else:
            core("VDBMember", member)
            _require((member["sample_key"] is None and not links) or (member["sample_key"] is not None and bool(links)),
                     "sequence_sample_link_conflict")
            _require(all(link["dataset_key"] == member["dataset_key"]
                and link["link"]["sample_key"] == member["sample_key"] for link in links), "sequence_sample_link_conflict")
            if links:
                identities = [{k: item["link"][k] for k in ("sample_identifier", "biosample_identifier")} for item in links]
                _require(all(item == identities[0] for item in identities), "sequence_sample_link_conflict")
        _require(identity == _vdb_identity(member, links, member_reason=reason), "sequence_identity_qualification_conflict")


def _qualified_vdb_context(context, *, source_ref, operation, outcome, occurrences, parsed):
    if context is None:
        _require(not parsed, "vdb_qualified_context_required")
        return None
    context = _copy(context)
    _require(type(context) is dict and set(context) == {"operation", "native_outcome", "occurrences", "database_binding",
        "failures", "operation_input_occurrences", "vdb_context"}, "vdb_qualified_context_invalid")
    _require(context["operation"] == operation and context["native_outcome"] == outcome
             and context["occurrences"] == occurrences, "vdb_original_context_conflict")
    binding = core("DatabaseBinding", context["database_binding"])
    _require(binding["source_ref"] == source_ref, "vdb_source_context_conflict")
    from .blast_vdb_utility_contracts import validate_vdb_utility_context
    validate_vdb_utility_context(context["vdb_context"], operation=operation, database_binding=binding,
        operation_input_occurrences=context["operation_input_occurrences"] if parsed else None)
    known = {row["occurrence_id"]: row for row in occurrences}
    bindings = [binding, *context["vdb_context"]["dependency_database_bindings"]]
    _require(all(set(b["occurrence_ids"]) <= known.keys() for b in bindings), "vdb_database_occurrence_conflict")
    _require(all(known[oid]["direction"] == "input" for b in bindings for oid in b["occurrence_ids"]),
             "vdb_database_occurrence_conflict")
    _require(type(context["operation_input_occurrences"]) is list, "vdb_operation_input_context_conflict")
    inputs = [core("ArtifactOccurrence", row) for row in context["operation_input_occurrences"]]
    _require(all(known.get(row["occurrence_id"]) == row for row in inputs), "vdb_operation_input_context_conflict")
    if parsed:
        _require(set(operation["input_occurrence_ids"]) <= {key for key, row in known.items() if row["direction"] == "input"},
                 "vdb_operation_input_context_conflict")
    _require(type(context["failures"]) is list, "result_failure_list_required")
    for failure in context["failures"]:
        core("UtilityFailure", failure)
        _require(failure["occurrence_id"] is None or failure["occurrence_id"] in known,
                 "projection_failure_occurrence_conflict")
        _require(failure["native_returncode"] is None or failure["native_returncode"] == outcome["returncode"],
                 "projection_failure_outcome_conflict")
    return context


def _vdb_requested(selector):
    result = []
    if selector["sequences"] is not None:
        selection = selector["sequences"]["selection"]
        if selection["values"] is None:
            result.append({"type": "native_enumeration"})
        else:
            result.extend({"type": "sequence_selector" if selection["kind"] == "selector_ordinals" else "native_row",
                           "ordinal": ordinal} for ordinal in selection["values"])
    result.extend({"type": "database_field", "field_name": key} for key in selector["database_fields"])
    paths = selector["paths"]
    if paths is not None:
        if paths["native_path_ordinals"] is None:
            result.extend({"type": "path_population", "kind": kind} for kind in paths["kinds"])
        elif paths["kinds"]:
            result.extend({"type": "path_row", "ordinal": ordinal} for ordinal in paths["native_path_ordinals"])
        if paths["include_sections"]:
            result.extend({"type": "path_section", "kind": kind} for kind in paths["kinds"])
    if selector["vdb_context"]:
        result.append({"type": "vdb_context"})
    if selector["include_checks"]:
        result.append({"type": "checks"})
    result.extend({"type": "artifact", "slot": row} for row in selector["artifacts"])
    result.extend({"type": "saved_data", "kind": kind} for kind in selector["saved_data"])
    return result


def _vdb_list_artifact_selection(selector, operation, context, occurrences, *, parsed):
    selections = [row for row in selector["artifacts"] if row["direction"] == "input" and row["role"] == "database_list"]
    if not selections:
        return
    original = operation["parameters"]["database_selection"]
    explicit = {original["list_occurrence_id"]} if original["source"] == "dbs_file" else set()
    bound = set()
    declared_missing = set()
    if context is not None:
        membership = {oid for binding in [context["database_binding"], *context["vdb_context"]["dependency_database_bindings"]]
                      for oid in binding["occurrence_ids"]}
        bound = {row["occurrence_id"] for row in occurrences if row["direction"] == "input"
                 and row["role"] == "database_list" and row["native_format"] == "text" and row["occurrence_id"] in membership}
        if not parsed:
            declared_missing = {row["list_occurrence_id"] for row in context["vdb_context"]["declared_dependencies"]
                                if row["source"] in {"dblist_file", "vdblist_file"}}
        _require(bool(explicit | bound | declared_missing), "artifact_selection_not_applicable")
    # A known but uncaptured declaration can yield qualified unavailability.
    # A role/provenance string alone can never make a captured row grantable.
    for row in _selected_artifacts(selections, occurrences):
        _require(row["native_format"] == "text" and row["occurrence_id"] in (explicit | bound),
                 "projection_database_list_membership_conflict")


def _vdb_state(projection, outcome, selector):
    state = _state(projection, outcome)
    if not projection["missing"] or state == "partial":
        return state
    useful = any(projection[name] for name in ("paths", "path_sections", "vdb_context"))
    # An available empty enumeration or an explicitly reported empty path
    # population was delivered. Missing bytes elsewhere do not erase that fact.
    missing = [row["request"] for row in projection["missing"]]
    useful |= projection["status"]["result_completeness"] is not None and any(
        request["type"] in {"native_enumeration", "path_population"} and request not in missing
        for request in _vdb_requested(selector))
    return "partial" if useful else state


def _validate_vdb_projection(projection, *, source_ref, operation, native_outcome, selector, occurrences, context):
    occurrences = _occurrences(occurrences)
    projection = _validated(projection, _object({
        **{name: schema if name == "status" else _array(schema) for name, schema in _FACT_SCHEMAS.items()},
        "record_refs": _array(_STR, unique=True)}))
    for name in _FACT_SCHEMAS:
        rows = [projection[name]] if name == "status" else projection[name]
        validate_blast_utility_fact_values(FACT_PREFIX + name, rows)
        _require(all(row["source_ref"] == source_ref for row in rows), "projection_source_conflict")
    status = projection["status"]
    _require(all(status[key] == native_outcome["state" if key == "native_state" else key]
                 for key in ("native_state", "writer_closed", "inventory_complete")), "projection_outcome_conflict")
    extracting = operation["mode"] == "extract_sequences"
    allowed = {None, "complete_selection", "partial_selection", "unknown"} if extracting else {None, "complete", "partial", "unknown"}
    _require(status["result_completeness"] in allowed, "projection_completeness_conflict")
    parsed = status["result_completeness"] is not None
    context = _qualified_vdb_context(context, source_ref=source_ref, operation=operation,
        outcome=native_outcome, occurrences=occurrences, parsed=parsed)
    _vdb_list_artifact_selection(selector, operation, context, occurrences, parsed=parsed)
    _require(not any(projection[key] for key in ("integrity", "preparation", "prepared_database")), "projection_vdb_operation_conflict")
    _require(parsed or not any(projection[key] for key in
        ("sequences", "database_fields", "paths", "path_sections", "vdb_context", "checks")), "projection_result_required")
    known = {row["occurrence_id"]: row for row in occurrences}
    stdout = [row for row in occurrences if row["direction"] == "output" and row["role"] == "stdout"]
    stderr = [row for row in occurrences if row["direction"] == "output" and row["role"] == "stderr"]
    if parsed:
        _require(len(stdout) == len(stderr) == 1 and stdout[0]["native_format"] == operation["parameters"]["output_format"]
                 and stderr[0]["native_format"] == "text", "projection_vdb_stream_conflict")
    oid = stdout[0]["occurrence_id"] if len(stdout) == 1 else None
    database_key = operation["database_key"]
    expected_artifacts = [{"source_ref": source_ref, **row} for row in _selected_artifacts(selector["artifacts"], occurrences)]
    _require(projection["artifacts"] == expected_artifacts, "projection_artifact_grant_conflict")
    saved_kinds = [row["kind"] for row in projection["saved_data"]]
    _require(saved_kinds == [kind for kind in selector["saved_data"] if kind in saved_kinds]
        and len(saved_kinds) == len(set(saved_kinds)), "projection_saved_data_selection_conflict")
    _require(all(parsed and row["schema"] == blast_utility_result_version_for_operation(operation)
                 and row["kind"] == "result" for row in projection["saved_data"]), "projection_saved_result_version_conflict")
    _require(projection["record_refs"] == list(dict.fromkeys([source_ref,
        *[row["artifact_ref"] for row in projection["artifacts"]], *[row["artifact_ref"] for row in projection["saved_data"]]])),
        "projection_reference_grant_conflict")
    selected = selector["sequences"]
    seen = []
    for row in projection["sequences"]:
        _require(row.get("version") == PREFIX + "sequence_fact_v2" and selected is not None,
                 "projection_sequence_selection_conflict")
        selection, original = selected["selection"], operation["parameters"]["selection"]
        _require(row["database_key"] == database_key and row["occurrence_id"] == oid,
                 "projection_sequence_context_conflict")
        _require(set(row["fields"]) == set(selected["record_fields"])
            and set(row["sequences"]) == set(selected["sequence_fields"])
            and ("vdb_identity" in row) == selected["include_vdb_identity"], "projection_sequence_selection_conflict")
        entries = selection["kind"] == "selector_ordinals"
        _require(row["scope"] == {"kind": "selected_entries" if entries else original["kind"]}, "projection_sequence_scope_conflict")
        if entries:
            _require(row["selector_ordinals"] == [n for n in selection["values"] if n in row["selector_ordinals"]],
                     "projection_sequence_selection_conflict")
            reported = {row["fields"][key] for key in ("native_identifier", "native_accession") if key in row["fields"]}
            expected = [n for n in selection["values"] if original["selectors"][n]["value"] in reported]
            _require(set(expected) <= set(row["selector_ordinals"]), "projection_sequence_association_conflict")
            if row["association"] == "exact" and {"native_identifier", "native_accession"} <= row["fields"].keys():
                _require(row["selector_ordinals"] == expected, "projection_sequence_association_conflict")
        else:
            _require(selection["values"] is None or row["native_row_ordinal"] in selection["values"],
                     "projection_sequence_selection_conflict")
        if "vdb_identity" in row:
            identity = row["vdb_identity"]
            member = identity["member"]
            if member is not None:
                matches = [m for m in context["vdb_context"]["member_bindings"] if m["native_identifier"] == member["native_identifier"]]
                _require(matches == [member] and ("native_identifier" not in row["fields"]
                    or row["fields"]["native_identifier"] == member["native_identifier"]), "projection_member_context_conflict")
                links = [link for link in context["vdb_context"]["sample_links"] if link["dataset_key"] == member["dataset_key"]
                         and link["link"]["sample_key"] == member["sample_key"]]
                _require(identity["sample_links"] == links, "projection_sample_context_conflict")
            else:
                reason = next(q["reason"] for q in identity["qualifications"] if q["pointer"] == "/member")
                matches = ([m for m in context["vdb_context"]["member_bindings"]
                    if m["native_identifier"] == row["fields"]["native_identifier"]] if "native_identifier" in row["fields"] else None)
                if matches is not None:
                    _require(len(matches) != 1 and reason == ("supplied_binding_conflict" if matches else "not_supplied"),
                             "projection_member_context_conflict")
                if reason == "supplied_binding_conflict":
                    identifiers = [m["native_identifier"] for m in context["vdb_context"]["member_bindings"]]
                    _require(len(identifiers) > len(set(identifiers)), "projection_member_context_conflict")
                    _require(any(f["code"] == reason and f["record_key"] == row["record_key"] and f["stage"] == "association"
                                 for f in projection["failures"]), "projection_member_qualification_conflict")
        for qualification in row["field_qualifications"]:
            reason = qualification["reason"]
            if reason in {"native_row_invalid", "sequence_symbol_invalid", "sequence_length_conflict"}:
                _require(any(f["code"] == reason and f["record_key"] == row["record_key"] for f in projection["failures"]),
                         "projection_sequence_qualification_conflict")
        seen.append(row["native_row_ordinal"])
    _require(seen == sorted(set(seen)), "projection_sequence_order_conflict")
    for row in projection["database_fields"]:
        _require(row["field_name"] in selector["database_fields"] and row.get("database_key") == database_key
                 and row["occurrence_id"] == oid, "projection_database_field_context_conflict")
    paths = selector["paths"]
    section_by_index, section_by_kind = {}, {}
    for row in projection["path_sections"]:
        _require(paths is not None and paths["include_sections"] and row["kind"] in paths["kinds"]
            and row["database_key"] == database_key and row["occurrence_id"] == oid, "projection_path_section_selection_conflict")
        _require(row["section_ordinal"] not in section_by_index and row["kind"] not in section_by_kind, "projection_path_section_identity_conflict")
        section_by_index[row["section_ordinal"]] = row
        section_by_kind[row["kind"]] = row
    _require(list(section_by_index) == sorted(section_by_index), "projection_path_section_order_conflict")
    headers = [row["header_line_number"] for row in projection["path_sections"] if row["header_line_number"] is not None]
    _require(headers == sorted(set(headers)), "projection_path_section_order_conflict")
    path_ordinals, path_lines, kind_sections = [], [], {}
    for row in projection["paths"]:
        _require(paths is not None and row["kind"] in paths["kinds"] and (paths["native_path_ordinals"] is None
            or row["native_path_ordinal"] in paths["native_path_ordinals"])
            and row["database_key"] == database_key and row["occurrence_id"] == oid, "projection_path_selection_conflict")
        _require(kind_sections.setdefault(row["kind"], row["section_ordinal"]) == row["section_ordinal"], "projection_path_section_context_conflict")
        if paths["include_sections"]:
            section = section_by_index.get(row["section_ordinal"])
            _require(section is not None and section["kind"] == row["kind"] and section["presence"] == "reported_values"
                and row["line_number"] > section["header_line_number"], "projection_path_section_context_conflict")
            later = [s["header_line_number"] for s in projection["path_sections"]
                     if s["section_ordinal"] > row["section_ordinal"] and s["header_line_number"] is not None]
            _require(not later or row["line_number"] < min(later), "projection_path_section_context_conflict")
        dependencies = {d["ordinal"]: d for d in context["vdb_context"]["declared_dependencies"]}
        databases = {b["database_key"]: b for b in [context["database_binding"], *context["vdb_context"]["dependency_database_bindings"]]}
        for ordinal in row["matched_dependency_ordinals"]:
            _require(ordinal in dependencies, "projection_path_dependency_conflict")
            dependency = dependencies[ordinal]
            bound = databases[dependency["database_key"]]["native_paths"][dependency["native_path_index"]]
            _require(row["native_path"] in {bound, dependency["native_reference"]}, "projection_path_dependency_conflict")
        path_ordinals.append(row["native_path_ordinal"]); path_lines.append(row["line_number"])
    _require(path_ordinals == sorted(set(path_ordinals)) and path_lines == sorted(set(path_lines)), "projection_path_order_conflict")
    _require(len(projection["vdb_context"]) == int(parsed and selector["vdb_context"]),
             "projection_context_selection_conflict")
    for row in projection["vdb_context"]:
        _require(row["database_key"] == database_key and row["context"] == context["vdb_context"], "projection_context_conflict")
    _require(not projection["checks"] or selector["include_checks"], "projection_unrequested_checks")
    selected_keys = {row["record_key"] for row in projection["sequences"]}
    subjects = set(known) | {database_key} | selected_keys
    if context is not None:
        subjects.update(b["database_key"] for b in context["vdb_context"]["dependency_database_bindings"])
    if extracting and operation["parameters"]["selection"]["kind"] == "entries":
        subjects.update(row["value"] for row in operation["parameters"]["selection"]["selectors"])
    for row in projection["checks"]:
        _require(set(row["evidence_occurrence_ids"]) <= known.keys() and set(row["subject_refs"]) <= subjects,
                 "projection_check_evidence_conflict")
    for row in projection["failures"]:
        _require(row["occurrence_id"] is None or row["occurrence_id"] in known, "projection_failure_occurrence_conflict")
        _require(row["native_returncode"] is None or row["native_returncode"] == native_outcome["returncode"], "projection_failure_outcome_conflict")
        if row["record_key"] is not None:
            prefix = str(oid) + "#/records/"
            suffix = row["record_key"].removeprefix(prefix)
            _require(oid is not None and extracting and row["record_key"].startswith(prefix)
                and suffix.isdecimal() and str(int(suffix)) == suffix and row["occurrence_id"] == oid
                and row["line_number"] == int(suffix) + 1
                and (row["record_key"] in selected_keys or row["stage"] in {"parse", "association"}),
                "projection_failure_record_conflict")
    requests, missing = _vdb_requested(selector), []
    for row in projection["missing"]:
        _require(row.get("version") == PREFIX + "missing_fact_v2" and row["request"] in requests
                 and row["request"] not in missing, "projection_missing_request_conflict")
        missing.append(row["request"])
    for request in requests:
        kind = request["type"]
        row = next((r for r in projection["missing"] if r["request"] == request), None)
        reason = None if row is None else row["reason"]
        if kind == "artifact":
            fulfilled = any(_slot_matches(request["slot"], r) for r in occurrences)
            expected_reason = "artifact_unavailable"
        elif kind == "saved_data":
            fulfilled, expected_reason = request["kind"] in saved_kinds, "saved_data_unavailable"
        elif not parsed:
            fulfilled, expected_reason = False, "result_unavailable"
        elif kind in {"sequence_selector", "native_row"}:
            fulfilled = any(request["ordinal"] in r["selector_ordinals"] if kind == "sequence_selector"
                            else request["ordinal"] == r["native_row_ordinal"] for r in projection["sequences"])
            expected_reason = "selection_unavailable"
        elif kind == "database_field":
            fulfilled = any(r["field_name"] == request["field_name"] for r in projection["database_fields"])
            expected_reason = "field_unavailable"
        elif kind == "path_row":
            fulfilled, expected_reason = request["ordinal"] in path_ordinals, "selection_unavailable"
        elif kind in {"path_population", "path_section"}:
            section = section_by_kind.get(request["kind"])
            if section is not None:
                fulfilled = section["presence"] != "not_reported"
            elif kind == "path_section":
                fulfilled = False
            else:
                fulfilled = any(r["kind"] == request["kind"] for r in projection["paths"]) or row is None
            expected_reason = "field_unavailable"
        elif kind == "vdb_context":
            fulfilled, expected_reason = bool(projection["vdb_context"]), "result_unavailable"
        else:  # Available checks and enumerations may both have zero rows.
            fulfilled, expected_reason = True, "result_unavailable"
        _require(fulfilled == (row is None) and (row is None or reason == expected_reason), "projection_missing_population_conflict")
    _require(status["state"] == _vdb_state(projection, native_outcome, selector), "projection_state_conflict")
    return projection


def _project_vdb_result(*, source_ref, operation, native_outcome, result, prepared_database,
                        occurrences, selector, failures, saved_data, context):
    occurrences = _occurrences(occurrences)
    _require(prepared_database is None, "prepared_database_result_not_applicable")
    _require(type(failures) is list, "result_failure_list_required")
    failures = [core("UtilityFailure", failure) for failure in failures]
    context = _qualified_vdb_context(context, source_ref=source_ref, operation=operation,
        outcome=native_outcome, occurrences=occurrences, parsed=result is not None)
    _vdb_list_artifact_selection(selector, operation, context, occurrences, parsed=result is not None)
    if result is not None:
        # This invokes the existing common validator and its shared symbol
        # authority. Projection copies its retained values; it calculates none.
        result = validate_blast_utility_result(result)
        _require(result["version"] == blast_utility_result_version_for_operation(operation)
            and result["operation"] == operation and result["original_outcome"] == native_outcome,
            "result_original_context_conflict")
        _require(all(result[key] == context[key] for key in
            ("database_binding", "operation_input_occurrences", "vdb_context")), "vdb_result_context_conflict")
        known = {row["occurrence_id"]: row for row in occurrences}
        _require(all(known.get(result[key]["occurrence_id"]) == result[key] for key in
            ("output_occurrence", "stderr_occurrence")), "result_occurrence_context_conflict")
    projection = {name: [] for name in _FACT_SCHEMAS if name != "status"}
    projection["status"] = {"source_ref": source_ref, "state": "unavailable", "native_state": native_outcome["state"],
        "writer_closed": native_outcome["writer_closed"], "inventory_complete": native_outcome["inventory_complete"],
        "result_completeness": None if result is None else result.get("population_completeness", result.get("completeness"))}
    database_key, selected_keys = operation["database_key"], set()
    checks = [] if result is None else list(result["checks"])
    problems = [*failures, *([] if result is None else result["failures"])]
    selected = selector["sequences"]
    if selected is not None and result is not None:
        selection = selected["selection"]
        for row in result["records"]:
            if selection["kind"] == "selector_ordinals":
                ordinals = [n for n in selection["values"] if n in row["matched_selector_ordinals"]]
                if not ordinals:
                    continue
            else:
                ordinals = []
                if selection["values"] is not None and row["native_row_ordinal"] not in selection["values"]:
                    continue
            fields = {key: deepcopy(row[key]) for key in selected["record_fields"]}
            reasons = [check["reason"] for check in row["checks"] if check["name"] == "sequence_length"
                       and row["record_key"] in check["subject_refs"]]
            if "returned_symbol_count" in fields and fields["returned_symbol_count"] is None:
                _require(len(set(reasons)) == 1 and reasons[0] in {
                    "native_row_invalid", "sequence_symbol_invalid", "sequence_length_conflict"}, "sequence_length_qualification_required")
            if "native_reported_length" in fields and fields["native_reported_length"] is None:
                _require(any(f["code"] == "native_row_invalid" and f["record_key"] == row["record_key"]
                             and f["stage"] == "parse" for f in row["failures"]), "sequence_native_length_qualification_required")
            fact = {"version": PREFIX + "sequence_fact_v2", "source_ref": source_ref, "database_key": database_key,
                "occurrence_id": result["output_occurrence"]["occurrence_id"], "selector_ordinals": ordinals,
                **{key: deepcopy(row[key]) for key in ("record_key", "native_row_ordinal", "line_number", "association", "completeness")},
                "scope": deepcopy(result["scope"]), "fields": fields,
                "sequences": {key: row[key] for key in selected["sequence_fields"]},
                "field_qualifications": _field_qualifications(fields, reasons[0] if reasons else None)}
            if selected["include_vdb_identity"]:
                member = row["vdb_member"]
                links = [] if member is None else [link for link in result["vdb_context"]["sample_links"]
                    if link["dataset_key"] == member["dataset_key"] and link["link"]["sample_key"] == member["sample_key"]]
                matches = [m for m in result["vdb_context"]["member_bindings"] if m["native_identifier"] == row["native_identifier"]]
                fact["vdb_identity"] = _vdb_identity(member, links,
                    member_reason="supplied_binding_conflict" if len(matches) > 1 else "not_supplied")
            projection["sequences"].append(fact)
            selected_keys.add(row["record_key"])
            checks.extend(row["checks"]); problems.extend(row["failures"])
    if result is not None:
        projection["database_fields"] = [{"source_ref": source_ref, "database_key": database_key, **deepcopy(row)}
            for row in result.get("native_fields", []) if row["field_name"] in selector["database_fields"]]
        paths = selector["paths"]
        if paths is not None:
            oid = result["output_occurrence"]["occurrence_id"]
            for row in result["path_records"]:
                if row["kind"] in paths["kinds"] and (paths["native_path_ordinals"] is None
                        or row["native_path_ordinal"] in paths["native_path_ordinals"]):
                    projection["paths"].append({"source_ref": source_ref, "database_key": database_key,
                        "occurrence_id": oid, "path_ref": oid + "#/path_records/" + str(row["native_path_ordinal"]), **deepcopy(row)})
            if paths["include_sections"]:
                projection["path_sections"] = [{"source_ref": source_ref, "database_key": database_key, "occurrence_id": oid,
                    "section_ref": oid + "#/path_sections/" + str(index), "section_ordinal": index, **deepcopy(row)}
                    for index, row in enumerate(result["path_sections"]) if row["kind"] in paths["kinds"]]
        if selector["vdb_context"]:
            projection["vdb_context"] = [{"source_ref": source_ref, "database_key": database_key,
                "context": deepcopy(result["vdb_context"]), "qualifications": _context_qualifications(result["vdb_context"])}]
    projection["artifacts"] = [{"source_ref": source_ref, **deepcopy(row)}
        for row in _selected_artifacts(selector["artifacts"], occurrences)]
    available = {}
    for row in validate_blast_utility_fact_values(FACT_PREFIX + "saved_data", saved_data):
        _require(row["source_ref"] == source_ref and row["kind"] not in available, "saved_data_context_conflict")
        _require(row["kind"] == "result" and result is not None and row["schema"] == result["version"], "saved_result_context_conflict")
        available[row["kind"]] = row
    projection["saved_data"] = [available[kind] for kind in selector["saved_data"] if kind in available]
    all_records = set() if result is None else {r["record_key"] for r in result.get("records", [])}
    if selector["include_checks"] and result is not None:
        projection["checks"] = [{"source_ref": source_ref, **deepcopy(row)} for row in _unique(checks)
            if not set(row["subject_refs"]) & all_records or set(row["subject_refs"]) & selected_keys]
    projection["failures"] = [{"source_ref": source_ref, **deepcopy(row)} for row in _unique(problems)
        if row["record_key"] is None or row["record_key"] in selected_keys or
        row["record_key"] not in all_records and row["stage"] in {"parse", "association"}]
    sections = {} if result is None else {row["kind"]: row for row in result.get("path_sections", [])}
    for request in _vdb_requested(selector):
        kind, reason = request["type"], None
        if kind == "artifact":
            if not any(_slot_matches(request["slot"], row) for row in occurrences):
                reason = "artifact_unavailable"
        elif kind == "saved_data":
            if request["kind"] not in available:
                reason = "saved_data_unavailable"
        elif result is None:
            reason = "result_unavailable"
        elif kind in {"sequence_selector", "native_row"}:
            present = ({n for row in projection["sequences"] for n in row["selector_ordinals"]}
                if kind == "sequence_selector" else {row["native_row_ordinal"] for row in projection["sequences"]})
            if request["ordinal"] not in present:
                reason = "selection_unavailable"
        elif kind == "database_field":
            if not any(row["field_name"] == request["field_name"] for row in projection["database_fields"]):
                reason = "field_unavailable"
        elif kind == "path_row":
            if not any(row["native_path_ordinal"] == request["ordinal"] for row in projection["paths"]):
                reason = "selection_unavailable"
        elif kind in {"path_population", "path_section"}:
            if sections.get(request["kind"], {}).get("presence", "not_reported") == "not_reported":
                reason = "field_unavailable"
        if reason is not None:
            projection["missing"].append({"version": PREFIX + "missing_fact_v2", "source_ref": source_ref,
                "request": deepcopy(request), "reason": reason})
    projection["record_refs"] = list(dict.fromkeys([source_ref,
        *[row["artifact_ref"] for row in projection["artifacts"]], *[row["artifact_ref"] for row in projection["saved_data"]]]))
    projection["status"]["state"] = _vdb_state(projection, native_outcome, selector)
    return validate_blast_utility_projection(projection, source_ref=source_ref, operation=operation,
        native_outcome=native_outcome, selector=selector, occurrences=occurrences, context=context)


__all__ = ["NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA", "NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V1_SCHEMA",
    "NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA", "FACT_SOURCES", "PROJECTION_FIELDS", "PROJECTION_V2_FIELDS",
    "VDB_RECORD_FIELDS", "VDB_DATABASE_FIELDS", "VDB_PATH_KINDS", "SEQUENCE_V2_SCHEMA", "MISSING_V2_SCHEMA",
    "PATH_SCHEMA", "PATH_SECTION_SCHEMA", "VDB_CONTEXT_SCHEMA", "blast_utility_projection_fields",
    "IDENTIFIER_NAMESPACES", "STATUS_SCHEMA", "SEQUENCE_SCHEMA", "DATABASE_FIELD_SCHEMA",
    "INTEGRITY_SCHEMA", "PREPARATION_SCHEMA", "PREPARED_DATABASE_SCHEMA", "CHECK_SCHEMA",
    "FAILURE_SCHEMA", "MISSING_SCHEMA", "ARTIFACT_SCHEMA", "SAVED_DATA_SCHEMA",
    "validate_blast_utility_result_selector", "project_blast_utility_result",
    "validate_blast_utility_projection", "blast_utility_fact_sources", "validate_blast_utility_fact_values",
    "projection_identifiers"]
