"""Inspectable numerical components for populated HMMER protein search sheets.

No overall confidence, E-value transform, native rerun or acquisition occurs.
The default parameter set is empty; unsupported parameters are errors. Printed
posterior characters supply intervals over observed sequence-residue columns,
not calibrated gene-function probabilities. Definitions document executed code.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .hmmer_search_inputs import finite_json

SCALARS = "model_length sequence_length model_span_positions sequence_span_residues sequence_envelope_residues model_span_coverage sequence_span_coverage sequence_envelope_coverage paired_positions insert_positions delete_positions alignment_columns paired_model_coverage paired_sequence_coverage sequence_identity_fraction consensus_identity_fraction alignment_identity_fraction api_identity_fraction native_domain_score_bits native_domain_bias_bits native_conditional_evalue native_independent_evalue native_accuracy posterior_lower_mean posterior_upper_mean".split()
NATIVE_SCALARS = {"native_domain_score_bits": "domain_score_bits", "native_domain_bias_bits": "domain_bias_bits",
                  "native_conditional_evalue": "conditional_evalue", "native_independent_evalue": "independent_evalue", "native_accuracy": "accuracy"}


def _definition(inputs, formula, units, population, *, origin="derived", coordinate=None, uncertainty=None):
    return {"inputs": inputs, "formula": formula, "units": units, "population": population,
            "origin": origin, "coordinate_convention": coordinate, "uncertainty": uncertainty,
            "missing_input_behavior": "null plus scoped unavailable reason; observed zero is retained"}


def _definitions():
    d = {}
    for axis in ("model", "sequence"):
        d[axis + "_length"] = _definition([f"native.{axis}_length", f"joins.{axis}.length"], "native full length, or exact-identity supplied operand length", "positions" if axis == "model" else "residues", f"entire {axis}", origin="native_or_supplied")
    for field, axis, units in (("model_span_positions", "model", "model positions"), ("sequence_span_residues", "sequence", "residues"), ("sequence_envelope_residues", "envelope", "residues")):
        d[field] = _definition([f"intervals.{axis}"], "end - start (native inclusive to - from + 1)", units, f"one domain {axis} interval", coordinate="zero_based_half_open")
    for field, numerator, denominator in (("model_span_coverage", "model_span_positions", "model_length"), ("sequence_span_coverage", "sequence_span_residues", "sequence_length"), ("sequence_envelope_coverage", "sequence_envelope_residues", "sequence_length"), ("paired_model_coverage", "paired_positions", "model_length"), ("paired_sequence_coverage", "paired_positions", "sequence_length")):
        d[field] = _definition([numerator, denominator], "numerator / denominator", "fraction", denominator)
    for field, formula in (("paired_positions", "count(model != '.' and sequence != '-')"), ("insert_positions", "count(model == '.' and sequence != '-')"), ("delete_positions", "count(model != '.' and sequence == '-')"), ("alignment_columns", "length of validated aligned model/sequence display")):
        d[field] = _definition(["quantities." + field], formula, "columns", "one validated native alignment display")
    d["consensus_identity_fraction"] = _definition(["quantities.consensus_identical_positions", "quantities.paired_positions"], "equal uppercase displayed model and sequence residues / paired positions", "fraction", "paired display columns; model consensus is not an actual reference sequence")
    d["sequence_identity_fraction"] = _definition(["quantities.actual_sequence_correspondence", "quantities.consensus_identical_positions", "quantities.paired_positions"], "identical / paired only after exact supplied protein sequence operands agree with native intervals, for phmmer or jackhmmer round 1", "fraction", "paired actual sequence residues")
    d["alignment_identity_fraction"] = _definition(["quantities.consensus_identical_positions", "quantities.alignment_columns"], "identical displayed residues / all alignment columns", "fraction", "paired, insertion and deletion columns")
    d["api_identity_fraction"] = _definition(["alignment.identity[0]", "quantities.api_identity_numerator", "quantities.api_identity_denominator"], "retain provider fraction; independently check alphabetic mline count / min(ungapped model, ungapped sequence)", "fraction", "minimum ungapped display length", origin="native_provider")
    for field, source in NATIVE_SCALARS.items():
        d[field] = _definition(["native." + source], "retain native measurement", "bits" if field.endswith("bits") else "expected chance hit count" if field.endswith("evalue") else "native mean posterior accuracy", "native domain statistical population; E-values depend on native search space", origin="native", uncertainty="printed precision; zero E-value may be rounded or underflowed")
    d["native_domain_bias_bits"]["inputs"].append("native.domain_bias_nats")
    d["native_domain_bias_bits"]["formula"] = "native bits unchanged; provider domain_bias_nats / ln(2) when supplied"
    for field, bound in (("posterior_lower_mean", "lower"), ("posterior_upper_mean", "upper")):
        d[field] = _definition(["alignment.ppline", "alignment.aseq"], f"sum(character interval {bound} bounds) / count(sequence residues with available posterior characters)", "posterior bound", "sequence residues with valid PP characters; gap/missing columns excluded with explicit counts", uncertainty="0:[0,.05), 1:[.05,.15), ..., 9:[.85,.95), *:[.95,1]; upper endpoint open except *")
    d["cutoff_margins"] = _definition(["inputs.model_cutoffs", "native.sequence_score_bits", "native.domain_score_bits"], "score bits - explicitly supplied matching model cutoff bits, separately for GA/TC/NC and sequence/domain scope", "bits", "one exact model and score scope; no category confidence")
    d["hit_interval_unions"] = _definition(["same-hit domains.intervals"], "merge overlapping/adjacent intervals and sum end-start", "positions or residues", "same query occurrence, target occurrence and round; no sums across models or dependent rounds", coordinate="zero_based_half_open")
    d["native_hit_measurements"] = _definition(["hits.native"], "retain full sequence score/bias/E-value and native domain counts", "bits, expected chance hit count, or native count as named", "one native target at one search/round", origin="native", uncertainty="native precision; reported domains differ from internal domains")
    d["query_and_iteration_counts"] = _definition(["rows.query_record_key", "rows.iteration", "rows.is_reported", "rows.is_included"], "count retained rows with matching explicit keys and flags; native round measurements retained separately", "rows", "acquired rows only; neither database population nor independent evidence")
    return d


def _base(row):
    keys = ("record_key", "locator", "query_record_key", "hit_record_key", "query_name", "query_occurrence", "target_name", "target_accession", "target_occurrence", "iteration", "iteration_scope", "is_reported", "is_included", "identifiers", "associations")
    return {**{k: deepcopy(row[k]) for k in keys if k in row}, "issues": deepcopy(row.get("issues", [])),
            "native": deepcopy(row.get("native", {})), "components": {}, "unavailable": {}, "derived": {}}


def _validated_saved_row(source):
    """A damaged saved component cannot discard sound components or siblings."""
    row = deepcopy(source)
    if not isinstance(row.get("issues"), list): row["issues"] = []
    native = row.get("native")
    if not isinstance(native, dict):
        row["issues"].append({"code": "hmmer_saved_native_components_not_object", "record_key": row["record_key"]})
        native = row["native"] = {}
    for name, value in list(native.items()):
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
            row["issues"].append({"code": "hmmer_invalid_saved_numeric_component", "record_key": row["record_key"], "field": "native." + name, "supplied": deepcopy(value)})
            native[name] = None
    intervals = row.get("intervals", {})
    if not isinstance(intervals, dict): intervals = {}
    for name, value in list(intervals.items()):
        if value is not None and not (isinstance(value, list) and len(value) == 2 and all(type(x) is int for x in value) and 0 <= value[0] < value[1]):
            row["issues"].append({"code": "hmmer_invalid_saved_interval", "record_key": row["record_key"], "field": name})
            intervals[name] = None
    row["intervals"] = intervals
    q = row.get("quantities", {})
    if not isinstance(q, dict): q = {}
    counts = ("paired_positions", "insert_positions", "delete_positions", "alignment_columns", "consensus_identical_positions", "api_identity_numerator", "api_identity_denominator")
    for name in counts:
        value = q.get(name)
        if value is not None and (type(value) is not int or value < 0):
            q[name] = None
            row["issues"].append({"code": "hmmer_invalid_saved_count", "record_key": row["record_key"], "field": name})
    row["quantities"] = q
    if not isinstance(row.get("alignment", {}), dict): row["alignment"] = {}
    return row


def _set(row, name, value, *, numerator=None, denominator=None, reason="native_measurement_unavailable", units=None):
    row[name] = value
    row["components"][name] = {"value": value, "numerator": numerator, "denominator": denominator, "definition": name}
    if units is not None: row["components"][name]["units"] = units
    if value is None:
        row["unavailable"][name] = reason
    else:
        row["unavailable"].pop(name, None)


def _ratio(row, field, numerator, denominator, *, reason="numerator_or_denominator_unavailable"):
    _set(row, field, numerator / denominator if numerator is not None and denominator is not None and denominator > 0 else None,
         numerator=numerator, denominator=denominator, reason=reason)


def _pp(row, source):
    alignment = source.get("alignment", {})
    pp, seq = alignment.get("ppline"), alignment.get("aseq")
    if not source.get("quantities", {}).get("valid") or not isinstance(pp, str) or not isinstance(seq, str) or len(pp) != len(seq):
        row["posterior_population"] = {"observed_residues": None, "missing_residues": None}
        _set(row, "posterior_lower_mean", None, reason="posterior_display_unavailable_or_geometry_invalid")
        _set(row, "posterior_upper_mean", None, reason="posterior_display_unavailable_or_geometry_invalid")
        return
    lows, ups, missing, gaps, invalid = [], [], 0, 0, []
    chars = {}
    all_upper_closed = True
    for index, (c, s) in enumerate(zip(pp, seq)):
        if s == "-": gaps += 1; continue
        chars[c] = chars.get(c, 0) + 1
        if c == ".": missing += 1; continue
        if c == "*": lo, hi = .95, 1.0
        elif c in "0123456789":
            lo = max(0.0, (int(c) - .5) / 10); hi = (int(c) + .5) / 10
            all_upper_closed = False
        else:
            missing += 1; invalid.append(index); continue
        lows.append(lo); ups.append(hi)
    n = len(lows)
    row["posterior_population"] = {"observed_residues": n, "missing_residues": missing, "gap_columns": gaps,
                                   "character_counts": chars, "upper_endpoint_closed": all_upper_closed if n else None,
                                   "invalid_column_indices": invalid}
    if invalid: row["issues"].append({"code": "hmmer_invalid_posterior_characters", "record_key": row["record_key"], "column_indices": invalid})
    _ratio(row, "posterior_lower_mean", math.fsum(lows) if n else None, n, reason="no_observed_posterior_residues")
    _ratio(row, "posterior_upper_mean", math.fsum(ups) if n else None, n, reason="no_observed_posterior_residues")


def _cutoffs(source, sheet):
    program = sheet["operation"]["program"]
    name = source.get("target_name") if program == "hmmscan" else source.get("query_name")
    acc = source.get("target_accession") if program == "hmmscan" else source.get("query_accession")
    supplied = sheet.get("inputs", {}).get("model_cutoffs", [])
    if not isinstance(supplied, list): return {"available": False, "reason": "model_cutoffs_not_array", "values": []}
    matched = []
    for item in supplied:
        if not isinstance(item, dict): continue
        declared = [(k, v) for k, v in (("name", name), ("accession", acc)) if item.get(k) is not None]
        if declared and all(item[k] == value for k, value in declared): matched.append(item)
    if len(matched) != 1: return {"available": False, "reason": "model_cutoff_unavailable" if not matched else "model_cutoff_ambiguous", "values": []}
    result = {"available": True, "model_name": name, "model_accession": acc, "values": []}
    for cutoff in ("GA", "TC", "NC"):
        values = matched[0].get(cutoff)
        if not isinstance(values, dict): continue
        for scope in ("sequence", "domain"):
            threshold, score = values.get(scope + "_bits"), source.get("native", {}).get(scope + "_score_bits")
            valid = type(threshold) in (int, float) and math.isfinite(threshold)
            result["values"].append({"cutoff": cutoff, "scope": scope, "score_bits": score,
                "cutoff_bits": threshold if valid else None, "margin_bits": score - threshold if valid and score is not None else None,
                "unavailable_reason": None if valid and score is not None else "cutoff_or_score_unavailable", "units": "bits"})
    return result


def _domain(source, sheet):
    row = _base(source); native = source.get("native", {}); q = source.get("quantities", {})
    intervals = source.get("intervals", {})
    row["intervals"] = deepcopy(intervals)
    row["coordinate_convention"] = deepcopy(source.get("coordinate_convention"))
    for key in SCALARS: _set(row, key, None)
    for axis in ("model", "sequence"): _set(row, axis + "_length", native.get(axis + "_length"), reason="full_operand_length_unavailable")
    for field, axis in (("model_span_positions", "model"), ("sequence_span_residues", "sequence"), ("sequence_envelope_residues", "envelope")):
        interval = intervals.get(axis)
        _set(row, field, interval[1] - interval[0] if interval else None, reason="valid_interval_unavailable")
    for field, numerator, denominator in (("model_span_coverage", "model_span_positions", "model_length"), ("sequence_span_coverage", "sequence_span_residues", "sequence_length"), ("sequence_envelope_coverage", "sequence_envelope_residues", "sequence_length")):
        _ratio(row, field, row[numerator], row[denominator])
    if q.get("valid"):
        for field in ("paired_positions", "insert_positions", "delete_positions", "alignment_columns"):
            _set(row, field, q.get(field))
        identical, paired, columns = q.get("consensus_identical_positions"), q.get("paired_positions"), q.get("alignment_columns")
        row["consensus_identical_positions"] = identical
        _ratio(row, "consensus_identity_fraction", identical, paired)
        _ratio(row, "alignment_identity_fraction", identical, columns)
        _ratio(row, "sequence_identity_fraction", identical if q.get("actual_sequence_correspondence") else None, paired,
               reason="actual_sequence_operands_and_correspondence_unavailable")
    else:
        for field in ("paired_positions", "insert_positions", "delete_positions", "alignment_columns", "consensus_identity_fraction", "alignment_identity_fraction", "sequence_identity_fraction", "api_identity_fraction"):
            row["unavailable"][field] = q.get("reason", "alignment_measurements_unavailable")
    if sheet["operation"]["format"] == "hmmer_api_json":
        ad = source.get("alignment", {}); ident = ad.get("identity")
        provider = ident[0] if isinstance(ident, list) and len(ident) == 2 else None
        valid = type(provider) in (int, float) and 0 <= provider <= 1
        numerator, denominator = q.get("api_identity_numerator"), q.get("api_identity_denominator")
        _set(row, "api_identity_fraction", provider if valid else None, numerator=numerator, denominator=denominator,
             reason="native_api_identity_fraction_unavailable_or_invalid")
        row["api_identity_reported_count"] = ident[1] if isinstance(ident, list) and len(ident) == 2 else None
        row["api_identity_recalculated_fraction"] = numerator / denominator if numerator is not None and denominator else None
        if valid and row["api_identity_recalculated_fraction"] is not None and (not math.isclose(provider, row["api_identity_recalculated_fraction"], rel_tol=1e-6, abs_tol=1e-9) or ident[1] != numerator):
            row["issues"].append({"code": "hmmer_api_identity_native_calculation_mismatch", "record_key": row["record_key"]})
    _ratio(row, "paired_model_coverage", row["paired_positions"], row["model_length"])
    _ratio(row, "paired_sequence_coverage", row["paired_positions"], row["sequence_length"])
    for field, source_name in NATIVE_SCALARS.items():
        _set(row, field, native.get(source_name))
    if native.get("domain_bias_bits") is None and native.get("domain_bias_nats") is not None:
        _set(row, "native_domain_bias_bits", native["domain_bias_nats"] / math.log(2), numerator=native["domain_bias_nats"], denominator=math.log(2), units="bits")
    _pp(row, source)
    row["cutoff_margins"] = _cutoffs(source, sheet)
    row["derived"] = {name: row[name] for name in SCALARS if name not in NATIVE_SCALARS}
    if native.get("domain_bias_nats") is not None: row["derived"]["domain_bias_bits_from_nats"] = row["native_domain_bias_bits"]
    row["availability"] = "partial" if row["unavailable"] or row["issues"] else "available"
    return row


def _union(intervals):
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    return {"intervals": merged, "positions": sum(b - a for a, b in merged)}


def calculate_hmmer_search_scores(sheet, *, parameters=None):
    """Calculate only from saved sheet; reject all undeclared parameters."""
    if type(sheet) is not dict or sheet.get("schema") != "hmmer_search_sheet_v1":
        raise ValueError("hmmer_invalid_search_sheet_schema")
    if parameters is not None and type(parameters) is not dict: raise ValueError("hmmer_parameters_must_be_object")
    finite_json(sheet); finite_json(parameters)
    if parameters: raise ValueError("hmmer_unsupported_calculator_parameters:" + ",".join(sorted(parameters)))
    for key in ("hits", "domains", "queries", "iterations"):
        if not isinstance(sheet.get(key), list): raise ValueError("hmmer_sheet_rows_must_be_arrays:" + key)
    result = {"schema": "hmmer_search_scores_v1", "operation": deepcopy(sheet["operation"]), "parameters": {},
              "hits": [], "domains": [], "queries": [], "iterations": [], "definitions": _definitions(), "issues": deepcopy(sheet.get("issues", []))}
    for source in sheet["domains"]:
        if not isinstance(source, dict) or "record_key" not in source or "locator" not in source:
            result["issues"].append({"code": "hmmer_invalid_saved_domain_row"}); continue
        result["domains"].append(_domain(_validated_saved_row(source), sheet))
    for source in sheet["hits"]:
        if not isinstance(source, dict) or "record_key" not in source or "locator" not in source:
            result["issues"].append({"code": "hmmer_invalid_saved_hit_row"}); continue
        source = _validated_saved_row(source)
        row = _base(source)
        for key, value in source.get("native", {}).items(): row["native_" + key] = deepcopy(value)
        domains = [d for d in result["domains"] if d.get("hit_record_key") == source["record_key"]]
        row["domain_record_keys"] = [d["record_key"] for d in domains]
        row["retained_domain_count"] = len(domains)
        row["cutoff_margins"] = _cutoffs(source, sheet)
        row["interval_unions"] = {}
        # Only exact per-hit associations contribute. Ambiguous duplicate
        # representations do not become a union or an independent count.
        for axis in ("model", "sequence", "envelope"):
            valid = [d["intervals"][axis] for d in domains if d.get("intervals", {}).get(axis)]
            row["interval_unions"][axis] = _union(valid) if valid else None
            if valid: row["interval_unions"][axis]["population"] = "available domains for this exact hit occurrence and iteration"
        row["availability"] = "partial" if row["issues"] else "native_measurements_available"
        result["hits"].append(row)
    for source in sheet["queries"]:
        if not isinstance(source, dict) or "record_key" not in source:
            result["issues"].append({"code": "hmmer_invalid_saved_query_row"}); continue
        row = _base(source)
        rows = [h for h in result["hits"] if h.get("query_record_key") == source["record_key"]]
        occurrence_established = source.get("occurrence") is not None
        row.update(name=source.get("name"), occurrence=source.get("occurrence"), length=source.get("length"),
                   acquired_hit_row_count=len(rows) if occurrence_established else None,
                   acquired_reported_hit_row_count=sum(h.get("is_reported") is True for h in rows) if occurrence_established else None,
                   acquired_included_hit_row_count=sum(h.get("is_included") is True for h in rows) if occurrence_established else None,
                   included_status_unavailable_rows=sum(h.get("is_included") is None for h in rows) if occurrence_established else None,
                   reporting_status_unavailable_rows=sum(h.get("is_reported") is None for h in rows) if occurrence_established else None,
                   acquisition=deepcopy(sheet.get("inputs", {}).get("acquisition", {})), completion=deepcopy(sheet.get("completion", {})),
                   count_population="retained rows across explicitly identified rounds; dependent rounds are not independent evidence")
        if not occurrence_established:
            row["unavailable"]["acquired_hit_row_count"] = "query_occurrence_unestablished_in_tables_without_stdout"
        statistics = sheet.get("statistics", [])
        if isinstance(statistics, list):
            row["native_search_statistics"] = [deepcopy(s) for s in statistics if isinstance(s, dict) and s.get("query_record_key") == source["record_key"] and s.get("native")]
        elif isinstance(statistics, dict):
            row["native_search_statistics"] = {k: deepcopy(v) for k, v in statistics.items() if k in {"Z", "domZ", "Z_setby", "domZ_setby", "nmodels", "nseqs", "nhits", "nreported", "nincluded"}}
        result["queries"].append(row)
    for source in sheet["iterations"]:
        if not isinstance(source, dict) or "record_key" not in source:
            result["issues"].append({"code": "hmmer_invalid_saved_iteration_row"}); continue
        row = deepcopy(source)
        rows = [h for h in result["hits"] if h.get("query_record_key") == source.get("query_record_key") and h.get("iteration") == source.get("iteration")]
        row.update(acquired_hit_row_count=len(rows), included_hit_record_keys=[h["record_key"] for h in rows if h.get("is_included") is True],
                   new_hit_record_keys=[h["record_key"] for h in sheet["hits"] if h.get("query_record_key") == source.get("query_record_key") and h.get("iteration") == source.get("iteration") and h.get("is_new") is True],
                   dependent_round=sheet["operation"]["program"] == "jackhmmer")
        result["iterations"].append(row)
    finite_json(result, code="hmmer_nonfinite_calculation")
    return result
