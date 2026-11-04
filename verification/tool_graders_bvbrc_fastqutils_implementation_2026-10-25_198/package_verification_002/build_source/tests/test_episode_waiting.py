"""C6 selected waits; scripted event providers, real isolated Store/history."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import execution_timing as timing
from gene_annotation_episode.numerical import YieldController, estimate_score_yield
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory, RunStatistic
from gene_annotation_episode.state import Store
from gene_annotation_episode.waiting import (WaitError, WaitStore, completed_action_context,
    estimate_wait, validate_condition)


STAMP = "2026-10-21T12:00:00+00:00"
DEADLINE = "2026-10-21T13:00:00+00:00"


def pending(*handles, expectation_refs=(), resource=None):
    return {"version": "pending_work_v1", "captured_at": STAMP, "items": [
        {"handle": handle, "role": "improvement", "lifecycle_state": "executing",
         "selected_at": STAMP, "observed_at": STAMP, "resource_selection": resource,
         "expectation_snapshot_refs": list(expectation_refs), "latest_progress_ref": None,
         "return_available": False} for handle in handles]}


def condition(*handles, after_cursor=0, reconsider_at=None, event="returned"):
    return {"version": "event_condition_v1", "events": [
        {"handle": handle, "event": event, "after_cursor": after_cursor} for handle in handles],
        "reconsider_at": reconsider_at}


def request(selected=None, *, wait_id="wait:0", index=0):
    selected = condition("child:a") if selected is None else selected
    estimate = estimate_wait(selected, pending("child:a", "child:b"), [], [], [])
    return {"version": "wait_request_v1", "wait_id": wait_id, "parent_episode_id": "parent",
        "original_decision_index": index, "condition": selected, "estimate_snapshot": estimate}


def wake(selected, *, handle=None, event="returned", cursor=1):
    return {"version": "event_wake_v1", "reason": event if handle else "reconsideration",
        "observed_at": DEADLINE, "reconsider_at": selected["reconsider_at"],
        "events": [{"cursor": cursor, "handle": handle, "event": event,
                    "record_ref": "return:actual"}] if handle else []}


@pytest.fixture
def clock(monkeypatch):
    state = {"ns": 10_000_000_000,
        "identity": {"pid": 123, "start_ticks": "77", "boot_id": "boot"}}
    monkeypatch.setattr(timing.time, "monotonic_ns", lambda: state["ns"])
    monkeypatch.setattr(timing, "_process_identity", lambda pid=None: state["identity"])
    return state


class ImmediateProvider:
    def __init__(self, returned, clock=None):
        self.returned, self.clock, self.calls = returned, clock, []

    async def wait_events(self, selected):
        self.calls.append(deepcopy(selected))
        if self.clock:
            self.clock["ns"] += 2_000_000_000
        return deepcopy(self.returned)


@pytest.mark.parametrize("event", ["returned", "state_changed", "progress_committed"])
def test_selected_event_set_closes_once_and_replays_original_outcome(tmp_path, clock, event):
    selected = condition("child:a", "child:b", after_cursor=4, event=event)
    selected_request = request(selected)
    provider = ImmediateProvider(wake(selected, handle="child:b", cursor=7, event=event), clock)
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        first = asyncio.run(waits.perform_wait(selected_request, provider))
        saved = waits.get("wait:0")
        assert first["version"] == "wait_outcome_v1"
        assert first["trigger"] == {"handle": "child:b", "cursor": 7}
        assert first["measured_duration_seconds"] == 2
        assert first["wake_reason"] == event
        assert first["duration_measure"] == "measured_wait_intervals"
        assert first["unmeasured_interruption"] is False
        assert saved["request"] == selected_request
        assert saved["wake"] == provider.returned
        clock["ns"] += 1_000_000_000_000
        assert asyncio.run(WaitStore(store, "run").perform_wait(selected_request, provider)) == first
        assert len(provider.calls) == 1
        assert waits.get("wait:0") == saved
        # Wait persistence writes no scientific ledger or controller history.
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == 0


def test_arrival_during_provider_subscription_is_not_reinspected_or_lost(tmp_path):
    async def scenario():
        # The provider owns race-free observation. E passes the original cursor
        # directly instead of first inspecting status or using a later cursor.
        class RaceProvider:
            def __init__(self):
                self.inspected = asyncio.Event()
                self.subscribed = asyncio.Event()
                self.rows = []
                self.calls = 0

            async def wait_events(self, selected):
                self.calls += 1
                assert selected == selection
                self.inspected.set()
                await self.subscribed.wait()
                # Durable backlog is inspected after subscription installation.
                assert self.rows
                return wake(selected, handle="child:a", cursor=self.rows[0])

        selection = condition("child:a", after_cursor=41)
        provider = RaceProvider()
        with Store(tmp_path) as store:
            waits = WaitStore(store, "run")
            task = asyncio.create_task(waits.perform_wait(request(selection), provider))
            await provider.inspected.wait()
            provider.rows.append(42)
            provider.subscribed.set()
            result = await task
            assert result["trigger"]["cursor"] == 42
            assert provider.calls == 1
    asyncio.run(scenario())


def test_episode_selected_reconsideration_has_no_fabricated_events(tmp_path, clock):
    selection = condition(reconsider_at=DEADLINE)
    provider = ImmediateProvider(wake(selection), clock)
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        outcome = asyncio.run(waits.perform_wait(request(selection), provider))
        assert provider.calls == [selection]
        assert outcome["wake_reason"] == "reconsideration"
        assert outcome["trigger"] is None
        assert waits.get("wait:0")["wake"]["events"] == []
        assert outcome["measured_duration_seconds"] == 2


def test_cancellation_keeps_intervals_deadline_and_does_not_cancel_target(tmp_path, clock):
    async def scenario():
        class BlockingProvider:
            def __init__(self):
                self.entered = asyncio.Event()
                self.target_cancelled = False
                self.calls = []

            async def wait_events(self, selected):
                self.calls.append(deepcopy(selected))
                self.entered.set()
                await asyncio.Future()

        selection = condition("child:a", reconsider_at=DEADLINE)
        selected_request = request(selection)
        provider = BlockingProvider()
        with Store(tmp_path) as store:
            waits = WaitStore(store, "run")
            task = asyncio.create_task(waits.perform_wait(selected_request, provider))
            await provider.entered.wait()
            clock["ns"] += 3_000_000_000
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            saved = waits.get("wait:0")
            assert saved["outcome"] is None
            assert saved["timing"]["intervals"][-1]["state"] == "interrupted"
            assert saved["timing"]["measured_elapsed_seconds"] == 3
            assert provider.target_cancelled is False
        # A new connection resumes the same selection, excluding offline time.
        clock["ns"] += 1_000_000_000_000
        later = ImmediateProvider(wake(selection, handle="child:a"), clock)
        with Store(tmp_path) as store:
            resumed = WaitStore(store, "run")
            result = await resumed.perform_wait(selected_request, later)
            assert result["measured_duration_seconds"] == 5
            assert result["unmeasured_interruption"] is True
            assert result["started_at"] == saved["timing"]["intervals"][0]["started_at"]
            assert resumed.get("wait:0")["request"] == selected_request
            assert later.calls[0]["reconsider_at"] == DEADLINE
    asyncio.run(scenario())


def test_recovery_never_turns_a_lost_interval_or_offline_gap_into_measurement(tmp_path, clock):
    selected_request = request(condition("child:a", reconsider_at=DEADLINE))
    lost = {"version": timing.VERSION, "intervals": [
        {"state": "returned", "started_at": STAMP, "ended_at": STAMP, "elapsed_seconds": 3},
        {"state": "running", "owner": dict(clock["identity"]), "started_at": STAMP,
         "started_monotonic_ns": clock["ns"], "ended_at": None,
         "elapsed_seconds": None, "exception_type": None}],
        "measured_elapsed_seconds": 3, "unmeasured_ended_intervals": 0}
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        waits.select(selected_request)
        # Actual durable crash state: no measured end exists for this owner.
        store.db.execute("UPDATE episode_waits SET timing=? WHERE wait_id=?",
            (json.dumps(lost), selected_request["wait_id"]))
    clock["ns"] += 10_000_000_000_000
    clock["identity"] = {**clock["identity"], "start_ticks": "restarted"}
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        provider = ImmediateProvider(wake(selected_request["condition"], handle="child:a"), clock)
        result = asyncio.run(waits.perform_wait(selected_request, provider))
        persisted = waits.get("wait:0")
        assert result["measured_duration_seconds"] == 5
        assert result["unmeasured_interruption"] is True
        assert persisted["timing"]["unmeasured_ended_intervals"] == 1
        assert persisted["timing"]["intervals"][1]["elapsed_seconds"] is None
        assert persisted["timing"]["intervals"][1]["ended_at"] is None
        assert persisted["timing"]["intervals"][1]["state"] == "end_unobserved"
        assert persisted["request"] == selected_request


def test_concurrent_wait_attempt_cannot_overwrite_a_live_interval(tmp_path):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        selected_request = request()

        class Blocking:
            async def wait_events(self, selected):
                entered.set()
                await release.wait()
                return wake(selected, handle="child:a")

        with Store(tmp_path) as first, Store(tmp_path) as second:
            one, two = WaitStore(first, "run"), WaitStore(second, "run")
            task = asyncio.create_task(one.perform_wait(selected_request, Blocking()))
            await entered.wait()
            original = two.get("wait:0")
            with pytest.raises(WaitError, match="wait_already_active"):
                await two.perform_wait(selected_request, ImmediateProvider(wake(
                    selected_request["condition"], handle="child:a")))
            assert two.get("wait:0") == original
            release.set()
            await task
    asyncio.run(scenario())


def test_selection_and_schema_setup_participate_in_caller_transaction(tmp_path):
    selected_request = request()
    with Store(tmp_path) as store:
        with pytest.raises(RuntimeError):
            with store.transaction():
                WaitStore(store, "run").select(selected_request)
                assert store.db.in_transaction
                raise RuntimeError("rollback selected action")
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='episode_waits'").fetchone() is None
        waits = WaitStore(store, "run")
        with pytest.raises(RuntimeError):
            with store.transaction():
                waits.select(selected_request)
                raise RuntimeError("rollback selection")
        assert waits.get("wait:0") is None
        waits.select(selected_request)
        with Store(tmp_path) as other:
            assert WaitStore(other, "run").get("wait:0")["request"] == selected_request


def test_operation_identity_preserves_original_estimate_and_refuses_changed_selection(tmp_path):
    selected_request = request()
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        saved = waits.select(selected_request)
        assert waits.select(deepcopy(selected_request)) == saved
        changed = deepcopy(selected_request)
        changed["estimate_snapshot"]["captured_at"] = DEADLINE
        with pytest.raises(WaitError, match="wait_identity_conflict"):
            waits.select(changed)
        another = deepcopy(selected_request)
        another["wait_id"] = "different:identity"
        with pytest.raises(WaitError, match="wait_identity_conflict"):
            waits.select(another)
        assert waits.get("wait:0") == saved


@pytest.mark.parametrize("replacement", [
    {"handle": "unselected", "event": "returned", "cursor": 4, "record_ref": None},
    {"handle": "child:a", "event": "returned", "cursor": 3, "record_ref": None},
    {"handle": "child:a", "event": "progress_committed", "cursor": 4, "record_ref": None},
])
def test_unselected_old_or_different_events_cannot_complete_wait(tmp_path, replacement):
    selection = condition("child:a", after_cursor=3)
    bad = wake(selection, handle="child:a", cursor=4)
    bad["events"] = [replacement]
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        with pytest.raises(WaitError, match="invalid_event_wake"):
            asyncio.run(waits.perform_wait(request(selection), ImmediateProvider(bad)))
        saved = waits.get("wait:0")
        assert saved["outcome"] is None
        assert saved["timing"]["intervals"][-1]["state"] == "raised"


def test_unknown_probability_is_not_fabricated_from_real_duration_mean(tmp_path):
    scope = ExecutionClass(phase="protein_homology_search", backend="local", resource_id="host:local",
        implementation_sha256="a" * 64, parameters_sha256="b" * 64,
        memory_bytes=20 * 2**30, scratch_bytes=4 * 2**30, cpu_threads=2,
        query_residues=253, reference_residues=1000, reference_records=10,
        reference_state="available")
    history = RunHistory(tmp_path / "statistics.sqlite3")
    for i, (outcome, kind, seconds) in enumerate([
            ("succeeded", "complete", 10), ("succeeded", "complete", 20),
            ("failed", "complete", 2), ("unknown", "lower_bound", 7),
            ("cancelled", "unmeasured", None)]):
        history.record(scope, RunStatistic(attempt_sha256=f"{i:064x}", source_sha256="c" * 64,
            observed_at=STAMP, outcome=outcome, duration_kind=kind, elapsed_seconds=seconds,
            condition_ref=None))
    ref = history.capture(scope)
    reader = history.reader(ref)
    snapshot = {"ref": ref, "data": reader.get(ref)}
    reader.close()
    history.close()
    resource = {"resource_id": "host:local", "kind": "local", "capability_binding_ref": "capability:bound",
        "allocation": {"cpu": 2, "memory_bytes": 20 * 2**30, "scratch_bytes": 4 * 2**30,
                       "wall_seconds": None}}
    work = pending("child:a", expectation_refs=[ref], resource=resource)
    selection = condition("child:a", reconsider_at=DEADLINE)
    progress = [{"version": "progress_snapshot_v1", "target_handle": "child:a",
        "progress_ref": "progress:recorded", "observed_at": STAMP,
        "measurements": [{"name": "elapsed", "value": 7, "unit": "seconds"}]}]
    local = [{"observation_ref": "observation:previous", "marginal_credit": 0}]
    estimate = estimate_wait(selection, work, progress, [snapshot], local)
    assert estimate["duration_expectation_refs"] == [ref]
    assert estimate["progress_refs"] == ["progress:recorded"]
    assert estimate["local_history_refs"] == ["observation:previous"]
    assert estimate["event_expectations"] == [{"handle": "child:a", "event": "returned",
        "probability": None, "method": "exact_class_duration_summary_only",
        "support_refs": [ref, "progress:recorded"]}]
    assert estimate["scientific_gain"] is estimate["monitoring_gain"] is None
    assert "event_probability_model_unbound" in estimate["unavailable_reasons"]
    # Preserve all outcome/censoring facts in the original completion context.
    context = completed_action_context({}, pending_at_selection=work, pending_after_action=work,
        wait_estimate_at_selection=estimate, progress_records=progress,
        duration_expectations=[snapshot], own_completed_action_history=local)
    assert context["duration_expectations"][0] == snapshot
    assert len(snapshot["data"]["statistics"]) == 4
    assert context["progress_records"] == progress
    assert context["own_completed_action_history"] == local
    # Explicit reference selection cannot transfer this support to another job.
    incompatible = pending("child:a", expectation_refs=[ref], resource={**resource, "resource_id": "other:host"})
    missing = estimate_wait(selection, incompatible, progress, [snapshot], local)
    assert missing["duration_expectation_refs"] == []
    assert missing["event_expectations"][0]["probability"] is None
    assert "duration_resource_mismatch" in missing["unavailable_reasons"]
    wrong_cpu = pending("child:a", expectation_refs=[ref], resource={**resource,
        "allocation": {**resource["allocation"], "cpu": 4}})
    unsupported = estimate_wait(selection, wrong_cpu, progress, [snapshot], local)
    assert unsupported["duration_expectation_refs"] == []
    assert "duration_allocation_mismatch" in unsupported["unavailable_reasons"]
    unavailable = estimate_wait(selection, work, progress,
        {"status": "unavailable", "snapshots": [snapshot]}, local)
    assert unavailable["duration_expectation_refs"] == []
    assert "duration_history_unavailable" in unavailable["unavailable_reasons"]
    empty = estimate_wait(selection, pending("child:a"), [], [snapshot], [])
    assert empty["duration_expectation_refs"] == []
    assert empty["event_expectations"][0]["method"] == "unavailable"


def test_invalid_frozen_duration_identity_is_not_accepted_as_support(tmp_path):
    # Corrupted payload claims an existing snapshot identity. Finite data alone
    # cannot make the claim into measured duration support.
    snapshot = {"ref": "execution_expectation_" + "a" * 64,
        "data": {"execution_class": {"phase": "unknown"}}}
    estimate = estimate_wait(condition("child:a"), pending("child:a", expectation_refs=[snapshot["ref"]]),
        [], [snapshot], [])
    assert estimate["duration_expectation_refs"] == []
    assert "invalid_duration_support" in estimate["unavailable_reasons"]


def test_original_pending_wait_snapshots_reach_configured_estimator_at_actual_observation(tmp_path, clock):
    seen = []

    def contextual(history, parameters, contexts):
        seen.append((history, deepcopy(contexts)))
        # Caller explicitly retains the unchanged formula for this fixture.
        return estimate_score_yield(history, parameters)

    before = pending("child:a")
    after = pending("child:a")
    after["items"][0].update(lifecycle_state="returned", return_available=True)
    selected_request = request()
    controller = YieldController("epoch", 5, 0.001, estimate_with_context=contextual)
    with Store(tmp_path) as store:
        waits = WaitStore(store, "run")
        outcome = asyncio.run(waits.perform_wait(selected_request, ImmediateProvider(
            wake(selected_request["condition"], handle="child:a"), clock)))
        # Returning a wait itself creates no controller observation or child
        # receipt. F owns wait-first, child-admission-second completion routing.
        assert controller.state().history == ()
        context = completed_action_context({"expectations": {"status": "unavailable"}},
            pending_at_selection=before, pending_after_action=after,
            wait_estimate_at_selection=selected_request["estimate_snapshot"], wait_outcome=outcome)
        controller.observe("wait:0", {"credit": 5, "estimation_context": context})
        assert controller.state().history == (0,)
        assert seen[-1][1][0]["pending_work_after_action"]["items"][0]["return_available"] is True
        before["items"].clear()
        after["items"].clear()
        outcome["wake_reason"] = "state_changed"
        assert context["pending_work_at_selection"]["items"]
        assert context["pending_work_after_action"]["items"]
        assert context["wait_outcome"]["wake_reason"] == "returned"
        assert context["version"] == "completed_action_estimation_context_v3"
        assert len(seen[-1][0]) == len(seen[-1][1]) == 1


@pytest.mark.parametrize("bad", [
    {"version": "event_condition_v1", "events": [], "reconsider_at": None},
    {"version": "event_condition_v1", "events": [], "reconsider_at": "2026-10-21T12:00:00"},
    {"version": "event_condition_v1", "events": [{"handle": "child:a", "event": "returned", "after_cursor": True}], "reconsider_at": None},
])
def test_invalid_conditions_are_rejected_without_selecting_a_timer(bad):
    with pytest.raises(WaitError, match="invalid_wait_record"):
        validate_condition(bad)
