"""Ordinary episode model supplement and synthetic typed parent delivery."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, EXPERIMENTAL_TASK
from gene_annotation_episode.literature_binding_interaction_model_storage import COMPONENTS, binding_interaction_model_cells_schema
from gene_annotation_episode.literature_binding_interaction_model_prompt import BINDING_INTERACTION_MODEL_TASK
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_binding_interaction_model_inputs import setup_model
from test_literature_binding_interaction_model_storage import populate
from test_runtime import FixtureController, ScriptedProvider


def binding_for(store, context):
    host=SimpleNamespace(store=store,run_id=context.run_id,tools=ToolRegistry(store))
    binding=LiteratureEpisodes(WorkflowServices(host),rate_population=True)
    host.episode_bindings=EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize("status",["known","estimated"])
def test_selected_child_original_parent_subset_and_one_observation_per_action(tmp_path,status):
    store,context,args,model_args,_,_=setup_model(tmp_path/"state",status=status)
    controllers,received=[],[]
    selected=["log_interaction_standard_uncertainty","signed_index"]
    form=obj({"interaction_precision":binding_interaction_model_cells_schema()})
    try:
        assignment={**plain(context.assignment),"requested_binding_interaction_model_components":selected}
        commission={"selection":{"kind":"episode_child","role":"literature","assignment":assignment,
            "goal":"Evaluate the supplied synthetic binding discrimination interaction using its explicit retained log model.",
            "scope":plain(context.scope),"purpose":"Return requested precision and conditional interaction index.",
            "schema_json":json.dumps(form),"initial_report_json":"{}"},"report_update":{}}
        native={"selection":{"kind":"tool","tool":"literature.binding.interaction.populate","arguments":args},"report_update":{}}
        def model_action(inputs):
            prior=inputs["last_local_outcome"]
            assert prior["status"]=="completed"
            return {"selection":{"kind":"tool","tool":"literature.binding.interaction.model.populate",
                "arguments":{**model_args,"source_ref":prior["result"]["sheet_ref"]}},"report_update":{}}
        def receive(inputs):
            report,=inputs["child_reports"];received.append(report)
            rows=report["interaction_precision"]
            assert [r["component"] for r in rows]==selected
            assert rows[0]["value"]==pytest.approx(.4)
            assert rows[1]["value"]==(pytest.approx(.9950826091535326) if status=="known" else None)
            assert rows[1]["unavailable_reason"]==(None if status=="known" else "covariance_estimated_not_known")
            assert all(r["variance_status"]==status and r["source_kind"]=="synthetic_fixture" for r in rows)
            assert all(r["values"]["delivery_status"]=="not_requested" for r in rows[0]["roles"].values())
            paper=store.get(args["source_ref"]);raw=store.get_artifact(paper["artifact_ref"])
            commit={name:[] for name in store.reasoning_schema()["required"]}
            commit["source_subjects"]=[{"alias":"synthetic_source","reference_type":"assay","source_ref":paper["id"],
                "label":"formA","anchor":{"source_ref":paper["id"],"artifact_ref":paper["artifact_ref"],"start":0,"end":len(raw),"quote":raw.decode()}}]
            return {"selection":{"kind":"reason","commit":commit},"report_update":{}}
        def controller(path,initial):
            value=FixtureController(str(path),initial,2);controllers.append(value);return value
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=ScriptedProvider([commission,native,model_action,receive]),
            run_dir=tmp_path/"run",controller_factory=controller,project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True),),binding_definitions={"credit":scorer.as_record()}))
        assert len(received)==1 and summary["credit"]==0
        assert [v.scores for v in controllers]==[[0,0],[0,0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]==4
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_operations").fetchone()[0]==1
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_model_operations").fetchone()[0]==1
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_model_received").fetchone()[0]==1
    finally:store.close()


def test_catalog_dispatch_exact_return_request_and_page_ancestry(tmp_path):
    store,context,args,model_args,_,_=setup_model(tmp_path)
    with store:
        binding=binding_for(store,context)
        assert "literature.binding.interaction.model.populate" in {r["name"] for r in binding.catalog(context)}
        native=asyncio.run(binding.execute(context,"literature.binding.interaction.populate",args,"native"))
        owner=replace(context,received_record_refs=(*context.received_record_refs,*native["record_refs"]),
            assignment={**context.assignment,"requested_binding_interaction_model_components":["signed_index"]})
        model_args["source_ref"]=native["result"]["sheet_ref"]
        modeled=asyncio.run(binding.execute(owner,"literature.binding.interaction.model.populate",model_args,"model"))
        assert modeled["status"]=="completed",modeled
        owner=replace(owner,received_record_refs=(*owner.received_record_refs,*modeled["record_refs"]))
        form=obj({"selected":binding_interaction_model_cells_schema()})
        returned=form_with_facts({},form,binding.facts(owner,{"committed_record_refs":[modeled["result"]["sheet_ref"]]}))
        assert [r["component"] for r in returned["selected"]]==["signed_index"]
        binding.validate_report(owner,returned,form)
        forged=deepcopy(returned);forged["selected"][0]["value"]=.8
        with pytest.raises(Exception,match="differs_from_saved"):binding.validate_report(owner,forged,form)
        other=store.put("source",{"provider":"synthetic_unrelated","accession":None,"uri":None,
            "artifact_ref":store.artifact("unrelated","text/plain"),"text_ref":None,"request_ref":None,"version":None,"retrieved_at":None},origin="caller")
        page={"version":"page_assignment_v1","source_ref":other["id"],"representation":"original","artifact_ref":other["artifact_ref"],"question_context_refs":[],"prior_delivery_refs":[]}
        wrong=replace(owner,role="literature_page",path=(("literature_page","wrong"),),assignment=page,received_record_refs=(*owner.received_record_refs,other["id"]))
        failure=asyncio.run(binding.execute(wrong,"literature.binding.interaction.model.populate",model_args,"wrong-page"))
        assert failure["status"]=="invalid" and failure["feedback"]["code"]=="literature_reading_outside_assigned_source"


@pytest.mark.parametrize("foreign",["model","witness"])
def test_model_and_support_each_require_page_ancestry(tmp_path,foreign):
    store,context,args,model_args,_,_=setup_model(tmp_path)
    with store:
        binding=binding_for(store,context)
        native=asyncio.run(binding.execute(context,"literature.binding.interaction.populate",args,"native"))
        root=store.get(args["source_ref"])
        page={"version":"page_assignment_v1","source_ref":root["id"],"representation":"original","artifact_ref":root["artifact_ref"],"question_context_refs":[],"prior_delivery_refs":[]}
        owner=replace(context,role="literature_page",path=(("literature_page","root"),),assignment=page,received_record_refs=(*context.received_record_refs,*native["record_refs"]))
        model_args["source_ref"]=native["result"]["sheet_ref"]
        original=store.get(model_args["model_source_ref"] if foreign=="model" else model_args["model_witnesses"][0]["source_ref"])
        value={k:v for k,v in original.items() if k not in ("id","record_type","origin")};value.update(provider="synthetic_outside_page",parent_source_refs=[])
        external=store.put("source",value,origin="caller")["id"]
        if foreign=="model":model_args["model_source_ref"]=external
        else:model_args["model_witnesses"][0]["source_ref"]=external
        owner=replace(owner,received_record_refs=(*owner.received_record_refs,external))
        failed=asyncio.run(binding.execute(owner,"literature.binding.interaction.model.populate",model_args,"foreign-page"))
        assert failed["status"]=="invalid" and failed["feedback"]["code"]=="literature_reading_outside_assigned_source"


@pytest.mark.parametrize("parent",[False,True])
def test_full_task_once_and_own_parent_lookup_mask_raw_numbers_and_aliases(tmp_path,parent):
    from test_literature_experimental_prompt_delivery import snapshot
    store,context,args,model_args,_,_=setup_model(tmp_path)
    with store:
        context=replace(context,assignment={**context.assignment,"requested_binding_interaction_model_components":["signed_index"]})
        repo,owner,_,outcome,_=populate(store,context,args,model_args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=["signed_index"])
        records={ref:store.get(ref) for ref in outcome["record_refs"] if ref.startswith("reference_")}
        support=store.get(rows[0]["model_support_refs"][0])
        value={k:v for k,v in support.items() if k not in ("id","record_type","origin")}
        value.update(accession="synthetic_support_alias",label="PRIVATE_COVARIANCE_ALIAS_0.04")
        alias=store.put("reference",value,origin="tool",scope=plain(context.scope));records[alias["id"]]=alias
        model=store.get(model_args["model_source_ref"]);raw=store.get_artifact(model["artifact_ref"])
        value.update(source_ref=model["id"],accession="synthetic_model_alias",label="PRIVATE_MODEL_BYTES_ALIAS_0.04",
            anchor={"source_ref":model["id"],"artifact_ref":model["artifact_ref"],"start":0,"end":len(raw),"quote":raw.decode()})
        model_alias=store.put("reference",value,origin="tool",scope=plain(context.scope));records[model_alias["id"]]=model_alias
        state=snapshot();state["literature_assignment"]=plain(context.assignment)
        state["literature_assignment"]["question_context_refs"]=[alias["id"],model_alias["id"]]
        state["literature_received_fact_display"]={"records":records,"received_refs":list(records)}
        if parent:
            state["literature_experimental_work"]["aspect"]="reference_evidence_parent"
            state["reference_evidence_parent"]={"version":"reference_evidence_parent_v1","source_refs":list(context.received_record_refs),"source_custody":[],"child_population_operations":[]}
        own=deepcopy(state);own["last_local_outcome"]=outcome
        returned=deepcopy(state);returned["child_reports"]=[{"only_index":rows}]
        variants=[render_literature_experimental_prompt(own,"Evaluate the supplied source binding interaction."),
            render_literature_experimental_prompt(returned,"Evaluate the supplied source binding interaction."),
            render_literature_experimental_prompt(state,"Evaluate the supplied source binding interaction.",lookup_results=[{"status":"completed","result":outcome["result"]}])]
        tasks=[v.split("\n\nSTEERING\n")[0] for v in variants]
        assert tasks[0]==tasks[1]==tasks[2]
        if not parent:
            assert tasks[0].count(BINDING_INTERACTION_MODEL_TASK)==1 and EXPERIMENTAL_TASK in tasks[0]
        for text in variants:
            steering=text.split("\n\nSTEERING\n")[1]
            assert "signed_index" in steering and ".995082" in steering
            assert "natural_log_nM" in steering and "synthetic_fixture" in steering
            assert "reference_form_log_ligand_ratio_minus_test_form_log_ligand_ratio" in steering
            assert "reported_parameter_not_intrinsic_affinity" in steering
            for secret in ("PRIVATE_COVARIANCE_ALIAS","PRIVATE_MODEL_BYTES_ALIAS",'"log_covariance"',"6.005662","0.4", "covariance diagonal .04"):
                assert secret not in steering


def test_empty_own_subset_and_saved_lookup_do_not_expand_model_or_operand_aliases(tmp_path):
    from test_literature_experimental_prompt_delivery import snapshot
    store,context,args,model_args,_,_=setup_model(tmp_path)
    with store:
        context=replace(context,assignment={**context.assignment,"requested_binding_interaction_model_components":[]})
        _,_,_,outcome,_=populate(store,context,args,model_args)
        assert outcome["result"]["rows"]==[] and outcome["result"]["cells"]=={}
        records={ref:store.get(ref) for ref in outcome["record_refs"] if ref.startswith("reference_")}
        support=next(r for r in records.values() if r.get("label")=="Binding interaction model interpretation support")
        alias_value={k:v for k,v in support.items() if k not in ("id","record_type","origin")}
        alias_value.update(accession="empty_alias",label="PRIVATE_EMPTY_MODEL_ALIAS_0.04")
        alias=store.put("reference",alias_value,origin="tool",scope=plain(context.scope))
        records[alias["id"]]=alias
        state=snapshot();state["literature_assignment"]=plain(context.assignment)
        state["literature_assignment"]["question_context_refs"]=[alias["id"]]
        state["literature_received_fact_display"]={"records":records,"received_refs":list(records)}
        for lookup in (False,True):
            current=deepcopy(state)
            if not lookup:current["last_local_outcome"]=outcome
            text=render_literature_experimental_prompt(current,"Evaluate the supplied source binding interaction.",
                lookup_results=[{"status":"completed","result":outcome["result"]}] if lookup else [])
            steering=text.split("\n\nSTEERING\n")[1]
            assert "PRIVATE_EMPTY_MODEL_ALIAS" not in steering
            assert "covariance diagonal .04" not in steering
            assert '"log_covariance"' not in steering


def test_actual_history_record_shape_preserves_requested_cells_without_selected_witness_quotes(tmp_path):
    from test_literature_experimental_prompt_delivery import snapshot
    store,context,args,model_args,_,_=setup_model(tmp_path)
    with store:
        context=replace(context,assignment={**context.assignment,"requested_binding_interaction_model_components":["signed_index"]})
        _,_,selected_args,outcome,_=populate(store,context,args,model_args)
        history={"status":"completed","record_refs":[],"changed_record_refs":[],"result":{"view":"records","records":[{
            "selection":{"kind":"tool","tool":"literature.binding.interaction.model.populate","arguments":selected_args},
            "outcome":outcome,"admitted_report":None,"report_delivery_failure":None}]}}
        state=snapshot();state["literature_assignment"]=plain(context.assignment)
        for own in (False,True):
            current=deepcopy(state)
            if own:current["last_local_outcome"]=history
            text=render_literature_experimental_prompt(current,"Evaluate the supplied source binding interaction.",
                lookup_results=[] if own else [history])
            steering=text.split("\n\nSTEERING\n")[1]
            assert "signed_index" in steering and ".995082" in steering
            assert "covariance diagonal .04" not in steering
            assert "model_witnesses" not in steering
            assert "6.005662" not in steering
