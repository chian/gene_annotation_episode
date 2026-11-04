"""Deterministic calculations from populated Infernal cells, without parsing.

Span fractions describe inclusive coordinate spans. They are neither paired
residue coverage nor function-confidence probabilities. Native scores and
E-values are never summed; statistical independence is never inferred.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math

SCORE_SCHEMA = "infernal_search_scores_v1"


def _definition(inputs, formula, units, population, denominator=None, *, kind="derived", uncertainty=None, missing=None):
    return {"inputs": inputs, "formula_or_native_source": formula, "units": units,
            "population": population, "denominator": denominator, "kind": kind,
            "coordinate_convention": "native_one_based_inclusive; intervals_zero_based_half_open",
            "uncertainty": uncertainty or "not supplied; no confidence interval inferred",
            "missing_behavior": missing or "null with an issue; independent valid components survive"}


def _definitions():
    definitions = {
        "bitscore": _definition(["hits[].bitscore"], "native tblout score, already bias-corrected", "bits", "one retained hit", kind="native_model_score", uncertainty="1.1.5 writer rounds to one decimal; no statistical interval"),
        "evalue": _definition(["hits[].evalue", "operation.settings", "artifacts[].footer"], "native tblout E-value; no conversion or summation", "expected false positive count", "native query search space", kind="native_statistical_estimate", uncertainty="1.1.5 writer uses two significant digits; zero remains zero"),
        "bias_bits": _definition(["hits[].bias_bits", "hits[].algorithm"], "native null3 correction for cm; null2 for hmm", "bits", "one retained hit", kind="native_model_score", uncertainty="1.1.5 writer rounds to one decimal"),
        "gc_fraction": _definition(["hits[].gc_fraction"], "native tblout gc", "fraction", "nucleotides in native hit", "native hit nucleotide population; original counts not in tblout", kind="native_composition", uncertainty="1.1.5 writer rounds to two decimals"),
        "model_span_length": _definition(["hits[].model_from", "hits[].model_to"], "model_to - model_from + 1", "model_consensus_positions", "one retained hit"),
        "sequence_span_length": _definition(["hits[].sequence_from", "hits[].sequence_to", "hits[].strand"], "abs(sequence_to - sequence_from) + 1", "nucleotides", "one retained hit in physical sequence"),
        "model_span_fraction": _definition(["model_span_length", "hits[].lengths.model.value"], "model_span_length / consensus_length", "fraction", "one retained hit", "validated full model consensus length"),
        "sequence_span_fraction": _definition(["sequence_span_length", "hits[].lengths.sequence.value"], "sequence_span_length / sequence_length", "fraction", "one retained hit", "validated full physical sequence length"),
        "hit_count": _definition(["parameters.hit_scope", "hits[].inclusion", "hits[].sequence.identity", "hits[].strand"], "count retained representations selected by hit_scope", "hit_representations", "one resolved sequence and strand", missing="zero for a known empty selected population; unknown selection counted separately"),
        "union_numerator": _definition(["selected hits[].sequence_from", "selected hits[].sequence_to"], "cardinality of union of valid physical sequence intervals", "nucleotides", "one resolved sequence and strand", missing="observed partial numerator retained; null if selected rows exist but none have valid geometry"),
        "union_denominator": _definition(["selected hits[].lengths.sequence.value"], "common validated sequence length, requiring agreement", "nucleotides", "one resolved physical sequence", kind="validated_input", missing="null if absent, ambiguous, conflicting, or invalid for any selected hit"),
        "union_span_fraction": _definition(["union_numerator", "union_denominator", "complete_for_selected_population"], "union_numerator / union_denominator", "fraction", "one resolved sequence and strand", "validated physical sequence length", missing="null if any selected geometry, inclusion selection or denominator is unresolved"),
        "overlap_length": _definition(["selected hits[].sequence_interval"], "max(0,min(end1,end2)-max(start1,start2))", "nucleotides", "one pair of selected hit representations on the same resolved sequence and strand"),
        "unselected_hit_count": _definition(["hit_scope", "hits[].inclusion"], "count of retained rows excluded by declared hit_scope", "hit_representations", "one resolved sequence and strand"),
        "unknown_selection_count": _definition(["hit_scope", "hits[].inclusion"], "count rows whose inclusion flag cannot resolve selected population", "hit_representations", "one resolved sequence and strand"),
        "invalid_geometry_count": _definition(["selected hit coordinates and length validation"], "count selected rows with invalid coordinate geometry", "hit_representations", "one resolved sequence and strand"),
    }
    return definitions


def _number(value, *, lower=None, upper=None):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or lower is not None and value < lower or upper is not None and value > upper):
        return None
    return value


def _positive(value):
    return type(value) is int and value > 0


def _length(hit, kind, issues):
    row = hit.get("lengths", {}).get(kind, {})
    value = row.get("value")
    if row.get("status") != "validated" or not _positive(value):
        issues.append({"code": "score_denominator_unavailable", "kind": kind})
        return None
    native, supplied = row.get("native"), row.get("supplied")
    if any(v is not None and (not _positive(v) or v != value) for v in (native, supplied)):
        issues.append({"code": "score_denominator_cells_conflict", "kind": kind})
        return None
    return value


def _span(hit, kind, length, issues):
    a, b = hit.get(kind + "_from"), hit.get(kind + "_to")
    valid = _positive(a) and _positive(b)
    if valid and kind == "model":
        valid = a <= b
    elif valid:
        valid = hit.get("strand") in ("+", "-") and (a <= b if hit["strand"] == "+" else a >= b)
    native = hit.get("native_" + kind + "_length")
    if valid and native is not None:
        valid = _positive(native) and max(a, b) <= native
    if valid and length is not None:
        valid = max(a, b) <= length
    # Parser validation may establish a relationship failure even if values
    # themselves are integers (e.g. incomplete provenance). Do not reread text.
    if hit.get(kind + "_interval") is None:
        valid = False
    if not valid:
        issues.append({"code": "score_coordinates_unavailable_or_invalid", "kind": kind})
        return None, None
    interval = [min(a, b)-1, max(a, b)]
    if hit.get(kind + "_interval") != interval:
        issues.append({"code": "score_interval_coordinate_conflict", "kind": kind})
        return None, None
    return interval[1]-interval[0], interval


def _union(intervals):
    result = []
    for a, b in sorted(intervals):
        if result and a <= result[-1][1]:
            result[-1][1] = max(result[-1][1], b)
        else:
            result.append([a, b])
    return result, sum(b-a for a, b in result)


def calculate_infernal_search_scores(sheet: dict, *, parameters: dict | None = None) -> dict:
    """Recalculate solely from saved numerical cells and explicit parameters.

    The only parameter is hit_scope=reported|included, affecting aggregates;
    all per-hit components remain inspectable. This module imports neither the
    parser nor any acquisition, execution, network, model or episode interface.
    """
    if not isinstance(sheet, dict) or sheet.get("schema") != "infernal_search_sheet_v1":
        raise ValueError("infernal_search_sheet_required")
    parameters = {} if parameters is None else parameters
    if (not isinstance(parameters, dict) or set(parameters)-{"hit_scope"}
            or parameters.get("hit_scope", "reported") not in ("reported", "included")):
        raise ValueError("infernal_search_score_parameters_invalid")
    try:
        json.dumps(sheet, allow_nan=False)
        json.dumps(parameters, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError("infernal_finite_json_required") from error
    if not isinstance(sheet.get("hits"), list) or any(not isinstance(x, dict) for x in sheet["hits"]):
        raise ValueError("infernal_search_hit_objects_required")
    scope = parameters.get("hit_scope", "reported")
    issues = deepcopy(sheet.get("issues", []))
    output, populations, unresolved = [], defaultdict(list), []
    for hit in sheet["hits"]:
        problems = []
        lengths = {kind: _length(hit, kind, problems) for kind in ("model", "sequence")}
        spans = {kind: _span(hit, kind, lengths[kind], problems) for kind in ("model", "sequence")}
        components = {field: _number(hit.get(field), lower=0 if field in ("evalue", "gc_fraction") else None,
                                      upper=1 if field == "gc_fraction" else None)
                      for field in ("bitscore", "evalue", "bias_bits", "gc_fraction")}
        for field in components:
            if components[field] is None:
                problems.append({"code": "native_score_cell_unavailable", "field": field})
        for kind in ("model", "sequence"):
            numerator = spans[kind][0]
            components[kind+"_span_length"] = numerator
            components[kind+"_span_fraction"] = numerator/lengths[kind] if numerator is not None and lengths[kind] else None
        selected = True if scope == "reported" else (hit.get("inclusion") == "!" if hit.get("inclusion") in ("!", "?") else None)
        row = {"hit_id": hit.get("hit_id"), "locator": deepcopy(hit.get("locator")),
               "sequence": deepcopy(hit.get("sequence")), "model": deepcopy(hit.get("model")),
               "algorithm": hit.get("algorithm"), "strand": hit.get("strand"), "inclusion": hit.get("inclusion"),
               "selected_for_aggregate": selected, "components": components,
               "population_complete": hit.get("population_complete") is True,
               "denominators": {"consensus_length": lengths["model"], "sequence_length": lengths["sequence"]},
               "model_interval": spans["model"][1], "sequence_interval": spans["sequence"][1],
               "unavailable_components": [name for name, value in components.items() if value is None],
               "status": "partial" if problems or hit.get("issues") else "available",
               "issues": deepcopy(hit.get("issues", [])) + problems}
        output.append(row)
        issues.extend({**p, "hit_id": row["hit_id"]} for p in problems)
        identity = hit.get("sequence", {}).get("identity")
        if not isinstance(identity, dict) or hit.get("strand") not in ("+", "-"):
            unresolved.append(row["hit_id"])
            continue
        key = (json.dumps(identity, sort_keys=True), hit["strand"])
        populations[key].append(row)
    aggregates = []
    for (identity_json, strand), members in populations.items():
        selected = [r for r in members if r["selected_for_aggregate"] is True]
        unknown = [r for r in members if r["selected_for_aggregate"] is None]
        valid = [r for r in selected if r["sequence_interval"] is not None]
        intervals, numerator = _union([r["sequence_interval"] for r in valid])
        if selected and not valid:
            numerator = None
        length_rows = selected or members
        lengths = {r["denominators"]["sequence_length"] for r in length_rows}
        denominator = next(iter(lengths)) if len(lengths) == 1 and None not in lengths else None
        geometrically_complete = len(valid) == len(selected) and not unknown
        population_complete = geometrically_complete and all(r["population_complete"] for r in selected or members)
        if len(lengths-{None}) > 1:
            issues.append({"code": "aggregate_sequence_lengths_conflict", "identity": json.loads(identity_json), "strand": strand})
        duplicate_intervals, representations = defaultdict(list), defaultdict(list)
        for row in valid:
            duplicate_intervals[tuple(row["sequence_interval"])].append(row["hit_id"])
            signature = (json.dumps(row["model"], sort_keys=True), tuple(row["model_interval"] or []),
                         tuple(row["sequence_interval"]), row["algorithm"], row["inclusion"],
                         *(row["components"][f] for f in ("bitscore", "evalue", "bias_bits", "gc_fraction")))
            representations[signature].append(row["hit_id"])
        overlaps = []
        for i, left in enumerate(valid):
            for right in valid[i+1:]:
                a, b = left["sequence_interval"], right["sequence_interval"]
                count = max(0, min(a[1], b[1])-max(a[0], b[0]))
                if count:
                    overlaps.append({"hit_ids": [left["hit_id"], right["hit_id"]], "overlap_length": count})
        aggregate_issues = []
        if not population_complete:
            aggregate_issues.append({"code": "aggregate_population_incomplete"})
        if denominator is None:
            aggregate_issues.append({"code": "aggregate_denominator_unavailable"})
        aggregates.append({"aggregate_id": json.dumps([json.loads(identity_json), strand, scope], sort_keys=True, separators=(",", ":")),
            "sequence_identity": json.loads(identity_json),
            "sequence_names": list(dict.fromkeys(r["sequence"]["name"] for r in members)), "strand": strand,
            "hit_scope": scope, "hit_count": len(selected), "hit_ids": [r["hit_id"] for r in selected],
            "unselected_hit_count": sum(r["selected_for_aggregate"] is False for r in members),
            "unknown_selection_count": len(unknown), "invalid_geometry_count": len(selected)-len(valid),
            "union_intervals": intervals, "union_numerator": numerator, "union_denominator": denominator,
            "union_span_fraction": numerator/denominator if population_complete and numerator is not None and denominator else None,
            "complete_for_selected_population": population_complete,
            "identical_interval_memberships": [v for v in duplicate_intervals.values() if len(v)>1],
            "duplicate_representation_memberships": [v for v in representations.values() if len(v)>1],
            "overlap_memberships": overlaps,
            "status": "partial" if aggregate_issues else "available", "issues": aggregate_issues,
            "meaning": "union of reported coordinate spans on one resolved physical sequence and strand; not paired coverage or independent evidence"})
    if unresolved:
        issues.append({"code": "aggregate_identity_unresolved", "hit_ids": unresolved})
    result = {"schema": SCORE_SCHEMA, "operation": deepcopy(sheet.get("operation")),
              "parameters": {"hit_scope": scope}, "hits": output,
              "sequence_strand_aggregates": aggregates, "unresolved_aggregate_hit_ids": unresolved,
              "definitions": _definitions(), "statistical_limitations": deepcopy(sheet.get("statistical_limitations", [])),
              "search_space": {"recorded_settings": deepcopy(sheet.get("operation", {}).get("settings", {})),
                               "native_options": [deepcopy(a.get("footer", {}).get("fields", {}).get("Option settings", [])) for a in sheet.get("artifacts", [])],
                               "inferred_database_size": None},
              "retained_but_not_combined": ["bitscore", "evalue", "bias_bits", "gc_fraction", "inclusion", "overlap_classification"],
              "issues": issues, "status": sheet.get("status", "invalid")}
    if result["status"] == "available" and issues:
        result["status"] = "partial"
    json.dumps(result, allow_nan=False)
    return result


__all__ = ["calculate_infernal_search_scores", "SCORE_SCHEMA"]
