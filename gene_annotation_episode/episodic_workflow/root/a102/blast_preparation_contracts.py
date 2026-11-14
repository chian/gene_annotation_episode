"""Closed preparation ports (646), with no I/O, scoring or inferred defaults.

Common custody and diagnostic primitives are supplied to schema construction.
Validation imports their authority lazily, avoiding a second failure policy or
a circular initialization dependency.
"""
from __future__ import annotations

import re

from .domain import ContractError
from .native_blast_standard_database_contracts import (
    _array, _copy, _nullable, _object, _relative, _schema,
)
from .native_blast_database_contracts import DATABASE_IDENTITY_SCHEMA

_TEXT = {"type": "string"}
_STR = {"type": "string", "minLength": 1}
_INT = {"type": "integer", "minimum": 0}
_POS = {"type": "integer", "minimum": 1}
_BOOL = {"type": "boolean"}
_NUMBER = {"type": "number"}
_SHA = {"type": "string", "pattern": r"[0-9a-f]{64}"}


def _enum(text):
    return {"enum": text.split()}


def _unique(schema):
    return _array(schema, uniqueItems=True)


DATABASE_ENTRY_SCHEMA = _object({"ordinal": _INT, "database_key": _STR,
    "native_path_index": _INT, "native_reference": _STR, "line_number": _nullable(_POS)})
PROFILE_ENTRY_SCHEMA = _object({"ordinal": _INT, "input_occurrence_id": _STR,
    "native_reference": _STR, "line_number": _POS, "token_ordinal": _INT})
_LIST = {"anyOf": [_object({"source": {"const": "inline"},
    "entries": _array(DATABASE_ENTRY_SCHEMA, minItems=1)}),
    _object({"source": {"const": "file"}, "input_occurrence_id": _STR,
             "entries": _array(DATABASE_ENTRY_SCHEMA, minItems=1)})]}
RESTRICTION_SCHEMA = {"anyOf": [
    _object({"kind": {"const": kind}, "occurrence_id": _STR, "format": {"enum": formats}})
    for kind, formats in (("gi_list", ["text", "gi_list_binary"]),
                         ("seqid_list", ["text", "seqid_list_binary"]),
                         ("taxid_list", ["text"]))] + [
    _object({"kind": {"const": "oid_masks"}, "value": _INT})]}
