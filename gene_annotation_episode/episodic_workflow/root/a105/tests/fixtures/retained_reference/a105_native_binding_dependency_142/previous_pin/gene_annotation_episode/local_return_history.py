"""Read original parent-return evidence without projecting or observing credit.

C4 admissions define the samples. C1, C3, F2 and the parent's observations
qualify those samples; missing support never creates another action or identity.
Only the immutable C3 reader is used on the execution backend. Child archives,
current status, native durations and today's credit projections are not read.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import nullcontext
from datetime import datetime
import json
import math
from typing import Literal, TypedDict

from method_loop.durable import canonical, content_digest, validate_commission, validate_return
from method_loop.identities import EpisodeRef, UnitRef

from .communication import validate_form
from .waiting import validate_condition


VERSION = "local_parent_return_history_v1"
_STATES = {"admitted", "delivery_failed", "execution_failed", "receiver_closed"}
_CHILD_KINDS = {"child", "job_child", "episode_child"}


class SelectionToReturnV1(TypedDict):
    seconds: float | None
    measure: Literal["utc_timestamp_difference"]
    unavailable_reason: str | None


class LinkedWaitV1(TypedDict):
    wait_id: str
    condition_sha256: str
    measured_duration_seconds: float | None
    duration_measure: Literal["measured_wait_intervals"]
    unmeasured_interruption: bool


class LocalReturnSampleV1(TypedDict):
    sample_ref: str
    original_decision_index: int
    completion_sequence: int | None
    unit_ref: dict | None
    child_handle: str
    child_role: str | None
    report_contract_sha256: str | None
    commission_sha256: str
    return_id: str
    admission_id: str
    admission_state: Literal["admitted", "delivery_failed", "execution_failed", "receiver_closed"]
    observation_state: Literal["observed", "unobserved"]
    controller_input: object
    controller_step: object
    raw_controller_delta: float | None
    selected_at: str | None
    returned_at: str | None
    selection_to_return: SelectionToReturnV1
    received_record_refs: list[str]
    received_progress_refs: list[str]
    linked_waits: list[LinkedWaitV1]


class LocalReturnHistoryV1(TypedDict):
    version: Literal["local_parent_return_history_v1"]
    run_id: str
    episode_id: str
    credit_kind: Literal["scientific", "monitoring", "operational"]
    credit_binding: dict
    samples: list[LocalReturnSampleV1]
    unavailable_reasons: list[str]


def _text(value):
    return isinstance(value, str) and bool(value)


def _index(value):
    return type(value) is int and value >= 0


def _conflict():
    raise ValueError("local_return_history_identity_conflict")


def _load(value):
    try:
        return json.loads(canonical(json.loads(value)))
    except (TypeError, ValueError) as error:
        raise ValueError("local_return_history_invalid_saved_json") from error


def _utc(value):
    if not _text(value):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo is not None and stamp.utcoffset().total_seconds() == 0 else None
    except (ValueError, OverflowError):
        return None


def _refs(value):
    if not isinstance(value, list) or any(not _text(ref) for ref in value):
        _conflict()
    return value


def _progress_refs(report, contract):
    schema = contract.get("measurements", {}).get("schema")
    if not isinstance(schema, dict):
        return None
    # Validate only the original admitted shape. Re-resolving references against
    # current data would reinterpret the information admitted at that time.
    refs = []
    def declared_reference(reference, namespace):
        if namespace == "episode_progress":
            refs.append(reference)
        return True
    try:
        # The shared semantic walk handles the exact registered native field
        # within its own schema resource. Scientific references do not confer
        # progress; only the original episode_progress annotation does.
        validate_form(report, schema, declared_reference)
    except (TypeError, ValueError) as error:
        raise ValueError("local_return_history_admitted_form_conflict") from error
    return list(dict.fromkeys(refs))


class LocalReturnHistory:
    """A read-only projection scoped to the Journal's original run identity."""

    def __init__(self, store, journal, backend):
        if journal.db is not store.db:
            raise ValueError("local_return_history_journal_requires_same_store_connection")
        if not _text(journal.run_id):
            raise ValueError("local_return_history_run_identity_required")
        self.store, self.journal, self.backend = store, journal, backend

    def read_return(self, episode_id, original_decision_index):
        """Read one original C4 sample, without capturing history or linking waits.

        A completion reader can join its existing snapshot. Missing admissions
        mean no C4 return, rather than a newly inferred admission or sample.
        """
        if not _text(episode_id):
            raise ValueError("local_return_history_episode_identity_required")
        if not _index(original_decision_index):
            raise ValueError("local_return_history_original_decision_index_required")
        with (nullcontext() if self.store.db.in_transaction else self.store.read_snapshot()):
            tables = {row[0] for row in self.store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            episode = (self.store.db.execute(
                "SELECT path,json_extract(request,'$.goal.goal_id') AS goal_id "
                "FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (self.journal.run_id, episode_id)).fetchone()
                if "runtime_episodes" in tables else None)
            if episode is None:
                raise ValueError("local_return_history_episode_unavailable")
            if "runtime_return_admissions" not in tables:
                return None
            row = self.store.db.execute("SELECT * FROM runtime_return_admissions "
                "WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?",
                (self.journal.run_id, episode_id, original_decision_index)).fetchone()
            if row is None:
                return None
            admission = _load(row["admission"])
            if (not isinstance(admission, dict)
                    or not _index(admission.get("original_decision_index"))):
                _conflict()
            try:
                reference = EpisodeRef(self.journal.run_id, _load(episode["path"]))
            except (TypeError, ValueError) as error:
                raise ValueError("local_return_history_identity_conflict") from error
            if reference.episode_id != episode_id:
                _conflict()
            if "runtime_commission_intents" in tables:
                original = self.store.db.execute("SELECT json_extract(spec,'$.parent.path') AS path, "
                    "json_extract(spec,'$.parent.goal_id') AS goal_id FROM runtime_commission_intents "
                    "WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?",
                    (self.journal.run_id, episode_id, original_decision_index)).fetchone()
                if original is not None and (original["goal_id"] != episode["goal_id"]
                        or canonical(_load(original["path"])) != canonical(_load(episode["path"]))):
                    _conflict()
            reasons = []
            sample = self._sample(row, episode_id, tables, reasons)
            sample.pop("_observation_index", None)
            return {"version": "local_return_evidence_v1", "sample": sample,
                "unavailable_reasons": list(dict.fromkeys(reasons))}

    def capture(self, episode_id, *, credit_kind, credit_binding) -> LocalReturnHistoryV1:
        if not _text(episode_id):
            raise ValueError("local_return_history_episode_identity_required")
        if credit_kind not in {"scientific", "monitoring", "operational"}:
            raise ValueError("local_return_history_credit_kind_required")
        if not isinstance(credit_binding, Mapping) or not credit_binding:
            raise ValueError("local_return_history_credit_binding_required")
        binding = json.loads(canonical(credit_binding))
        reasons = []
        with self.store.read_snapshot():
            tables = {row[0] for row in self.store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "runtime_episodes" not in tables or self.store.db.execute(
                    "SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                    (self.journal.run_id, episode_id)).fetchone() is None:
                raise ValueError("local_return_history_episode_unavailable")
            if "runtime_return_admissions" not in tables:
                reasons.append("return_admissions_unavailable")
                samples = []
            else:
                rows = self.store.db.execute("SELECT * FROM runtime_return_admissions "
                    "WHERE run_id=? AND parent_episode_id=? ORDER BY original_decision_index",
                    (self.journal.run_id, episode_id)).fetchall()
                samples = [self._sample(row, episode_id, tables, reasons) for row in rows]
                self._link_waits(samples, episode_id, tables, reasons)
                # Missing F2 does not turn decision order into completion order:
                # a legacy observation's own unit_index is retained only as its
                # original observation order, with completion_sequence null.
                samples.sort(key=lambda sample: (
                    0 if sample["observation_state"] == "observed" else 1,
                    sample["_observation_index"] if sample["observation_state"] == "observed"
                    else sample["original_decision_index"]))
                for sample in samples:
                    sample.pop("_observation_index", None)
        return {"version": VERSION, "run_id": self.journal.run_id, "episode_id": episode_id,
            "credit_kind": credit_kind, "credit_binding": binding, "samples": samples,
            "unavailable_reasons": list(dict.fromkeys(reasons))}

    def _sample(self, row, episode_id, tables, reasons):
        admission = _load(row["admission"])
        index = row["original_decision_index"]
        if (not isinstance(admission, dict) or not _index(index)
                or admission.get("version") != "episode_admission_v1"
                or admission.get("parent_episode_id") != episode_id
                or admission.get("original_decision_index") != index
                or admission.get("handle") != row["handle"]
                or admission.get("return_id") != row["return_id"]
                or admission.get("state") not in _STATES
                or not _text(row["handle"]) or not _text(row["return_id"])):
            _conflict()
        expected_id = "admission_" + content_digest({"run_id": self.journal.run_id,
            "parent_episode_id": episode_id, "original_decision_index": index,
            "return_id": row["return_id"]})
        if admission.get("admission_id") != expected_id:
            _conflict()
        refs = admission.get("received_record_refs")
        if refs is None:
            refs = []
            reasons.append("admission_record_references_unavailable")
        _refs(refs)
        state = admission["state"]
        if state != "admitted" and (refs or admission.get("report") is not None):
            _conflict()
        if state in {"execution_failed", "receiver_closed"} and admission.get("controller_input") is not None:
            _conflict()
        action = (self.journal.row("runtime_actions", episode_id, index)
                  if "runtime_actions" in tables else None)
        if action is None:
            reasons.append("original_action_unavailable")
        elif content_digest(_load(action["action"])) != row["selection_sha256"]:
            _conflict()
        elif _load(action["action"]).get("kind") not in _CHILD_KINDS:
            _conflict()
        if action is not None and state in {"admitted", "delivery_failed"}:
            outcome = None if action["result"] is None else _load(action["result"])
            if (not isinstance(outcome, dict) or outcome.get("status") != "completed"
                    or outcome.get("record_refs") != refs or action["credit"] != row["credit_snapshot"]):
                _conflict()
        intent = None
        if "runtime_commission_intents" in tables:
            intent = self.store.db.execute("SELECT * FROM runtime_commission_intents "
                "WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?",
                (self.journal.run_id, episode_id, index)).fetchone()
        spec, contract, selected_at = None, None, None
        if intent is None:
            reasons.append("original_commission_unavailable")
        else:
            try:
                spec = validate_commission(_load(intent["spec"]))
            except (TypeError, ValueError, RuntimeError) as error:
                raise ValueError("local_return_history_identity_conflict") from error
            if (spec["run_id"] != self.journal.run_id or spec["parent"]["episode_id"] != episode_id
                    or spec["handle"] != row["handle"] or spec["handle"] != intent["handle"]
                    or spec["operation_key"] != intent["operation_key"]
                    or content_digest(spec) != intent["commission_sha256"]
                    or content_digest(spec) != row["commission_sha256"]
                    or content_digest(_load(intent["selection"])) != row["selection_sha256"]
                    or canonical(spec["expectation_snapshot_refs"]) != canonical(_load(row["expectation_snapshot_refs"]))):
                _conflict()
            contract = spec["child"]["request"]["report_contract"]
            selected_at = intent["selected_at"] if _utc(intent["selected_at"]) is not None else None
            if selected_at is None:
                reasons.append("selected_at_invalid")
        attempt = None
        if "runtime_report_attempts" in tables:
            attempt = self.store.db.execute("SELECT child_episode_id,contract,form,failure "
                "FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=?",
                (self.journal.run_id, episode_id, index)).fetchone()
        if attempt is not None:
            saved_contract = _load(attempt["contract"])
            if (contract is not None and canonical(contract) != canonical(saved_contract)
                    or spec is not None and attempt["child_episode_id"] != spec["child"]["episode_id"]):
                _conflict()
            contract = saved_contract
            if state == "admitted" and (attempt["form"] is None
                    or canonical(_load(attempt["form"])) != canonical(admission.get("report"))
                    or attempt["failure"] is not None):
                _conflict()
            if state == "delivery_failed" and (attempt["form"] is not None or attempt["failure"] is None):
                _conflict()
        elif state in {"admitted", "delivery_failed"}:
            reasons.append("original_report_attempt_unavailable")
        progress = []
        if state == "admitted":
            if contract is None or admission.get("report") is None:
                reasons.append("admitted_progress_schema_unavailable")
            else:
                progress = _progress_refs(admission["report"], contract)
                if progress is None:
                    reasons.append("admitted_progress_schema_unavailable")
                    progress = []
        returned_at = self._returned_at(spec, row, admission, reasons)
        seconds, unavailable = None, None
        if selected_at is None:
            unavailable = "selected_at_unavailable"
        elif returned_at is None:
            unavailable = "returned_at_unavailable"
        else:
            seconds = (_utc(returned_at) - _utc(selected_at)).total_seconds()
            if seconds < 0:
                seconds, unavailable = None, "negative_selection_to_return"
        if unavailable:
            reasons.append(unavailable)
        sample = {"sample_ref": admission["admission_id"], "original_decision_index": index,
            "completion_sequence": None, "unit_ref": None, "child_handle": row["handle"],
            "child_role": None if spec is None else spec["child"]["role"],
            "report_contract_sha256": None if contract is None else content_digest(contract),
            "commission_sha256": row["commission_sha256"], "return_id": row["return_id"],
            "admission_id": admission["admission_id"], "admission_state": state,
            "observation_state": "unobserved", "controller_input": admission.get("controller_input"),
            "controller_step": None, "raw_controller_delta": None,
            "selected_at": selected_at, "returned_at": returned_at,
            "selection_to_return": {"seconds": seconds, "measure": "utc_timestamp_difference",
                                    "unavailable_reason": unavailable},
            "received_record_refs": refs, "received_progress_refs": progress, "linked_waits": []}
        self._observe(sample, admission, episode_id, tables, reasons)
        return sample

    def _returned_at(self, spec, row, admission, reasons):
        if spec is None:
            reasons.append("original_return_commission_unavailable")
            return None
        try:
            returned = self.backend.load_return(row["handle"], row["return_id"])
        except Exception:
            # Reading C3 can fail after the admission committed. Keep its one
            # original sample; never poll, restart or hydrate a child archive.
            reasons.append("original_return_read_unavailable")
            return None
        if (not isinstance(returned, dict) or returned.get("handle") != row["handle"]
                or returned.get("return_id") != row["return_id"]
                or returned.get("commission_sha256") != row["commission_sha256"]):
            reasons.append("original_return_identity_conflict")
            return None
        if _utc(returned.get("returned_at")) is None:
            reasons.append("returned_at_invalid")
            return None
        try:
            validate_return(returned, spec=spec, commission_sha256=row["commission_sha256"])
        except (TypeError, ValueError, RuntimeError):
            reasons.append("original_return_invalid")
            return None
        if (admission["state"] in {"admitted", "delivery_failed"} and returned["outcome"] != "closed"
                or admission["state"] == "execution_failed" and returned["outcome"] == "closed"
                or admission["state"] == "admitted"
                    and canonical(returned["form"]) != canonical(admission.get("report"))):
            reasons.append("original_return_admission_conflict")
            return None
        return returned["returned_at"]

    def _observe(self, sample, admission, episode_id, tables, reasons):
        index = sample["original_decision_index"]
        slot_row = None
        if "runtime_completion_slots" in tables:
            slot_row = self.store.db.execute("SELECT sequence,slot FROM runtime_completion_slots "
                "WHERE run_id=? AND episode_id=? AND original_decision_index=?",
                (self.journal.run_id, episode_id, index)).fetchone()
        slot = None if slot_row is None else _load(slot_row["slot"])
        if slot is not None:
            if (slot.get("version") != "episode_completion_slot_v1" or slot.get("episode_id") != episode_id
                    or slot.get("original_decision_index") != index or slot.get("kind") != "child_return"
                    or not _index(slot_row["sequence"]) or slot.get("sequence") != slot_row["sequence"]
                    or slot.get("child_return") != {key: admission[key]
                        for key in ("handle", "return_id", "admission_id")}
                    or canonical(slot.get("controller_input")) != canonical(admission.get("controller_input"))):
                _conflict()
            sample["completion_sequence"] = slot_row["sequence"]
        elif admission["state"] in {"admitted", "delivery_failed"}:
            reasons.append("completion_slot_unavailable")
        observations = []
        if "runtime_observations" in tables:
            observations = self.store.db.execute("SELECT unit_index,observation FROM runtime_observations "
                "WHERE run_id=? AND episode_id=? AND (json_extract(observation,'$.decision_index')=? "
                "OR unit_index=?) ORDER BY unit_index", (self.journal.run_id, episode_id, index,
                    None if slot is None else slot_row["sequence"])).fetchall()
        if len(observations) > 1:
            _conflict()
        if not observations:
            reasons.append("controller_observation_unavailable")
            return
        row = observations[0]
        observed = _load(row["observation"])
        if (not _index(row["unit_index"]) or observed.get("decision_index") != index
                or admission["state"] not in {"admitted", "delivery_failed"}
                or slot is not None and (row["unit_index"] != slot_row["sequence"]
                    or observed.get("label") != slot.get("label"))
                or canonical(observed.get("credit")) != canonical(admission.get("controller_input"))):
            _conflict()
        unit = observed.get("unit_ref")
        if unit is None:
            reasons.append("observation_unit_ref_unavailable")
        else:
            try:
                reference = UnitRef.from_record(unit)
            except (TypeError, ValueError) as error:
                raise ValueError("local_return_history_identity_conflict") from error
            if reference.episode_id != episode_id or reference.unit_index != row["unit_index"]:
                _conflict()
        sample.update(observation_state="observed", unit_ref=unit,
            controller_input=observed.get("credit"), controller_step=observed.get("step"),
            _observation_index=row["unit_index"])
        step = observed.get("step")
        delta = step.get("marginal_credit") if isinstance(step, dict) else None
        if type(delta) in (int, float) and math.isfinite(delta):
            sample["raw_controller_delta"] = delta
        else:
            reasons.append("standard_controller_marginal_credit_unavailable")
        if isinstance(step, dict) and "unit_label" in step and step["unit_label"] != observed.get("label"):
            _conflict()
        if (isinstance(step, dict) and "credit" in step
                and isinstance(observed.get("credit"), dict) and "credit" in observed["credit"]
                and step["credit"] != observed["credit"]["credit"]):
            _conflict()

    def _link_waits(self, samples, episode_id, tables, reasons):
        if "episode_waits" not in tables:
            if samples:
                reasons.append("wait_records_unavailable")
            return
        by_handle = {sample["child_handle"]: sample for sample in samples}
        rows = self.store.db.execute("SELECT wait_id,original_decision_index,request_sha256,request,wake,outcome "
            "FROM episode_waits WHERE run_id=? AND parent_episode_id=? "
            "AND json_extract(outcome,'$.wake_reason')='returned' ORDER BY original_decision_index,wait_id",
            (self.journal.run_id, episode_id))
        for row in rows:
            outcome = _load(row["outcome"])
            trigger = outcome.get("trigger")
            if not isinstance(trigger, dict) or trigger.get("handle") not in by_handle:
                continue
            request = _load(row["request"])
            wake = None if row["wake"] is None else _load(row["wake"])
            try:
                condition = validate_condition(request["condition"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("local_return_history_wait_identity_conflict") from error
            duration = outcome.get("measured_duration_seconds")
            if (request.get("version") != "wait_request_v1" or request.get("wait_id") != row["wait_id"]
                    or request.get("parent_episode_id") != episode_id
                    or request.get("original_decision_index") != row["original_decision_index"]
                    or content_digest(request) != row["request_sha256"]
                    or outcome.get("version") != "wait_outcome_v1" or outcome.get("wait_id") != row["wait_id"]
                    or outcome.get("condition_sha256") != content_digest(condition)
                    or outcome.get("duration_measure") != "measured_wait_intervals"
                    or type(outcome.get("unmeasured_interruption")) is not bool
                    or duration is not None and (type(duration) not in (int, float)
                        or not math.isfinite(duration) or duration < 0)
                    or not isinstance(wake, dict) or wake.get("reason") != "returned"):
                raise ValueError("local_return_history_wait_identity_conflict")
            selected = {event["handle"]: event["after_cursor"] for event in condition["events"]
                        if event["event"] == "returned"}
            events = [event for event in wake.get("events", []) if event.get("event") == "returned"
                      and event.get("handle") == trigger["handle"] and event.get("cursor") == trigger.get("cursor")]
            sample = by_handle[trigger["handle"]]
            if (trigger["handle"] not in selected or not _index(trigger.get("cursor"))
                    or trigger["cursor"] <= selected[trigger["handle"]] or len(events) != 1
                    or events[0].get("record_ref") not in (None, sample["return_id"])):
                raise ValueError("local_return_history_wait_identity_conflict")
            sample["linked_waits"].append({key: outcome[key] for key in (
                "wait_id", "condition_sha256", "measured_duration_seconds",
                "duration_measure", "unmeasured_interruption")})


__all__ = ["LocalReturnHistory", "LocalReturnHistoryV1", "LocalReturnSampleV1",
           "SelectionToReturnV1", "LinkedWaitV1", "VERSION"]
