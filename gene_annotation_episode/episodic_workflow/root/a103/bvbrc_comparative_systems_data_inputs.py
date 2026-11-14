"""Pure extraction of explicitly supplied ComparativeSystems Data populations.

All native row occurrences and Data cell states survive. Native query totals,
retained occurrences and locally included unique records are distinct counts.
This module neither authenticates host possession nor reads Store, discovers a
source, acquires a page, invokes a model/process, or calculates scientific ratios.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json

from .acquisition import SourceSnapshot
from .bvbrc_data_fields import FIELD_REGISTRY
from .bvbrc_data_query import encode_native_query
from .bvbrc_data_readers import _decode_native_payload, parse_data_snapshot
from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, validate_shape
from .bvbrc_comparative_systems_data_contracts import (
    _require, _scalar_identifier, _scalar_string, validate_data_population_selection,
    validate_supplied_record_sets,
)

__all__ = ("extract_comparative_systems_data_inputs",)

_IDENTIFIERS = ("record_id", "genome_id", "feature_id", "patric_id", "pathway_id",
                "ec_number", "subsystem_id", "role_id", "plfam_id", "pgfam_id", "accession", "sequence_id")
_REQUIRED = {
    "genome": ("genome_id",),
    "genome_feature": ("feature_id", "genome_id", "plfam_id", "pgfam_id", "aa_length"),
    "pathway": ("id", "genome_id", "feature_id", "pathway_id", "ec_number"),
    "subsystem": ("id", "genome_id", "feature_id", "subsystem_id", "role_id"),
    "protein_family_ref": ("family_id", "family_type"),
    "pathway_ref": ("id", "pathway_id", "ec_number", "map_name", "map_type"),
    "subsystem_ref": ("id", "subsystem_id", "role_id"),
}
_DEFAULT_ROLE = {"genome": "genome_records", "genome_feature": "family_feature_records",
                 "pathway": "pathway_records", "subsystem": "subsystem_records",
                 "protein_family_ref": "family_reference", "pathway_ref": "pathway_reference",
                 "subsystem_ref": "subsystem_reference"}


def _codes(values):
    return list(dict.fromkeys(values))


def _same(left, right):
    return canonical_sha256(left) == canonical_sha256(right)


def _cell(value, population, *, state="available", method="record_occurrences", codes=(), refs=()):
    return {"state": state, "value": value if state == "available" else None, "unit": "record",
            "origin": "derived_supplied_records" if state == "available" else "unavailable",
            "population_id": population, "method_id": method, "input_refs": deepcopy(list(refs)),
            "uncertainty": None, "qualification_codes": _codes(codes)}


def _location(binding, *, row=None, field=None, column=None, pointer=""):
    return {"source_ref": binding["source_ref"], "raw_artifact_ref": binding["native_artifact_ref"],
            "document_id": None, "json_pointer": pointer,
            "table": "data_rows" if row is not None else None,
            "row_ordinal": row, "column_ordinal": column, "native_field": field}


def _diagnostic(code, selection, *, source=None, location=None, row=None, role=None):
    return {"code": code, "phase": "population", "document_id": None, "row_ordinal": row,
            "field": role, "source_refs": [source] if source else list(selection["source_refs"]),
            "locations": [] if location is None else [location], "affected_field_ids": [],
            "required_input_role": role}


def _requirement(code, selection, *, role=None):
    role = role or _DEFAULT_ROLE[selection["collection"]]
    return {"requirement_id": "data:" + selection["record_set_id"] + ":" + role + ":" + code,
            "code": code, "required_input_role": role, "document_id": None,
            "affected_field_ids": [], "source_refs": list(selection["source_refs"])}


class _Lexeme(str):
    """A JSON number's original spelling for lossless retained-field text."""


