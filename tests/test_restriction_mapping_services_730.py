"""Scientific consumer and receiver wiring; no new native or reader work.

Injected unavailable action rows exercise plumbing only. Retained positive
service checks use the original728 engineering host context, not a newly
selectable tool or complete nonempty scientific Workflow.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.restriction_mapping_returns import (
    restriction_mapping_fact_sources, requested_restriction_projections,
    project_restriction_action_return, validate_frozen_restriction_return,
)
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from test_scientific_process_episodes import mother, make_context, SCOPE, SUBJECT, SCHEMA
from test_scientific_process_runtime import Scenario, action, supplied_molecule_reasoning
from test_runtime import ScriptedProvider


SOURCE = "restriction_mapping_results"
SELECTOR = Path(__file__).resolve().parents[1] / "verification/tool_graders_restriction_registry_2026-10-29_728/SAVED_SELECTOR_001.json"
pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")


def requested(*, policy="all_own_completed_results", sequence=None, names=False, positions=False):
    fields = restriction_mapping_fact_sources()[SOURCE]["report_schema"]
    props = fields["items"]["properties"]
    keep = {"selection_policy", "sequence_ref", "namespace", "topology", "data_status",
        "coordinate_unit", "population_scope", "population"}
    if names:
        keep.add("enzyme_rows")
        row = props["enzyme_rows"]["items"]
        row_keep = {"catalog_ordinal", "name", "search_state", "position_meaning"}
        if positions:
            row_keep.update(("positions", "recognition_match_count", "native_search_positions_1based"))
        row["properties"] = {k:v for k,v in row["properties"].items() if k in row_keep}
        row["required"] = list(row["properties"])
    props = {k:v for k,v in props.items() if k in keep}
    props["selection_policy"] = {"type":"string", "const":policy}
    if policy == "matching_sequence":
        props["sequence_ref"]["const"] = sequence
    fields["items"]["properties"] = props
    fields["items"]["required"] = list(props)
    return obj({**SCHEMA["properties"], "selected": fields})


def unavailable_record(index):
    return {"decision_index":index, "operation_ref":"operation_"+str(index)*24,
        "tool_name":"find_restriction_sites", "work_mode":"native", "operation_status":"partial",
        "sequence_ref":SUBJECT, "namespace":"subject", "input_source_ref":"source_"+"1"*24,
        "source_ref":"source_"+str(index)*24, "native_artifact_ref":None,
        "mapping_artifact_ref":None, "mapping":None, "failure_code":"reader_unavailable"}


def forbidden(*args, **kwargs):
    raise AssertionError("No native/719/dispatch or live reconstruction during frozen validation")


def test_fact_source_registered_without_changing_existing_sources(mother):
    binding, services = mother
    sources = binding.fact_sources("scientific_process")
    assert set(sources) == {"scientific_process_results", "reference_site_rows", "blast_hsp_column_rows", SOURCE}
    assert sources[SOURCE] == restriction_mapping_fact_sources()[SOURCE]
    assert services.calls == []


@pytest.mark.parametrize("fault", ["selection", "meaning", "mandatory"])
def test_invocation_rejects_restriction_meaning_before_commission(fault):
    schema = requested()
    props = schema["properties"]["selected"]["items"]["properties"]
    if fault == "selection":
        props["selection_policy"].pop("const")
    elif fault == "meaning":
        props["coordinate_unit"]["const"] = "aa"
    else:
        props.pop("population_scope")
        schema["properties"]["selected"]["items"]["required"].remove("population_scope")
    with pytest.raises(ReportBoundaryError, match="selection|meaning|fields"):
        ScientificProcessEpisodes._invocation({"objective":"Read selected restriction evidence",
            "purpose":"Return original counts", "report_schema":schema,
            "initial_report":{"status":"unresolved","basis":[]}}, SCOPE)


def test_scientific_facts_page_only_requested_own_fields_and_preserve_unavailable(mother):
    binding, services = mother
    schema = requested()
    context = make_context(binding, schema=schema)
    calls = []
    def page(ctx, *, selection, after_decision_index, limit):
        assert ctx is context and selection == {"policy":"all_own_completed_results", "sequence_ref":None}
        calls.append((after_decision_index,limit))
        return {"records":[unavailable_record(1 if after_decision_index is None else 2)],
            "next_after_decision_index":1 if after_decision_index is None else None}
    services.restriction_mapping_own_action_results = page
    facts = binding.facts(context,{})
    assert calls == [(None,64),(1,64)]
    assert facts["scientific_process_results"] == []
    assert len(facts[SOURCE]) == 2
    assert all(r["data_status"] == "unavailable" and r["population"] is None for r in facts[SOURCE])
    assert all(set(r)==set(schema["properties"]["selected"]["items"]["properties"]) for r in facts[SOURCE])
    assert all("source_ref" not in r and "enzyme_rows" not in r for r in facts[SOURCE])
    facts[SOURCE][0]["sequence_ref"] = "detached"
    assert binding.facts(context,{})[SOURCE][0]["sequence_ref"] == SUBJECT


def test_unrequested_restriction_facts_do_not_read_actions(mother):
    binding, services = mother
    services.restriction_mapping_own_action_results = forbidden
    assert binding.facts(make_context(binding),{}) == {"scientific_process_results":[]}


@pytest.mark.parametrize("change", [None,"missing","changed","wrong_type"])
def test_semantic_report_uses_literal_frozen_restrictions_without_live_reads(mother, change):
    binding, services = mother
    schema = requested()
    context = make_context(binding, schema=schema)
    projection = requested_restriction_projections(schema)[SOURCE]
    original = [project_restriction_action_return(unavailable_record(1),projection["fields"])]
    services.restriction_mapping_own_action_results = forbidden
    frozen = {SOURCE:deepcopy(original)}
    services.restriction_mapping_frozen_facts = lambda ctx,*,sources: deepcopy(frozen)
    form = {"status":"qualified","basis":[],"selected":deepcopy(original)}
    if change == "missing":
        frozen.clear()
    elif change == "changed":
        form["selected"][0]["data_status"] = "complete"
    elif change == "wrong_type":
        frozen[SOURCE] = None
    if change is None:
        binding.validate_report(context,form,schema)
    else:
        with pytest.raises(ReportBoundaryError):
            binding.validate_report(context,form,schema)


def test_direct_and_registry_reference_ports_keep_tristate_and_authoritative_false(mother):
    binding, services = mother
    context = make_context(binding)
    calls = []
    def reference(ctx,value,namespace):
        calls.append((ctx.role,value,namespace))
        return value == "EcoRI"
    services.restriction_mapping_reference = reference
    assert binding.resolve(context,"EcoRI","restriction_enzyme") is True
    assert binding.resolve(context,"BcgI","restriction_enzyme") is False
    registry = EpisodeBindingRegistry([binding])
    assert registry.resolve_received_reference(context,"EcoRI","restriction_enzyme") is True
    assert registry.resolve_received_reference(context,"BcgI","restriction_enzyme") is False
    assert registry.resolve_received_reference(context,SUBJECT,"subject") is None
    assert len(calls) == 4


@pytest.fixture(scope="module")
def retained_services():
    selector = json.loads(SELECTOR.read_bytes())
    with Store(selector["store_path"]) as store:
        service = WorkflowServices(SimpleNamespace(store=store,run_id=selector["run_id"]))
        context = BindingContext(selector["run_id"],selector["episode_id"],"scientific_process",
            tuple(tuple(p) for p in selector["path"]),selector["scope"],{},selector["request"])
        yield store,service,context,selector


def test_actual_service_reads_original_owned_saved_record_without_dispatch(retained_services, monkeypatch):
    store, service, context, selector = retained_services
    from gene_annotation_episode.restriction_mapping_jobs import RestrictionMappingJobs
    monkeypatch.setattr(RestrictionMappingJobs,"run_async",forbidden)
    before = store.db.total_changes
    selection = requested_restriction_projections(plain(context.request)["report_contract"]["measurements"]["schema"])[SOURCE]["selection"]
    page = service.restriction_mapping_own_action_results(context,selection=selection,
        after_decision_index=None,limit=64)
    record, = page["records"]
    assert record["source_ref"] == selector["source_ref"]
    row, = record["mapping"]["enzyme_rows"]
    assert row["native_search_positions_1based"] == [6]
    assert row["recognition_match_count"] == 1
    assert row["positions"][0]["watson_boundary_0based"] == 5
    assert row["positions"][0]["crick_boundary_0based"] == 9
    assert service.restriction_mapping_reference(context,"EcoRI","restriction_enzyme") is True
    assert store.db.total_changes == before


def test_actual_namespace_port_ignores_unrelated_references(retained_services):
    store,service,context,_ = retained_services
    before=store.db.total_changes
    assert service.restriction_mapping_reference(context,"EcoRI","source") is None
    assert store.db.total_changes==before


def test_actual_composed_empty_source_closes_through_requested_parent_form(tmp_path):
    with Store(tmp_path/"store") as store:
        case=Scenario(tmp_path,store)
        commission=case.commission()
        original=json.loads(commission["selection"]["schema_json"])
        fields=requested()["properties"]["selected"]
        original["properties"]["restriction_evidence"]=fields
        original["required"].append("restriction_evidence")
        commission["selection"]["schema_json"]=json.dumps(original)
        received=[]
        def parent(context):
            received.extend(context["child_reports"])
            assert received[0]["restriction_evidence"] == []
            return supplied_molecule_reasoning(store,case.scope)
        provider=ScriptedProvider([commission, action("fixture.inspect",{"value":2},"unresolved"),
            action("process.entry",{"option_id":"P01"},"qualified"),
            action("process.entry",{"option_id":"P77"},"qualified"),
            action("episode.history",{"view":"index"},"qualified"),parent])
        workflow=case.workflow(provider)
        root=workflow.build("annotation","root","Return the requested restriction facts",case.scope)
        record=asyncio.run(root.run_async(workflow.context))
        asyncio.run(root.build_result(record))
        child=store.db.execute("SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=2").fetchone()[0]
        frozen=json.loads(store.db.execute("SELECT facts FROM runtime_forms WHERE episode_id=?",(child,)).fetchone()[0])
        assert frozen[SOURCE]==[] and len(received)==1
        assert len(case.tools.calls)==1 and case.tools.calls[0][0]=="fixture.inspect"
        assert "find_restriction_sites" not in {r["name"] for r in case.tools.catalog()}


def prepared_requested_child(case, workflow, schema):
    root=workflow.build("annotation","root","Inspect requested restriction records",case.scope)
    selected=case.commission()["selection"]
    selected["schema_json"]=json.dumps(schema)
    selected["initial_report_json"]='{"status":"unresolved","basis":[]}'
    unit=workflow.selected(root.source,selected,0)
    return root,unit.child


@pytest.mark.parametrize("policy",["all_own_completed_results","matching_sequence"])
@pytest.mark.parametrize("mode",[None,"native","saved"])
def test_no_operations_table_preserves_empty_work_and_rejects_missing_authority(tmp_path,policy,mode):
    with Store(tmp_path/"store") as store:
        case=Scenario(tmp_path,store)
        workflow=case.workflow(ScriptedProvider([]))
        schema=requested(policy=policy,sequence=case.scope["subject_refs"][0])
        _,child=prepared_requested_child(case,workflow,schema)
        context=workflow.binding_context(child.source)
        selection=requested_restriction_projections(schema)[SOURCE]["selection"]
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='tool_operations'").fetchone() is None
        if mode is not None:
            # Missing original authority is an engineering failure, not a
            # fabricated operation or unavailable scientific measurement.
            args={"mode":mode,"sequence_ref":case.scope["subject_refs"][0]} if mode=="native" else {"mode":mode,"result_source_ref":"missing"}
            workflow.journal.save("runtime_actions",{"episode_id":context.episode_id,"decision_index":0,
                "action":json.dumps({"kind":"tool","tool":"find_restriction_sites","arguments":args}),
                "result":'{"status":"partial"}',"credit":None})
            with pytest.raises(ValueError,match="restriction_mapping_return_completed_operation_missing"):
                workflow.services.restriction_mapping_own_action_results(context,selection=selection,
                    after_decision_index=None,limit=64)
            with pytest.raises(ValueError,match="restriction_mapping_reference_own_authority_invalid") as error:
                workflow.services.restriction_mapping_reference(context,"EcoRI","restriction_enzyme")
            assert str(error.value.__cause__)=="restriction_mapping_return_completed_operation_missing"
        else:
            assert workflow.services.restriction_mapping_own_action_results(context,selection=selection,
                after_decision_index=None,limit=64)=={"records":[],"next_after_decision_index":None}
            assert workflow.services.restriction_mapping_reference(context,"EcoRI","restriction_enzyme") is False


def test_actual_workflow_and_service_false_prevent_store_fallback(tmp_path,monkeypatch):
    with Store(tmp_path/"store") as store:
        case=Scenario(tmp_path,store)
        workflow=case.workflow(ScriptedProvider([]))
        root=workflow.build("annotation","root","Validate known restriction names",case.scope)
        context=workflow.binding_context(root.source)
        monkeypatch.setattr(store,"reference_subset",forbidden)
        monkeypatch.setattr(workflow.services,"reference_in_scope",forbidden)
        assert workflow.resolver(case.scope,context=context)("EcoRI","restriction_enzyme") is False
        assert workflow.services.reference_in_context(context,"EcoRI","restriction_enzyme") is False


def test_actual_receiver_ports_admit_only_requested_frozen_name_and_record_no_credit(tmp_path,monkeypatch):
    """Engineering host-frozen name row; no native data/counts/coordinates.

    Real Workflow, child preparation, TypedReportContract, original commission,
    report attempt and receipt admission are used. This is not a nonempty
    scientific-operation execution or configured-model verification.
    """
    from gene_annotation_episode.runtime import TypedReportContract
    with Store(tmp_path/"store") as store:
        case=Scenario(tmp_path,store)
        workflow=case.workflow(ScriptedProvider([]))
        schema=requested(names=True)
        root,child=prepared_requested_child(case,workflow,schema)
        context=workflow.binding_context(child.source)
        group={"selection_policy":"all_own_completed_results",
            "sequence_ref":case.scope["subject_refs"][0],"namespace":"subject",
            "topology":None,"data_status":"unavailable","coordinate_unit":"nt",
            "population_scope":"full_selected_native_enzyme_population","population":None,
            "enzyme_rows":[{"catalog_ordinal":0,"name":"EcoRI","search_state":"not_started",
                "position_meaning":"unknown"}]}
        form={"status":"qualified","basis":[],"selected":[group]}
        facts={SOURCE:[deepcopy(group)],"interpretations":{"status":"qualified","basis":[]}}
        workflow.journal.save("runtime_forms",{"episode_id":child.source.episode_id,
            "facts":json.dumps(facts),"form":json.dumps(form)})
        contract=TypedReportContract(child.request.report_contract.decision,schema,
            workflow.resolver(case.scope,context=context),
            lambda value:workflow.validate_report(value,case.scope,schema=schema,context=context))
        admitted=contract.admit(form,audit_identifiers=(child.source.episode_id,child.request.goal.goal_id)).as_record()
        root_context=workflow.binding_context(root.source)
        root_resolve=workflow.resolver(case.scope,context=root_context)
        assert root_resolve("EcoRI","restriction_enzyme") is False
        workflow.save_attempt(root.source.episode_id,0,"delivery_engineering730",child.source.episode_id,
            contract,form=admitted)
        refs=workflow.receive_form(root.source,admitted,schema,0)
        assert refs==case.scope["subject_refs"]
        before=store.db.total_changes
        monkeypatch.setattr(store,"reference_subset",forbidden)
        monkeypatch.setattr(workflow.services,"reference_in_scope",forbidden)
        assert root_resolve("EcoRI","restriction_enzyme") is True
        assert root_resolve("ecori","restriction_enzyme") is False
        assert root_resolve("BcgI","restriction_enzyme") is False
        assert workflow.services.reference_in_context(root_context,"EcoRI","restriction_enzyme") is True
        assert workflow.services.reference_in_context(root_context,"BcgI","restriction_enzyme") is False
        assert store.db.total_changes==before
        assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0]==0
        assert store.db.execute("SELECT COUNT(*) FROM runtime_actions WHERE credit IS NOT NULL").fetchone()[0]==0
        monkeypatch.undo()
        # Choose a new receiving field name over the same original frozen
        # requested rows. Record the engineering selection, not a completed
        # action or a new scientific observation.
        schema2=deepcopy(schema)
        schema2["properties"]["redelivered"]=schema2["properties"].pop("selected")
        schema2["required"]=["redelivered" if k=="selected" else k for k in schema2["required"]]
        selection={"kind":"redeliver_report","delivery_ref":"delivery_engineering730",
            "purpose":"Read the same requested frozen names","schema_json":json.dumps(schema2)}
        workflow.journal.save("runtime_model_calls",{"episode_id":root.source.episode_id,"call_index":1,
            "purpose":"decision","request":"{}","response":json.dumps({"selection":selection})})
        original=store.db.execute("SELECT facts,form FROM runtime_forms WHERE episode_id=?",
            (child.source.episode_id,)).fetchone()
        delivered=workflow.selected(root.source,selection,1)
        assert delivered.report.as_record()["redelivered"]==[group]
        from gene_annotation_episode.restriction_mapping_references import RestrictionMappingReferences
        assert RestrictionMappingReferences(store,workflow.run_id)._attempt(root_context,1)=={"EcoRI"}
        assert tuple(store.db.execute("SELECT facts,form FROM runtime_forms WHERE episode_id=?",
            (child.source.episode_id,)).fetchone())==tuple(original)
        assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0]==0
        assert store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0]==1

