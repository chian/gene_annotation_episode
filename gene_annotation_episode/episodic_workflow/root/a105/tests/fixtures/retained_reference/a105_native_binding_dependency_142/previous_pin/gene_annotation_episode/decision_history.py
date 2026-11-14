"""Read-only steering information from this episode's recorded own attempts.

Saved controller marginal deltas, in completion order, are the observations.
Neither cumulative credit nor inherited state is converted into a new gain.
Category fits are an explicitly bound presentation model; they never supply the
episode controller or estimate a failed attempt's chance of completion.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math
from typing import Literal, TypedDict

from jsonschema import Draft202012Validator
from method_loop.durable import canonical
from method_loop.identities import UnitRef

from .episode_journal import WorkflowError
from .numerical import (ESTIMATOR_VERSION, STATUS_INSUFFICIENT, STATUS_NORMAL,
                        STATUS_UNIDENTIFIABLE, _parameters, estimate_score_yield)


TABLE_VERSION = "own_decision_yield_table_v1"
LOOKUP_VERSION = "own_attempts_v1"
CATEGORY_ESTIMATOR_VERSION = "category_occurrence_yield_v1"
REFERENCE_PREVIEW_SIZE = 32
INLINE_VALUE_BYTES = 1024
INPUT_PREVIEW_BYTES = 4096
DETAIL_STRING_PAGE = 4096
DETAIL_CONTAINER_PAGE = 32
DISCRIMINATOR_BYTES = 1024
OWN_ATTEMPTS_REPLY_BYTES = 128 * 1024
_CHILD_KINDS = {"child", "job_child", "episode_child"}
_OUTCOME_STATUSES = {"completed", "partial", "pending", "failed", "invalid", "unavailable"}


class OwnAttemptQuery(TypedDict):
    view: Literal["own_attempts"]
    category: str | None
    decision_indices: list[int] | None
    offset: int
    limit: int


class OwnAttemptDetailQuery(TypedDict):
    view: Literal["own_attempt_detail"]
    decision_index: int
    pointer: str
    offset: int
    limit: int


class SelectionDiscriminators(TypedDict):
    kind: str | None
    tool: str | None
    role: str | None


class CompletionIdentity(TypedDict):
    observation_index: int
    completion_sequence: int | None
    unit_ref: dict | None
    kind: str | None
    child_return: dict | None


class OwnAttemptRecord(TypedDict):
    decision_index: int
    category: str | None
    selection: SelectionDiscriminators
    selection_discriminator_summaries: dict
    status: str
    completed_gain: float | None
    completion: CompletionIdentity | None
    published_references: dict
    inputs: dict
    input_fields: dict
    selection_summary: dict
    outcome_summary: dict | None
    detail_reference: dict


class OwnAttempts(TypedDict):
    version: Literal["own_attempts_v1"]
    view: Literal["own_attempts"]
    run_id: str
    episode_id: str
    before: int
    category: str | None
    decision_indices: list[int] | None
    total: int
    offset: int
    limit: int
    returned_count: int
    pagination_reason: Literal["transport_byte_budget", "requested_limit", "end_of_records"]
    reply_byte_budget: int
    next_offset: int | None
    next_query: OwnAttemptQuery | None
    records: list[OwnAttemptRecord]
    unavailable_reasons: list[str]


class OwnAttemptDetail(TypedDict):
    version: Literal["own_attempt_detail_v1"]
    view: Literal["own_attempt_detail"]
    run_id: str
    episode_id: str
    before: int
    decision_index: int
    pointer: str
    slice_unit: Literal["unicode_codepoints", "array_items", "object_members_in_lexical_key_order", "scalar_values"]
    total: int
    offset: int
    limit: int
    effective_limit: int
    included: int
    values: object
    has_more: bool
    next_query: OwnAttemptDetailQuery | None
    value_sha256: str
    value_bytes: int


def _index(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + "_requires_nonnegative_integer")
    return value


def _text(value):
    return isinstance(value, str) and bool(value)


def _scope(journal, episode_id, before):
    if not _text(journal.run_id) or not _text(episode_id):
        raise ValueError("own_attempt_identity_required")
    _index(before, "before")


def category_for(selection) -> str:
    """Use the selected operation/role, never the job's scientific intention."""
    if not isinstance(selection, Mapping) or not _text(selection.get("kind")):
        raise ValueError("selection_kind_required")
    kind = selection["kind"]
    if kind == "tool":
        if not _text(selection.get("tool")):
            raise ValueError("selection_tool_required")
        return "tool/" + selection["tool"]
    if kind in _CHILD_KINDS:
        # This is the original runtime meaning of a roleless scientific child.
        role = selection.get("role", "improvement" if kind == "child" else None)
        if not _text(role):
            raise ValueError("selection_child_role_required")
        return kind + "/" + role
    return kind


