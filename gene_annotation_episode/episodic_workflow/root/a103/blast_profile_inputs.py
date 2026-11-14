"""Finite supplied-data sheets for RPS and explicitly bound DELTA domain searches.

Population checks caller types and retains the complete collection search and
model records. It does not establish scientific joins or calculate a score.
``blast_profile_calculators`` qualifies those joins and calculates numbers from
this saved sheet. No acquisition, execution, filesystem or Store access occurs.

The native HSP numbers in ``search`` are the measured cells. ``num_columns`` is
the supplied model's number of positions; thresholds are optional same-model,
same-release measurements in bits, never defaults. ``native_record`` preserves
all supplied model fields, including unknown fields. ``target_context`` is
retained but unused by this schema's calculations. A model representative is
not a biological reference sequence or a training-sequence taxonomy population.
"""
from __future__ import annotations

import math
import re


SCHEMA = "blast_profile_search_sheet_v1"
SHEET_FIELDS = {"schema", "search", "report_source", "search_binding", "query_binding",
                "profile_records", "profile_bindings", "function_bindings",
                "model_relations", "target_context"}
_SEARCH_FIELDS = {"search_key", "program_context", "stage", "iteration", "normalized",
                  "row_map", "operand_binding", "reporting", "native", "issues"}
_OPERAND_FIELDS = {"role", "artifact_key", "record_ordinal", "native_id", "native_title",
                   "subject_ref", "molecule", "length", "selected_interval", "identity"}
_MODEL_FIELDS = {"profile_key", "database_identity", "model_identifier", "pssm_key",
                 "num_columns", "master_sequence_ref", "specific_bits_threshold",
                 "reporting_bits_threshold", "source", "native_record"}
RELATIONS = frozenset({"identical_model", "same_family", "same_superfamily",
                       "overlapping_training_set"})


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _copy(item) for key, item in value.items()}
    raise ValueError("blast_profile_finite_json_required")


def _keys(value, names, code):
    if type(value) is not dict or set(value) != names:
        raise ValueError("blast_profile_" + code)


def _text(value, *, nullable=False):
    return value is None and nullable or type(value) is str and bool(value.strip())


def _integer(value, *, minimum=0, nullable=False):
    return value is None and nullable or type(value) is int and value >= minimum


def _pointer(value):
    return (type(value) is str and (not value or value.startswith("/"))
            and re.search(r"~(?![01])", value) is None)


def _digest(value):
    return value is None or type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _provenance(value, *, nullable=False):
    if value is None and nullable:
        return
    _keys(value, {"source_ref", "pointer"}, "provenance_fields_invalid")
    if not _text(value["source_ref"]) or not _pointer(value["pointer"]):
        raise ValueError("blast_profile_provenance_invalid")


def _search_key(value):
    _keys(value, {"artifact_key", "member_ordinal", "report_index", "search_pointer"},
          "search_key_fields_invalid")
    if (not _text(value["artifact_key"]) or not _integer(value["member_ordinal"], nullable=True)
            or not _integer(value["report_index"]) or not _pointer(value["search_pointer"])):
        raise ValueError("blast_profile_search_key_invalid")


def _identifier(value):
    _keys(value, {"namespace", "value", "version"}, "identifier_fields_invalid")
    if (not _text(value["namespace"]) or not _text(value["value"])
            or not _text(value["version"], nullable=True)):
        raise ValueError("blast_profile_identifier_invalid")


def _database(value):
    _keys(value, {"namespace", "value", "version", "release", "scope",
                  "preparation_type", "source"}, "database_fields_invalid")
    if (not _text(value["namespace"]) or not _text(value["value"])
            or any(not _text(value[key], nullable=True) for key in ("version", "release", "scope"))
            or value["preparation_type"] not in ("sequence_database", "rps", "delta", "unknown")):
        raise ValueError("blast_profile_database_invalid")
    _provenance(value["source"])


