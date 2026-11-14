"""Homology sheet envelopes and saved-sheet-only deterministic calculations.

BLAST geometry, pairwise union and conditional reference-function mathematics
are shared with the existing BLAST implementation. This module adds explicit
Homology custody/mode context, native table counts and separately named span
measurements. It assigns no annotation credit and makes no execution decisions.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .blast_database_grader import build_database_sheet, calculate_database_probabilities
from .blast_pairwise_grader import alignment_components, build_pairwise_sheet, _union_size
from .blast_search import PROGRAM_UNITS
from .bvbrc_homology_inputs import _diagnostic, _digest, _index, _pointer, _positive, _text


SCHEMA = "bvbrc_homology_sheet_v1"


def _pairwise_proof(parsed, query):
    binding = parsed["binding"]
    subject = binding.get("subject_binding")
    result = query.get("normalized_result")
    if (len(parsed["queries"]) != 1 or len(binding["query_bindings"]) != 1
            or query["query_binding_status"] != "validated" or result is None
            or not isinstance(subject, dict) or len(result["hits"]) > 1):
        return False
    if (not all(_text(subject.get(key)) for key in ("source_ref", "member_ref", "subject_ref"))
            or not _digest(subject.get("sequence_sha256")) or not _positive(subject.get("length"))
            or subject.get("molecule") != PROGRAM_UNITS[result["search"]["program"]][1]):
        return False
    membership = subject.get("database_membership")
    if (not isinstance(membership, dict) or type(membership.get("member_count")) is not int
            or membership["member_count"] != 1 or not _text(membership.get("source_ref"))
            or not _pointer(membership.get("pointer"))):
        return False
    members = binding["database_binding"].get("actual_database_members")
    if members is not None and (not isinstance(members, list) or len(members) != 1
            or not isinstance(members[0], dict) or members[0].get("identifier") != subject["member_ref"]):
        return False
    links = subject.get("native_hit_links")
    if not isinstance(links, list):
        return False
    valid_links = []
    for link in links:
        if not isinstance(link, dict) or set(link) != {"report_index", "hit_index", "description_index"}:
            return False
        if not all(_index(link[key]) for key in ("report_index", "hit_index", "description_index")):
            return False
        if link["report_index"] != query["report_index"]:
            return False
        matches = [hit for hit in result["hits"] if hit["hit_index"] == link["hit_index"]]
        if len(matches) != 1 or not any(desc["source_locator"]["description_index"] == link["description_index"]
                                      for desc in matches[0]["descriptions"]):
            return False
        valid_links.append(link)
    if result["hits"]:
        hit = result["hits"][0]
        if hit["length"] is not None and hit["length"] != subject["length"]:
            return False
        if not valid_links:
            return False
    return True


def build_homology_sheet(parsed: dict, *, metadata: dict) -> dict:
    if not isinstance(parsed, dict) or parsed.get("schema") != "bvbrc_homology_parse_v1":
        raise ValueError("homology_parse_required")
    if not isinstance(metadata, dict) or metadata.get("schema") != "bvbrc_homology_metadata_bindings_v1":
        raise ValueError("homology_metadata_bindings_required")
    json.dumps(parsed, allow_nan=False)
    json.dumps(metadata, allow_nan=False)
    binding = parsed["binding"]
    mode = binding.get("scientific_mode")
    if mode not in {"database_identification", "pairwise_correspondence"}:
        raise ValueError("homology_scientific_mode_invalid")
    output = {"schema": SCHEMA, "application_id": "Homology", "scientific_mode": mode,
        "binding": deepcopy(binding), "artifact_refs": [deepcopy(row["artifact"]) for row in parsed["artifacts"]],
        "queries": [], "artifact_statuses": deepcopy(parsed["artifacts"]),
        "diagnostics": deepcopy(parsed["diagnostics"] + metadata.get("diagnostics", []))}
    for query in parsed["queries"]:
        matches = [row for row in metadata.get("queries", []) if row.get("report_index") == query["report_index"]]
        operands = matches[0] if len(matches) == 1 else None
        row = {"report_index": query["report_index"], "source_locator": deepcopy(query["source_locator"]),
            "query_binding": deepcopy(query["query_binding"]), "query_binding_status": query["query_binding_status"],
            "status": query["status"], "normalized_result": deepcopy(query["normalized_result"]),
            "description_links": deepcopy(query["description_links"]), "metadata_bindings": deepcopy(operands),
            "unresolved_metadata": deepcopy(metadata.get("unresolved_metadata", [])) +
                deepcopy(operands.get("unresolved_metadata", []) if operands else []),
            "blast_sheet": None, "native_tabular_measurements": deepcopy(query["native_tabular_measurements"]),
            "diagnostics": deepcopy(query["diagnostics"] + (operands.get("diagnostics", []) if operands else []))}
        output["queries"].append(row)
        normalized = row["normalized_result"]
        if normalized is None:
            continue
        if mode == "pairwise_correspondence":
            if not _pairwise_proof(parsed, query):
                row["status"] = "unavailable"
                row["diagnostics"].append(_diagnostic("homology_pairwise_subject_membership_unproved", locator=row["source_locator"]))
                continue
            projection = deepcopy(normalized)
            projection["mode"] = "pairwise"
            projection["pairwise_binding"] = deepcopy(binding["subject_binding"])
            # Native database-backed target and original bytes remain untouched.
            if projection["hits"] and projection["hits"][0]["length"] is None:
                projection["hits"][0]["length"] = binding["subject_binding"]["length"]
                projection["hits"][0]["length_source"] = "verified_supplied_single_subject_binding"
            row["blast_sheet"] = build_pairwise_sheet(projection)
        else:
            if operands is None:
                row["status"] = "unavailable"
                row["diagnostics"].append(_diagnostic("homology_query_metadata_operands_unavailable", locator=row["source_locator"]))
                continue
            try:
                row["blast_sheet"] = build_database_sheet(normalized,
                    reference_metadata=operands["reference_metadata"], target_context=operands["target_context"],
                    database_profile=operands["database_profile"], description_bindings=operands["description_bindings"],
                    sequence_identity_bindings=operands["sequence_identity_bindings"])
            except (ValueError, TypeError) as error:
                row["status"] = "unavailable"
                row["diagnostics"].append(_diagnostic(str(error), locator=row["source_locator"]))
                continue
        if row["blast_sheet"].get("issues"):
            row["status"] = "partial"
        for issue in row["blast_sheet"].get("issues", []):
            row["diagnostics"].append(_diagnostic(issue["code"], locator={**row["source_locator"], **issue}))
        if mode == "database_identification":
            source_hits = {hit["hit_index"]: hit for hit in normalized["hits"]}
            for hit in row["blast_sheet"]["hits"]:
                native_hsps = source_hits[hit["hit_index"]]["hsps"]
                for hsp, component in zip(native_hsps, hit["hsp_components"]):
                    for issue in component["issues"]:
                        row["diagnostics"].append(_diagnostic(issue["code"], locator=hsp["source_locator"]))
                        row["status"] = "partial"
    return output


def _span(hsp, prefix, length, unit):
    start, end = hsp.get(prefix + "_from"), hsp.get(prefix + "_to")
    if not _positive(start) or not _positive(end) or unit == "aa" and end < start:
        return None
    if length is not None and (not _positive(length) or max(start, end) > length):
        return None
    strand = hsp.get(prefix + "_strand")
    if strand is not None and (strand not in {"Plus", "Minus"} or
            start != end and (strand == "Plus") != (end >= start)):
        return None
    return [min(start, end) - 1, max(start, end)]


def _quantity(value, *, source, operands, unit, denominator=None, meaning=None):
    return {"value": value, "origin": source, "operands": operands, "unit": unit,
            "denominator": denominator, "uncertainty": None, "meaning": meaning}


def calculate_homology_alignment_supplements(sheet: dict) -> dict:
    if not isinstance(sheet, dict) or sheet.get("schema") != SCHEMA:
        raise ValueError("homology_sheet_required")
    output = {"schema": "bvbrc_homology_alignment_supplements_v1", "queries": []}
    for query in sheet["queries"]:
        row = {"report_index": query["report_index"], "source_locator": deepcopy(query["source_locator"]),
            "hits": [], "native_tabular_measurements": deepcopy(query["native_tabular_measurements"]),
            "original_supplied_coordinate_projection": "unavailable", "diagnostics": []}
        output["queries"].append(row)
        normalized = query["normalized_result"]
        if normalized is None:
            row["diagnostics"].append(_diagnostic("homology_normalized_measurements_unavailable", locator=query["source_locator"]))
            continue
        query_binding = query.get("query_binding")
        if query_binding and query_binding.get("sequence_transform", {}).get("kind") == "identity":
            row["original_supplied_coordinate_projection"] = "identity"
        elif query_binding:
            row["diagnostics"].append(_diagnostic("homology_original_coordinate_map_content_unavailable",
                locator=query["source_locator"], severity="qualification", required_input="supplied_coordinate_map_content"))
        program, qlength = normalized["search"]["program"], normalized["query"]["length"]
        qunit, runit, aunit = PROGRAM_UNITS[program]
        for hit in normalized["hits"]:
            rlength = hit["length"]
            hit_output = {"hit_index": hit["hit_index"], "source_locator": deepcopy(hit["source_locator"]), "hsps": [],
                          "span_union": {}, "qualifications": ["span_coverage_includes_positions_aligned_to_gaps"]}
            row["hits"].append(hit_output)
            spans = {"query": [], "reference": []}
            for saved_hsp_index, native_hsp in enumerate(hit["hsps"]):
                hsp = native_hsp if isinstance(native_hsp, dict) else {}
                components = alignment_components(hsp, program=program, query_length=qlength,
                    reference_length=rlength,
                    coordinate_convention="blast_json2" if normalized.get("format") == "json2" else "directional")
                counts = components["counts"]
                loc = deepcopy(hsp.get("source_locator"))
                if not isinstance(loc, dict) or not _index(loc.get("hsp_index")):
                    loc = {**hit["source_locator"], "pointer": None, "hsp_index": None}
                    row["diagnostics"].append(_diagnostic("homology_saved_hsp_locator_unavailable", locator=loc))
                operands = {"hsp": loc, "paired_columns": counts["paired_columns"], "identical_pairs": counts["identical_pairs"]}
                substitutions = (counts["paired_columns"] - counts["identical_pairs"]
                    if counts["paired_columns"] is not None and counts["identical_pairs"] is not None else None)
                item = {"hsp_index": loc["hsp_index"], "source_locator": loc,
                    "saved_hsp_index": saved_hsp_index,
                    "alignment_components": components,
                    "substitution_columns": _quantity(substitutions, source="derived", operands=operands,
                        unit=aunit + "_pair_columns", meaning="paired_columns - identical_pairs"),
                    "query_gap_runs": _quantity(len(re.findall(r"-+", hsp["qseq"])) if components["traceback_available"] else None,
                        source="derived", operands={"hsp": loc, "field": "qseq"}, unit="gap_events"),
                    "reference_gap_runs": _quantity(len(re.findall(r"-+", hsp["hseq"])) if components["traceback_available"] else None,
                        source="derived", operands={"hsp": loc, "field": "hseq"}, unit="gap_events"),
                    "spans": {}}
                for axis, prefix, length, unit in (("query", "query", qlength, qunit), ("reference", "hit", rlength, runit)):
                    interval = _span(hsp, prefix, length, unit)
                    spans[axis].append(interval)
                    span_length = interval[1] - interval[0] if interval is not None else None
                    item["spans"][axis] = {"interval": interval, "coordinate_convention": "zero_based_half_open",
                        "length": _quantity(span_length, source="derived", operands={"hsp": loc,
                            "from": hsp.get(prefix + "_from"), "to": hsp.get(prefix + "_to")}, unit=unit),
                        "coverage": _quantity(span_length / length if span_length is not None and _positive(length) else None,
                            source="derived", operands={"span_length": span_length}, unit="fraction", denominator=length,
                            meaning="endpoint_span_length / native_operand_length; not paired coverage")}
                hit_output["hsps"].append(item)
            for axis, length, unit in (("query", qlength, qunit), ("reference", rlength, runit)):
                intervals = spans[axis]
                valid = [value for value in intervals if value is not None]
                observed = _union_size(tuple(interval) for interval in valid) if valid else None
                complete = bool(intervals) and len(valid) == len(intervals)
                hit_output["span_union"][axis] = {"intervals": valid, "complete_for_reported_hsps": complete,
                    "observed_positions": _quantity(observed, source="derived", operands={"intervals": valid}, unit=unit),
                    "coverage": _quantity(observed / length if complete and _positive(length) else None,
                        source="derived", operands={"observed_union_positions": observed}, unit="fraction", denominator=length,
                        meaning="union of validated endpoint spans / native operand length; not paired coverage")}
    return output


def calculate_homology_scores(sheet: dict, *, database_model: dict | None = None) -> dict:
    if not isinstance(sheet, dict) or sheet.get("schema") != SCHEMA:
        raise ValueError("homology_sheet_required")
    if sheet["scientific_mode"] == "pairwise_correspondence" and database_model is not None:
        raise ValueError("homology_database_model_unused_for_pairwise")
    output = {"schema": "bvbrc_homology_scores_v1", "scientific_mode": sheet["scientific_mode"],
              "queries": [], "alignment_supplements": calculate_homology_alignment_supplements(sheet)}
    for query in sheet["queries"]:
        row = {"report_index": query["report_index"], "source_locator": deepcopy(query["source_locator"]),
            "status": query["status"], "conditional_function_weights": None, "pairwise_correspondence": None,
            "diagnostics": []}
        output["queries"].append(row)
        blast_sheet = query["blast_sheet"]
        if blast_sheet is None:
            row["diagnostics"].append(_diagnostic("homology_blast_sheet_unavailable", locator=query["source_locator"]))
        elif sheet["scientific_mode"] == "database_identification":
            try:
                row["conditional_function_weights"] = calculate_database_probabilities(blast_sheet, model=database_model)
            except (ValueError, TypeError, KeyError) as error:
                # One query's candidate set can differ from another's. Never
                # silently trim supplied priors or lose valid other queries.
                row["status"] = "unavailable"
                row["diagnostics"].append(_diagnostic(str(error), locator=query["source_locator"]))
        else:
            row["pairwise_correspondence"] = {"hsps": deepcopy(blast_sheet["hsps"]), "union": deepcopy(blast_sheet["union"]),
                "meaning": "residue_correspondence; database E-value is not paired-sequence relevance"}
    return output


__all__ = ["build_homology_sheet", "calculate_homology_alignment_supplements", "calculate_homology_scores"]
