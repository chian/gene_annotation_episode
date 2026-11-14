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

from .infernal_search_contracts import (
    SCORE_SCHEMA, CORRESPONDENCE_COUNT_FIELDS, HIT_COMPONENT_FIELDS,
    sheet_digest, validate_infernal_search_sheet, validate_infernal_search_scores)


def _definition(inputs, formula, units, population, denominator=None, *, kind="derived", uncertainty=None, missing=None):
    return {"inputs": inputs, "formula_or_native_source": formula, "units": units,
            "population": population, "denominator": denominator, "kind": kind,
            "coordinate_convention": "native_one_based_inclusive; intervals_zero_based_half_open",
            "uncertainty": uncertainty or "not supplied; no confidence interval inferred",
            "missing_behavior": missing or "null with an issue; independent valid components survive"}


def _definitions():
    definitions = {
        "bitscore": _definition(["hits[].bitscore"], "native reported score, already bias-corrected", "bits", "one retained hit", kind="native_model_score", uncertainty="source precision retained; native tblout 1.1.5 rounds to one decimal; other source precision is not inferred"),
        "evalue": _definition(["hits[].evalue", "operation.settings", "artifacts[].footer"], "native reported E-value; no conversion or summation", "expected false positive count", "native query search space", kind="native_statistical_estimate", uncertainty="source precision retained; native tblout 1.1.5 uses two significant digits; zero remains zero"),
        "bias_bits": _definition(["hits[].bias_bits", "hits[].algorithm"], "native null3 correction for cm; null2 for hmm", "bits", "one retained hit", kind="native_model_score", uncertainty="source precision retained; native tblout 1.1.5 rounds to one decimal"),
        "gc_fraction": _definition(["hits[].gc_fraction"], "native reported GC fraction", "fraction", "nucleotides in native hit", "native hit nucleotide population; original counts not in tblout", kind="native_composition", uncertainty="source precision retained; native tblout 1.1.5 rounds to two decimals"),
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
    for kind, units in (("sequence", "nucleotide_position_1i"), ("model", "model_position_1i")):
        for end in ("from", "to"):
            name = kind + "_" + end
            definitions[name] = _definition(["hits[]." + name], "validated observed positive native endpoint; joint geometry may remain invalid", units, "one retained hit", kind="native_coordinate")
    for name, units in (("sequence_length", "nucleotides"), ("consensus_length", "model_consensus_positions")):
        definitions[name] = _definition(["hits[].lengths"], "validated full input length with agreeing native/supplied values", units, "one bound input record", kind="validated_input")
    for name in ("native_rank", "native_alignment_accuracy"):
        definitions[name] = _definition(["hits[]." + name], "native reported value; never inferred from display/order/posterior bins", "rank" if name == "native_rank" else "fraction", "one native hit", kind="native_measurement")
    for kind, units in (("model", "model_consensus_positions"), ("query", "nucleotides")):
        for end in ("from", "to"):
            name = "display_" + kind + "_" + end
            definitions[name] = _definition(["hits[].correspondence." + name], "native display endpoint; not full model length", units, "one source-bound display", kind="native_coordinate")
        name = "represented_" + kind + "_positions"
        definitions[name] = _definition(["hits[].correspondence.aligned_" + kind + "_intervals"], "cardinality of interval union of explicit represented positions", units, "one usable complete or partial correspondence", missing="null for absent/unusable correspondence or empty intervals in a partial correspondence; complete empty represented population is zero")
    for name in CORRESPONDENCE_COUNT_FIELDS:
        definitions[name] = _definition(["hits[].correspondence." + name, "hits[].correspondence.segments", "hits[].correspondence.paired_positions"], "validated native traversal or determinate-pair count; omission shorthand never supplies represented residues", "comparisons" if "consensus" in name else "nucleotides" if name in ("query_insert_count", "local_end_query_count") else "model_consensus_positions", "one source-bound correspondence", kind="validated_native_count")
    definitions["represented_model_fraction"] = _definition(["represented_model_positions", "consensus_length"], "represented_model_positions / consensus_length", "fraction", "one source-bound correspondence", "validated full searched-model consensus length")
    definitions["model_consensus_equal_fraction"] = _definition(["model_consensus_equal_count", "model_consensus_compared_count"], "equal_count / compared_count; canonical A/C/G/U pairs only, T equivalent to U", "fraction", "explicit determinate pairs", "positive compared_count", missing="null with no_determinate_pairs when compared_count is zero; no padded pairs")
    for name, formula, units in (
        ("valid_geometry_count", "count selected rows with valid attributed physical intervals", "hit_representations"),
        ("span_sum", "sum selected valid attributed physical sequence_span_length, retaining multiplicity", "nucleotides"),
        ("overlap_excess", "span_sum - union_numerator; multiplicity, not independent support", "nucleotides"),
        ("reported_row_count", "retained source representation count, including malformed/rejected rows where declared", "source_rows"),
        ("exact_source_duplicate_row_count", "count explicit same-source exact-row duplicate links", "source_rows")):
        definitions[name] = _definition(["selected common hit cells", "sequence_populations"], formula, units, "one resolved physical sequence; strand-qualified for strand aggregates", missing="complete declared empty population is zero; incomplete absent population is null; partial observed quantities survive")
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


def _correspondence_components(hit, lengths, components, issues):
    correspondence = hit.get("correspondence")
    if correspondence is None or correspondence["status"] not in ("complete", "partial"):
        return
    for field in CORRESPONDENCE_COUNT_FIELDS:
        value = correspondence[field]
        components[field] = value if type(value) is int and value >= 0 else None
    for kind in ("model", "query"):
        for end in ("from", "to"):
            field = "display_" + kind + "_" + end
            value = correspondence[field]
            components[field] = value if _positive(value) else None
        intervals = correspondence["aligned_" + kind + "_intervals"]
        represented = _union(intervals)[1] if intervals or correspondence["status"] == "complete" else None
        components["represented_" + kind + "_positions"] = represented
    numerator = components["represented_model_positions"]
    denominator = lengths["model"]
    if numerator is not None and denominator is not None:
        if all(end <= denominator for _, end in correspondence["aligned_model_intervals"]):
            components["represented_model_fraction"] = numerator / denominator
        else:
            issues.append({"code": "correspondence_exceeds_validated_model_length"})
    compared, equal = (components[field] for field in CORRESPONDENCE_COUNT_FIELDS[:2])
    if compared is not None and equal is not None and compared > 0:
        components["model_consensus_equal_fraction"] = equal / compared
    elif compared == 0:
        issues.append({"code": "no_determinate_pairs"})


def _hit_components(hit, scope):
    problems = []
    lengths = {kind: _length(hit, kind, problems) for kind in ("model", "sequence")}
    spans = {kind: _span(hit, kind, lengths[kind], problems) for kind in ("model", "sequence")}
    components = dict.fromkeys(HIT_COMPONENT_FIELDS)
    for field in ("bitscore", "evalue", "bias_bits", "gc_fraction"):
        components[field] = _number(hit.get(field), lower=0 if field in ("evalue", "gc_fraction") else None,
                                    upper=1 if field == "gc_fraction" else None)
        if components[field] is None:
            problems.append({"code": "native_score_cell_unavailable", "field": field})
    for kind in ("model", "sequence"):
        numerator = spans[kind][0]
        components[kind + "_span_length"] = numerator
        components[kind + "_span_fraction"] = numerator / lengths[kind] if numerator is not None and lengths[kind] else None
        for end in ("from", "to"):
            field = kind + "_" + end
            components[field] = hit.get(field) if _positive(hit.get(field)) else None
    components.update(consensus_length=lengths["model"], sequence_length=lengths["sequence"],
        native_rank=hit["native_rank"] if _positive(hit["native_rank"]) else None,
        native_alignment_accuracy=_number(hit["native_alignment_accuracy"], lower=0, upper=1))
    _correspondence_components(hit, lengths, components, problems)
    selected = True if scope == "reported" else (hit.get("inclusion") == "!" if hit.get("inclusion") in ("!", "?") else None)
    attributed = all(hit["attribution"][kind] == "valid" for kind in ("sequence", "model"))
    return {"hit_id": hit["hit_id"], "locator": deepcopy(hit["locator"]),
        "sequence": deepcopy(hit["sequence"]), "model": deepcopy(hit["model"]),
        "query_occurrence_key": hit["query_occurrence_key"], "attribution": deepcopy(hit["attribution"]),
        "algorithm": hit.get("algorithm"), "strand": hit.get("strand"), "inclusion": hit.get("inclusion"),
        "selected_for_aggregate": selected, "components": components,
        "attributed_components": deepcopy(components) if attributed else dict.fromkeys(HIT_COMPONENT_FIELDS),
        "population_complete": hit["population_complete"], "duplicate_of": hit["duplicate_of"],
        "denominators": {"consensus_length": lengths["model"], "sequence_length": lengths["sequence"]},
        "model_interval": spans["model"][1], "sequence_interval": spans["sequence"][1],
        "unavailable_components": [name for name, value in components.items() if value is None],
        "status": "partial" if problems or hit.get("issues") else "available",
        "issues": deepcopy(hit.get("issues", [])) + problems}


def _population(identity, strand, members, declaration, scope, *, uncertain=()):
    """Calculate one strand or whole-occurrence population from common cells."""
    selected = [r for r in members if r["selected_for_aggregate"] is True]
    unknown = [r for r in members if r["selected_for_aggregate"] is None]
    valid = [r for r in selected if r["sequence_interval"] is not None
             and all(r["attribution"][kind] == "valid" for kind in ("sequence", "model"))]
    declared_complete = declaration["reported_set_complete"] if declaration else bool(members) and all(r["population_complete"] for r in members)
    observed = bool(selected) or declared_complete and not unknown and not uncertain or bool(members) and not unknown and not uncertain and not selected
    intervals, numerator = _union([r["sequence_interval"] for r in valid])
    if selected and not valid or not observed:
        numerator = None
    span_sum = sum(r["components"]["sequence_span_length"] for r in valid) if numerator is not None else None
    length_rows = selected or members
    lengths = {r["denominators"]["sequence_length"] for r in length_rows}
    if declaration:
        cell = declaration["length"]
        lengths.add(cell["value"] if cell["status"] == "validated" else None)
    denominator = next(iter(lengths)) if len(lengths) == 1 and None not in lengths else None
    geometry_complete = len(valid) == len(selected) and not unknown and not uncertain
    complete = declared_complete and geometry_complete and all(r["population_complete"] for r in members)
    reported_count = (declaration["reported_row_count"] if declaration and strand is None else len(members) if members or declared_complete and not uncertain else None)
    if declaration and strand is None and reported_count is not None and reported_count != len(members):
        complete = False
    duplicate_intervals, representations = defaultdict(list), defaultdict(list)
    for row in valid:
        duplicate_intervals[tuple(row["sequence_interval"])].append(row["hit_id"])
        signature = (json.dumps(row["model"], sort_keys=True), tuple(row["model_interval"] or []),
            tuple(row["sequence_interval"]), row["algorithm"], row["inclusion"],
            *(row["components"][f] for f in ("bitscore", "evalue", "bias_bits", "gc_fraction")))
        representations[signature].append(row["hit_id"])
    overlaps = []
    for index, left in enumerate(valid):
        for right in valid[index + 1:]:
            a, b = left["sequence_interval"], right["sequence_interval"]
            count = max(0, min(a[1], b[1]) - max(a[0], b[0]))
            if count:
                overlaps.append({"hit_ids": [left["hit_id"], right["hit_id"]], "overlap_length": count})
    problems = []
    if not complete:
        problems.append({"code": "aggregate_population_incomplete"})
    if denominator is None:
        problems.append({"code": "aggregate_denominator_unavailable"})
    if len(lengths - {None}) > 1:
        problems.append({"code": "aggregate_sequence_lengths_conflict", "identity": identity, "strand": strand})
    occurrence = declaration["query_occurrence_key"] if declaration else next((r["query_occurrence_key"] for r in members if r["query_occurrence_key"] is not None), None)
    names = list(dict.fromkeys(r["sequence"]["name"] for r in members))
    if not names and declaration:
        names = [declaration["native_name"]]
    return {"aggregate_id": json.dumps([identity, strand, scope], sort_keys=True, separators=(",", ":")),
        "sequence_identity": deepcopy(identity), "query_occurrence_key": occurrence,
        "sequence_names": names, "strand": strand, "hit_scope": scope,
        "hit_count": len(selected) if observed else None, "hit_ids": [r["hit_id"] for r in selected],
        "unselected_hit_count": sum(r["selected_for_aggregate"] is False for r in members) if members or observed else None,
        "unknown_selection_count": len(unknown) if members or observed else None,
        "invalid_geometry_count": len(selected) - len(valid) if observed else None,
        "valid_geometry_count": len(valid) if observed else None,
        "reported_row_count": reported_count,
        "exact_source_duplicate_row_count": sum(r["duplicate_of"] is not None for r in selected) if observed else None,
        "span_sum": span_sum, "union_intervals": intervals, "union_numerator": numerator,
        "overlap_excess": span_sum - numerator if span_sum is not None and numerator is not None else None,
        "union_denominator": denominator,
        "union_span_fraction": numerator / denominator if complete and numerator is not None and denominator else None,
        "complete_for_selected_population": complete, "reported_set_complete": declared_complete,
        "interval_population_complete": complete,
        "identical_interval_memberships": [v for v in duplicate_intervals.values() if len(v) > 1],
        "duplicate_representation_memberships": [v for v in representations.values() if len(v) > 1],
        "overlap_memberships": overlaps, "status": "partial" if problems else "available", "issues": problems,
        "meaning": "union of attributed physical coordinate spans for the declared occurrence and strand; not paired coverage or independent evidence"}


def calculate_infernal_search_scores(sheet: dict, *, parameters: dict | None = None) -> dict:
    """Calculate only from saved v2 cells; explicit v1 conversion is separate."""
    validate_infernal_search_sheet(sheet)
    parameters = {} if parameters is None else parameters
    if (not isinstance(parameters, dict) or set(parameters) - {"hit_scope"}
            or parameters.get("hit_scope", "reported") not in ("reported", "included")):
        raise ValueError("infernal_search_score_parameters_invalid")
    scope = parameters.get("hit_scope", "reported")
    issues = deepcopy(sheet["issues"])
    output = [_hit_components(hit, scope) for hit in sheet["hits"]]
    for row, hit in zip(output, sheet["hits"]):
        issues.extend({**p, "hit_id": row["hit_id"]} for p in row["issues"][len(hit["issues"]):])
    by_identity, declarations, unresolved = {}, {}, []
    for declaration in sheet["sequence_populations"]:
        key = json.dumps(declaration["sequence_identity"], sort_keys=True)
        declarations[key] = declaration
        by_identity[key] = []
    for row in output:
        identity = row["sequence"].get("identity")
        if not isinstance(identity, dict):
            unresolved.append(row["hit_id"])
            continue
        key = json.dumps(identity, sort_keys=True)
        by_identity.setdefault(key, []).append(row)
        if row["strand"] not in ("+", "-"):
            unresolved.append(row["hit_id"])
    aggregates, summaries = [], []
    for key, members in by_identity.items():
        identity, declaration = json.loads(key), declarations.get(key)
        strands = list(declaration["declared_strands"]) if declaration else []
        for row in members:
            if row["strand"] in ("+", "-") and row["strand"] not in strands:
                strands.append(row["strand"])
        uncertain = [row for row in members if row["strand"] not in ("+", "-")]
        for strand in strands:
            aggregates.append(_population(identity, strand, [r for r in members if r["strand"] == strand], declaration, scope, uncertain=uncertain))
        summaries.append(_population(identity, None, members, declaration, scope))
    if unresolved:
        issues.append({"code": "aggregate_identity_unresolved", "hit_ids": unresolved})
    result = {"schema": SCORE_SCHEMA, "sheet_digest": sheet_digest(sheet),
        "operation": deepcopy(sheet["operation"]), "source_context": deepcopy(sheet["source_context"]),
        "parameters": {"hit_scope": scope}, "hits": output,
        "sequence_strand_aggregates": aggregates, "sequence_populations": summaries,
        "unresolved_aggregate_hit_ids": unresolved, "definitions": _definitions(),
        "statistical_limitations": deepcopy(sheet["statistical_limitations"]),
        "search_space": {"recorded_settings": deepcopy(sheet["operation"].get("settings", {})),
            "native_options": [deepcopy(a.get("footer", {}).get("fields", {}).get("Option settings", [])) for a in sheet["artifacts"]],
            "inferred_database_size": None},
        "retained_but_not_combined": ["bitscore", "evalue", "bias_bits", "gc_fraction", "inclusion", "overlap_classification", "native_alignment_accuracy"],
        "issues": issues, "status": sheet["status"]}
    if result["status"] == "available" and issues:
        result["status"] = "partial"
    return validate_infernal_search_scores(result, sheet=sheet)


__all__ = ["calculate_infernal_search_scores", "SCORE_SCHEMA"]