def _raw_text(value, *, nested=False, sorted_keys=False):
    if isinstance(value, _Lexeme):
        return str(value)
    if type(value) is str:
        return json.dumps(value, ensure_ascii=False) if nested else value
    if type(value) is list:
        return "[" + ",".join(_raw_text(item, nested=True, sorted_keys=sorted_keys) for item in value) + "]"
    if type(value) is dict:
        keys = sorted(value) if sorted_keys else value
        return "{" + ",".join(json.dumps(key, ensure_ascii=False) + ":" +
                              _raw_text(value[key], nested=True, sorted_keys=sorted_keys) for key in keys) + "}"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _pointer(value, pointer):
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            _require(token.isascii() and token.isdigit() and str(int(token)) == token and int(token) < len(value),
                     "snapshot_pointer_invalid")
            value = value[int(token)]
        else:
            _require(type(value) is dict and token in value, "snapshot_pointer_invalid")
            value = value[token]
    return value


def _check_input(wrapper, artifact_bytes):
    """Check supplied bytes/values, never infer that a host admitted them."""
    wrapper = validate_shape("QualifiedDataInputV1", wrapper)
    qualified, raw = wrapper["qualified_result"], wrapper["raw_binding"]
    binding, grading = qualified["binding"], qualified["grading"]
    prepared, parsed = grading["prepared"], grading["parse_result"]
    _require(raw["source_ref"] == binding["source_ref"] and raw["raw_artifact_ref"] == binding["native_artifact_ref"]
             and raw["bytes_key"] == raw["raw_artifact_ref"]
             and raw["sha256"] == binding["native_sha256"] == parsed["retained_native_sha256"], "raw_binding_mismatch")
    _require(binding["collection"] == prepared["effective_request"]["collection"], "binding_collection_mismatch")
    _require(grading["selector"]["page"] == prepared["page_selector"], "original_page_selection_mismatch")
    # Selector identity uses the existing host convention, not this module's
    # canonical hash: execution_contracts.digest is intentionally independent.
    from .execution_contracts import digest
    _require(binding["selector_sha256"] == digest(grading["selector"]), "original_selector_mismatch")
    try:
        expected = encode_native_query(prepared["original_request"],
            base_url=prepared["query_population"]["base_url"], page_selector=prepared["page_selector"])
    except ValueError as error:
        raise ValueError("comparative_systems_data_prepared_request_invalid:" + str(error)) from error
    _require(_same(expected, prepared), "prepared_request_mismatch")
    _require(_same(grading["input_bindings"], [item["binding"] for item in qualified["input_results"]]),
             "saved_input_bindings_mismatch")
    content = artifact_bytes.get(raw["bytes_key"])
    if content is None:
        return wrapper, None, None
    _require(type(content) is bytes, "native_bytes_required")
    _require(len(content) == raw["byte_count"] and hashlib.sha256(content).hexdigest() == raw["sha256"],
             "byte_identity_mismatch")
    sheet = parsed["sheet"]
    if sheet is None:
        _require(parsed["status"] == "failed" and bool(parsed["failures"]), "failed_parse_required")
        return wrapper, content, None
    custody, transport = sheet["custody"], sheet["transport"]
    _require(custody["native_sha256"] == raw["sha256"] and custody["prepared_sha256"] == canonical_sha256(prepared),
             "sheet_custody_mismatch")
    # Re-use the established reader to check native bytes against the supplied
    # sheet. The request and transport below are saved normalized facts, not a
    # reconstructed acquisition receipt or new host/authentication evidence.
    snapshot = SourceSnapshot(service="bvbrc_data", url=custody["requested_url"],
        request=deepcopy(prepared["effective_request"]), retrieved_at=custody["retrieved_at"],
        content=content, media_type=custody["media_type"], transport={
            "request": {key: deepcopy(prepared["native_request"][key]) for key in ("method", "url", "headers", "body")},
            "effective_url": custody["effective_url"], "automatic_redirects": False,
            "response": {"status": transport["http_status"], "body_complete": transport["body_complete"],
                         "headers": deepcopy(transport["headers"]), "failure_code": transport["failure_code"]}})
    checked = (parse_data_snapshot(snapshot, prepared=prepared)
               if custody["native_profile"] == "solr_json_envelope_v1" else
               _decode_native_payload(snapshot, prepared=prepared,
                                      qualified_request=sheet["qualification"]["request_matches"]))
    _require(_same(checked, parsed), "native_parse_correspondence_mismatch")
    # The established reader has already rejected duplicate keys/non-JSON
    # constants. Retain raw fields (including unselected/complex fields) with
    # exact number lexemes; normalized cell states still come from its sheet.
    payload = json.loads(content, parse_int=_Lexeme, parse_float=_Lexeme)
    return wrapper, content, payload