OPERATION_PARAMETERS = {
    ("blastdb_aliastool", "convert_gi_list"): _object({"input_occurrence_id": _STR, "output_path": _STR}),
    ("blastdb_aliastool", "convert_seqid_list"): _object({"input_occurrence_id": _STR,
        "output_path": _STR, "title": _TEXT, "seqid_database_key": _nullable(_STR)}),
    ("blastdb_aliastool", "inspect_seqid_list"): _object({"input_occurrence_id": _STR}),
    ("blastdb_aliastool", "create_subset_alias"): _object({"output_prefix": _STR,
        "title": _TEXT, "source_database_key": _STR, "restriction": RESTRICTION_SCHEMA}),
    ("blastdb_aliastool", "aggregate_databases"): _object({"output_prefix": _STR,
        "title": _TEXT, "classic_list": _nullable(_LIST), "vdb_list": _nullable(_LIST)}),
    ("blastdb_aliastool", "aggregate_volumes"): _object({"output_prefix": _STR,
        "title": _TEXT, "source_database_key": _STR, "num_volumes": _POS,
        "volume_entries": _array(DATABASE_ENTRY_SCHEMA, minItems=1)}),
    ("makembindex", "create_megablast_index"): _object({
        "input_format": _enum("fasta blastdb"), "input_occurrence_id": _nullable(_STR),
        "source_database_key": _nullable(_STR), "old_style_index": _BOOL, "legacy": _BOOL,
        "output_prefix": _nullable(_STR), "idmap": _BOOL, "db_mask": _nullable(_STR),
        "nmer": _nullable({"type": "integer", "minimum": 8, "maximum": 15}),
        "ws_hint": _nullable(_POS), "stride": _nullable(_POS), "volume_size_mb": _nullable(_POS),
        "verbosity": _enum("quiet normal verbose"), "statistics_path": _nullable(_STR)}),
    ("makembindex", "show_filters"): _object({"source_database_key": _STR}),
    ("makeprofiledb", "create_profile_database"): _object({
        "profile_list_occurrence_id": _STR, "profile_entries": _array(PROFILE_ENTRY_SCHEMA, minItems=1),
        "profile_type": _enum("rps delta cobalt"), "input_format": _enum("pssm_asn1_text pssm_asn1_binary"),
        "output_prefix": _STR, "title": _TEXT, "database_format_version": {"enum": [4, 5]},
        "max_smp_per_volume": _POS, "create_sequence_indexes": _BOOL,
        "word_score_threshold": _NUMBER, "force_threshold": _BOOL,
        "gap_open": _nullable({"type": "integer"}), "gap_extend": _nullable({"type": "integer"}),
        "scale": _NUMBER, "matrix": _enum("BLOSUM45 BLOSUM50 BLOSUM62 BLOSUM80 BLOSUM90 PAM250 PAM30 PAM70"),
        "observations_threshold": _NUMBER, "exclude_invalid": _BOOL,
        "taxid": _nullable(_INT), "taxid_map_occurrence_id": _nullable(_STR)}),
}
OPERATION_SCHEMA = {"anyOf": [_object({
    "version": {"const": "blast_utility_operation_v2"}, "program": {"const": program},
    "mode": {"const": mode}, "input_occurrence_ids": _unique(_STR),
    "database_key": _nullable(_STR), "molecule": _enum("dna protein unknown"), "parameters": parameters,
}) for (program, mode), parameters in OPERATION_PARAMETERS.items()]}
_PARAMETER_TYPES = {**{k: {"type": "integer"} for k in ("nmer", "ws_hint", "stride", "gap_open", "gap_extend")},
    "scale": _NUMBER, "word_score_threshold": _NUMBER, "matrix": _STR,
    "output_prefix": _STR, "legacy": _BOOL, "old_style_index": _BOOL}
PARAMETER_OBSERVATION_SCHEMA = {"anyOf": [_object({
    "parameter": {"const": name}, "scope_key": _STR, "value": _nullable(kind),
    "effect": _enum("effective ignored unknown"), "occurrence_id": _nullable(_STR),
    "line_number": _nullable(_POS), "native_lexeme": _nullable(_TEXT),
    "missing_reason": _nullable(_enum("native_field_absent native_field_invalid ambiguous_population")),
}) for name, kind in _PARAMETER_TYPES.items()]}
_IDENTITY = _object({"sha256": _SHA, "size_bytes": _INT})
_TARGET = {"anyOf": [_object({"kind": {"const": "input"}, "input_key": _STR}),
    _object({"kind": {"const": "database"}, "database_key": _STR, "native_path_index": _INT})]}
MATERIALIZATION_ENTRY_SCHEMA = _object({"ordinal": _INT, "line_number": _POS,
    "token_ordinal": _INT, "original_token": _STR, "target": _TARGET, "realized_token": _STR})
MATERIALIZATION_RECEIPT_SCHEMA = {"anyOf": [
    _object({"kind": {"const": "database_copy"}, "database_key": _STR,
        "source_path": _STR, "relative_path": _STR, "expected": _IDENTITY,
        "staged": _nullable(_IDENTITY), "final": _nullable(_IDENTITY)}),
    _object({"kind": {"const": "input_copy"}, "input_key": _STR,
        "source_path": _STR, "relative_path": _STR, "expected": _IDENTITY,
        "staged": _nullable(_IDENTITY), "final": _nullable(_IDENTITY)}),
    _object({"kind": {"const": "list_rewrite"}, "input_key": _STR,
        "original_sha256": _SHA, "relative_path": _STR, "sha256": _SHA, "size_bytes": _INT,
        "grammar": _enum("blast_database_lines profile_whitespace_tokens"),
        "entries": _array(MATERIALIZATION_ENTRY_SCHEMA, minItems=1)}),
]}
DATABASE_DEPENDENCY_SCHEMA = _object({"role": {"const": "database"}, "ordinal": _INT,
    "database_key": _STR, "native_path_index": _INT, "native_reference": _STR,
    "source": _enum("db dblist dblist_file vdblist vdblist_file num_volumes"),
    "list_occurrence_id": _nullable(_STR), "list_entry_ordinal": _nullable(_INT)})
