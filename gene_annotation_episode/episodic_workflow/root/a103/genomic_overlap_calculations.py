"""Deterministic interval components from an immutable genomic-overlap sheet.

Every base count is in bp under exact-chromosome, zero-based half-open outer
span coordinates. Counts retain occurrence multiplicity; union quantities do
not. Ratios retain integer numerators/denominators and have no invented
statistical uncertainty. Parameters filter recorded native pairs by integer
cross-products; they never recover absent edges or repeat an overlap analysis.
"""
from __future__ import annotations

from copy import deepcopy

from .genomic_overlap_contracts import (
    Components, Parameters, Sheet, canonical_genomic_overlap_sheet_sha256,
    validate_genomic_overlap_record,
)
from .genomic_overlap_inputs import _failure, _unique_issues, _validate_sheet


def _union(intervals):
    """Merge actual retained intervals, partitioning by exact chromosome token."""
    merged = []
    for row in sorted(intervals, key=lambda row: (row["chromosome"].encode("utf-8"), row["start"], row["end"])):
        if merged and row["chromosome"] == merged[-1]["chromosome"] and row["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], row["end"])
        else:
            merged.append({key: row[key] for key in ("chromosome", "start", "end")})
    return merged


def _measure(intervals):
    return sum(row["end"] - row["start"] for row in intervals)


def _ratio(numerator, denominator, missing_reason=None):
    if numerator is None or denominator is None:
        if missing_reason is None:
            raise ValueError("genomic_overlap_missing_ratio_reason")
        value, reason = None, missing_reason
    elif denominator == 0:
        value, reason = None, "zero_denominator"
    else:
        if not 0 <= numerator <= denominator:
            raise ValueError("genomic_overlap_inconsistent_ratio_population")
        value, reason = numerator / denominator, None
    return {"numerator": numerator, "denominator": denominator, "value": value, "missing_reason": reason}


def _set_components(parsed):
    rows = parsed["regions"]
    complete = parsed["result_extent"] == "complete"
    union = _union(rows) if complete else None
    loci = len(parsed["coordinate_groups"]) if complete else None
    count = len(rows) if complete else None
    return {"set_key": parsed["set_key"], "result_extent": parsed["result_extent"],
        "input_data_row_count": parsed["input_data_row_count"], "valid_region_count": len(rows),
        "region_count": count, "summed_region_bp": sum(row["end"] - row["start"] for row in rows) if complete else None,
        "union_bp": _measure(union) if complete else None, "coordinate_locus_count": loci,
        "duplicate_coordinate_excess": count - loci if complete else None,
        "issues": deepcopy(parsed["issues"]), "union_segments": union,
        "region_geometry": [{"set_key": parsed["set_key"], "occurrence_key": row["occurrence_key"],
                             "span_bp": row["end"] - row["start"]} for row in rows]}


def _missing_reason(operands, extent):
    if any(row["result_extent"] == "unavailable" for row in operands):
        return "unavailable_input"
    if any(row["result_extent"] == "partial" for row in operands):
        return "incomplete_input"
    return "unavailable_native_result" if extent == "unavailable" else "incomplete_native_result"


def _selected(row, parameters):
    width, a, b = row["native_overlap_bp"], row["a"], row["b"]
    at, bt = parameters["minimum_a_fraction"], parameters["minimum_b_fraction"]
    return (width >= parameters["minimum_overlap_bp"] and
            width * at["denominator"] >= at["numerator"] * (a["end"] - a["start"]) and
            width * bt["denominator"] >= bt["numerator"] * (b["end"] - b["start"]))


def _edge(row, parameters):
    a, b, width = row["a"], row["b"], row["native_overlap_bp"]
    return {"pair_key": row["pair_key"], "a_set_key": a["set_key"], "a_occurrence_key": a["occurrence_key"],
        "b_set_key": b["set_key"], "b_occurrence_key": b["occurrence_key"],
        "intersection": {"chromosome": a["chromosome"], "start": max(a["start"], b["start"]),
                         "end": min(a["end"], b["end"])}, "overlap_bp": width,
        "a_overlap_fraction": _ratio(width, a["end"] - a["start"]),
        "b_overlap_fraction": _ratio(width, b["end"] - b["start"]), "selected": _selected(row, parameters)}


def _metrics(edges, *, complete, a, b, combined, reason, selected):
    shared = _measure(_union([row["intersection"] for row in edges])) if complete else None
    count = len(edges) if complete else None
    summed = sum(row["overlap_bp"] for row in edges) if complete else None
    acount = len({row["a_occurrence_key"] for row in edges}) if complete else None
    bcount = len({row["b_occurrence_key"] for row in edges}) if complete else None
    result = {"a_union_coverage_fraction": _ratio(shared, a["union_bp"], reason),
        "b_union_coverage_fraction": _ratio(shared, b["union_bp"], reason),
        "a_regions_with_overlap": acount, "b_regions_with_overlap": bcount,
        "a_region_overlap_fraction": _ratio(acount, a["region_count"], reason),
        "b_region_overlap_fraction": _ratio(bcount, b["region_count"], reason)}
    if selected:
        result.update(selected_pair_count=count, selected_pairwise_bp_sum=summed,
            selected_intersection_union_bp=shared, selected_shared_union_fraction=_ratio(shared, combined, reason))
    else:
        result.update(native_pair_count=count, pairwise_overlap_bp_sum=summed,
            intersection_union_bp=shared, combined_union_bp=combined, jaccard_bp=_ratio(shared, combined, reason))
    return result


def _measurement_failures(pair_key, pair_index, value, path, *, set_key=None, locator=None, artifact_ref=None):
    """Locate unavailable requested-capable cells without explanatory free text."""
    failures = []
    for field, item in value.items():
        if item is None or (type(item) is dict and "missing_reason" in item and item["value"] is None):
            zero = type(item) is dict and item["missing_reason"] == "zero_denominator"
            failures.append(_failure("zero_denominator" if zero else "requested_field_unavailable", "calculate",
                set_key=set_key, comparison_key=pair_key, artifact_ref=artifact_ref, locator=locator,
                field_path=f"/pairs/{pair_index}/{path}/{field}",
                observed_value=0 if zero else None,
                requirement="nonzero_denominator" if zero else "requested_selected_field"))
    return failures


def calculate_genomic_overlap_components(sheet: Sheet, *, parameters: Parameters) -> Components:
    """Calculate an independent numerical snapshot; never mutate the source sheet."""
    sheet = _validate_sheet(sheet)
    parameters = validate_genomic_overlap_record("Parameters", parameters)
    for name in ("minimum_a_fraction", "minimum_b_fraction"):
        if parameters[name]["numerator"] > parameters[name]["denominator"]:
            raise ValueError("genomic_overlap_fraction_threshold")
    set_components = [_set_components(value) for value in sheet["sets"]]
    components_by_key = {row["set_key"]: row for row in set_components}
    input_by_key = {row["set_key"]: row for row in sheet["sets"]}
    pairs = []
    for index, (comparison, parsed, reference) in enumerate(zip(sheet["request"]["comparisons"],
            sheet["comparisons"], sheet["reference_relations"])):
        key = comparison["comparison_key"]
        operands = [input_by_key[comparison[side + "_set_key"]] for side in ("a", "b")]
        a, b = [components_by_key[row["set_key"]] for row in operands]
        extent = parsed["result_extent"]
        complete = extent == "complete"
        reason = _missing_reason(operands, extent)
        edges = [_edge(row, parameters) for row in parsed["valid_pairs"]]
        selected = [row for row in edges if row["selected"]]
        union = _union([row["intersection"] for row in edges])
        selected_union = _union([row["intersection"] for row in selected])
        shared = _measure(union)
        combined = a["union_bp"] + b["union_bp"] - shared if complete else None
        inherited = _unique_issues(*(row["issues"] for row in operands), parsed["receipt"]["issues"],
                                  parsed["issues"], reference["issues"])
        # Byte/operand identity failures mean the saved rows cannot establish a
        # subset of the intended result. Keep rows/edges, but no lower-bound total.
        trusted = extent != "unavailable" and not any(issue["code"] in {
            "input_digest_mismatch", "artifact_digest_mismatch", "original_attempt_mismatch"} for issue in inherited)
        observed = {"observed_pair_count": len(edges) if trusted else None,
            "observed_pairwise_bp_sum": sum(row["overlap_bp"] for row in edges) if trusted else None,
            "observed_intersection_union_bp": shared if trusted else None,
            "interpretation": "exact_complete_result" if complete else "lower_bound_subset" if trusted else "unavailable"}
        unfiltered_metrics = _metrics(edges, complete=complete, a=a, b=b, combined=combined, reason=reason, selected=False)
        selected_metrics = _metrics(selected, complete=complete, a=a, b=b, combined=combined, reason=reason, selected=True)
        issues = list(inherited)
        for population, metrics in (("unfiltered", unfiltered_metrics), ("selected", selected_metrics), ("observed", observed)):
            issues.extend(_measurement_failures(key, index, metrics, population))
        occurrences = []
        for population, population_edges in (("unfiltered", edges), ("selected", selected)):
            # Each native edge contributes to exactly one occurrence on each
            # side. Build ordered joins once instead of scanning all edges for
            # every input occurrence (including the many no-hit occurrences).
            adjacency = {side: {} for side in ("a", "b")}
            for edge in population_edges:
                for side in ("a", "b"):
                    adjacency[side].setdefault(edge[side + "_occurrence_key"], []).append(edge)
            for side, operand in zip(("a", "b"), operands):
                for row in operand["regions"]:
                    attached = adjacency[side].get(row["occurrence_key"], [])
                    span = row["end"] - row["start"]
                    covered = _measure(_union([edge["intersection"] for edge in attached])) if complete else None
                    occurrence = {"comparison_key": key, "population": population, "set_key": operand["set_key"],
                        "occurrence_key": row["occurrence_key"], "span_bp": span,
                        "partner_count": len(attached) if complete else None, "covered_bp": covered,
                        "coverage_fraction": _ratio(covered, span, reason),
                        "pair_keys": [edge["pair_key"] for edge in attached], "result_extent": extent}
                    issues.extend(_measurement_failures(key, index,
                        {field: occurrence[field] for field in ("partner_count", "covered_bp", "coverage_fraction")},
                        f"occurrences/{len(occurrences)}", set_key=operand["set_key"], locator=row["locator"],
                        artifact_ref=operand["source_file"]["artifact_ref"]))
                    occurrences.append(occurrence)
        pairs.append({"comparison_key": key, "a_set_key": a["set_key"], "b_set_key": b["set_key"],
            "result_extent": extent, "reference_relation": reference["relation"], "observed": observed,
            "unfiltered": unfiltered_metrics, "selected": selected_metrics, "issues": _unique_issues(issues),
            "intersection_union_segments": union if complete else None,
            "selected_intersection_union_segments": selected_union if complete else None,
            "edges": edges, "occurrences": occurrences})
    result = {"version": "genomic_region_overlap_components_v1",
        "source_sheet_sha256": canonical_genomic_overlap_sheet_sha256(sheet), "parameters": parameters,
        "sets": set_components, "pairs": pairs,
        "issues": _unique_issues(sheet["issues"], *(row["issues"] for row in pairs))}
    return validate_genomic_overlap_record("Components", result)


__all__ = ["calculate_genomic_overlap_components"]
