"""Closed, pure custody and result contracts for selected BLAST utilities.

These records validate supplied facts, not files, deployments or scientific
confidence. Native errors belong in qualified partial records. Caller schema or
relationship errors raise ``ContractError('blast_utility_' + stable_code)``.
No validator reads an artifact, launches work, authenticates a digest or chooses
an additional check. Contract: increment 624/001, with additive clarifications.
"""
from __future__ import annotations

import re

from .domain import ContractError, parse_sequences
from .native_blast_standard_database_contracts import (
    DATABASE_IDENTITY_SCHEMA, PREPARED_DATABASE_SCHEMA,
    _absolute, _array, _copy, _nullable, _object, _relative, _schema,
)


_TEXT = {"type": "string"}
_STR = {"type": "string", "minLength": 1}
_INT = {"type": "integer", "minimum": 0}
_POSITIVE = {"type": "integer", "minimum": 1}
_BOOL = {"type": "boolean"}
_SHA = {"type": "string", "pattern": r"[0-9a-f]{64}"}


def _enum(values):
    return {"enum": values.split()}


def _unique(schema, **kwargs):
    return _array(schema, uniqueItems=True, **kwargs)


FAILURE_CODES = tuple("""input_identity_mismatch dependency_unavailable
database_kind_conflict native_start_failed native_nonzero_exit output_missing
output_inventory_incomplete output_writer_not_closed output_completeness_unestablished
native_outcome_unavailable native_format_unsupported native_row_invalid
native_document_invalid record_association_unresolved sequence_length_conflict
selection_incomplete original_attempt_conflict semantic_validation_unavailable
sequence_symbol_invalid duplicate_native_identity input_population_unavailable
input_sequence_invalid database_metadata_conflict output_family_incomplete
preparation_not_successful native_diagnostic_unrecognized sampled_check_scope
supplied_binding_conflict incompatible_database_format native_integrity_failure""".split())

_OCCURRENCE = _object({
    "occurrence_id": _STR, "direction": _enum("input output"),
    "role": _enum("sequence_input database_file database_metadata extracted_sequences "
                  "database_manifest taxid_map mask_input stdout stderr diagnostics "
                  "preparation_receipt input_manifest offline_configuration"),
    "ordinal": _INT, "artifact_ref": _STR, "sha256": _SHA,
    "size_bytes": _INT,
    "native_format": _enum("fasta blastdbcmd_tabular_v1 blastdb_info_text "
        "blastdb_metadata_json blastdbcheck_text blastdb_binary json text "
        "maskinfo_xml maskinfo_asn1_text unknown"),
    "completeness": _enum("complete partial unknown"),
    "native_path": _nullable(_STR),
})
_OUTCOME = _object({"started": _BOOL, "returncode": _nullable({"type": "integer"}),
    "state": _enum("succeeded failed incomplete unknown"),
    "writer_closed": _BOOL, "inventory_complete": _BOOL})
_FAILURE = _object({"stage": _enum("request input native capture parse association validation projection"),
    "code": {"enum": list(FAILURE_CODES)}, "occurrence_id": _nullable(_STR),
    "record_key": _nullable(_STR), "line_number": _nullable(_POSITIVE),
    "native_returncode": _nullable({"type": "integer"})})
_OBSERVATION = _object({
    "name": _enum("custody syntax identity selection sequence_length sequence_symbols "
                  "database_inventory database_metadata native_integrity native_execution"),
    "status": _enum("pass fail unknown not_applicable"), "subject_refs": _unique(_STR),
    "method": _enum("identity_digest family_inventory native_format_parser explicit_reference_join "
                    "selected_record_match sequence_length_agreement native_full_check "
                    "native_sample_check native_execution_outcome"),
    "reason": _nullable({"enum": list(FAILURE_CODES)}),
    "evidence_occurrence_ids": _unique(_STR),
})
_BINDING = _object({"database_key": _STR,
    "kind": _enum("blast_protein_sequence blast_nucleotide_sequence vdb"),
    "molecule": _enum("dna protein unknown"),
    "identity": _object({"namespace": _TEXT, "value": _TEXT,
                         "version": _nullable(_TEXT), "release": _nullable(_TEXT)}),
    "source_ref": _STR, "native_paths": _unique(_STR, minItems=1),
    "occurrence_ids": _unique(_STR), "inventory_complete": _BOOL})