def lookup_schema() -> dict:
    """The model can filter attempts, but cannot supply another owner/boundary."""
    attempts = {"title": "OwnAttemptQuery", "type": "object", "additionalProperties": False,
        "required": ["view", "category", "decision_indices", "offset", "limit"],
        "properties": {
            "view": {"type": "string", "const": "own_attempts"},
            "category": {"type": ["string", "null"]},
            "decision_indices": {"type": ["array", "null"], "uniqueItems": True,
                "items": {"type": "integer", "minimum": 0}},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1}}}
    detail = {"title": "OwnAttemptDetailQuery", "type": "object", "additionalProperties": False,
        "required": ["view", "decision_index", "pointer", "offset", "limit"],
        "properties": {
            "view": {"type": "string", "const": "own_attempt_detail"},
            "decision_index": {"type": "integer", "minimum": 0},
            "pointer": {"type": "string", "pattern": "^(?:$|/(?:[^~]|~[01])*)$",
                "description": "JSON pointer into this own attempt's recorded selected inputs only."},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1}}}
    return {"title": "OwnAttemptLookupQuery", "anyOf": [attempts, detail]}


def _tables(journal):
    return {row[0] for row in journal.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _attempt_rows(journal, episode_id, before, tables):
    # Extract only public selection discriminators and status. In particular,
    # automatic table construction never materializes saved model requests,
    # reasoning commits, outcome bodies or a child's private history.
    effects = ("LEFT JOIN runtime_decision_effects e ON e.run_id=i.run_id "
        "AND e.episode_id=i.episode_id AND e.decision_index=i.decision_index"
        if "runtime_decision_effects" in tables else "")
    effect = "json_extract(e.effect,'$.state')" if effects else "NULL"
    query = """WITH identities AS (
        SELECT run_id,episode_id,call_index AS decision_index FROM runtime_model_calls
          WHERE run_id=? AND episode_id=? AND call_index<? AND purpose='decision' AND response IS NOT NULL
        UNION
        SELECT run_id,episode_id,decision_index FROM runtime_actions
          WHERE run_id=? AND episode_id=? AND decision_index<?),
      attempts AS (
        SELECT i.*,a.decision_index AS action_index,a.credit,a.result IS NOT NULL AS result_recorded,
          json_extract(a.result,'$.status') AS outcome_status,
          CASE WHEN a.action IS NOT NULL THEN a.action
            WHEN json_type(c.response,'$.selection')='object' THEN c.response->'$.selection'
            ELSE NULL END AS selected,
          p.decision_index AS report_index,p.form IS NOT NULL AS report_admitted,
          p.failure IS NOT NULL AS report_failed,""" + effect + """ AS effect_state
        FROM identities i LEFT JOIN runtime_actions a ON a.run_id=i.run_id
          AND a.episode_id=i.episode_id AND a.decision_index=i.decision_index
        LEFT JOIN runtime_model_calls c ON c.run_id=i.run_id
          AND c.episode_id=i.episode_id AND c.call_index=i.decision_index AND c.purpose='decision'
        LEFT JOIN runtime_report_attempts p ON p.run_id=i.run_id
          AND p.parent_episode_id=i.episode_id AND p.decision_index=i.decision_index """ + effects + """)
      SELECT decision_index,action_index,credit,result_recorded,outcome_status,
        json_extract(selected,'$.kind') AS kind,json_extract(selected,'$.tool') AS tool,
        json_extract(selected,'$.role') AS role,report_index,report_admitted,report_failed,effect_state
      FROM attempts ORDER BY decision_index"""
    parameters = (journal.run_id, episode_id, before) * 2
    result = []
    for raw in journal.db.execute(query, parameters):
        row = dict(raw)
        selected = {name: row[name] for name in ("kind", "tool", "role")
                    if isinstance(row[name], str)}
        try:
            row["category"] = category_for(selected)
        except ValueError:
            row["category"] = None
        row["oversized_discriminators"] = {name: value for name, value in selected.items()
            if len(value.encode("utf-8")) > DISCRIMINATOR_BYTES}
        if row["oversized_discriminators"]:
            row["category"] = None
        row["selection"] = {name: selected.get(name) if name not in row["oversized_discriminators"] else None
                            for name in ("kind", "tool", "role")}
        if row["result_recorded"]:
            row["status"] = (row["outcome_status"] if row["outcome_status"] in _OUTCOME_STATUSES
                             else "unrecognized")
        elif row["action_index"] is not None:
            row["status"] = "pending"
        elif row["report_index"] is not None:
            row["status"] = "report_delivered" if row["report_admitted"] else "report_delivery_failed"
        elif row["effect_state"] == "rejected":
            row["status"] = "rejected"
        else:
            row["status"] = "unexecuted"
        result.append(row)
    return result


def _observations(journal, episode_id, before, rows, tables):
    """Join original decision identity; never equate decision/completion order."""
    by_decision = {row["decision_index"]: row for row in rows}
    has_slots = "runtime_completion_slots" in tables
    join = ("LEFT JOIN runtime_completion_slots s ON s.run_id=o.run_id AND s.episode_id=o.episode_id "
            "AND s.sequence=o.unit_index" if has_slots else "")
    slot_columns = ("s.sequence,s.original_decision_index AS slot_decision,"
        "json_extract(s.slot,'$.episode_id') AS slot_episode,"
        "json_extract(s.slot,'$.sequence') AS slot_sequence,"
        "json_extract(s.slot,'$.original_decision_index') AS slot_original,"
        "json_extract(s.slot,'$.kind') AS completion_kind,"
        "json_extract(s.slot,'$.child_return') AS child_return" if has_slots else
        "NULL AS sequence,NULL AS slot_decision,NULL AS slot_episode,NULL AS slot_sequence,"
        "NULL AS slot_original,NULL AS completion_kind,NULL AS child_return")
    query = """SELECT o.unit_index,
        json_extract(o.observation,'$.decision_index') AS original_decision,
        json_extract(o.observation,'$.unit_ref') AS unit_ref,
        json_extract(o.observation,'$.step.marginal_credit') AS gain,
        json_type(o.observation,'$.step.marginal_credit') AS gain_type,""" + slot_columns + """
        FROM runtime_observations o """ + join + """
        WHERE o.run_id=? AND o.episode_id=? ORDER BY o.unit_index"""
    observations, reasons, unassigned = {}, [], 0
    for row in journal.db.execute(query, (journal.run_id, episode_id)):
        index = row["original_decision"]
        if index is None:
            index = row["slot_decision"]
        if index is None:
            unassigned += 1
            reasons.append("observation_original_decision_unavailable")
            continue
        _index(index, "saved_original_decision")
        if index >= before:
            continue
        attempt = by_decision.get(index)
        if (attempt is None or attempt["action_index"] is None
                or attempt["status"] not in {"completed", "partial"}
                or index in observations):
            raise WorkflowError("decision_history_observation_identity_conflict")
        _index(row["unit_index"], "saved_observation_index")
        if row["sequence"] is not None and (
                row["slot_decision"] != index or row["slot_original"] != index
                or row["slot_episode"] != episode_id or row["slot_sequence"] != row["sequence"]):
            raise WorkflowError("decision_history_completion_identity_conflict")
        reference = None if row["unit_ref"] is None else json.loads(row["unit_ref"])
        if reference is not None:
            try:
                unit = UnitRef.from_record(reference)
            except (TypeError, ValueError) as error:
                raise WorkflowError("decision_history_unit_identity_conflict") from error
            if unit.episode_id != episode_id or unit.unit_index != row["unit_index"]:
                raise WorkflowError("decision_history_unit_identity_conflict")
        gain = row["gain"]
        if row["gain_type"] not in {"integer", "real"} or not math.isfinite(gain):
            gain = None
            reasons.append("saved_marginal_credit_unavailable")
        observations[index] = {"gain": gain, "identity": {
            "observation_index": row["unit_index"], "completion_sequence": row["sequence"],
            "unit_ref": reference, "kind": row["completion_kind"],
            "child_return": None if row["child_return"] is None else json.loads(row["child_return"])}}
    return observations, list(dict.fromkeys(reasons)), unassigned


def _expectation(history, parameters, *, complete):
    result = {"status": "unavailable", "unavailable_reason": None,
        "band": None, "completed_occurrences": len(history)}
    if parameters is None:
        result["unavailable_reason"] = "parameters_unbound"
    elif not complete:
        result["unavailable_reason"] = "saved_marginal_credit_unavailable"
    else:
        estimate = estimate_score_yield(history, parameters)
        band = estimate.expected_next_gain
        result["band"] = band.as_record()
        if band.status_code == STATUS_NORMAL:
            result["status"] = "available"
        else:
            result["unavailable_reason"] = {
                STATUS_INSUFFICIENT: "insufficient_completed_actions",
                STATUS_UNIDENTIFIABLE: "unidentifiable"}[band.status_code]
    return result


def yield_table(journal, episode_id, *, before, parameters=None) -> dict:
    """Summarize saved signed observations, excluding the inherited baseline."""
    _scope(journal, episode_id, before)
    parameters = None if parameters is None else _parameters(parameters)
    with journal.store.read_snapshot():
        tables = _tables(journal)
        attempts = _attempt_rows(journal, episode_id, before, tables)
        observations, reasons, unassigned = _observations(journal, episode_id, before, attempts, tables)
    groups = {}
    for attempt in attempts:
        category = attempt["category"]
        if category is not None:
            groups.setdefault(category, []).append(attempt)
    rows = []
    for category, members in sorted(groups.items()):
        completed = [observations[member["decision_index"]] for member in members
                     if member["decision_index"] in observations]
        completed.sort(key=lambda item: item["identity"]["observation_index"])
        history = [item["gain"] for item in completed]
        complete = all(gain is not None for gain in history)
        rows.append({"category": category, "completed_actions": len(completed),
            "total_yield": math.fsum(history) if complete else None,
            "expected_yield": _expectation(history, parameters, complete=complete),
            "attempted_uncompleted": len(members) - len(completed)})
    return {"version": TABLE_VERSION, "before": before,
        "completion_count_basis": "saved_own_controller_observations",
        "yield_basis": "saved_signed_marginal_credit_excluding_inherited_baseline",
        "expectation_model": {"version": CATEGORY_ESTIMATOR_VERSION,
            "estimator": ESTIMATOR_VERSION, "parameters": None if parameters is None else parameters.as_record(),
            "scope": "table_only", "conditional_on": "category_completed_again",
            "rank_unit": "completed_category_occurrence",
            "occurrence_order": "own_observation_completion_order",
            "uncertainty": "approximate_uncalibrated_working_model_band",
            "calibrated_confidence_interval": False, "failed_attempt_probability_model": False,
            "controller_effect": "none"},
        "rows": rows, "uncategorized_attempts": sum(row["category"] is None for row in attempts),
        "unassigned_completed_observations": unassigned, "unavailable_reasons": reasons}


def _summary(encoded, detail_reference):
    """An exact serialized-value fingerprint, not a truncated authoritative value."""
    if encoded is None:
        return None
    payload = encoded.encode("utf-8")
    return {"representation": "saved_json_reference_v1", "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(), "detail_reference": detail_reference}


def _detail_query(index, pointer="", *, offset=0, limit=DETAIL_CONTAINER_PAGE):
    return {"view": "own_attempt_detail", "decision_index": index,
            "pointer": pointer, "offset": offset, "limit": limit}


def _pointer_child(pointer, key):
    return pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _bounded_input(value, index, pointer, budget, depth=0):
    """Preserve small exact inputs; identify every omitted large value explicitly."""
    encoded = canonical(value)
    size = len(encoded.encode("utf-8"))
    if size <= min(INLINE_VALUE_BYTES, budget[0]):
        budget[0] -= size
        return json.loads(encoded)
    kind = ("object" if isinstance(value, dict) else "array" if isinstance(value, list)
            else "string" if isinstance(value, str) else "scalar")
    summary = {"representation": "bounded_selected_input_v1", "value_type": kind,
        "bytes": size, "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "detail_query": _detail_query(index, pointer,
            limit=DETAIL_STRING_PAGE if isinstance(value, str) else DETAIL_CONTAINER_PAGE)}
    if isinstance(value, (str, list, dict)):
        summary["total"] = len(value)
    budget[0] -= len(canonical(summary).encode("utf-8"))
    if depth < 3 and isinstance(value, (dict, list)):
        entries = list(sorted(value.items())) if isinstance(value, dict) else list(enumerate(value))
        included = []
        for key, item in entries[:12]:
            if budget[0] < 512:
                break
            included.append((key, _bounded_input(item, index, _pointer_child(pointer, key), budget, depth + 1)))
        summary["values"] = dict(included) if isinstance(value, dict) else [item for _, item in included]
        summary["included"] = len(included)
        summary["complete"] = len(included) == len(value)
    return summary


def _selected_inputs(selection, index):
    budget, result = [INPUT_PREVIEW_BYTES], {}
    values = ({key: item for key, item in selection.items() if key not in {"kind", "tool", "role"}}
              if isinstance(selection, dict) else {})
    for key, value in sorted(values.items()):
        if budget[0] < 512:
            break
        result[key] = _bounded_input(value, index, _pointer_child("", key), budget)
    return result, {"total": len(values), "included": len(result), "complete": len(result) == len(values),
        "detail_query": _detail_query(index)}


def _saved_selection(journal, episode_id, index):
    action = journal.db.execute("SELECT action FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND decision_index=?", (journal.run_id, episode_id, index)).fetchone()
    if action is not None:
        return action[0]
    call = journal.db.execute("SELECT response->'$.selection' FROM runtime_model_calls "
        "WHERE run_id=? AND episode_id=? AND call_index=? AND purpose='decision'",
        (journal.run_id, episode_id, index)).fetchone()
    return None if call is None else call[0]


def _lookup_detail(journal, episode_id, before, query) -> OwnAttemptDetail:
    index = _index(query["decision_index"], "decision_index")
    with journal.store.read_snapshot():
        present = {row["decision_index"] for row in _attempt_rows(journal, episode_id, before, _tables(journal))}
        if index not in present:
            raise ValueError("own_attempt_decision_unavailable")
        encoded = _saved_selection(journal, episode_id, index)
        if encoded is None:
            raise ValueError("own_attempt_selected_inputs_unavailable")
        value = json.loads(encoded)
        if not isinstance(value, dict):
            raise ValueError("own_attempt_selected_inputs_unavailable")
        pointer = query["pointer"]
        for token in ([] if not pointer else pointer[1:].split("/")):
            key = token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, list) and key.isdecimal() and str(int(key)) == key and int(key) < len(value):
                value = value[int(key)]
            else:
                raise ValueError("own_attempt_input_pointer_unavailable")
        offset, limit = query["offset"], query["limit"]
        budget = [INPUT_PREVIEW_BYTES]
        if isinstance(value, str):
            unit, total, effective = "unicode_codepoints", len(value), min(limit, DETAIL_STRING_PAGE)
            values = value[offset:offset + effective]
            included = len(values)
        elif isinstance(value, (dict, list)):
            unit = "object_members_in_lexical_key_order" if isinstance(value, dict) else "array_items"
            total, effective = len(value), min(limit, DETAIL_CONTAINER_PAGE)
            items = list(sorted(value.items())) if isinstance(value, dict) else list(enumerate(value))
            selected = []
            for key, item in items[offset:offset + effective]:
                if budget[0] < 512:
                    break
                selected.append((key, _bounded_input(item, index, _pointer_child(pointer, key), budget)))
            values = dict(selected) if isinstance(value, dict) else [item for _, item in selected]
            included = len(selected)
        else:
            unit, total, effective = "scalar_values", 1, 1
            values, included = (value, 1) if offset == 0 else (None, 0)
        has_more = offset + included < total
        next_query = {**query, "offset": offset + included} if has_more else None
        raw = canonical(value).encode("utf-8")
        return {"version": "own_attempt_detail_v1", "view": "own_attempt_detail",
            "run_id": journal.run_id, "episode_id": episode_id, "before": before,
            "decision_index": index, "pointer": pointer, "slice_unit": unit,
            "total": total, "offset": offset, "limit": limit, "effective_limit": effective,
            "included": included, "values": values, "has_more": has_more, "next_query": next_query,
            "value_sha256": hashlib.sha256(raw).hexdigest(), "value_bytes": len(raw)}


