"""Pure requested views of retained BLAST utility records.

The shared utility records own native values and their validation. These views
copy selected values; they do not parse, calculate, read files or grant access
to artifacts merely mentioned by a provenance relationship.
"""
from __future__ import annotations

from copy import deepcopy

from .blast_utility_contracts import (
    SCHEMAS, validate_blast_utility_operation, validate_blast_utility_record as core,
    validate_blast_utility_result,
)
from .domain import ContractError
from .native_blast_standard_database_contracts import _copy, _schema


PREFIX = "native_blast_utility_"
FACT_PREFIX = "execution.blast_utility_"
IDENTIFIER_NAMESPACES = (PREFIX + "record", PREFIX + "occurrence")
SEQUENCE_FIELDS = ("original_sequence", "normalized_sequence")
DATABASE_FIELDS = tuple(branch["properties"]["field_name"]["const"]
                       for branch in SCHEMAS["NativeField"]["anyOf"])
INTEGRITY_FIELDS = ("observed_checked_count", "observed_population_count",
                   "observed_sampled_oids", "realized_seed", "diagnostics")
PREPARATION_FIELDS = ("identity", "software", "argv", "native_paths", "dependencies",
                      "inventory_complete", "detail", "compatibility")
RESULT_VERSIONS = tuple(SCHEMAS[name]["properties"]["version"]["const"] for name in (
    "SequenceExtraction", "DatabaseInspection", "DatabaseIntegrity", "DatabaseArtifactSet"))
PREPARED_DATABASE_VERSION = "native_blast_standard_prepared_database_manifest_v1"
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
NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA = _object({
    "version": {"const": PREFIX + "result_selector_v1"},
    "sequences": _nullable(_object({"selector_ordinals": _array(_UINT, unique=True),
        "sequence_fields": _array(_enum(SEQUENCE_FIELDS), unique=True)})),
    "database_fields": _array(_enum(DATABASE_FIELDS), unique=True),
    "integrity": _nullable(_object({"fields": _array(_enum(INTEGRITY_FIELDS), unique=True)})),
    "preparation": _nullable(_object({"fields": _array(_enum(PREPARATION_FIELDS), unique=True)})),
    "prepared_database": _BOOL, "include_checks": _BOOL,
    "artifacts": _array(_SLOT_SCHEMA, unique=True),
    "saved_data": _array(_enum(("result", "prepared_database")), unique=True),
})
STATUS_SCHEMA = _object({"source_ref": _SOURCE,
    "state": _enum(("complete", "partial", "failed", "unavailable")),
    "native_state": SCHEMAS["NativeOutcome"]["properties"]["state"],
    "writer_closed": _BOOL, "inventory_complete": _BOOL,
    "result_completeness": _nullable(_enum(("complete_selection", "partial_selection",
                                            "complete", "partial", "unknown")))})
_EXTRACTION_ROW = SCHEMAS["SequenceExtraction"]["properties"]["records"]["items"]["properties"]
_SEQUENCE_KEYS = tuple(key for key in _EXTRACTION_ROW if key not in {
    "record_key", "matched_selector_ordinals", *SEQUENCE_FIELDS, "checks", "failures"})
SEQUENCE_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "record_key": _RECORD, "occurrence_id": _OCCURRENCE,
    "selector_ordinals": _array(_UINT, unique=True, minItems=1),
    **{key: _EXTRACTION_ROW[key] for key in _SEQUENCE_KEYS},
    "sequences": _object({key: _EXTRACTION_ROW[key] for key in SEQUENCE_FIELDS}, required=[])})
DATABASE_FIELD_SCHEMA = {"anyOf": [_with_source(branch, database_key=_STR)
    for branch in SCHEMAS["NativeField"]["anyOf"]]}
_INTEGRITY = SCHEMAS["DatabaseIntegrity"]["properties"]
INTEGRITY_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "scope": _INTEGRITY["scope"],
    "fields": _object({key: _INTEGRITY[key] for key in INTEGRITY_FIELDS}, required=[])})
_PREPARATION = SCHEMAS["DatabaseArtifactSet"]["properties"]
PREPARATION_SCHEMA = _object({"source_ref": _SOURCE, "database_key": _STR,
    "fields": _object({key: _PREPARATION[key] for key in PREPARATION_FIELDS}, required=[])})