_FIELD_TYPES = {
    "database_title": (_TEXT, "text"),
    "database_format_version": (_INT, "version"),
    "database_created_at_native": (_TEXT, "text"),
    "database_sequence_count": (_INT, "sequences"),
    "database_residue_count": (_INT, "nt aa symbols"),
    "database_bytes": (_INT, "bytes"),
    "database_file_names": (_array(_TEXT), "paths"),
    "database_volume_names": (_array(_TEXT), "paths"),
}
_FIELD = {"anyOf": [_object({
    "field_name": {"const": name}, "value": _nullable(kind), "unit": _enum(units),
    "value_basis": _enum("native_reported native_reported_exact native_reported_approximate"),
    "native_lexeme": _nullable(_TEXT), "occurrence_id": _STR,
    "line_number": _nullable(_POSITIVE), "json_pointer": _nullable(_TEXT),
    "missing_reason": _nullable(_enum("native_field_absent native_field_invalid ambiguous_population")),
}) for name, (kind, units) in _FIELD_TYPES.items()]}

_RANGE = _object({"start_1based": _POSITIVE, "end_1based": _POSITIVE})
_DETAIL = _object({"input_type": {"const": "fasta"},
    "database_format_version": {"enum": [4, 5]}, "parse_seqids": _BOOL,
    "hash_index": _BOOL, "taxid": _nullable(_INT),
    "taxid_map_occurrence_id": _nullable(_STR), "mask_occurrence_ids": _unique(_STR)})
_PARAMETERS = {
    ("makeblastdb", "create_sequence_database"): _object({
        **_DETAIL["properties"], "output_prefix": _STR, "title": _TEXT,
        "max_file_size": _nullable(_TEXT)}),
    ("blastdbcmd", "extract_sequences"): _object({
        "selectors": _array(_object({"ordinal": _INT, "value": _STR}), minItems=1),
        "output_format": {"const": "blastdbcmd_tabular_v1"},
        "range": _nullable(_RANGE), "strand": _enum("plus minus"),
        "get_dups": _BOOL, "target_only": _BOOL}),
    ("blastdbcmd", "info"): _object({"exact_length": _BOOL}),
    ("blastdbcmd", "metadata"): _object({}),
    ("blastdbcheck", "integrity"): _object({"full": _BOOL,
        "stride": _nullable(_POSITIVE), "random_count": _nullable(_INT),
        "ends_count": _nullable(_INT), "no_isam": _BOOL,
        "legacy_file_checks": _BOOL, "require_taxids": _BOOL, "cdd_delta": _BOOL}),
}
_OPERATION = {"anyOf": [_object({
    "version": {"const": "blast_utility_operation_v1"},
    "program": {"const": program}, "mode": {"const": mode},
    "input_occurrence_ids": _unique(_STR), "database_key": _nullable(_STR),
    "molecule": _enum("dna protein"), "parameters": parameters,
}) for (program, mode), parameters in _PARAMETERS.items()]}
_DIAGNOSTICS = {"checks": _array(_OBSERVATION), "failures": _array(_FAILURE)}
_RESULT_BASE = {"operation": _OPERATION, "database_binding": _BINDING,
                "original_outcome": _OUTCOME, **_DIAGNOSTICS}
_EXTRACTION_RECORD = _object({
    "record_key": _STR, "native_row_ordinal": _INT, "line_number": _POSITIVE,
    "matched_selector_ordinals": _unique(_INT), "association": _enum("exact explicit unresolved"),
    "native_oid": _nullable(_INT), "native_identifier": _TEXT,
    "native_accession": _nullable(_TEXT), "native_reported_length": _nullable(_INT),
    "native_length_basis": _enum("full_sequence returned_sequence unknown"),
    "original_sequence": _TEXT, "normalized_sequence": _TEXT,
    "returned_symbol_count": _nullable(_INT), "molecule": _enum("dna protein"),
    "requested_range": _nullable(_RANGE),
    "effective_range": _nullable(_object({"start_0based": _INT, "end_exclusive": _INT,
                                          "strand": _enum("plus minus")})),
    "completeness": _enum("complete partial unknown"), **_DIAGNOSTICS,
})
_EXTRACTION = _object({"version": {"const": "blast_sequence_extraction_v1"},
    **_RESULT_BASE, "output_occurrence": _OCCURRENCE,
    "records": _array(_EXTRACTION_RECORD), "missing_selector_ordinals": _unique(_INT),
    "unexpected_record_keys": _unique(_STR),
    "population_completeness": _enum("complete_selection partial_selection unknown")})