def _operand(value):
    _keys(value, _OPERAND_FIELDS, "operand_fields_invalid")
    if (value["role"] not in ("query", "subject", "database", "profile", "msa", "checkpoint")
            or value["molecule"] not in ("dna", "rna", "protein", "unknown")
            or not _integer(value["record_ordinal"], nullable=True)
            or not _integer(value["length"], minimum=1, nullable=True)
            or any(not _text(value[key], nullable=True) for key in
                   ("artifact_key", "native_id", "native_title", "subject_ref"))):
        raise ValueError("blast_profile_operand_invalid")
    interval = value["selected_interval"]
    if interval is not None and (type(interval) is not list or len(interval) != 2
            or any(not _integer(x) for x in interval) or interval[0] >= interval[1]
            or value["length"] is not None and interval[1] > value["length"]):
        raise ValueError("blast_profile_operand_interval_invalid")
    if value["identity"] is not None:
        _identifier(value["identity"])


def _query(value):
    if value is None:
        return
    _keys(value, {"operand", "axis_kind", "full_length", "coordinate_unit", "sequence_sha256",
                  "pssm_key", "master_mapping_ref"}, "query_binding_fields_invalid")
    _operand(value["operand"])
    if (value["axis_kind"] not in ("sequence", "pssm_master", "msa_master")
            or not _integer(value["full_length"], minimum=1)
            or value["coordinate_unit"] not in ("aa", "nt")
            or not _digest(value["sequence_sha256"])
            or not _text(value["pssm_key"], nullable=True)):
        raise ValueError("blast_profile_query_binding_invalid")
    _provenance(value["master_mapping_ref"], nullable=True)


def _description(value):
    _keys(value, {"id", "accession", "title", "taxid"}, "native_description_fields_invalid")
    if (any(value[key] is not None and type(value[key]) is not str for key in ("id", "accession", "title"))
            or not _integer(value["taxid"], minimum=1, nullable=True)):
        raise ValueError("blast_profile_native_description_invalid")


