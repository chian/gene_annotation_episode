"""Original supplied scalar and M1 occurrence checks."""
from __future__ import annotations

import math
import re

OCCURRENCE_FIELDS = frozenset({"occurrence_id", "direction", "role", "ordinal",
                             "artifact_ref", "sha256", "size_bytes", "completeness"})


_INTEGER = re.compile(r"[+-]?[0-9]+\Z")
_REAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


def _numeric(token, *, integer=False, minimum=None, positive=False, maximum=None):
    if not isinstance(token, str) or not (_INTEGER if integer else _REAL).fullmatch(token):
        return None
    try:
        value = int(token) if integer else float(token)
        if not math.isfinite(value) or (minimum is not None and value < minimum):
            return None
        if (positive and value <= 0) or (maximum is not None and value > maximum):
            return None
        return value
    except (ValueError, OverflowError):
        return None


def _occurrence_valid(occurrence):
    if not isinstance(occurrence, dict) or occurrence.keys() != OCCURRENCE_FIELDS:
        return False
    if any(type(occurrence[key]) is not str or not occurrence[key]
           for key in ("occurrence_id", "role", "artifact_ref")):
        return False
    return (isinstance(occurrence["direction"], str) and occurrence["direction"] in {"input", "output"}
            and isinstance(occurrence["completeness"], str)
            and occurrence["completeness"] in {"complete", "partial", "unknown"}
            and type(occurrence["ordinal"]) is int and occurrence["ordinal"] >= 0
            and type(occurrence["size_bytes"]) is int and occurrence["size_bytes"] >= 0
            and isinstance(occurrence["sha256"], str)
            and re.fullmatch(r"[0-9a-fA-F]{64}", occurrence["sha256"]) is not None)