_INSPECTION = _object({"version": {"const": "blast_database_inspection_v1"},
    **_RESULT_BASE, "output_occurrence": _OCCURRENCE, "native_fields": _array(_FIELD),
    "completeness": _enum("complete partial unknown")})
_INTEGRITY = _object({"version": {"const": "blast_database_integrity_v1"},
    **_RESULT_BASE, "stdout_occurrence": _OCCURRENCE, "stderr_occurrence": _OCCURRENCE,
    "scope": _enum("all_sequences selected_sample unknown"),
    "observed_checked_count": _nullable(_INT), "observed_population_count": _nullable(_INT),
    "observed_sampled_oids": _nullable(_unique(_INT)), "realized_seed": _nullable({"type": "integer"}),
    "diagnostics": _array(_object({"occurrence_id": _STR, "line_number": _POSITIVE,
        "category": _enum("check_pass check_failure execution_failure unknown"),
        "native_oid": _nullable(_INT)}))})
_ARTIFACT_SET = _object({"version": {"const": "blast_database_artifact_set_v1"},
    "kind": {"const": "sequence_database"}, "operation": _OPERATION,
    "original_outcome": _OUTCOME, "database_key": _STR, "identity": DATABASE_IDENTITY_SCHEMA,
    "software": _object({"name": _TEXT, "version": _nullable(_TEXT),
                          "executable_sha256": _nullable(_SHA)}),
    "argv": _array(_TEXT), "native_paths": _unique(_STR, minItems=1),
    "inputs": _array(_OCCURRENCE), "outputs": _array(_OCCURRENCE),
    "dependencies": _array(_object({"role": _enum("taxid_map mask_input"), "occurrence_id": _STR})),
    "inventory_complete": _BOOL, "native_metadata": _array(_FIELD), "detail": _DETAIL,
    "compatibility": _enum("validated unverified incompatible"), **_DIAGNOSTICS})
_PROJECTION = _object({"status": _enum("available unavailable"),
    "manifest": _nullable(PREPARED_DATABASE_SCHEMA), "failures": _array(_FAILURE)})

SCHEMAS = {"ArtifactOccurrence": _OCCURRENCE, "NativeOutcome": _OUTCOME,
    "UtilityFailure": _FAILURE, "ValidationObservation": _OBSERVATION,
    "DatabaseBinding": _BINDING, "NativeField": _FIELD, "Operation": _OPERATION,
    "SequenceExtraction": _EXTRACTION, "DatabaseInspection": _INSPECTION,
    "DatabaseIntegrity": _INTEGRITY, "DatabaseArtifactSet": _ARTIFACT_SET,
    "PreparedDatabaseProjection": _PROJECTION}


def _require(condition, code):
    if not condition:
        raise ContractError("blast_utility_" + code)


def _pointer(value):
    _require(value == "" or value.startswith("/"), "native_pointer_invalid")
    _require(re.search(r"~(?![01])", value) is None, "native_pointer_invalid")


def _occurrence(value):
    if value["native_path"] is not None:
        _absolute(value["native_path"])
    if value["role"] in {"sequence_input", "taxid_map", "mask_input"}:
        _require(value["direction"] == "input", "occurrence_direction")
    if value["role"] in {"stdout", "stderr", "extracted_sequences", "diagnostics"}:
        _require(value["direction"] == "output", "occurrence_direction")


