"""Source recovery against actual Store/Journal rows, with synthetic outcomes.

These checks execute no model, scientific parent, native work or controller.
The delayed-return case uses the existing C4 admission transaction.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import threading

import pytest

from method_loop import ClosedRecord
from method_loop.durable import canonical
from method_loop.identities import UnitRef

from gene_annotation_episode.episode_admission import admit_return
from gene_annotation_episode.episode_completion import (
    CompletionLedger, EFFECT_VERSION, SOURCE_STATE_VERSION)
from gene_annotation_episode.episode_journal import Journal, WorkflowError
from gene_annotation_episode.state import Store
from test_episode_admission import receiver_for, setup_case


@dataclass(frozen=True)
class Value(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value


def save_action(journal, index, outcome, *, episode="parent", kind="tool", credit=None):
    journal.save("runtime_actions", {"episode_id": episode, "decision_index": index,
        "action": canonical({"kind": kind, "selection": index}),
        "result": None if outcome is None else canonical(outcome), "credit": credit})


def save_effect(journal, ledger, index, *, episode="parent", state="selected", feedback=None):
    if journal.row("runtime_model_calls", episode, index) is None:
        journal.save("runtime_model_calls", {"episode_id": episode, "call_index": index,
            "purpose": "decision", "request": canonical({"original_context": index}),
            "response": canonical({"selected_index": index})})
    return ledger.record_decision_effect(episode, index, {"version": EFFECT_VERSION,
        "state": state, "report_values": {"interpretation": index},
        "report_basis_refs": [], "feedback": feedback})


def checkpoint(ledger, *, revision=None, effect=None, outcome=None, feedback=None,
               episode="parent"):
    return ledger.checkpoint_source(episode, expected_revision=revision,
        latest_effect_index=effect, last_outcome_index=outcome, feedback=feedback)


def own_slot(ledger, index, *, episode="parent", credit=1):
    return ledger.stage(episode, index, label=f"tool:{index}", kind="own_action",
        controller_input=Value({"credit": credit, "estimation_action_index": index}),
        child_return=None)


def confirm(ledger, slot):
    ledger.confirm_observed(slot["episode_id"], slot["sequence"], {
        "label": slot["label"], "credit": slot["controller_input"],
        "step": {"completed_count": slot["sequence"] + 1},
        "unit_ref": UnitRef(slot["episode_id"], slot["sequence"]).as_record(),
        "decision_index": slot["original_decision_index"]})


def test_absent_checkpoint_and_explicit_null_cursors_survive_reopen(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        restored = ledger.restore_source("parent")
        assert restored["source_state"] is None
        assert restored["latest_effect_index"] is None
        assert restored["latest_effect"] is None
        state = checkpoint(ledger)
        assert state == {"version": SOURCE_STATE_VERSION, "episode_id": "parent",
            "revision": 0, "latest_effect_index": None, "last_outcome_index": None,
            "feedback": None}
    with Store(path) as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        assert ledger.restore_source("parent")["source_state"] == state
        assert ledger.restore_source("other")["source_state"] is None
        assert ledger.slot("parent", 0) is None


@pytest.mark.parametrize("status", ["failed", "interrupted"])
def test_failed_attempt_after_completed_slot_restores_its_own_outcome_and_feedback(tmp_path, status):
    path = tmp_path / "workspace"
    feedback = {"status": status, "code": "fixture_failure", "affected_refs": []}
    with Store(path) as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        save_action(journal, 1, {"status": "completed"}, credit=2.75)
        save_effect(journal, ledger, 1)
        original = own_slot(ledger, 1, credit=2.75)
        checkpoint(ledger, effect=1, outcome=1)
        with store.transaction():
            save_action(journal, 4, {"status": status, "feedback": feedback})
            latest = save_effect(journal, ledger, 4)
            state = checkpoint(ledger, revision=0, effect=4, outcome=4, feedback=feedback)
        assert state["revision"] == 1
        assert ledger.slot("parent", 1) is None
    with Store(path) as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        restored = ledger.restore_source("parent")
        assert restored["source_state"] == state
        assert restored["latest_effect_index"] == 4
        assert restored["latest_effect"] == latest
        assert restored["last_completed_decision_index"] == 1
        assert restored["unfinished_own_action_indices"] == []
        assert json.loads(journal.row("runtime_actions", "parent", 4)["result"])["status"] == status
        # Replaying the original observation cannot move the durable cursor
        # backward or replace the more recent failure's feedback.
        confirm(ledger, ledger.slot("parent", 0))
        assert ledger.slot("parent", 0) == original
        assert ledger.restore_source("parent")["source_state"] == state


def test_delayed_child_outcome_can_follow_a_higher_decision_index(tmp_path):
    store, spec, returned, contract, finding, receipts = setup_case(tmp_path)
    parent = spec["parent"]["episode_id"]
    with store:
        journal = Journal(store, spec["run_id"])
        ledger = CompletionLedger(store, journal)
        save_effect(journal, ledger, 7, episode=parent)
        save_action(journal, 11, {"status": "completed"}, episode=parent, credit=0)
        save_effect(journal, ledger, 11, episode=parent)
        first = own_slot(ledger, 11, episode=parent, credit=0)
        checkpoint(ledger, episode=parent, effect=11, outcome=11)
        # A failure has no controller slot, yet it is the source's last outcome.
        failure = {"code": "fixture_failure"}
        save_action(journal, 13, {"status": "failed", "feedback": failure}, episode=parent)
        save_effect(journal, ledger, 13, episode=parent)
        checkpoint(ledger, episode=parent, revision=0, effect=13, outcome=13, feedback=failure)
        with store.transaction():
            admission = admit_return(spec, returned, receiver_for(store, spec, contract, receipts))
            child = ledger.stage(parent, 7, label="child:7", kind="child_return",
                controller_input=Value(admission["controller_input"]),
                child_return={name: admission[name] for name in ("handle", "return_id", "admission_id")})
            state = checkpoint(ledger, episode=parent, revision=1, effect=13, outcome=7)
        assert [first["original_decision_index"], child["original_decision_index"]] == [11, 7]
        # A rejected selection updates source feedback without inventing an
        # action or moving its last-outcome pointer to that call's index.
        rejection = {"category": "action_contract", "detail": "fixture_rejection"}
        save_effect(journal, ledger, 14, episode=parent, state="rejected", feedback=rejection)
        state = checkpoint(ledger, episode=parent, revision=2, effect=14, outcome=7, feedback=rejection)
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, spec["run_id"])
        ledger = CompletionLedger(store, journal)
        restored = ledger.restore_source(parent)
        assert restored["source_state"] == state
        assert restored["latest_effect_index"] == 14
        assert state["last_outcome_index"] == 7 and state["revision"] == 3
        assert restored["next_call_index"] == 15
        assert journal.row("runtime_actions", parent, 14) is None
        for sequence, expected in enumerate((first, child)):
            slot = ledger.slot(parent, sequence)
            assert slot == expected
            confirm(ledger, slot)
        assert ledger.restore_source(parent)["source_state"] == state


@pytest.mark.parametrize("existing", [False, True])
def test_checkpoint_joins_outcome_effect_and_outer_store_rollback(tmp_path, existing):
    path = tmp_path / "workspace"
    with Store(path) as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        baseline = checkpoint(ledger) if existing else None
        with Store(path) as reader:
            other = CompletionLedger(reader, Journal(reader, "run"))
            with pytest.raises(KeyboardInterrupt):
                with store.transaction():
                    save_action(journal, 0, {"status": "failed"})
                    save_effect(journal, ledger, 0)
                    checkpoint(ledger, revision=0 if existing else None,
                        effect=0, outcome=0, feedback={"code": "not_committed"})
                    assert other.restore_source("parent")["source_state"] == baseline
                    raise KeyboardInterrupt("fixture rollback")
            assert other.restore_source("parent")["source_state"] == baseline
        assert ledger.restore_source("parent")["source_state"] == baseline
        assert journal.row("runtime_actions", "parent", 0) is None
        assert journal.row("runtime_model_calls", "parent", 0) is None
        assert ledger.restore_source("parent")["latest_effect"] is None


def test_exact_replay_is_detached_and_stale_changed_writer_cannot_overwrite(tmp_path):
    with Store(tmp_path / "workspace") as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        with pytest.raises(WorkflowError, match="source_checkpoint_revision_conflict"):
            checkpoint(ledger, revision=0)
        feedback = {"code": "original", "values": [1, None]}
        original = checkpoint(ledger, feedback=feedback)
        assert checkpoint(ledger, feedback={"values": [1, None], "code": "original"}) == original
        assert checkpoint(ledger, revision=0, feedback=feedback) == original
        feedback["values"].append("caller mutation")
        original["feedback"]["values"].append("return mutation")
        assert ledger.restore_source("parent")["source_state"]["feedback"] == {
            "code": "original", "values": [1, None]}
        changed = checkpoint(ledger, revision=0, feedback={"code": "newer"})
        assert changed["revision"] == 1
        # A repeat after its successful CAS uses the original expected revision.
        assert checkpoint(ledger, revision=0, feedback={"code": "newer"}) == changed
        for stale in (None, 0, 8):
            with pytest.raises(WorkflowError, match="source_checkpoint_revision_conflict"):
                checkpoint(ledger, revision=stale, feedback={"code": "stale"})
        assert ledger.restore_source("parent")["source_state"] == changed
        assert store.db.execute("SELECT count(*) FROM runtime_source_states").fetchone()[0] == 1
        for table in ("runtime_actions", "runtime_model_calls", "runtime_completion_slots", "runtime_observations"):
            assert store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] == 0


def test_canonical_content_distinguishes_boolean_and_integer_feedback(tmp_path):
    with Store(tmp_path / "workspace") as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        assert checkpoint(ledger, feedback={"value": True})["revision"] == 0
        assert checkpoint(ledger, revision=0, feedback={"value": 1})["revision"] == 1


def test_zero_indices_name_actual_records_and_checkpoint_is_returned_unchanged(tmp_path):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        save_action(journal, 0, {"status": "completed"})
        latest = save_effect(journal, ledger, 0)
        state = checkpoint(ledger, effect=0, outcome=0)
        # A newer immutable effect can exist before its source checkpoint is
        # committed. Restoration exposes both facts without rewriting either.
        save_effect(journal, ledger, 2, state="rejected", feedback={"code": "new"})
        restored = ledger.restore_source("parent")
        assert restored["latest_effect_index"] == 2
        assert restored["source_state"] == state
        assert state["latest_effect_index"] == 0 and state["last_outcome_index"] == 0
        assert latest["feedback"] is None


def test_concurrent_stale_writers_have_one_winner(tmp_path):
    path = tmp_path / "workspace"
    with Store(path) as store:
        checkpoint(CompletionLedger(store, Journal(store, "run")))
    barrier = threading.Barrier(2)

    def writer(index):
        with Store(path) as store:
            ledger = CompletionLedger(store, Journal(store, "run"))
            barrier.wait(timeout=10)
            try:
                return checkpoint(ledger, revision=0, feedback={"writer": index})
            except WorkflowError as error:
                assert str(error) == "source_checkpoint_revision_conflict"
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(writer, (1, 2)))
    winners = [result for result in results if result is not None]
    assert len(winners) == 1 and winners[0]["revision"] == 1
    with Store(path) as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        assert ledger.restore_source("parent")["source_state"] == winners[0]


@pytest.mark.parametrize("scope", ["episode", "run"])
@pytest.mark.parametrize("field", ["effect", "outcome"])
def test_checkpoint_references_cannot_cross_episode_or_run(tmp_path, scope, field):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        save_action(journal, 3, {"status": "completed"})
        save_effect(journal, ledger, 3)
        target = ledger if scope == "episode" else CompletionLedger(store, Journal(store, "other-run"))
        target_episode = "sibling" if scope == "episode" else "parent"
        expected = "decision_effect" if field == "effect" else "recorded_outcome"
        with pytest.raises(WorkflowError, match="source_checkpoint_requires_" + expected):
            checkpoint(target, episode=target_episode, **{field: 3})
        assert target.restore_source(target_episode)["source_state"] is None
        assert target.restore_source(target_episode)["latest_effect_index"] is None
        assert checkpoint(ledger, effect=3, outcome=3)["revision"] == 0


@pytest.mark.parametrize("outcome", [None, {"status": "pending"},
    {"status": "completed", "pending_handle": "still-pending"}, {}, []])
def test_checkpoint_requires_an_actual_nonpending_outcome(tmp_path, outcome):
    with Store(tmp_path / "workspace") as store:
        journal = Journal(store, "run")
        ledger = CompletionLedger(store, journal)
        with pytest.raises(WorkflowError, match="source_checkpoint_requires_recorded_outcome"):
            checkpoint(ledger, outcome=0)
        save_action(journal, 0, outcome)
        with pytest.raises(WorkflowError, match="source_checkpoint_requires_recorded_outcome"):
            checkpoint(ledger, outcome=0)
        assert store.db.execute("SELECT count(*) FROM runtime_source_states").fetchone()[0] == 0


@pytest.mark.parametrize("field", ["revision", "effect", "outcome"])
@pytest.mark.parametrize("value", [-1, True, 1.5])
def test_checkpoint_indices_and_revision_require_nonnegative_integers(tmp_path, field, value):
    with Store(tmp_path / "workspace") as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        with pytest.raises(ValueError, match="requires_nonnegative_integer"):
            checkpoint(ledger, **{field: value})
        assert ledger.restore_source("parent")["source_state"] is None


@pytest.mark.parametrize("feedback", [[], {"value": float("nan")}, {1: "invalid-key"}])
def test_checkpoint_feedback_requires_finite_json_object(tmp_path, feedback):
    with Store(tmp_path / "workspace") as store:
        ledger = CompletionLedger(store, Journal(store, "run"))
        with pytest.raises((TypeError, ValueError)):
            checkpoint(ledger, feedback=feedback)
        assert ledger.restore_source("parent")["source_state"] is None
