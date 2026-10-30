"""Synthetic selected supplement, persistence and exact typed custody."""
from copy import deepcopy
from dataclasses import replace
import math

import pytest

from gene_annotation_episode.domain import ContractError, canonical, obj, validate_schema
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.literature_binding_interaction_storage import LiteratureBindingInteractionRepository
from gene_annotation_episode.literature_binding_interaction_model_storage import LiteratureBindingInteractionModelRepository, COMPONENTS, binding_interaction_model_cells_schema
from gene_annotation_episode.literature_binding_interaction_calculations import ROLES
from gene_annotation_episode.state import Store
from test_literature_binding_interaction_model_inputs import setup_model


def populate(store,context,native_args,model_args):
    native = LiteratureBindingInteractionRepository(store,context.run_id).populate(context,native_args,"native")
    owner = replace(context,received_record_refs=(*context.received_record_refs,*native["record_refs"]))
    args = {**model_args,"source_ref":native["result"]["sheet_ref"]}
    repo = LiteratureBindingInteractionModelRepository(store,context.run_id)
    outcome = repo.populate(owner,args,"model")
    owner = replace(owner,received_record_refs=(*owner.received_record_refs,*outcome["record_refs"]))
    return repo,owner,args,outcome,native


@pytest.mark.parametrize("status",["known","estimated","unknown","absent"])
def test_existing_four_cells_native_eight_preserved_and_conditional_meanings(tmp_path,status):
    store,context,native_args,args,_,_=setup_model(tmp_path,status=status if status!="absent" else "known")
    with store:
        if status=="absent":args.update(model_source_ref=None,model_witnesses=[])
        repo,owner,args,outcome,native=populate(store,context,native_args,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        validate_closed_schema(obj({"cells":binding_interaction_model_cells_schema()}))
        validate_schema(rows,binding_interaction_model_cells_schema())
        assert [r["component"] for r in rows]==list(COMPONENTS)
        assert all(r["origin"]=="derived" and r["source_kind"]=="synthetic_fixture" for r in rows)
        if status in ("known","estimated"):
            assert rows[0]["value"]==pytest.approx(.16)
            assert rows[1]["value"]==pytest.approx(.4)
            if status=="known":
                assert rows[2]["value"]==pytest.approx(6.005662673977517)
                assert rows[3]["value"]==pytest.approx(.9950826091535326)
            else:
                assert rows[2]["unavailable_reason"]=="covariance_estimated_not_known"
                assert rows[3]["value"] is None
        else:
            assert all(r["value"] is None for r in rows)
            assert rows[0]["unavailable_reason"]==("observation_model_missing" if status=="absent" else "covariance_status_unknown")
        saved=repo.read(outcome["result"]["sheet_ref"])
        original=LiteratureBindingInteractionRepository(store,context.run_id).read(native["result"]["sheet_ref"])
        assert {k:saved["calculation"]["cells"][k] for k in original["cells"]}=={k:original["calculation"]["cells"][k] for k in original["cells"]}
        assert original["calculation"]["model"] is None
        assert repo.populate(owner,args,"model")==outcome
        assert not store.list("assessment") and not store.list("observation")


@pytest.mark.parametrize("expression,distribution,reason",[("<5","normal","censored_joint_likelihood_unimplemented"),("5","unspecified","normal_log_observation_model_unspecified")])
def test_censoring_distribution_and_source_defined_event_do_not_become_points(tmp_path,expression,distribution,reason):
    store,context,native,args,_,_=setup_model(tmp_path,expressions=(expression,"40","2","4"),distribution=distribution,reporting_event=True)
    with store:
        repo,owner,_,outcome,_=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        assert rows[0]["value"]==pytest.approx(.16)
        assert rows[2]["unavailable_reason"]==reason and rows[3]["value"] is None
        assert rows[0]["reporting_event"]=="source_defined"


@pytest.mark.parametrize("case",["unknown_kind","missing_operand","unknown_mapping","conflicting_relationship","shared_fit"])
def test_partial_inputs_and_scientific_relationships_are_preserved(tmp_path,case):
    def change(args):
        if case=="unknown_kind":args["parameter_kind"]={"value":"unknown","witnesses":[]}
        elif case=="missing_operand":args["roles"][ROLES[0]]=None
        elif case=="unknown_mapping":args["roles"][ROLES[0]]["definitions"]["construct"]={"status":"unknown","label":None,"witnesses":[],"canonical_witness":None}
        elif case=="conflicting_relationship":args["relationships"]["ligand_correspondence"]={"status":"unknown","witnesses":[]}
        else:args["roles"][ROLES[1]]["physical_fit"]=deepcopy(args["roles"][ROLES[0]]["physical_fit"])
    status="unknown" if case=="missing_operand" else "known"
    matrix=[[.04 if i==j else 0 for j in range(4)] for i in range(4)]
    if case=="shared_fit":matrix=[[.04,.04,0,0],[.04,.04,0,0],[0,0,.04,0],[0,0,0,.04]]
    store,context,native,args,_,_=setup_model(tmp_path,change=change,status=status,covariance=matrix)
    with store:
        repo,owner,_,outcome,original=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        assert all(r["value"] is None for r in rows)
        expected={"unknown_kind":"common_parameter_kind_unknown","missing_operand":"missing_operand:"+ROLES[0],
            "unknown_mapping":"canonical_construct_unknown","conflicting_relationship":"ligand_correspondence_unknown","shared_fit":"reused_physical_fit"}[case]
        assert all(r["unavailable_reason"]==expected for r in rows)
        if case=="unknown_kind":
            assert original["result"]["cells"]["parameter_rr"]["value"]==5
            assert rows[0]["common_parameter_kind"]["value"]=="unknown"


def test_cross_terms_propagate_and_shared_owner_matrix_must_agree(tmp_path):
    matrix=[[.04,.01,0,0],[.01,.04,0,0],[0,0,.04,0],[0,0,0,.04]]
    store,context,native,args,_,_=setup_model(tmp_path,covariance=matrix)
    with store:
        repo,owner,_,outcome,_=populate(store,context,native,args)
        assert repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=[COMPONENTS[0]])[0]["value"]==pytest.approx(.14)