def _outcome(value):
    _require(value["started"] or value["returncode"] is None, "unstarted_returncode")
    _require(not value["inventory_complete"] or value["writer_closed"], "open_writer_inventory")
    if value["state"] == "succeeded":
        _require(value["started"] and value["returncode"] == 0 and value["writer_closed"], "native_outcome")
    elif value["state"] == "failed":
        _require(value["returncode"] != 0, "native_outcome")
    elif value["state"] == "incomplete":
        _require(not (value["writer_closed"] and value["inventory_complete"]), "native_outcome")


def _failure(value):
    if value["line_number"] is not None:
        _require(value["occurrence_id"] is not None, "failure_locator")
    if value["code"] == "native_nonzero_exit":
        _require(value["native_returncode"] is not None and value["native_returncode"] != 0,
                 "failure_returncode")
    if value["code"] == "native_start_failed":
        _require(value["native_returncode"] is None, "failure_returncode")


def _observation(value):
    if value["status"] in {"fail", "unknown"}:
        _require(value["reason"] is not None, "observation_reason")
    if value["name"] == "native_integrity":
        _require(value["method"] in {"native_full_check", "native_sample_check"}, "integrity_method")
    if value["method"] in {"native_full_check", "native_sample_check"}:
        _require(value["name"] == "native_integrity", "integrity_method")
    if value["name"] == "native_execution" or value["method"] == "native_execution_outcome":
        _require(value["name"] == "native_execution" and value["method"] == "native_execution_outcome",
                 "execution_method")


def _binding(value):
    for path in value["native_paths"]:
        _absolute(path)
    expected = {"blast_protein_sequence": "protein", "blast_nucleotide_sequence": "dna"}
    if value["kind"] in expected:
        _require(value["molecule"] == expected[value["kind"]], "database_kind_molecule")


def _field(value):
    _require((value["value"] is None) == (value["missing_reason"] is not None), "native_field_missing_reason")
    _require(value["line_number"] is not None or value["json_pointer"] is not None, "native_field_locator")
    if value["json_pointer"] is not None:
        _pointer(value["json_pointer"])


def _range(value):
    if value is not None:
        _require(value["start_1based"] <= value["end_1based"], "range_order")


def _operation(value):
    p, mode = value["parameters"], value["mode"]
    if mode == "create_sequence_database":
        _require(value["database_key"] is None, "preparation_database_key")
        _relative(p["output_prefix"])
        taxmap, masks = p["taxid_map_occurrence_id"], p["mask_occurrence_ids"]
        _require(p["taxid"] is None or taxmap is None, "taxid_map_exclusive")
        _require(taxmap is None or p["parse_seqids"], "taxid_map_parse_seqids")
        _require(taxmap not in masks, "dependency_role_conflict")
        dependencies = set(masks) | ({taxmap} if taxmap is not None else set())
        inputs = set(value["input_occurrence_ids"])
        _require(dependencies <= inputs and len(inputs - dependencies) == 1, "preparation_input_population")
    else:
        _require(value["database_key"] is not None, "selected_database_required")
    if mode == "extract_sequences":
        _require([s["ordinal"] for s in p["selectors"]] == list(range(len(p["selectors"]))), "selector_ordinals")
        for selector in p["selectors"]:
            raw = selector["value"]
            _require(raw.lower() != "all" and "," not in raw and
                     not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw), "selector_value")
        _range(p["range"])
        _require(value["molecule"] != "protein" or p["strand"] == "plus", "protein_strand")
        _require(not (p["get_dups"] and p["target_only"]), "extraction_option_conflict")
    if mode == "integrity" and p["full"]:
        _require(all(p[k] is None for k in ("stride", "random_count", "ends_count")), "integrity_sampling_conflict")


def _occurrences(rows):
    by_id = {}
    for row in rows:
        _occurrence(row)
        key = row["occurrence_id"]
        _require(key not in by_id, "duplicate_occurrence_identity")
        by_id[key] = row
    return by_id