def _query_genomes(prepared):
    members = None
    for predicate in prepared["effective_request"]["filters"]:
        if predicate["field"] == "genome_id" and predicate["operator"] in ("eq", "in"):
            values = {predicate["value"]} if predicate["operator"] == "eq" else set(predicate["value"])
            members = values if members is None else members & values
    return members


def _selection_matches(selected, wrapper):
    qualified = wrapper["qualified_result"]
    prepared = qualified["grading"]["prepared"]
    effective = prepared["effective_request"]
    _require(effective["mode"] == "page" and effective["collection"] == selected["collection"],
             "selected_collection_or_mode_mismatch")
    _require(prepared["query_population"]["population_key"] == selected["query_population_key"],
             "selected_query_population_mismatch")
    _require(effective["fields"] == selected["selected_fields"] and effective["sort"] == selected["sort"],
             "selected_fields_or_sort_mismatch")
    genomes = _query_genomes(prepared)
    population = selected["declared_genome_population"]
    if selected["collection"] in ("genome", "genome_feature", "pathway", "subsystem"):
        if genomes is not None:
            _require(set(population["members"]) <= genomes, "declared_genome_query_mismatch")
            if population["completeness"] == "complete_for_declared_population":
                _require(set(population["members"]) == genomes, "declared_genome_query_mismatch")
        elif population["completeness"] == "complete_for_declared_population":
            _require(False, "declared_genome_query_unbound")


def _association(selected, binding, native, raw_row):
    if type(raw_row) is not dict:
        return None
    rid = selected["record_set_id"]
    identifiers = {field: _scalar_identifier(native, field) for field in _IDENTIFIERS}
    identifiers["record_id"] = native["native_id"] or None
    codes = []
    cells = {cell["field"]: cell for cell in native["cells"]}
    required = _REQUIRED[selected["collection"]]
    for field in required:
        cell = cells.get(field)
        if (field in ("plfam_id", "pgfam_id") and cell is not None
                and cell["presence"] in ("absent", "null")):
            continue
        if cell is None or cell["status"] != "valid":
            codes.append("missing_required_field")
        elif (cell["native_shape"] == "scalar" and cell["atoms"] and cell["atoms"][0]["kind"] == "string"
              and not (cell["atoms"][0]["string_value"] or "").strip()):
            # Empty family assignments are retained valid no-assignment cells.
            if field not in ("plfam_id", "pgfam_id"):
                codes.append("native_identifier_placeholder")
    if native["native_id"] is None:
        codes.append("native_identifier_placeholder")
    if native["status"] != "valid":
        codes.append("missing_required_field")
    if selected["collection"] == "genome_feature":
        lengths = [cell for cell in native["numerical_cells"] if cell["field"] == "aa_length"]
        if (len(lengths) != 1 or lengths[0]["status"] not in ("reported", "parsed_numeric_text")
                or lengths[0]["value"] is None or lengths[0]["value"] < 0):
            codes.append("numeric_token_invalid")
    active = _scalar_identifier(native, "active")
    if active not in ("active", "likely", "inactive"):
        active = None
    fields = []
    for column, (field, value) in enumerate(raw_row.items()):
        escaped = field.replace("~", "~0").replace("/", "~1")
        fields.append({"name": field, "raw_text": _raw_text(value),
                       "location": _location(binding, row=native["row_index"], field=field, column=column,
                                             pointer=native["native_path"] + "/" + escaped)})
    return {"association_id": "data:" + canonical_sha256([rid, binding["source_ref"], native["row_key"]]),
            "document_id": None, "record_set_id": rid, "table": "data_rows", "row_ordinal": native["row_index"],
            "identifiers": identifiers, "active_category": active, "fields": fields,
            "identity_status": "partial" if codes else "valid",
            "coordinate_convention": "one_based_inclusive" if selected["collection"] == "genome_feature"
                and any(field in cells for field in ("start", "end")) else "not_applicable",
            "qualification_codes": _codes(codes)}


