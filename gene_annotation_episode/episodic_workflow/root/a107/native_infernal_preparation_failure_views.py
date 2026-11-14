"""Project recorded preparation failures without interpreting or grading them.

The result owner authenticates the receipt and original bundle first. This pure
projection copies requested diagnostic facts; it makes no acquisition, source
lookup, scoring decision or inference that a failed row was successfully decoded.
"""
from __future__ import annotations

import re

from .domain import ContractError, validate_schema
from .execution_contracts import canonical
from .infernal_preparation_result_views import FAILURE_SCHEMA, FAILURE_STAGES
from .native_infernal_preparation_acquisition import _selected_files


_CODE = re.compile(r"[a-z][A-Za-z0-9_]{0,191}")
_FILE_CODES = {"native_infernal_preparation_" + suffix for suffix in (
    "sealed_artifact_digest_mismatch", "unlisted_file_present", "bundle_file_unavailable_or_escaped")}


def _selection(row):
    return {key: row[key] for key in ("direction", "role", "ordinal")}


def _affected(problem, body, bundle):
    key = problem["record_key"]
    occurrences = (body.get("prepared") or {}).get("occurrences", [])
    # A numerical row's key is the exact occurrence locator followed by its
    # producer-declared record kind/ordinal. No name or nearby-row join is used.
    matches = [row for row in occurrences if key is not None and (
        key == row["occurrence_ref"] or key.startswith(row["occurrence_ref"] + "#"))]
    if len(matches) == 1:
        return _selection(matches[0])
    if bundle is None:
        return None
    code = problem["code"].split(":", 4)
    if problem["stage"] == "capture" and len(code) == 5 and code[0] in _FILE_CODES:
        matches = [row for row in _selected_files(bundle) if code[1:] == [
            row["direction"], row["role"], str(row["ordinal"]), row["relative_path"]]]
        if len(matches) != 1:
            raise ContractError("native_infernal_preparation_failure_file_association_conflict")
        return _selection(matches[0])
    prefix = (body.get("capture") or {}).get("bundle_artifact_ref", "") + "#/failures/"
    if key is not None and key.startswith(prefix):
        position = key[len(prefix):]
        if not position.isdecimal() or str(int(position)) != position or int(position) >= len(bundle["failures"]):
            raise ContractError("native_infernal_preparation_failure_locator_conflict")
        native = bundle["failures"][int(position)]
        if native["code"] != problem["code"] or native["stage"] != problem["stage"]:
            raise ContractError("native_infernal_preparation_failure_locator_conflict")
        detail = native["detail"]
        if native["stage"] == "outputs":
            return {"direction": "output", "role": native["role"], "ordinal": 0}
        for field, direction in (("ordinal", "input"), ("operand_ordinal", "working_copy")):
            if field in detail:
                return {"direction": direction, "role": native["role"], "ordinal": detail[field]}
    return None


def preparation_failure_facts(body, *, bundle=None):
    """Copy failures from an authenticated result with their original handoff."""
    result, seen = [], set()
    for problem in body["failures"]:
        code = problem["code"].split(":", 1)[0]
        if _CODE.fullmatch(code) is None:
            code = "native_infernal_preparation_unclassified_error"
        row = {"handoff_ref": body["assignment"]["handoff_ref"],
            "source_ref": body["source_ref"],
            "stage": problem["stage"] if problem["stage"] in FAILURE_STAGES else "unclassified",
            "code": code, "record_key": problem["record_key"],
            "affected": _affected(problem, body, bundle)}
        validate_schema(row, FAILURE_SCHEMA)
        identity = canonical(row)
        if identity not in seen:
            result.append(row)
            seen.add(identity)
    return result


__all__ = ["preparation_failure_facts"]