def _diagnostics(value, *, occurrences, subjects, record_keys=(), malformed_prefix=None, outcome=None):
    for check in value["checks"]:
        _observation(check)
        _require(set(check["subject_refs"]) <= subjects, "observation_subject_reference")
        _require(set(check["evidence_occurrence_ids"]) <= occurrences, "observation_evidence_reference")
        if outcome is not None and check["name"] == "native_execution" and check["status"] == "pass":
            _require(outcome["state"] == "succeeded", "execution_observation_conflict")
    for failure in value["failures"]:
        _failure(failure)
        _require(failure["occurrence_id"] is None or failure["occurrence_id"] in occurrences,
                 "failure_occurrence_reference")
        key = failure["record_key"]
        malformed = (malformed_prefix is not None and type(key) is str and
            re.fullmatch(re.escape(malformed_prefix) + r"[0-9]+", key) is not None and
            failure["code"] in {"native_row_invalid", "native_document_invalid"} and
            failure["line_number"] is not None)
        _require(key is None or key in record_keys or malformed, "failure_record_reference")
        if outcome is not None and failure["native_returncode"] is not None:
            _require(failure["native_returncode"] == outcome["returncode"], "failure_outcome_conflict")


def _result_context(value, *, program, modes, outputs):
    op, binding, outcome = value["operation"], value["database_binding"], value["original_outcome"]
    _operation(op); _binding(binding); _outcome(outcome)
    _require(op["program"] == program and op["mode"] in modes, "result_operation")
    _require(op["database_key"] == binding["database_key"], "result_database_key")
    _require(binding["molecule"] in {op["molecule"], "unknown"}, "result_database_molecule")
    rows = _occurrences(outputs)
    known = set(binding["occurrence_ids"])
    _require(set(op["input_occurrence_ids"]) <= known, "result_input_reference")
    _require(not (rows.keys() & known), "duplicate_occurrence_identity")
    known.update(rows)
    for output in outputs:
        _require(output["direction"] == "output", "result_output_direction")
    return known, known | {binding["database_key"]}


def _extraction(value):
    out, op = value["output_occurrence"], value["operation"]
    known, subjects = _result_context(value, program="blastdbcmd", modes={"extract_sequences"}, outputs=[out])
    _require(out["role"] in {"extracted_sequences", "stdout"} and
             out["native_format"] == "blastdbcmd_tabular_v1", "extraction_output")
    selectors = op["parameters"]["selectors"]
    ordinals = set(range(len(selectors)))
    subjects.update(s["value"] for s in selectors)
    rows = value["records"]
    keys = {r["record_key"] for r in rows}
    _require(len(keys) == len(rows), "duplicate_record_identity")
    _require(len({r["native_row_ordinal"] for r in rows}) == len(rows), "duplicate_native_row")
    subjects.update(keys)
    matched = set()
    for row in rows:
        _require(row["record_key"] == out["occurrence_id"] + "#/records/" + str(row["native_row_ordinal"]), "record_identity")
        selected = set(row["matched_selector_ordinals"])
        _require(selected <= ordinals, "selector_reference")
        exact = {s["ordinal"] for s in selectors if s["value"] in
                 {row["native_identifier"], row["native_accession"]}}
        if row["association"] == "exact":
            _require(bool(selected) and selected == exact, "exact_selector_association")
        elif row["association"] == "explicit":
            _require(bool(selected) and exact <= selected, "supplied_binding_conflict")
        else:
            _require(not selected and not exact, "unresolved_selector_association")
        matched.update(selected)
        _require(row["molecule"] == op["molecule"], "record_molecule")
        _require(row["requested_range"] == op["parameters"]["range"], "record_requested_range")
        _require(row["normalized_sequence"] == row["original_sequence"].upper(), "sequence_normalization")
        _diagnostics(row, occurrences=known, subjects=subjects, record_keys=keys, outcome=value["original_outcome"])
        count, native_length = row["returned_symbol_count"], row["native_reported_length"]
        codes = {f["code"] for f in row["failures"]}
        if count is not None:
            _require(count == len(row["normalized_sequence"]) and
                     not any(c.isspace() for c in row["original_sequence"]), "returned_sequence_count")
            try:
                parsed = parse_sequences(row["original_sequence"], format="raw", molecule=row["molecule"])[0]
            except ContractError:
                _require(False, "returned_sequence_symbols")
            _require("unexpected_symbol_for_declared_molecule" not in parsed.issues, "returned_sequence_symbols")
            compare_native = row["native_length_basis"] == "returned_sequence" or (
                row["native_length_basis"] == "full_sequence" and row["requested_range"] is None)
            _require(not compare_native or native_length is None or native_length == count, "native_length_unqualified")
            _require(not codes & {"sequence_symbol_invalid", "sequence_length_conflict"}, "qualified_sequence_count")
        else:
            _require(bool(codes), "missing_sequence_count_reason")
        effective = row["effective_range"]
        if effective is not None:
            _require(count is not None and effective["end_exclusive"] >= effective["start_0based"] and
                     effective["end_exclusive"] - effective["start_0based"] == count and
                     effective["strand"] == op["parameters"]["strand"], "effective_range")
            _require(row["native_length_basis"] != "full_sequence" or native_length is None or
                     effective["end_exclusive"] <= native_length, "effective_range_population")
            requested = row["requested_range"]
            expected_start = 0 if requested is None else requested["start_1based"] - 1
            _require(effective["start_0based"] == expected_start, "effective_range_origin")
            if row["native_length_basis"] == "full_sequence" and native_length is not None:
                expected_end = native_length if requested is None else min(requested["end_1based"], native_length)
                _require(effective["end_exclusive"] == expected_end, "effective_range_end")
            elif requested is not None:
                _require(effective["end_exclusive"] <= requested["end_1based"], "effective_range_end")
        if row["completeness"] == "complete":
            _require(count is not None, "complete_record_count")
    _require(set(value["missing_selector_ordinals"]) == ordinals - matched, "missing_selector_population")
    unexpected = {r["record_key"] for r in rows if not r["matched_selector_ordinals"]}
    _require(set(value["unexpected_record_keys"]) == unexpected, "unexpected_record_population")
    if value["population_completeness"] == "complete_selection":
        _require(not value["missing_selector_ordinals"] and not unexpected and
                 all(r["completeness"] == "complete" for r in rows) and
                 out["completeness"] == "complete" and value["original_outcome"]["state"] == "succeeded",
                 "complete_selection_unestablished")
        _require(not any(f["stage"] in {"parse", "association"} for f in value["failures"]),
                 "complete_selection_failures")
    _diagnostics(value, occurrences=known, subjects=subjects, record_keys=keys,
        malformed_prefix=out["occurrence_id"] + "#/records/", outcome=value["original_outcome"])