DEPENDENCY_SCHEMA = {"anyOf": [DATABASE_DEPENDENCY_SCHEMA, _object({"role": {"const": "input_file"},
    "occurrence_id": _STR, "purpose": _enum("gi_restriction seqid_restriction taxid_restriction "
        "profile_list profile_input database_list taxid_map")})]}


def build_preparation_schemas(common):
    """Build new closed branches using the one shared primitive authority."""
    field, failure, check = (common[k] for k in ("NativeField", "UtilityFailure", "ValidationObservation"))
    diagnostics = {"checks": _array(check), "failures": _array(failure)}
    rows = {
        "list": _object({"ordinal": _INT, "line_number": _POS, "token_ordinal": _INT,
            "original_token": _STR, "start_byte": _INT, "end_byte": _INT}),
        "alias": _object({"row_ordinal": _INT, "line_number": _POS, "native_key": _STR,
            "value_lexeme": _TEXT, "tokens": _array(_object({"ordinal": _INT, "value": _TEXT, "native_lexeme": _TEXT}))}),
        "seqid_info": {},
        "aliastool_diagnostics": _object({"line_number": _POS,
            "category": _enum("converted_gi_count created_alias_sequence_count native_error unknown"),
            "native_lexeme": _TEXT, "native_count": _nullable(_INT)}),
        "index_diagnostics": _object({"line_number": _POS,
            "category": _enum("parameter_adjusted parameter_ignored member_created empty_member_removed native_error unknown"),
            "native_lexeme": _TEXT, "parameter_observation": _nullable(PARAMETER_OBSERVATION_SCHEMA),
            "native_output_reference": _nullable(_STR)}),
        "profile_aux": _object({"native_profile_ordinal": _INT, "sequence_length": _INT,
            "karlin_k": _NUMBER, "length_line_number": _POS, "k_line_number": _POS}),
        "profile_diagnostics": _object({"line_number": _POS,
            "category": _enum("excluded_low_observations excluded_invalid missing_frequency_ratios "
                "missing_weighted_frequencies missing_independent_observations missing_core_blocks "
                "profile_size_conflict parameter_conflict native_error unknown"),
            "native_reference": _nullable(_STR), "native_lexeme": _TEXT}),
    }
    documents = {kind: _object({"version": {"const": "blast_preparation_document_v1"},
        "kind": {"const": kind}, "occurrence_id": _STR,
        "native_fields": _array(field, **({} if kind in {"alias", "seqid_info", "aliastool_diagnostics"} else {"maxItems": 0})),
        "rows": _array(row, **({"maxItems": 0} if kind == "seqid_info" else {})), **diagnostics,
        **({"parameter_observations": _array(PARAMETER_OBSERVATION_SCHEMA)} if kind == "profile_aux" else {}),
    }) for kind, row in rows.items()}
    identifier_detail = _object({"list_kind": _enum("gi seqid"), "input_occurrence_id": _STR,
        "output_occurrence_ids": _unique(_STR), "database_key": _nullable(_STR), "native_fields": _array(field)})
    alias_base = {"database_dependencies": _array(DATABASE_DEPENDENCY_SCHEMA),
                  "alias_documents": _array(documents["alias"])}
    alias_detail = {"anyOf": [_object({"alias_kind": {"const": "subset"},
        "restriction": RESTRICTION_SCHEMA, **alias_base}),
        _object({"alias_kind": _enum("aggregate volumes"), **alias_base})]}
    index_detail = _object({"input_format": _enum("fasta blastdb"),
        "source_database_key": _nullable(_STR), "input_occurrence_id": _nullable(_STR),
        "old_style_index": _BOOL, "legacy": _BOOL,
        "index_members": _array(_object({"ordinal": _INT, "occurrence_id": _STR,
            "database_key": _nullable(_STR), "source_volume_reference": _nullable(_STR),
            "source_volume_occurrence_ids": _unique(_STR), "association": _enum("explicit unresolved")})),
        "parameter_observations": _array(PARAMETER_OBSERVATION_SCHEMA)})
    profile_detail = _object({"profile_type": _enum("rps delta cobalt"),
        "profile_list_occurrence_id": _STR, "profile_entries": _array(PROFILE_ENTRY_SCHEMA),
        "profiles": _array(_object({"entry_ordinal": _INT, "input_occurrence_id": _STR,
            "disposition": _enum("included excluded failed unknown"),
            "reason": _nullable(_enum("native_excluded_low_observations native_excluded_invalid native_failed_input native_disposition_unavailable")),
            "evidence_occurrence_id": _nullable(_STR), "evidence_line_number": _nullable(_POS),
            "volume_key": _nullable(_STR), "native_profile_ordinal": _nullable(_INT)})),
        "volumes": _array(_object({"volume_key": _STR, "native_prefix": _STR,
            "occurrence_ids": _unique(_STR), "parameter_observations": _array(PARAMETER_OBSERVATION_SCHEMA),
            "auxiliary_documents": _array(documents["profile_aux"]), "profile_entry_ordinals": _nullable(_unique(_INT))})),
        "profile_members": _array(_object({"occurrence_id": _STR,
            "component": _enum("sequence_database rps lookup auxiliary frequency delta_weights delta_observations cobalt_blocks alias unknown")}))})
    artifact_base = {k: v for k, v in common["DatabaseArtifactSet"]["properties"].items()
                     if k not in {"version", "kind", "operation", "identity", "dependencies", "detail"}}
    artifact_base.update({"version": {"const": "blast_database_artifact_set_v2"},
        "operation": OPERATION_SCHEMA, "identity": DATABASE_IDENTITY_SCHEMA,
        "dependencies": _array(DEPENDENCY_SCHEMA), "database_bindings": _array(common["DatabaseBinding"]),
        "materializations": _array(MATERIALIZATION_RECEIPT_SCHEMA)})
    artifact = {"anyOf": [_object({**artifact_base, "kind": {"const": kind}, "detail": detail})
        for kind, detail in (("identifier_list", identifier_detail), ("database_alias", alias_detail),
                             ("megablast_index", index_detail), ("profile_database", profile_detail))]}
    inspection = _object({"version": {"const": "blast_database_inspection_v2"},
        "operation": OPERATION_SCHEMA, "original_outcome": common["NativeOutcome"],
        "subject": {"anyOf": [_object({"kind": {"const": "identifier_list"}, "occurrence_id": _STR}),
            _object({"kind": {"const": "database"}, "database_key": _STR})]},
        "database_bindings": _array(common["DatabaseBinding"]), "output_occurrence": common["ArtifactOccurrence"],
        "native_fields": _array(field), "completeness": _enum("complete partial unknown"), **diagnostics})
    return {"PreparationDocument": {"anyOf": list(documents.values())},
        "ParameterObservation": PARAMETER_OBSERVATION_SCHEMA, "MaterializationReceipt": MATERIALIZATION_RECEIPT_SCHEMA,
        "Operation": OPERATION_SCHEMA, "DatabaseArtifactSet": artifact, "DatabaseInspection": inspection}


