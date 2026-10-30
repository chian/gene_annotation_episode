"""Pure native scalar decoding shared by HMMER parsers and saved validators.

These ports retain the encoded source. They neither normalize distributions nor
convert a configured HMMER2 model into a HMMER3 model. HMMER2 reconstructions
follow the retained reader's nominal binary32 expression, not a claim about the
unrecoverable probabilities preceding integer quantization.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
import struct


_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_CELL_FIELDS = {"token", "negative_log_probability", "probability", "state", "source"}


def binary_probability_cell(raw: bytes, *, byte_start: int,
                            byte_order: str) -> dict:
    """Decode one original binary32 cell, keeping partial or invalid bytes."""
    cell = {"token": None, "negative_log_probability": None, "probability": None,
            "state": "invalid", "source": {
                "encoding": "ieee754_binary32_probability",
                "raw_hex": raw.hex() if isinstance(raw, bytes) else None,
                "byte_start": byte_start,
                "byte_end": byte_start + len(raw) if type(byte_start) is int and isinstance(raw, bytes) else None}}
    if (not isinstance(raw, bytes) or len(raw) != 4 or type(byte_start) is not int
            or byte_start < 0 or byte_order not in ("little", "big")):
        return cell
    value = struct.unpack(("<" if byte_order == "little" else ">") + "f", raw)[0]
    if math.isfinite(value) and 0 <= value <= 1:
        cell.update(probability=value, state="structural_zero" if value == 0 else "finite")
    return cell


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _reference_kind(reference):
    if type(reference) is not dict:
        return None
    if reference == {"kind": "unit"}:
        return "unit"
    if (set(reference) == {"kind", "denominator"} and reference["kind"] == "uniform_alphabet"
            and type(reference["denominator"]) is int and reference["denominator"] > 0):
        return "uniform_alphabet"
    if (set(reference) == {"kind", "cell_index"} and reference["kind"] == "nule"
            and type(reference["cell_index"]) is int and reference["cell_index"] >= 0):
        return "nule"
    return None


def hmmer2_probability_cell(token: str, *, reference: dict,
                            reference_cell: dict | None = None) -> dict:
    """Retain an integer millibit score and its explicit nominal reconstruction.

Only ``*`` supplies structural zero. An integer score token with an absent NULE
reference stays reference_missing. A malformed supplied NULE is invalid; a
finite out-of-range nominal value remains inspectable without a probability.
"""
    cell = {"token": token, "negative_log_probability": None, "probability": None,
            "state": "invalid", "source": {"encoding": "hmmer2_millibit_log_odds",
                "score": None, "reference": deepcopy(reference), "nominal_probability": None}}
    if not isinstance(token, str):
        return cell
    if token != "*":
        if not _INTEGER.fullmatch(token):
            return cell
        try:
            cell["source"]["score"] = int(token)
        except ValueError:
            return cell
    kind = _reference_kind(reference)
    if kind is None:
        return cell
    if token == "*":
        cell["source"]["nominal_probability"] = 0.0
        cell.update(probability=0.0, state="structural_zero")
        return cell
    if kind == "unit":
        q = 1.0
    elif kind == "uniform_alphabet":
        try:
            q = _f32(1 / reference["denominator"])
        except (OverflowError, ZeroDivisionError):
            return cell
    else:
        if reference_cell is None:
            cell["state"] = "reference_missing"
            return cell
        if (type(reference_cell) is not dict or set(reference_cell) != _CELL_FIELDS
                or type(reference_cell.get("source")) is not dict):
            return cell
        source = reference_cell["source"]
        if (set(source) != {"encoding", "score", "reference", "nominal_probability"}
                or source["encoding"] != "hmmer2_millibit_log_odds"
                or source["score"] is not None and type(source["score"]) is not int
                or source["nominal_probability"] is not None and type(source["nominal_probability"]) not in (int, float)
                or reference_cell["probability"] is not None and type(reference_cell["probability"]) not in (int, float)
                or _reference_kind(source["reference"]) != "uniform_alphabet"):
            return cell
        expected = hmmer2_probability_cell(reference_cell["token"], reference=source["reference"])
        if expected != reference_cell:
            return cell
        if expected["state"] == "underflow":
            cell["state"] = "underflow"
            return cell
        q = expected["probability"]
        if q is None:
            return cell
        if q == 0:
            # A finite log-odds score against an exact zero null has an
            # undefined reference. The nominal expression is exactly zero;
            # it is not positive-probability floating-point underflow.
            cell["source"]["nominal_probability"] = 0.0
            return cell
    try:
        nominal = _f32(q * math.exp(cell["source"]["score"] * 0.00069314718))
    except (ValueError, OverflowError):
        return cell
    if not math.isfinite(nominal):
        return cell
    if nominal == 0:
        cell["state"] = "underflow"
        return cell
    cell["source"]["nominal_probability"] = nominal
    if nominal > 1:
        cell["state"] = "quantized_out_of_range"
    elif nominal > 0:
        cell.update(probability=nominal, state="finite")
    return cell
