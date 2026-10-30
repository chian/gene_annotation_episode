"""Selected ordinary episode kinetic model work, using synthetic fixtures only."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt, EXPERIMENTAL_TASK
from gene_annotation_episode.literature_kinetic_model_storage import COMPONENTS, kinetic_model_cells_schema
from gene_annotation_episode.literature_kinetic_model_prompt import KINETIC_MODEL_TASK
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_kinetic_model_inputs import setup_model
from test_literature_kinetic_model_storage import populate
from test_runtime import FixtureController, ScriptedProvider


def binding_for(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


@pytest.mark.parametrize("status", ["known", "estimated"])
def test_selected_child_to_parent_model_subset_and_ordinary_observations(tmp_path, status):
    store, context, args, model_args, _, _ = setup_model(tmp_path / "state", status=status)
    controllers, received = [], []
    selected = ["log_contrast_standard_uncertainty", "source_signed_index"]
    form = obj({"kinetic_precision": kinetic_model_cells_schema()})
    try:
        assignment = {**plain(context.assignment), "requested_kinetic_model_components": selected}
        commission = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Evaluate the supplied synthetic kinetic parameter contrast using its explicit retained log model.",
            "scope": plain(context.scope), "purpose": "Return the requested precision and conditional source contrast index.",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}
        native = {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": args}, "report_update": {}}
        def model_action(inputs):
            prior = inputs["last_local_outcome"]
            assert prior["status"] == "completed"
            return {"selection": {"kind": "tool", "tool": "literature.kinetic.model.populate",
                "arguments": {**model_args, "source_ref": prior["result"]["sheet_ref"]}}, "report_update": {}}
        def receive(inputs):
            report, = inputs["child_reports"]
            received.append(report)
            rows = report["kinetic_precision"]
            assert [row["component"] for row in rows] == selected
            assert rows[0]["value"] == pytest.approx(.33166247903553997)
            assert rows[1]["value"] == (pytest.approx(.7975846370428177) if status == "known" else None)
            assert rows[1]["unavailable_reason"] == (None if status == "known" else "known_log_covariance_required")
            assert rows[1]["numerator"]["parameter_kind"] == "Km"
            assert rows[1]["numerator"]["uncertainty_values"]["delivery_status"] == "not_requested"
            assert all(row["variance_status"] == status for row in rows)
            paper = store.get(args["source_ref"])
            raw = store.get_artifact(paper["artifact_ref"])
            commit = {name: [] for name in store.reasoning_schema()["required"]}
            commit["source_subjects"] = [{"alias": "synthetic_source", "reference_type": "assay", "source_ref": paper["id"],
                "label": "ProteinFixture", "anchor": {"source_ref": paper["id"], "artifact_ref": paper["artifact_ref"],
                    "start": 0, "end": len(raw), "quote": raw.decode()}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([commission, native, model_action, receive]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),), binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert [value.scores for value in controllers] == [[0,0], [0,0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_model_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_model_received").fetchone()[0] == 1
    finally:
        store.close()


def test_catalog_dispatch_page_ancestry_and_exact_return_request(tmp_path):
    store, context, args, model_args, _, _ = setup_model(tmp_path)
    with store:
        binding = binding_for(store, context)
        assert "literature.kinetic.model.populate" in {row["name"] for row in binding.catalog(context)}
        native = asyncio.run(binding.execute(context, "literature.kinetic.populate", args, "native"))
        owner = replace(context, received_record_refs=(*context.received_record_refs, *native["record_refs"]),
            assignment={**context.assignment, "requested_kinetic_model_components":["source_signed_index"]})
        model_args["source_ref"] = native["result"]["sheet_ref"]
        modeled = asyncio.run(binding.execute(owner, "literature.kinetic.model.populate", model_args, "model"))
        assert modeled["status"] == "completed", modeled
        owner = replace(owner, received_record_refs=(*owner.received_record_refs, *modeled["record_refs"]))
        facts = binding.facts(owner, {"committed_record_refs":[modeled["result"]["sheet_ref"]]})
        form = obj({"selected":kinetic_model_cells_schema()})
        returned = form_with_facts({}, form, facts)
        assert [r["component"] for r in returned["selected"]] == ["source_signed_index"]
        binding.validate_report(owner, returned, form)
        forged = deepcopy(returned); forged["selected"][0]["value"] = .8
        with pytest.raises(Exception, match="differs_from_saved"):
            binding.validate_report(owner, forged, form)
        # A different retained source is globally known and received, but it is
        # outside the selected page's actual source ancestry.
        other = store.put("source", {"provider":"synthetic_unrelated", "accession":None,"uri":None,
            "artifact_ref":store.artifact("unrelated", "text/plain"),"text_ref":None,"request_ref":None,"version":None,"retrieved_at":None},origin="caller")
        page = {"version":"page_assignment_v1", "source_ref":other["id"], "representation":"original",
            "artifact_ref":other["artifact_ref"], "question_context_refs":[], "prior_delivery_refs":[]}
        wrong = replace(owner, role="literature_page", path=(("literature_page","wrong"),), assignment=page,
            received_record_refs=(*owner.received_record_refs, other["id"]))
        failure = asyncio.run(binding.execute(wrong, "literature.kinetic.model.populate", model_args, "wrong-page"))
        assert failure["status"] == "invalid" and failure["feedback"]["code"] == "literature_reading_outside_assigned_source"


@pytest.mark.parametrize("foreign", ["model", "witness"])
def test_model_and_its_support_must_each_descend_from_selected_page(tmp_path, foreign):
    store, context, args, model_args, _, _ = setup_model(tmp_path)
    with store:
        binding = binding_for(store,context)
        native = asyncio.run(binding.execute(context,"literature.kinetic.populate",args,"native"))
        root = store.get(args["source_ref"])
        page = {"version":"page_assignment_v1", "source_ref":root["id"],"representation":"original",
            "artifact_ref":root["artifact_ref"],"question_context_refs":[],"prior_delivery_refs":[]}
        owner = replace(context,role="literature_page",path=(("literature_page","root"),),assignment=page,
            received_record_refs=(*context.received_record_refs,*native["record_refs"]))
        model_args["source_ref"] = native["result"]["sheet_ref"]
        valid = asyncio.run(binding.execute(owner,"literature.kinetic.model.populate",model_args,"valid-page"))
        assert valid["status"] == "completed",valid
        source_ref = model_args["model_source_ref"] if foreign == "model" else model_args["model_witnesses"][0]["source_ref"]
        original = store.get(source_ref)
        value = {k:v for k,v in original.items() if k not in ("id","record_type","origin")}
        value.update(provider="synthetic_outside_page",parent_source_refs=[])
        external = store.put("source",value,origin="caller")["id"]
        if foreign == "model":
            model_args["model_source_ref"] = external
        else:
            model_args["model_witnesses"][0]["source_ref"] = external
        owner = replace(owner,received_record_refs=(*owner.received_record_refs,external))
        failed = asyncio.run(binding.execute(owner,"literature.kinetic.model.populate",model_args,"foreign-page"))
        assert failed["status"] == "invalid" and failed["feedback"]["code"] == "literature_reading_outside_assigned_source"


def test_full_task_recurs_and_model_rows_do_not_expand_private_numbers(tmp_path):
    from test_literature_experimental_prompt_delivery import snapshot
    store, context, args, model_args, _, _ = setup_model(tmp_path)
    with store:
        context = replace(context, assignment={**context.assignment,"requested_kinetic_model_components":["source_signed_index"]})
        repo, owner, _, outcome, _ = populate(store, context, args, model_args)
        reference = outcome["result"]["sheet_ref"]
        rows = repo.fact_cells(owner,[reference],components=["source_signed_index"])
        records = {ref:store.get(ref) for ref in outcome["record_refs"] if ref.startswith("reference_")}
        support = store.get(rows[0]["model_support_refs"][0])
        alias_value = {k:v for k,v in support.items() if k not in ("id","record_type","origin")}
        alias_value.update(accession="synthetic_support_alias", label="PRIVATE_COVARIANCE_ALIAS_0.04_0.01_0.09")
        alias = store.put("reference", alias_value, origin="tool", scope=plain(context.scope))
        records[alias["id"]] = alias
        model_source = store.get(model_args["model_source_ref"])
        model_bytes = store.get_artifact(model_source["artifact_ref"])
        model_alias_value = {**alias_value, "source_ref":model_source["id"], "accession":"synthetic_model_bytes_alias",
            "label":"PRIVATE_MODEL_BYTES_ALIAS_0.04_0.01_0.09", "anchor":{"source_ref":model_source["id"],
                "artifact_ref":model_source["artifact_ref"], "start":0,"end":len(model_bytes),"quote":model_bytes.decode()}}
        model_alias = store.put("reference",model_alias_value,origin="tool",scope=plain(context.scope))
        records[model_alias["id"]] = model_alias
        state = snapshot()
        state["literature_assignment"] = plain(context.assignment)
        state["literature_assignment"]["question_context_refs"] = [alias["id"],model_alias["id"]]
        state["literature_received_fact_display"] = {"records":records,"received_refs":list(records)}
        state["last_local_outcome"] = outcome
        first = render_literature_experimental_prompt(state,"Evaluate the supplied source kinetic comparison.")
        parent = deepcopy(state)
        parent.pop("last_local_outcome")
        parent["child_reports"] = [{"only_index":rows}]
        second = render_literature_experimental_prompt(parent,"Evaluate the supplied source kinetic comparison.")
        lookup_state = deepcopy(state)
        lookup_state.pop("last_local_outcome")
        third = render_literature_experimental_prompt(lookup_state,"Evaluate the supplied source kinetic comparison.",
            lookup_results=[{"status":"completed","result":outcome["result"]}])
        assert first.split("\n\nSTEERING\n")[0] == second.split("\n\nSTEERING\n")[0]
        assert first.split("\n\nSTEERING\n")[0] == third.split("\n\nSTEERING\n")[0]
        assert EXPERIMENTAL_TASK in first and EXPERIMENTAL_TASK in second
        assert first.count(KINETIC_MODEL_TASK) == 1 and second.count(KINETIC_MODEL_TASK) == 1
        for text in (first,second,third):
            steering = text.split("\n\nSTEERING\n")[1]
            assert "source_signed_index" in steering and ".797584" in steering
            assert "known_normal_log_parameters" in steering and "synthetic" in steering
            assert "numerator_parameter_exceeds_denominator" in steering
            assert "measurement_keys" not in steering and "covariance\"" not in steering
            assert "20 uM" not in steering and "10 uM" not in steering
            assert "2.183877" not in steering and "0.331662" not in steering
            assert "PRIVATE_COVARIANCE_ALIAS" not in steering
            assert "PRIVATE_MODEL_BYTES_ALIAS" not in steering
            assert "Cnn 0.04" not in steering
