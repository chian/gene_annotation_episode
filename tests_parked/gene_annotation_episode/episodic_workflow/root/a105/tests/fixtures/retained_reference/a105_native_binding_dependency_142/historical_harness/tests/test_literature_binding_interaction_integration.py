"""Real selected Episodes/C4 and actual provider text with synthetic sources."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
import sqlite3

import pytest
from PIL import Image
from method_loop import EpisodeGoal
from method_loop.archive import JsonArchive
from method_loop.durable import content_digest
from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_admission import ReceiverBindingV1, admit_return
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_binding_interaction_storage import LiteratureBindingInteractionRepository, COMPONENTS, binding_interaction_cells_schema
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES
from gene_annotation_episode.runtime import run_workflow, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_episode_admission import Value, seal_return
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_binding_interaction_storage import setup, project
from test_literature_rate_episode_integration import service_binding
from test_runtime import FixtureController, ScriptedProvider

FORM = obj({"numbers": binding_interaction_cells_schema()})


def reason(store, source_ref):
    raw = store.get_artifact(store.get(source_ref)["artifact_ref"])
    token = b"formA"; first = raw.index(token)
    commit = {k: [] for k in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias":"source_form","reference_type":"assay","source_ref":source_ref,
        "label":token.decode(),"anchor":{"source_ref":source_ref,"artifact_ref":store.get(source_ref)["artifact_ref"],
            "start":first,"end":first+len(token),"quote":token.decode()}}]
    return {"selection":{"kind":"reason","commit":commit},"report_update":{}}


def test_actual_nested_selected_episode_delivery_has_exact_observations_and_zero_credit(tmp_path):
    store,context,args=setup(tmp_path/"state")
    try:
        outer={**plain(context.assignment),"requested_binding_interaction_components":list(COMPONENTS)}
        inner={"version":"strategy_assignment_v1","question_context_refs":[],"prior_search_refs":list(context.received_record_refs),
            "requested_binding_interaction_components":["interaction_ratio","log_interaction"]}
        def commission(role,assignment):
            return {"selection":{"kind":"episode_child","role":role,"assignment":assignment,
                "goal":"Compare two source molecular forms across two ligands","scope":plain(context.scope),
                "purpose":"Return the requested native interaction components","schema_json":json.dumps(FORM),"initial_report_json":"{}"},"report_update":{}}
        received=[]
        def use(inputs):
            form,=inputs["child_reports"]
            assert [r["component"] for r in form["numbers"]]==["interaction_ratio","log_interaction"]
            assert form["numbers"][0]["value"]==4
            assert all(r["roles"][role]["values"]["delivery_status"]=="not_requested" for r in form["numbers"] for role in ROLES)
            received.append(deepcopy(form));return reason(store,args["source_ref"])
        provider=ScriptedProvider([commission("literature",outer),commission("literature_strategy",inner),
            {"selection":{"kind":"tool","tool":"literature.binding.interaction.populate","arguments":args},"report_update":{}},use,use])
        controllers=[]
        def controller(path,initial):
            value=FixtureController(str(path),initial,1 if len(path)==3 else 2);controllers.append(value);return value
        scorer=ScientificFindingProgress(FindingProgressPolicy(1))
        summary=asyncio.run(run_workflow(store,ToolRegistry(store),provider=provider,run_dir=tmp_path/"run",controller_factory=controller,
            project_credit=scorer,initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,reference_parent_sources=list(context.received_record_refs)),),
            binding_definitions={"credit":scorer.as_record()}))
        assert summary["credit"]==0 and received[0]==received[1]
        assert len(provider.contexts)==5 and [c.scores for c in controllers]==[[0,0],[0,0],[0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]==5
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_operations").fetchone()[0]==1
        assert store.db.execute("SELECT count(*) FROM literature_binding_interaction_received").fetchone()[0]==2
        assert not store.list("observation") and not store.list("assessment")
    finally:store.close()


@pytest.mark.parametrize("parent,off_page",[(False,False),(False,True),(True,False),(True,True)])
def test_actual_provider_text_masks_unrequested_image_text_and_unknown_source_labels(tmp_path,parent,off_page):
    extra="CI limits 1.1357911 and 9.2468022; confidence 95%; count 73; technical measurements"
    store,context,args=setup(tmp_path/"state",expressions=("5.13792468 ± 0.86421357","40.12342468","2.213579","4.32468"),extra=extra)
    try:
        text=store.get_artifact(store.get(args["source_ref"])["artifact_ref"]).decode()
        def witness(quote):
            start=text.index(quote);return {"kind":"text","source_ref":args["source_ref"],"representation":"original",
                "start":len(text[:start].encode()),"end":len(text[:start+len(quote)].encode()),"quote":quote}
        def meaning(value,quote=extra):return {"value":value,"witnesses":[witness(quote)]}
        # The broad source condition includes count, confidence and endpoint
        # literals. Those labels must not undo the requested derived-only form.
        for role in ROLES:
            definition=args["roles"][role]["definitions"]["conditions"]
            definition.update(label=extra,witnesses=[witness(extra)],canonical_witness=witness(extra))
        unc=args["roles"][ROLES[0]]["uncertainty"]
        unc.update(statistic=meaning("sd"),exact_count={"status":"exact","candidates":[witness("73")],"fragments":[]},
            repetition_basis=meaning("technical_measurements"))
        repo=LiteratureBindingInteractionRepository(store,context.run_id);out=repo.populate(context,args,"selected")
        rows=project(repo,out,["interaction_ratio"])
        state=snapshot();state["child_reports"]=[{"arbitrary_parent_field":rows}];state["requested_form"]=FORM
        state["literature_assignment"]={**plain(context.assignment),"requested_binding_interaction_components":["interaction_ratio"]}
        records=store.list("reference")
        if off_page:
            hidden={t["ref"] for role in rows[0]["roles"].values() for t in role["numeric_locations"]}
            records=[r for r in records if r["id"] not in hidden]
        other_raw=b"unrelated source definition";artifact=store.artifact(other_raw,"text/plain")
        other=store.put("source",{"provider":"synthetic_unrelated","accession":None,"uri":None,"artifact_ref":artifact,
            "text_ref":artifact,"request_ref":None,"version":None,"retrieved_at":None},origin="caller")
        label=store.put("reference",{"reference_type":"literature_result","source_ref":other["id"],"accession":"unrelated","label":other_raw.decode(),
            "sequence_ref":None,"molecule":None,"length":None,"term_refs":[],"context_refs":[],"anchor":{"source_ref":other["id"],"artifact_ref":artifact,
                "start":0,"end":len(other_raw),"quote":other_raw.decode()}},origin="tool")
        state["working_state"]={"references":[*records,label]};state["current_report_basis_refs"]=[label["id"]]
        if parent:
            state.pop("literature_assignment",None);state["literature_experimental_work"]["aspect"]="reference_evidence_parent"
            state["reference_evidence_parent"]={"version":"reference_evidence_parent_v1","source_refs":list(context.received_record_refs),"source_custody":[],"child_population_operations":[]}
        wire=LiteratureWire(tmp_path/"wire");asyncio.run(complete(wire,state_frame(state)))
        rendered=wire.turns_sent()[0]["input"][0]["text"]
        assert "Admitted requested binding interaction components" in rendered
        assert str(rows[0]["value"]) in rendered and "unrelated source definition" in rendered
        assert "technical_measurements" in rendered
        for secret in ("5.13792468","0.86421357","40.12342468","2.213579","4.32468","1.1357911","9.2468022","95%"):
            assert secret not in rendered
        assert "| exact_count | 73" not in rendered
        assert "formA" in rendered and "constructA" in rendered
        # Explicit subsequent source access remains authorized, including image.
        assert repo._native_source(context,args["images"][0]["source_ref"])["record_type"]=="source"
    finally:store.close()


def test_actual_c4_admission_rollback_original_receipt_tamper_and_read_only_reopen(tmp_path, monkeypatch):
    store, seed, args = setup(tmp_path / "state")
    run = seed.run_id
    root_goal = EpisodeGoal.root(objective="Evaluate synthetic native evidence", result_contract={})
    child_goal = EpisodeGoal.child(root_goal, objective="Compare native binding_interaction parameters", result_contract={})
    parent_path, child_path = [["annotation", "root"]], [["annotation", "root"], ["literature", "binding_interaction"]]
    parent_id, child_id = EpisodeRef(run, parent_path).episode_id, EpisodeRef(run, child_path).episode_id
    assignment = {**plain(seed.assignment), "requested_binding_interaction_components": ["interaction_ratio"]}
    child = replace(seed, episode_id=child_id, path=tuple(tuple(p) for p in child_path), assignment=assignment)
    parent = replace(seed, episode_id=parent_id, role="annotation", path=(("annotation", "root"),), assignment={})
    repo = LiteratureBindingInteractionRepository(store, run)
    outcome = repo.populate(child, args, "selected")
    child = replace(child, received_record_refs=(*child.received_record_refs, *outcome["record_refs"]))
    _, binding = service_binding(store, child)
    rows = binding.facts(child, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})["literature_binding_interaction_cells"]
    form = {"numbers": rows}
    contract = TypedReportContract("Receive native binding_interaction contrast", FORM, lambda *_: True)
    parent_request = {"goal": root_goal.as_record(), "message": {"scope": plain(seed.scope)}, "report_contract": None}
    request = {"goal": child_goal.as_record(), "message": {"scope": plain(seed.scope), "episode_assignment": assignment}, "report_contract": contract.as_record()}
    journal = Journal(store, run)
    for eid, path, req, state in ((parent_id, parent_path, parent_request, "active"), (child_id, child_path, request, "yielded")):
        journal.save("runtime_episodes", {"episode_id": eid, "path": canonical(path), "request": canonical(req),
            "initial_credit": 0, "state": state, "completion": None, "archive": None})
    spec = {"version": "episode_commission_v1", "handle": "original-binding_interaction-handle", "operation_key": "original-commission", "run_id": run,
        "parent": {"episode_id": parent_id, "goal_id": root_goal.goal_id, "path": parent_path},
        "child": {"episode_id": child_id, "role": "literature", "key": "binding_interaction", "path": child_path, "request": request, "scope": plain(seed.scope)},
        "input_versions": [], "runtime_binding": {"factory_module": "fixture", "factory_name": "open_commission", "arguments": {},
            "implementation_sha256": "a" * 64, "settings_sha256": "b" * 64}, "constraints": {}, "resource_selection": None, "expectation_snapshot_refs": []}
    journal.save("runtime_actions", {"episode_id": parent_id, "decision_index": 7, "action": canonical({"kind": "episode_child", "role": "literature"}),
        "result": canonical({"status": "pending", "pending_handle": spec["handle"]}), "credit": None})
    journal.save("runtime_forms", {"episode_id": child_id, "facts": canonical({"literature_binding_interaction_cells": rows, "changed_record_refs": outcome["changed_record_refs"]}), "form": canonical(form)})
    archive = JsonArchive(tmp_path / "archive")
    returned = {"version": "returned_episode_v1", "handle": spec["handle"], "return_id": "", "commission_sha256": content_digest(spec),
        "returned_at": "2026-10-26T12:00:00+00:00", "outcome": "closed", "completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 1},
        "episode_archive": archive.store({"synthetic": True}).descriptor(), "result_archive": archive.store({"form": form}).descriptor(),
        "form": form, "facts_archive": archive.store({"literature_binding_interaction_cells": rows}).descriptor(), "pending_handles": [], "failure": None}
    seal_return(returned)
    key = run + ":" + parent_id + ":7:typed_form"
    def receive(value):
        binding.received_form_references(parent, value, FORM, key)
        return outcome["record_refs"]
    receiver = ReceiverBindingV1(store, journal, 7, contract, lambda value: binding.validate_report(child, value, FORM),
        receive, lambda: 0, lambda index, credit: Value({"credit": credit, "estimation_action_index": index}))
    try:
        bound_repo = binding.services.literature_binding_interaction_repository()
        original = bound_repo.receive_cells
        def interrupted(*a, **kw):
            original(*a, **kw)
            raise OSError("interrupted after binding_interaction receipt")
        monkeypatch.setattr(bound_repo, "receive_cells", interrupted)
        with pytest.raises(OSError):
            admit_return(spec, returned, receiver)
        assert repo.received_cells(parent) == []
        monkeypatch.setattr(bound_repo, "receive_cells", original)
        admitted = admit_return(spec, returned, receiver)
        assert admitted["state"] == "admitted" and admitted["report"] == form
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys([*parent.received_record_refs, *admitted["received_record_refs"]])))
        assert binding.received_report_facts(parent)["literature_binding_interaction_cells"] == rows
        forged = project(repo, outcome, ["parameter_rr"])
        store.db.execute("UPDATE literature_binding_interaction_received SET cells=?", (canonical(forged),))
        store.db.execute("UPDATE literature_binding_interaction_delivery_bindings SET cells_digest=?", (repo._delivery_digest(forged),))
        with pytest.raises(ContractError, match="delivery_binding_mismatch"):
            repo.received_cells(parent)
        store.db.execute("UPDATE literature_binding_interaction_received SET cells=?", (canonical(rows),))
        store.db.execute("UPDATE literature_binding_interaction_delivery_bindings SET cells_digest=?", (repo._delivery_digest(rows),))
        before = list(store.db.iterdump())
        source_artifacts = {store.get(ref)["artifact_ref"] for ref in seed.received_record_refs}
        store.close()
        def forbidden(*_a, **_kw):
            raise AssertionError("saved reconstruction must not read science, calculate, receive again or reprice")
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.read_binding_interaction_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_binding_interaction_storage.populate_binding_interaction", forbidden)
        reopened = Store.__new__(Store)
        reopened.path = (tmp_path / "state").resolve()
        reopened._savepoint = 0
        reopened.db = sqlite3.connect((tmp_path / "state/state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
        reopened.db.row_factory = sqlite3.Row
        try:
            restored = LiteratureBindingInteractionRepository(reopened, run)
            _, rebuilt = service_binding(reopened, child)
            restored_journal = Journal(reopened, run)
            get = reopened.get_artifact
            artifacts = source_artifacts
            monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref in artifacts else get(ref))
            monkeypatch.setattr(Image, "open", forbidden)
            monkeypatch.setattr(restored, "receive_cells", forbidden)
            monkeypatch.setattr(rebuilt.services.literature_binding_interaction_repository(), "receive_cells", forbidden)
            assert rebuilt.received_report_facts(parent)["literature_binding_interaction_cells"] == rows
            assert restored.received_cells(parent) == rows
            rebound = replace(receiver, store=reopened, journal=restored_journal, receive_references=forbidden,
                project_received_credit=forbidden, validate_semantics=forbidden)
            with reopened.read_snapshot():
                assert admit_return(spec, returned, rebound) == admitted
            assert list(reopened.db.iterdump()) == before
            assert reopened.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        finally:
            reopened.db.close()
    finally:
        store.close()


def test_label_masking_uses_actual_location_scope_and_preserves_disjoint_definitions():
    from gene_annotation_episode.literature_binding_interaction_render import overlaps_numbers
    source="source_fixture";record={"source_ref":source,"anchor":None,"label":"safe source header"}
    numeric=[{"kind":"image_region","source_ref":source,"region":[200,10,400,38]}]
    assert overlaps_numbers(record,numeric)
    assert not overlaps_numbers(record,numeric,{"kind":"image_region","source_ref":source,"region":[0,0,150,9]})
    assert overlaps_numbers(record,numeric,{"kind":"image_region","source_ref":source,"region":[0,0,250,20]})
    unknown=[{"kind":"unresolved","source_ref":source}]
    assert overlaps_numbers(record,unknown)
    assert not overlaps_numbers({"source_ref":"source_other","anchor":None,"label":"unrelated"},unknown)
    text={"source_ref":source,"anchor":{"source_ref":source,"start":0,"end":100},"label":"broad text label"}
    assert overlaps_numbers(text,[{"kind":"utf8_span","source_ref":source,"start":20,"end":30}])
    assert not overlaps_numbers(text,[{"kind":"utf8_span","source_ref":source,"start":100,"end":110}])


@pytest.mark.parametrize("requested",["parameter_rr","interaction_ratio"])
@pytest.mark.parametrize("missing_parameter_unit",[False,True])
def test_actual_provider_retains_requested_scalar_qualifiers_and_explicit_interval_units_without_operand_leak(tmp_path,requested,missing_parameter_unit):
    extra="reported CI; lower 0.00123 upper 0.00987; interval unit uM; count at least 73; confidence about 95%"
    from test_literature_binding_interaction_inputs import fixture
    _,_,_,enum,literal,_=fixture(extra=extra)
    def change(args):
        selected=args["roles"][ROLES[0]]
        if missing_parameter_unit:selected["measurement"]["unit"]=None
        selected["uncertainty"].update(statistic=enum("confidence_interval","reported CI"),exact_count=literal("at least 73"),
            confidence_level=literal("about 95%"),interval={"lower":literal("0.00123"),"upper":literal("0.00987"),
                "unit_relationship":enum("explicit_unit","interval unit uM"),"unit":literal("uM")})
    store,context,args=setup(tmp_path/"state",change,expressions=("13.579042","40.12342468","2.213579","4.32468"),extra=extra)
    try:
        repo=LiteratureBindingInteractionRepository(store,context.run_id);out=repo.populate(context,args,"qualified-scalars")
        rows=project(repo,out,[requested]);metadata=rows[0]["roles"][ROLES[0]]
        assert metadata["uncertainty"]["exact_count"]["status"]=="qualified"
        assert metadata["uncertainty"]["exact_count"]["relation"]=="ge"
        assert metadata["uncertainty"]["confidence_level"]["approximate"] is True
        assert metadata["uncertainty"]["confidence_level"]["percent"] is True
        state=snapshot();state["child_reports"]=[{"requested_scalars":rows}];state["requested_form"]=FORM
        state["literature_assignment"]={**plain(context.assignment),"requested_binding_interaction_components":[requested]}
        state["working_state"]={"references":store.list("reference")}
        wire=LiteratureWire(tmp_path/"wire");asyncio.run(complete(wire,state_frame(state)))
        rendered=wire.turns_sent()[0]["input"][0]["text"].split("\n\nSTEERING\n",1)[1]
        if requested=="parameter_rr":
            assert "| exact_count | qualified | ge | false | false | selected_literal | exact |" in rendered
            assert "| confidence_level | qualified | eq | true | true | selected_literal | exact |" in rendered
            assert "Requested interval endpoint reading meanings" in rendered
            assert "| explicit_unit | interpreted | exact | uM | nM | parsed |" in rendered
            assert metadata["values"]["uncertainty"]["exact_count"] is None
            assert metadata["values"]["uncertainty"]["confidence_level"] is None
            assert metadata["values"]["interval_native"]==[.00123,.00987]
            for printed in ("73","95","0.00123","0.00987","13.579042"):assert printed in rendered
        else:
            assert metadata["values"]["delivery_status"]=="not_requested"
            for printed in ("73","95","0.00123","0.00987","13.579042"):assert printed not in rendered
            assert "requested scalar reading meanings" not in rendered
            assert "Requested interval endpoint reading meanings" not in rendered
        for other in ("40.12342468","2.213579","4.32468"):assert other not in rendered
        assert not store.list("observation") and not store.list("assessment")
    finally:store.close()