def _fields(rows, known):
    for row in rows:
        _field(row)
        _require(row["occurrence_id"] in known, "native_field_occurrence_reference")


def _metadata_relationships(value, rows):
    """Qualify retained conflicting facts without calculating or replacing them."""
    expected_unit = "nt" if value["operation"]["molecule"] == "dna" else "aa"
    seen, conflict = {}, False
    for row in rows:
        if row["value"] is None:
            continue
        name = row["field_name"]
        if name == "database_residue_count" and row["unit"] not in {expected_unit, "symbols"}:
            conflict = True
        if (name in {"database_sequence_count", "database_residue_count", "database_format_version"}
                and row["value_basis"] != "native_reported_approximate"):
            fact = row["value"], row["unit"]
            if name in seen and seen[name] != fact:
                conflict = True
            seen[name] = fact
        if name == "database_format_version" and value["operation"]["mode"] == "create_sequence_database":
            if row["value"] != value["operation"]["parameters"]["database_format_version"]:
                conflict = True
    if conflict:
        _require(any(f["code"] in {"database_metadata_conflict", "database_kind_conflict", "incompatible_database_format"}
                     for f in value["failures"]), "native_metadata_conflict_unqualified")


def _inspection(value):
    out = value["output_occurrence"]
    known, subjects = _result_context(value, program="blastdbcmd", modes={"info", "metadata"}, outputs=[out])
    fmt = "blastdb_info_text" if value["operation"]["mode"] == "info" else "blastdb_metadata_json"
    _require(out["role"] in {"database_metadata", "stdout"} and out["native_format"] == fmt, "inspection_output")
    _fields(value["native_fields"], {out["occurrence_id"]})
    _metadata_relationships(value, value["native_fields"])
    if value["completeness"] == "complete":
        _require(out["completeness"] == "complete", "inspection_capture_completeness")
    _diagnostics(value, occurrences=known, subjects=subjects, outcome=value["original_outcome"])