@pytest.mark.parametrize("missing",["sheet","model","witness"])
def test_all_direct_sources_require_actual_receipt(tmp_path,missing):
    store,context,native,args,_,_=setup_model(tmp_path)
    with store:
        original=LiteratureBindingInteractionRepository(store,context.run_id).populate(context,native,"native")
        args["source_ref"]=original["result"]["sheet_ref"]
        received=(*context.received_record_refs,*original["record_refs"])
        ref=args["source_ref"] if missing=="sheet" else args["model_source_ref"] if missing=="model" else args["model_witnesses"][0]["source_ref"]
        owner=replace(context,received_record_refs=tuple(r for r in received if r!=ref))
        with pytest.raises(ContractError,match="source_not_received"):
            LiteratureBindingInteractionModelRepository(store,context.run_id).populate(owner,args,"model")


def test_exact_subset_and_query_only_saved_reconstruction(tmp_path,monkeypatch):
    path=tmp_path/"state"
    store,context,native,args,_,_=setup_model(path)
    repo,owner,args,outcome,_=populate(store,context,native,args)
    ref=outcome["result"]["sheet_ref"]
    rows=repo.fact_cells(owner,[ref],components=COMPONENTS)
    parent=replace(owner,episode_id="parent")
    assert repo.fact_cells(parent,[ref],components=COMPONENTS)==[]
    subset=[rows[3]];repo.receive_cells(parent,subset,"trusted-admission")
    assert repo.fact_cells(parent,[ref],components=COMPONENTS)==subset
    with pytest.raises(ContractError,match="cell_not_received"):repo.validate_fact_values(parent,rows)
    invalid=deepcopy(subset);invalid[0]["value"]=.9
    with pytest.raises(ContractError,match="differs_from_saved"):repo.receive_cells(parent,invalid,"forged")
    before=list(store.db.iterdump())
    raw={store.get(r)["artifact_ref"] for r in context.received_record_refs}
    store.close()
    def forbidden(*a,**k):raise AssertionError("saved replay must not read/reparse/recalculate science")
    for module,name in [("literature_binding_interaction_model_storage","read_binding_interaction_model"),
        ("literature_binding_interaction_model_storage","populate_binding_interaction"),
        ("literature_binding_interaction_storage","read_binding_interaction_inputs"),
        ("literature_binding_interaction_storage","populate_binding_interaction")]:
        monkeypatch.setattr("gene_annotation_episode."+module+"."+name,forbidden)
    with Store(path) as reopened:
        get=reopened.get_artifact
        def saved_only(ref):
            assert ref not in raw
            return get(ref)
        monkeypatch.setattr(reopened,"get_artifact",saved_only)
        reopened.db.execute("PRAGMA query_only=ON")
        restored=LiteratureBindingInteractionModelRepository(reopened,context.run_id)
        assert restored.populate(owner,args,"model")==outcome
        assert restored.fact_cells(parent,[ref],components=COMPONENTS)==subset
        assert restored.received_cells(parent)==subset
        assert list(reopened.db.iterdump())==before