def _record(journal, episode_id, attempt, observed):
    index = attempt["decision_index"]
    detail = {"lookup": _detail_query(index)}
    action = journal.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
        "AND episode_id=? AND decision_index=?", (journal.run_id, episode_id, index)).fetchone()
    if action is None:
        call = journal.db.execute("SELECT response->'$.selection' FROM runtime_model_calls "
            "WHERE run_id=? AND episode_id=? AND call_index=? AND purpose='decision'",
            (journal.run_id, episode_id, index)).fetchone()
        selection, outcome = (None if call is None else call[0]), None
    else:
        selection, outcome = action["action"], action["result"]
    # The publication page is the saved outcome's actual own record_refs array.
    # No recursive reference scan can accidentally expose child-private data.
    saved = journal.db.execute("SELECT json_array_length(result,'$.record_refs'),"
        "result->'$.record_refs',json_type(result,'$.record_refs') FROM runtime_actions "
        "WHERE run_id=? AND episode_id=? AND decision_index=?",
        (journal.run_id, episode_id, index)).fetchone()
    if saved is not None and saved[2] not in (None, "null", "array"):
        raise WorkflowError("decision_history_publication_reference_conflict")
    count = saved[0] if saved is not None and saved[2] == "array" else None
    # Outcomes are fingerprinted and have durable record locators. The detail
    # lookup intentionally permits selected inputs only, never outcome prose.
    outcome_detail = {"table": "runtime_actions", "run_id": journal.run_id,
        "episode_id": episode_id, "decision_index": index, "field": "result"}
    reference_detail = {**outcome_detail, "field": "result.record_refs"}
    references, bounded_references, previewed = [], [], 0
    if count is not None:
        entries = journal.db.execute("SELECT refs.value FROM runtime_actions a "
            "JOIN json_each(a.result,'$.record_refs') refs WHERE a.run_id=? AND a.episode_id=? "
            "AND a.decision_index=? ORDER BY CAST(refs.key AS INTEGER) LIMIT ?",
            (journal.run_id, episode_id, index, REFERENCE_PREVIEW_SIZE))
        for entry in entries:
            if not isinstance(entry[0], str):
                raise WorkflowError("decision_history_publication_reference_conflict")
            if len(entry[0].encode("utf-8")) <= INLINE_VALUE_BYTES:
                references.append(entry[0])
            else:
                bounded_references.append({"publication_index": previewed,
                    "value": _summary(canonical(entry[0]), {**reference_detail,
                        "field": f"result.record_refs[{previewed}]"})})
            previewed += 1
    published = {"values": references, "total": count, "included": len(references),
        "previewed": previewed, "bounded_values": bounded_references,
        "complete": count is not None and count == len(references),
        "saved_value": _summary(None if saved is None else saved[1], reference_detail),
        "detail_reference": reference_detail if count is not None else None}
    inputs, input_fields = _selected_inputs(None if selection is None else json.loads(selection), index)
    return {"decision_index": index, "category": attempt["category"],
        "selection": attempt["selection"], "status": attempt["status"],
        "selection_discriminator_summaries": {name: _bounded_input(value, index, "/" + name, [0])
            for name, value in attempt["oversized_discriminators"].items()},
        "completed_gain": None if observed is None else observed["gain"],
        "completion": None if observed is None else observed["identity"],
        "published_references": published, "inputs": inputs, "input_fields": input_fields,
        "selection_summary": _summary(selection, detail),
        "outcome_summary": _summary(outcome, outcome_detail), "detail_reference": detail}