def _require(condition, code):
    if not condition:
        raise ContractError("blast_utility_" + code)


def _ordinals(rows, field="ordinal", *, partial=False):
    values = [r[field] for r in rows]
    _require(values == sorted(set(values)) if partial else values == list(range(len(rows))), "preparation_ordinals")


def validate_preparation_operation(value):
    """Relationships for the closed v2 branch; called after shared shape checks."""
    p, mode, key = value["parameters"], value["mode"], value["database_key"]
    refs = set()
    source = p.get("source_database_key", p.get("seqid_database_key"))
    _require(key == source, "preparation_database_key")
    for name in ("output_path", "output_prefix", "statistics_path"):
        if p.get(name) is not None:
            _relative(p[name])
    if mode in {"convert_gi_list", "convert_seqid_list", "inspect_seqid_list"}:
        refs.add(p["input_occurrence_id"])
        if key is None:
            _require(value["molecule"] == "unknown", "unbound_list_molecule")
    elif mode == "create_subset_alias":
        if p["restriction"]["kind"] != "oid_masks":
            refs.add(p["restriction"]["occurrence_id"])
    elif mode == "aggregate_databases":
        _require(p["classic_list"] is not None or p["vdb_list"] is not None, "aggregate_population_required")
        for selected in (p["classic_list"], p["vdb_list"]):
            if selected is None:
                continue
            _ordinals(selected["entries"])
            file = selected["source"] == "file"
            if file:
                refs.add(selected["input_occurrence_id"])
            for entry in selected["entries"]:
                _require((entry["line_number"] is not None) == file, "database_list_location")
                if not file:
                    _require(not any(c.isspace() for c in entry["native_reference"]), "database_inline_token")
    elif mode == "aggregate_volumes":
        _ordinals(p["volume_entries"])
        _require(p["num_volumes"] == len(p["volume_entries"]), "volume_population")
        _require(all(e["line_number"] is None for e in p["volume_entries"]), "volume_database_reference")
    elif mode == "create_megablast_index":
        fasta = p["input_format"] == "fasta"
        _require(fasta == (p["input_occurrence_id"] is not None) and fasta == (key is None), "index_input_source")
        _require(p["old_style_index"] or not fasta, "index_new_style_database")
        _require(not p["old_style_index"] or p["output_prefix"] is not None, "index_output_prefix")
        _require(not fasta or p["db_mask"] is None, "index_mask_database_required")
        if fasta:
            refs.add(p["input_occurrence_id"])
    elif mode == "create_profile_database":
        _ordinals(p["profile_entries"])
        refs = {p["profile_list_occurrence_id"], *(e["input_occurrence_id"] for e in p["profile_entries"])}
        _require(p["profile_list_occurrence_id"] not in {e["input_occurrence_id"] for e in p["profile_entries"]}, "profile_input_role_conflict")
        _require(p["taxid"] is None or p["taxid_map_occurrence_id"] is None, "taxid_map_exclusive")
        if p["taxid_map_occurrence_id"] is not None:
            _require(p["taxid_map_occurrence_id"] not in refs, "profile_input_role_conflict")
            refs.add(p["taxid_map_occurrence_id"])
        _require(value["molecule"] == "protein", "profile_molecule")
        for entry in p["profile_entries"]:
            _require(not any(c.isspace() for c in entry["native_reference"]), "profile_native_token")
        positions = [(e["line_number"], e["token_ordinal"]) for e in p["profile_entries"]]
        _require(positions == sorted(set(positions)), "profile_list_locations")
    _require(set(value["input_occurrence_ids"]) == refs, "preparation_input_population")
    if value["program"] == "makembindex":
        _require(value["molecule"] == "dna", "index_molecule")
    if key is not None or mode.startswith("aggregate") or mode == "create_subset_alias":
        _require(value["molecule"] in {"dna", "protein"}, "preparation_molecule")


