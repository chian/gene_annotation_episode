"""Deterministic nucleotide-locus calculations from saved nhmmer_sheet_v1.

No program execution, source reading, model invocation, or network acquisition
occurs here. Native E-values, scores, bias and rounded accuracy are independent
measurements. Calculated span/paired coverages and posterior display bounds do
not assert protein translation, function, or annotation correctness.
"""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
import math

from .nhmmer_inputs import finite_json


_NATIVE = {"native_evalue": ("evalue", "expected_hits"), "native_score_bits": ("score_bits", "bits"),
           "native_bias_bits": ("bias_bits", "bits"), "native_accuracy": ("accuracy", "posterior_fraction")}
_COUNTS = ("paired_positions", "insert_positions", "delete_positions", "alignment_columns")
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


def _valid_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _valid_length(value):
    return type(value) is int and value > 0


def _valid_interval(interval):
    return (type(interval) is list and len(interval) == 2 and all(type(x) is int for x in interval)
            and 0 <= interval[0] < interval[1])


def _cell(value, *, inputs, unit, numerator=None, denominator=None, reason=None, **extra):
    return {"value": value, "numerator": numerator, "denominator": denominator,
        "unit": unit, "input_fields": inputs, "unavailable_reason": reason if value is None else None, **extra}


def _intervals(positions):
    result = []
    for position in sorted(set(positions)):
        if result and result[-1][1] == position:
            result[-1][1] += 1
        else:
            result.append([position, position + 1])
    return result


def _union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def _alignment_components(row):
    alignment = row.get("alignment")
    result = {name: None for name in _COUNTS}
    result.update(posterior_lower_mean=None, posterior_upper_mean=None,
        paired_model_intervals=None, paired_sequence_intervals=None,
        posterior_residue_count=None, posterior_missing_residue_count=None,
        posterior_lower_sum=None, posterior_upper_sum=None, posterior_upper_inclusive=None)
    if not isinstance(alignment, dict) or not alignment.get("valid"):
        return result, "alignment_unavailable_or_invalid"
    model, sequence = alignment.get("model_aligned"), alignment.get("sequence_aligned")
    if not isinstance(model, str) or not isinstance(sequence, str) or not model or len(model) != len(sequence):
        return result, "alignment_unavailable_or_invalid"
    if any(not (a.isalpha() or a == ".") or not (b.isalpha() or b == "-")
           or (a == "." and b == "-") for a, b in zip(model, sequence)):
        return result, "alignment_symbols_invalid"
    coords = row.get("coordinates", {})
    if not _valid_interval(coords.get("model_interval")) or not _valid_interval(coords.get("sequence_interval")):
        return result, "alignment_coordinates_invalid"
    mi, si = coords["model_interval"], coords["sequence_interval"]
    if sum(c.isalpha() for c in model) != mi[1] - mi[0] or sum(c.isalpha() for c in sequence) != si[1] - si[0]:
        return result, "alignment_spans_disagree"
    paired = sum(a.isalpha() and b.isalpha() for a, b in zip(model, sequence))
    inserts = sum(a == "." and b.isalpha() for a, b in zip(model, sequence))
    deletes = sum(a.isalpha() and b == "-" for a, b in zip(model, sequence))
    result.update(paired_positions=paired, insert_positions=inserts, delete_positions=deletes, alignment_columns=len(model))
    mpos, spos = mi[0], si[1] - 1 if row["native"].get("strand") == "-" else si[0]
    step = -1 if row["native"].get("strand") == "-" else 1
    mpaired, spaired = [], []
    for a, b in zip(model, sequence):
        if a.isalpha() and b.isalpha():
            mpaired.append(mpos)
            spaired.append(spos)
        mpos += a.isalpha()
        spos += step * b.isalpha()
    result["paired_model_intervals"], result["paired_sequence_intervals"] = _intervals(mpaired), _intervals(spaired)
    pp = alignment.get("posterior")
    if pp is None or not alignment.get("posterior_valid") or len(pp) != len(sequence):
        return result, "posterior_unavailable_or_invalid"
    lower, upper, missing, bins = [], [], 0, []
    for symbol, residue in zip(pp, sequence):
        if symbol not in "0123456789*.":
            return result, "posterior_symbol_invalid"
        if residue == "-":
            if symbol != ".":
                return result, "posterior_assigned_to_deletion_gap"
            continue
        if symbol == ".":
            missing += 1
            continue
        bins.append(symbol)
        if symbol == "*":
            low, high = 0.95, 1.0
        elif symbol == "0":
            low, high = 0.0, 0.05
        else:
            low, high = (int(symbol) - 0.5) / 10, (int(symbol) + 0.5) / 10
        lower.append(low)
        upper.append(high)
    n = len(lower)
    result.update(posterior_residue_count=n, posterior_missing_residue_count=missing,
        posterior_lower_sum=math.fsum(lower), posterior_upper_sum=math.fsum(upper),
        posterior_lower_mean=math.fsum(lower) / n if n else None,
        posterior_upper_mean=math.fsum(upper) / n if n else None,
        posterior_upper_inclusive=all(symbol == "*" for symbol in bins) if n else None)
    return result, None if n else "posterior_no_scored_sequence_residues"


