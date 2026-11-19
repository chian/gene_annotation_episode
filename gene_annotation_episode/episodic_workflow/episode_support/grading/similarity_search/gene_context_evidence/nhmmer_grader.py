"""Deterministic nucleotide-locus calculations from saved nhmmer_sheet_v1.

No program execution, source reading, model invocation, or network acquisition
occurs here. Native E-values, scores, bias and rounded accuracy are independent
measurements. Calculated span/paired coverages and posterior display bounds do
not assert protein translation, function, or annotation correctness.
"""
from __future__ import annotations




_NATIVE = {"native_evalue": ("evalue", "expected_hits"), "native_score_bits": ("score_bits", "bits"),
           "native_bias_bits": ("bias_bits", "bits"), "native_accuracy": ("accuracy", "posterior_fraction")}
_SPANS = {"model_span_positions": ("model_interval", "model_positions"),
          "sequence_span_positions": ("sequence_interval", "nucleotides"),
          "sequence_envelope_positions": ("sequence_envelope_interval", "nucleotides")}
_COVERAGES = {"model_span_coverage": ("model_span_positions", "model_length"),
    "sequence_span_coverage": ("sequence_span_positions", "sequence_length"),
    "sequence_envelope_coverage": ("sequence_envelope_positions", "sequence_length"),
    "paired_model_coverage": ("paired_positions", "model_length"),
    "paired_sequence_coverage": ("paired_positions", "sequence_length")}


def _definition(inputs, formula, unit, population, *, kind="derived", coordinate=None, uncertainty=None):
    return {"input_fields": inputs, "formula": formula, "unit": unit, "population": population,
        "kind": kind, "coordinate_convention": coordinate, "uncertainty": uncertainty,
        "missing_input_behavior": "null_with_scoped_unavailable_reason"}


def _definitions():
    result = {key: _definition(["native." + source], "native printed measurement", unit,
        "one reported local locus", kind="native", uncertainty="printed precision; E-value 0 is not a correctness probability")
        for key, (source, unit) in _NATIVE.items()}
    result["native_accuracy"] = _definition(["native.accuracy", "native.env_from", "native.env_to"],
        "native printed oasc / inclusive envelope length; oasc numerator is not printed",
        "posterior_fraction", "native envelope", kind="native", uncertainty="rounded to two decimals; not sequence identity")
    for key, unit in (("model_length", "model_positions"), ("sequence_length", "nucleotides")):
        result[key] = _definition([key, "length_sources." + key], "unique consistent full length",
            unit, "full actual model or sequence", kind="native_or_explicit_metadata")
    for key, (source, unit) in _SPANS.items():
        result[key] = _definition(["coordinates." + source], "end - start (= abs(native_to-native_from)+1)",
            unit, "one local locus", coordinate="zero_based_half_open; native is one_based_inclusive")
    for key, (numerator, denominator) in _COVERAGES.items():
        result[key] = _definition([numerator, denominator], numerator + " / " + denominator,
            "fraction", "full model or sequence; numerator may include gaps for span coverage")
    for key, formula in {
        "paired_positions": "count(model alphabetic AND sequence alphabetic)",
        "insert_positions": "count(model '.' AND sequence alphabetic)",
        "delete_positions": "count(model alphabetic AND sequence '-')",
        "alignment_columns": "number of validated displayed model/sequence columns"}.items():
        result[key] = _definition(["alignment.model_aligned", "alignment.sequence_aligned"], formula,
            "alignment_positions", "validated native displayed alignment")
    for key, bound in (("posterior_lower_mean", "lower"), ("posterior_upper_mean", "upper")):
        result[key] = _definition(["alignment.posterior", "alignment.sequence_aligned"],
            "sum(display-bin " + bound + " bounds for sequence residues with PP) / PP residue count",
            "posterior_fraction_bound", "sequence-residue columns carrying 0-9 or *; excludes '.' and deletion gaps",
            uncertainty="0=[0,.05), d=1..9=[(d-.5)/10,(d+.5)/10), *=[.95,1]; bounds, not exact probabilities")
    result["unions"] = _definition(["loci.union_identity", "loci.coordinates", "loci.alignment"],
        "length of merged zero-based half-open intervals within exactly one sequence/model/strand/iteration",
        "positions", "identified same operand pair; partial observed population remains partial",
        coordinate="zero_based_half_open")
    result["cutoff_margins"] = _definition(["native.score_bits", "inputs.model_cutoffs"],
        "native_score_bits - explicitly supplied nucleotide per-hit cutoff (sequence_bits); domain_bits unused",
        "bits", "one exactly identified nucleotide model and one local locus")
    result["searched_space"] = _definition(["queries.statistics", "native_settings", "inputs.native_parameters"],
        "retain native observed populations and explicit declarations independently; no E-value reconstruction",
        "native_units", "actual measured searched strands/sequence positions/model population", kind="native_or_supplied")
    return result


def _cell(value, *, inputs, unit, numerator=None, denominator=None, reason=None, **extra):
    return {"value": value, "numerator": numerator, "denominator": denominator,
        "unit": unit, "input_fields": inputs, "unavailable_reason": reason if value is None else None, **extra}


def _union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


TBL_IDENTITY_FIELDS = ("query_name", "query_accession", "target_name", "target_accession")


