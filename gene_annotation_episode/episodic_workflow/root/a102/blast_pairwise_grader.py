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
from .alignment_correspondence import (
    ARTIFACT_SCHEMA, BASE_COUNT_NAMES, count_literal_alignment_columns,
    reported_column_measurements, total_gap_columns, interval_union_length,
    populate_correspondence_sheet, calculate_correspondence_components,
    _ratio as _fraction, _mapping_conflicts as _common_mapping_conflicts,
)


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


def _read_alignment_components(hsp: dict, *, program: str, query_length: int | None,
                         reference_length: int | None,
                         coordinate_convention: str = "directional") -> dict:
    """Calculate one HSP's numeric components without replacing its raw scores.

    Endpoint-span fractions use the validated inclusive native span divided by
    the full operand length in that operand's original nt/aa units. They do not
    require traceback, and remain separate from corresponding-position coverage.
    Frame/strand, bounds or endpoint conflicts make that axis's span unavailable;
    a string/span conflict disqualifies paired geometry, not independent endpoints.
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
    measured, count_issues = reported_column_measurements(alignment_columns=length,
        identical_positions=identity_count, positive_positions=reported["positive"], gap_columns=gaps)
    native_names = {"identical_positions": "identity", "positive_positions": "positive", "gap_columns": "gaps"}
    for issue in count_issues:
        issues.append({**issue, **({"field": native_names[issue["field"]]} if "field" in issue else {})})
    paired, valid_identity = measured["paired_positions"], measured["identical_positions"]
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
                      "query_span_coverage": None, "reference_span_coverage": None,
                      "paired_identity": None,
                      "alignment_identity": reported_identity_fraction},
        "denominators": {"query_length": qlength, "reference_length": rlength,
                         "paired_columns": paired, "alignment_columns": length},
        "coordinate_units": None,
        "endpoint_spans": {"query": None, "reference": None},
        "traceback_available": False, "geometry_available": False,
        "pairs": [], "issues": issues,
    }
    if not isinstance(program, str) or program not in PROGRAM_UNITS:
        issues.append({"code": "unsupported_blast_program"})
        return result
    qunit, runit, aunit = PROGRAM_UNITS[program]
    result["coordinate_units"] = {"query": qunit, "reference": runit, "alignment": aunit}
    for role, prefix, operand_length, unit in (("query", "query", qlength, qunit),
                                              ("reference", "hit", rlength, runit)):
        geometry = _axis_geometry(hsp, prefix=prefix, length=operand_length,
            coordinate_unit=unit, alignment_unit=aunit, issues=issues,
            coordinate_convention=coordinate_convention)
        if geometry is not None:
            start, end, width, direction = geometry
            interval = [min(start, end) - 1, max(start, end)]
            result["endpoint_spans"][role] = {"interval": interval, "positions": None,
                "unit": unit, "operand_length": operand_length, "direction": direction,
                "alignment_symbol_width": width}
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
    literal = count_literal_alignment_columns(query, reference)
    query_gaps, reference_gaps = literal["query_gap_columns"], literal["reference_gap_columns"]
    pairs_count, identical = literal["paired_positions"], literal["identical_positions"]
    result["traceback_available"] = True
    result["counts"] = {"alignment_columns": len(query), "paired_columns": pairs_count,
                        "identical_pairs": identical, "query_gap_columns": query_gaps,
                        "reference_gap_columns": reference_gaps}
    result["denominators"].update(paired_columns=pairs_count, alignment_columns=len(query))
    computed = {"align_len": literal["alignment_columns"], "identity": identical,
        "gaps": total_gap_columns(literal)}
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
    return result


def correspondence_sheet_from_blast_components(components, *, program,
        query_length=None, reference_length=None, source_keys=None,
        population=None, selected_intervals=None):
    """Project actual component cells into the source-neutral numerical sheet.

    Saved components supply their actual counts and mapped pairs.  No strings
    or native envelopes are reconstructed.  Span-axis denominators remain
    separate from qualified paired-axis denominators.
    """
    units = PROGRAM_UNITS.get(program) if isinstance(program, str) else None
    coordinate_units = (components[0].get("coordinate_units") if components else None)
    if coordinate_units is not None:
        units = tuple(coordinate_units[axis] for axis in ("query", "reference", "alignment"))
    units = units or (None, None, None)
    if components:
        query_length = components[0].get("denominators", {}).get("query_length", query_length)
        reference_length = components[0].get("denominators", {}).get("reference_length", reference_length)
    lengths = {"query": query_length, "reference": reference_length}
    rows = []
    for i, component in enumerate(components):
        counts = component["counts"]
        measured = {"alignment_columns": counts.get("alignment_columns"),
            "paired_positions": counts.get("paired_columns"),
            "identical_positions": counts.get("identical_pairs"),
            "query_gap_columns": counts.get("query_gap_columns"),
            "reference_gap_columns": counts.get("reference_gap_columns"),
            "query_aligned_positions": None, "reference_aligned_positions": None}
        spans = component.get("endpoint_spans") or {}
        row_lengths = {axis: component.get("denominators", {}).get(axis + "_length", lengths[axis])
            for axis in ("query", "reference")}
        widths = {axis: (3 if unit == "nt" and units[2] == "aa" else
            1 if unit is not None and unit == units[2] else None)
            for axis, unit in zip(("query", "reference"), units)}
        fallback = (component.get("fractions", {}).get("alignment_identity")
            if measured["identical_positions"] is None or not measured["alignment_columns"] else None)
        rows.append({"source_key": source_keys[i] if source_keys is not None else "/" + str(i),
            "measurement_input": {"kind": "validated_saved_counts",
                "basis": "traceback" if component.get("traceback_available") else "native_reported",
                "counts": measured}, "paired_lengths": row_lengths,
            "span_inputs": {axis: {"interval": deepcopy((spans.get(axis) or {}).get("interval")),
                "length": (spans[axis]["operand_length"] if spans.get(axis) is not None else row_lengths[axis])}
                for axis in ("query", "reference")},
            "geometry_available": component.get("geometry_available", False),
            "pairs": deepcopy(component.get("pairs", [])), "symbol_widths": widths,
            "reported_alignment_identity_fallback": fallback})
    return populate_correspondence_sheet(
        operands={"query": {"length": lengths["query"], "unit": units[0]},
            "reference": {"length": lengths["reference"], "unit": units[1]}, "alignment_unit": units[2]},
        rows=rows,
        population=population if population is not None else {"original_rows_complete": None,
            "execution_state": "unknown", "producer_state": "unknown", "explicit_zero_result": False},
        selected_intervals=selected_intervals if selected_intervals is not None else {"query": None, "reference": None})


def project_alignment_component(component, common):
    """Select common calculated cells into the unchanged legacy HSP shape."""
    result = deepcopy(component)
    counts = common["counts"]
    result["counts"] = {"alignment_columns": counts["alignment_columns"],
        "paired_columns": counts["paired_positions"], "identical_pairs": counts["identical_positions"],
        "query_gap_columns": counts["query_gap_columns"],
        "reference_gap_columns": counts["reference_gap_columns"]}
    if result["geometry_available"]:
        result["counts"].update(paired_query_positions=common["paired_units"]["query"],
            paired_reference_positions=common["paired_units"]["reference"])
    result["fractions"] = {name: common["fractions"][name] for name in (
        "query_paired_coverage", "reference_paired_coverage", "query_span_coverage",
        "reference_span_coverage", "paired_identity", "alignment_identity")}
    result["denominators"].update(paired_columns=counts["paired_positions"],
        alignment_columns=counts["alignment_columns"])
    for axis in ("query", "reference"):
        span = result.get("endpoint_spans", {}).get(axis)
        if span is not None:
            span["positions"] = common["span_positions"][axis]
    return result


def alignment_component_artifacts(hsp, *, program, query_length, reference_length,
        coordinate_convention="directional", qualification=None, _qualification_diagnostics=None):
    """Decode native geometry, apply factual qualifications, then calculate once."""
    component = _read_alignment_components(hsp, program=program, query_length=query_length,
        reference_length=reference_length, coordinate_convention=coordinate_convention)
    history, outside_selection = deepcopy(component["issues"]), False
    if qualification is not None:
        native_bound = qualification.get("native_reference_bound")
        if reference_length is None and native_bound is not None:
            checked = _read_alignment_components(hsp, program=program, query_length=query_length,
                reference_length=native_bound, coordinate_convention=coordinate_convention)
            if checked["geometry_available"] is False:
                component = checked
                history.extend(deepcopy(checked["issues"]))
                # This is the qualified INPUT length, before any ratio exists.
                component["denominators"]["reference_length"] = None
        selection = qualification.get("query_selection")
        endpoints = [hsp.get("query_from"), hsp.get("query_to")] if isinstance(hsp, dict) else []
        outside = (len(endpoints) == 2 and all(type(value) is int and value >= 1 for value in endpoints)
            and (min(endpoints) - 1 < selection[0] or max(endpoints) > selection[1])) if selection is not None else False
        if selection is not None and (outside or any(pair["query_start"] < selection[0]
                or pair["query_end"] > selection[1] for pair in component["pairs"])):
            outside_selection = True
            component["geometry_available"] = False
            component["pairs"] = []
            component["issues"].append({"code": "blast_sequence_database_coordinates_outside_selection"})
    if _qualification_diagnostics is not None:
        _qualification_diagnostics.update(issues=history, outside_selection=outside_selection)
    sheet = correspondence_sheet_from_blast_components([component], program=program,
        source_keys=[""])
    calculated = calculate_correspondence_components(sheet)
    return project_alignment_component(component, calculated["rows"][0]), sheet, calculated


def alignment_components(hsp: dict, *, program: str, query_length: int | None,
        reference_length: int | None, coordinate_convention: str = "directional") -> dict:
    """Legacy HSP view of the common correspondence sheet/calculator."""
    return alignment_component_artifacts(hsp, program=program, query_length=query_length,
        reference_length=reference_length, coordinate_convention=coordinate_convention)[0]


def blast_hsp_column_correspondence(hsp: dict, *, program: str,
                                   query_length: int | None,
                                   reference_length: int | None,
                                   coordinate_convention: str = "directional",
                                   precomputed_components: dict | None = None) -> dict:
    """Expose every native column using the established HSP geometry checks.

    This view does not change the whole-HSP calculations above. Incomplete
    reported extent/midline additionally disqualifies positional correspondence
    here, as it does in the retained-HSP reader; readable string counts survive.
    Symbols preserve native case, while relationships compare uppercase symbols.
    Direction is derived only when the whole HSP has usable geometry. Native
    frame and strand remain distinct supplied facts, not inferred labels.
    """
    # Host readers can supply the component from the explicitly bound retained
    # artifact. The selected-column parser validates that source/operand binding.
    components = (deepcopy(precomputed_components) if precomputed_components is not None
        else alignment_components(hsp, program=program,
        query_length=query_length, reference_length=reference_length,
        coordinate_convention=coordinate_convention))
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
    return interval_union_length(intervals)


def _mapping_conflicts(pairs, axis):
    return _common_mapping_conflicts(pairs, axis)


def project_blast_union(common, *, query_length, reference_length):
    """Rename the common calculated union without changing its population."""
    pairs = [{**{key: deepcopy(value) for key, value in pair.items() if key != "row_indices"},
        "hsp_indices": deepcopy(pair["row_indices"])} for pair in common["pairs"]]
    conflicts = [{**{key: deepcopy(value) for key, value in item.items() if key != "row_indices"},
        **({"hsp_indices": deepcopy(item["row_indices"])} if "row_indices" in item else {})}
        for item in common["conflicts"]]
    counts, fractions = common["counts"], common["fractions"]
    return {"pairs": pairs, "counts": {
        "distinct_residue_pairs": counts["distinct_residue_pairs"],
        "paired_query_positions": counts["query_paired_positions"],
        "paired_reference_positions": counts["reference_paired_positions"],
        "identical_residue_pairs": counts["identical_residue_pairs"],
        "hsps_with_geometry": counts["rows_with_geometry"],
        "hsps_without_geometry": counts["rows_without_geometry"]},
        "denominators": {"query_length": query_length, "reference_length": reference_length,
            "distinct_residue_pairs": counts["distinct_residue_pairs"]},
        "fractions": {"query_paired_coverage": fractions["query_observed_coverage"],
            "reference_paired_coverage": fractions["reference_observed_coverage"],
            "paired_identity": fractions["paired_identity"]},
        "complete_for_reported_hsps": common["complete_for_supplied_rows"],
        "identical_mapping_hsp_groups": deepcopy(common["identical_mapping_row_groups"]),
        "conflicts": conflicts,
        "meaning": "union_of_observed_correspondences_not_a_selected_global_alignment"}


def build_pairwise_artifacts(result: dict, *, population=None, selected_intervals=None):
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
        if "hsp_source_map" in hit:
            rows[-1]["source_address"] = deepcopy(hit["hsp_source_map"][index])
        issues.extend({**issue, "hsp_index": index} for issue in components["issues"])
    common_sheet = correspondence_sheet_from_blast_components(
        [row["components"] for row in rows], program=search.get("program"),
        query_length=qlength, reference_length=rlength,
        source_keys=["/hsps/" + str(i) + "/components" for i in range(len(rows))],
        population=population, selected_intervals=selected_intervals)
    common_components = calculate_correspondence_components(common_sheet)
    for row, common in zip(rows, common_components["rows"]):
        row["components"] = project_alignment_component(row["components"], common)
    union = project_blast_union(common_components["union"], query_length=qlength, reference_length=rlength)
    conflicts, complete = union["conflicts"], union["complete_for_reported_hsps"]
    issues.extend(conflicts)
    if not hits:
        state = "no_reported_alignment" if search.get("hit_array_present") is True else "alignment_report_unavailable"
    elif not rows:
        state = "alignment_report_unavailable"
        issues.append({"code": "hit_hsps_unavailable"})
    else:
        state = "complete" if complete and not issues else "partial"
    sheet = {
        "schema": "blast_pairwise_sheet_v1", "status": state,
        "input": deepcopy(result), "query": deepcopy(query),
        "reference": {"length": hit.get("length"),
                      "descriptions": deepcopy(hit.get("descriptions", [])),
                      "unpaired_metadata": deepcopy(hit.get("unpaired_metadata", {}))} if hit else None,
        "hsps": rows, "union": union, "issues": issues,
        "calculations": {
            "paired_identity": "identical_paired_columns / paired_columns",
            "alignment_identity": "identical_paired_columns / all_alignment_columns",
            "query_span_coverage": "validated_native_query_endpoint_span / supplied_query_length; per HSP, original units",
            "reference_span_coverage": "validated_native_reference_endpoint_span / reported_reference_length; per HSP, original units",
            "query_paired_coverage": "union_of_paired_query_positions / supplied_query_length",
            "reference_paired_coverage": "union_of_paired_reference_positions / reported_reference_length",
            "native_scores": "preserved_per_HSP_without_summing_alternative_or_overlapping_HSPs",
        },
    }
    return sheet, common_sheet, common_components


def build_pairwise_sheet(result: dict) -> dict:
    return build_pairwise_artifacts(result)[0]


def validate_blast_correspondence_instance(legacy, instance, *, program=None):
    """Compare stored common inputs and projections, without HSP recalculation."""
    from .alignment_correspondence import _same
    sheet, calculated = instance["sheet"], instance["components"]
    if legacy.get("schema") == "blast_pairwise_sheet_v1":
        components = [row["components"] for row in legacy["hsps"]]
        program = legacy["input"]["search"].get("program")
        lengths = legacy["union"]["denominators"]
        keys = ["/hsps/" + str(i) + "/components" for i in range(len(components))]
        if not _same(legacy["union"], project_blast_union(calculated["union"],
                query_length=lengths["query_length"], reference_length=lengths["reference_length"])):
            raise ValueError("blast_saved_correspondence_union_conflict")
        if "selected_operand_coverage" in legacy:
            expected = {axis: {"numerator": calculated["selected"][axis]["execution_qualified_numerator"],
                "denominator": calculated["selected"][axis]["denominator"],
                "value": calculated["selected"][axis]["execution_qualified_value"], "unit": "fraction"}
                for axis in ("query", "reference")}
            if not _same(expected, legacy["selected_operand_coverage"]):
                raise ValueError("blast_saved_correspondence_selection_conflict")
    elif "hsp_components" in legacy and "measurements" in legacy:
        components = legacy["hsp_components"]
        lengths = {axis + "_length": sheet["operands"][axis]["length"] for axis in ("query", "reference")}
        keys = ["/hsp_components/" + str(i) for i in range(len(components))]
        union, measured = calculated["union"], legacy["measurements"]
        counts, fractions = union["counts"], union["fractions"]
        expected = {"hsp_count": counts["supplied_rows"],
            "traceback_complete": union["complete_for_supplied_rows"] and sheet["population"]["original_rows_complete"] is True,
            "observed_paired_query_positions": counts["query_paired_positions"] if union["position_counts_available"] else None,
            "observed_paired_reference_positions": counts["reference_paired_positions"] if union["position_counts_available"] else None,
            "query_paired_coverage": fractions["query_original_complete_coverage"],
            "reference_paired_coverage": fractions["reference_original_complete_coverage"],
            "unique_pair_count": counts["distinct_position_identity_pairs"] if union["position_counts_available"] else None,
            "identical_unique_pair_count": counts["identical_position_identity_pairs"] if union["position_counts_available"] else None,
            "overlap_pair_representations": counts["overlap_pair_representations"] if union["position_counts_available"] else None}
        if not _same(expected, {key: measured[key] for key in expected}):
            raise ValueError("blast_saved_correspondence_hit_conflict")
    else:
        components, keys = [legacy], [""]
        lengths = legacy["denominators"]
    expected_sheet = correspondence_sheet_from_blast_components(components, program=program,
        query_length=lengths["query_length"], reference_length=lengths["reference_length"], source_keys=keys,
        population=sheet["population"], selected_intervals=sheet["selected_intervals"])
    if not _same(expected_sheet, sheet):
        raise ValueError("blast_saved_correspondence_input_conflict")
    for component, common in zip(components, calculated["rows"]):
        if "denominators" in component and not _same(component, project_alignment_component(component, common)):
            raise ValueError("blast_saved_correspondence_hsp_conflict")


__all__ = ["alignment_components", "build_pairwise_sheet", "blast_hsp_column_correspondence"]