def _cutoff_margins(row, sheet, native_score):
    facts = row["native"]
    target_model = sheet["operation"]["program"] == "nhmmscan"
    name = facts.get("target_name" if target_model else "query_name")
    accession = facts.get("target_accession" if target_model else "query_accession")
    matches = []
    for index, entry in enumerate(sheet.get("inputs", {}).get("model_cutoffs") or []):
        if not isinstance(entry, dict):
            continue
        if entry.get("name") is not None and entry["name"] != name:
            continue
        if entry.get("accession") is not None and entry["accession"] != accession:
            continue
        if entry.get("name") is not None or entry.get("accession") is not None:
            matches.append((index, entry))
    result = []
    for index, entry in matches:
        for family in ("GA", "TC", "NC"):
            if family not in entry:
                continue
            supplied = entry[family]
            cutoff = supplied.get("sequence_bits") if isinstance(supplied, dict) else supplied
            reason = ("ambiguous_model_cutoffs" if len(matches) != 1 else
                      "missing_or_invalid_per_hit_cutoff" if not _valid_number(cutoff) else
                      "native_score_unavailable" if native_score is None else None)
            margin = native_score - cutoff if reason is None else None
            if margin is not None and not _valid_number(margin):
                margin, reason = None, "cutoff_margin_overflow"
            result.append({"model_name": name, "model_accession": accession, "cutoff": family,
                "scope": "nucleotide_locus_per_hit", "supplied": deepcopy(supplied),
                "native_score_bits": native_score, "cutoff_bits": cutoff if _valid_number(cutoff) else None,
                "margin_bits": margin,
                "input_fields": ["native.score_bits", f"inputs.model_cutoffs/{index}/{family}"],
                "unavailable_reason": reason, "domain_bits_used": False})
    return result


