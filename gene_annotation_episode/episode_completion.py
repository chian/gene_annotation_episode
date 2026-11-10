"""Immutable completed-action order and decision-source restoration metadata.

The owning runtime commits outcomes, receipts and credit before staging a slot
in the same Store transaction.  This ledger records those already-computed
values; replay never executes work or recomputes a controller input.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import math
from typing import Literal, TypedDict

from method_loop import ClosedRecord
from method_loop.durable import canonical
from method_loop.identities import UnitRef

from .episode_journal import WorkflowError


SLOT_VERSION = "episode_completion_slot_v1"
EFFECT_VERSION = "episode_decision_effect_v1"
SOURCE_RESTORE_VERSION = "episode_source_restore_v1"
SOURCE_STATE_VERSION = "episode_source_state_v1"
_CHILD_KINDS = frozenset({"child", "job_child", "episode_child"})


def observes_action_outcome(kind, status):
    """Executed own attempts enter their iterator even when acquisition fails.

    Callers use recorded, dispatched actions. A returned invalid result is an
    executed failed attempt, just like another failed source read or reasoning
    commit. Requests rejected before acquiring a unit have no executed action
    here. Pending work and child report admission retain their own boundaries.
    """
    return status in {"completed", "partial"} or (
        kind in {"tool", "reason"} and status in {"invalid", "failed", "unavailable"}) or (
        kind in _CHILD_KINDS and status in {"failed", "interrupted"})


class ChildReturnRefV1(TypedDict):
    handle: str
    return_id: str
    admission_id: str


class CompletionSlotV1(TypedDict):
    version: Literal["episode_completion_slot_v1"]
    episode_id: str
    sequence: int
    original_decision_index: int
    label: str
    kind: Literal["own_action", "child_return"]
    controller_input: dict
    child_return: ChildReturnRefV1 | None


class DecisionEffectV1(TypedDict):
    version: Literal["episode_decision_effect_v1"]
    state: Literal["selected", "rejected", "redelivery"]
    report_values: dict
    report_basis_refs: list[str]
    feedback: dict | None


class SourceStateV1(TypedDict):
    version: Literal["episode_source_state_v1"]
    episode_id: str
    revision: int
    latest_effect_index: int | None
    last_outcome_index: int | None
    feedback: dict | None


class SourceRestoreV1(TypedDict):
    version: Literal["episode_source_restore_v1"]
    next_call_index: int
    latest_effect: DecisionEffectV1 | None
    latest_effect_index: int | None
    last_completed_decision_index: int | None
    unfinished_own_action_indices: list[int]
    source_state: SourceStateV1 | None


def _text(value, name):
    if not isinstance(value, str) or not value:
        raise ValueError(name + "_required")
    return value


def _index(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(name + "_requires_nonnegative_integer")
    return value


def _object(value, name):
    if not isinstance(value, Mapping):
        raise TypeError(name + "_requires_json_object")
    return json.loads(canonical(value))


def _child_reference(value):
    value = _object(value, "child_return")
    if set(value) != {"handle", "return_id", "admission_id"}:
        raise ValueError("invalid_child_return_reference")
    for name, item in value.items():
        _text(item, name)
    return value


def _effect(value):
    value = _object(value, "decision_effect")
    if (set(value) != {"version", "state", "report_values", "report_basis_refs", "feedback"}
            or value["version"] != EFFECT_VERSION
            or value["state"] not in {"selected", "rejected", "redelivery"}):
        raise ValueError("invalid_decision_effect")
    _object(value["report_values"], "report_values")
    refs = value["report_basis_refs"]
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError("report_basis_references_required")
    if value["feedback"] is not None:
        _object(value["feedback"], "feedback")
    return value


class CompletionLedger:
    """Ordering metadata scoped by the Journal's original run identity."""

    def __init__(self, store, journal):
        if journal.db is not store.db:
            raise ValueError("completion_journal_requires_same_store_connection")
        self.store, self.journal, self.db = store, journal, store.db
        self.run_id = journal.run_id
        # execute(), unlike executescript(), joins an outer Store transaction.
        with store.transaction():
            self.db.execute("""CREATE TABLE IF NOT EXISTS runtime_completion_slots (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                sequence INTEGER NOT NULL, original_decision_index INTEGER NOT NULL,
                slot TEXT NOT NULL, PRIMARY KEY(run_id,episode_id,sequence),
                UNIQUE(run_id,episode_id,original_decision_index))""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS runtime_decision_effects (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                decision_index INTEGER NOT NULL, effect TEXT NOT NULL,
                PRIMARY KEY(run_id,episode_id,decision_index))""")
            self.db.execute("""CREATE TABLE IF NOT EXISTS runtime_source_states (
                run_id TEXT NOT NULL, episode_id TEXT NOT NULL,
                source_state TEXT NOT NULL, PRIMARY KEY(run_id,episode_id))""")

    def stage(self, episode_id, original_decision_index, *, label,
              kind: Literal["own_action", "child_return"],
              controller_input: ClosedRecord,
              child_return: ChildReturnRefV1 | None) -> CompletionSlotV1:
        """Freeze one completion in arrival order, joining the outcome transaction."""
        _text(episode_id, "episode_id")
        _index(original_decision_index, "original_decision_index")
        _text(label, "label")
        if kind not in {"own_action", "child_return"}:
            raise ValueError("invalid_completion_kind")
        if not isinstance(controller_input, ClosedRecord):
            raise TypeError("completion_controller_input_requires_closed_record")
        value = _object(controller_input.as_record(), "controller_input")
        if kind == "child_return":
            child_return = _child_reference(child_return)
        elif child_return is not None:
            raise ValueError("own_action_has_no_child_return")
        with self.store.transaction():
            old = self.db.execute("SELECT sequence,slot FROM runtime_completion_slots "
                "WHERE run_id=? AND episode_id=? AND original_decision_index=?",
                (self.run_id, episode_id, original_decision_index)).fetchone()
            sequence = (old["sequence"] if old else self.db.execute(
                "SELECT coalesce(max(sequence)+1,0) FROM runtime_completion_slots "
                "WHERE run_id=? AND episode_id=?", (self.run_id, episode_id)).fetchone()[0])
            slot = {"version": SLOT_VERSION, "episode_id": episode_id, "sequence": sequence,
                "original_decision_index": original_decision_index, "label": label,
                "kind": kind, "controller_input": value, "child_return": child_return}
            if old is not None:
                if canonical(slot) != old["slot"]:
                    raise WorkflowError("completion_identity_conflict")
                return json.loads(old["slot"])
            action = self.journal.row("runtime_actions", episode_id, original_decision_index)
            if action is None or action["result"] is None or action["credit"] is None:
                raise WorkflowError("completion_requires_recorded_outcome_and_credit")
            from .numerical import validate_task_credit
            validate_task_credit(action['credit'])
            action_kind = json.loads(action["action"]).get("kind")
            if not observes_action_outcome(action_kind, json.loads(action["result"]).get("status")):
                raise WorkflowError("completion_requires_recorded_outcome_and_credit")
            is_child = action_kind in _CHILD_KINDS
            outcome = json.loads(action['result'])
            attempted_dispatch = (is_child and kind == 'own_action' and child_return is None
                and outcome.get('status') == 'failed' and outcome.get('execution_handle') is not None)
            if not attempted_dispatch and is_child != (kind == "child_return"):
                raise WorkflowError("completion_action_kind_conflict")
            if child_return is not None:
                self._validate_admission(episode_id, original_decision_index, value, child_return)
            self.db.execute("INSERT INTO runtime_completion_slots VALUES(?,?,?,?,?)",
                (self.run_id, episode_id, sequence, original_decision_index, canonical(slot)))
            return slot

    def _validate_admission(self, episode_id, index, controller_input, reference):
        installed = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_return_admissions'").fetchone()
        row = (self.db.execute("SELECT admission FROM runtime_return_admissions "
            "WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?",
            (self.run_id, episode_id, index)).fetchone() if installed else None)
        if row is None:
            raise WorkflowError("completion_requires_child_admission")
        from .episode_admission import load_return_admission
        admission = load_return_admission(self.store, self.run_id, reference["return_id"])
        if (any(admission[name] != value for name, value in reference.items())
                or admission["parent_episode_id"] != episode_id
                or admission["original_decision_index"] != index
                or admission["state"] not in {"admitted", "delivery_failed", "execution_failed"}
                or canonical(admission["controller_input"]) != canonical(controller_input)):
            raise WorkflowError("completion_child_admission_conflict")

    def slot(self, episode_id, sequence: int) -> CompletionSlotV1 | None:
        _text(episode_id, "episode_id")
        _index(sequence, "sequence")
        row = self.db.execute("SELECT slot FROM runtime_completion_slots WHERE run_id=? "
            "AND episode_id=? AND sequence=?", (self.run_id, episode_id, sequence)).fetchone()
        return None if row is None else json.loads(row[0])

    def confirm_observed(self, episode_id, sequence: int, observation: dict) -> None:
        """Persist the ordinary on_unit hook's value after controller observation."""
        observation = _object(observation, "observation")
        with self.store.transaction():
            slot = self.slot(episode_id, sequence)
            if slot is None:
                raise WorkflowError("completion_slot_unavailable")
            if set(observation) != {"label", "credit", "step", "unit_ref", "decision_index"}:
                raise WorkflowError("completion_observation_conflict")
            try:
                unit_ref = UnitRef.from_record(observation["unit_ref"])
            except (TypeError, ValueError) as error:
                raise WorkflowError("completion_observation_conflict") from error
            if (unit_ref.episode_id != episode_id or unit_ref.unit_index != sequence
                    or type(observation["decision_index"]) is not int
                    or observation["decision_index"] != slot["original_decision_index"]
                    or observation["label"] != slot["label"]
                    or canonical(observation["credit"]) != canonical(slot["controller_input"])):
                raise WorkflowError("completion_observation_conflict")
            old = self.journal.row("runtime_observations", episode_id, sequence)
            if old is not None:
                if canonical(json.loads(old["observation"])) != canonical(observation):
                    raise WorkflowError("completion_observation_conflict")
                return
            self.journal.save("runtime_observations", {"episode_id": episode_id,
                "unit_index": sequence, "observation": canonical(observation)})

    def record_decision_effect(self, episode_id, decision_index,
                               effect: DecisionEffectV1) -> DecisionEffectV1:
        """Freeze a real call's validated state, including rejected selections."""
        _text(episode_id, "episode_id")
        _index(decision_index, "decision_index")
        effect = _effect(effect)
        with self.store.transaction():
            old = self.db.execute("SELECT effect FROM runtime_decision_effects WHERE run_id=? "
                "AND episode_id=? AND decision_index=?",
                (self.run_id, episode_id, decision_index)).fetchone()
            if old is not None:
                if old[0] != canonical(effect):
                    raise WorkflowError("decision_effect_identity_conflict")
                return json.loads(old[0])
            call = self.journal.row("runtime_model_calls", episode_id, decision_index)
            if call is None or call["purpose"] != "decision" or call["response"] is None:
                raise WorkflowError("decision_effect_requires_saved_response")
            if (effect["state"] == "selected"
                    and self.journal.row("runtime_actions", episode_id, decision_index) is None):
                raise WorkflowError("selected_decision_effect_requires_saved_action")
            self.db.execute("INSERT INTO runtime_decision_effects VALUES(?,?,?,?)",
                (self.run_id, episode_id, decision_index, canonical(effect)))
            return effect

    def checkpoint_source(self, episode_id, *, expected_revision: int | None,
                          latest_effect_index: int | None,
                          last_outcome_index: int | None,
                          feedback: dict | None) -> SourceStateV1:
        """Save the owning source's cursor with compare-and-set semantics.

        None expects an absent checkpoint; the first revision is zero. An exact
        replay of current content returns that revision even if its original
        expected revision has since been consumed. Changed content must name
        the current revision. Outcome order is supplied by the source, including
        failed attempts and delayed returns, never inferred from decision order.
        """
        _text(episode_id, "episode_id")
        for name, value in (("expected_revision", expected_revision),
                            ("latest_effect_index", latest_effect_index),
                            ("last_outcome_index", last_outcome_index)):
            if value is not None:
                _index(value, name)
        if feedback is not None:
            feedback = _object(feedback, "feedback")
        with self.store.transaction():
            if latest_effect_index is not None:
                effect = self.db.execute("SELECT 1 FROM runtime_decision_effects "
                    "WHERE run_id=? AND episode_id=? AND decision_index=?",
                    (self.run_id, episode_id, latest_effect_index)).fetchone()
                if effect is None:
                    raise WorkflowError("source_checkpoint_requires_decision_effect")
            if last_outcome_index is not None:
                action = self.journal.row("runtime_actions", episode_id, last_outcome_index)
                outcome = (None if action is None or action["result"] is None
                           else json.loads(action["result"]))
                if (not isinstance(outcome, dict)
                        or not isinstance(outcome.get("status"), str)
                        or not outcome["status"] or outcome["status"] == "pending"
                        or outcome.get("pending_handle") is not None):
                    raise WorkflowError("source_checkpoint_requires_recorded_outcome")
            old = self.db.execute("SELECT source_state FROM runtime_source_states "
                "WHERE run_id=? AND episode_id=?", (self.run_id, episode_id)).fetchone()
            previous = None if old is None else json.loads(old[0])
            revision = None if previous is None else previous["revision"]
            state = {"version": SOURCE_STATE_VERSION, "episode_id": episode_id,
                "revision": 0 if revision is None else revision,
                "latest_effect_index": latest_effect_index,
                "last_outcome_index": last_outcome_index, "feedback": feedback}
            if old is not None and old[0] == canonical(state):
                return previous
            if expected_revision != revision:
                raise WorkflowError("source_checkpoint_revision_conflict")
            if revision is not None:
                state["revision"] = revision + 1
            self.db.execute("INSERT INTO runtime_source_states VALUES(?,?,?) "
                "ON CONFLICT(run_id,episode_id) DO UPDATE SET source_state=excluded.source_state",
                (self.run_id, episode_id, canonical(state)))
            return state

    def restore_source(self, episode_id) -> SourceRestoreV1:
        """Return source cursors without replaying a selection or creating a slot.

        A saved call without an effect still needs its normal response handling.
        An ordinary outcome awaiting projection/staging remains unfinished;
        executed failures awaiting observation do too. Rejected requests and
        independently executing children do not.
        Legacy actions without slots retain unknown historical completion order.
        """
        _text(episode_id, "episode_id")
        with self.store.read_snapshot():
            missing = self.db.execute("SELECT c.call_index FROM runtime_model_calls c "
                "LEFT JOIN runtime_decision_effects e ON e.run_id=c.run_id "
                "AND e.episode_id=c.episode_id AND e.decision_index=c.call_index "
                "WHERE c.run_id=? AND c.episode_id=? AND c.purpose='decision' "
                "AND e.decision_index IS NULL ORDER BY c.call_index LIMIT 1",
                (self.run_id, episode_id)).fetchone()
            next_index = (missing[0] if missing is not None else self.db.execute(
                "SELECT coalesce(max(call_index)+1,0) FROM runtime_model_calls WHERE run_id=? "
                "AND episode_id=? AND purpose='decision'", (self.run_id, episode_id)).fetchone()[0])
            latest = self.db.execute("SELECT decision_index,effect FROM runtime_decision_effects WHERE run_id=? "
                "AND episode_id=? ORDER BY decision_index DESC LIMIT 1",
                (self.run_id, episode_id)).fetchone()
            completed = self.db.execute("SELECT original_decision_index FROM runtime_completion_slots "
                "WHERE run_id=? AND episode_id=? ORDER BY sequence DESC LIMIT 1",
                (self.run_id, episode_id)).fetchone()
            checkpoint = self.db.execute("SELECT source_state FROM runtime_source_states "
                "WHERE run_id=? AND episode_id=?", (self.run_id, episode_id)).fetchone()
            unfinished = []
            rows = self.db.execute("SELECT a.decision_index,a.action,a.result FROM runtime_actions a "
                "LEFT JOIN runtime_completion_slots s ON s.run_id=a.run_id "
                "AND s.episode_id=a.episode_id AND s.original_decision_index=a.decision_index "
                "WHERE a.run_id=? AND a.episode_id=? AND s.sequence IS NULL ORDER BY a.decision_index",
                (self.run_id, episode_id))
            for row in rows:
                action = json.loads(row["action"])
                result = None if row["result"] is None else json.loads(row["result"])
                if action.get("kind") in _CHILD_KINDS:
                    continue
                if result is not None and (result.get("pending_handle") is not None
                        or not observes_action_outcome(action.get("kind"), result.get("status"))):
                    continue
                unfinished.append(row["decision_index"])
            return {"version": SOURCE_RESTORE_VERSION, "next_call_index": next_index,
                "latest_effect": None if latest is None else json.loads(latest["effect"]),
                "latest_effect_index": None if latest is None else latest["decision_index"],
                "last_completed_decision_index": None if completed is None else completed[0],
                "unfinished_own_action_indices": unfinished,
                "source_state": None if checkpoint is None else json.loads(checkpoint[0])}
