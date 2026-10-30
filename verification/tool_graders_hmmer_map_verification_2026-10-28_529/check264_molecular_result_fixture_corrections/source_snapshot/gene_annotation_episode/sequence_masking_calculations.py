"""One deterministic numerical authority for all raw-sequence mask algorithms.

Counts describe prepared sequences; they are not annotation confidence. Shared
half-open union and missing/zero-denominator ratio primitives remain the existing
implementations. Native thresholds are observations, never calculator settings.
"""
from __future__ import annotations

from . import genomic_overlap_calculations, hmmer_search_grader
from .sequence_masking_contracts import sequence_masking_molecule, validate_sequence_masking_record


def _count(value, unit, reason=None):
    return {"value": value, "unit": unit, "missing_reason": reason if value is None else None}


def calculate_sequence_masking_components(sheet: dict) -> dict:
    """Calculate per-input-record mask extent from a retained validated sheet."""
    sheet = validate_sequence_masking_record("SequenceMaskingSheet", sheet)
    output = sheet["parsed_output"]
    by_key = {r["input_record_key"]: r for r in output["records"]}
    known_zero = {r["input_record_key"] for r in output.get("known_zero_records", [])}
    conversion = sheet["operation"]["mode"] == "convert_mask"
    records = []
    for source in sheet["inputs"]:
        key, length = source["record_key"], source["length"]
        expected_molecule = sequence_masking_molecule(sheet["operation"])
        unit = "aa" if expected_molecule == "protein" else "nt"
        row = by_key.get(key)
        input_reason = source["failures"][0]["code"] if length is None else None
        if source["molecule"] != expected_molecule:
            length, input_reason = None, "incompatible_input_molecule"
        reason = input_reason
        if reason is None and row is None and key not in known_zero:
            reason = "mask_output_absent"
        elif reason is None and row is not None and row["measurement"] == "hard_mask_ambiguous":
            reason = "hard_mask_ambiguous"
        elif reason is None and row is not None and row["measurement"] != "exact_mask":
            reason = row["failures"][0]["code"] if row["failures"] else "mask_measurement_unavailable"
        merged, masked, unmasked, merged_count = None, None, None, None
        if reason is None:
            union = hmmer_search_grader._union([] if key in known_zero else row["intervals_half_open"])
            merged, masked = union["intervals"], union["positions"]
            merged_count, unmasked = len(merged), length - masked
        native_count = len(row["native_intervals"]) if row is not None and output["format"] == "interval" else None
        native_reason = "not_applicable" if output["format"] == "fasta" else "mask_output_absent"
        if conversion:
            native_count = len(row["native_intervals"]) if row is not None and row["completeness"] == "complete" and not any(
                f["stage"] == "parse" for f in row["failures"]) else None
            native_reason = "native_mask_record_not_emitted" if key in known_zero else (
                row["failures"][0]["code"] if row is not None and row["failures"] else "mask_output_absent")
        changed, changed_reason = None, "not_applicable" if conversion or output["format"] == "interval" else "mask_output_absent"
        if output["format"] == "fasta" and row is not None:
            # Equal length alone does not authenticate compatibility. Only exact
            # or explicitly ambiguous hard-mask transformations establish it.
            if length is not None and row["measurement"] in ("exact_mask", "hard_mask_ambiguous"):
                changed = sum(a != b for a, b in zip(source["normalized_sequence"], row["output_sequence"].upper()))
                changed_reason = None
            else:
                changed_reason = reason or "output_sequence_incompatible"
        record_failures = source["failures"] + ([] if row is None else row["failures"])
        records.append({"record_key": key, "unit": unit,
            "input_length": _count(length, unit, input_reason),
            "native_interval_count": _count(native_count, "intervals", native_reason),
            "merged_interval_count": _count(merged_count, "intervals", reason),
            "merged_intervals_half_open": merged,
            "masked_positions": _count(masked, unit, reason),
            "unmasked_positions": _count(unmasked, unit, reason),
            "masked_fraction": genomic_overlap_calculations._ratio(masked, length, reason),
            "changed_positions": _count(changed, unit, changed_reason),
            "checks": source["checks"] + [c for c in output["checks"] if c["record_key"] == key],
            "failures": record_failures})
    return validate_sequence_masking_record("SequenceMaskingComponents", {
        "version": "sequence_masking_components_v1", "analysis": "sequence_masking_preparation",
        "records": records, "checks": sheet["checks"], "failures": sheet["failures"]})