PREPARED_DATABASE_SCHEMA = _with_source(SCHEMAS["PreparedDatabaseProjection"], database_key=_STR)
CHECK_SCHEMA = _with_source(SCHEMAS["ValidationObservation"])
FAILURE_SCHEMA = _with_source(SCHEMAS["UtilityFailure"])
ARTIFACT_SCHEMA = _with_source(SCHEMAS["ArtifactOccurrence"])
ARTIFACT_SCHEMA["properties"]["occurrence_id"] = deepcopy(_OCCURRENCE)
ARTIFACT_SCHEMA["properties"]["artifact_ref"] = deepcopy(_ARTIFACT)
SAVED_DATA_SCHEMA = _object({"source_ref": _SOURCE,
    "kind": _enum(("result", "prepared_database")), "artifact_ref": _ARTIFACT,
    "sha256": SCHEMAS["ArtifactOccurrence"]["properties"]["sha256"], "size_bytes": _UINT,
    "schema": _enum((*RESULT_VERSIONS, PREPARED_DATABASE_VERSION))})
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
    mode = operation["mode"]
    if selector["sequences"] is not None:
        _require(mode == "extract_sequences", "sequence_selection_not_applicable")
        wanted = set(selector["sequences"]["selector_ordinals"])
        _require(wanted <= {row["ordinal"] for row in operation["parameters"]["selectors"]},
                 "sequence_selector_not_in_original_request")
    _require(not selector["database_fields"] or mode in {"info", "metadata", "create_sequence_database"},
             "database_fields_not_applicable")
    _require(selector["integrity"] is None or mode == "integrity", "integrity_selection_not_applicable")
    _require(mode == "create_sequence_database" or (selector["preparation"] is None
        and not selector["prepared_database"] and "prepared_database" not in selector["saved_data"]),
        "preparation_selection_not_applicable")
    inputs = ({"sequence_input", "taxid_map", "mask_input"} if mode == "create_sequence_database" else
              {"database_file", "database_metadata", "database_manifest", "preparation_receipt",
               "input_manifest", "offline_configuration"})
    outputs = {"stdout", "stderr", "diagnostics"}
    if mode == "create_sequence_database":
        outputs |= {"database_file", "database_metadata", "database_manifest", "preparation_receipt", "input_manifest"}
    elif mode == "extract_sequences":
        outputs.add("extracted_sequences")
    elif mode in {"info", "metadata"}:
        outputs.add("database_metadata")
    _require(all(row["role"] in (inputs if row["direction"] == "input" else outputs)
                 for row in selector["artifacts"]), "artifact_selection_not_applicable")
    return selector


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
            _require((row["kind"] == "prepared_database") == (row["schema"] == PREPARED_DATABASE_VERSION),
                     "saved_data_schema_conflict")
        elif name == "database_fields":
            core("NativeField", {key: value for key, value in row.items()
                                 if key not in {"source_ref", "database_key"}})
        elif name == "sequences":
            _require(row["record_key"] == row["occurrence_id"] + "#/records/" + str(row["native_row_ordinal"]),
                     "sequence_record_identity_conflict")
            _require(row["association"] in {"exact", "explicit"}, "sequence_association_unresolved")
        elif name == "prepared_database":
            projection = core("PreparedDatabaseProjection", {key: row[key] for key in ("status", "manifest", "failures")})
            _require(projection["manifest"] is None or projection["manifest"]["database_key"] == row["database_key"],
                     "prepared_database_key_conflict")
        elif name == "status":
            _require(not row["inventory_complete"] or row["writer_closed"], "status_inventory_conflict")
    return rows


def _requested(selector):
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
        references.extend(row["occurrence_id"] for field in ("sequences", "artifacts")
                          for row in projection.get(field, []))
    return list(dict.fromkeys(references))


def _state(projection, outcome):
    if not projection["missing"]:
        return "complete"
    useful = any(projection[name] for name in ("sequences", "database_fields", "integrity",
        "preparation", "prepared_database", "artifacts", "saved_data", "checks"))
    return "partial" if useful else "failed" if outcome["state"] == "failed" else "unavailable"