def validate_parameter_observation(value):
    if value["effect"] == "unknown":
        _require(value["value"] is None and value["missing_reason"] is not None, "parameter_unknown_reason")
    else:
        _require(value["occurrence_id"] is not None and value["line_number"] is not None
                 and value["native_lexeme"] is not None and value["missing_reason"] is None, "parameter_evidence")
        _require((value["value"] is None) == (value["effect"] == "ignored"), "parameter_effect_value")


def validate_materialization_receipt(value):
    from .native_blast_standard_database_contracts import _absolute
    _relative(value["relative_path"])
    if value["kind"] in {"database_copy", "input_copy"}:
        _absolute(value["source_path"])
    else:
        _ordinals(value["entries"])
        positions = [(r["line_number"], r["token_ordinal"]) for r in value["entries"]]
        _require(positions == sorted(set(positions)), "materialization_locations")
        for row in value["entries"]:
            _require(not any(c.isspace() for c in row["realized_token"]), "materialization_native_token")
            if value["grammar"] == "blast_database_lines":
                _require(row["token_ordinal"] == 0 and row["target"]["kind"] == "database", "materialization_grammar")
            else:
                _require(row["target"]["kind"] == "input", "materialization_grammar")


def blast_preparation_document_schema() -> dict:
    from .blast_utility_contracts import SCHEMAS
    return _copy(SCHEMAS["PreparationDocument"])


