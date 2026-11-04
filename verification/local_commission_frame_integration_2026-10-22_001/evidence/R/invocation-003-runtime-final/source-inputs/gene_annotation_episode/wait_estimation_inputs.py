"""Read an episode's original inputs for wait and continuation estimation.

This adapter reads saved selections and actual completed-action observations.
It neither observes pending targets nor refreshes duration statistics. The
caller supplies only progress references actually delivered to this episode and
the current ExecutionExpectations captures already obtained before its choice.
"""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Literal, NotRequired, TypedDict

from method_loop.identities import UnitRef
from method_loop.durable import canonical, content_digest

from .execution_expectations import VERSION as EXPECTATIONS_VERSION
from .waiting import PendingWorkV1, validate_pending
from .local_return_history import LocalReturnHistoryV1, VERSION as LOCAL_RETURN_VERSION


VERSION = "wait_inputs_v1"
IDENTITY_VERSION = "wait_inputs_v2"


class DurationExpectationV1(TypedDict):
    ref: str
    data: dict


class OwnCompletedActionV1(TypedDict):
    episode_id: str
    unit_index: int
    decision_index: int
    controller_input: Any
    controller_step: Any


class WaitInputsV1(TypedDict):
    version: Literal["wait_inputs_v1"]
    progress_records: list[dict]
    duration_expectations: list[DurationExpectationV1]
    own_completed_action_history: list[OwnCompletedActionV1]


class OwnCompletedActionV2(OwnCompletedActionV1):
    unit_ref: dict | None
    label: str | None


class WaitInputsV2(TypedDict):
    version: Literal["wait_inputs_v2"]
    progress_records: list[dict]
    duration_expectations: list[DurationExpectationV1]
    own_completed_action_history: list[OwnCompletedActionV2]
    local_return_history: NotRequired[LocalReturnHistoryV1]


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _index(value):
    return type(value) is int and value >= 0


def _optional_seconds(value):
    return value is None or (type(value) in (int, float) and math.isfinite(value) and value >= 0)


def _validate_local_return_samples(samples, *, episode_id, invalid_code):
    """Shared original E2 sample shape checks; historical acceptance is unchanged."""
    def invalid():
        raise ValueError(invalid_code)

    fields = {"sample_ref", "original_decision_index", "completion_sequence", "unit_ref",
        "child_handle", "child_role", "report_contract_sha256", "commission_sha256", "return_id",
        "admission_id", "admission_state", "observation_state", "controller_input", "controller_step",
        "raw_controller_delta", "selected_at", "returned_at", "selection_to_return",
        "received_record_refs", "received_progress_refs", "linked_waits"}
    seen = set()
    for sample in samples:
        if not isinstance(sample, dict) or set(sample) != fields:
            invalid()
        if (any(not _text(sample[key]) for key in ("sample_ref", "child_handle",
                "commission_sha256", "return_id", "admission_id"))
                or sample["sample_ref"] != sample["admission_id"]
                or sample["sample_ref"] in seen
                or not _index(sample["original_decision_index"])
                or sample["completion_sequence"] is not None and not _index(sample["completion_sequence"])
                or not _text(sample["admission_state"])
                or sample["admission_state"] not in {
                    "admitted", "delivery_failed", "execution_failed", "receiver_closed"}
                or not _text(sample["observation_state"])
                or sample["observation_state"] not in {"observed", "unobserved"}
                or any(sample[key] is not None and not _text(sample[key])
                    for key in ("child_role", "report_contract_sha256"))):
            invalid()
        seen.add(sample["sample_ref"])
        unit = sample["unit_ref"]
        if unit is not None:
            try:
                reference = UnitRef.from_record(unit)
            except (TypeError, ValueError) as error:
                raise ValueError(invalid_code) from error
            if (reference.episode_id != episode_id
                    or sample["completion_sequence"] is not None
                    and reference.unit_index != sample["completion_sequence"]):
                invalid()
        delta = sample["raw_controller_delta"]
        if delta is not None and (type(delta) not in (int, float) or not math.isfinite(delta)):
            invalid()
        if (sample["observation_state"] == "unobserved"
                and any(sample[key] is not None for key in ("unit_ref", "controller_step", "raw_controller_delta"))
                or sample["observation_state"] == "observed"
                and sample["admission_state"] not in {"admitted", "delivery_failed"}):
            invalid()
        for key in ("received_record_refs", "received_progress_refs"):
            if not isinstance(sample[key], list) or any(not _text(ref) for ref in sample[key]):
                invalid()
        for key in ("selected_at", "returned_at"):
            stamp = sample[key]
            if stamp is not None:
                try:
                    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
                        invalid()
                except (AttributeError, TypeError, ValueError, OverflowError) as error:
                    raise ValueError(invalid_code) from error
        duration = sample["selection_to_return"]
        if (not isinstance(duration, dict) or set(duration) != {"seconds", "measure", "unavailable_reason"}
                or duration["measure"] != "utc_timestamp_difference"
                or not _optional_seconds(duration["seconds"])
                or duration["unavailable_reason"] is not None and not _text(duration["unavailable_reason"])):
            invalid()
        if not isinstance(sample["linked_waits"], list):
            invalid()
        for wait in sample["linked_waits"]:
            if (not isinstance(wait, dict) or set(wait) != {"wait_id", "condition_sha256",
                    "measured_duration_seconds", "duration_measure", "unmeasured_interruption"}
                    or not _text(wait["wait_id"]) or not _text(wait["condition_sha256"])
                    or not _optional_seconds(wait["measured_duration_seconds"])
                    or wait["duration_measure"] != "measured_wait_intervals"
                    or type(wait["unmeasured_interruption"]) is not bool):
                invalid()