def _validate_sheet(sheet):
    """Validate and detach a saved sheet as well as newly supplied inputs."""
    sheet = _copy(sheet)
    _keys(sheet, SHEET_FIELDS, "sheet_fields_invalid")
    if sheet["schema"] != SCHEMA:
        raise ValueError("blast_profile_sheet_schema_invalid")
    search = sheet["search"]
    _keys(search, _SEARCH_FIELDS, "search_fields_invalid")
    _search_key(search["search_key"])
    for key in ("program_context", "normalized", "reporting", "native"):
        if type(search[key]) is not dict:
            raise ValueError("blast_profile_search_object_required:" + key)
    for key in ("row_map", "issues"):
        if type(search[key]) is not list:
            raise ValueError("blast_profile_search_array_required:" + key)
    if search["operand_binding"] is not None:
        _operand(search["operand_binding"])
    normalized = search["normalized"]
    if (normalized.get("schema") != "blast_normalized_result_v1"
            or normalized.get("format") not in ("json2", "tabular")
            or any(type(normalized.get(key)) is not dict for key in ("query", "search", "native"))
            or type(normalized.get("hits")) is not list
            or type(normalized.get("issues")) is not list):
        raise ValueError("blast_profile_normalized_search_invalid")
    source = sheet["report_source"]
    _keys(source, {"artifact_key", "artifact_ref", "member_ordinal", "member_sha256"},
          "report_source_fields_invalid")
    if (not _text(source["artifact_key"]) or not _text(source["artifact_ref"])
            or not _integer(source["member_ordinal"], nullable=True) or not _digest(source["member_sha256"])):
        raise ValueError("blast_profile_report_source_invalid")
    binding = sheet["search_binding"]
    _keys(binding, {"search_key", "stage", "biological_round", "database_identity", "input_pssm_key",
                   "provenance"}, "search_binding_fields_invalid")
    _search_key(binding["search_key"])
    if (binding["stage"] not in (None, "sequence_database", "domain_database")
            or not _integer(binding["biological_round"], minimum=1, nullable=True)
            or not _text(binding["input_pssm_key"], nullable=True)):
        raise ValueError("blast_profile_search_binding_invalid")
    _provenance(binding["provenance"], nullable=True)
    if binding["database_identity"] is not None:
        _database(binding["database_identity"])
    _query(sheet["query_binding"])
    for key in ("profile_records", "profile_bindings", "function_bindings", "model_relations"):
        if type(sheet[key]) is not list:
            raise ValueError("blast_profile_array_required:" + key)
    seen = set()
    for record in sheet["profile_records"]:
        _keys(record, _MODEL_FIELDS, "record_fields_invalid")
        key = record["profile_key"]
        if not _text(key) or key in seen:
            raise ValueError("blast_profile_record_key_invalid_or_duplicate")
        seen.add(key)
        _database(record["database_identity"])
        _identifier(record["model_identifier"])
        _provenance(record["source"])
        _provenance(record["master_sequence_ref"], nullable=True)
        if (not _text(record["pssm_key"], nullable=True)
                or not _integer(record["num_columns"], minimum=1, nullable=True)
                or type(record["native_record"]) is not dict):
            raise ValueError("blast_profile_record_invalid")
        for field in ("specific_bits_threshold", "reporting_bits_threshold"):
            value = record[field]
            if value is not None and type(value) not in (int, float):
                raise ValueError("blast_profile_threshold_invalid")
            if value is not None:
                try:
                    finite = math.isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    raise ValueError("blast_profile_threshold_invalid")
    seen = set()
    for binding in sheet["profile_bindings"]:
        _keys(binding, {"search_key", "hit_ordinal", "description_ordinal", "profile_key",
                        "native_description", "provenance"}, "binding_fields_invalid")
        _search_key(binding["search_key"])
        _description(binding["native_description"])
        _provenance(binding["provenance"])
        if (not _integer(binding["hit_ordinal"]) or not _integer(binding["description_ordinal"])
                or not _text(binding["profile_key"])):
            raise ValueError("blast_profile_binding_invalid")
        # Dict insertion order does not change a source binding's identity.
        identity = (tuple(sorted(binding["search_key"].items())), binding["hit_ordinal"],
                    binding["description_ordinal"], binding["profile_key"])
        if identity in seen:
            raise ValueError("blast_profile_binding_duplicate")
        seen.add(identity)
    for binding in sheet["function_bindings"]:
        _keys(binding, {"profile_key", "function", "evidence_refs", "provenance"},
              "function_binding_fields_invalid")
        _keys(binding["function"], {"namespace", "value"}, "function_fields_invalid")
        if (not _text(binding["profile_key"])
                or any(not _text(value) for value in binding["function"].values())
                or type(binding["evidence_refs"]) is not list):
            raise ValueError("blast_profile_function_binding_invalid")
        _provenance(binding["provenance"])
        for source in binding["evidence_refs"]:
            _provenance(source)
    for relation in sheet["model_relations"]:
        _keys(relation, {"left_profile_key", "right_profile_key", "relation", "provenance"},
              "model_relation_fields_invalid")
        if (any(not _text(relation[key]) for key in ("left_profile_key", "right_profile_key"))
                or type(relation["relation"]) is not str or relation["relation"] not in RELATIONS):
            raise ValueError("blast_profile_model_relation_invalid")
        _provenance(relation["provenance"])
    if sheet["target_context"] is not None and type(sheet["target_context"]) is not dict:
        raise ValueError("blast_profile_target_context_object_required")
    return sheet


def populate_blast_profile_sheet(search, *, report_source, search_binding,
        query_binding, profile_records, profile_bindings, function_bindings,
        model_relations, target_context=None) -> dict:
    """Copy the exact v1 fields; retain conflicts for the separate calculator.

    A missing QueryBinding, model length, threshold, stage or database is not a
    measured zero. Syntactically invalid caller inputs raise specific ValueErrors;
    native scientific conflicts survive in the returned search and metadata.
    """
    return _validate_sheet({"schema": SCHEMA, "search": search, "report_source": report_source,
        "search_binding": search_binding, "query_binding": query_binding,
        "profile_records": profile_records, "profile_bindings": profile_bindings,
        "function_bindings": function_bindings, "model_relations": model_relations,
        "target_context": target_context})


__all__ = ["populate_blast_profile_sheet", "SCHEMA"]