def _integrity(value):
    streams = [value["stdout_occurrence"], value["stderr_occurrence"]]
    known, subjects = _result_context(value, program="blastdbcheck", modes={"integrity"}, outputs=streams)
    for row, role in zip(streams, ("stdout", "stderr")):
        _require(row["role"] == role and row["native_format"] in {"blastdbcheck_text", "text"}, "integrity_stream")
    stream_ids = {r["occurrence_id"] for r in streams}
    for diagnostic in value["diagnostics"]:
        _require(diagnostic["occurrence_id"] in stream_ids, "integrity_diagnostic_reference")
    categories = {d["category"] for d in value["diagnostics"]}
    for check in value["checks"]:
        if check["name"] != "native_integrity" or check["status"] not in {"pass", "fail"}:
            continue
        required = "check_pass" if check["status"] == "pass" else "check_failure"
        _require(required in categories and bool(check["evidence_occurrence_ids"]) and
                 set(check["evidence_occurrence_ids"]) <= stream_ids, "integrity_observation_evidence")
        if check["status"] == "pass":
            _require(value["original_outcome"]["state"] == "succeeded", "integrity_execution_conflict")
        if check["method"] == "native_full_check" and check["status"] == "pass":
            _require(value["scope"] == "all_sequences", "integrity_full_scope")
    checked, population = value["observed_checked_count"], value["observed_population_count"]
    if checked is not None and population is not None:
        _require(checked <= population, "integrity_count_population")
    if value["observed_sampled_oids"] is not None:
        _require(value["scope"] == "selected_sample", "integrity_sample_scope")
        if checked is not None:
            _require(len(value["observed_sampled_oids"]) <= checked, "integrity_sample_count")
    if value["scope"] == "all_sequences":
        _require(bool(value["diagnostics"]) and any(c["name"] == "native_integrity" and
            c["method"] == "native_full_check" and c["status"] in {"pass", "fail"} and
            c["evidence_occurrence_ids"] for c in value["checks"]), "integrity_full_evidence")
        if checked is not None and population is not None:
            _require(checked == population, "integrity_full_population")
    if value["scope"] == "selected_sample":
        _require(not any(c["name"] == "native_integrity" and c["method"] == "native_full_check" and
                         c["status"] == "pass" for c in value["checks"]), "sampled_full_integrity_claim")
    _diagnostics(value, occurrences=known, subjects=subjects, outcome=value["original_outcome"])


def _artifact_set(value):
    op, outcome = value["operation"], value["original_outcome"]
    _operation(op); _outcome(outcome)
    _require(op["program"] == "makeblastdb" and op["mode"] == "create_sequence_database", "artifact_set_operation")
    _pointer(value["identity"]["source"]["pointer"])
    for path in value["native_paths"]:
        _absolute(path)
    all_occurrences = _occurrences(value["inputs"] + value["outputs"])
    inputs = {r["occurrence_id"]: r for r in value["inputs"]}
    _require(set(inputs) == set(op["input_occurrence_ids"]), "artifact_set_inputs")
    _require(all(r["direction"] == "input" for r in value["inputs"]) and
             all(r["direction"] == "output" for r in value["outputs"]), "artifact_set_direction")
    _require(sum(r["role"] == "sequence_input" for r in value["inputs"]) == 1 and
             all(r["role"] in {"sequence_input", "taxid_map", "mask_input"} for r in value["inputs"]),
             "artifact_set_input_roles")
    _require(all(r["native_format"] == "fasta" for r in value["inputs"] if r["role"] == "sequence_input"),
             "artifact_set_input_format")
    expected_detail = {key: op["parameters"][key] for key in value["detail"]}
    _require(value["detail"] == expected_detail, "artifact_set_detail")
    dependencies = [(r["role"], r["occurrence_id"]) for r in value["dependencies"]]
    expected = [("mask_input", k) for k in value["detail"]["mask_occurrence_ids"]]
    if value["detail"]["taxid_map_occurrence_id"] is not None:
        expected.append(("taxid_map", value["detail"]["taxid_map_occurrence_id"]))
    _require(len(dependencies) == len(set(dependencies)) and set(dependencies) == set(expected),
             "artifact_set_dependency_population")
    for role, key in dependencies:
        _require(key in inputs and inputs[key]["role"] == role, "artifact_set_dependency_reference")
    if value["inventory_complete"]:
        _require(outcome["writer_closed"] and outcome["inventory_complete"] and
                 all(r["completeness"] == "complete" and r["native_path"] is not None for r in value["outputs"]),
                 "artifact_set_inventory_completeness")
    _fields(value["native_metadata"], set(all_occurrences))
    _metadata_relationships(value, value["native_metadata"])
    _diagnostics(value, occurrences=set(all_occurrences), subjects=set(all_occurrences) | {value["database_key"]},
                 outcome=outcome)
    if value["compatibility"] == "validated":
        _require(value["inventory_complete"] and outcome["state"] == "succeeded" and
            any(c["name"] == "native_integrity" and c["method"] == "native_full_check" and
                c["status"] == "pass" and any(
                    all_occurrences[key]["direction"] == "output" and
                    all_occurrences[key]["role"] in {"stdout", "stderr", "diagnostics"} and
                    all_occurrences[key]["native_format"] == "blastdbcheck_text"
                    for key in c["evidence_occurrence_ids"])
                for c in value["checks"]),
            "database_compatibility_evidence")