@pytest.mark.parametrize("requested",[[],["signed_index"]])
def test_own_outcome_contains_only_requested_numbers(tmp_path,requested):
    store,context,native,args,_,_=setup_model(tmp_path)
    with store:
        context=replace(context,assignment={**context.assignment,"requested_binding_interaction_model_components":requested})
        _,_,_,outcome,_=populate(store,context,native,args)
        assert set(outcome["result"]["cells"])==set(requested)
        assert [r["component"] for r in outcome["result"]["rows"]]==requested
        assert '"log_covariance"' not in canonical(outcome["result"])
        for row in outcome["result"]["rows"]:
            assert all(all(v is None for k,v in r["values"].items() if k!="delivery_status") for r in row["roles"].values())


@pytest.mark.parametrize("target",["payload","request","outcome"])
def test_saved_tampering_never_becomes_original_fact(tmp_path,target):
    from gene_annotation_episode.materials import artifact_path
    store,context,native,args,_,_=setup_model(tmp_path)
    with store:
        repo,_,_,outcome,_=populate(store,context,native,args)
        sheet=store.get(outcome["result"]["sheet_ref"])
        if target in ("payload","request"):
            ref=sheet["artifact_ref" if target=="payload" else "request_ref"]
            artifact_path(store,ref).write_bytes(store.get_artifact(ref)+b' ')
        else:
            forged=deepcopy(outcome);forged["result"]["cells"]["signed_index"]["value"]=True
            store.db.execute("UPDATE literature_binding_interaction_model_operations SET outcome=?",(canonical(forged),))
        with pytest.raises(ContractError):repo.read(sheet["id"])


@pytest.mark.parametrize("matrix,reason", [([[0]*4 for _ in range(4)],"zero_interaction_variance"),
    ([[.04 if i==j else 0 for j in range(4)] for i in range(4)],None)])
def test_known_covariance_zero_variance_and_index_prerequisites(tmp_path,matrix,reason):
    store,context,native,args,_,_=setup_model(tmp_path,covariance=matrix)
    with store:
        repo,owner,_,outcome,_=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        assert rows[2]["unavailable_reason"]==reason and rows[3]["unavailable_reason"]==reason
        if reason:
            assert rows[0]["value"]==rows[1]["value"]==0
            assert rows[2]["value"] is None


def test_index_numerical_saturation_retains_case_specific_not_certainty_qualification(tmp_path):
    matrix=[[1e-310 if i==j else 0 for j in range(4)] for i in range(4)]
    store,context,native,args,_,_=setup_model(tmp_path,covariance=matrix,expressions=("1","1e300","1","1"))
    with store:
        repo,owner,_,outcome,_=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        assert rows[2]["value"] is None and rows[2]["unavailable_reason"]=="profile_log_ratio_representation_range"
        assert rows[3]["value"]==1
        assert "signed_index_rounded_endpoint_not_certainty" in rows[3]["qualifications"]


def test_optional_repository_discovery_installs_no_tables_on_query_only_store(tmp_path):
    store,context,_,_,_,_=setup_model(tmp_path)
    with store:
        before=list(store.db.iterdump())
        store.db.execute("PRAGMA query_only=ON")
        repo=LiteratureBindingInteractionModelRepository(store,context.run_id)
        assert repo.received_cells(context)==[]
        assert repo.project_cells([],permitted_record_refs=(),components=[])==[]
        assert list(store.db.iterdump())==before


def test_reporting_event_locator_requires_actual_exact_selected_support(tmp_path):
    store,context,native,args,_,wire=setup_model(tmp_path,reporting_event=True)
    with store:
        wire["reporting_event_source"]["end"]-=1
        old=store.get(args["model_source_ref"])
        record={k:v for k,v in old.items() if k not in ("id","record_type","origin")}
        record["artifact_ref"]=record["text_ref"]=store.artifact(canonical(wire),"application/json")
        replacement=store.put("source",record,origin="caller")["id"]
        args["model_source_ref"]=replacement
        context=replace(context,received_record_refs=(*context.received_record_refs,replacement))
        with pytest.raises(ContractError,match="reporting_event_witness_required"):
            populate(store,context,native,args)


