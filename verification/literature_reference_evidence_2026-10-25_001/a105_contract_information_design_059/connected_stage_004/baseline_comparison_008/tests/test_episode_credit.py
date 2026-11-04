"""Scoped native credit reads and caller binding fidelity; no model/network use."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.credit import CreditPolicy, project_credit
from gene_annotation_episode.runtime import Workflow, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import (FixtureController, FixtureStore, FixtureTools,
                          ScriptedProvider, fixture_credit, reason)


def interpreted_composition(store, tools, subject):
    """A scripted numeric fixture interpretation of actual local tool output."""
    result = tools.execute("sequence.inspect", {"subject_ref": subject})
    assert result["status"] == "completed"
    observation, = [store.get(ref) for ref in result["record_refs"]
                    if store.get(ref)["record_type"] == "observation"]
    hypothesis = store.put("hypothesis", {"subject_refs": [subject],
        "predicate": "molecule_type", "value": {"type": "enum", "value": "dna"},
        "context_refs": []}, origin="reasoning")
    assessment = store.put("assessment", {"hypothesis_ref": hypothesis["id"],
        "observation_ref": observation["id"], "relation": "strengthens", "applicability": "direct",
        "extent_basis": "observed_extent", "condition_refs": [], "assumption_refs": [],
        "expected_revision": 0}, origin="reasoning")
    annotation = store.put("annotation", {"subject_ref": subject,
        "footprint_kind": "whole_input_context", "coherent_sets": [{"interpretations": [{
            "hypothesis_ref": hypothesis["id"], "disposition": "supported",
            "assessment_refs": [assessment["id"]]}], "context_refs": []}],
        "alternative_refs": [], "resolution": "selected", "expected_revision": 0}, origin="reasoning")
    return observation, assessment, annotation


def test_selected_annotation_page_uses_run_frozen_nondefault_policy_and_one_observation(tmp_path):
    with Store(tmp_path / "store") as store:
        subject = store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"][0]
        tools = ToolRegistry(store)
        observation, assessment, annotation = interpreted_composition(store, tools, subject)
        policy = CreditPolicy(scale=231., epsilon=.4)
        expected = project_credit(store, policy=policy).credit
        assert expected > 0 and expected != project_credit(store).credit
        before = store.db.execute("SELECT count(*) FROM records").fetchone()[0]
        controllers = []
        def factory(path, initial):
            controller = FixtureController(str(path), initial, 1)
            controllers.append(controller)
            return controller
        def choose(context):
            assert context['current_credit'] == 0
            assert context['annotation_score'] == pytest.approx(expected)
            catalog = {item["name"]: item for item in context["tools"]}
            assert set(catalog['episode.annotation_score']['input_schema']['required']) == {'limit', 'offset'}
            return {"selection": {"kind": "tool", "tool": "episode.annotation_score",
                "arguments": {"limit": 1, "offset": 0}}, "report_update": {}}
        provider = ScriptedProvider([choose])
        summary = asyncio.run(run_workflow(store, tools, provider=provider,
            credit_policy=policy.as_record(), controller_factory=factory, run_dir=tmp_path / "run"))
        assert summary['completed_actions'] == 1 and summary['credit'] == 0
        assert summary['annotation_score'] == pytest.approx(expected)
        action = store.db.execute("SELECT result,credit FROM runtime_actions").fetchone()
        outcome = json.loads(action["result"])
        assert outcome["status"] == "completed" and outcome["changed_record_refs"] == []
        page = outcome["result"]
        assert page['policy'] == policy.as_record() and page['annotation_score'] == pytest.approx(expected)
        assert page["scope"] == {"subject_refs": [subject]}
        row, = page["source_contributions"]
        assert row["observation_ref"] == observation["id"]
        assert row["assessment_ref"] == assessment["id"] and row["annotation_ref"] == annotation["id"]
        assert row["contributing_segments"] == [{"target_ref": subject, "unit": "nt", "start": 0, "end": 8}]
        assert page["detail_pages"]["source_contributions"]["next_offset"] is None
        assert len(page["detail_pages"]["state_basis_sha256"]) == 64
        assert controllers[0].scores == [0]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == before


def test_credit_read_uses_owner_region_without_expanding_to_other_original_targets(tmp_path):
    with Store(tmp_path / "store") as store:
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps({"schema_version": 2, "entries": [
            {"sequence": "ACGTACGT", "molecule": "dna", "name": "one"},
            {"sequence": "GATTACAA", "molecule": "dna", "name": "two"}]}))
        one, two = store.create_problem(manifest_path=path)["subject_refs"]
        tools = ToolRegistry(store)
        interpreted_composition(store, tools, one)
        interpreted_composition(store, tools, two)
        policy = CreditPolicy(scale=317.)
        def bound(store, scope, **options):
            return project_credit(store, scope, policy, **options)
        bound.read_details = bound
        workflow = Workflow(store, tools, ScriptedProvider([]), tmp_path / "run", "scoped_fixture",
                            lambda *_: None, bound)
        scope = {"subject_refs": [one], "segments": [{"target_ref": one, "start": 2, "end": 6, "unit": "nt"}]}
        result = workflow.credit_read(SimpleNamespace(scope=scope), {"limit": 5, "offset": 0})
        assert result["status"] == "completed"
        page = result["result"]
        assert page["scope"] == scope and page["policy"] == policy.as_record()
        assert page["credit"] == pytest.approx(project_credit(store, scope, policy).credit)
        assert {row["target_ref"] for row in page["targets"]} == {one}
        assert all(row["contributing_segments"] == [{"target_ref": one, "unit": "nt", "start": 2, "end": 6}]
                   for row in page["source_contributions"])
        assert not store.db.execute("SELECT 1 FROM runtime_observations").fetchone()


def test_custom_projector_without_details_is_not_replaced_with_default_policy(tmp_path):
    store = FixtureStore(tmp_path / "fixture.sqlite3")
    provider = ScriptedProvider([reason(7)])
    summary = asyncio.run(run_workflow(store, FixtureTools(store), provider=provider,
        project_credit=fixture_credit, run_dir=tmp_path / "run",
        controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
    assert summary["credit"] == 7
    assert "episode.credit" not in {item["name"] for item in provider.contexts[0]["tools"]}


def test_native_current_credit_reads_do_not_materialize_scalar_operand_archives(tmp_path, monkeypatch):
    import gene_annotation_episode.credit as credit_module

    with Store(tmp_path / "store") as store:
        subject = store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"][0]
        tools = ToolRegistry(store)
        interpreted_composition(store, tools, subject)
        policy = CreditPolicy(scale=231., epsilon=.4)
        expected = project_credit(store, policy=policy).credit
        assert expected > 0
        def unbounded_scalar_details(*args, **kwargs):
            pytest.fail("native scalar/axes read materialized the unpaged scalar operand archive")
        monkeypatch.setattr(credit_module, "_scalar_full_shape", unbounded_scalar_details)
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "sequence.inspect",
            "arguments": {"subject_ref": subject}}, "report_update": {}}])
        summary = asyncio.run(run_workflow(store, tools, provider=provider,
            credit_policy=policy.as_record(), run_dir=tmp_path / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert summary['credit'] == 0 and summary['completed_actions'] == 1
        assert summary['annotation_score'] == pytest.approx(expected)
        assert provider.contexts[0]['current_credit'] == 0
        assert provider.contexts[0]['annotation_score'] == pytest.approx(expected)
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1


def test_detail_read_failure_returns_owner_feedback_without_completed_observation(tmp_path):
    with Store(tmp_path / "store") as store:
        subject = store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"][0]
        tools = ToolRegistry(store)
        def bound(store, scope):
            return project_credit(store, scope)
        def unavailable_details(*args, **kwargs):
            raise OSError("labelled local projection-read failure")
        bound.read_details = unavailable_details
        def after_failure(context):
            assert context["feedback"]["code"] == "credit_details_read_failed"
            assert context["feedback"]["exception_type"] == "OSError"
            assert context["last_local_outcome"]["status"] == "failed"
            assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
            return {"selection": {"kind": "tool", "tool": "sequence.inspect",
                "arguments": {"subject_ref": subject}}, "report_update": {}}
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "episode.credit",
            "arguments": {"limit": 1, "offset": 0}}, "report_update": {}}, after_failure])
        summary = asyncio.run(run_workflow(store, tools, provider=provider, project_credit=bound,
            run_dir=tmp_path / "run", controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert summary["completed_actions"] == 1
        actions = store.db.execute("SELECT result,credit FROM runtime_actions ORDER BY decision_index").fetchall()
        assert [json.loads(row["result"])["status"] for row in actions] == ["failed", "completed"]
        assert actions[0]["credit"] is None and len(provider.contexts) == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
