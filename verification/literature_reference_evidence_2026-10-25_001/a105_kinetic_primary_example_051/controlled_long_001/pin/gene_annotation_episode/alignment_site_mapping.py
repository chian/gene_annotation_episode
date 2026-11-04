"""Pure original-coordinate projection for already bound alignment operands.

An alignment interval and an original derivation path are distinct facts. This
leaf never infers ancestry, merges path segments, or looks up a subject.
"""
from __future__ import annotations

from .minimap2_grading_inputs import require_finite_json
from .sequence_mapping import map_interval, validate_mapping


def _validate_operand(operand):
    require_finite_json(operand, "site_finite_json_required")
    if (type(operand) is not dict
            or set(operand) != {"subject_ref", "length", "unit", "alignment_unit", "molecule"}
            or type(operand["subject_ref"]) is not str or not operand["subject_ref"]
            or operand["length"] is not None and (type(operand["length"]) is not int or operand["length"] < 0)
            or operand["unit"] not in ("aa", "nt", "symbol")
            or operand["alignment_unit"] not in ("aa", "nt")
            or operand["molecule"] not in ("protein", "dna", "rna", "unknown")):
        raise ValueError("site_operand_invalid")


def map_operand_interval(operand: dict, mapping: dict | None,
                         interval: list[int] | None) -> dict:
    """Map a local interval through an actual supplied oriented source path.

Missing paths and incompatible paths keep different states. A null interval is
a gap/skip, not missing geometry. Scale-three paths retain split codons, repeats
and ordered source strands using the existing sequence_mapping arithmetic.
"""
    _validate_operand(operand)
    require_finite_json([mapping, interval], "site_finite_json_required")
    if interval is None:
        return {"status": "not_applicable", "intervals": [], "reason": None}
    if (type(interval) is not list or len(interval) != 2
            or any(type(value) is not int for value in interval)
            or not 0 <= interval[0] < interval[1]
            or operand["length"] is not None and interval[1] > operand["length"]):
        raise ValueError("site_operand_interval_invalid")
    if mapping is None:
        return {"status": "unavailable", "intervals": None,
                "reason": "site_original_mapping_unavailable"}
    try:
        validate_mapping(mapping)
        if operand["length"] is not None and mapping["symbol_length"] != operand["length"]:
            raise ValueError("mapping_length_mismatch")
        scale = mapping["units_per_symbol"]
        units = {row["unit"] for row in mapping["path"]}
        if scale == 3:
            if operand["unit"] not in ("aa", "symbol") or not units <= {"nt", "symbol"}:
                raise ValueError("mapping_unit_conflict")
        elif operand["unit"] != "symbol" and not units <= {operand["unit"], "symbol"}:
            raise ValueError("mapping_unit_conflict")
        intervals = map_interval(mapping, *interval)
    except (ValueError, TypeError, KeyError):
        return {"status": "incompatible", "intervals": None,
                "reason": "site_original_mapping_conflict"}
    return {"status": "available", "intervals": intervals, "reason": None}


__all__ = ["map_operand_interval"]