def validate_blast_preparation_document(value: dict) -> dict:
    from .blast_utility_contracts import validate_blast_utility_record
    return validate_blast_utility_record("PreparationDocument", value)


def validate_preparation_document_relationships(value):
    from .blast_utility_contracts import _diagnostics, _fields
    oid, kind = value["occurrence_id"], value["kind"]
    _fields(value["native_fields"], {oid})
    _diagnostics(value, occurrences={oid}, subjects={oid},
                 malformed_prefix=oid + "#/records/")
    partial = any(r["code"] in {"native_row_invalid", "native_document_invalid"} for r in value["failures"])
    for field in value["native_fields"]:
        name = field["field_name"]
        allowed = {"database_title", "database_sequence_count", "database_residue_count"} if kind == "alias" else (
            {"identifier_list_converted_count", "database_sequence_count"} if kind == "aliastool_diagnostics" else
            {"identifier_list_title", "identifier_list_count", "identifier_list_created_at_native",
             "identifier_list_database_created_at_native", "identifier_list_database_length", "identifier_list_database_volumes"})
        _require(name in allowed, "preparation_native_field_kind")
        if kind == "alias" and name == "database_residue_count":
            _require(field["value_basis"] == "native_reported", "alias_length_basis")
    if kind == "alias":
        names = {"TITLE": "database_title", "NSEQ": "database_sequence_count", "LENGTH": "database_residue_count"}
        located = [(names[r["native_key"]], r["line_number"], r["value_lexeme"])
                   for r in value["rows"] if r["native_key"] in names]
        _require([(f["field_name"], f["line_number"], f["native_lexeme"]) for f in value["native_fields"]] == located,
                 "alias_native_field_location")
        for field in value["native_fields"]:
            lexeme = field["native_lexeme"]
            if field["field_name"] == "database_title":
                _require(field["value"] == lexeme, "alias_native_field_value")
            elif field["value"] is not None:
                _require(re.fullmatch(r"[0-9]+", lexeme.strip(" \t")) is not None
                         and field["value"] == int(lexeme), "alias_native_field_value")
    elif kind == "aliastool_diagnostics":
        names = {"converted_gi_count": "identifier_list_converted_count", "created_alias_sequence_count": "database_sequence_count"}
        expected = [(names[r["category"]], r["line_number"], r["native_count"])
                    for r in value["rows"] if r["category"] in names]
        _require([(f["field_name"], f["line_number"], f["value"]) for f in value["native_fields"]] == expected,
                 "diagnostic_native_field_location")
    if kind in {"list", "alias", "profile_aux"}:
        name = {"list": "ordinal", "alias": "row_ordinal", "profile_aux": "native_profile_ordinal"}[kind]
        _ordinals(value["rows"], name, partial=partial)
    prior_end = 0
    for row in value["rows"]:
        if kind == "list":
            _require(prior_end <= row["start_byte"] < row["end_byte"], "preparation_list_offsets")
            _require(row["end_byte"] - row["start_byte"] == len(row["original_token"].encode("utf-8")), "preparation_list_span")
            prior_end = row["end_byte"]
        elif kind == "alias":
            _ordinals(row["tokens"])
        elif kind == "aliastool_diagnostics":
            _require((row["native_count"] is not None) == (row["category"] in {"converted_gi_count", "created_alias_sequence_count"}), "diagnostic_count_category")
        elif kind == "index_diagnostics":
            parameter = row["parameter_observation"]
            _require((parameter is not None) == (row["category"] in {"parameter_adjusted", "parameter_ignored"}), "diagnostic_parameter_category")
            _require((row["native_output_reference"] is not None) == (row["category"] in {"member_created", "empty_member_removed"}), "diagnostic_output_category")
            if parameter is not None:
                validate_parameter_observation(parameter)
                _require(parameter["scope_key"] == oid and parameter["occurrence_id"] == oid
                         and parameter["line_number"] == row["line_number"], "parameter_document_scope")
                _require(parameter["parameter"] in {"nmer", "ws_hint", "stride", "legacy", "old_style_index", "output_prefix"}, "parameter_document_kind")
        elif kind == "profile_aux":
            _require(row["length_line_number"] == 9 + 2 * row["native_profile_ordinal"]
                     and row["k_line_number"] == row["length_line_number"] + 1, "profile_aux_locations")
    for parameter in value.get("parameter_observations", []):
        validate_parameter_observation(parameter)
        _require(parameter["scope_key"] == oid and parameter["occurrence_id"] in {None, oid}, "parameter_document_scope")
        _require(parameter["parameter"] in {"matrix", "gap_open", "gap_extend", "scale", "word_score_threshold"}, "parameter_document_kind")
    if kind == "profile_aux":
        locations = {"matrix": 1, "gap_open": 2, "gap_extend": 3, "scale": 8}
        _require([p["parameter"] for p in value["parameter_observations"]] == list(locations), "profile_aux_parameters")
        for parameter in value["parameter_observations"]:
            _require(parameter["line_number"] in {None, locations[parameter["parameter"]]}, "profile_aux_parameter_location")


