"""Finite supplied-data fields for one selected PSI/DELTA invocation.

The sheet retains complete collector and PSSM numerical inputs. This function
does not decode membership/convergence formats, qualify scientific relations,
select a round, or calculate evidence. Inner sequence/profile metadata syntax
belongs to its delivered dependency and is checked locally during composition.
"""
from __future__ import annotations

import json
import math
import re

from . import blast_pssm_calculators as _pssm


_FIELDS = {"schema", "collection", "report_sources", "query_bindings", "search_bindings",
           "pssm_sheets", "checkpoint_bindings", "sequence_metadata", "profile_metadata",
           "comparison_pairs", "inclusion_records", "convergence_records",
           "invocation_source", "target_context"}
_LISTS = _FIELDS - {"schema", "collection", "invocation_source", "target_context"}
_SEARCH_FIELDS = {"search_key", "program_context", "stage", "iteration", "normalized",
                  "row_map", "operand_binding", "reporting", "native", "issues"}
_OPERAND_FIELDS = {"role", "artifact_key", "record_ordinal", "native_id", "native_title",
                   "subject_ref", "molecule", "length", "selected_interval", "identity"}


def _copy(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    raise ValueError("blast_iteration_finite_json_required")


def _fail(kind, path):
    raise ValueError("blast_iteration_input_" + kind + "_invalid", path)


def _keys(value, keys, path):
    if type(value) is not dict or set(value) != set(keys):
        _fail("fields", path)


def _is(value, condition, path):
    if not condition:
        _fail("type", path)
    return value


def _text(value):
    return type(value) is str and bool(value.strip())


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _pointer(value):
    return (type(value) is str and (value == "" or value.startswith("/"))
            and re.search(r"~(?![01])", value) is None)


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _key(value, path):
    _keys(value, {"artifact_key", "member_ordinal", "report_index", "search_pointer"}, path)
    _is(value, _text(value["artifact_key"]) and _integer(value["report_index"])
        and (value["member_ordinal"] is None or _integer(value["member_ordinal"]))
        and _pointer(value["search_pointer"]), path)


def _token(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _provenance(value, path, nullable=False):
    if value is None and nullable:
        return
    _keys(value, {"source_ref", "pointer"}, path)
    _is(value, _text(value["source_ref"]) and _pointer(value["pointer"]), path)


def _identity(value, path):
    _keys(value, {"namespace", "value", "version"}, path)
    _is(value, _text(value["namespace"]) and _text(value["value"])
        and (value["version"] is None or _text(value["version"])), path)


def _operand(value, path):
    _keys(value, _OPERAND_FIELDS, path)
    _is(value, value["role"] in ("query", "subject", "database", "profile", "msa", "checkpoint")
        and value["molecule"] in ("dna", "rna", "protein", "unknown")
        and (value["record_ordinal"] is None or _integer(value["record_ordinal"]))
        and (value["length"] is None or _integer(value["length"], 1))
        and all(value[k] is None or _text(value[k]) for k in ("artifact_key", "subject_ref"))
        and all(value[k] is None or type(value[k]) is str for k in ("native_id", "native_title")), path)
    interval = value["selected_interval"]
    _is(interval, interval is None or type(interval) is list and len(interval) == 2
        and all(_integer(v) for v in interval) and interval[0] < interval[1]
        and (value["length"] is None or interval[1] <= value["length"]), path + "/selected_interval")
    if value["identity"] is not None:
        _identity(value["identity"], path + "/identity")


def _database(value, path):
    if value is None:
        return
    _keys(value, {"namespace", "value", "version", "release", "scope", "preparation_type", "source"}, path)
    _is(value, _text(value["namespace"]) and _text(value["value"])
        and all(value[k] is None or _text(value[k]) for k in ("version", "release", "scope"))
        and value["preparation_type"] in ("sequence_database", "rps", "delta", "unknown"), path)
    _provenance(value["source"], path + "/source")


def _query(value, path):
    if value is None:
        return
    _keys(value, {"operand", "axis_kind", "full_length", "coordinate_unit", "sequence_sha256",
                  "pssm_key", "master_mapping_ref"}, path)
    _operand(value["operand"], path + "/operand")
    _is(value, value["axis_kind"] in ("sequence", "pssm_master", "msa_master")
        and _integer(value["full_length"], 1) and value["coordinate_unit"] in ("aa", "nt")
        and (value["sequence_sha256"] is None or _digest(value["sequence_sha256"]))
        and (value["pssm_key"] is None or _text(value["pssm_key"])), path)
    _provenance(value["master_mapping_ref"], path + "/master_mapping_ref", True)


def _evidence(value, path):
    _keys(value, {"origin", "source", "source_format", "original_record", "extractor"}, path)
    _is(value, value["origin"] in ("supplied_source_record", "native_extractor_output")
        and _text(value["source_format"]) and type(value["original_record"]) in (dict, list, str), path)
    _provenance(value["source"], path + "/source")
    if value["origin"] == "supplied_source_record":
        _is(value["extractor"], value["extractor"] is None, path + "/extractor")
    else:
        _keys(value["extractor"], {"module", "function", "version"}, path + "/extractor")
        _is(value["extractor"], all(_text(v) for v in value["extractor"].values()), path + "/extractor")


def _collection(value):
    if (type(value) is not dict or set(value) != {"schema", "invocation", "artifacts", "searches", "issues"}
            or value["schema"] != "blast_report_collection_v1"):
        raise ValueError("blast_iteration_collection_schema_invalid")
    inv = value["invocation"]
    _keys(inv, {"execution_program", "scientific_mode", "resource_kind", "query_kind", "reference_kind",
                "request", "effective_options", "operands", "completion"}, "/collection/invocation")
    if (inv["execution_program"] not in ("psiblast", "deltablast") or inv["scientific_mode"] != "database"
            or inv["reference_kind"] != "sequence" or inv["query_kind"] not in
            (("sequence", "msa", "pssm") if inv["execution_program"] == "psiblast" else ("sequence",))):
        raise ValueError("blast_iteration_program_or_mode_unsupported")
    for name in ("request", "effective_options", "completion"):
        _is(inv[name], type(inv[name]) is dict, "/collection/invocation/" + name)
    _is(inv["operands"], type(inv["operands"]) is list, "/collection/invocation/operands")
    for i, operand in enumerate(inv["operands"]):
        _operand(operand, f"/collection/invocation/operands/{i}")
    for name in ("artifacts", "searches", "issues"):
        _is(value[name], type(value[name]) is list, "/collection/" + name)
    seen = set()
    for i, search in enumerate(value["searches"]):
        path = f"/collection/searches/{i}"
        _keys(search, _SEARCH_FIELDS, path)
        _key(search["search_key"], path + "/search_key")
        token = _token(search["search_key"])
        if token in seen:
            raise ValueError("blast_iteration_collection_search_key_duplicate")
        seen.add(token)
        for name in ("program_context", "normalized", "reporting", "native"):
            _is(search[name], type(search[name]) is dict, path + "/" + name)
        for name in ("row_map", "issues"):
            _is(search[name], type(search[name]) is list, path + "/" + name)
        norm = search["normalized"]
        _is(norm, norm.get("schema") == "blast_normalized_result_v1"
            and norm.get("format") in ("json2", "tabular")
            and all(type(norm.get(k)) is dict for k in ("query", "search", "native"))
            and type(norm.get("hits")) is list and type(norm.get("issues")) is list, path + "/normalized")
        if search["operand_binding"] is not None:
            _operand(search["operand_binding"], path + "/operand_binding")


def _validate(sheet):
    sheet = _copy(sheet)
    if type(sheet) is not dict or set(sheet) != _FIELDS or sheet["schema"] != "blast_iteration_sheet_v1":
        raise ValueError("blast_iteration_sheet_fields_invalid")
    _collection(sheet["collection"])
    for name in _LISTS:
        _is(sheet[name], type(sheet[name]) is list, "/" + name)
    for name in ("report_sources", "query_bindings", "search_bindings", "sequence_metadata", "profile_metadata"):
        for i, row in enumerate(sheet[name]):
            p = f"/{name}/{i}"
            fields = {"report_sources": {"search_key", "report_source"}, "query_bindings": {"search_key", "query_binding"},
                "search_bindings": {"search_key", "stage", "biological_round", "database_identity", "input_pssm_key", "provenance"},
                "sequence_metadata": {"search_key", "reference_metadata", "description_bindings", "sequence_identity_bindings", "database_profile"},
                "profile_metadata": {"search_key", "profile_records", "profile_bindings", "function_bindings", "model_relations"}}[name]
            _keys(row, fields, p)
            _key(row["search_key"], p + "/search_key")
            if name == "report_sources":
                source = row["report_source"]
                _keys(source, {"artifact_key", "artifact_ref", "member_ordinal", "member_sha256"}, p + "/report_source")
                _is(source, _text(source["artifact_key"]) and _text(source["artifact_ref"])
                    and (source["member_ordinal"] is None or _integer(source["member_ordinal"]))
                    and (source["member_sha256"] is None or _digest(source["member_sha256"]))
                    and (source["member_ordinal"] is None) == (source["member_sha256"] is None), p + "/report_source")
            elif name == "query_bindings":
                _query(row["query_binding"], p + "/query_binding")
            elif name == "search_bindings":
                _is(row, row["stage"] in (None, "sequence_database", "domain_database")
                    and (row["biological_round"] is None or _integer(row["biological_round"], 1))
                    and (row["input_pssm_key"] is None or _text(row["input_pssm_key"])), p)
                _provenance(row["provenance"], p + "/provenance", True)
                _database(row["database_identity"], p + "/database_identity")
            else:
                for field in fields - {"search_key", "database_profile"}:
                    _is(row[field], type(row[field]) is list and all(type(v) is dict for v in row[field]), p + "/" + field)
                if name == "sequence_metadata":
                    _is(row["database_profile"], row["database_profile"] is None or type(row["database_profile"]) is dict, p + "/database_profile")
                    for field in ("description_bindings", "sequence_identity_bindings"):
                        for j, link in enumerate(row[field]):
                            _keys(link, {"search_key", "binding"}, f"{p}/{field}/{j}")
                            _key(link["search_key"], f"{p}/{field}/{j}/search_key")
                            _is(link["binding"], type(link["binding"]) is dict, f"{p}/{field}/{j}/binding")
    for i, pssm in enumerate(sheet["pssm_sheets"]):
        try:
            _pssm._validate_sheet(pssm)
        except ValueError as error:
            raise ValueError("blast_iteration_input_fields_invalid", f"/pssm_sheets/{i}", error.args[0]) from error
        _is(pssm, _text(pssm["artifact_key"]) and _text(pssm["source_ref"]), f"/pssm_sheets/{i}")
        _keys(pssm["input_identity"], {"sha256", "size_bytes"}, f"/pssm_sheets/{i}/input_identity")
        _is(pssm, _digest(pssm["input_identity"]["sha256"]) and _integer(pssm["input_identity"]["size_bytes"]), f"/pssm_sheets/{i}/input_identity")
    for i, row in enumerate(sheet["checkpoint_bindings"]):
        p = f"/checkpoint_bindings/{i}"
        _keys(row, {"pssm_key", "role", "search_key", "biological_round", "provenance"}, p)
        _is(row, _text(row["pssm_key"]) and row["role"] in ("input", "after_search", "output")
            and (row["biological_round"] is None or _integer(row["biological_round"], 1)), p)
        if row["search_key"] is not None:
            _key(row["search_key"], p + "/search_key")
        _provenance(row["provenance"], p + "/provenance")
    seen = set()
    for i, row in enumerate(sheet["comparison_pairs"]):
        p = f"/comparison_pairs/{i}"
        _keys(row, {"comparison_key", "earlier_search_key", "later_search_key", "identity_basis", "relation_source"}, p)
        _is(row, _text(row["comparison_key"]) and row["identity_basis"] in ("full_sequence_digest", "profile_model_identifier"), p)
        if row["comparison_key"] in seen:
            raise ValueError("blast_iteration_comparison_key_duplicate")
        seen.add(row["comparison_key"])
        for field in ("earlier_search_key", "later_search_key"):
            _key(row[field], p + "/" + field)
        _provenance(row["relation_source"], p + "/relation_source")
    seen = set()
    for name in ("inclusion_records", "convergence_records"):
        for i, row in enumerate(sheet[name]):
            p = f"/{name}/{i}"
            fields = ({"record_key", "pssm_key", "search_key", "membership_kind", "query_membership", "complete", "members", "evidence"}
                      if name == "inclusion_records" else {"record_key", "search_key", "query_operand", "native_converged", "evidence"})
            _keys(row, fields, p)
            _is(row["record_key"], _text(row["record_key"]), p + "/record_key")
            if row["record_key"] in seen:
                raise ValueError("blast_iteration_observation_record_key_duplicate")
            seen.add(row["record_key"])
            if row["search_key"] is not None:
                _key(row["search_key"], p + "/search_key")
            _evidence(row["evidence"], p + "/evidence")
            if name == "inclusion_records":
                _is(row, _text(row["pssm_key"]) and row["membership_kind"] == "checkpoint_sequence_members"
                    and row["query_membership"] in ("included", "excluded", "unknown")
                    and type(row["complete"]) is bool and type(row["members"]) is list, p)
                for j, member in enumerate(row["members"]):
                    _keys(member, {"identity", "provenance"}, f"{p}/members/{j}")
                    _identity(member["identity"], f"{p}/members/{j}/identity")
                    _provenance(member["provenance"], f"{p}/members/{j}/provenance")
            else:
                _is(row["native_converged"], type(row["native_converged"]) is bool, p + "/native_converged")
                if row["query_operand"] is not None:
                    _operand(row["query_operand"], p + "/query_operand")
    _provenance(sheet["invocation_source"], "/invocation_source", True)
    _is(sheet["target_context"], sheet["target_context"] is None or type(sheet["target_context"]) is dict, "/target_context")
    return sheet


def populate_blast_iteration_sheet(collection, *, report_sources, query_bindings,
        search_bindings, pssm_sheets, checkpoint_bindings, sequence_metadata,
        profile_metadata, comparison_pairs, inclusion_records, convergence_records,
        invocation_source=None, target_context=None) -> dict:
    """Detach exact input fields; preserve conflicting associations for calculation."""
    return _validate(dict(schema="blast_iteration_sheet_v1", collection=collection,
        report_sources=report_sources, query_bindings=query_bindings, search_bindings=search_bindings,
        pssm_sheets=pssm_sheets, checkpoint_bindings=checkpoint_bindings, sequence_metadata=sequence_metadata,
        profile_metadata=profile_metadata, comparison_pairs=comparison_pairs, inclusion_records=inclusion_records,
        convergence_records=convergence_records, invocation_source=invocation_source, target_context=target_context))


__all__ = ["populate_blast_iteration_sheet"]