def _extract_set(selected, inputs):
    rid, collection = selected["record_set_id"], selected["collection"]
    rows, pages, diagnostics, requirements, codes = [], [], [], [], []
    population_locations, row_positions = [], {}
    signatures, positions = {}, defaultdict(list)
    page_ok, missing_sources, scopes = [], [], set()
    http_failed = False
    relationship = selected["relationship_to_original_task"]
    if relationship == "later_selected_snapshot":
        codes.append("later_snapshot_not_original")
    if relationship == "original_execution_snapshot":
        relationship = "unverified"
        codes.append("data_input_binding_mismatch")
        requirements.append(_requirement("data_input_binding_mismatch", selected, role="original_genome_population"))
    genome_population = selected["declared_genome_population"]
    if (genome_population["completeness"] != "complete_for_declared_population"
            or genome_population["missing_members"] or genome_population["unresolved_members"]):
        codes.append("group_membership_unknown")
        requirements.append(_requirement("group_membership_unknown", selected, role="original_genome_population"))
    required_fields = set(_REQUIRED[collection])
    if selected["annotation_filter"] == "exact_PATRIC":
        required_fields.add("annotation")
        codes.append("annotation_filter_applied")
        if not FIELD_REGISTRY[collection]["fields"]["annotation"]["exact_filter_supported"]:
            diagnostics.append(_diagnostic("unsupported_server_filter", selected))
    missing_fields = required_fields - set(selected["selected_fields"])
    if missing_fields:
        codes.append("missing_required_field")
        requirements.append(_requirement("missing_required_field", selected))
    if selected["release"] is None and collection.endswith("_ref"):
        codes.append("reference_release_unknown")
    for source in selected["source_refs"]:
        if source not in inputs:
            missing_sources.append(source)
            continue
        wrapper, content, payload = inputs[source]
        _selection_matches(selected, wrapper)
        qualified = wrapper["qualified_result"]
        binding, grading = qualified["binding"], qualified["grading"]
        host = qualified["host_qualification"]
        scopes.add((host["run_id"], host["receiver_episode_id"], host["scope_sha256"]))
        sheet = grading["parse_result"]["sheet"]
        if content is None:
            missing_sources.append(source)
            continue
        if sheet is None:
            codes.append("data_input_unavailable")
            if any(item["code"] == "bvbrc_invalid_json_response" for item in grading["parse_result"]["failures"]):
                codes.append("outer_json_invalid")
            continue
        native_page = sheet["page"]
        evidence = {"kind": "unknown", "snapshot_id": None, "source_locations": []}
        for location in selected["snapshot_evidence"]["source_locations"]:
            if location["source_ref"] == source:
                _require(location["raw_artifact_ref"] == binding["native_artifact_ref"], "snapshot_artifact_mismatch")
                _pointer(payload, location["json_pointer"])
                evidence["source_locations"].append(deepcopy(location))
        good = (sheet["custody"]["native_profile"] == "solr_json_envelope_v1"
                and all(sheet["qualification"][key] for key in ("service_matches", "request_matches", "http_success",
                    "format_valid", "population_metadata_valid", "transport_complete"))
                and sheet["qualification"]["native_partial_results"] is not True)
        http_failed = http_failed or not sheet["qualification"]["http_success"]
        page_ok.append(good)
        if good and sheet["population"]["native_num_found_exact"] is True and native_page["response_start"] == 0 \
                and native_page["reported_total"] == native_page["returned_row_count"]:
            evidence = {"kind": "single_complete_response", "snapshot_id": None,
                        "source_locations": [_location(binding, pointer="/response")]}
        pages.append({"binding": deepcopy(binding), "requested_offset": native_page["requested_offset"],
                      "response_start": native_page["response_start"], "returned_row_count": native_page["returned_row_count"],
                      "reported_total": native_page["reported_total"], "num_found_exact": sheet["population"]["native_num_found_exact"],
                      "body_complete": sheet["transport"]["body_complete"],
                      "partial_results": sheet["qualification"]["native_partial_results"], "snapshot_evidence": evidence})
        if not sheet["transport"]["body_complete"]:
            codes.append("artifact_truncated")
        if not good:
            codes.append("population_incomplete")
        if not sheet["qualification"]["population_metadata_valid"]:
            codes.append("population_incompatible")
        native_rows = payload["response"]["docs"] if type(payload) is dict else payload
        population_locations.append(_location(binding, pointer="/response/docs" if type(payload) is dict else ""))
        query_genomes = _query_genomes(grading["prepared"])
        for native, raw_row in zip(sheet["rows"], native_rows, strict=True):
            association = _association(selected, binding, native, raw_row)
            genome = _scalar_identifier(native, "genome_id")
            if genome is not None and query_genomes is not None and genome not in query_genomes:
                codes.append("population_incompatible")
            annotation = _scalar_string(native, "annotation")
            filter_state = ("included" if selected["annotation_filter"] == "none" else "filter_undetermined"
                            if annotation is None else "included" if annotation == "PATRIC"
                            else "excluded_by_explicit_filter")
            row_codes = list(codes)
            if association is None or association["identity_status"] != "valid":
                row_codes.append("missing_required_field")
            if filter_state == "filter_undetermined":
                row_codes.append("missing_required_field")
            row = {"record_set_id": rid, "source_ref": source, "native_sha256": binding["native_sha256"],
                   "page_row_key": native["row_key"], "native_unique_key": native["native_id"] or None,
                   "native_row": deepcopy(native), "association": association,
                   "filter_state": filter_state, "duplicate_state": "unique", "qualification_codes": _codes(row_codes)}
            signatures[len(rows)] = _raw_text(raw_row, nested=True, sorted_keys=True)
            if native_page["response_start"] is not None:
                position = native_page["response_start"] + native["row_index"]
                positions[position].append(len(rows))
                row_positions[len(rows)] = position
            rows.append(row)
    _require(len(scopes) <= 1, "access_scope_mismatch")
    if missing_sources:
        codes.append("data_input_unavailable")
    if missing_sources or len(pages) != len(selected["source_refs"]):
        requirements.append(_requirement("data_input_unavailable", selected))
    by_id = defaultdict(list)
    for index, row in enumerate(rows):
        if row["native_unique_key"] is not None:
            by_id[row["native_unique_key"]].append(index)
    conflict = False
    for indices in by_id.values():
        if len(indices) < 2:
            continue
        differing = len({signatures[index] for index in indices}) > 1
        code = "duplicate_record_conflict" if differing else "duplicate_identical_representation"
        codes.append(code)
        for index in indices:
            row = rows[index]
            row["duplicate_state"] = "conflicting_repeat" if differing else "identical_repeat"
            row["qualification_codes"] = _codes(row["qualification_codes"] + [code])
            if differing and row["association"] is not None:
                row["association"]["identity_status"] = "conflicting"
                row["association"]["qualification_codes"] = _codes(row["association"]["qualification_codes"] + [code])
        observed_positions = {row_positions[index] for index in indices if index in row_positions}
        if differing or len(observed_positions) > 1:
            conflict = True
    for indices in positions.values():
        if len(indices) > 1:
            codes.append("page_overlap")
            if len({signatures[index] for index in indices}) > 1:
                conflict = True
    totals = {page["reported_total"] for page in pages if page["reported_total"] is not None}
    total = next(iter(totals)) if len(totals) == 1 else None
    if len(totals) > 1:
        conflict = True
    # Unique-key-only sorting can be checked directly using exact native IDs.
    # Composite sort fields can remain unselected; the preserved prepared
    # request proves its stable unique-key tie-breaker, not extra field values.
    unique_key = FIELD_REGISTRY[collection]["unique_key"]
    if len(selected["sort"]) == 1 and selected["sort"][0]["field"] == unique_key:
        ordered = [(position, rows[indices[0]]["native_unique_key"]) for position, indices in sorted(positions.items())]
        ids = [value for _, value in ordered if value is not None]
        if ids != sorted(ids, reverse=selected["sort"][0]["direction"] == "desc"):
            conflict = True
    if conflict:
        codes.append("population_incompatible")
    exact = bool(pages) and all(page["num_found_exact"] is True and page["reported_total"] is not None for page in pages)
    consistent = bool(pages) and all(page_ok) and not conflict and "population_incompatible" not in codes
    # Compare interval endpoints, never allocate a list proportional to numFound.
    intervals = sorted((page["response_start"], page["response_start"] + page["returned_row_count"])
                       for page in pages if page["response_start"] is not None)
    end, gap = 0, False
    for start, stop in intervals:
        if start > end:
            gap = True
        if start < end and stop > start:
            codes.append("page_overlap")
        end = max(end, stop)
    if total is not None and end < total:
        gap = True
    if gap:
        codes.append("page_gap")
    if conflict or "population_incompatible" in codes:
        coverage = "incompatible"
    elif consistent and exact and not gap and end == total and len(pages) == len(selected["source_refs"]):
        coverage = "complete"
    elif not pages or total is None or not exact:
        coverage = "unknown"
    else:
        coverage = "partial"
    # A repeated response is still retained as another occurrence. It is not
    # a second independent snapshot or an extra covered interval.
    response_identities = {(page["binding"]["native_sha256"], page["requested_offset"]) for page in pages}
    single = len(response_identities) == 1 and bool(pages)
    snapshot = "conflicting" if conflict else "single_response" if single else "unknown"
    if snapshot == "unknown" and pages:
        codes.append("snapshot_consistency_unknown")
        requirements.append(_requirement("snapshot_consistency_unknown", selected))
    if selected["snapshot_evidence"]["kind"] == "immutable_snapshot":
        codes.append("snapshot_consistency_unknown")
        requirements.append(_requirement("snapshot_consistency_unknown", selected))
    invalid_rows = any(row["native_row"]["status"] != "valid" or row["filter_state"] == "filter_undetermined"
                       or row["association"] is None or row["association"]["identity_status"] != "valid" for row in rows)
    if invalid_rows or missing_fields:
        codes.append("missing_required_field")
        requirements.append(_requirement("missing_required_field", selected))
    completeness = ("incompatible" if coverage == "incompatible" else
                    "partial" if coverage == "partial" or invalid_rows or missing_fields else
                    "complete_for_declared_population" if coverage == "complete" and snapshot == "single_response" else "unknown")
    if completeness != "complete_for_declared_population":
        codes.append("population_incomplete")
        requirements.append(_requirement("population_incomplete", selected))
    codes = _codes(codes)
    refs = [{"kind": "supplied", "owner_id": rid, "pointer": "/rows/" + str(index)} for index in range(len(rows))]
    members = list(dict.fromkeys(row["native_unique_key"] for row in rows
        if row["filter_state"] == "included" and row["native_unique_key"] is not None
        and row["native_row"]["status"] == "valid" and row["duplicate_state"] != "conflicting_repeat"
        and row["association"] is not None and row["association"]["identity_status"] == "valid"))
    no_rows_state = "available" if pages else "missing" if missing_sources or not selected["source_refs"] else "failed"
    raw_count = _cell(len(rows), rid, state=no_rows_state, codes=codes, refs=refs)
    valid_count = _cell(len(members), rid, state=no_rows_state, method="distinct_valid_members", codes=codes, refs=refs)
    original_state = ("incompatible" if conflict or "population_incompatible" in codes else
                      "truncated" if "artifact_truncated" in codes else
                      "failed" if http_failed else
                      "available" if consistent and exact and total is not None else
                      "failed" if not pages and no_rows_state == "failed" else "missing")
    included = [row for row in rows if row["filter_state"] == "included"]
    local_state = ("incompatible" if any(row["duplicate_state"] == "conflicting_repeat" for row in included) else
                   "missing" if any(row["filter_state"] == "filter_undetermined" for row in rows)
                       or any(row["native_unique_key"] is None for row in included) else no_rows_state)
    result = {"record_set_id": rid, "collection": collection,
        "population": {"population_id": rid, "kind": "supplied_data_records", "member_kind": "record_id",
            "members": members, "source_locations": population_locations,
            "raw_occurrence_count": raw_count, "distinct_valid_member_count": valid_count,
            "completeness": completeness, "missing_members": [],
            "unresolved_members": [row["page_row_key"] for row in rows if row["native_unique_key"] is None],
            "relationship_to_original_task": relationship, "qualification_codes": codes},
        "pages": pages, "rows": rows, "annotation_filter": selected["annotation_filter"],
        "page_coverage": coverage, "snapshot_consistency": snapshot,
        "original_query_record_count": _cell(total, rid, state=original_state, method="native_field", codes=codes,
            refs=[{"kind": "supplied", "owner_id": rid, "pointer": "/pages/" + str(i) + "/reported_total"} for i in range(len(pages))]),
        "locally_included_record_count": _cell(len({row["native_unique_key"] for row in included}), rid,
            state=local_state, method="distinct_valid_members", codes=codes, refs=refs)}
    diagnostics.extend(_diagnostic(code, selected) for code in codes)
    return result, requirements, diagnostics