def _projection(value):
    _require((value["status"] == "available") == (value["manifest"] is not None), "projection_availability")
    for failure in value["failures"]:
        _failure(failure)
    if value["manifest"] is not None:
        # Public wrapper preserves the established standard-manifest validator.
        from .native_blast_standard_database_contracts import validate_standard_prepared_blast_database_manifest
        validate_standard_prepared_blast_database_manifest(value["manifest"])
        _require(not value["failures"], "available_projection_failures")
    else:
        _require(bool(value["failures"]), "unavailable_projection_reason")


_VALIDATORS = {"ArtifactOccurrence": _occurrence, "NativeOutcome": _outcome,
    "UtilityFailure": _failure, "ValidationObservation": _observation,
    "DatabaseBinding": _binding, "NativeField": _field, "Operation": _operation,
    "SequenceExtraction": _extraction, "DatabaseInspection": _inspection,
    "DatabaseIntegrity": _integrity, "DatabaseArtifactSet": _artifact_set,
    "PreparedDatabaseProjection": _projection}
_VERSIONS = {schema["properties"]["version"]["const"]: name for name, schema in SCHEMAS.items()
             if "version" in schema.get("properties", {})}


def validate_blast_utility_record(kind: str, value: dict) -> dict:
    """Validate closed shape and relationships, returning a detached JSON copy."""
    _require(type(kind) is str and kind in SCHEMAS, "unknown_record_kind")
    try:
        copied = _copy(value)
        _schema(copied, SCHEMAS[kind])
        _VALIDATORS[kind](copied)
    except ContractError:
        raise
    except RecursionError as exc:
        raise ContractError("blast_utility_finite_json_required") from exc
    except ValueError as exc:
        message = str(exc)
        prefix = "native_blast_standard_database_"
        code = message.removeprefix(prefix) if message.startswith(prefix) else "record_invalid"
        if code.startswith("schema:"):
            code = "schema_invalid"
        raise ContractError("blast_utility_" + code) from exc
    return copied


def validate_blast_utility_operation(value: dict) -> dict:
    """Validate a selected request, without guessing its effective defaults."""
    return validate_blast_utility_record("Operation", value)


def validate_blast_utility_result(value: dict) -> dict:
    """Dispatch only the four exact, versioned native-result payloads."""
    _require(type(value) is dict and type(value.get("version")) is str and
             value["version"] in _VERSIONS, "unknown_result_version")
    return validate_blast_utility_record(_VERSIONS[value["version"]], value)


__all__ = ["SCHEMAS", "FAILURE_CODES", "validate_blast_utility_record",
           "validate_blast_utility_operation", "validate_blast_utility_result"]
