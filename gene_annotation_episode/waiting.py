"""Selected, durable waits and their statistical context.

This module executes a condition chosen by an episode.  It does not choose a
timer, poll, admit child returns, award credit or observe a controller.  The
event provider implements the public C2 ``wait_events(condition)`` interface;
subscription races and event cursors belong to that provider.

The available execution histories describe exact-class total service durations.
Their means/ranges are not distributions of report-arrival or progress events.
They are retained as explicit support, with unknown event probabilities and
unknown information gains, until a caller binds a model with those meanings.
"""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Literal, NotRequired, Protocol, TypedDict

from method_loop.identities import UnitRef

from . import execution_timing
from .resource_estimation import ResourceToolEstimator
from .run_statistics import ExecutionClass


CONDITION_VERSION = "event_condition_v1"
WAKE_VERSION = "event_wake_v1"
PENDING_VERSION = "pending_work_v2"
ESTIMATE_VERSION = "wait_estimate_v1"
REQUEST_VERSION = "wait_request_v1"
OUTCOME_VERSION = "wait_outcome_v1"
PERSISTED_VERSION = "persisted_wait_v1"
CONTEXT_VERSION = "completed_action_estimation_context_v3"
CONTEXT_IDENTITY_VERSION = "completed_action_estimation_context_v4"
CONTEXT_COMPLETION_VERSION = "completed_action_estimation_context_v5"
EVENTS = frozenset({"returned", "state_changed", "progress_committed"})
WAKE_REASONS = EVENTS | {"reconsideration"}
EVENT_METHODS = frozenset({"exact_class_duration_summary_only", "unavailable"})


class EventSelectionV1(TypedDict):
    handle: str
    event: Literal["returned", "state_changed", "progress_committed"]
    after_cursor: int


class EventConditionV1(TypedDict):
    version: Literal["event_condition_v1"]
    events: list[EventSelectionV1]
    reconsider_at: str | None


class EventRowV1(TypedDict):
    cursor: int
    handle: str
    event: Literal["returned", "state_changed", "progress_committed"]
    record_ref: str | None


class EventWakeV1(TypedDict):
    version: Literal["event_wake_v1"]
    reason: Literal["returned", "state_changed", "progress_committed", "reconsideration"]
    observed_at: str
    events: list[EventRowV1]
    reconsider_at: str | None


class PendingWorkItemV1(TypedDict):
    handle: str
    role: str
    lifecycle_state: Literal["pending", "executing", "returned", "admitted"]
    selected_at: str
    observed_at: str
    resource_selection: dict | None
    expectation_snapshot_refs: list[str]
    latest_progress_ref: str | None
    return_available: bool


class PendingWorkV1(TypedDict):
    version: Literal["pending_work_v1"]
    captured_at: str
    items: list[PendingWorkItemV1]


class PendingWorkItemV2(PendingWorkItemV1):
    suspension: dict | None
    event_target: bool
    original_assignment: NotRequired[dict | None]


class PendingWorkV2(TypedDict):
    version: Literal['pending_work_v2']
    captured_at: str
    items: list[PendingWorkItemV2]


class EventExpectationV1(TypedDict):
    handle: str
    event: Literal["returned", "state_changed", "progress_committed"]
    probability: float | None
    method: Literal["exact_class_duration_summary_only", "unavailable"]
    support_refs: list[str]


class WaitEstimateV1(TypedDict):
    version: Literal["wait_estimate_v1"]
    captured_at: str
    condition: EventConditionV1
    duration_expectation_refs: list[str]
    progress_refs: list[str]
    local_history_refs: list[str]
    event_expectations: list[EventExpectationV1]
    scientific_gain: dict | None
    monitoring_gain: dict | None
    unavailable_reasons: list[str]


class WaitRequestV1(TypedDict):
    version: Literal["wait_request_v1"]
    wait_id: str
    parent_episode_id: str
    original_decision_index: int
    condition: EventConditionV1
    estimate_snapshot: WaitEstimateV1


