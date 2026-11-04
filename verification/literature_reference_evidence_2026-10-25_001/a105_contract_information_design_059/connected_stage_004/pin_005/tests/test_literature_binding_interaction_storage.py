"""Synthetic selected four-cell persistence, custody and finite native returns."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import sqlite3

import pytest
from PIL import Image

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_binding_interaction_storage import (
    LiteratureBindingInteractionRepository, COMPONENTS, RAW_COMPONENTS, binding_interaction_cells_schema,
)
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES
from gene_annotation_episode.literature_binding_interaction_validation import validate_saved_binding_interaction
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.state import Store
from test_literature_binding_interaction_inputs import fixture, png


def setup(path, change=None, expressions=("5", "40", "2", "4"), unit="nM", extra=""):
    args, sources, *_ = fixture(expressions, unit, extra)
    if change:
        change(args)
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    refs = {}
    for key, raw in sources.items():
        artifact = store.artifact(raw, "image/png" if key == "image" else "text/plain")
        refs[key] = store.put("source", {"provider": "synthetic_binding_" + key, "accession": None, "uri": None,
            "artifact_ref": artifact, "text_ref": artifact if key == "methods" else None,
            "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]
    def bind(value):
        if isinstance(value, dict):
            return {k: refs.get(v, v) if k in ("source_ref", "original_source_ref") else bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return value
    args = bind(args)
    context = BindingContext("binding-run", "binding-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": list(refs.values())}, {}, tuple(refs.values()))
    return store, context, args


def project(repo, outcome, components=None):
    return repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=components)


def test_eight_actual_native_cells_closed_schema_and_full_source_custody(tmp_path):
    store, context, args = setup(tmp_path)
    with store:
        repo = LiteratureBindingInteractionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = project(repo, outcome)
        assert [r["component"] for r in rows] == list(COMPONENTS)
        assert [r["value"] for r in rows[:7]] == [5,40,2,4,8,2,4]
        validate_form({"cells": rows}, obj({"cells": binding_interaction_cells_schema()}), lambda *_: True)
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["selection"] == args
        assert saved["extraction"]["selection"] == args
        assert all(r["model_reader_capability"] == "unimplemented" for r in rows)
        assert len(saved["calculation"]["cells"]) == 12
        assert not store.list("observation") and not store.list("assessment")
        for role in ROLES:
            m = saved["extraction"]["roles"][role]["measurement"]
            b = saved["role_bindings"][role]
            assert m["source_cell_id"] != saved["extraction"]["roles"][role]["physical_fit"]["physical_fit_id"]
            assert store.get(b["source_cell_ref"])["anchor"] is None
            assert store.get(b["expression"]["candidate_refs"][0])["anchor"] is None
            definition = store.get(b["definitions"]["subject"]["canonical_witness_ref"])
            anchor = definition["anchor"]
            assert store.get_artifact(anchor["artifact_ref"])[anchor["start"]:anchor["end"]].decode() == anchor["quote"]
        assert repo.populate(context, args, "selected") == outcome


@pytest.mark.parametrize("case", ["unknown_common", "conflicting_common", "unknown_unit", "mismatch", "unknown_context", "ambiguous", "unreadable", "reported_unavailable", "unresolved_uncertainty", "missing_sd", "partial_ci", "ci_unknown_level", "qualified_count"])
def test_partial_source_meanings_and_matching_row_only_numbers(tmp_path, case):
    args0, _, witness, enum, literal, _ = fixture(extra="CI lower 1 upper 9; count at least 3; SD statistic.")
    def change(args):
        role = args["roles"][ROLES[0]]
        if case == "unknown_common": args["parameter_kind"] = enum("unknown")
        elif case == "conflicting_common": args["parameter_kind"] = {"value":"conflicting", "witnesses":[witness("IC50 parameter"),witness("Hill Kd parameter")]}
        elif case == "unknown_unit": role["measurement"]["unit"] = None
        elif case == "mismatch": role["parameter_kind"] = enum("reported_hill_kd", "Hill Kd parameter")
        elif case == "unknown_context": role["definitions"]["construct"] = {"status":"unknown","label":None,"witnesses":[],"canonical_witness":None}
        elif case in ("ambiguous", "unreadable"):
            ex = role["measurement"]["expression"]; ex["status"] = case
            if case == "ambiguous":
                candidate = deepcopy(ex["candidates"][0]); candidate["quote"] = "8"; ex["candidates"].append(candidate)
            else: ex["fragments"], ex["candidates"] = ex["candidates"], []
        elif case == "unresolved_uncertainty": role["uncertainty"] = None
        elif case == "missing_sd": role["uncertainty"]["statistic"] = enum("sd", "SD statistic")
        elif case in ("partial_ci", "ci_unknown_level"):
            u=role["uncertainty"];u["statistic"]=enum("confidence_interval", "CI lower")
            endpoint=witness("CI lower 1"); endpoint.update(start=endpoint["end"]-1,quote="1")
            u["interval"]={"lower":{"status":"exact","candidates":[endpoint],"fragments":[]},"upper":None,"unit_relationship":enum("same_as_parameter", "Unit nM"),"unit":None}
            if case == "ci_unknown_level": u["interval"]["upper"] = literal("9")
        elif case == "qualified_count": role["uncertainty"]["exact_count"] = literal("at least 3")
    expressions = ("n.d.","40","2","4") if case == "reported_unavailable" else ("5","40","2","4")
    store, context, args = setup(tmp_path, change, expressions=expressions, extra="CI lower 1 upper 9; count at least 3; SD statistic.")
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        out=repo.populate(context,args,"selected"); rows=project(repo,out)
        validate_form({"cells":rows},obj({"cells":binding_interaction_cells_schema()}),lambda *_:True)
        for i,row in enumerate(rows):
            for j,role in enumerate(ROLES):
                values=row["roles"][role]["values"]
                assert values["delivery_status"] == ("requested" if i == j else "not_requested")
                if i != j: assert all(v is None for k,v in values.items() if k != "delivery_status")
        raw=rows[0]["roles"][ROLES[0]]["values"]
        if case in ("unknown_common","conflicting_common"):
            assert rows[0]["value"]==5 and rows[6]["value"] is None
            assert repo.read(out["result"]["sheet_ref"])["calculation"] is None
        if case == "unknown_unit": assert raw["native"]["value"]==5 and raw["canonical"] is None and rows[0]["unit"] is None
        if case == "mismatch": assert rows[0]["value"]==5 and rows[0]["roles"][ROLES[0]]["parameter_kind"]["value"]=="reported_hill_kd" and rows[6]["value"] is None
        if case == "ambiguous": assert [c["native"]["value"] for c in raw["candidates"]]==[5,8] and raw["native"] is None
        if case == "partial_ci": assert raw["uncertainty"]["interval"] == [1,None] and raw["uncertainty"]["confidence_level"] is None
        if case == "ci_unknown_level": assert raw["uncertainty"]["interval"] == [1,9] and raw["uncertainty"]["confidence_level"] is None
        if case == "missing_sd": assert raw["uncertainty"]["statistic"] == "sd" and raw["canonical"]["reported_spread"] is None
        if case == "qualified_count": assert raw["uncertainty"]["exact_count"] is None and raw["scalar_native"]["exact_count"] == 3


def test_ownership_admitted_subset_and_actual_mode_ro_before_first_projection(tmp_path,monkeypatch):
    path=tmp_path/"state";store,context,args=setup(path)
    repo=LiteratureBindingInteractionRepository(store,context.run_id);out=repo.populate(context,args,"selected")
    rows=project(repo,out);owner=replace(context,received_record_refs=(*context.received_record_refs,*out["record_refs"]))
    parent=replace(owner,episode_id="parent")
    assert repo.fact_cells(parent,[out["result"]["sheet_ref"]],components=COMPONENTS)==[]
    repo.receive_cells(parent,[rows[6]],"manual-admission")
    assert repo.fact_cells(parent,[out["result"]["sheet_ref"]],components=COMPONENTS)==[rows[6]]
    with pytest.raises(ContractError,match="cell_not_received"):repo.validate_fact_values(parent,rows)
    before=list(store.db.iterdump());artifacts={store.get(r)["artifact_ref"] for r in context.received_record_refs}
    actualpath=store.db.execute("PRAGMA database_list").fetchone()[2];store.close()
    def forbidden(*_a,**_kw):raise AssertionError("read-only reopen must not read sources/decode/parse/calculate/receive/reprice")
    monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.read_binding_interaction_inputs",forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.populate_binding_interaction",forbidden)
    monkeypatch.setattr(Image,"open",forbidden)
    reopened=Store.__new__(Store);reopened.path=path;reopened.db=sqlite3.connect("file:"+actualpath+"?mode=ro",uri=True);reopened.db.row_factory=sqlite3.Row
    try:
        original=reopened.get_artifact
        def saved_only(ref):
            assert ref not in artifacts
            return original(ref)
        monkeypatch.setattr(reopened,"get_artifact",saved_only)
        restored=LiteratureBindingInteractionRepository(reopened,context.run_id)
        monkeypatch.setattr(restored,"receive_cells",forbidden)
        assert restored.fact_cells(parent,[out["result"]["sheet_ref"]],components=COMPONENTS)==[rows[6]]
        assert restored.fact_cells(owner,[out["result"]["sheet_ref"]],components=COMPONENTS)==rows
        assert restored.populate(context,args,"selected")==out
        assert list(reopened.db.iterdump())==before
    finally:reopened.db.close()


@pytest.mark.parametrize("target",["request","payload","source_metadata","binding","outcome"])
def test_tampered_custody_is_rejected(tmp_path,target):
    store,context,args=setup(tmp_path)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id);out=repo.populate(context,args,"selected");saved=repo.read(out["result"]["sheet_ref"])
        if target in ("request","payload"):
            from gene_annotation_episode.materials import artifact_path
            source=store.get(out["result"]["sheet_ref"]);key=source["request_ref" if target=="request" else "artifact_ref"]
            artifact_path(store,key).write_bytes(store.get_artifact(key).replace(b'synthetic_fixture',b'primary_source',1))
        elif target in ("source_metadata","binding"):
            ref=args["source_ref"] if target=="source_metadata" else saved["role_bindings"][ROLES[0]]["source_cell_ref"]
            record=store.get(ref);record["provider" if target=="source_metadata" else "label"]="forged"
            store.db.execute("UPDATE records SET data=? WHERE id=?",(canonical(record),ref))
        else:
            fake=deepcopy(out);fake["result"]["cells"]["interaction_ratio"]["value"]=77
            store.db.execute("UPDATE literature_binding_interaction_operations SET outcome=?",(canonical(fake),))
        with pytest.raises(ContractError):repo.read(out["result"]["sheet_ref"])


def test_authorization_precedes_bytes_and_page_ancestry_is_actual(tmp_path,monkeypatch):
    store,context,args=setup(tmp_path)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        def forbidden(*_):raise AssertionError("unauthorized source bytes")
        monkeypatch.setattr(store,"get_artifact",forbidden)
        with pytest.raises(ContractError,match="not_received"):repo.populate(replace(context,received_record_refs=()),args,"unauthorized")
        page={"source_ref":args["source_ref"]}
        with pytest.raises(ContractError,match="outside_assigned_source"):
            repo.populate(replace(context,role="literature_targeted",path=(("literature_targeted","case"),),assignment={"page":page}),args,"wrong-page")


def test_selected_unsupported_model_component_and_different_key_reuse_reject(tmp_path):
    store,context,args=setup(tmp_path)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        with pytest.raises(ContractError,match="component_selection_invalid"):
            repo.populate(replace(context,assignment={"requested_binding_interaction_components":["signed_index"]}),args,"bad")
        repo.populate(context,args,"selected")
        args["source_kind"]="primary_source"
        with pytest.raises(ContractError,match="reused_for_different_work"):repo.populate(context,args,"selected")


@pytest.mark.parametrize("target",["canonical_meaning","physical_owner","cell_identity","operand_key","uncertainty_count","raw_relation","raw_value","unavailable_reason","context_association"])
def test_detached_association_checks_reject_tampering_without_source_or_calculation(tmp_path,monkeypatch,target):
    store,context,args=setup(tmp_path)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        saved=repo.read(repo.populate(context,args,"selected")["result"]["sheet_ref"])
        extraction,calculation=saved["extraction"],saved["calculation"];role=extraction["roles"][ROLES[0]]
        if target=="canonical_meaning":role["definitions"]["subject"]["canonical_id"]="invented"
        elif target=="physical_owner":role["physical_fit"]["physical_fit_id"]="invented"
        elif target=="cell_identity":role["measurement"]["source_cell_id"]="invented"
        elif target=="operand_key":calculation["operand_keys"][ROLES[0]]=calculation["operand_keys"][ROLES[1]]
        elif target=="uncertainty_count":role["uncertainty"]["canonical"]["exact_count"]=True
        elif target=="raw_relation":calculation["cells"]["parameter_rr"]["relation"]="gt"
        elif target=="raw_value":calculation["cells"]["parameter_rr"]["value"]=77
        elif target=="unavailable_reason":calculation["cells"]["interaction_ratio"].update(status="unavailable",value=None,relation=None,reason="missing_operand:"+ROLES[0])
        else:role["calculation_operand"]["context"]["subject"]="wrong form"
        def forbidden(*_a,**_kw):raise AssertionError("detached validation must not reacquire/reparse/recalculate")
        monkeypatch.setattr(store,"get_artifact",forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.read_binding_interaction_inputs",forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.populate_binding_interaction",forbidden)
        with pytest.raises(ExperimentalContractError,match="binding_interaction_saved_mismatch"):
            validate_saved_binding_interaction(args,extraction,calculation,saved["cells"])


@pytest.mark.parametrize("failed",["image","text"])
def test_authorized_local_source_failure_preserves_other_raw_work(tmp_path,monkeypatch,failed):
    store,context,args=setup(tmp_path)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        ref=args["images"][0]["source_ref"] if failed=="image" else args["source_ref"]
        artifact=store.get(ref)["artifact_ref"];read=store.get_artifact
        def local_read(key):
            if key==artifact:raise OSError("synthetic authorized dependency unavailable")
            return read(key)
        monkeypatch.setattr(store,"get_artifact",local_read)
        out=repo.populate(context,args,"selected");rows=project(repo,out)
        assert rows[6]["value"] is None
        if failed=="text":
            assert rows[0]["roles"][ROLES[0]]["values"]["native"]["value"]==5
            assert rows[0]["roles"][ROLES[0]]["values"]["canonical"] is None
            assert rows[0]["common_parameter_kind"]["status"]=="source_unavailable"
        else:
            assert rows[0]["roles"][ROLES[0]]["parse_status"]=="source_unavailable"
            assert rows[0]["common_parameter_kind"]["value"]=="ic50"
        validate_form({"cells":rows},obj({"cells":binding_interaction_cells_schema()}),lambda *_:True)


def test_original_image_crop_requires_actual_ancestry_and_keeps_canonical_geometry(tmp_path):
    from io import BytesIO
    store,context,args=setup(tmp_path)
    with store:
        original=args["images"][0]["source_ref"]
        image=Image.open(BytesIO(store.get_artifact(store.get(original)["artifact_ref"])))
        artifact=store.artifact(png(image.crop((200,0,450,200))),"image/png")
        def wrapper(parents):
            return store.put("source",{"provider":"synthetic_crop","accession":None,"uri":None,"artifact_ref":artifact,
                "text_ref":None,"request_ref":None,"version":None,"retrieved_at":None,"parent_source_refs":parents},origin="caller")["id"]
        cropped=wrapper([original]);orphan=wrapper([])
        args["images"][0].update(source_ref=cropped,mapping={"original_region":[200,0,450,200],"colour_conversion":"preserve"})
        for role in ROLES:
            measurement=args["roles"][role]["measurement"]
            for region in [measurement["cell_region"],measurement["expression"]["candidates"][0]["region"]]:region[0]-=200;region[2]-=200
        context=replace(context,received_record_refs=(*context.received_record_refs,cropped,orphan))
        repo=LiteratureBindingInteractionRepository(store,context.run_id);out=repo.populate(context,args,"crop")
        saved=repo.read(out["result"]["sheet_ref"])
        role=saved["extraction"]["roles"][ROLES[0]]
        assert role["measurement"]["canonical_locator"]["image_region"]==[200,10,400,38]
        ref=saved["role_bindings"][ROLES[0]]["expression"]["candidate_refs"][0]
        assert store.get(ref)["anchor"] is None and store.get(ref)["source_ref"]==original
        args["images"][0]["source_ref"]=orphan
        with pytest.raises(ContractError,match="image_original_ancestry_mismatch"):repo.populate(context,args,"orphan")
        # An original image must be received too, even when the crop is received.
        args["images"][0]["source_ref"]=cropped
        with pytest.raises(ContractError,match="source_not_received"):
            repo.populate(replace(context,received_record_refs=tuple(r for r in context.received_record_refs if r!=original)),args,"unreceived-original")


@pytest.mark.parametrize("expressions",[("<5","40","2","4"),("5","<40","2","<4")])
def test_printed_limits_keep_thresholds_and_do_not_become_points(tmp_path,expressions):
    store,context,args=setup(tmp_path,expressions=expressions)
    with store:
        repo=LiteratureBindingInteractionRepository(store,context.run_id);rows=project(repo,repo.populate(context,args,"limits"))
        limit=next(r for r in rows[:4] if r["threshold"] is not None)
        assert limit["value"] is None and limit["bound_kind"]=="printed_limit"
        if expressions[0].startswith("<"):
            assert rows[6]["value"] is None and rows[6]["threshold"]==4 and rows[6]["relation"]=="gt"
        else:assert rows[6]["unavailable_reason"]=="opposing_reported_limits"
        validate_form({"cells":rows},obj({"cells":binding_interaction_cells_schema()}),lambda *_:True)


@pytest.mark.parametrize("alias",["physical_fit","conflicting_cell","ambiguous_rereading"])
def test_actual_cell_aliases_and_fit_owners_remain_distinct_and_local(tmp_path,alias):
    store,context,args=setup(tmp_path)
    with store:
        rr,rt=args["roles"][ROLES[0]],args["roles"][ROLES[1]]
        if alias=="physical_fit":rt["physical_fit"]=deepcopy(rr["physical_fit"])
        else:
            rt["measurement"]["cell_region"]=deepcopy(rr["measurement"]["cell_region"])
            rt["measurement"]["expression"]["candidates"][0]["region"]=deepcopy(rr["measurement"]["cell_region"])
            if alias=="ambiguous_rereading":
                ex=rt["measurement"]["expression"];ex["status"]="ambiguous"
                other=deepcopy(ex["candidates"][0]);other["quote"]="8";ex["candidates"].append(other)
                # Canonical meaning must agree for an unresolved rereading, so
                # the ambiguous token remains ambiguity rather than conflict.
                rt["definitions"]=deepcopy(rr["definitions"])
        repo=LiteratureBindingInteractionRepository(store,context.run_id)
        out=repo.populate(context,args,"alias");rows=project(repo,out)
        if alias=="physical_fit":
            assert rows[0]["value"]==5 and rows[1]["value"]==40
            assert rows[4]["unavailable_reason"]=="reused_physical_fit"
        else:
            status="ambiguous" if alias=="ambiguous_rereading" else "conflicting"
            assert rows[0]["value"] is None and rows[0]["roles"][ROLES[0]]["parse_status"]==status
            assert rows[1]["roles"][ROLES[1]]["values"]["candidates"][0]["native"]["value"]==40
        assert rows[5]["value"]==2
        validate_form({"cells":rows},obj({"cells":binding_interaction_cells_schema()}),lambda *_:True)
