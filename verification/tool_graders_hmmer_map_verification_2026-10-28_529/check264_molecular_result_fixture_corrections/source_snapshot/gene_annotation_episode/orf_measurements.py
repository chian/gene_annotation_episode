"""Supplied exhaustive-ORF measurements, separate from native enumeration.

No Bio, Store, files, resource selection, enumeration or protein generation is
used here. Native results, complete input/request and frozen reference data stay
separate. Coordinates and codon compatibility reuse the existing authorities.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .sequence_extraction_grader import frozen_reverse_complement
from .sequence_mapping import map_interval, reverse_path, slice_path, validate_mapping
from .sequence_translation_grader import inspect_frozen_codon, inspect_frozen_genetic_code


NATIVE_SCHEMA = "biomni_orf_native_record_v1"
SHEET_SCHEMA = "orf_measurement_sheet_v1"
COMPONENT_SCHEMA = "orf_measurement_components_v1"
_FIELDS = ("sequence", "aa_sequence", "start", "end", "strand", "frame")
_DNA = frozenset("ACGTRYSWKMBDHVN")
_STOPS = frozenset(("TAA", "TAG", "TGA"))
_REQUEST = {"min_length", "search_reverse", "filter_subsets"}
_INPUTS = {"native_record", "input_sequence", "subject_ref", "parent_mapping", "request", "genetic_code"}


def _issue(issues, code, path="", **details):
    item = {"code": code, "path": path, **details}
    if item not in issues:
        issues.append(item)


def _capture(value):
    """Keep finite JSON literally; unavailable values have explicit rejection rows.

    A rejected value's JSON position is null, never a fabricated measurement.
    Its original type and nonfinite token remain separate from native metadata.
    """
    rejected = []

    def visit(item, path):
        if item is None or type(item) in (str, int, bool):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        if type(item) is list:
            return [visit(child, path + "/" + str(i)) for i, child in enumerate(item)]
        if type(item) is dict and all(type(k) is str for k in item):
            return {k: visit(v, path + "/" + k.replace("~", "~0").replace("/", "~1")) for k, v in item.items()}
        rejected.append({"path": path, "value_type": type(item).__name__,
            "nonfinite_token": repr(item) if type(item) is float else None})
        return None

    try:
        return visit(value, ""), rejected
    except RecursionError as error:
        raise ValueError("orf_nested_data_too_deep") from error


def _same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def _translation(dna, protein, table, observed_settings):
    result = {"state": "unknown", "codons": [], "termination_codon_index": None,
        "termination_codon": None, "early_ambiguity_termination": None,
        "untranslated_suffix_nt": None, "omitted_stop_codon_count": None}
    if type(dna) is not str or set(dna) - _DNA or len(dna) % 3:
        return result
    for index in range(len(dna) // 3):
        codon = dna[index * 3:index * 3 + 3]
        operands = inspect_frozen_codon(codon, table, role="ordinary", cds=False)
        result["codons"].append({"codon_index": index, "codon": codon, "table_operands": operands})
    if not observed_settings or table is None:
        return result
    stop = next((r["codon_index"] for r in result["codons"]
        if r["table_operands"]["expected_symbol"] == "*" and r["table_operands"]["reason"] is None), None)
    if stop is None:
        return result
    before = result["codons"][:stop]
    if any(row["table_operands"]["reason"] is not None or row["table_operands"]["expected_symbol"] is None for row in before):
        return result
    termination = dna[3 * stop:3 * stop + 3]
    result.update(termination_codon_index=stop, termination_codon=termination,
        early_ambiguity_termination=stop < len(result["codons"]) - 1 and bool(set(termination) - set("ACGT")),
        untranslated_suffix_nt=len(dna) - 3 * (stop + 1), omitted_stop_codon_count=1)
    if type(protein) is not str:
        return result
    result["state"] = ("compatible" if len(protein) == stop and all(
        protein[i] == row["table_operands"]["expected_symbol"] for i, row in enumerate(before)) else "incompatible")
    return result


def _populate(inputs, rejected):
    issues = [{"code": "orf_non_json_value_rejected", **row} for row in rejected]
    native, sequence, request = (inputs[k] for k in ("native_record", "input_sequence", "request"))
    sequence_ok = type(sequence) is str and not set(sequence.upper()) - _DNA
    if not sequence_ok:
        _issue(issues, "orf_complete_dna_input_required", "/input_sequence")
    length = len(sequence) if type(sequence) is str else None
    request_ok = (type(request) is dict and set(request) == _REQUEST
        and type(request.get("min_length")) is int and request["min_length"] >= 0
        and all(type(request.get(k)) is bool for k in ("search_reverse", "filter_subsets")))
    if not request_ok:
        _issue(issues, "orf_explicit_request_required", "/request")
    source = native if type(native) is dict else {}
    if source.get("schema") != NATIVE_SCHEMA:
        _issue(issues, "orf_native_record_schema_required", "/native_record/schema")
    outcome = source.get("outcome")
    if outcome not in ("completed", "failed", "partial", "truncated"):
        outcome = "unknown"
        _issue(issues, "orf_native_outcome_required", "/native_record/outcome")
    if outcome != "completed":
        _issue(issues, "orf_native_population_" + outcome, "/native_record/outcome")
    if outcome == "failed" and type(source.get("failure")) is not dict:
        _issue(issues, "orf_native_failure_detail_required", "/native_record/failure")
    if outcome == "completed" and source.get("failure") is not None:
        _issue(issues, "orf_native_outcome_failure_conflict", "/native_record/failure")
    identity = source.get("source_identity")
    if not (type(identity) is dict and identity.get("callable") == "annotate_open_reading_frames"
        and type(identity.get("path")) is str and bool(identity["path"])
        and type(identity.get("sha256")) is str and re.fullmatch("[0-9a-f]{64}", identity["sha256"])):
        _issue(issues, "orf_source_identity_unavailable", "/native_record/source_identity")
    version = source.get("biopython_version")
    observed_settings = _same(source.get("translation"), {"table": "Standard", "to_stop": True, "cds": False})
    if not observed_settings:
        _issue(issues, "orf_observed_translation_settings_unavailable", "/native_record/translation")
    table = None
    if type(version) is not str or not version:
        _issue(issues, "orf_native_library_version_unavailable", "/native_record/biopython_version")
    elif observed_settings:
        table_issues = []
        table, table_state = inspect_frozen_genetic_code(inputs["genetic_code"], source, {"code": 1}, table_issues)
        issues.extend({"path": "/genetic_code", **row} for row in table_issues)
        if table_state["state"] != "present":
            _issue(issues, "orf_frozen_genetic_code_" + table_state["state"], "/genetic_code")
    mapping = inputs["parent_mapping"]
    mapping_ok = False
    try:
        validate_mapping(mapping)
        mapping_ok = (type(inputs["subject_ref"]) is str and bool(inputs["subject_ref"])
            and mapping["units_per_symbol"] == 1 and mapping["symbol_length"] == length
            and all(row["unit"] in ("nt", "symbol") for row in mapping["path"]))
    except (ValueError, TypeError, KeyError):
        pass
    if not mapping_ok:
        _issue(issues, "orf_original_source_mapping_unavailable", "/parent_mapping")
    result = source.get("result")
    raw_rows = result.get("orfs") if type(result) is dict else None
    if type(raw_rows) is not list:
        _issue(issues, "orf_native_rows_unavailable", "/native_record/result/orfs")
    rows = []
    for index, raw in enumerate(raw_rows if type(raw_rows) is list else []):
        path = "/native_record/result/orfs/" + str(index)
        local = []
        values = dict(zip(_FIELDS, raw)) if type(raw) is list and len(raw) == 6 else raw if type(raw) is dict else {}
        if type(values) is not dict or set(values) != set(_FIELDS):
            _issue(local, "orf_native_row_fields_required", path)
            values = values if type(values) is dict else {}
        start, end, strand, frame = (values.get(k) for k in ("start", "end", "strand", "frame"))
        dna, protein = values.get("sequence"), values.get("aa_sequence")
        interval = ([start, end] if type(start) is int and type(end) is int and length is not None
            and 0 <= start < end <= length else None)
        if interval is None:
            _issue(local, "orf_interval_outside_full_input_or_missing", path)
        orientation_ok = strand in ("+", "-") and type(frame) is int and frame in (1, 2, 3, -1, -2, -3)
        if not orientation_ok:
            _issue(local, "orf_strand_and_frame_required", path)
        definition = "unknown"
        if sequence_ok and interval is not None and orientation_ok and request_ok:
            expected = sequence[start:end].upper()
            if strand == "-":
                expected = frozen_reverse_complement(expected, molecule="dna")
            expected_frame = start % 3 + 1 if strand == "+" else -((length - end) % 3 + 1)
            valid = (dna == expected and type(dna) is str and len(dna) >= max(6, request["min_length"])
                and len(dna) % 3 == 0 and dna.startswith("ATG") and dna[-3:] in _STOPS
                and not any(dna[j:j + 3] in _STOPS for j in range(0, len(dna) - 3, 3))
                and frame == expected_frame and (strand == "+" or request["search_reverse"]))
            definition = "compatible" if valid else "incompatible"
            if not valid:
                _issue(local, "orf_source_definition_or_input_conflict", path)
        if type(dna) is not str:
            _issue(local, "orf_nucleotide_symbols_unavailable", path + "/sequence")
        if type(protein) is not str:
            _issue(local, "orf_protein_symbols_unavailable", path + "/aa_sequence")
        translation = _translation(dna, protein, table, observed_settings)
        if translation["state"] != "compatible":
            _issue(local, "orf_translation_" + translation["state"], path + "/aa_sequence")
        if translation["early_ambiguity_termination"]:
            _issue(local, "orf_translation_terminates_before_literal_orf_stop", path + "/aa_sequence")
        orf_path = protein_path = stop_path = None
        if mapping_ok and definition == "compatible":
            orf_path = map_interval(mapping, start, end)
            if strand == "-":
                orf_path = reverse_path(orf_path)
            if translation["state"] == "compatible":
                protein_path = slice_path(orf_path, 0, 3 * len(protein))
                stop = translation["termination_codon_index"] * 3
                stop_path = slice_path(orf_path, stop, stop + 3)
        rows.append({"row_index": index, "native_row": deepcopy(raw), "interval": interval,
            "strand": strand if strand in ("+", "-") else None,
            "frame": frame if orientation_ok else None,
            "interval_length_nt": end - start if interval is not None else None,
            "nucleotide_symbol_count": len(dna) if type(dna) is str else None,
            "protein_symbol_count": len(protein) if type(protein) is str else None,
            "source_definition": definition, "translation": translation,
            "orf_source_path": orf_path, "protein_source_path": protein_path,
            "omitted_stop_source_path": stop_path, "issues": local})
        issues.extend(local)
    previous = None
    for row in rows:
        n, strand, frame, span = (row[k] for k in ("nucleotide_symbol_count", "strand", "frame", "interval"))
        if n is not None and span is not None and frame is not None and strand is not None:
            key = (-n, 0 if strand == "+" else 1, abs(frame), span[0] if strand == "+" else length - span[1])
            if previous is not None and key < previous:
                _issue(issues, "orf_source_order_conflict", "/rows/" + str(row["row_index"]))
            previous = key
    if request_ok and request["filter_subsets"]:
        for i, row in enumerate(rows):
            if row["interval"] is None:
                continue
            for other in rows[:i]:
                if other["interval"] is not None and row["strand"] is not None and row["strand"] == other["strand"]:
                    if other["interval"][0] <= row["interval"][0] and row["interval"][1] <= other["interval"][1]:
                        _issue(issues, "orf_source_subset_filter_conflict", "/rows/" + str(i))
                        break
    measurements = {"input_length_nt": length,
        "reported_row_count": len(raw_rows) if type(raw_rows) is list else None}
    return {"rows": rows, "measurements": measurements, "native_outcome": outcome,
        "population_scope": "all_retained_native_rows_in_original_order; completeness_is_only_the_recorded_outcome",
        "issues": issues, "status": "partial" if issues else "complete"}


def build_orf_sheet(native_record, *, input_sequence, subject_ref, parent_mapping, request, genetic_code=None):
    """Populate a sheet from full supplied input, native output and references.

    Native orfs accept the original six-position JSON arrays or explicit objects
    with those six fields. No rows are searched, padded, deduplicated or sorted.
    Metadata identities/versions are retained from the caller, never invented.
    """
    inputs, rejected = _capture({"native_record": native_record, "input_sequence": input_sequence,
        "subject_ref": subject_ref, "parent_mapping": parent_mapping, "request": request, "genetic_code": genetic_code})
    return {"schema": SHEET_SCHEMA, "inputs": inputs, "rejected_values": rejected, **_populate(inputs, rejected)}


def _definitions():
    rows = {
        "input_length_nt": ("len(full supplied input string)", "nt_symbols", "entire supplied input; nominal DNA symbols even if its alphabet is incompatible"),
        "reported_row_count": ("len(native result.orfs)", "rows", "all supplied native rows, including malformed rows and repeated occurrences"),
        "usable_saved_row_count": ("count unchanged saved rows", "rows", "saved rows agreeing with their retained operands; corrupt/missing saved rows excluded"),
        "forward_row_count": ("count strand == '+'", "rows", "usable saved rows with the literal supplied forward strand"),
        "reverse_row_count": ("count strand == '-'", "rows", "usable saved rows with the literal supplied reverse strand"),
        "strand_known_row_count": ("count recognized '+' or '-' strand", "rows", "usable saved rows; unknown strands do not count as forward or reverse"),
        "retained_length_sum_nt": ("sum actual nucleotide-string lengths", "nt_symbols", "usable saved rows having a nucleotide string, including incompatible source definitions or translations"),
        "retained_length_denominator_rows": ("count available nucleotide strings", "rows", "same exact string-length population; excludes unavailable strings and corrupt/missing saved rows"),
        "mean_retained_orf_length_nt": ("retained_length_sum_nt / retained_length_denominator_rows", "nt_symbols_per_row", "same exact retained string-length population; not a complete-enumeration mean unless separately evidenced"),
        "source_definition_compatible_row_count": ("count source_definition == 'compatible'", "rows", "usable saved rows passing literal input/interval/frame/start/stop/request consistency checks; not confidence"),
        "translation_compatible_row_count": ("count translation.state == 'compatible'", "rows", "usable saved rows consistent with supplied observed settings and frozen codon reference; not confidence"),
        "interval_length_nt": ("validated interval end - start", "nt", "one native row's bounded geometric interval; separate from actual nucleotide-string length"),
        "nucleotide_symbol_count": ("len(actual native nucleotide string)", "nt_symbols", "one actual retained string, even when source-definition or translation compatibility fails"),
        "protein_symbol_count": ("len(actual native protein string)", "product_symbols", "all literal returned symbols; no inferred or replacement protein"),
        "termination_codon_index": ("first reference-supported stop after fully known preceding codons", "zero_based_codon_index", "the retained oriented ORF nucleotide string under observed Standard/to_stop settings"),
        "untranslated_suffix_nt": ("nucleotide-string length - 3 * (termination_codon_index + 1)", "nt_symbols", "retained nucleotide suffix after the omitted translation stop; excludes that stop"),
        "omitted_stop_codon_count": ("1 for a reference-supported translation stop", "codons", "the identified stop is omitted by to_stop=True; no CDS validation is asserted"),
    }
    result = {key: {"calculation": formula, "unit": unit, "population": population,
        "missing_behavior": "null when required operands or saved cells are unavailable/incompatible; independent observed counts survive"}
        for key, (formula, unit, population) in rows.items()}
    result["usable_saved_row_count"]["missing_behavior"] = "zero means no usable saved rows; it does not establish zero native ORFs"
    result["retained_length_denominator_rows"]["missing_behavior"] = "zero means no available strings in the usable saved population, not a measured zero ORF length"
    result["mean_retained_orf_length_nt"]["missing_behavior"] = "null for zero denominator or unavailable numerator; preserve the actual partial/corrupt-row denominator separately"
    result["retained_length_sum_nt"]["missing_behavior"] = "null without a native row list or an intact reported-row-count cell; an empty available-string population sums to zero with denominator zero"
    result["native_summary_comparisons"] = {"calculation": "native_value - retained_population_value; signed, with no rescaling",
        "units": {"total_orfs": "rows", "forward_orfs": "rows", "reverse_orfs": "rows", "avg_length": "nt_symbols_per_row"},
        "population": "total_orfs uses retained native row count; strand comparisons require every saved row usable and every strand known; avg_length comparison additionally requires every actual nucleotide-string length. No difference certifies complete enumeration",
        "missing_behavior": "null difference when either operand is unavailable; native values remain separate. avg_length compares native one-decimal rounding, including its empty-list zero convention; the calculated empty-population mean remains null"}
    result["combinations"] = "only the explicit string-length mean and signed native-summary differences; no score or annotation probability"
    return result


def calculate_orf_components(sheet):
    """Calculate saved numerical rows, leaving corrupted saved cells unavailable."""
    saved, newly_rejected = _capture(sheet)
    if not (type(saved) is dict and saved.get("schema") == SHEET_SCHEMA
        and type(saved.get("inputs")) is dict and set(saved["inputs"]) == _INPUTS
        and type(saved.get("rejected_values")) is list):
        raise ValueError("orf_saved_sheet_required")
    if not all(type(r) is dict and set(r) == {"path", "value_type", "nonfinite_token"}
        and type(r["path"]) is str and type(r["value_type"]) is str for r in saved["rejected_values"]):
        raise ValueError("orf_rejected_value_records_invalid")
    expected = _populate(saved["inputs"], saved["rejected_values"])
    issues = deepcopy(expected["issues"])
    issues.extend({"code": "orf_saved_non_json_value_rejected", **row} for row in newly_rejected)
    measurements = {}
    for key, value in expected["measurements"].items():
        actual = saved.get("measurements")
        if type(actual) is dict and key in actual and _same(actual[key], value):
            measurements[key] = deepcopy(actual[key])
        else:
            measurements[key] = None
            _issue(issues, "orf_saved_cell_conflicts_with_operands", "/measurements/" + key)
    rows = []
    supplied = saved.get("rows")
    for i, wanted in enumerate(expected["rows"]):
        actual = supplied[i] if type(supplied) is list and i < len(supplied) else None
        if _same(actual, wanted):
            rows.append(deepcopy(actual))
        else:
            rows.append({"row_index": i, "saved_row": deepcopy(actual), "state": "incompatible"})
            _issue(issues, "orf_saved_row_conflicts_with_operands", "/rows/" + str(i))
    if type(supplied) is not list or len(supplied) != len(expected["rows"]):
        _issue(issues, "orf_saved_row_population_conflict", "/rows")
    for key in ("issues", "native_outcome", "population_scope", "status"):
        if not _same(saved.get(key), expected[key]):
            _issue(issues, "orf_saved_metadata_conflict", "/" + key)
    usable = [r for r in rows if r.get("state") != "incompatible"]
    lengths = [r["nucleotide_symbol_count"] for r in usable if r["nucleotide_symbol_count"] is not None]
    have_rows = measurements["reported_row_count"] is not None
    numerator, denominator = sum(lengths) if have_rows else None, len(lengths)
    mean = numerator / denominator if numerator is not None and denominator else None
    summary = {**measurements, "usable_saved_row_count": len(usable),
        "forward_row_count": sum(r["strand"] == "+" for r in usable) if have_rows else None,
        "reverse_row_count": sum(r["strand"] == "-" for r in usable) if have_rows else None,
        "strand_known_row_count": sum(r["strand"] is not None for r in usable) if have_rows else None,
        "retained_length_sum_nt": numerator, "retained_length_denominator_rows": denominator,
        "mean_retained_orf_length_nt": mean,
        "source_definition_compatible_row_count": sum(r["source_definition"] == "compatible" for r in usable) if have_rows else None,
        "translation_compatible_row_count": sum(r["translation"]["state"] == "compatible" for r in usable) if have_rows else None}
    native = saved["inputs"]["native_record"]
    result = native.get("result") if type(native) is dict else None
    native_summary = result.get("summary_stats") if type(result) is dict else None
    comparisons = {}
    all_rows_usable = measurements["reported_row_count"] is not None and len(usable) == measurements["reported_row_count"]
    reference = {"total_orfs": measurements["reported_row_count"],
        "forward_orfs": summary["forward_row_count"] if all_rows_usable and summary["strand_known_row_count"] == len(usable) else None,
        "reverse_orfs": summary["reverse_row_count"] if all_rows_usable and summary["strand_known_row_count"] == len(usable) else None,
        "avg_length": round(mean, 1) if all_rows_usable and denominator == len(usable) and mean is not None
            else 0 if all_rows_usable and not usable else None}
    for key, observed in reference.items():
        raw = native_summary.get(key) if type(native_summary) is dict else None
        present = type(raw) in (int, float)
        comparisons[key] = {"native_value": raw, "retained_population_value": observed,
            "difference": raw - observed if present and observed is not None else None}
        if not present:
            _issue(issues, "orf_native_summary_value_unavailable", "/native_record/result/summary_stats/" + key)
        elif observed is not None and raw != observed:
            _issue(issues, "orf_native_summary_conflicts_with_retained_rows", "/native_record/result/summary_stats/" + key)
    return {"schema": COMPONENT_SCHEMA, "status": "partial" if issues else "complete",
        "native_outcome": expected["native_outcome"], "population_scope": expected["population_scope"],
        "summary": summary, "rows": rows, "native_summary_comparisons": comparisons, "issues": issues,
        "definitions": _definitions(),
        "mean_definition": "sum actual retained nucleotide-string lengths / rows with those strings; no-ORF mean is null; native empty-population zero is retained separately",
        "meaning": "literal ATG-to-next-literal-stop ORF measurements; not gene prediction, coding validation or annotation confidence"}


__all__ = ["NATIVE_SCHEMA", "SHEET_SCHEMA", "COMPONENT_SCHEMA", "build_orf_sheet", "calculate_orf_components"]