class WaitTriggerV1(TypedDict):
    handle: str
    cursor: int


class WaitOutcomeV1(TypedDict):
    version: Literal["wait_outcome_v1"]
    wait_id: str
    condition_sha256: str
    started_at: str
    woke_at: str
    measured_duration_seconds: float | None
    duration_measure: Literal["measured_wait_intervals"]
    wake_reason: Literal["returned", "state_changed", "progress_committed", "reconsideration"]
    trigger: WaitTriggerV1 | None
    unmeasured_interruption: bool


class EventProvider(Protocol):
    async def wait_events(self, condition: EventConditionV1) -> EventWakeV1: ...


class WaitError(ValueError):
    """An actionable wait identity, input, provider or ownership failure."""

    CODES = frozenset({"invalid_wait_record", "wait_identity_conflict",
        "wait_already_active", "invalid_event_wake", "unknown_wait"})

    def __init__(self, code):
        if code not in self.CODES:
            raise ValueError("undeclared_wait_failure_code")
        self.code = code
        super().__init__(code)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _copy(value):
    # Exact JSON data crosses this boundary, never callbacks or live contexts.
    try:
        return json.loads(_json(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise WaitError("invalid_wait_record") from error


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _text(value):
    return type(value) is str and bool(value.strip())


def _utc(value):
    try:
        parsed = datetime.fromisoformat(value) if type(value) is str else None
    except ValueError as error:
        raise WaitError("invalid_wait_record") from error
    if parsed is None or parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise WaitError("invalid_wait_record")
    return parsed


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise WaitError("invalid_wait_record")


def _refs(value):
    if type(value) is not list or any(not _text(item) for item in value):
        raise WaitError("invalid_wait_record")
    return value


def validate_condition(condition):
    """Validate and copy the exact episode-selected C6 event/set/time choice."""
    _keys(condition, ("version", "events", "reconsider_at"))
    if condition["version"] != CONDITION_VERSION or type(condition["events"]) is not list:
        raise WaitError("invalid_wait_record")
    selected = set()
    for event in condition["events"]:
        _keys(event, ("handle", "event", "after_cursor"))
        pair = (event["handle"], event["event"])
        if (not _text(event["handle"]) or not _text(event["event"]) or event["event"] not in EVENTS
                or type(event["after_cursor"]) is not int or event["after_cursor"] < 0
                or pair in selected):
            raise WaitError("invalid_wait_record")
        selected.add(pair)
    if condition["reconsider_at"] is not None:
        _utc(condition["reconsider_at"])
    if not selected and condition["reconsider_at"] is None:
        raise WaitError("invalid_wait_record")
    return _copy(condition)


def validate_pending(pending):
    _keys(pending, ("version", "captured_at", "items"))
    if pending["version"] not in {"pending_work_v1", PENDING_VERSION} or type(pending["items"]) is not list:
        raise WaitError("invalid_wait_record")
    _utc(pending["captured_at"])
    seen = set()
    for item in pending["items"]:
        fields = ("handle", "role", "lifecycle_state", "selected_at", "observed_at",
            "resource_selection", "expectation_snapshot_refs", "latest_progress_ref", "return_available")
        if pending['version'] == PENDING_VERSION:
            fields += ('suspension', 'event_target')
            if 'original_assignment' in item:
                fields += ('original_assignment',)
        _keys(item, fields)
        assignment = item.get('original_assignment')
        if assignment is not None:
            assignment_fields = ('objective', 'scope', 'decision_index')
            if isinstance(assignment, dict):
                assignment_fields += tuple(key for key in
                    ('context', 'constraints', 'evidence_refs', 'investigation_focus')
                    if key in assignment)
            _keys(assignment, assignment_fields)
            index = assignment['decision_index']
            if (index is not None and (type(index) is not int or index < 0)
                    or assignment['scope'] is not None and type(assignment['scope']) is not dict):
                raise WaitError('invalid_wait_record')
            for key in ('context', 'constraints'):
                if assignment.get(key) is not None and type(assignment[key]) is not dict:
                    raise WaitError('invalid_wait_record')
            if assignment.get('evidence_refs') is not None:
                _refs(assignment['evidence_refs'])
        if pending['version'] == PENDING_VERSION and type(item['event_target']) is not bool:
            raise WaitError('invalid_wait_record')
        if pending['version'] == PENDING_VERSION and item['suspension'] is not None:
            if type(item['suspension']) is not dict:
                raise WaitError('invalid_wait_record')
            _copy(item['suspension'])
        if (not _text(item["handle"]) or item["handle"] in seen or not _text(item["role"])
                or not _text(item["lifecycle_state"])
                or item["lifecycle_state"] not in {"pending", "executing", "returned", "admitted"}
                or type(item["return_available"]) is not bool):
            raise WaitError("invalid_wait_record")
        seen.add(item["handle"])
        _utc(item["selected_at"])
        _utc(item["observed_at"])
        _refs(item["expectation_snapshot_refs"])
        if item["latest_progress_ref"] is not None and not _text(item["latest_progress_ref"]):
            raise WaitError("invalid_wait_record")
        resource = item["resource_selection"]
        if resource is not None:
            _keys(resource, ("resource_id", "kind", "allocation", "capability_binding_ref"))
            if (not _text(resource["resource_id"]) or not _text(resource["kind"])
                    or resource["kind"] not in {"api", "local", "hpc"}
                    or not _text(resource["capability_binding_ref"])):
                raise WaitError("invalid_wait_record")
            _keys(resource["allocation"], ('cpu', 'memory_bytes', 'scratch_bytes'))
            for key, value in resource["allocation"].items():
                if value is not None and (type(value) is not int or value <= 0):
                    raise WaitError("invalid_wait_record")
    return _copy(pending)


def _duration_rows(value):
    # The existing ExecutionExpectations binding returns a snapshots envelope;
    # direct callers may supply exactly its frozen {ref,data} rows instead.
    if type(value) is dict:
        value = value.get("snapshots", [])
    if not isinstance(value, (list, tuple)):
        raise WaitError("invalid_wait_record")
    return value


def estimate_wait(requested_condition: EventConditionV1, pending: PendingWorkV1, progress_records,
                  duration_expectations, own_completed_action_history) -> WaitEstimateV1:
    """Project C6 support without inventing a report-arrival or gain model.

    ``duration_expectations`` is an ExecutionExpectations capture or a sequence
    of its immutable ``{ref, data}`` snapshots. A pending item's explicit
    expectation refs bind compatibility; no other resource/workload is pooled.
    Progress records are exposed C8 snapshots. Local-history refs are explicit
    ``reference``, ``record_ref``, ``result_ref`` or ``observation_ref`` fields,
    or the unit_id of a validated original UnitRef. Labels are not identities.
    Complete original inputs can be frozen with ``completed_action_context``.
    """
    condition = validate_condition(requested_condition)
    pending = validate_pending(pending)
    _copy(progress_records)
    _copy(duration_expectations)
    _copy(own_completed_action_history)
    if not isinstance(progress_records, (list, tuple)) or not isinstance(own_completed_action_history, (list, tuple)):
        raise WaitError("invalid_wait_record")
    by_handle = {item["handle"]: item for item in pending["items"]}
    handles = {event["handle"] for event in condition["events"]}
    allowed = {ref for handle in handles if handle in by_handle
               for ref in by_handle[handle]["expectation_snapshot_refs"]}
    duration_refs, progress_refs, local_refs = [], [], []
    supported = {}
    reasons = ["scientific_gain_model_unbound", "monitoring_gain_model_unbound"]
    duration_rows = _duration_rows(duration_expectations)
    if type(duration_expectations) is dict and duration_expectations.get("status") != "available":
        duration_rows = []
        reasons.append("duration_history_unavailable")
    seen_snapshots = set()
    for snapshot in duration_rows:
        if type(snapshot) is not dict or snapshot.get("ref") not in allowed:
            continue
        ref = snapshot["ref"]
        if ref in seen_snapshots:
            raise WaitError("invalid_wait_record")
        seen_snapshots.add(ref)
        try:
            scope = ExecutionClass(**snapshot["data"]["execution_class"])
            forecasts = ResourceToolEstimator().estimate_context({"status": "available",
                "execution_classes": [snapshot["data"]["execution_class"]], "snapshots": [snapshot]})
            if forecasts[0]["status"] == "invalid_statistics":
                raise ValueError("invalid_statistics")
        except (KeyError, TypeError, ValueError):
            reasons.append("invalid_duration_support")
            continue
        compatible = []
        for handle in handles:
            item = by_handle.get(handle)
            if item is None or ref not in item["expectation_snapshot_refs"]:
                continue
            resource = item["resource_selection"]
            if resource is not None and resource["resource_id"] != scope.resource_id:
                reasons.append("duration_resource_mismatch")
                continue
            if resource is not None and any(resource["allocation"][key] is not None
                    and resource["allocation"][key] != getattr(scope, field) for key, field in (
                        ("cpu", "cpu_threads"), ("memory_bytes", "memory_bytes"),
                        ("scratch_bytes", "scratch_bytes"))):
                reasons.append("duration_allocation_mismatch")
                continue
            compatible.append(handle)
        if compatible:
            duration_refs.append(ref)
            for handle in compatible:
                supported.setdefault(handle, []).append(ref)
    progress_by_handle = {}
    for progress in progress_records:
        if type(progress) is not dict or progress.get("target_handle") not in handles:
            continue
        ref = progress.get("progress_ref")
        if not _text(ref):
            reasons.append("progress_record_has_no_reference")
            continue
        progress_refs.append(ref)
        progress_by_handle.setdefault(progress["target_handle"], []).append(ref)
    for record in own_completed_action_history:
        if type(record) is not dict:
            continue
        for key in ("reference", "record_ref", "result_ref", "observation_ref"):
            if _text(record.get(key)):
                local_refs.append(record[key])
        unit = record.get("unit_ref")
        if unit is not None:
            try:
                reference = UnitRef.from_record(unit)
            except (TypeError, ValueError) as error:
                raise WaitError("invalid_wait_record") from error
            if ("episode_id" in record and record["episode_id"] != reference.episode_id
                    or "unit_index" in record and record["unit_index"] != reference.unit_index):
                raise WaitError("invalid_wait_record")
            local_refs.append(reference.unit_id)
    if own_completed_action_history and not local_refs:
        reasons.append("local_history_has_no_references")
    expectations = []
    for event in condition["events"]:
        handle = event["handle"]
        refs = supported.get(handle, [])
        if handle not in by_handle:
            reasons.append("selected_handle_not_in_pending_snapshot")
        if not refs:
            reasons.append("no_compatible_duration_support")
        # Even return_available does not locate a qualifying after_cursor event.
        # A service-duration mean does not model total child report turnaround,
        # remaining duration, state change or committed scientific information.
        reasons.append("event_probability_model_unbound")
        expectations.append({"handle": handle, "event": event["event"], "probability": None,
            "method": "exact_class_duration_summary_only" if refs else "unavailable",
            "support_refs": list(dict.fromkeys([*refs, *progress_by_handle.get(handle, [])]))})
    return {"version": ESTIMATE_VERSION, "captured_at": _now(), "condition": condition,
        "duration_expectation_refs": list(dict.fromkeys(duration_refs)),
        "progress_refs": list(dict.fromkeys(progress_refs)),
        "local_history_refs": list(dict.fromkeys(local_refs)), "event_expectations": expectations,
        "scientific_gain": None, "monitoring_gain": None,
        "unavailable_reasons": list(dict.fromkeys(reasons))}


def _validate_estimate(estimate, condition):
    _keys(estimate, ("version", "captured_at", "condition", "duration_expectation_refs", "progress_refs",
        "local_history_refs", "event_expectations", "scientific_gain", "monitoring_gain", "unavailable_reasons"))
    if estimate["version"] != ESTIMATE_VERSION or estimate["condition"] != condition:
        raise WaitError("invalid_wait_record")
    _utc(estimate["captured_at"])
    for field in ("duration_expectation_refs", "progress_refs", "local_history_refs", "unavailable_reasons"):
        _refs(estimate[field])
    if type(estimate["event_expectations"]) is not list:
        raise WaitError("invalid_wait_record")
    expected = {(row["handle"], row["event"]) for row in condition["events"]}
    actual = set()
    for row in estimate["event_expectations"]:
        _keys(row, ("handle", "event", "probability", "method", "support_refs"))
        probability = row["probability"]
        pair = (row["handle"], row["event"])
        if (not _text(row["handle"]) or not _text(row["event"]) or pair not in expected
                or pair in actual or not _text(row["method"]) or row["method"] not in EVENT_METHODS
                or probability is not None and (type(probability) not in (int, float)
                    or not math.isfinite(probability) or not 0 <= probability <= 1)):
            raise WaitError("invalid_wait_record")
        actual.add(pair)
        _refs(row["support_refs"])
    if actual != expected:
        raise WaitError("invalid_wait_record")
    for field in ("scientific_gain", "monitoring_gain"):
        gain = estimate[field]
        if gain is not None:
            if (type(gain) is not dict or not {"binding", "units", "support_refs"} <= gain.keys()
                    or not gain["binding"] or not _text(gain["units"])):
                raise WaitError("invalid_wait_record")
            _refs(gain["support_refs"])
    _copy(estimate)


def _validate_request(request):
    _keys(request, ("version", "wait_id", "parent_episode_id", "original_decision_index",
                    "condition", "estimate_snapshot"))
    if (request["version"] != REQUEST_VERSION or not _text(request["wait_id"])
            or not _text(request["parent_episode_id"])
            or type(request["original_decision_index"]) is not int or request["original_decision_index"] < 0):
        raise WaitError("invalid_wait_record")
    condition = validate_condition(request["condition"])
    _validate_estimate(request["estimate_snapshot"], condition)
    return _copy(request)


def _validate_wake(wake, condition):
    try:
        _keys(wake, ("version", "reason", "observed_at", "events", "reconsider_at"))
        if (wake["version"] != WAKE_VERSION or wake["reason"] not in WAKE_REASONS
                or wake["reconsider_at"] != condition["reconsider_at"]
                or type(wake["events"]) is not list):
            raise WaitError("invalid_event_wake")
        observed = _utc(wake["observed_at"])
        selected = {(row["handle"], row["event"]): row["after_cursor"] for row in condition["events"]}
        seen = set()
        for event in wake["events"]:
            _keys(event, ("cursor", "handle", "event", "record_ref"))
            pair = (event["handle"], event["event"])
            if (pair not in selected or type(event["cursor"]) is not int
                    or event["cursor"] <= selected[pair] or event["cursor"] in seen
                    or event["record_ref"] is not None and not _text(event["record_ref"])):
                raise WaitError("invalid_event_wake")
            seen.add(event["cursor"])
        if wake["reason"] == "reconsideration":
            if wake["events"] or condition["reconsider_at"] is None or observed < _utc(condition["reconsider_at"]):
                raise WaitError("invalid_event_wake")
        elif not any(event["event"] == wake["reason"] for event in wake["events"]):
            raise WaitError("invalid_event_wake")
        return _copy(wake)
    except (WaitError, KeyError, TypeError) as error:
        raise WaitError("invalid_event_wake") from error


class WaitStore:
    """Persist C6 selections/outcomes in the caller's authoritative Store.

    ``select`` can share the transaction that records the selected action. Call
    ``perform_wait`` after committing that selection so no transaction is held
    across the await. Helpers participate in an existing transaction and never
    commit it. Replays restore the original estimate, deadline and outcome.
    """

    def __init__(self, store, run_id):
        if not _text(run_id):
            raise WaitError("invalid_wait_record")
        self.store, self.db, self.run_id = store, store.db, run_id
        # executescript would implicitly commit a caller's open transaction.
        with store.transaction():
            self.db.execute("""CREATE TABLE IF NOT EXISTS episode_waits (
                run_id TEXT NOT NULL, wait_id TEXT NOT NULL, parent_episode_id TEXT NOT NULL,
                original_decision_index INTEGER NOT NULL, request_sha256 TEXT NOT NULL,
                request TEXT NOT NULL, selected_at TEXT NOT NULL, timing TEXT, wake TEXT, outcome TEXT,
                PRIMARY KEY(run_id,wait_id),
                UNIQUE(run_id,parent_episode_id,original_decision_index))""")

    def get(self, wait_id):
        """Return persisted_wait_v1, or None, without making a new observation."""
        row = self.db.execute("SELECT * FROM episode_waits WHERE run_id=? AND wait_id=?",
                              (self.run_id, wait_id)).fetchone()
        if row is None:
            return None
        return {"version": PERSISTED_VERSION, "request": json.loads(row["request"]),
            "request_sha256": row["request_sha256"], "selected_at": row["selected_at"],
            "timing": json.loads(row["timing"]) if row["timing"] is not None else None,
            "wake": json.loads(row["wake"]) if row["wake"] is not None else None,
            "outcome": json.loads(row["outcome"]) if row["outcome"] is not None else None}

    def select(self, request):
        """Record one immutable selected operation, idempotently and atomically."""
        request = _validate_request(request)
        digest = _digest(request)
        with self.store.transaction():
            existing = self.get(request["wait_id"])
            if existing is not None:
                if existing["request_sha256"] != digest:
                    raise WaitError("wait_identity_conflict")
                return existing
            selected = self.db.execute("SELECT wait_id FROM episode_waits WHERE run_id=? "
                "AND parent_episode_id=? AND original_decision_index=?",
                (self.run_id, request["parent_episode_id"], request["original_decision_index"])).fetchone()
            if selected is not None:
                raise WaitError("wait_identity_conflict")
            self.db.execute("INSERT INTO episode_waits VALUES(?,?,?,?,?,?,?,NULL,NULL,NULL)",
                (self.run_id, request["wait_id"], request["parent_episode_id"],
                 request["original_decision_index"], digest, _json(request), _now()))
            return self.get(request["wait_id"])

    async def perform_wait(self, request: WaitRequestV1, event_provider: EventProvider) -> WaitOutcomeV1:
        """Execute exactly the selected condition; complete no child admission.

        Cancellation interrupts this wait coroutine only. Recovery excludes all
        offline gaps and unknown ends from measured_duration_seconds, and flags
        them explicitly. A completed replay never calls the provider again.
        """
        saved = self.select(request)
        request = saved["request"]
        if saved["outcome"] is not None:
            return saved["outcome"]
        wake = None
        outcome = None
        interval_started = False

        def read():
            saved = self.get(request["wait_id"])
            if saved is None:
                raise WaitError("unknown_wait")
            if saved["outcome"] is not None:
                raise WaitError("wait_already_active")
            timing = saved["timing"]
            if timing and timing["intervals"] and timing["intervals"][-1]["state"] == "running":
                if execution_timing.owner_is_live(timing["intervals"][-1]["owner"]):
                    raise WaitError("wait_already_active")
            return None if timing is None else _json(timing)

        def write(encoded):
            nonlocal outcome, interval_started
            timing = json.loads(encoded)
            with self.store.transaction():
                # Atomic active-owner check prevents two simultaneous callers
                # from both starting an interval on the same durable selection.
                if not interval_started:
                    read()
                elif self.get(request["wait_id"])["outcome"] is not None:
                    raise WaitError("wait_already_active")
                if wake is not None and timing["intervals"][-1]["state"] == "returned":
                    trigger = next(({"handle": row["handle"], "cursor": row["cursor"]}
                                    for row in wake["events"] if row["event"] == wake["reason"]), None)
                    outcome = {"version": OUTCOME_VERSION, "wait_id": request["wait_id"],
                        "condition_sha256": _digest(request["condition"]),
                        "started_at": timing["intervals"][0]["started_at"],
                        "woke_at": timing["intervals"][-1]["ended_at"],
                        "measured_duration_seconds": timing["measured_elapsed_seconds"],
                        "duration_measure": "measured_wait_intervals", "wake_reason": wake["reason"],
                        "trigger": trigger, "unmeasured_interruption": any(
                            span["state"] in {"interrupted", "raised", "end_unobserved"}
                            for span in timing["intervals"])}
                self.db.execute("UPDATE episode_waits SET timing=?,wake=?,outcome=? "
                    "WHERE run_id=? AND wait_id=?", (encoded, _json(wake) if outcome is not None else None,
                    _json(outcome) if outcome is not None else None, self.run_id, request["wait_id"]))
                interval_started = True

        with ExitStack() as measured:
            # Reading the prior interval and starting the next one share the
            # writer lock. A concurrent worker cannot slip a measured interval
            # between those operations and have it overwritten from stale data.
            with self.store.transaction():
                measured.enter_context(execution_timing.measure(read, write))
            received = await event_provider.wait_events(_copy(request["condition"]))
            wake = _validate_wake(received, request["condition"])
        return _copy(outcome)


def completed_action_context(existing_context, *, pending_at_selection,
        pending_after_action, wait_estimate_at_selection=None, wait_outcome=None,
        progress_records=(), duration_expectations=(), own_completed_action_history=(),
        local_return_history_at_selection=None, current_completion_evidence=None):
    """Freeze original pending/wait inputs at one actual completion boundary.

    Pass this record to the existing controller as ``estimation_context``. The
    scalar estimator's raw history and formula are unchanged. This helper does
    not call ``observe`` and does not claim that an estimator uses these inputs.
    Earlier stored contexts should be replayed, rather than rebuilt here.
    """
    if type(existing_context) is not dict:
        raise WaitError("invalid_wait_record")
    for pending in (pending_at_selection, pending_after_action):
        if pending is not None:
            validate_pending(pending)
    result = _copy(existing_context)
    result.update(version=CONTEXT_VERSION,
        pending_work_at_selection=_copy(pending_at_selection),
        pending_work_after_action=_copy(pending_after_action),
        wait_estimate_at_selection=_copy(wait_estimate_at_selection),
        wait_outcome=_copy(wait_outcome), progress_records=_copy(progress_records),
        duration_expectations=_copy(duration_expectations),
        own_completed_action_history=_copy(own_completed_action_history))
    if local_return_history_at_selection is not None:
        # Lazy import preserves the E2 collector's existing dependency on this
        # module's condition validator. This only validates/copies supplied old
        # evidence; it does not collect the currently completing action.
        from .wait_estimation_inputs import validate_local_return_history
        try:
            history = validate_local_return_history(local_return_history_at_selection)
        except (TypeError, ValueError) as error:
            raise WaitError("invalid_wait_record") from error
        result.update(version=CONTEXT_IDENTITY_VERSION,
            local_return_history_at_selection=history)
    if current_completion_evidence is not None:
        from .completion_evidence import validate_completion_evidence
        try:
            packet = validate_completion_evidence(current_completion_evidence)
        except (TypeError, ValueError) as error:
            raise WaitError("invalid_wait_record") from error
        result.update(version=CONTEXT_COMPLETION_VERSION, current_completion_evidence=packet)
    return result
