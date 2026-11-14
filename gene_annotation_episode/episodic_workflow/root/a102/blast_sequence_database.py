"""Pure source-qualified sequence-database BLAST sheet and calculations.

``populate`` retains the full collector search and explicit supplied relations.
``calculate`` qualifies those relations on a detached copy and uses the existing
reference-kernel model. Neither function opens files, acquires records, executes
programs or publishes biological observations. Acquisition must authenticate
artifact_ref, sequence digests and each provenance record against captured data.

Numerical definitions (native statistical uncertainty is retained, not fitted):
* reported_length: native query_len/qlen or hit len/slen, in original aa/nt.
* full_length: exact bound query operand length, or validated target sequence
  binding length. A native full reference length is usable absent contradictory
  sequence metadata. Profile master length is a coordinate axis, not biology.
* selected coverage numerator: union of paired query intervals intersected with
  the explicit zero-based half-open selected interval, separately for each hit.
  The denominator is that interval's length; value is numerator/denominator
  only when all native HSPs have qualified geometry. No selection means null,
  not an invented full-range selection. A partial numerator is an observed
  lower bound and never a complete fraction. Translated axes count original nt.
* database_sheet: native HSP scores/counts, string-derived paired/identical/gap
  counts, coverage unions, explicit function/taxon/source associations, actual
  sequence groups and population counts, using blast_database_grader meanings.
* function_weights: unchanged conditional_reference_kernel_v1 and explicit
  retained-but-unused measurements; no source category becomes a confidence.

Caller contract defects raise ValueError. Native conflicts/missing inputs use
source-qualified issues (codes declared at their check, or retained upstream/
legacy codes); surviving native data always remains in the saved outer sheet.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from . import blast_grading_inputs as _reader
from . import blast_report_collection as _collection
from .blast_database_grader import (
    _DESCRIPTION_BINDING_FIELDS, _SEQUENCE_BINDING_FIELDS,
    _calculation_context, _explicit_inputs, _sequence_links, _union_length,
    _hit_measurements, _numeric_summary, _binding_fields_valid,
    _uses_record_locators, _validate_record_locators,
    _build_database_sheet, build_database_sheet, calculate_database_probabilities,
)
from .blast_program_context import resolve_blast_program_context
from .blast_pairwise_grader import alignment_components
from .blast_search import PROGRAM_UNITS
from .blast_database_population_associations import validate_blast_database_population_context
from .alignment_correspondence import ARTIFACT_SCHEMA, interval_length


SHEET_SCHEMA = "blast_sequence_database_result_sheet_v1"
SHEET_SCHEMA_V2 = "blast_sequence_database_result_sheet_v2"
SHEET_SCHEMA_V3 = "blast_sequence_database_result_sheet_v3"
COMPONENT_SCHEMA = "blast_sequence_database_result_components_v1"
_SHEET_FIELDS = {"schema", "search", "report_source", "search_binding", "query_binding",
    "reference_metadata", "description_bindings", "sequence_identity_bindings",
    "target_context", "database_profile"}
_SEARCH_FIELDS = {"search_key", "program_context", "stage", "iteration", "normalized",
    "row_map", "operand_binding", "reporting", "native", "issues"}
_KEY_FIELDS = {"artifact_key", "member_ordinal", "report_index", "search_pointer"}
_OPERAND_FIELDS = {"role", "artifact_key", "record_ordinal", "native_id", "native_title",
    "subject_ref", "molecule", "length", "selected_interval", "identity"}
_CONTEXT_FIELDS = {"execution_program", "reported_program", "scientific_mode", "query_kind",
    "reference_kind", "native_version", "geometry_program"}
_PROGRAMS = set(PROGRAM_UNITS) | {"psiblast", "deltablast"}


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(item) for item in value]
    if type(value) is dict and all(type(key) is str for key in value):
        return {key: _copy(item) for key, item in value.items()}
    raise ValueError("blast_sequence_database_finite_json_required")


def _keys(value, keys, code):
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(code)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _int(value, minimum=0):
    return type(value) is int and value >= minimum


def _pointer(value):
    return isinstance(value, str) and (value == "" or value.startswith("/")) and re.search(r"~(?![01])", value) is None


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None


def _provenance(value):
    _keys(value, {"source_ref", "pointer"}, "blast_sequence_database_provenance_fields_invalid")
    if not _text(value["source_ref"]) or not _pointer(value["pointer"]):
        raise ValueError("blast_sequence_database_provenance_invalid")


def _search_key(value):
    _keys(value, _KEY_FIELDS, "blast_sequence_database_search_key_fields_invalid")
    if (not _text(value["artifact_key"]) or not _int(value["report_index"])
            or value["member_ordinal"] is not None and not _int(value["member_ordinal"])
            or not _pointer(value["search_pointer"])):
        raise ValueError("blast_sequence_database_search_key_invalid")


def _operand(value):
    _keys(value, _OPERAND_FIELDS, "blast_sequence_database_operand_fields_invalid")
    if (value["role"] not in ("query", "subject", "database", "profile", "msa", "checkpoint")
            or value["molecule"] not in ("dna", "rna", "protein", "unknown")
            or any(value[key] is not None and not _text(value[key]) for key in
                   ("artifact_key", "subject_ref"))
            or any(value[key] is not None and not isinstance(value[key], str) for key in ("native_id", "native_title"))
            or value["record_ordinal"] is not None and not _int(value["record_ordinal"])
            or value["length"] is not None and not _int(value["length"], 1)):
        raise ValueError("blast_sequence_database_operand_invalid")
    interval = value["selected_interval"]
    if interval is not None and (not isinstance(interval, list) or len(interval) != 2
            or not _int(interval[0]) or not _int(interval[1], 1) or interval[0] >= interval[1]
            or value["length"] is not None and interval[1] > value["length"]):
        raise ValueError("blast_sequence_database_operand_interval_invalid")
    identity = value["identity"]
    if identity is not None:
        _keys(identity, {"namespace", "value", "version"}, "blast_sequence_database_operand_identity_fields_invalid")
        if not _text(identity["namespace"]) or not _text(identity["value"]) or identity["version"] is not None and not _text(identity["version"]):
            raise ValueError("blast_sequence_database_operand_identity_invalid")


def _validate(sheet):
    version = sheet.get("schema") if isinstance(sheet, dict) else None
    fields = _SHEET_FIELDS | {"database_population_associations"} if version == SHEET_SCHEMA_V3 else _SHEET_FIELDS
    _keys(sheet, fields, "blast_sequence_database_sheet_fields_invalid")
    if sheet["schema"] not in (SHEET_SCHEMA, SHEET_SCHEMA_V2, SHEET_SCHEMA_V3):
        raise ValueError("blast_sequence_database_sheet_required")
    association_version = 2 if sheet["schema"] in (SHEET_SCHEMA_V2, SHEET_SCHEMA_V3) else 1
    search = sheet["search"]
    _keys(search, _SEARCH_FIELDS, "blast_sequence_database_search_fields_invalid")
    _search_key(search["search_key"])
    if version == SHEET_SCHEMA_V3:
        validate_blast_database_population_context(dict(schema="blast_database_population_context_v1",
            search_key=search["search_key"], associations=sheet["database_population_associations"]))
    _keys(search["program_context"], _CONTEXT_FIELDS, "blast_sequence_database_program_context_fields_invalid")
    context = search["program_context"]
    if (any(not _text(context[field]) for field in ("execution_program", "scientific_mode", "query_kind", "reference_kind"))
            or any(context[field] is not None and not _text(context[field]) for field in
                   ("reported_program", "native_version", "geometry_program"))):
        raise ValueError("blast_sequence_database_program_context_invalid")
    if search["program_context"]["scientific_mode"] != "database":
        raise ValueError("blast_sequence_database_mode_required")
    normalized = search["normalized"]
    _keys(normalized, {"schema", "mode", "resource", "format", "query", "search", "hits", "native", "issues"},
          "blast_sequence_database_normalized_fields_invalid")
    if (not isinstance(normalized, dict) or normalized.get("schema") != "blast_normalized_result_v1"
            or not isinstance(normalized.get("query"), dict) or not isinstance(normalized.get("search"), dict)
            or not isinstance(normalized.get("hits"), list) or not isinstance(normalized.get("native"), dict)
            or not isinstance(search["native"], dict) or not isinstance(search["issues"], list)):
        raise ValueError("blast_sequence_database_normalized_search_invalid")
    _keys(normalized["query"], {"id", "title", "length"}, "blast_sequence_database_native_query_fields_invalid")
    if (any(normalized["query"][field] is not None and not isinstance(normalized["query"][field], str) for field in ("id", "title"))
            or normalized["query"]["length"] is not None and not _int(normalized["query"]["length"], 1)):
        raise ValueError("blast_sequence_database_native_query_invalid")
    _keys(normalized["search"], {"program", "version", "database", "parameters", "statistics", "request", "hit_array_present", "reported_hit_count"},
          "blast_sequence_database_normalized_search_fields_invalid")
    if not isinstance(normalized["search"]["request"], dict):
        raise ValueError("blast_sequence_database_native_request_object_required")
    if search["operand_binding"] is not None:
        _operand(search["operand_binding"])
    source = sheet["report_source"]
    source_fields = {"artifact_key", "artifact_ref", "member_ordinal", "member_sha256"}
    if version == SHEET_SCHEMA_V3 and isinstance(source, dict) and "source_ref" in source:
        source_fields.add("source_ref")
    _keys(source, source_fields, "blast_sequence_database_report_source_fields_invalid")
    if (not _text(source["artifact_key"]) or not _text(source["artifact_ref"])
            or "source_ref" in source and not _text(source["source_ref"])
            or source["member_ordinal"] is not None and not _int(source["member_ordinal"])
            or source["member_sha256"] is not None and not _digest(source["member_sha256"])
            or (source["member_ordinal"] is None) != (source["member_sha256"] is None)):
        raise ValueError("blast_sequence_database_report_source_invalid")
    binding = sheet["search_binding"]
    _keys(binding, {"search_key", "stage", "biological_round", "database_identity", "input_pssm_key", "provenance"},
          "blast_sequence_database_search_binding_fields_invalid")
    _search_key(binding["search_key"])
    if (binding["stage"] not in (None, "sequence_database", "domain_database")
            or binding["biological_round"] is not None and not _int(binding["biological_round"], 1)
            or binding["input_pssm_key"] is not None and not _text(binding["input_pssm_key"])):
        raise ValueError("blast_sequence_database_search_binding_invalid")
    if binding["provenance"] is not None:
        _provenance(binding["provenance"])
    _calculation_context({"reporting": search["reporting"], "database_identity": binding["database_identity"]})
    query = sheet["query_binding"]
    if query is not None:
        _keys(query, {"operand", "axis_kind", "full_length", "coordinate_unit", "sequence_sha256", "pssm_key", "master_mapping_ref"},
              "blast_sequence_database_query_binding_fields_invalid")
        _operand(query["operand"])
        if (query["axis_kind"] not in ("sequence", "pssm_master", "msa_master") or not _int(query["full_length"], 1)
                or query["coordinate_unit"] not in ("aa", "nt")
                or query["sequence_sha256"] is not None and not _digest(query["sequence_sha256"])
                or query["pssm_key"] is not None and not _text(query["pssm_key"])):
            raise ValueError("blast_sequence_database_query_binding_invalid")
        if query["master_mapping_ref"] is not None:
            _provenance(query["master_mapping_ref"])
    if not isinstance(sheet["reference_metadata"], list) or any(not isinstance(row, dict) for row in sheet["reference_metadata"]):
        raise ValueError("blast_sequence_database_metadata_records_required")
    for field in ("target_context", "database_profile"):
        if sheet[field] is not None and not isinstance(sheet[field], dict):
            raise ValueError("blast_sequence_database_" + field + "_object_required")
    for name, fields, locator_field in (("description_bindings", _DESCRIPTION_BINDING_FIELDS, "metadata_record_locator"),
                         ("sequence_identity_bindings", _SEQUENCE_BINDING_FIELDS, "record_locator")):
        if not isinstance(sheet[name], list):
            raise ValueError("blast_sequence_database_binding_list_required")
        seen = set()
        for link in sheet[name]:
            _keys(link, {"search_key", "binding"}, "blast_sequence_database_link_fields_invalid")
            _search_key(link["search_key"])
            if not _binding_fields_valid(link["binding"], fields, locator_field, association_version):
                raise ValueError("blast_sequence_database_inner_binding_fields_invalid")
            serialized = json.dumps(link, sort_keys=True)
            if serialized in seen:
                raise ValueError("blast_sequence_database_duplicate_source_binding")
            seen.add(serialized)
    _validate_record_locators(sheet["reference_metadata"],
        [row["binding"] for row in sheet["description_bindings"]],
        [row["binding"] for row in sheet["sequence_identity_bindings"]], association_version=association_version)


def populate_blast_sequence_database_sheet(search, *, report_source, search_binding,
        query_binding, reference_metadata, description_bindings, sequence_identity_bindings,
        target_context=None, database_profile=None, database_population_associations=None) -> dict:
    """Retain the complete native numerical search and supplied relationships."""
    sheet = _copy(dict(schema=SHEET_SCHEMA, search=search, report_source=report_source,
        search_binding=search_binding, query_binding=query_binding, reference_metadata=reference_metadata,
        description_bindings=description_bindings, sequence_identity_bindings=sequence_identity_bindings,
        target_context=target_context, database_profile=database_profile))
    # Representation dispatch is limited to the declared association fields.
    # Validation below still rejects malformed links and unknown inner fields.
    def bindings(rows):
        return [row.get("binding") for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if _uses_record_locators(sheet["reference_metadata"], bindings(sheet["description_bindings"]),
                             bindings(sheet["sequence_identity_bindings"])):
        sheet["schema"] = SHEET_SCHEMA_V2
    if database_population_associations is not None:
        sheet.update(schema=SHEET_SCHEMA_V3,
                     database_population_associations=_copy(database_population_associations))
    _validate(sheet)
    return sheet


def _issue(issues, key, code, *, hit=None, hsp=None, pointer=None, **details):
    issues.append({"code": code, "search_key": deepcopy(key), "hit_ordinal": hit,
        "hsp_ordinal": hsp, "source_pointer": key["search_pointer"] if pointer is None else pointer,
        "details": details})


def _row_key(key, hit=None, hsp=None, description=None):
    return dict(search_key=deepcopy(key), hit_ordinal=hit, hsp_ordinal=hsp, description_ordinal=description)


def _at(document, pointer):
    value = document
    for token in pointer.split("/")[1:] if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise KeyError(token)
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise KeyError(token)
    return value


def _admit(sheet, issues):
    search, source, binding = sheet["search"], sheet["report_source"], sheet["search_binding"]
    key, normalized, context = search["search_key"], search["normalized"], search["program_context"]
    problems = []
    if binding["search_key"] != key:
        problems.append("blast_sequence_database_search_binding_key_mismatch")
    if any(source[field] != key[field] for field in ("artifact_key", "member_ordinal")):
        problems.append("blast_sequence_database_report_source_key_mismatch")
    member = normalized["native"].get("archive_member")
    if key["member_ordinal"] is not None:
        if not isinstance(member, dict) or member.get("ordinal") != key["member_ordinal"]:
            problems.append("blast_sequence_database_member_ordinal_mismatch")
        elif member.get("sha256") is None:
            problems.append("blast_sequence_database_member_digest_unverifiable")
        elif member["sha256"] != source["member_sha256"]:
            problems.append("blast_sequence_database_member_digest_mismatch")
    elif member is not None:
        problems.append("blast_sequence_database_member_ordinal_mismatch")
    if binding["stage"] != "sequence_database":
        problems.append("blast_sequence_database_stage_unresolved" if binding["stage"] is None else "blast_sequence_database_stage_incompatible")
    if binding["provenance"] is None:
        problems.append("blast_sequence_database_stage_provenance_unavailable")
    identity = binding["database_identity"]
    if identity is not None and identity["preparation_type"] in ("rps", "delta"):
        problems.append("blast_sequence_database_target_population_incompatible")
    if context["execution_program"] not in _PROGRAMS or context["reference_kind"] != "sequence":
        problems.append("blast_sequence_database_target_population_incompatible")
    try:
        reproduced = resolve_blast_program_context(**{key: value for key, value in context.items() if key != "geometry_program"})
        if reproduced != context or context["geometry_program"] is None:
            problems.append("blast_sequence_database_program_context_unresolved")
    except (ValueError, TypeError) as error:
        problems.append("blast_sequence_database_program_context_incompatible")
        _issue(issues, key, "blast_sequence_database_program_resolver_rejected", reason=str(error))
    if (normalized["mode"] != "database" or normalized["search"].get("program") != context["execution_program"]
            or normalized["search"].get("version") != context["native_version"]):
        problems.append("blast_sequence_database_normalized_context_conflict")
    report = search["native"].get("report")
    if not isinstance(report, dict) or any(report.get(native) != context[field] for native, field in
            (("program", "reported_program"), ("version", "native_version"))):
        problems.append("blast_sequence_database_native_program_context_conflict")
    target = report.get("search_target") if isinstance(report, dict) else None
    if normalized.get("format") == "json2" and (not isinstance(target, dict) or "subjects" in target):
        problems.append("blast_sequence_database_native_target_incompatible")
    elif normalized.get("format") == "json2" and target.get("db") != normalized["search"].get("database"):
        problems.append("blast_sequence_database_native_database_conflict")
    for code in problems:
        _issue(issues, key, code)
    return not problems


def _query_axis(sheet, geometry, issues):
    search, query = sheet["search"], sheet["query_binding"]
    key = search["search_key"]
    unit = PROGRAM_UNITS[geometry][0] if geometry in PROGRAM_UNITS else None
    axis = {"sequence": "sequence", "pssm": "pssm_master", "msa": "msa_master"}.get(search["program_context"]["query_kind"])
    result = dict(axis_kind=axis, reported_length=search["normalized"]["query"].get("length"),
                  full_length=None, selected_interval=None, coordinate_unit=unit)
    if query is None or search["operand_binding"] is None:
        _issue(issues, key, "blast_sequence_database_query_axis_unbound")
        return result
    operand, reasons = query["operand"], []
    if operand != search["operand_binding"] or operand["role"] != "query":
        reasons.append("operand")
    if query["axis_kind"] != axis:
        reasons.append("axis_kind")
    if query["coordinate_unit"] != unit or operand["molecule"] not in ({"protein"} if unit == "aa" else {"dna", "rna"}):
        reasons.append("molecule")
    if query["full_length"] != operand["length"]:
        reasons.append("full_length")
    interval, reported = operand["selected_interval"], result["reported_length"]
    if reported is not None and reported != query["full_length"] and (interval is None or reported != interval[1] - interval[0]):
        reasons.append("reported_length")
    native = search["normalized"]["query"]
    if native.get("title") is not None and operand["native_title"] is not None and native["title"] != operand["native_title"]:
        reasons.append("native_title")
    if native.get("id") is not None and operand["native_id"] is not None and native["id"] != operand["native_id"]:
        generated = re.fullmatch(r"Query_\d+", native["id"]) and not re.fullmatch(r"Query_\d+", operand["native_id"])
        if not generated or native.get("title") != operand["native_title"]:
            reasons.append("native_id")
    if axis in ("pssm_master", "msa_master"):
        if query["master_mapping_ref"] is None:
            reasons.append("master_mapping_ref")
        if axis == "pssm_master" and query["pssm_key"] is None:
            reasons.append("pssm_key")
        selected_pssm = sheet["search_binding"]["input_pssm_key"]
        if selected_pssm is not None and query["pssm_key"] != selected_pssm:
            reasons.append("input_pssm_key")
        _issue(issues, key, "blast_sequence_database_master_biological_identity_unestablished")
    elif query["sequence_sha256"] is None:
        _issue(issues, key, "blast_sequence_database_query_sequence_digest_unavailable")
    if reasons:
        _issue(issues, key, "blast_sequence_database_query_axis_incompatible", fields=reasons)
    else:
        result.update(full_length=query["full_length"], selected_interval=deepcopy(interval))
    return result


def _locator(source, key, format_name, *, hit=None, hsp=None, description=None, rows=None, lines=None):
    pointer = key["search_pointer"]
    if format_name == "json2" and hit is not None:
        pointer += f"/hits/{hit}"
        if hsp is not None:
            pointer += f"/hsps/{hsp}"
        if description is not None:
            pointer += f"/description/{description}"
    locator = dict(artifact_ref=source["artifact_ref"], report_index=key["report_index"], pointer=pointer,
        search_key=deepcopy(key), member_ordinal=source["member_ordinal"], member_sha256=source["member_sha256"],
        native_format=format_name, hit_index=hit, description_index=description, hsp_index=hsp,
        line_numbers=deepcopy(lines), data_row_ordinals=deepcopy(rows))
    if "source_ref" in source:
        locator["source_ref"] = source["source_ref"]
    return locator


def _table_reconstruction(search):
    """Recheck actual retained text and declared fields with the same pure reader."""
    normalized, context, reporting = search["normalized"], search["program_context"], search["reporting"]
    key = search["search_key"]
    if key["member_ordinal"] is not None or key["report_index"] != 0:
        raise ValueError("blast_sequence_database_table_search_key_conflict")
    text = search["native"]["report"]["text"]
    match = re.fullmatch(r"/sections/(0|[1-9][0-9]*)", key["search_pointer"])
    if match is None:
        raise ValueError("blast_sequence_database_table_pointer_invalid")
    ordinal = int(match.group(1))
    layout = normalized["native"].get("table_layout")
    if layout is None:
        raise ValueError("blast_sequence_database_table_layout_unavailable")
    if (not isinstance(layout, dict) or set(layout) != {"format", "declared_fields", "delimiter"}
            or layout["format"] not in ("tabular6", "tabular7")
            or not isinstance(layout["delimiter"], str) or len(layout["delimiter"]) != 1
            or layout["delimiter"] in "\r\n\x00"
            or layout["format"] == "tabular6" and layout["declared_fields"] is None):
        raise ValueError("blast_sequence_database_table_layout_invalid")
    if layout["declared_fields"] is not None:
        try:
            _reader._fields(layout["declared_fields"])
        except ValueError as error:
            raise ValueError("blast_sequence_database_table_layout_invalid") from error
    artifact = dict(artifact_key=search["search_key"]["artifact_key"], format=layout["format"],
                    fields=layout["declared_fields"], delimiter=layout["delimiter"], sha256=normalized["native"].get("sha256"))
    sections = _collection._sections(text, artifact)
    invocation = {field: context[field] for field in ("execution_program", "scientific_mode", "query_kind", "reference_kind")}
    invocation.update(resource_kind=normalized["resource"], request=normalized["search"]["request"],
        effective_options={field: reporting[field] for field in ("requested_hit_limit", "requested_hsp_limit")},
        operands=[search["operand_binding"]] if search["operand_binding"] is not None else [],
        completion={field: reporting[field] for field in ("native_returncode", "producer_complete")})
    rebuilt = _collection._tabular_search(text, sections[ordinal], artifact, invocation, ordinal)
    if rebuilt["search_key"] != key:
        raise ValueError("blast_sequence_database_table_search_key_conflict")
    return rebuilt


def _rows(sheet, issues):
    search, source = sheet["search"], sheet["report_source"]
    key, normalized = search["search_key"], deepcopy(search["normalized"])
    fmt = normalized.get("format")
    index = {"search": _row_key(key), "hits": []}
    incomplete, native_ordinals = set(), []
    if fmt not in ("json2", "tabular"):
        _issue(issues, key, "blast_sequence_database_format_unsupported")
        return None, index, incomplete, native_ordinals
    try:
        if fmt == "json2":
            document = normalized["native"]["document"]
            outer = document.get("BlastOutput2") if isinstance(document, dict) else None
            if isinstance(outer, list):
                expected_report_pointer = f"/BlastOutput2/{key['report_index']}/report"
            elif isinstance(outer, dict) and key["report_index"] == 0:
                expected_report_pointer = "/BlastOutput2/report"
            else:
                raise ValueError("blast_sequence_database_native_report_index_conflict")
            report_pointer = key["search_pointer"].split("/results/")[0]
            if report_pointer != expected_report_pointer:
                raise ValueError("blast_sequence_database_native_report_index_conflict")
            native = _at(document, key["search_pointer"])
            if native != search["native"]["search"]:
                raise ValueError("blast_sequence_database_native_search_pointer_conflict")
            if _at(document, report_pointer) != search["native"]["report"]:
                raise ValueError("blast_sequence_database_native_report_pointer_conflict")
            native_query = _collection._query(native, key["search_pointer"], [])
            if native_query != normalized["query"]:
                raise ValueError("blast_sequence_database_native_query_conflict")
            original_hits = native.get("hits") if isinstance(native, dict) else None
            original_hits = original_hits if isinstance(original_hits, list) else []
            native_ordinals = list(range(len(original_hits)))
            expected_hits, expected_maps = [], []
            for h, native_hit in enumerate(original_hits):
                if not isinstance(native_hit, dict):
                    continue
                hit = dict(hit_index=h, length=native_hit.get("len"), descriptions=[], hsps=[], unpaired_metadata={})
                if not _int(hit["length"], 1):
                    hit["length"] = None
                mapping = dict(hit_index=h, description_ordinals=[], hsp_ordinals=[])
                for native_field, field, ordinals, reader in (("description", "descriptions", "description_ordinals", _reader._description),
                        ("hsps", "hsps", "hsp_ordinals", _collection._hsp)):
                    values = native_hit.get(native_field)
                    for ordinal, value in enumerate(values if isinstance(values, list) else []):
                        row = reader(value, [])
                        if row is not None:
                            hit[field].append(row)
                            mapping[ordinals].append(ordinal)
                    if native_field == "hsps" and (not isinstance(values, list) or len(values) != len(hit[field])):
                        incomplete.add(h)
                expected_hits.append(hit)
                expected_maps.append(mapping)
        else:
            rebuilt = _table_reconstruction(search)
            if rebuilt["native"]["search"] != search["native"]["search"] or rebuilt["native"]["line_numbers"] != search["native"]["line_numbers"]:
                raise ValueError("blast_sequence_database_native_table_conflict")
            if rebuilt["normalized"]["query"] != normalized["query"] or rebuilt["normalized"]["search"] != normalized["search"]:
                raise ValueError("blast_sequence_database_normalized_table_context_conflict")
            expected_hits, expected_maps = rebuilt["normalized"]["hits"], rebuilt["row_map"]
            native_ordinals = [hit["hit_index"] for hit in expected_hits]
            if any(row["code"] in ("blast_tabular_column_count_invalid", "blast_tabular_fields_unavailable_or_conflicting",
                    "blast_tabular_subject_identifier_required") for row in rebuilt["issues"]):
                incomplete.update(native_ordinals)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as error:
        code = str(error) if str(error).startswith("blast_sequence_database_") else "blast_sequence_database_native_row_validation_unavailable"
        _issue(issues, key, code, reason=str(error))
        return None, index, incomplete, native_ordinals
    if (not isinstance(search["row_map"], list) or search["row_map"] != expected_maps
            or normalized["hits"] != expected_hits):
        # Never assign a plausible source pointer to a row that did not come
        # from that original native ordinal. The complete input stays retained.
        _issue(issues, key, "blast_sequence_database_row_map_or_normalized_rows_conflict")
        return None, index, incomplete, native_ordinals
    normalized["source_locator"] = _locator(source, key, fmt)
    for component_index, (hit, mapping) in enumerate(zip(normalized["hits"], expected_maps)):
        h = hit["hit_index"]
        rows = mapping["hsp_ordinals"] if fmt == "tabular" else None
        lines = [search["native"]["line_numbers"][j] for j in rows] if rows is not None else None
        hit["source_locator"] = _locator(source, key, fmt, hit=h, rows=rows, lines=lines)
        item = dict(component_index=component_index, row_key=_row_key(key, h), source_locator=deepcopy(hit["source_locator"]), hsps=[], descriptions=[])
        index["hits"].append(item)
        for field, map_name in (("hsps", "hsp_ordinals"), ("descriptions", "description_ordinals")):
            for compact, (row, ordinal) in enumerate(zip(hit[field], mapping[map_name])):
                selected_rows = None
                if fmt == "tabular":
                    if field == "hsps":
                        selected_rows = [ordinal]
                    else:
                        selected_rows = []
                        for j in mapping["hsp_ordinals"]:
                            raw = search["native"]["search"]["rows"][j]
                            _, descriptions, _ = _reader._tab_descriptions(raw["fields"], [], raw["line"])
                            if row in descriptions:
                                selected_rows.append(j)
                    if not selected_rows:
                        _issue(issues, key, "blast_sequence_database_description_row_membership_unavailable", hit=h, description_ordinal=ordinal)
                        continue
                row_lines = [search["native"]["line_numbers"][j] for j in selected_rows] if selected_rows is not None else None
                row["source_locator"] = _locator(source, key, fmt, hit=h,
                    hsp=ordinal if field == "hsps" else None, description=ordinal if field == "descriptions" else None,
                    rows=selected_rows, lines=row_lines)
                item[field].append(dict(component_index=compact, row_key=_row_key(key, h,
                    hsp=ordinal if field == "hsps" else None, description=ordinal if field == "descriptions" else None),
                    source_locator=deepcopy(row["source_locator"])))
    return normalized, index, incomplete, native_ordinals


def _links(sheet, field, issues):
    key, result = sheet["search"]["search_key"], []
    for ordinal, link in enumerate(sheet[field]):
        if link["search_key"] != key:
            _issue(issues, key, "blast_sequence_database_link_search_key_mismatch", binding_kind=field, binding_index=ordinal,
                   supplied_search_key=link["search_key"])
        else:
            result.append(deepcopy(link["binding"]))
    return result


def _qualify_references(normalized, geometry, descriptions, sequences, issues, key, *, association_version=1):
    legacy_issues = []
    report, hits, _, _, _ = _explicit_inputs(normalized, descriptions, sequences, legacy_issues)
    links = _sequence_links(sequences, normalized, report, hits, legacy_issues, geometry_program=geometry,
                            association_version=association_version)
    for issue in legacy_issues:
        _issue(issues, key, issue["code"], hit=issue.get("hit_index"), original_issue=issue)
    result = []
    for hit in normalized["hits"]:
        h, reported = hit["hit_index"], hit["length"]
        offered = [row for row in sequences if row.get("report_index") == key["report_index"] and row.get("hit_index") == h]
        valid = [row for _, row in links.get(h, [])]
        identities = {(row["digest"], row["molecule"], row["sequence_length"]) for row in valid}
        length = reported
        if offered:
            if len(valid) != len(offered) or len(identities) != 1:
                length = None
                _issue(issues, key, "blast_sequence_database_reference_length_unqualified", hit=h)
            else:
                length = next(iter(identities))[2]
        hit["length"] = length
        result.append(dict(row_key=_row_key(key, h), reported_length=reported, full_length=length,
                           coordinate_unit=PROGRAM_UNITS[geometry][1]))
    # The actual build repeats the binding checks against original native
    # reference lengths; callers below supply only already validated links.
    return result, [row for rows in links.values() for _, row in rows]


def _selected_coverage(database, axis, row_index, incomplete, native_ordinals, key, issues, common_by_hit):
    result, selection = [], axis["selected_interval"]
    hits = {row["hit_index"]: row for row in database["hits"]}
    for h in native_ordinals:
        hit = hits.get(h)
        denominator = interval_length(selection)
        numerator, complete, reason = None, False, "invalid_native_row" if hit is None else None
        if hit is not None:
            selected = common_by_hit[h]["selected"]["query"]
            numerator, denominator = selected["observed_numerator"], selected["denominator"]
            complete = selected["complete_for_original_rows"]
            if axis["full_length"] is None or selection is None:
                reason = ("incompatible_input" if any(issue["code"] == "blast_sequence_database_query_axis_incompatible"
                          for issue in issues) else "missing_input")
            elif not complete:
                reason = ("partial_output" if numerator is not None or h in incomplete else "incompatible_input"
                          if any(c.get("traceback_available") is True for c in hit["hsp_components"])
                          else "not_measured")
        result.append(dict(row_key=_row_key(key, h), numerator=numerator, denominator=denominator,
            value=common_by_hit[h]["selected"]["query"]["complete_value"] if hit is not None else None,
            unit="fraction", complete_for_reported_hsps=complete, unavailable_reason=reason))
    return result


def calculate_blast_sequence_database_components(sheet, *, model=None, _retain_correspondence=False) -> dict:
    """Recalculate supplied sheets; source identity and execution never change."""
    if type(_retain_correspondence) is not bool:
        raise ValueError("blast_sequence_database_private_retention_flag_invalid")
    sheet = _copy(sheet)
    _validate(sheet)
    # Validate model shape/numbers even when native context later proves unusable.
    if model is not None:
        model = _copy(model)
        if not isinstance(model, dict) or set(model) - {"temperature_bits", "function_priors"}:
            raise ValueError("blast_probability_model_parameters_invalid")
        temperature = model.get("temperature_bits", 1)
        if type(temperature) not in (int, float) or temperature <= 0:
            raise ValueError("positive_finite_temperature_bits_required")
        priors = model.get("function_priors")
        if priors is not None and (not isinstance(priors, dict) or not priors or
                any(not _text(k) or type(v) not in (int, float) or v < 0 for k, v in priors.items()) or sum(priors.values()) <= 0):
            raise ValueError("complete_nonnegative_function_priors_required")
    search, issues = sheet["search"], []
    key = search["search_key"]
    for issue in search["issues"]:
        _issue(issues, key, issue.get("code", "blast_sequence_database_native_issue"),
               pointer=issue.get("pointer", key["search_pointer"]), original_issue=issue)
    admitted = _admit(sheet, issues)
    geometry = search["program_context"]["geometry_program"] if admitted else None
    axis = _query_axis(sheet, geometry, issues)
    components = dict(database_sheet=None, function_weights=None,
        coordinate_context={"query": axis, "references": []}, selected_query_coverage=[],
        row_keys={"search": _row_key(key), "hits": []})
    output = dict(schema=COMPONENT_SCHEMA, search_key=deepcopy(key), status="incompatible", components=components, issues=issues)
    instances = []
    if _retain_correspondence:
        output["correspondence"] = {"version": ARTIFACT_SCHEMA, "instances": instances}
    if not admitted:
        if all(row["code"] not in ("blast_sequence_database_stage_incompatible", "blast_sequence_database_target_population_incompatible",
                "blast_sequence_database_member_digest_mismatch", "blast_sequence_database_search_binding_key_mismatch",
                "blast_sequence_database_program_context_incompatible", "blast_sequence_database_program_context_unresolved") for row in issues):
            output["status"] = "unavailable"
        return output
    normalized, row_index, incomplete, native_ordinals = _rows(sheet, issues)
    components["row_keys"] = row_index
    if normalized is None:
        if any(row["code"] in ("blast_sequence_database_table_layout_unavailable", "blast_sequence_database_native_row_validation_unavailable") for row in issues):
            output["status"] = "unavailable"
        return output
    descriptions = _links(sheet, "description_bindings", issues)
    sequences = _links(sheet, "sequence_identity_bindings", issues)
    association_version = 2 if sheet["schema"] in (SHEET_SCHEMA_V2, SHEET_SCHEMA_V3) else 1
    references, valid_sequences = _qualify_references(normalized, geometry, descriptions, sequences, issues, key,
                                                     association_version=association_version)
    components["coordinate_context"]["references"] = references
    normalized["query"]["length"] = axis["full_length"]
    qualifications = {row["row_key"]["hit_ordinal"]: {
        "native_reference_bound": row["reported_length"], "query_selection": axis["selected_interval"],
        "original_rows_complete": row["row_key"]["hit_ordinal"] not in incomplete} for row in references}
    qualification_diagnostics = {}
    database = _build_database_sheet(normalized, reference_metadata=sheet["reference_metadata"],
        target_context=sheet["target_context"], database_profile=sheet["database_profile"],
        description_bindings=descriptions, sequence_identity_bindings=valid_sequences,
        geometry_program=geometry, calculation_context={"reporting": search["reporting"], "database_identity": sheet["search_binding"]["database_identity"]},
        database_population_context=dict(schema="blast_database_population_context_v1", search_key=key,
            associations=sheet["database_population_associations"]) if sheet["schema"] == SHEET_SCHEMA_V3 else None,
        association_version=association_version, _qualifications=qualifications,
        _correspondence_instances=instances, _qualification_diagnostics=qualification_diagnostics)
    common_by_hit = {hit["hit_index"]: instance["components"] for hit, instance in zip(database["hits"], instances)}
    for instance in instances:
        instance["legacy_pointer"] = "/components/database_sheet" + instance["legacy_pointer"]
    # Preserve the supplied inner bindings as well as qualification failures.
    database["sequence_identity_bindings"] = sequences
    selected = axis["selected_interval"]
    for hit, row in zip(database["hits"], row_index["hits"]):
        h = hit["hit_index"]
        for compact, component in enumerate(hit["hsp_components"]):
            row_key = row["hsps"][compact]["row_key"]
            diagnostic = qualification_diagnostics[(h, compact)]
            for issue in diagnostic.get("issues", component.get("issues", [])):
                _issue(issues, key, issue["code"], hit=h, hsp=row_key["hsp_ordinal"],
                       pointer=row["hsps"][compact]["source_locator"]["pointer"], original_issue=issue)
            if diagnostic.get("outside_selection"):
                _issue(issues, key, "blast_sequence_database_coordinates_outside_selection", hit=h, hsp=row_key["hsp_ordinal"])
                incomplete.add(h)
        if h in incomplete:
            _issue(issues, key, "blast_sequence_database_native_hsp_set_incomplete", hit=h)
    for issue in database["issues"]:
        _issue(issues, key, issue["code"], hit=issue.get("hit_index"), original_issue=issue)
    components.update(database_sheet=database, function_weights=calculate_database_probabilities(database, model=model),
        selected_query_coverage=_selected_coverage(database, axis, row_index, incomplete, native_ordinals, key, issues, common_by_hit))
    reporting = search["reporting"]
    if (reporting["native_hit_array_present"] != search["normalized"]["search"]["hit_array_present"]
            or reporting["native_hit_count"] != search["normalized"]["search"]["reported_hit_count"]):
        _issue(issues, key, "blast_sequence_database_reporting_native_conflict", reporting=reporting)
    success = reporting["native_returncode"] == 0 and reporting["producer_complete"] is True
    if not success:
        _issue(issues, key, "blast_sequence_database_execution_completion_unqualified", reporting=reporting)
    if not database["hits"]:
        output["status"] = ("no_reported_hits" if success and reporting["native_hit_array_present"] is True
                            and reporting["native_hit_count"] == 0 and any(search["normalized"]["query"].get(field) is not None for field in ("id", "title"))
                            and search["normalized"]["search"]["hit_array_present"] is True
                            and search["normalized"]["search"]["reported_hit_count"] == 0
                            else "unavailable")
    else:
        output["status"] = "partial" if issues else "complete"
    return _copy(output)


__all__ = ["populate_blast_sequence_database_sheet", "calculate_blast_sequence_database_components",
           "SHEET_SCHEMA", "SHEET_SCHEMA_V2", "SHEET_SCHEMA_V3", "COMPONENT_SCHEMA"]