def extract_comparative_systems_data_inputs(qualified_inputs: tuple[dict, ...], *,
        artifact_bytes: dict[str, bytes], selection: dict) -> dict:
    """Extract selected supplied records and their explicitly qualified counts.

    ``original_query_record_count`` is the exact native broader query total
    when compatible; it is never the sum of page totals. ``raw_occurrence_count``
    counts every retained response row, including repeats/exclusions/invalids.
    ``locally_included_record_count`` counts distinct known record IDs passing
    the exact local filter among the acquired rows; it remains qualified when
    acquisition is partial, and is unavailable if filter/identity is unknown.
    ``distinct_valid_member_count`` counts the valid included record IDs only.
    None of these counts is a score, biological absence, or historical proof.
    """
    selected = validate_data_population_selection(selection)
    _require(type(qualified_inputs) is tuple, "qualified_input_tuple_required")
    _require(type(artifact_bytes) is dict and all(type(key) is str and type(value) is bytes
                                               for key, value in artifact_bytes.items()), "artifact_byte_map_required")
    allowed = {source for record_set in selected["record_sets"] for source in record_set["source_refs"]}
    inputs = {}
    for value in qualified_inputs:
        wrapper = validate_shape("QualifiedDataInputV1", value)
        source = wrapper["qualified_result"]["binding"]["source_ref"]
        _require(source in allowed, "source_not_selected")
        _require(source not in inputs, "duplicate_qualified_source")
        inputs[source] = _check_input(wrapper, artifact_bytes)
    result = {"version": "bvbrc_comparative_systems_supplied_records_v1", "selection": selected,
              "record_sets": [], "requirements": [], "diagnostics": []}
    for record_set in selected["record_sets"]:
        extracted, requirements, diagnostics = _extract_set(record_set, inputs)
        result["record_sets"].append(extracted)
        result["requirements"].extend(requirements)
        result["diagnostics"].extend(diagnostics)
    for name in ("requirements", "diagnostics"):
        result[name] = list({canonical_sha256(item): item for item in result[name]}.values())
    return validate_supplied_record_sets(result)
