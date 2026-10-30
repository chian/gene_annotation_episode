"""Explicit synthetic score units test ownership, reports and replay, not biology.

The fixture's fixed turn counts are only an engineering controller seam. No
production scientific credit or continuation policy is selected by these tests.
"""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.runtime import WorkflowError
from test_runtime import (ScriptedProvider, commission, fixture_credit, obj, reason,
                          run, setup)


FORM = obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]},
            "local_credit": {"type": "number", "x-source": "credit"},
            "assessments": {"type": "array", "x-source": "changed_assessment_refs",
                "items": {"type": "string", "format": "reference",
                          "x-reference-namespace": "assessment"}}})
DEFINITIONS = {"scientific_child_credit": {"kind": "fixture_own_contributions", "scale": 10}}


def local_credit(store, scope, *, assignment, episode_id, run_id):
    assert scope == assignment["scope"] == {"subject_refs": ["subject_A"]}
    assert assignment["purpose"] == "Choose the next synthetic comparison"
    assert assignment["schema"] == FORM
    assert assignment["initial_report"] == {"interpretation": "unresolved"}
    refs = store.db.execute("SELECT DISTINCT refs.value FROM runtime_actions actions "
        "JOIN json_each(actions.result, '$.changed_record_refs') refs "
        "WHERE actions.run_id=? AND actions.episode_id=?", (run_id, episode_id))
    return {"credit": 10*sum(store.get(row[0]).get("fixture_value", 0) for row in refs)}


def local_details(store, scope, *, details_limit, details_offset, **assignment):
    return {**local_credit(store, scope, **assignment), "limit": details_limit, "offset": details_offset,
            "meaning": "fixture_local_details"}


def seed(store):
    store.add({"id": "inherited_assessment", "record_type": "assessment",
               "subject_refs": ["subject_A"], "fixture_value": 5})


def observations(store):
    return {json.loads(row["path"])[-1][0]: [json.loads(item[0])["step"]["delta"] for item in
            store.db.execute("SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index",
                             (row["episode_id"],))]
            for row in store.db.execute("SELECT path,episode_id FROM runtime_episodes")}


def test_scientific_local_credit_uses_original_commission_and_does_not_add_its_units_to_parent(tmp_path):
    store, tools = setup(tmp_path)
    seed(store)
    # Opt-in details are routed to this projector rather than a root default.
    def projector(*args, **kwargs):
        captured = deepcopy(kwargs["assignment"])
        result = local_credit(*args, **kwargs)
        kwargs["assignment"]["schema"].clear()
        assert captured["schema"] == FORM
        return result
    projector.read_details = local_details
    provider = ScriptedProvider([
        commission(FORM, {"interpretation": "unresolved"}),
        reason(1, {"interpretation": "supported"}),
        {"selection": {"kind": "tool", "tool": "episode.credit", "arguments": {"limit": 1, "offset": 0}},
         "report_update": {"interpretation": "supported"}},
        {"selection": {"kind": "tool", "tool": "episode.history", "arguments": {"view": "index"}},
         "report_update": {"interpretation": "supported"}},
        reason(1)])
    summary = run(store, tools, provider, tmp_path/"run", counts=(2, 3), project_child_credit=projector,
                  binding_definitions=DEFINITIONS)
    assert summary["credit"] == 7 and summary["completed_actions"] == 2
    assert [context["current_credit"] for context in provider.contexts] == [5, 0, 10, 10, 6]
    assert observations(store) == {"annotation": [1, 1], "improvement": [10, 0, 0]}
    parent = provider.contexts[-1]
    report, = parent["child_reports"]
    assert report["local_credit"] == 10 and report["interpretation"] == "supported"
    assert len(report["assessments"]) == 1
    assert "inherited_assessment" not in report["assessments"]
    for context in provider.contexts[1:3]:
        assert context["credit_binding"]["definition"] == DEFINITIONS["scientific_child_credit"]
        assert "episode.credit" in {tool["name"] for tool in context["tools"]}
    assert "episode.credit" not in {tool["name"] for tool in parent["tools"]}
    assert parent["credit_binding"]["projector"].endswith("fixture_credit")
    action = store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='episode.credit'").fetchone()
    assert json.loads(action[0])["result"] == {"credit": 10, "limit": 1, "offset": 0,
                                            "meaning": "fixture_local_details"}
    history = store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='episode.history'").fetchone()
    assert json.loads(history[0])["result"]["entries"][1]["tool"] == "episode.credit"
    assert store.db.execute("SELECT COUNT(*) FROM runtime_model_calls").fetchone()[0] == 5
    assert store.db.execute("SELECT COUNT(*) FROM runtime_forms").fetchone()[0] == 1