def _attempt_page(journal, episode_id, before, query, total, records, reasons, pagination_reason):
    offset = query["offset"]
    next_offset = offset + len(records) if offset + len(records) < total else None
    return {"version": LOOKUP_VERSION, "view": "own_attempts", "run_id": journal.run_id,
        "episode_id": episode_id, "before": before, "category": query["category"],
        "decision_indices": None if query["decision_indices"] is None else list(query["decision_indices"]),
        "total": total, "offset": offset, "limit": query["limit"], "returned_count": len(records),
        "pagination_reason": pagination_reason, "reply_byte_budget": OWN_ATTEMPTS_REPLY_BYTES,
        "next_offset": next_offset, "next_query": None if next_offset is None else {**query, "offset": next_offset},
        "records": records, "unavailable_reasons": reasons}


def _reply_bytes(value):
    # Include field names, separators, escaping and pagination operands. ASCII
    # escaping is conservative for the provider's UTF-8 JSON presentation.
    return len(json.dumps(value, ensure_ascii=True, allow_nan=False).encode("utf-8"))


def lookup_attempts(journal, episode_id, *, before, query) -> OwnAttempts | OwnAttemptDetail:
    """Return one compact page without executing work or creating observations."""
    _scope(journal, episode_id, before)
    errors = sorted(Draft202012Validator(lookup_schema()).iter_errors(query), key=lambda error: str(error.path))
    if errors:
        raise ValueError("invalid_own_attempt_query")
    # bool is an int in Python, but not an integer operand for this interface.
    _index(query["offset"], "offset")
    if type(query["limit"]) is not int or query["limit"] < 1:
        raise ValueError("limit_requires_positive_integer")
    if query["view"] == "own_attempt_detail":
        return _lookup_detail(journal, episode_id, before, query)
    indices = query["decision_indices"]
    if indices is not None:
        for index in indices:
            _index(index, "decision_index")
    with journal.store.read_snapshot():
        tables = _tables(journal)
        attempts = _attempt_rows(journal, episode_id, before, tables)
        observations, reasons, _ = _observations(journal, episode_id, before, attempts, tables)
        if indices is not None and not set(indices) <= {row["decision_index"] for row in attempts}:
            raise ValueError("own_attempt_decision_unavailable")
        matching = [row for row in attempts
                    if (query["category"] is None or row["category"] == query["category"])
                    and (indices is None or row["decision_index"] in indices)]
        offset, limit, total = query["offset"], query["limit"], len(matching)
        records, budget_limited = [], False
        # A requested row count is an upper bound on this transport page, never
        # a cap on the episode's attempts, actions or accessible history.
        provisional_reason = "transport_byte_budget"
        page = _attempt_page(journal, episode_id, before, query, total, records, reasons, provisional_reason)
        if _reply_bytes(page) > OWN_ATTEMPTS_REPLY_BYTES:
            raise ValueError("own_attempt_query_metadata_exceeds_reply_budget")
        for row in matching[offset:offset + limit]:
            records.append(_record(journal, episode_id, row, observations.get(row["decision_index"])))
            candidate = _attempt_page(journal, episode_id, before, query, total, records, reasons, provisional_reason)
            if _reply_bytes(candidate) > OWN_ATTEMPTS_REPLY_BYTES:
                records.pop()
                if not records:
                    raise ValueError("own_attempt_record_exceeds_reply_budget")
                budget_limited = True
                break
        reason = ("transport_byte_budget" if budget_limited else
                  "requested_limit" if offset + len(records) < total else "end_of_records")
        return _attempt_page(journal, episode_id, before, query, total, records, reasons, reason)


__all__ = ["category_for", "yield_table", "lookup_schema", "lookup_attempts",
           "OwnAttemptQuery", "OwnAttemptDetailQuery", "OwnAttemptRecord", "OwnAttempts", "OwnAttemptDetail",
           "TABLE_VERSION", "LOOKUP_VERSION",
           "CATEGORY_ESTIMATOR_VERSION", "OWN_ATTEMPTS_REPLY_BYTES"]
