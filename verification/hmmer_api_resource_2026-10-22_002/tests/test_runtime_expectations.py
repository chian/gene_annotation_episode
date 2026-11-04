"""Actual method_loop plumbing with synthetic scores/models/estimator policies.

Fixture stopping counts and supplied numeric bands test routing/replay. They are
not an approved monitoring/time formula or evidence of biological annotation.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sqlite3

import pytest

from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
from gene_annotation_episode.run_statistics import ExecutionClass, RunHistory, RunStatistic
from gene_annotation_episode.runtime import WorkflowError, run_workflow
from test_runtime import (FixtureController, FixtureTools, ScriptedProvider, commission,
                          fixture_credit, obj, reason, setup, tool)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def make_history(path):
    scope = ExecutionClass(phase="protein_homology_search", backend="local", resource_id="fixture-host",
        implementation_sha256=digest("fixture-program"), parameters_sha256=digest("fixture-params"),
        memory_bytes=20*1024**3, scratch_bytes=4*1024**3, cpu_threads=1,
        query_residues=253, reference_residues=209017843, reference_records=575748,
        reference_state="available")
    append(path, scope, "first", 2)
    return scope


def append(path, scope, attempt, seconds):
    history = RunHistory(path)
    try:
        history.record(scope, RunStatistic(attempt_sha256=digest(attempt), source_sha256=digest("receipt:"+attempt),
            observed_at="2026-10-20T10:00:00Z", outcome="succeeded", duration_kind="complete",
            elapsed_seconds=seconds, condition_ref=None))
    finally:
        history.close()


def mean(context):
    return context["expectations"]["snapshots"][0]["data"]["statistics"][0]["mean_seconds"]


class CapturingController(FixtureController):
    def __init__(self, epoch, initial, stop_after, captures):
        super().__init__(epoch, initial, stop_after)
        self.captures = captures

    def observe(self, label, value, *, is_root):
        self.captures.append(deepcopy(value.as_record()))
        return super().observe(label, value, is_root=is_root)


def run(store, tools, provider, directory, factory, binding=None, resume=False):
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=directory,
        controller_factory=factory, project_credit=fixture_credit,
        execution_expectations=binding, resume=resume))


def test_child_estimator_receives_pinned_statistics_and_raw_changes_without_report_leak(tmp_path):
    path = tmp_path / "global.sqlite"
    scope = make_history(path)
    binding = ExecutionExpectations(path, by_grain={"improvement": [scope]})
    store, _ = setup(tmp_path)

    class UpdatingTools(FixtureTools):
        def execute(self, *args, **kwargs):
            result = super().execute(*args, **kwargs)
            # Another actual-execution receipt arrives after selection. The
            # current action retains what informed that selection, not this.
            append(path, scope, "second", 6)
            return result

    tools = UpdatingTools(store)
    fits = []

    def fixture_estimator(history, parameters, contexts):
        if not history:
            assert contexts == ()
            return YieldEstimate(0, NumericBand.exact(1), parameters, {})
        assert len(contexts) == len(history)
        context = contexts[-1]
        fits.append((tuple(history), deepcopy(context)))
        # Test-only finite script: band tests the controller's ordinary rule.
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) == 2 else 1), parameters,
                             {"fixture_mean_seen": mean(context)})

    def factory(path, initial):
        if len(path) == 1:
            return FixtureController(str(path), initial, 2)
        return YieldController(str(path), initial, 0, estimate_with_context=fixture_estimator)

    form = obj({"state": {"type": "string", "enum": ["unresolved", "supported"]},
                "scoped_credit": {"type": "number", "x-source": "credit"}})
    provider = ScriptedProvider([commission(form, {"state": "unresolved"}),
        tool(report={"state": "unresolved"}), reason(2, {"state": "supported"}), reason(0)])
    result = run(store, tools, provider, tmp_path / "run", factory, binding)
    assert [history for history, _ in fits] == [(0,), (0, 2)]
    assert [mean(context) for _, context in fits] == [2, 4]
    for _, context in fits:
        assert context["decision_time"]["state"] == "returned"
        assert context["selected_work_time"]["state"] == "returned"
        assert context["selected_work_time"]["live_interval_elapsed_seconds"] is None
    assert "execution_expectations" not in provider.contexts[0]
    assert "execution_expectations" not in provider.contexts[-1]
    assert provider.contexts[-1]["child_reports"] == [{"state": "supported", "scoped_credit": 2}]
    counts = [row[0] for row in store.db.execute("SELECT count(*) FROM runtime_observations GROUP BY episode_id")]
    assert sorted(counts) == [2, 2]  # two child actions, one child-return parent action
    # New runs preserve completion evidence for parent actions too, even when
    # only the child has an execution-duration binding.
    saved_contexts = store.db.execute(
        "SELECT episode_id,decision_index,data FROM runtime_estimation_contexts").fetchall()
    assert len(saved_contexts) == sum(counts)
    for saved in saved_contexts:
        context = json.loads(saved["data"])
        packet = context["current_completion_evidence"]
        observation = store.db.execute(
            "SELECT observation FROM runtime_observations WHERE episode_id=? AND unit_index=?",
            (saved["episode_id"], packet["unit_ref"]["unit_index"])).fetchone()
        assert observation is not None
        assert packet["unit_ref"] == json.loads(observation["observation"])["unit_ref"]
        assert packet["original_decision_index"] == saved["decision_index"]
    assert result["credit"] == 2 and tools.executions == 1


def test_interruption_replays_old_estimates_and_pending_context_then_reads_fresh_history(tmp_path):
    path = tmp_path / "global.sqlite"
    scope = make_history(path)
    binding = ExecutionExpectations(path, by_grain={"annotation": [scope]})
    store, tools = setup(tmp_path)
    captures = []

    def factory(path, initial):
        return CapturingController(str(path), initial, 3, captures)

    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([reason(1), KeyboardInterrupt()]), tmp_path / "run", factory, binding)
    old = store.db.execute("SELECT data FROM runtime_estimation_contexts").fetchone()[0]
    assert len(captures) == 1 and mean(captures[0]["estimation_context"]) == 2
    append(path, scope, "after-interruption", 100)
    captures.clear()
    provider = ScriptedProvider([reason(2), reason(3)])
    # The frozen binding is restored from the run. It is not replaced by a new
    # caller default when omitted during resume.
    result = run(store, tools, provider, None, factory, resume=True)
    assert [mean(row["estimation_context"]) for row in captures] == [2, 2, 51]
    assert [row["credit"] for row in captures] == [1, 3, 6]
    assert store.db.execute("SELECT data FROM runtime_estimation_contexts WHERE decision_index=0").fetchone()[0] == old
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
    assert store.db.execute("SELECT count(*) FROM synthetic_operations").fetchone()[0] == 3
    assert result["completed_actions"] == 3


def test_unavailable_history_and_failed_work_are_not_zero_samples_or_stops(tmp_path):
    reference_history = tmp_path / "reference.sqlite"
    scope = make_history(reference_history)
    missing = tmp_path / "missing.sqlite"
    binding = ExecutionExpectations(missing, by_grain={"annotation": [scope]})
    captures = []
    def factory(path, initial):
        return CapturingController(str(path), initial, 1, captures)
    store, tools = setup(tmp_path)
    result = run(store, tools, ScriptedProvider([tool("unavailable"), reason(1)]), tmp_path / "run", factory, binding)
    assert result["completed_actions"] == 1 and len(captures) == 1
    context = captures[0]["estimation_context"]
    assert context["expectations"]["status"] == "unavailable"
    assert context["expectations"]["snapshots"] == []
    assert store.db.execute("SELECT decision_index FROM runtime_estimation_contexts").fetchone()[0] == 1
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
    assert not missing.exists()


def test_parent_child_duration_is_recorded_after_return_without_extra_parent_turns(tmp_path):
    path = tmp_path / "global.sqlite"
    scope = make_history(path)
    binding = ExecutionExpectations(path, by_grain={"annotation": [scope], "improvement": [scope]})
    captures = {}
    def factory(path, initial):
        items = captures.setdefault(len(path), [])
        return CapturingController(str(path), initial, 1 if len(path) == 1 else 2, items)
    store, tools = setup(tmp_path)
    form = obj({"scoped_credit": {"type": "number", "x-source": "credit"}})
    result = run(store, tools, ScriptedProvider([commission(form, {}), reason(1), reason(0)]),
                 tmp_path / "run", factory, binding)
    assert len(captures[1]) == 1 and len(captures[2]) == 2
    parent_time = captures[1][0]["estimation_context"]["selected_work_time"]
    assert parent_time["state"] == "returned" and parent_time["live_interval_elapsed_seconds"] is None
    assert parent_time["includes_child_wait"] is True and parent_time["is_compute_consumption"] is False
    assert parent_time["measured_elapsed_seconds"] >= sum(
        row["estimation_context"]["selected_work_time"]["measured_elapsed_seconds"] for row in captures[2])
    assert result["completed_actions"] == 1 and result["credit"] == 1


def test_resume_rejects_replacing_caller_expectation_class_or_path(tmp_path):
    path = tmp_path / "global.sqlite"
    scope = make_history(path)
    binding = ExecutionExpectations(path, by_grain={"annotation": [scope]})
    store, tools = setup(tmp_path)
    def factory(path, initial):
        return FixtureController(str(path), initial, 1)
    run(store, tools, ScriptedProvider([reason(0)]), tmp_path / "run", factory, binding)
    changed = ExecutionExpectations(path, by_grain={"annotation": [replace(scope, cpu_threads=2)]})
    with pytest.raises(WorkflowError, match="execution expectation binding"):
        run(store, tools, ScriptedProvider([]), tmp_path / "run", factory, changed, resume=True)


def test_statistics_consumer_does_not_adopt_or_write_an_unrelated_database(tmp_path):
    scope = make_history(tmp_path / "reference.sqlite")
    wrong = tmp_path / "unrelated.sqlite"
    with sqlite3.connect(wrong) as db:
        db.execute("CREATE TABLE unrelated (value INTEGER)")
    before = wrong.read_bytes()
    binding = ExecutionExpectations(wrong, by_grain={"annotation": [scope]})
    result = binding.capture("annotation")
    assert result["status"] == "unavailable" and result["snapshots"] == []
    assert wrong.read_bytes() == before