def test_scientific_local_replay_preserves_its_baseline_and_signed_actions(tmp_path):
    store, tools = setup(tmp_path)
    seed(store)
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([commission(FORM, {"interpretation": "unresolved"}),
            reason(1, {"interpretation": "supported"}), KeyboardInterrupt()]), tmp_path/"run",
            project_child_credit=local_credit, binding_definitions=DEFINITIONS)
    with pytest.raises(WorkflowError, match="same controller and credit bindings"):
        run(store, tools, ScriptedProvider([]), tmp_path/"run", resume=True)
    changed = deepcopy(DEFINITIONS)
    changed["scientific_child_credit"]["scale"] = 11
    with pytest.raises(WorkflowError, match="custom binding definitions"):
        run(store, tools, ScriptedProvider([]), tmp_path/"run", resume=True,
            project_child_credit=local_credit, binding_definitions=changed)
    provider = ScriptedProvider([reason(-.5, {"interpretation": "unresolved"}), reason(0)])
    result = run(store, tools, provider, tmp_path/"run", resume=True, project_child_credit=local_credit)
    assert result["credit"] == 5.5
    assert observations(store) == {"annotation": [.5, 0], "improvement": [10, -5]}
    assert provider.contexts[0]["current_credit"] == 10
    assert provider.contexts[0]["credit_binding"]["definition"] == DEFINITIONS["scientific_child_credit"]
    report, = provider.contexts[-1]["child_reports"]
    assert report["local_credit"] == 5 and report["interpretation"] == "unresolved"
    baseline = store.db.execute("SELECT initial_credit FROM runtime_episodes WHERE path LIKE '%improvement%'").fetchone()[0]
    assert baseline == 0
    frozen = store.db.execute("SELECT facts FROM runtime_forms").fetchone()[0]
    store.add({"id": "unrelated_later_assessment", "record_type": "assessment",
               "subject_refs": ["subject_A"], "fixture_value": 99})
    assert fixture_credit(store, {"subject_refs": ["subject_A"]}) == 104.5
    assert run(store, tools, ScriptedProvider([]), tmp_path/"run", resume=True,
               project_child_credit=local_credit) == result
    assert store.db.execute("SELECT facts FROM runtime_forms").fetchone()[0] == frozen


def test_local_definition_without_executable_is_not_a_scientific_policy(tmp_path):
    store, tools = setup(tmp_path)
    with pytest.raises(ValueError, match="binding_definition_requires_its_custom_executable"):
        run(store, tools, ScriptedProvider([]), tmp_path/"run", binding_definitions=DEFINITIONS)


def test_nested_scientific_children_use_their_own_commissions_and_parent_projection(tmp_path):
    store, tools = setup(tmp_path)
    seed(store)
    nested = commission(FORM, {"interpretation": "unresolved"})
    nested["report_update"] = {"interpretation": "unresolved"}
    provider = ScriptedProvider([commission(FORM, {"interpretation": "unresolved"}), nested,
        reason(1, {"interpretation": "supported"}), reason(0, {"interpretation": "supported"}),
        reason(-.5, {"interpretation": "unresolved"}), reason(0)])
    summary = run(store, tools, provider, tmp_path/"run", project_child_credit=local_credit,
                  binding_definitions=DEFINITIONS)
    assert summary["credit"] == 5.5 and summary["episode_count"] == 3
    outer = provider.contexts[-2]
    assert outer["current_credit"] == 10 and outer["child_reports"][0]["local_credit"] == 10
    assert provider.contexts[-1]["child_reports"][0]["local_credit"] == 5
    for row in store.db.execute("SELECT path,episode_id,initial_credit FROM runtime_episodes"):
        depth = len(json.loads(row["path"]))
        changes = [json.loads(item[0])["step"]["delta"] for item in store.db.execute(
            "SELECT observation FROM runtime_observations WHERE episode_id=? ORDER BY unit_index", (row["episode_id"],))]
        assert row["initial_credit"] == (5 if depth == 1 else 0)
        assert changes == {1: [.5, 0], 2: [10, -5], 3: [10, 0]}[depth]