def _score_locus(row, sheet):
    issues = deepcopy(row.get("issues", []))
    result = {"record_key": row.get("record_key"), "locator": deepcopy(row.get("locator")),
        "status": row.get("status"), "query_record_key": row.get("query_record_key"),
        "query_occurrence": row.get("query_occurrence"), "target_occurrence": row.get("target_occurrence"),
        "identities": {key: row.get("native", {}).get(key) for key in TBL_IDENTITY_FIELDS},
        "strand": row.get("native", {}).get("strand"), "iteration": None,
        "native_status": {key: row.get("native", {}).get(key) for key in ("reported", "included", "inclusion_flag")},
        "coordinates": deepcopy(row.get("coordinates", {})), "native": {}, "derived": {},
        "components": {}, "issues": issues}
    invalid = row.get("status") == "invalid"
    for name, (source, unit) in _NATIVE.items():
        value = row.get("native", {}).get(source)
        valid = not invalid and _valid_number(value) and (source != "evalue" or value >= 0) and (source != "accuracy" or 0 <= value <= 1)
        value = value if valid else None
        result[name] = result["native"][name] = value
        result["components"][name] = _cell(value, inputs=["native." + source], unit=unit,
            reason="native_row_invalid" if invalid else "native_value_unavailable_or_invalid")
        if name == "native_accuracy":
            envelope = row.get("coordinates", {}).get("sequence_envelope_interval")
            result["components"][name].update(
                denominator=envelope[1] - envelope[0] if _valid_interval(envelope) else None,
                numerator_unavailable_reason="native_oasc_not_printed",
                input_fields=["native.accuracy", "coordinates.sequence_envelope_interval"])
    for key in ("model_length", "sequence_length"):
        value = row.get(key)
        value = value if _valid_length(value) and not invalid else None
        result[key] = result["derived"][key] = value
        result["components"][key] = _cell(value, inputs=[key, "length_sources." + key],
            unit="model_positions" if key == "model_length" else "nucleotides",
            reason="full_length_unavailable_or_conflicting", sources=deepcopy(row.get("length_sources", {}).get(key, [])))
    for key, (axis, unit) in _SPANS.items():
        interval = row.get("coordinates", {}).get(axis)
        length = result["model_length" if axis == "model_interval" else "sequence_length"]
        valid = not invalid and _valid_interval(interval) and (length is None or interval[1] <= length)
        value = interval[1] - interval[0] if valid else None
        result[key] = result["derived"][key] = value
        result["components"][key] = _cell(value, inputs=["coordinates." + axis], unit=unit,
            reason="coordinates_unavailable_or_invalid", coordinate_convention="zero_based_half_open")
    aligned, alignment_reason = _alignment_components(row) if not invalid else ({name: None for name in _COUNTS}, "native_row_invalid")
    for key in _COUNTS:
        value = aligned.get(key)
        result[key] = result["derived"][key] = value
        result["components"][key] = _cell(value, inputs=["alignment.model_aligned", "alignment.sequence_aligned"],
            unit="alignment_positions", reason=alignment_reason or "alignment_unavailable")
    for key, (numerator, denominator) in _COVERAGES.items():
        n, d = result[numerator], result[denominator]
        value = n / d if n is not None and d is not None and n <= d else None
        reason = "numerator_unavailable" if n is None else "full_length_unavailable_or_conflicting" if d is None else "numerator_exceeds_full_length"
        result[key] = result["derived"][key] = value
        result["components"][key] = _cell(value, inputs=[numerator, denominator], unit="fraction",
            numerator=n, denominator=d, reason=reason)
    for key in ("posterior_lower_mean", "posterior_upper_mean"):
        value = aligned.get(key)
        result[key] = result["derived"][key] = value
        result["components"][key] = _cell(value, inputs=["alignment.posterior", "alignment.sequence_aligned"],
            unit="posterior_fraction_bound", numerator=aligned.get(key.replace("mean", "sum")),
            denominator=aligned.get("posterior_residue_count"), reason=alignment_reason or "posterior_unavailable",
            bound_inclusive=True if key == "posterior_lower_mean" else aligned.get("posterior_upper_inclusive"),
            population="sequence residues with native PP bins", missing_residue_count=aligned.get("posterior_missing_residue_count"))
    result["paired_model_intervals"] = aligned.get("paired_model_intervals")
    result["paired_sequence_intervals"] = aligned.get("paired_sequence_intervals")
    result["cutoff_margins"] = _cutoff_margins(row, sheet, result["native_score_bits"])
    result["union_identity"] = deepcopy(row.get("union_identity"))
    result["availability"] = {key: cell["unavailable_reason"] for key, cell in result["components"].items() if cell["value"] is None}
    return result


TBL_IDENTITY_FIELDS = ("query_name", "query_accession", "target_name", "target_accession")


def _group_unions(rows):
    groups = defaultdict(list)
    for row in rows:
        identity = row.get("union_identity")
        if identity and row["status"] != "invalid" and identity.get("query") and identity.get("target") and identity.get("strand") in {"+", "-"}:
            groups[(identity["query"], identity["target"], identity["strand"], identity.get("iteration"))].append(row)
    result = []
    for key, members in groups.items():
        group = {"query_identity": key[0], "target_identity": key[1], "strand": key[2], "iteration": key[3],
            "record_keys": [row["record_key"] for row in members], "union_components": {}, "issues": []}
        for name, axis, length_key in (("model_span", "model_interval", "model_length"),
                ("sequence_span", "sequence_interval", "sequence_length"),
                ("sequence_envelope", "sequence_envelope_interval", "sequence_length"),
                ("paired_model", "paired_model_intervals", "model_length"),
                ("paired_sequence", "paired_sequence_intervals", "sequence_length")):
            all_intervals, omitted = [], []
            for row in members:
                values = row.get(axis) if axis.startswith("paired_") else [row["coordinates"].get(axis)]
                if values is None or any(not _valid_interval(value) for value in values):
                    omitted.append(row["record_key"])
                else:
                    all_intervals.extend(values)
            merged = _union(all_intervals)
            count = sum(end - start for start, end in merged) if all_intervals or not omitted else None
            lengths = {row[length_key] for row in members if row[length_key] is not None}
            conflicting = any(any(issue.get("code") == "nhmmer_conflicting_lengths" and issue.get("field") == length_key
                for issue in row["issues"] if isinstance(issue, dict)) for row in members)
            denominator = next(iter(lengths)) if len(lengths) == 1 else None
            if conflicting:
                denominator = None
            coverage = count / denominator if count is not None and denominator and count <= denominator else None
            group["union_components"][name] = {"positions": count, "intervals": merged,
                "numerator": count, "denominator": denominator, "coverage": coverage,
                "unit": "model_positions" if "model" in name else "nucleotides",
                "coordinate_convention": "zero_based_half_open", "input_fields": [axis, length_key],
                "included_record_count": len(members) - len(omitted), "omitted_record_keys": omitted,
                "population": "observed identified loci only", "all_supplied_loci_measured": not omitted,
                "hit_population_complete": None,
                "unavailable_reason": "all_intervals_unavailable" if count is None else "full_length_unavailable_or_conflicting" if denominator is None else None}
        result.append(group)
    return result