def validate_local_return_history(value, *, run_id=None, episode_id=None):
    """Copy typed, finite original E2 evidence without obtaining newer facts.

    The capture boundary supplies the expected run and episode. Completion
    forwarding can validate the saved envelope on its own; sample UnitRefs
    still have to belong to that envelope's episode.
    """
    def invalid():
        raise ValueError("invalid_local_return_history")

    try:
        value = json.loads(_json(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("invalid_local_return_history") from error
    if (not isinstance(value, dict) or set(value) != {
            "version", "run_id", "episode_id", "credit_kind", "credit_binding",
            "samples", "unavailable_reasons"}
            or value["version"] != LOCAL_RETURN_VERSION
            or not _text(value["run_id"]) or not _text(value["episode_id"])
            or run_id is not None and value["run_id"] != run_id
            or episode_id is not None and value["episode_id"] != episode_id
            or not _text(value["credit_kind"])
            or value["credit_kind"] not in {"scientific", "monitoring", "operational"}
            or not isinstance(value["credit_binding"], dict) or not value["credit_binding"]
            or not isinstance(value["samples"], list)
            or not isinstance(value["unavailable_reasons"], list)
            or any(not _text(reason) for reason in value["unavailable_reasons"])):
        invalid()
    _validate_local_return_samples(value["samples"], episode_id=value["episode_id"],
                                   invalid_code="invalid_local_return_history")
    return value


def validate_local_return_evidence(value, *, run_id, episode_id,
                                   original_decision_index=None) -> dict:
    """Validate one original read_return envelope, without making up a history.

    Its enclosing frame supplies run/parent identity. The older history seam
    deliberately retains its original validation and error vocabulary.
    """
    invalid_code = "invalid_local_return_evidence"
    conflict_code = "local_return_evidence_identity_conflict"

    def invalid():
        raise ValueError(invalid_code)

    def conflict():
        raise ValueError(conflict_code)

    try:
        value = json.loads(canonical(value))
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError(invalid_code) from error
    if (not _text(run_id) or not _text(episode_id)
            or original_decision_index is not None and not _index(original_decision_index)
            or not isinstance(value, dict)
            or set(value) != {"version", "sample", "unavailable_reasons"}
            or value["version"] != "local_return_evidence_v1"
            or not isinstance(value["sample"], dict)
            or not isinstance(value["unavailable_reasons"], list)
            or any(not _text(reason) for reason in value["unavailable_reasons"])):
        invalid()
    sample = value["sample"]
    index = sample.get("original_decision_index")
    if not _index(index):
        invalid()
    if original_decision_index is not None and index != original_decision_index:
        conflict()
    if any(not _text(sample.get(key)) for key in ("sample_ref", "admission_id", "return_id")):
        invalid()
    expected = "admission_" + content_digest({"run_id": run_id,
        "parent_episode_id": episode_id, "original_decision_index": index,
        "return_id": sample["return_id"]})
    if sample["sample_ref"] != sample["admission_id"] or sample["admission_id"] != expected:
        conflict()
    unit = sample.get("unit_ref")
    if unit is not None:
        try:
            reference = UnitRef.from_record(unit)
        except (TypeError, ValueError) as error:
            raise ValueError(invalid_code) from error
        if (reference.episode_id != episode_id
                or sample.get("completion_sequence") is not None
                and reference.unit_index != sample["completion_sequence"]):
            conflict()
    _validate_local_return_samples([sample], episode_id=episode_id, invalid_code=invalid_code)
    for key in ("commission_sha256", "return_id", "report_contract_sha256"):
        digest = sample[key]
        if digest is not None and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            invalid()
    if sample["linked_waits"] != []:
        invalid()
    if sample["admission_state"] != "admitted" and (
            sample["received_record_refs"] or sample["received_progress_refs"]):
        conflict()
    if sample["admission_state"] in {"execution_failed", "receiver_closed"} and (
            sample["controller_input"] is not None or sample["completion_sequence"] is not None):
        conflict()
    duration = sample["selection_to_return"]
    selected, returned = sample["selected_at"], sample["returned_at"]
    expected_seconds, reason = None, None
    if selected is None:
        reason = "selected_at_unavailable"
    elif returned is None:
        reason = "returned_at_unavailable"
    else:
        expected_seconds = (datetime.fromisoformat(returned.replace("Z", "+00:00")) -
                            datetime.fromisoformat(selected.replace("Z", "+00:00"))).total_seconds()
        if expected_seconds < 0:
            expected_seconds, reason = None, "negative_selection_to_return"
    if (duration["seconds"] != expected_seconds or duration["unavailable_reason"] != reason
            or reason is not None and reason not in value["unavailable_reasons"]):
        conflict()
    if sample["observation_state"] == "observed":
        step = sample["controller_step"]
        raw = step.get("marginal_credit") if isinstance(step, dict) else None
        raw = raw if type(raw) in (int, float) and math.isfinite(raw) else None
        if canonical(sample["raw_controller_delta"]) != canonical(raw):
            conflict()
        if raw is None and "standard_controller_marginal_credit_unavailable" not in value["unavailable_reasons"]:
            conflict()
        if (isinstance(step, dict) and "credit" in step
                and isinstance(sample["controller_input"], dict) and "credit" in sample["controller_input"]
                # The existing controller converts its numeric credit to a
                # float. Retain both original JSON values and use the same
                # numeric relationship as LocalReturnHistory._observe.
                and step["credit"] != sample["controller_input"]["credit"]):
            conflict()
    return value


def _add(values, reference, value, *, conflict):
    """Retain exact JSON values; a reference never acquires a newer meaning."""
    encoded = _json(value)
    if reference in values and values[reference] != encoded:
        raise ValueError(conflict)
    values.setdefault(reference, encoded)


def _add_duration(values, snapshot):
    if (not isinstance(snapshot, dict) or set(snapshot) != {"ref", "data"}
            or not _text(snapshot["ref"]) or not isinstance(snapshot["data"], dict)):
        raise ValueError("invalid_duration_expectation_snapshot")
    _add(values, snapshot["ref"], snapshot,
         conflict="duration_expectation_identity_conflict")


class WaitInputs:
    """Read C6 support using the Journal's run and the episode's saved scope.

    Construction installs no tables. Capture joins an existing read snapshot,
    or opens a read-only transaction when called without one. No private child
    history, old model context or scientific/source body is materialized.
    """

    def __init__(self, store, journal, progress_provider):
        if journal.db is not store.db:
            raise ValueError("wait_inputs_journal_requires_same_store_connection")
        if not _text(journal.run_id):
            raise ValueError("wait_inputs_run_identity_required")
        self.store, self.journal = store, journal
        self.progress_provider = progress_provider

    def capture(self, episode_id, *, pending: PendingWorkV1, known_progress_refs,
                current_duration_expectations=(), include_identities=False,
                local_return_history=None) -> WaitInputsV1 | WaitInputsV2:
        if not _text(episode_id):
            raise ValueError("wait_inputs_episode_identity_required")
        pending = validate_pending(pending)
        if (not isinstance(known_progress_refs, (list, tuple))
                or any(not _text(ref) for ref in known_progress_refs)):
            raise ValueError("wait_inputs_progress_references_required")
        if not isinstance(current_duration_expectations, (list, tuple)):
            raise ValueError("wait_inputs_expectation_capture_sequence_required")
        if type(include_identities) is not bool:
            raise ValueError("wait_inputs_identity_selection_required")
        if local_return_history is not None and not include_identities:
            raise ValueError("wait_inputs_history_requires_identities")
        if local_return_history is not None:
            local_return_history = validate_local_return_history(local_return_history,
                run_id=self.journal.run_id, episode_id=episode_id)

        with self.store.read_snapshot():
            row = self.store.db.execute(
                "SELECT json_extract(request,'$.message.scope') AS scope "
                "FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.journal.run_id, episode_id)).fetchone()
            if row is None:
                raise ValueError("wait_inputs_episode_unavailable")
            scope = json.loads(row["scope"]) if row["scope"] is not None else None
            if not isinstance(scope, dict):
                raise ValueError("wait_inputs_saved_scope_required")

            durations = {}
            # Only selected handles and their declared original references can
            # expose old support. JSON projections stay inside SQLite; whole
            # saved requests, responses and action bodies never enter Python.
            rows = self.store.db.execute("""
                WITH envelope_paths(path) AS (VALUES
                    ('$.context.execution_expectations.snapshots'),
                    ('$.context.native_execution_expectations.snapshots'))
                SELECT json_extract(s.value,'$.ref') AS snapshot_ref,
                       json_extract(s.value,'$.data') AS snapshot_data
                FROM runtime_actions a
                JOIN runtime_model_calls c ON c.run_id=a.run_id
                    AND c.episode_id=a.episode_id AND c.call_index=a.decision_index
                JOIN json_each(?, '$.items') p
                    ON json_extract(p.value,'$.handle')=json_extract(a.result,'$.pending_handle')
                CROSS JOIN envelope_paths
                CROSS JOIN json_each(c.request,envelope_paths.path) s
                WHERE a.run_id=? AND a.episode_id=? AND c.purpose='decision'
                    AND json_extract(a.action,'$.kind') IN ('child','job_child','episode_child')
                    AND json_extract(s.value,'$.ref') IN (
                        SELECT value FROM json_each(p.value,'$.expectation_snapshot_refs'))
                ORDER BY a.decision_index,envelope_paths.path,s.key
                """, (_json(pending), self.journal.run_id, episode_id))
            for row in rows:
                data = json.loads(row["snapshot_data"]) if row["snapshot_data"] is not None else None
                _add_duration(durations, {"ref": row["snapshot_ref"], "data": data})
            for capture in current_duration_expectations:
                if (not isinstance(capture, dict) or capture.get("version") != EXPECTATIONS_VERSION
                        or capture.get("status") not in {"available", "unavailable", "invalid_statistics"}
                        or not isinstance(capture.get("snapshots"), list)):
                    raise ValueError("wait_inputs_expectation_capture_required")
                for snapshot in capture["snapshots"]:
                    _add_duration(durations, snapshot)

            progress = {}
            for reference in known_progress_refs:
                if self.progress_provider is None:
                    raise ValueError("wait_inputs_progress_provider_required")
                snapshot = self.progress_provider.read_progress(reference, scope)
                if (not isinstance(snapshot, dict) or snapshot.get("version") != "progress_snapshot_v1"
                        or snapshot.get("progress_ref") != reference):
                    raise ValueError("wait_inputs_progress_identity_mismatch")
                _add(progress, reference, snapshot, conflict="progress_identity_conflict")

            # json_quote preserves JSON scalars, signed numbers and nulls as
            # well as object-valued controller records, without reconstructing
            # gains, inventing semantic references or reading child histories.
            identity_fields = (", json_quote(json_extract(observation,'$.unit_ref')) AS unit_ref, "
                "json_quote(json_extract(observation,'$.label')) AS label" if include_identities else "")
            rows = self.store.db.execute("""
                SELECT unit_index,
                    json_extract(observation,'$.decision_index') AS decision_index,
                    json_quote(json_extract(observation,'$.credit')) AS controller_input,
                    json_quote(json_extract(observation,'$.step')) AS controller_step
                """ + identity_fields + """
                FROM runtime_observations WHERE run_id=? AND episode_id=?
                ORDER BY unit_index
                """, (self.journal.run_id, episode_id))
            history = []
            for row in rows:
                observed = {"episode_id": episode_id, "unit_index": row["unit_index"],
                        "decision_index": row["decision_index"],
                        "controller_input": json.loads(row["controller_input"]),
                        "controller_step": json.loads(row["controller_step"])}
                if include_identities:
                    unit, label = json.loads(row["unit_ref"]), json.loads(row["label"])
                    if unit is not None:
                        try:
                            reference = UnitRef.from_record(unit)
                        except (TypeError, ValueError) as error:
                            raise ValueError("wait_inputs_observation_identity_conflict") from error
                        if reference.episode_id != episode_id or reference.unit_index != row["unit_index"]:
                            raise ValueError("wait_inputs_observation_identity_conflict")
                    if label is not None and not isinstance(label, str):
                        raise ValueError("wait_inputs_observation_label_invalid")
                    observed.update(unit_ref=unit, label=label)
                history.append(observed)
            result = {"version": IDENTITY_VERSION if include_identities else VERSION,
                    "progress_records": [json.loads(value) for value in progress.values()],
                    "duration_expectations": [json.loads(value) for value in durations.values()],
                    "own_completed_action_history": history}
            if local_return_history is not None:
                result["local_return_history"] = local_return_history
            return result


__all__ = ["WaitInputs", "WaitInputsV1", "WaitInputsV2", "DurationExpectationV1",
    "OwnCompletedActionV1", "OwnCompletedActionV2", "validate_local_return_history", "validate_local_return_evidence", "VERSION", "IDENTITY_VERSION"]