def validate_preparation_inspection(value):
    from .blast_utility_contracts import _binding, _diagnostics, _fields, _occurrence, _operation, _outcome
    op, out = value["operation"], value["output_occurrence"]
    _operation(op); _outcome(value["original_outcome"]); _occurrence(out)
    bindings = value["database_bindings"]
    keys = [r["database_key"] for r in bindings]
    _require(len(keys) == len(set(keys)), "duplicate_database_key")
    for row in bindings:
        _binding(row)
    if (op["program"], op["mode"]) == ("blastdb_aliastool", "inspect_seqid_list"):
        _require(value["subject"] == {"kind": "identifier_list", "occurrence_id": op["parameters"]["input_occurrence_id"]}
                 and not bindings and out["native_format"] == "blast_seqid_list_info_text", "inspection_subject")
        _require(all(f["field_name"] in {"identifier_list_title", "identifier_list_count", "identifier_list_created_at_native",
            "identifier_list_database_created_at_native", "identifier_list_database_length", "identifier_list_database_volumes"}
            for f in value["native_fields"]), "inspection_native_fields")
        _require(all(f["unit"] == "symbols" for f in value["native_fields"]
                     if f["field_name"] == "identifier_list_database_length"), "inspection_unknown_molecule_unit")
    else:
        _require((op["program"], op["mode"]) == ("makembindex", "show_filters"), "inspection_operation")
        _require(value["subject"] == {"kind": "database", "database_key": op["database_key"]}
                 and keys == [op["database_key"]] and bindings[0]["molecule"] == "dna", "inspection_subject")
        _require(not value["native_fields"] and out["native_format"] == "text", "filter_native_grammar_unverified")
    _require(out["direction"] == "output" and out["role"] == "stdout", "inspection_output")
    _fields(value["native_fields"], {out["occurrence_id"]})
    known = {out["occurrence_id"], *op["input_occurrence_ids"], *(k for b in bindings for k in b["occurrence_ids"])}
    _diagnostics(value, occurrences=known, subjects=known | set(keys), outcome=value["original_outcome"])
    if value["completeness"] == "complete":
        _require(out["completeness"] == "complete", "inspection_capture_completeness")


__all__ = ["blast_preparation_document_schema", "validate_blast_preparation_document",
    "PARAMETER_OBSERVATION_SCHEMA", "MATERIALIZATION_RECEIPT_SCHEMA", "OPERATION_PARAMETERS",
    "DATABASE_ENTRY_SCHEMA", "PROFILE_ENTRY_SCHEMA", "MATERIALIZATION_ENTRY_SCHEMA"]
