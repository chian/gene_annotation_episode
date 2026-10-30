"""Read supplied all-placement primer rows and calculate saved measurements.

This is not an aligner or a PCR workflow. No missing placements are enumerated.
Full original target/primer operands, native output/errors and source identities
remain separate from the numerical sheet. Only shared pure column/coordinate
arithmetic is reused; no other producer's native envelope is manufactured.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .biopython_pairwise_grader import count_literal_alignment_columns
from .sequence_extraction_grader import frozen_reverse_complement
from .sequence_mapping import map_interval, reverse_path, slice_path, validate_mapping


NATIVE_SCHEMA = "biomni_primer_placement_native_v1"
SHEET_SCHEMA = "primer_placement_sheet_v1"
COMPONENT_SCHEMA = "primer_placement_components_v1"
_DNA = frozenset("ACGT")
_INPUT_KEYS = {"native_record", "target_sequence", "primers", "target_ref", "primer_refs", "target_mapping", "primer_mappings"}


def _issue(issues, code, path=""):
    row = {"code": code, "path": path}
    if row not in issues:
        issues.append(row)


def _capture(value):
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
        raise ValueError("primer_placement_nested_data_too_deep") from error


def _same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def _source_reverse(primer):
    # Preserve the actual source bug/qualification: only A/C/G/T complement.
    # Other symbols remain literal, rather than becoming an IUPAC complement.
    return "".join(frozen_reverse_complement(c, molecule="dna") if c in _DNA else c for c in reversed(primer))


def _mapped(mapping, reference, length, interval, *, reverse=False):
    if mapping is None or type(reference) is not str or not reference:
        return {"state": "unavailable", "intervals": None}
    try:
        validate_mapping(mapping)
        if (mapping["units_per_symbol"] != 1 or mapping["symbol_length"] != length
            or any(p["unit"] not in ("nt", "symbol") for p in mapping["path"])):
            raise ValueError("primer_placement_mapping_conflict")
        path = map_interval(mapping, *interval)
        return {"state": "available", "intervals": reverse_path(path) if reverse else path}
    except (ValueError, TypeError, KeyError):
        return {"state": "incompatible", "intervals": None}


def _hit(raw, *, ordinal, primer, target, associated, target_ref, primer_ref, target_mapping, primer_mapping):
    issues = []
    value = raw if type(raw) is dict else {}
    if type(raw) is not dict or set(value) != {"position", "strand", "mismatches"}:
        _issue(issues, "primer_native_hit_fields_required")
    position, strand = value.get("position"), value.get("strand")
    width = len(primer) if type(primer) is str else None
    recognized = strand in ("+", "-")
    oriented = (primer if strand == "+" else _source_reverse(primer)) if type(primer) is str and recognized else None
    interval = ([position, position + width] if type(position) is int and width is not None and width > 0
        and type(target) is str and 0 <= position <= len(target) - width else None)
    window = target[slice(*interval)] if interval is not None else None
    if not recognized:
        _issue(issues, "primer_native_strand_required")
    if interval is None:
        _issue(issues, "primer_empty_pseudo_hit_unsupported" if width == 0 else "primer_native_position_outside_complete_target")
    canonical = oriented is not None and width > 0 and window is not None and not (set(oriented) | set(window)) - _DNA
    interpretation = "canonical_dna_window" if canonical else "empty_primer_unsupported" if width == 0 else "noncanonical_literal_only" if oriented is not None and window is not None else "unavailable"
    if interpretation == "noncanonical_literal_only":
        _issue(issues, "primer_source_noncanonical_rc_is_not_iupac_science")
    native_mismatches = value.get("mismatches")
    triples = native_mismatches if type(native_mismatches) is list else []
    if type(native_mismatches) is not list:
        _issue(issues, "primer_native_mismatch_list_unavailable")
    # Check only this supplied placement, never any absent target window.
    expected = ([[j, oriented[j], window[j]] for j in range(width) if oriented[j] != window[j]]
        if interval is not None and oriented is not None else None)
    mismatch_list_matches = expected is not None and type(native_mismatches) is list and _same(native_mismatches, expected)
    if expected is not None and not mismatch_list_matches:
        _issue(issues, "primer_native_mismatches_conflict_with_full_operands")
    columns = count_literal_alignment_columns(oriented, window) if canonical else None
    count = columns["substituted_positions"] if columns is not None else None
    if expected is not None and len(expected) > 1:
        _issue(issues, "primer_source_one_mismatch_acceptance_conflict")
    acceptance = ("unsupported" if interpretation in ("empty_primer_unsupported", "noncanonical_literal_only") else
        "unavailable" if interval is None or oriented is None else
        "compatible" if associated and mismatch_list_matches and len(expected) <= 1 and not issues else "incompatible")
    target_path = primer_path = {"state": "unavailable", "intervals": None}
    if acceptance == "compatible":
        target_path = _mapped(target_mapping, target_ref, len(target), interval)
        primer_path = _mapped(primer_mapping, primer_ref, width, [0, width], reverse=strand == "-")
        for role, path in (("target", target_path), ("primer", primer_path)):
            if path["state"] != "available":
                _issue(issues, "primer_" + role + "_original_mapping_" + path["state"])
    mismatches = []
    for index, triple in enumerate(triples):
        valid = (type(triple) is list and len(triple) == 3 and type(triple[0]) is int
            and width is not None and 0 <= triple[0] < width and all(type(c) is str and len(c) == 1 for c in triple[1:]))
        j = triple[0] if valid else None
        literal_match = (valid and oriented is not None and window is not None
            and triple[1] == oriented[j] and triple[2] == window[j] and triple[1] != triple[2])
        mismatches.append({"native_mismatch_ordinal": index, "native_triple": deepcopy(triple),
            "oriented_primer_position": j, "original_primer_position": j if valid and strand == "+" else width - 1 - j if valid and strand == "-" else None,
            "target_position": position + j if valid and interval is not None else None,
            "symbols_match_full_operands": bool(literal_match),
            "target_source_intervals": slice_path(target_path["intervals"], j, j + 1) if literal_match and target_path["state"] == "available" else None,
            "primer_source_intervals": slice_path(primer_path["intervals"], j, j + 1) if literal_match and primer_path["state"] == "available" else None})
        if not valid:
            _issue(issues, "primer_native_mismatch_triple_invalid", "/mismatches/" + str(index))
    return {"native_hit_ordinal": ordinal, "native_hit": deepcopy(raw), "strand": strand if recognized else None,
        "target_interval": interval, "oriented_source_primer": oriented, "target_window": window,
        "interpretation": interpretation, "source_acceptance": acceptance,
        "native_mismatch_entry_count": len(native_mismatches) if type(native_mismatches) is list else None,
        "compared_symbol_count": columns["paired_positions"] if columns is not None else None,
        "identical_symbol_count": columns["identical_positions"] if columns is not None else None,
        "mismatch_count": count, "mismatch_fraction": {"numerator": count, "denominator": width,
            "value": count / width if count is not None and width else None},
        "mismatch_list_matches_full_operands": mismatch_list_matches if expected is not None else None,
        "target_mapping": target_path, "primer_mapping": primer_path, "mismatches": mismatches, "issues": issues}


def _populate(inputs, rejected):
    issues = [{"code": "primer_non_json_value_rejected", **row} for row in rejected]
    native = inputs["native_record"] if type(inputs["native_record"]) is dict else {}
    if native.get("schema") != NATIVE_SCHEMA:
        _issue(issues, "primer_native_record_schema_required")
    outcome = native.get("outcome")
    if outcome not in ("completed", "failed", "partial", "truncated"):
        outcome = "unknown"
    if outcome != "completed":
        _issue(issues, "primer_native_outcome_" + outcome)
    if outcome == "failed" and type(native.get("failure")) is not dict or outcome == "completed" and native.get("failure") is not None:
        _issue(issues, "primer_native_failure_outcome_conflict")
    identity = native.get("source_identity")
    if not (type(identity) is dict and identity.get("callable") == "align_sequences"
        and type(identity.get("path")) is str and identity["path"]
        and type(identity.get("sha256")) is str and re.fullmatch("[0-9a-f]{64}", identity["sha256"])):
        _issue(issues, "primer_actual_source_identity_unavailable")
    raw_target, raw_primers = inputs["target_sequence"], inputs["primers"]
    target = raw_target.upper() if type(raw_target) is str else None
    if target is None:
        _issue(issues, "primer_full_target_string_required")
    elif set(target) - _DNA:
        _issue(issues, "primer_full_target_contains_noncanonical_literal_symbols")
    supplied = [raw_primers] if type(raw_primers) is str else raw_primers if type(raw_primers) is list else None
    if supplied is None:
        _issue(issues, "primer_full_ordered_primer_operands_required")
    refs, mappings = inputs["primer_refs"], inputs["primer_mappings"]
    for field, values in (("primer_refs", refs), ("primer_mappings", mappings)):
        if type(values) is not list or supplied is None or len(values) != len(supplied):
            _issue(issues, "primer_occurrence_binding_population_unavailable", "/" + field)
    body = native.get("result")
    raw_groups = body.get("sequences") if type(body) is dict else None
    if type(raw_groups) is not list:
        _issue(issues, "primer_native_group_population_unavailable")
    if supplied is not None and type(raw_groups) is list and len(supplied) != len(raw_groups):
        _issue(issues, "primer_native_primer_population_conflict")
    groups = []
    for i in range(max(len(supplied) if supplied is not None else 0, len(raw_groups) if type(raw_groups) is list else 0)):
        local = []
        original = supplied[i] if supplied is not None and i < len(supplied) else None
        primer = original.upper() if type(original) is str else None
        if primer is None:
            _issue(local, "primer_full_occurrence_string_unavailable")
        elif not primer:
            _issue(local, "primer_empty_source_pseudo_hits_unsupported")
        elif set(primer) - _DNA:
            _issue(local, "primer_source_noncanonical_rc_is_not_iupac_science")
        present = type(raw_groups) is list and i < len(raw_groups)
        raw = raw_groups[i] if present else None
        value = raw if type(raw) is dict else {}
        if not present or type(raw) is not dict or set(value) != {"sequence", "alignments"}:
            _issue(local, "primer_native_group_fields_unavailable")
        associated = primer is not None and value.get("sequence") == primer
        if not associated:
            _issue(local, "primer_native_occurrence_ordinal_or_sequence_conflict")
        hits = value.get("alignments")
        if type(hits) is not list:
            _issue(local, "primer_native_hit_list_unavailable")
        rows, previous, seen = [], None, set()
        for j, hit in enumerate(hits if type(hits) is list else []):
            row = _hit(hit, ordinal=j, primer=primer, target=target, associated=associated,
                target_ref=inputs["target_ref"], primer_ref=refs[i] if type(refs) is list and i < len(refs) else None,
                target_mapping=inputs["target_mapping"], primer_mapping=mappings[i] if type(mappings) is list and i < len(mappings) else None)
            rows.append(row)
            if row["strand"] is not None and row["target_interval"] is not None:
                key = (0 if row["strand"] == "+" else 1, row["target_interval"][0])
                if previous is not None and key < previous:
                    _issue(local, "primer_native_source_order_conflict", "/hits/" + str(j))
                if key in seen:
                    _issue(local, "primer_repeated_native_hit_occurrence", "/hits/" + str(j))
                seen.add(key)
                previous = key
            issues.extend({**problem, "path": "/groups/" + str(i) + "/hits/" + str(j) + problem["path"]} for problem in row["issues"])
        width = len(primer) if primer is not None else None
        candidates = max(len(target) - width + 1, 0) if target is not None and width is not None and width > 0 else None
        groups.append({"group_ordinal": i, "primer_occurrence_ordinal": i if supplied is not None and i < len(supplied) else None,
            "native_group_ordinal": i if present else None, "native_group": deepcopy(raw),
            "primer_length_symbols": width, "native_primer_length_symbols": len(value["sequence"]) if type(value.get("sequence")) is str else None,
            "candidate_windows_per_orientation": candidates, "candidate_oriented_windows": 2 * candidates if candidates is not None else None,
            "reported_hit_count": len(hits) if type(hits) is list else None,
            "native_sequence_matches_occurrence": associated, "hits": rows, "issues": local})
        issues.extend({**problem, "path": "/groups/" + str(i) + problem["path"]} for problem in local)
    return {"native_outcome": outcome, "groups": groups, "measurements": {
        "target_length_symbols": len(target) if target is not None else None,
        "requested_primer_occurrence_count": len(supplied) if supplied is not None else None,
        "native_group_count": len(raw_groups) if type(raw_groups) is list else None},
        "issues": issues, "status": "partial" if issues else "complete"}


def build_primer_placement_sheet(native_record, *, target_sequence, primers, target_ref,
                                 primer_refs=None, target_mapping=None, primer_mappings=None):
    """Retain full original operands and the complete supplied source result.

    Original mismatch tuples are represented by their unchanged JSON arrays.
    Single-string versus list input, duplicate primer occurrences, native groups,
    strands, hit order and malformed entries remain separate saved facts.
    """
    inputs, rejected = _capture({"native_record": native_record, "target_sequence": target_sequence,
        "primers": primers, "target_ref": target_ref, "primer_refs": primer_refs,
        "target_mapping": target_mapping, "primer_mappings": primer_mappings})
    return {"schema": SHEET_SCHEMA, "inputs": inputs, "rejected_values": rejected, **_populate(inputs, rejected)}


def _definitions():
    fields = {
        "target_length_symbols": ("len(full supplied uppercased target)", "symbols", "full original target string; uppercase is the source transformation"),
        "requested_primer_occurrence_count": ("1 for string input; len(list input)", "occurrences", "all ordered supplied primer occurrences, including identical strings"),
        "native_group_count": ("len(native result.sequences)", "groups", "all supplied native groups, including malformed/extraneous groups"),
        "known_native_hit_list_count": ("count intact saved groups having native hit lists", "lists", "retained source lists; missing lists are excluded, not empty"),
        "retained_native_hit_occurrence_count": ("sum reported_hit_count over known intact groups", "occurrences", "every original native hit, including malformed, duplicate, overlapping and opposite-strand occurrences"),
        "usable_saved_hit_count": ("count unchanged saved hit rows", "occurrences", "retained hit rows agreeing with full operands; saved corruption is excluded"),
        "plus_hit_count": ("count recognized '+' native strand", "occurrences", "usable saved hit rows, independently of source-acceptance compatibility"),
        "minus_hit_count": ("count recognized '-' native strand", "occurrences", "same usable saved population; palindromic +/- rows remain distinct"),
        "strand_known_hit_count": ("plus_hit_count + minus_hit_count", "occurrences", "same usable saved population; unknown strands excluded"),
        "source_compatible_hit_count": ("count source_acceptance == compatible", "occurrences", "usable rows satisfying source ordinal/sequence/window/mismatch/threshold checks; consistency, not confidence"),
        "mismatch_count_sum": ("sum available checked mismatch_count", "mismatched_symbols", "usable canonical equal-width hit comparisons; repetitions count repeatedly, never unique target coverage"),
        "mismatch_count_denominator_hits": ("count available checked mismatch_count", "occurrences", "exact retained comparison population for mismatch_count_sum; excludes missing/unsupported/corrupt comparisons"),
        "primer_length_symbols": ("len(actual original primer after uppercase)", "symbols", "one ordered supplied primer occurrence"),
        "native_primer_length_symbols": ("len(actual native group.sequence)", "symbols", "the retained native string, even when it conflicts with the supplied occurrence"),
        "candidate_windows_per_orientation": ("max(target_length - primer_length + 1, 0)", "windows", "possible complete linear windows for one nonempty primer; a structural denominator, not proof of attempted execution"),
        "candidate_oriented_windows": ("2 * candidate_windows_per_orientation", "oriented_windows", "both source orientations, including palindromic duplicate orientations"),
        "reported_hit_count": ("len(actual native alignments list)", "occurrences", "one native group; duplicates and malformed rows retained"),
        "native_mismatch_entry_count": ("len(actual native mismatch list)", "entries", "every retained mismatch entry, including duplicate or malformed triples"),
        "compared_symbol_count": ("shared literal-column paired_positions", "symbols", "one canonical equal-width complete supplied placement; no gaps or indels"),
        "identical_symbol_count": ("shared literal-column identical_positions", "symbols", "same one-placement comparison"),
        "mismatch_count": ("shared literal-column substituted_positions", "symbols", "same one-placement comparison; survives a conflicting native mismatch list, which remains explicit"),
        "mismatch_fraction": ("mismatch_count / actual full primer length", "fraction", "one checked canonical placement; exact numerator/denominator retained; no significance or annotation confidence"),
    }
    result = {name: {"calculation": formula, "unit": unit, "population": population,
        "missing_behavior": "null when its source/operand/saved cell is unavailable or incompatible; available independent observed counts survive"}
        for name, (formula, unit, population) in fields.items()}
    result["mismatch_fraction"]["missing_behavior"] = "null for unknown numerator or missing/zero denominator; empty-primer pseudo-hits are unsupported, never zero-mismatch science"
    result["mismatch_count_denominator_hits"]["missing_behavior"] = "zero means no usable checked comparisons, not a measured zero mismatch count"
    result["mismatch_count_sum"]["missing_behavior"] = "null without any known native hit-list population; an empty checked-comparison set sums to zero with denominator zero, never asserting zero mismatches for unsupported or corrupt hits"
    result["retained_native_hit_occurrence_count"]["missing_behavior"] = "null when no native hit lists are known, except explicit empty native-group population gives zero; known partial lists contribute only their actual retained occurrences"
    result["coordinates"] = {"unit": "zero_based_symbol_positions", "target_interval": "[native position, position + full primer length), never clipped",
        "oriented_primer_position": "native mismatch j", "original_primer_position": "j on '+'; primer_length - 1 - j on '-'",
        "target_position": "native position + j", "ordinals": "original occurrence/group/hit/mismatch array indices; no renumbering after failures",
        "missing_behavior": "null when bounds/strand/identity/compatibility or explicit original source paths are unavailable"}
    result["source_semantics"] = "literal <=1 mismatch, '+' ascending starts then '-' ascending starts, per ordered primer; source RC complements A/C/G/T only and leaves other symbols unchanged; unsupported noncanonical outcomes retained without IUPAC repair"
    result["completeness"] = "all retained source rows only; recorded native outcome is preserved but no omitted hit is inferred or enumerated"
    return result


def calculate_primer_placement_components(sheet):
    """Read saved cells and calculate explicit retained-population components."""
    saved, rejected_now = _capture(sheet)
    if not (type(saved) is dict and saved.get("schema") == SHEET_SCHEMA and type(saved.get("inputs")) is dict
        and set(saved["inputs"]) == _INPUT_KEYS and type(saved.get("rejected_values")) is list):
        raise ValueError("primer_placement_saved_sheet_required")
    if not all(type(row) is dict and set(row) == {"path", "value_type", "nonfinite_token"}
        and type(row["path"]) is str and type(row["value_type"]) is str for row in saved["rejected_values"]):
        raise ValueError("primer_placement_rejected_value_records_invalid")
    expected = _populate(saved["inputs"], saved["rejected_values"])
    issues = deepcopy(expected["issues"])
    issues.extend({"code": "primer_saved_non_json_value_rejected", **row} for row in rejected_now)
    measurements = {}
    for key, value in expected["measurements"].items():
        source = saved.get("measurements")
        measurements[key] = source[key] if type(source) is dict and key in source and _same(source[key], value) else None
        if measurements[key] is None and value is not None:
            _issue(issues, "primer_saved_measurement_conflict", "/measurements/" + key)
    groups, source = [], saved.get("groups")
    for i, wanted in enumerate(expected["groups"]):
        actual = source[i] if type(source) is list and i < len(source) else None
        header = lambda group: {k: v for k, v in group.items() if k != "hits"}
        if type(actual) is not dict or not _same(header(actual), header(wanted)):
            groups.append({"group_ordinal": i, "state": "incompatible", "saved_group": deepcopy(actual), "hits": []})
            _issue(issues, "primer_saved_group_conflict", "/groups/" + str(i))
            continue
        group = deepcopy(header(actual));group["hits"] = []
        raw_hits = actual.get("hits")
        for j, hit in enumerate(wanted["hits"]):
            observed = raw_hits[j] if type(raw_hits) is list and j < len(raw_hits) else None
            if _same(observed, hit):
                group["hits"].append(deepcopy(observed))
            else:
                group["hits"].append({"native_hit_ordinal": j, "state": "incompatible", "saved_hit": deepcopy(observed)})
                _issue(issues, "primer_saved_hit_conflict", "/groups/" + str(i) + "/hits/" + str(j))
        if type(raw_hits) is not list or len(raw_hits) != len(wanted["hits"]):
            _issue(issues, "primer_saved_hit_population_conflict", "/groups/" + str(i))
        groups.append(group)
    if type(source) is not list or len(source) != len(expected["groups"]):
        _issue(issues, "primer_saved_group_population_conflict")
    for key in ("native_outcome", "issues", "status"):
        if not _same(saved.get(key), expected[key]):
            _issue(issues, "primer_saved_metadata_conflict", "/" + key)
    usable_groups = [g for g in groups if g.get("state") != "incompatible"]
    known = [g for g in usable_groups if g["reported_hit_count"] is not None]
    hits = [h for g in usable_groups for h in g["hits"] if h.get("state") != "incompatible"]
    counts = [h["mismatch_count"] for h in hits if h["mismatch_count"] is not None]
    have_groups = measurements["native_group_count"] is not None
    have_hits = have_groups and (bool(known) or measurements["native_group_count"] == 0)
    summary = {**measurements, "known_native_hit_list_count": len(known),
        "retained_native_hit_occurrence_count": sum(g["reported_hit_count"] for g in known) if have_hits else None,
        "usable_saved_hit_count": len(hits),
        "plus_hit_count": sum(h["strand"] == "+" for h in hits) if have_hits else None,
        "minus_hit_count": sum(h["strand"] == "-" for h in hits) if have_hits else None,
        "strand_known_hit_count": sum(h["strand"] is not None for h in hits) if have_hits else None,
        "source_compatible_hit_count": sum(h["source_acceptance"] == "compatible" for h in hits) if have_hits else None,
        "mismatch_count_sum": sum(counts) if have_hits else None, "mismatch_count_denominator_hits": len(counts)}
    return {"schema": COMPONENT_SCHEMA, "native_outcome": expected["native_outcome"], "groups": groups,
        "summary": summary, "issues": issues, "status": "partial" if issues else "complete", "definitions": _definitions()}


__all__ = ["NATIVE_SCHEMA", "SHEET_SCHEMA", "COMPONENT_SCHEMA", "build_primer_placement_sheet", "calculate_primer_placement_components"]
