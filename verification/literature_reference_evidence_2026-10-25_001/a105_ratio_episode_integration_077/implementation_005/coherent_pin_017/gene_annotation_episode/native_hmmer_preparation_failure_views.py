"""Project recorded preparation failures without interpreting or grading them.

The result owner authenticates the receipt and original bundle first. This pure
projection copies requested diagnostic facts; it makes no acquisition, source
lookup, scoring decision or inference that a failed row was successfully decoded.
"""
from __future__ import annotations

import re

from .domain import ContractError, validate_schema
from .execution_contracts import canonical
from .hmmer_preparation_result_views import FAILURE_SCHEMA, FAILURE_STAGES
from .native_hmmer_preparation_acquisition import _selected_files
from .native_hmmer_preparation_driver import FAILURE_CODES, PREFLIGHT_FAILURE_CONTEXT


_CODE = re.compile(r"[a-z][A-Za-z0-9_]{0,191}")
_FILE_CODES = {"native_hmmer_preparation_" + suffix for suffix in (
    "sealed_artifact_digest_mismatch", "unlisted_file_present", "bundle_file_unavailable_or_escaped")}


def _selection(row):
    return {key: row[key] for key in ("direction", "role", "ordinal")}


def _native_selection(native, bundle):
    """Locate the declared operand; a native query-line number is not its ordinal."""
    stage, role, detail = native["stage"], native["role"], native["detail"]
    selected = _selected_files(bundle)
    if stage == "preflight":
        context = PREFLIGHT_FAILURE_CONTEXT.get(native["code"].removeprefix("native_hmmer_preparation_"))
        job = bundle["requested_job"]["native_hmmer_preparation"]
        if (context is None or role != context["role"] or job["program"] not in context["programs"]):
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        # invalid_exactmatch_queries.detail.ordinal is the zero-based query
        # line. Select the unique queries operand using its own actual ordinal.
        matches = [row for row in selected if row["direction"] == "input" and row["role"] == role]
    elif stage == "outputs":
        matches = [row for row in selected if row["direction"] == "output"
            and row["role"] == role and row["relative_path"] == detail["relative_path"]]
    elif "operand_ordinal" in detail:
        matches = [row for row in selected if row["direction"] == "working_copy"
            and row["role"] == role and row["ordinal"] == detail["operand_ordinal"]
            and row["relative_path"] == detail["relative_path"]]
    elif "ordinal" in detail:
        matches = [row for row in selected if row["direction"] == "input"
            and row["role"] == role and row["ordinal"] == detail["ordinal"]]
    else:
        matches = []
    return _selection(matches[0]) if len(matches) == 1 else None


def _affected(problem, body, bundle):
    key = problem["record_key"]
    occurrences = (body.get("prepared") or {}).get("occurrences", [])
    prefix = ((body.get("capture") or {}).get("bundle_artifact_ref") or "") + "#/failures/"
    # Authenticate native failure identity before considering occurrence keys.
    if key is not None and "#/failures/" in key:
        if bundle is None or not key.startswith(prefix):
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        position = key[len(prefix):]
        if not position.isdecimal() or str(int(position)) != position or int(position) >= len(bundle["failures"]):
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        native = bundle["failures"][int(position)]
        if native["code"] != problem["code"] or native["stage"] != problem["stage"]:
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        return _native_selection(native, bundle)
    matches = [row for row in occurrences if key is not None and (
        key == row["occurrence_id"] or key.startswith(row["occurrence_id"] + "#"))]
    if problem["code"] in FAILURE_CODES:
        if bundle is None:
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        native = [row for row in bundle["failures"] if row["code"] == problem["code"]
            and row["stage"] == problem["stage"]]
        if len(matches) == 1:
            selected = _selection(matches[0])
            if not any(_native_selection(row, bundle) == selected for row in native):
                raise ContractError("native_hmmer_preparation_failure_locator_conflict")
            return selected
        if key is not None or not native:
            raise ContractError("native_hmmer_preparation_failure_locator_conflict")
        selections = [_native_selection(row, bundle) for row in native]
        return selections[0] if len(selections) == 1 else None
    if len(matches) == 1:
        return _selection(matches[0])
    if bundle is None:
        return None
    code = problem["code"].split(":", 4)
    if problem["stage"] == "capture" and len(code) == 5 and code[0] in _FILE_CODES:
        matches = [row for row in _selected_files(bundle) if code[1:] == [
            row["direction"], row["role"], str(row["ordinal"]), row["relative_path"]]]
        if len(matches) != 1:
            raise ContractError("native_hmmer_preparation_failure_file_association_conflict")
        return _selection(matches[0])
    return None


def preparation_failure_facts(body, *, bundle=None):
    """Copy failures from an authenticated result with their original handoff."""
    result, seen = [], set()
    for problem in body["failures"]:
        code = problem["code"].split(":", 1)[0]
        if _CODE.fullmatch(code) is None:
            code = "native_hmmer_preparation_unclassified_error"
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