def validate_blast_utility_projection(projection: dict, *, source_ref: str, operation: dict,
                                     native_outcome: dict, selector: dict, occurrences: list) -> dict:
    """Validate selected fields and reference grants, without replaying calculations."""
    _text(source_ref)
    operation = validate_blast_utility_operation(operation)
    outcome = core("NativeOutcome", native_outcome)
    selector = validate_blast_utility_result_selector(selector, operation=operation)
    occurrences = _occurrences(occurrences)
    projection = _validated(projection, _object({
        **{name: schema if name == "status" else _array(schema) for name, schema in _FACT_SCHEMAS.items()},
        "record_refs": _array(_STR, unique=True)}))
    for name in _FACT_SCHEMAS:
        rows = [projection[name]] if name == "status" else projection[name]
        validate_blast_utility_fact_values(FACT_PREFIX + name, rows)
        _require(all(row["source_ref"] == source_ref for row in rows), "projection_source_conflict")
    status = projection["status"]
    _require(all(status[key] == outcome["state" if key == "native_state" else key]
                 for key in ("native_state", "writer_closed", "inventory_complete")), "projection_outcome_conflict")
    allowed_completeness = ({None, "complete_selection", "partial_selection", "unknown"}
        if operation["mode"] == "extract_sequences" else {None, "complete", "partial", "unknown"}
        if operation["mode"] in {"info", "metadata"} else {None})
    _require(status["result_completeness"] in allowed_completeness, "projection_completeness_conflict")
    expected_artifacts = [{"source_ref": source_ref, **row}
                          for row in _selected_artifacts(selector["artifacts"], occurrences)]
    _require(projection["artifacts"] == expected_artifacts, "projection_artifact_grant_conflict")
    saved_kinds = [row["kind"] for row in projection["saved_data"]]
    _require(saved_kinds == [kind for kind in selector["saved_data"] if kind in saved_kinds]
             and len(saved_kinds) == len(set(saved_kinds)), "projection_saved_data_selection_conflict")
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
    for name in ("integrity", "preparation"):
        rows = projection[name]
        _require(len(rows) <= 1 and (not rows or selector[name] is not None
            and set(rows[0]["fields"]) == set(selector[name]["fields"])), "projection_" + name + "_selection_conflict")
    _require(len(projection["prepared_database"]) <= 1 and
        (not projection["prepared_database"] or selector["prepared_database"]), "projection_prepared_selection_conflict")
    if operation["database_key"] is not None:
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


def _result_context(result, operation, outcome, occurrences):
    if result is None:
        return None
    result = validate_blast_utility_result(result)
    _require(result["operation"] == operation and result["original_outcome"] == outcome, "result_original_context_conflict")
    known = {row["occurrence_id"]: row for row in occurrences}
    if result["version"] == "blast_database_artifact_set_v1":
        rows = result["inputs"] + result["outputs"]
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
    _require(result is not None and result["version"] == "blast_database_artifact_set_v1",
             "prepared_database_result_required")
    manifest = value["manifest"]
    if manifest is None:
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
    return value


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def project_blast_utility_result(*, source_ref: str, operation: dict, native_outcome: dict,
        result: dict | None, prepared_database: dict | None, occurrences: list,
        selector: dict, failures: list, saved_data: list) -> dict:
    """Copy requested original values, keeping absent selections explicit."""
    _text(source_ref)
    operation = validate_blast_utility_operation(operation)
    outcome = core("NativeOutcome", native_outcome)
    selector = validate_blast_utility_result_selector(selector, operation=operation)
    occurrences = _occurrences(occurrences)
    result = _result_context(result, operation, outcome, occurrences)
    prepared = _prepared_context(prepared_database, result, occurrences)
    _require(type(failures) is list, "result_failure_list_required")
    failures = [core("UtilityFailure", row) for row in failures]
    projection = {name: [] for name in _FACT_SCHEMAS if name != "status"}
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
    projection["database_fields"] = [{"source_ref": source_ref, "database_key": database_key, **deepcopy(row)}
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


__all__ = ["NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA", "FACT_SOURCES", "PROJECTION_FIELDS",
    "IDENTIFIER_NAMESPACES", "STATUS_SCHEMA", "SEQUENCE_SCHEMA", "DATABASE_FIELD_SCHEMA",
    "INTEGRITY_SCHEMA", "PREPARATION_SCHEMA", "PREPARED_DATABASE_SCHEMA", "CHECK_SCHEMA",
    "FAILURE_SCHEMA", "MISSING_SCHEMA", "ARTIFACT_SCHEMA", "SAVED_DATA_SCHEMA",
    "validate_blast_utility_result_selector", "project_blast_utility_result",
    "validate_blast_utility_projection", "blast_utility_fact_sources", "validate_blast_utility_fact_values",
    "projection_identifiers"]