@pytest.mark.parametrize("change,reason",[
    (lambda a: a.update(model_witnesses=[]),"model_witness_required"),
    (lambda a: a.update(model_source_ref=None),"source_required_for_witnesses"),
    (lambda a: a["model_witnesses"][0].update(quote="different"),"source_quote_mismatch"),
])
def test_model_source_support_and_exact_quote_are_distinct_requirements(tmp_path,change,reason):
    from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
    store,context,native,args,_,_=setup_model(tmp_path)
    with store:
        change(args)
        with pytest.raises((ContractError,ExperimentalContractError),match=reason):populate(store,context,native,args)


def test_opposing_printed_limits_do_not_suppress_covariance_precision(tmp_path):
    store,context,native,args,_,_=setup_model(tmp_path,expressions=(">5",">40","2","4"))
    with store:
        repo,owner,_,outcome,_=populate(store,context,native,args)
        rows=repo.fact_cells(owner,[outcome["result"]["sheet_ref"]],components=COMPONENTS)
        assert rows[0]["value"]==pytest.approx(.16) and rows[1]["value"]==pytest.approx(.4)
        assert rows[2]["value"] is None and rows[2]["unavailable_reason"]=="opposing_reported_limits"


@pytest.mark.parametrize("target",["formula","unit","boolean","range","model_owner","model_psd","native_cell","qualifications","relation"])
def test_private_saved_structural_validation_without_source_reads_or_recalculation(tmp_path,monkeypatch,target):
    """Isolate semantic validation after the independently tested hash boundary."""
    store,context,native,args,_,_=setup_model(tmp_path)
    with store:
        context=replace(context,assignment={**context.assignment,"requested_binding_interaction_model_components":[]})
        repo,_,_,outcome,_=populate(store,context,native,args)
        ref=outcome["result"]["sheet_ref"];source=store.get(ref);saved=repo.read(ref)
        forged=deepcopy(saved);calc=forged["calculation"]
        if target=="formula":calc["cells"]["signed_profile_log_ratio"]["formula"]="unrelated formula"
        elif target=="unit":calc["cells"]["signed_profile_log_ratio"]["unit"]="nM"
        elif target=="boolean":calc["cells"]["signed_index"]["value"]=True
        elif target=="range":calc["cells"]["signed_index"]["value"]=1.1
        elif target=="model_owner":calc["model"]["physical_fit_ids"].reverse()
        elif target=="model_psd":calc["model"]["log_covariance"][0][0]=-1
        elif target=="native_cell":calc["cells"]["interaction_ratio"]["value"]=5
        elif target=="qualifications":calc["qualifications"]=[]
        else:calc["cells"]["signed_index"]["relation"]="gt"
        original_json=repo._json
        monkeypatch.setattr(repo,"_json",lambda key:deepcopy(forged) if key==source["artifact_ref"] else original_json(key))
        raw={store.get(r)["artifact_ref"] for r in context.received_record_refs};get=store.get_artifact
        def saved_only(key):
            assert key not in raw
            return get(key)
        def forbidden(*a,**k):raise AssertionError("semantic validation cannot calculate")
        monkeypatch.setattr(store,"get_artifact",saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_model_storage.populate_binding_interaction",forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_model_storage.read_binding_interaction_model",forbidden)
        with pytest.raises(ContractError):repo.read(ref)


def test_unknown_common_kind_never_calls_any_scientific_calculator(tmp_path,monkeypatch):
    def change(args):args["parameter_kind"]={"value":"unknown","witnesses":[]}
    store,context,native,args,_,_=setup_model(tmp_path,change=change)
    with store:
        def forbidden(*a,**k):raise AssertionError("unknown common kind has no calculation inputs")
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.populate_binding_interaction",forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_model_storage.populate_binding_interaction",forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_model_storage.read_binding_interaction_model",forbidden)
        repo,_,_,outcome,_=populate(store,context,native,args)
        assert repo.read(outcome["result"]["sheet_ref"])["calculation"] is None
        assert all(c["unavailable_reason"]=="common_parameter_kind_unknown" for c in outcome["result"]["cells"].values())