def test_local_projector_without_details_does_not_expose_root_detail_reader(tmp_path):
    from gene_annotation_episode.runtime import Workflow
    store, tools = setup(tmp_path)
    def root(*args):
        return fixture_credit(*args)
    def forbidden(*args, **kwargs):
        raise AssertionError("Root details are not the child's score binding")
    root.read_details = forbidden
    workflow = Workflow(store, tools, ScriptedProvider([]), tmp_path/"run", "fixture-routing",
                        lambda *_: None, root, project_child_credit=local_credit)
    root_episode = workflow.build("annotation", "root", "Fixture root", {"subject_refs": ["subject_A"]})
    child = workflow.selected(root_episode.source, commission(FORM, {"interpretation": "unresolved"})["selection"], 0)
    source = child.child.source
    assert "episode.credit" not in {tool["name"] for tool in workflow.catalog(source.scope, source=source)}
    assert workflow.credit_read(source, {"limit": 1, "offset": 0})["feedback"]["code"] == "credit_details_not_declared"


def test_invalid_job_role_does_not_break_history_feedback(tmp_path):
    store, tools = setup(tmp_path)
    invalid = commission(FORM, {"interpretation": "unresolved"})
    invalid["selection"].update(kind="job_child", role="unknown_role", query_ref="subject_A")
    provider = ScriptedProvider([invalid, reason(0)])
    result = run(store, tools, provider, tmp_path/"run", counts=(1, 1))
    assert result["completed_actions"] == 1
    assert provider.contexts[-1]["feedback"]["category"] == "action_contract"
    entry, = provider.contexts[-1]["restored_episode_history"]["entries"]
    assert entry["kind"] == "job_child" and entry["status"] == "unexecuted"


def test_interruption_after_child_outcome_before_parent_projection_does_not_repeat_child(tmp_path, monkeypatch):
    from gene_annotation_episode.runtime import Workflow
    store, tools = setup(tmp_path)
    seed(store)
    original = Workflow.source_credit_view
    interrupted = []
    def crash_after_return(workflow, source):
        pending = store.db.execute("SELECT result FROM runtime_actions WHERE episode_id=? "
            "AND credit IS NULL AND result IS NOT NULL", (source.episode_id,)).fetchone()
        if len(source.path) == 1 and pending is not None and not interrupted:
            interrupted.append(json.loads(pending[0]))
            raise KeyboardInterrupt()
        return original(workflow, source)
    monkeypatch.setattr(Workflow, "source_credit_view", crash_after_return)
    provider = ScriptedProvider([commission(FORM, {"interpretation": "unresolved"}),
        reason(1, {"interpretation": "supported"}), reason(0, {"interpretation": "supported"})])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, provider, tmp_path/"run", counts=(1, 2),
            project_child_credit=local_credit, binding_definitions=DEFINITIONS)
    assert len(interrupted) == 1 and interrupted[0]["status"] == "completed"
    assert len(interrupted[0]["changed_record_refs"]) == 2
    child = store.db.execute("SELECT state FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()
    assert child[0] == "yielded"
    frozen_form = store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()
    resumed = ScriptedProvider([])
    result = run(store, tools, resumed, tmp_path/"run", counts=(1, 2), resume=True,
                 project_child_credit=local_credit)
    assert resumed.contexts == [] and result["completed_actions"] == 1 and result["credit"] == 6
    assert observations(store) == {"annotation": [1], "improvement": [10, 0]}
    assert tuple(store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()) == tuple(frozen_form)
