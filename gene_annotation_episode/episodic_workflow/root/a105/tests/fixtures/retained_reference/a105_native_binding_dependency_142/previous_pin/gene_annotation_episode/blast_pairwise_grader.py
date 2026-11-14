"""Deterministic BLAST residue correspondence and pairwise scoring sheets.

These functions analyse already received results. They neither run BLAST nor
assign annotation credit. Coordinates in ``pairs`` are zero-based, half-open
intervals in the ORIGINAL operands (nt for translated operands, otherwise aa
or nt). Native HSP scores remain separate; alternative HSPs are never summed.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .blast_search import PROGRAM_UNITS


def _integer(value, field, issues, *, minimum=0):
    if value is None:
        return None
    if type(value) is not int or value < minimum:
        issues.append({"code": "invalid_integer", "field": field})
        return None
    return value


def _number(value, field, issues, *, minimum=None):
    if value is None:
        return None
    if (type(value) not in (int, float) or type(value) is float and not math.isfinite(value)
            or minimum is not None and value < minimum):
        issues.append({"code": "invalid_number", "field": field})
        return None
    return value


def _fraction(numerator, denominator):
    return numerator / denominator if numerator is not None and denominator else None


def _axis_geometry(hsp, *, prefix, length, coordinate_unit, alignment_unit,
                   issues, coordinate_convention="directional", symbols=None):
    """Validate one native axis and return oriented endpoints, width, direction.

    JSON2/JSON15 translated negative frames can report ascending bounds. Only
    that explicit convention and a valid negative frame orient traversal from
    the upper bound. Native endpoints are never rewritten. Supplied traceback
    symbols additionally validate the native span; absent symbols do not invent
    a traceback. This same endpoint arithmetic serves representation matching.
    """
    if coordinate_convention not in ("directional", "blast_json2"):
        raise ValueError("unsupported_blast_coordinate_convention")
    start = _integer(hsp.get(prefix + "_from"), prefix + "_from", issues, minimum=1)
    end = _integer(hsp.get(prefix + "_to"), prefix + "_to", issues, minimum=1)
    if start is None or end is None:
        issues.append({"code": "coordinate_endpoints_unavailable", "operand": prefix})
        return None
    width = 3 if coordinate_unit == "nt" and alignment_unit == "aa" else 1
    direction = 1 if end >= start else -1
    frame = hsp.get(prefix + "_frame")
    traversal_start, traversal_end = start, end
    if (coordinate_convention == "blast_json2" and width == 3
            and type(frame) is int and frame in (-3, -2, -1) and start < end):
        traversal_start, traversal_end, direction = end, start, -1
    if coordinate_unit == "aa" and direction < 0:
        issues.append({"code": "reverse_protein_coordinates", "operand": prefix})
        return None
    if symbols is not None:
        residues = sum(symbol != "-" for symbol in symbols)
        if abs(end - start) + 1 != residues * width:
            issues.append({"code": "traceback_coordinate_span_conflict", "operand": prefix,
                           "reported_span": abs(end - start) + 1,
                           "traceback_span": residues * width})
            return None
    if length is not None and max(start, end) > length:
        issues.append({"code": "coordinates_outside_operand", "operand": prefix})
        return None
    strand = hsp.get(prefix + "_strand")
    if strand is not None:
        if strand not in ("Plus", "Minus"):
            issues.append({"code": "invalid_strand", "operand": prefix})
            return None
        if start != end and (strand == "Plus") != (direction > 0):
            issues.append({"code": "strand_coordinate_conflict", "operand": prefix})
            return None
    if frame is not None:
        if type(frame) is not int:
            issues.append({"code": "invalid_frame", "operand": prefix})
            return None
        if width == 3:
            if frame not in (-3, -2, -1, 1, 2, 3):
                issues.append({"code": "invalid_translation_frame", "operand": prefix})
                return None
            if (frame > 0) != (direction > 0):
                issues.append({"code": "frame_coordinate_direction_conflict", "operand": prefix})
                return None
            phase = (traversal_start - 1) % 3 + 1 if direction > 0 else (
                (length - traversal_start) % 3 + 1 if length is not None else None)
            if phase is not None and phase != abs(frame):
                issues.append({"code": "frame_coordinate_phase_conflict", "operand": prefix})
                return None
    return traversal_start, traversal_end, width, direction


def _axis_positions(hsp, *, prefix, symbols, length, coordinate_unit,
                    alignment_unit, issues, coordinate_convention="directional"):
    """Map each nongap symbol to its explicit original-coordinate interval."""
    geometry = _axis_geometry(hsp, prefix=prefix, symbols=symbols, length=length,
        coordinate_unit=coordinate_unit, alignment_unit=alignment_unit, issues=issues,
        coordinate_convention=coordinate_convention)
    if geometry is None:
        return None
    start, _, width, direction = geometry
    cursor = start - 1 if direction > 0 else start
    positions = []
    for symbol in symbols:
        if symbol == "-":
            positions.append(None)
            continue
        positions.append((cursor, cursor + width) if direction > 0
                         else (cursor - width, cursor))
        cursor += direction * width
    return positions


def alignment_components(hsp: dict, *, program: str, query_length: int | None,
                         reference_length: int | None,
                         coordinate_convention: str = "directional") -> dict:
    """Calculate one HSP's numeric components without replacing its raw scores.

    With no traceback, reported alignment/identity counts remain usable, but
    residue correspondence and paired coverage remain unknown. With a valid
    traceback but invalid coordinates, column counts remain usable while
    coordinate-dependent cells remain unknown. Discrepant reported counts are
    retained separately from counts calculated from the actual strings.
    ``coordinate_convention`` identifies native endpoint semantics, not the
    execution resource: directional endpoints by default, or BLAST JSON2/15.
    """
    if coordinate_convention not in ("directional", "blast_json2"):
        raise ValueError("unsupported_blast_coordinate_convention")
    issues = []
    if not isinstance(hsp, dict):
        hsp = {}
        issues.append({"code": "hsp_object_required"})
    qlength = _integer(query_length, "query_length", issues, minimum=1)
    rlength = _integer(reference_length, "reference_length", issues, minimum=1)
    reported = {name: _integer(hsp.get(name), name, issues,
                              minimum=1 if name == "align_len" else 0)
                for name in ("align_len", "identity", "positive", "gaps")}
    length, identity_count, gaps = (reported[key] for key in ("align_len", "identity", "gaps"))
    percentages = {}
    for field in ("identity_percent", "query_coverage_percent", "query_subject_coverage_percent",
                  "query_unique_subject_coverage_percent"):
        value = _number(hsp.get(field), field, issues, minimum=0)
        if value is not None and value > 100:
            issues.append({"code": "percentage_outside_range", "field": field})
            value = None
        percentages[field] = value
    reported_identity_fraction = (percentages["identity_percent"] / 100
                                  if percentages["identity_percent"] is not None else None)
    valid_identity = identity_count
    for field in ("identity", "positive", "gaps"):
        if length is not None and reported[field] is not None and reported[field] > length:
            issues.append({"code": "reported_count_exceeds_alignment_length", "field": field})
            if field == "identity":
                valid_identity = None
    paired = length - gaps if length is not None and gaps is not None and gaps <= length else None
    if paired is not None and valid_identity is not None and valid_identity > paired:
        issues.append({"code": "reported_identity_exceeds_paired_columns"})
        valid_identity = None
    if paired is not None and reported["positive"] is not None and reported["positive"] > paired:
        issues.append({"code": "reported_positive_exceeds_paired_columns"})
    if (reported["positive"] is not None and identity_count is not None
            and reported["positive"] < identity_count):
        issues.append({"code": "reported_positive_below_identity"})
    result = {
        "native_scores": {name: _number(hsp.get(name), name, issues,
                                        minimum=0 if name == "evalue" else None)
                          for name in ("bit_score", "score", "evalue")},
        "reported_counts": reported,
        "reported_percentages": percentages,
        "counts": {"alignment_columns": length, "paired_columns": paired,
                   "identical_pairs": valid_identity, "query_gap_columns": None,
                   "reference_gap_columns": None},
        "fractions": {"query_paired_coverage": None, "reference_paired_coverage": None,
                      "paired_identity": _fraction(valid_identity, paired),
                      "alignment_identity": (_fraction(valid_identity, length)
                          if valid_identity is not None and length else reported_identity_fraction)},
        "denominators": {"query_length": qlength, "reference_length": rlength,
                         "paired_columns": paired, "alignment_columns": length},
        "coordinate_units": None,
        "traceback_available": False, "geometry_available": False,
        "pairs": [], "issues": issues,
    }
    if not isinstance(program, str) or program not in PROGRAM_UNITS:
        issues.append({"code": "unsupported_blast_program"})
        return result
    qunit, runit, aunit = PROGRAM_UNITS[program]
    result["coordinate_units"] = {"query": qunit, "reference": runit, "alignment": aunit}
    query, reference = hsp.get("qseq"), hsp.get("hseq")
    if query is None and reference is None:
        issues.append({"code": "traceback_not_reported"})
        return result
    if (not isinstance(query, str) or not isinstance(reference, str) or not query
            or len(query) != len(reference)
            or re.fullmatch(r"[A-Za-z*\-]+", query) is None
            or re.fullmatch(r"[A-Za-z*\-]+", reference) is None):
        issues.append({"code": "invalid_traceback_strings"})
        return result
    query, reference = query.upper(), reference.upper()
    if any(a == b == "-" for a, b in zip(query, reference)):
        issues.append({"code": "double_gap_alignment_column"})
        return result
    query_gaps, reference_gaps = query.count("-"), reference.count("-")
    pairs_count = sum(a != "-" and b != "-" for a, b in zip(query, reference))
    identical = sum(a == b and a != "-" for a, b in zip(query, reference))
    result["traceback_available"] = True
    result["counts"] = {"alignment_columns": len(query), "paired_columns": pairs_count,
                        "identical_pairs": identical, "query_gap_columns": query_gaps,
                        "reference_gap_columns": reference_gaps}
    result["fractions"].update(paired_identity=_fraction(identical, pairs_count),
                               alignment_identity=_fraction(identical, len(query)))
    result["denominators"].update(paired_columns=pairs_count, alignment_columns=len(query))
    computed = {"align_len": len(query), "identity": identical, "gaps": query_gaps + reference_gaps}
    for field, actual in computed.items():
        if reported[field] is not None and reported[field] != actual:
            issues.append({"code": "reported_count_traceback_conflict", "field": field,
                           "reported": reported[field], "calculated": actual})
    qpositions = _axis_positions(hsp, prefix="query", symbols=query, length=qlength,
                                coordinate_unit=qunit, alignment_unit=aunit, issues=issues,
                                coordinate_convention=coordinate_convention)
    rpositions = _axis_positions(hsp, prefix="hit", symbols=reference, length=rlength,
                                coordinate_unit=runit, alignment_unit=aunit, issues=issues,
                                coordinate_convention=coordinate_convention)
    if qpositions is None or rpositions is None:
        return result
    result["geometry_available"] = True
    for qpos, rpos, a, b in zip(qpositions, rpositions, query, reference):
        if qpos is not None and rpos is not None:
            result["pairs"].append({"query_start": qpos[0], "query_end": qpos[1],
                                    "reference_start": rpos[0], "reference_end": rpos[1],
                                    "identical": a == b})
    qcovered = sum(pair["query_end"] - pair["query_start"] for pair in result["pairs"])
    rcovered = sum(pair["reference_end"] - pair["reference_start"] for pair in result["pairs"])
    result["counts"].update(paired_query_positions=qcovered, paired_reference_positions=rcovered)
    result["fractions"].update(query_paired_coverage=_fraction(qcovered, qlength),
                               reference_paired_coverage=_fraction(rcovered, rlength))
    return result


def blast_hsp_column_correspondence(hsp: dict, *, program: str,
                                   query_length: int | None,
                                   reference_length: int | None,
                                   coordinate_convention: str = "directional") -> dict:
    """Expose every native column using the established HSP geometry checks.

    This view does not change the whole-HSP calculations above. Incomplete
    reported extent/midline additionally disqualifies positional correspondence
    here, as it does in the retained-HSP reader; readable string counts survive.
    Symbols preserve native case, while relationships compare uppercase symbols.
    Direction is derived only when the whole HSP has usable geometry. Native
    frame and strand remain distinct supplied facts, not inferred labels.
    """
    components = alignment_components(hsp, program=program,
        query_length=query_length, reference_length=reference_length,
        coordinate_convention=coordinate_convention)
    issues = deepcopy(components["issues"])
    traceback = components["traceback_available"]
    geometry = components["geometry_available"]
    if traceback:
        if ("align_len" in hsp and hsp["align_len"] is not None
                and (type(hsp["align_len"]) is not int
                     or hsp["align_len"] != len(hsp["qseq"]))):
            geometry = False
            issues.append({"code": "site_native_geometry_conflict", "field": "align_len"})
        midline = hsp.get("midline")
        if midline is not None and (type(midline) is not str or len(midline) != len(hsp["qseq"])):
            geometry = False
            issues.append({"code": "site_native_geometry_conflict", "field": "midline"})
        if any(item["code"] == "invalid_integer"
               and item.get("field") in ("query_length", "reference_length") for item in issues):
            geometry = False
    missing_traceback = isinstance(hsp, dict) and hsp.get("qseq") is None and hsp.get("hseq") is None
    result = {
        "traceback_status": "available" if traceback else "unavailable" if missing_traceback else "incompatible",
        "geometry_status": "available" if geometry else "unavailable" if missing_traceback else "incompatible",
        "native_scores": deepcopy(components["native_scores"]),
        "reported_counts": deepcopy(components["reported_counts"]),
        "reported_percentages": deepcopy(components["reported_percentages"]),
        "columns": [], "issues": issues,
    }
    if not traceback:
        return result
    query, reference = hsp["qseq"], hsp["hseq"]
    qunit, runit, aunit = PROGRAM_UNITS[program]
    qpositions = rpositions = [None] * len(query)
    directions = {}
    if geometry:
        # These are the SAME validated endpoint/frame arithmetic used above.
        qpositions = _axis_positions(hsp, prefix="query", symbols=query,
            length=query_length, coordinate_unit=qunit, alignment_unit=aunit, issues=[],
            coordinate_convention=coordinate_convention)
        rpositions = _axis_positions(hsp, prefix="hit", symbols=reference,
            length=reference_length, coordinate_unit=runit, alignment_unit=aunit, issues=[],
            coordinate_convention=coordinate_convention)
        for role, prefix, unit, length in (("query", "query", qunit, query_length),
                                         ("reference", "hit", runit, reference_length)):
            directions[role] = _axis_geometry(hsp, prefix=prefix, length=length,
                coordinate_unit=unit, alignment_unit=aunit, issues=[],
                coordinate_convention=coordinate_convention)[3]
    for column, (a, b, qpos, rpos) in enumerate(zip(query, reference, qpositions, rpositions)):
        row = {"column": column, "query_symbol": a, "reference_symbol": b,
               "query_interval": list(qpos) if qpos is not None else None,
               "reference_interval": list(rpos) if rpos is not None else None,
               "query_unit": qunit, "reference_unit": runit, "alignment_unit": aunit,
               "relationship": "query_gap" if a == "-" else "reference_gap" if b == "-"
                   else "identical" if a.upper() == b.upper() else "substituted"}
        for role, prefix in (("query", "query"), ("reference", "hit")):
            frame, strand = hsp.get(prefix + "_frame"), hsp.get(prefix + "_strand")
            direction = None
            if geometry:
                start, end = hsp[prefix + "_from"], hsp[prefix + "_to"]
                if start != end:
                    direction = directions[role]
                elif strand in ("Plus", "Minus"):
                    direction = 1 if strand == "Plus" else -1
                elif row[role + "_unit"] == "aa":
                    direction = 1
                # A single nt has identical bounds in either orientation. No
                # unreported strand is inferred merely from endpoint equality.
            row[role + "_direction"] = direction
            row[role + "_frame"] = frame if type(frame) is int else None
            row[role + "_strand"] = strand if strand in ("Plus", "Minus") else None
        result["columns"].append(row)
    return result


def _union_size(intervals):
    total, boundary = 0, -1
    for start, end in sorted(set(intervals)):
        total += max(0, end - max(start, boundary))
        boundary = max(end, boundary)
    return total


def _mapping_conflicts(pairs, axis):
    other = "reference" if axis == "query" else "query"
    active, conflicts = [], []
    ordered = sorted(enumerate(pairs), key=lambda item: (item[1][axis + "_start"],
                                                       item[1][axis + "_end"], item[0]))
    for index, row in ordered:
        active = [(i, previous) for i, previous in active
                  if previous[axis + "_end"] > row[axis + "_start"]]
        for i, previous in active:
            if (previous[axis + "_start"], previous[axis + "_end"],
                    previous[other + "_start"], previous[other + "_end"]) != (
                    row[axis + "_start"], row[axis + "_end"],
                    row[other + "_start"], row[other + "_end"]):
                conflicts.append({"code": "alternative_residue_mapping", "operand": axis,
                                  "pair_indices": [i, index]})
        active.append((index, row))
    return conflicts


def build_pairwise_sheet(result: dict) -> dict:
    """Preserve the pairwise input and populate per-HSP and union measurements.

    Union coverage is the fraction of positions appearing in ANY reported valid
    correspondence; it is not coverage of one selected global alignment. An
    aggregate identity fraction is unavailable when alternatives conflict.
    Missing HSP geometry makes the observed union incomplete, not zero evidence.
    """
    if not isinstance(result, dict) or result.get("schema") != "blast_normalized_result_v1":
        raise ValueError("normalized_blast_result_required")
    if result.get("mode") != "pairwise":
        raise ValueError("pairwise_blast_mode_required")
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("finite_json_blast_result_required") from error
    hits = result.get("hits")
    if not isinstance(hits, list) or len(hits) > 1:
        raise ValueError("single_pairwise_reference_required")
    query = result.get("query")
    search = result.get("search")
    if not isinstance(query, dict) or not isinstance(search, dict):
        raise ValueError("normalized_query_and_search_required")
    issues = deepcopy(result.get("issues", []))
    if not isinstance(issues, list):
        raise ValueError("normalized_issues_list_required")
    qlength = _integer(query.get("length"), "query_length", issues, minimum=1)
    hit = hits[0] if hits else None
    if hit is not None and not isinstance(hit, dict):
        raise ValueError("normalized_hit_object_required")
    rlength = _integer(hit.get("length") if hit else None, "reference_length", issues, minimum=1)
    native_hsps = hit.get("hsps", []) if hit else []
    if not isinstance(native_hsps, list):
        raise ValueError("normalized_hsp_list_required")
    rows = []
    convention = "blast_json2" if result.get("format") == "json2" else "directional"
    for index, native in enumerate(native_hsps):
        components = alignment_components(native, program=search.get("program"),
                                          query_length=qlength, reference_length=rlength,
                                          coordinate_convention=convention)
        rows.append({"hsp_index": index, "native": deepcopy(native), "components": components})
        issues.extend({**issue, "hsp_index": index} for issue in components["issues"])
    by_pair = {}
    signatures = {}
    for row in rows:
        keys = []
        for pair in row["components"]["pairs"]:
            key = tuple(pair[name] for name in ("query_start", "query_end", "reference_start", "reference_end"))
            keys.append(key)
            item = by_pair.setdefault(key, {"identity_values": set(), "hsp_indices": []})
            item["identity_values"].add(pair["identical"])
            if row["hsp_index"] not in item["hsp_indices"]:
                item["hsp_indices"].append(row["hsp_index"])
        if row["components"]["geometry_available"]:
            signatures.setdefault(tuple(sorted(keys)), []).append(row["hsp_index"])
    pairs, identity_conflicts = [], []
    for key, value in sorted(by_pair.items()):
        values = value["identity_values"]
        identical = next(iter(values)) if len(values) == 1 else None
        if identical is None:
            identity_conflicts.append({"code": "identity_at_correspondence_conflicts",
                                       "pair_index": len(pairs), "hsp_indices": value["hsp_indices"]})
        pairs.append({**dict(zip(("query_start", "query_end", "reference_start", "reference_end"), key)),
                      "identical": identical, "hsp_indices": value["hsp_indices"]})
    conflicts = identity_conflicts + _mapping_conflicts(pairs, "query") + _mapping_conflicts(pairs, "reference")
    qcovered = _union_size((row["query_start"], row["query_end"]) for row in pairs)
    rcovered = _union_size((row["reference_start"], row["reference_end"]) for row in pairs)
    mapped_count = sum(row["components"]["geometry_available"] for row in rows)
    complete = bool(rows) and mapped_count == len(rows)
    union = {
        "pairs": pairs,
        "counts": {"distinct_residue_pairs": len(pairs), "paired_query_positions": qcovered,
                   "paired_reference_positions": rcovered,
                   "identical_residue_pairs": sum(row["identical"] is True for row in pairs)
                       if pairs and not identity_conflicts else None,
                   "hsps_with_geometry": mapped_count, "hsps_without_geometry": len(rows) - mapped_count},
        "denominators": {"query_length": qlength, "reference_length": rlength,
                         "distinct_residue_pairs": len(pairs)},
        "fractions": {"query_paired_coverage": _fraction(qcovered, qlength) if mapped_count else None,
                      "reference_paired_coverage": _fraction(rcovered, rlength) if mapped_count else None,
                      "paired_identity": _fraction(sum(row["identical"] is True for row in pairs), len(pairs))
                          if pairs and not conflicts else None},
        "complete_for_reported_hsps": complete,
        "identical_mapping_hsp_groups": [indices for indices in signatures.values() if len(indices) > 1],
        "conflicts": conflicts,
        "meaning": "union_of_observed_correspondences_not_a_selected_global_alignment",
    }
    issues.extend(conflicts)
    if not hits:
        state = "no_reported_alignment" if search.get("hit_array_present") is True else "alignment_report_unavailable"
    elif not rows:
        state = "alignment_report_unavailable"
        issues.append({"code": "hit_hsps_unavailable"})
    else:
        state = "complete" if complete and not issues else "partial"
    return {
        "schema": "blast_pairwise_sheet_v1", "status": state,
        "input": deepcopy(result), "query": deepcopy(query),
        "reference": {"length": hit.get("length"),
                      "descriptions": deepcopy(hit.get("descriptions", [])),
                      "unpaired_metadata": deepcopy(hit.get("unpaired_metadata", {}))} if hit else None,
        "hsps": rows, "union": union, "issues": issues,
        "calculations": {
            "paired_identity": "identical_paired_columns / paired_columns",
            "alignment_identity": "identical_paired_columns / all_alignment_columns",
            "query_paired_coverage": "union_of_paired_query_positions / supplied_query_length",
            "reference_paired_coverage": "union_of_paired_reference_positions / reported_reference_length",
            "native_scores": "preserved_per_HSP_without_summing_alternative_or_overlapping_HSPs",
        },
    }


__all__ = ["alignment_components", "build_pairwise_sheet", "blast_hsp_column_correspondence"]
