"""Scripted native tool/form accounting; no live model or scientific result."""
import asyncio
import json

from gene_annotation_episode.runtime import run_workflow
from test_native_read_mapping import fixture
from test_runtime import FixtureController, ScriptedProvider


def response(selection, report=None):
    return {"selection": selection, "report_update": report or {}}


def test_native_preview_complete_child_facts_and_selected_parent_reuse_share_one_journal(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path, copies=32)
    with store:
        schema={"type":"object","additionalProperties":False,
            "required":["meaning","committed","last"],"properties":{
                "meaning":{"type":"string","enum":["uninterpreted"]},
                "committed":{"type":"array","items":{"type":"string","format":"reference"},"x-source":"committed_record_refs"},
                "last":{"type":"array","items":{"type":"string","format":"reference"},"x-source":"last_outcome_refs"}}}
        selected_ref={}
        def parent_reuses(context):
            report,=context["child_reports"]
            own=store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='reads.map' ORDER BY decision_index").fetchall()
            durable=[json.loads(row[0]) for row in own]
            expected=list(dict.fromkeys(ref for outcome in durable for ref in outcome["record_refs"]))
            assert report["committed"] == expected
            assert report["last"] == durable[-1]["record_refs"]
            assert len(report["last"]) > 32 and len(report["committed"]) > len(report["last"])
            observations=[ref for ref in report["last"] if store.get(ref).get("kind") == "alignment"]
            selected_ref["id"]=observations[-1]
            return response({"kind":"tool","tool":"state.query","arguments":{"refs":[selected_ref["id"]]}})
        provider=ScriptedProvider([
            response({"kind":"child","goal":"Iteratively compare the same synthetic read selection under explicitly chosen genomic models; return native facts without biological interpretation",
                "scope":selected["scope"],"purpose":"Decide which exact native placement to inspect next",
                "schema_json":json.dumps(schema),"initial_report_json":json.dumps({"meaning":"uninterpreted"})}),
            response({"kind":"tool","tool":"reads.map","arguments":args},{"meaning":"uninterpreted"}),
            response({"kind":"tool","tool":"reads.map","arguments":{**args,"preset":"map-pb"}},{"meaning":"uninterpreted"}),
            parent_reuses])
        factory=lambda path,initial:FixtureController(str(path),initial,2)
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"run",
            controller_factory=factory,restoration_settings={"preview_size":2},
            goal="Synthetic form/accounting fixture, not biological annotation"))
        context=provider.contexts[2]
        preview=context["last_local_outcome"]
        assert preview["automatic_preview"]["record_refs"] == {"total":34,"included":2,"truncated":True}
        assert preview["automatic_preview"]["rows"] == {"total":32,"included":2,"truncated":True}
        assert len(preview["record_refs"]) == len(preview["result"]["records"]) == 2
        assert preview["result"]["record_refs_are_preview"]
        # Every visible basis ID is reconstructible from actually presented
        # state/outcome. Hidden full durable IDs are not injected into basis.
        from gene_annotation_episode.runtime import _references_in
        expected=_references_in({"working_state":context["working_state"],
            "last_local_outcome":preview,"visual_evidence":context["visual_evidence"]},store.get,
            forms=[(context["current_report_update"],{"type":"object","properties":{"meaning":{"type":"string","enum":["uninterpreted"]}}})],
            reference_subset=lambda refs:store.reference_subset(refs,selected["scope"]))
        assert set(context["visible_record_refs"]) == set(expected)
        raw=store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='reads.map' ORDER BY decision_index LIMIT 1").fetchone()[0]
        assert len(json.loads(raw)["record_refs"]) == 34 and not json.loads(raw)["result"]["record_refs_are_preview"]
        last=store.db.execute("SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='state.query'").fetchone()[0]
        assert json.loads(last)["result"]["records"][0]["id"] == selected_ref["id"]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
        assert summary["completed_actions"] == 2  # child one parent action + selected read
        assert not store.current_annotations() and summary["credit"] == 0
        assert all(json.loads(row[0])["step"]["delta"] == 0 for row in store.db.execute("SELECT observation FROM runtime_observations"))