def calculate_nhmmer_scores(sheet, *, parameters=None):
    """Calculate inspectable locus components; only None/{} is supported.

The sheet's parsed native values are authoritative inputs. This function does
not read/reparse ``sheet.native.artifacts``; removing retained raw text leaves
all numerical calculations unchanged.
"""
    if type(sheet) is not dict:
        raise ValueError("nhmmer_invalid_sheet_type")
    sheet = finite_json(sheet, name="sheet")
    if sheet.get("schema") != "nhmmer_sheet_v1":
        raise ValueError("nhmmer_invalid_sheet_schema")
    if parameters is not None and type(parameters) is not dict:
        raise ValueError("nhmmer_invalid_parameters_type")
    parameters = finite_json(parameters or {}, name="parameters")
    if parameters:
        raise ValueError("nhmmer_unsupported_parameters:" + ",".join(sorted(parameters)))
    if type(sheet.get("loci")) is not list or type(sheet.get("queries")) is not list:
        raise ValueError("nhmmer_invalid_sheet_rows")
    operation = sheet.get("operation")
    if type(operation) is not dict or operation.get("program") not in {"nhmmer", "nhmmscan"}:
        raise ValueError("nhmmer_invalid_sheet_operation")
    issues, loci = deepcopy(sheet.get("issues", [])), []
    for index, row in enumerate(sheet["loci"]):
        if (type(row) is not dict or type(row.get("native")) is not dict or type(row.get("coordinates")) is not dict
                or type(row.get("issues", [])) is not list or type(row.get("length_sources", {})) is not dict
                or type(row.get("union_identity")) not in (dict, type(None))):
            issues.append({"code": "nhmmer_invalid_sheet_locus", "row_index": index})
            continue
        loci.append(_score_locus(row, sheet))
    unions = _group_unions(loci)
    queries = []
    for query in sheet["queries"]:
        if not isinstance(query, dict) or not query.get("record_key") or not isinstance(query.get("locator"), dict):
            issues.append({"code": "nhmmer_invalid_sheet_query"})
            continue
        owned = [row for row in loci if row.get("query_record_key") == query["record_key"]]
        queries.append({"record_key": query["record_key"], "locator": deepcopy(query["locator"]),
            "name": query.get("name"), "accession": query.get("accession"), "occurrence": query.get("occurrence"),
            "native_query_length": query.get("length"), "native_query_length_axis": query.get("length_axis"),
            "native_terminated": query.get("terminated"), "native_reported_locus_count": query.get("locus_count"),
            "scored_record_keys": [row["record_key"] for row in owned],
            "searched_space": deepcopy(query.get("statistics", [])),
            "native_settings": deepcopy(sheet.get("native_settings", [])),
            "unions": [group for group in unions if group["query_identity"] == query["record_key"]],
            "issues": deepcopy(query.get("issues", []))})
    unbound = [group for group in unions if group["query_identity"] not in {q["record_key"] for q in queries}]
    if unbound:
        queries.append({"record_key": "inputs/query", "locator": {"input_field": "inputs.query"},
            "name": (sheet.get("inputs", {}).get("query") or {}).get("name"), "occurrence": None,
            "native_terminated": None, "native_reported_locus_count": None,
            "unions": unbound, "searched_space": [], "issues": []})
    return {"schema": "nhmmer_scores_v1", "operation": deepcopy(operation), "parameters": parameters,
        "loci": loci, "queries": queries, "definitions": _definitions(), "issues": issues,
        "completeness": deepcopy(sheet.get("completeness", {})),
        "supplied_native_parameters": deepcopy(sheet.get("inputs", {}).get("native_parameters")),
        "unused_metadata": ["function_assignments", "taxon", "family", "clan", "sample", "contig", "database.population"]}
