"""A106 can select the existing wait path; A105 and A108 do not expose it.

Synthetic decisions exercise the real runtime and saved wait/credit records.
They do not test autonomous action selection or manufacture scientific gain.
"""
import asyncio
from copy import deepcopy
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_reference_parent_prompt import state, render, split
from test_runtime import FixtureController, ScriptedProvider


@pytest.mark.parametrize("axis,can_wait", [("A106", True), ("A105", False), ("A108", False)])
def test_wait_action_and_estimate_catalog_follow_the_bound_axis(tmp_path, axis, can_wait):
    with Store(tmp_path / "state") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        factory = partial(LiteratureEpisodes, rate_population=True, reference_parent_sources=[],
            a106_intervention=axis == "A106", a108_context_evidence=axis == "A108")
        workflow = Workflow(store, ToolRegistry(store), ScriptedProvider([]), tmp_path / "workflow",
            "waiting-axis-fixture", lambda path, initial: FixtureController(str(path), initial, 1),
            lambda *_args, **_kwargs: 0, episode_binding_factories=(factory,),
            episode_record_receipts=True, initial_known_record_refs=[], annotation_child_roles=("literature",))
        # These are permission/catalog lookups, not an executed episode.
        root = SimpleNamespace(path=(("annotation", "root"),), scope=scope)
        assert workflow.permits_common_action(root, "wait") is can_wait
        names = {entry["name"] for entry in workflow.catalog(scope, source=root)}
        assert ("episode.estimate_wait" in names) is can_wait
        assert "source.read" not in names
        denied = asyncio.run(workflow.execute(root, "source.read", {}, decision_index=0,
            operation_key="unavailable-source-reader"))
        assert denied["status"] == "invalid"
        if not can_wait:
            denied = asyncio.run(workflow.execute(root, "episode.estimate_wait", {}, decision_index=0,
                operation_key="unavailable-wait-estimate"))
            assert denied["status"] == "invalid"
        binding = workflow.episode_bindings.for_role("literature")
        context = BindingContext(workflow.run_id, "child", "literature", (("literature", "child"),),
            scope, {}, {})
        assert ("wait" in binding.permitted_common_actions(context)) is can_wait


def test_a106_parent_executes_estimate_and_wait_without_new_credit(tmp_path):
    condition = {"version": "event_condition_v1", "events": [],
        "reconsider_at": "2026-01-01T00:00:00+00:00"}
    # A past wake time makes the existing event service immediately reconsider.
    # It is not a run timeout and never terminates a child or workflow.
    def wait(context):
        estimate = context["last_local_outcome"]["result"]
        assert context["last_local_outcome"]["status"] == "completed"
        assert estimate["scientific_gain"] is None
        assert "waiting_support" in context
        assert store.db.execute("SELECT count(*) FROM episode_waits").fetchone()[0] == 0
        return {"selection": {"kind": "wait", "condition": condition}, "report_update": {}}

    with Store(tmp_path / "state") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MKWAA", molecule="protein")["subject_refs"]}
        provider = ScriptedProvider([
            {"selection": {"kind": "tool", "tool": "episode.estimate_wait",
                "arguments": {"condition": condition}}, "report_update": {}}, wait])
        workflow = Workflow(store, ToolRegistry(store), provider, tmp_path / "workflow", "a106-wait-fixture",
            lambda path, initial: FixtureController(str(path), initial, 2), lambda *_args, **_kwargs: 0,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                a106_intervention=True, reference_parent_sources=[]),),
            episode_record_receipts=True, initial_known_record_refs=[], annotation_child_roles=("literature",))
        root = workflow.build("annotation", "root", "Investigate the assigned intervention evidence.", scope)
        asyncio.run(root.run_async(workflow.context))
        outcome, = store.db.execute("SELECT outcome FROM episode_waits").fetchall()
        assert json.loads(outcome[0])["wake_reason"] == "reconsideration"
        observations = [json.loads(row[0]) for row in store.db.execute("SELECT observation FROM runtime_observations")]
        assert len(observations) == 2
        assert [row["step"]["delta"] for row in observations] == [0, 0]
        assert store.db.execute("SELECT count(*) FROM runtime_forms").fetchone()[0] == 0


def test_parent_shows_waiting_operands_without_repeating_training_history():
    value = state()
    value["reference_evidence_parent"]["evidence_axis"] = "A106"
    value["pending_work"] = {"items": [{"handle": "execution_pending_child", "role": "literature",
        "lifecycle_state": "executing", "return_available": False}]}
    value["waiting_support"] = {"progress_records": [], "duration_expectations": [],
        "local_return_history_unavailable_reason": "No comparable completed work.",
        "own_completed_action_history": [{"unneeded": "PRIVATE_TRAINING_HISTORY"}],
        "local_return_history": {"unneeded": "PRIVATE_RETURN_HISTORY"}}
    before = deepcopy(value)
    _, steering = split(render(value))
    assert "execution_pending_child" in steering
    assert "episode.estimate_wait" in steering and "reconsider_at=null" in steering
    assert "No comparable completed work." in steering
    assert "PRIVATE_TRAINING_HISTORY" not in steering and "PRIVATE_RETURN_HISTORY" not in steering
    assert value == before
    value.pop("waiting_support")
    assert "Choosing work or waiting for a child" not in split(render(value))[1]