def test_preview_does_not_recursively_edit_child_forms_or_exact_history_contract(tmp_path):
    from gene_annotation_episode.runtime import Workflow
    workflow=Workflow.__new__(Workflow);workflow.restoration_settings={"preview_size":0}
    native={"status":"completed","record_refs":["one","two"],
        "published_batch":{"representation":"native_publications_v1","published_rows_total":1,
            "failure_rows_total":None,"observation_query":None},"result":{
        "native_result_type":"minimap2_placements_v1","reported_placement_count":1,
        "records":[{"observation_ref":"two"}],"record_refs_are_preview":False,"all_observations_query":{"offset":0}}}
    shown=workflow.local_outcome_preview(native)
    assert shown["record_refs"] == [] and shown["result"]["records"] == []
    assert native["record_refs"] == ["one","two"] and not native["result"]["record_refs_are_preview"]
    history={"status":"completed","record_refs":[],"result":{"records":[{"outcome":native}]}}
    assert workflow.local_outcome_preview(history) is history
    form={"child_reports":[{"actual_refs":["one","two"]}]}
    assert workflow.local_outcome_preview(form) is form


def test_native_failure_feedback_keeps_failed_attempt_out_of_controller_observations(tmp_path):
    from test_read_mapping_failures import setup_synthetic_process_case
    store,tools,args=setup_synthetic_process_case(tmp_path,"failure")
    with store:
        def follow_failure(context):
            assert context["feedback"]["code"] == "native_mapping_error"
            assert context["last_local_outcome"]["status"] == "failed"
            assert context["controller"]["scores"] == []
            source=context["last_local_outcome"]["result"]["source_ref"]
            return response({"kind":"tool","tool":"state.query","arguments":{"refs":[source]}})
        provider=ScriptedProvider([response({"kind":"tool","tool":"reads.map","arguments":args}),follow_failure])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"failed-run",
            controller_factory=lambda path,initial:FixtureController(str(path),initial,1),
            goal="Synthetic native failure accounting fixture"))
        actions=store.db.execute("SELECT result,credit FROM runtime_actions ORDER BY decision_index").fetchall()
        assert len(actions)==2 and json.loads(actions[0][0])["status"] == "failed" and actions[0][1] is None
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        assert summary["completed_actions"] == 1 and summary["credit"] == 0


def test_restored_native_child_form_facts_retain_complete_saved_references(tmp_path,monkeypatch):
    import pytest
    from gene_annotation_episode import read_mapping
    store,tools,target,selected,args=fixture(tmp_path,copies=4)
    with store:
        schema={"type":"object","additionalProperties":False,"required":["meaning","last"],"properties":{
            "meaning":{"type":"string","enum":["uninterpreted"]},
            "last":{"type":"array","items":{"type":"string","format":"reference"},"x-source":"last_outcome_refs"}}}
        child=response({"kind":"child","goal":"Iteratively inspect native synthetic read placements",
            "scope":selected["scope"],"purpose":"Select a saved native placement for inspection",
            "schema_json":json.dumps(schema),"initial_report_json":json.dumps({"meaning":"uninterpreted"})})
        native=response({"kind":"tool","tool":"reads.map","arguments":args},{"meaning":"uninterpreted"})
        provider=ScriptedProvider([child,native,KeyboardInterrupt()])
        factory=lambda path,initial:FixtureController(str(path),initial,2)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"restore-run",
                controller_factory=factory,restoration_settings={"preview_size":1}))
        first=store.db.execute("SELECT result FROM runtime_actions WHERE result IS NOT NULL AND json_extract(action,'$.tool')='reads.map'").fetchone()[0]
        first=json.loads(first)
        assert len(first["record_refs"]) == 6
        calls=[];original=read_mapping.run_mapping
        async def counted(*a,**k):
            calls.append(1)
            return await original(*a,**k)
        monkeypatch.setattr(read_mapping,"run_mapping",counted)
        def parent(context):
            form,=context["child_reports"]
            last=store.db.execute("SELECT result FROM runtime_actions WHERE result IS NOT NULL AND json_extract(action,'$.tool')='reads.map' ORDER BY decision_index DESC LIMIT 1").fetchone()[0]
            assert form["last"] == json.loads(last)["record_refs"] and len(form["last"]) == 6
            return response({"kind":"tool","tool":"state.query","arguments":{"refs":[form["last"][2]]}})
        resumed=ScriptedProvider([response({"kind":"tool","tool":"reads.map","arguments":{**args,"preset":"map-pb"}},
            {"meaning":"uninterpreted"}),parent])
        summary=asyncio.run(run_workflow(store,tools,provider=resumed,resume=True,controller_factory=factory))
        preview=resumed.contexts[0]["last_local_outcome"]
        assert preview["automatic_preview"]["record_refs"] == {"total":6,"included":1,"truncated":True}
        assert calls == [1]  # Only the newly selected native operation executes.
        assert summary["completed_actions"] == 2
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
