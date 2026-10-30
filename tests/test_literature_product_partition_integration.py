"""Selected primary spans and controlled shared Episode integration."""
import asyncio
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_product_partition_prompt import PRODUCT_PARTITION_TASK
from gene_annotation_episode.literature_product_partition_storage import LiteratureProductPartitionRepository, product_partition_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_product_partition_inputs import fixture, PRIMARY, TEXT
from test_literature_product_partition_storage import setup
from test_runtime import FixtureController, ScriptedProvider

COMPONENTS = ["selected_fraction_sum", "partition_a_over_b"]
FORM = obj({"partition": product_partition_cells_schema()})


def binding_for(store, context, enabled=True):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, product_partition_population=enabled)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_original_source_selected_population_c7_exact_return_and_default_exclusion(tmp_path):
    raw = PRIMARY.read_bytes()
    args = fixture(raw, primary=True)[0]
    store, context, args = setup(tmp_path, raw=raw, arguments=args)
    try:
        binding = binding_for(store, context)
        legacy = binding_for(store, context, False)
        assert "literature.product_partition.populate" not in {row["name"] for row in legacy.catalog(context)}
        assert "product_partition_population" not in legacy.as_record()["configuration"]
        assert "requested_product_partition_components" not in legacy.assignment_schema("literature")["properties"]
        context = replace(context, assignment={**plain(context.assignment), "requested_product_partition_components": COMPONENTS})
        outcome = asyncio.run(binding.execute(context, "literature.product_partition.populate", args, "selected"))
        assert outcome["status"] == "completed", outcome
        assert [row["component"] for row in outcome["result"]["cells"]] == COMPONENTS
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        facts = binding.facts(current, {"committed_record_refs": outcome["record_refs"]})
        form = form_with_facts({}, FORM, facts)
        assert [row["value"] for row in form["partition"]] == [1, pytest.approx(.603 / .397)]
        binding.validate_report(current, form, FORM)
        omitted = replace(current, assignment={key: value for key, value in current.assignment.items() if key != "requested_product_partition_components"})
        assert binding.facts(omitted, {"committed_record_refs": outcome["record_refs"]})["literature_product_partition_cells"] == []
        with pytest.raises(ReportBoundaryError, match="unrequested"):
            binding.validate_report(omitted, form, FORM)
        parent = replace(current, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
        refs = binding.received_form_references(parent, form, FORM, "trusted_manual_delivery")
        assert refs and binding.received_report_facts(parent)["literature_product_partition_cells"] == form["partition"]
        assert binding.as_record()["configuration"]["product_partition_population"] is True
    finally: store.close()


def test_full_scientific_task_and_exact_subset_in_current_own_history_lookup_and_mixed_return(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        context = replace(context, assignment={**plain(context.assignment), "requested_product_partition_components": ["selected_fraction_sum"]})
        repo = LiteratureProductPartitionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        rows = outcome["result"]["cells"]
        records = [store.get(ref) for ref in repo.cell_record_refs(rows) if store.get(ref)["record_type"] == "reference"]
        state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
            "literature_product_partition_work": {"version": "literature_product_partition_task_v1"},
            "literature_assignment": plain(context.assignment), "last_local_outcome": outcome,
            "working_state": {"references": records}, "requested_form": FORM,
            "child_reports": [{"partition": rows, "interpretation": "partial"}],
            "current_report_update": {"partition": rows, "interpretation": "partial"}}
        history = {"result": {"view": "records", "records": [{"selection": {"kind": "tool", "tool": "literature.product_partition.populate", "arguments": args},
            "outcome": outcome, "admitted_report": {"partition": rows, "interpretation": "partial"}}]}}
        prompt = render_literature_experimental_prompt(state, "Evaluate the synthetic composition experiment.", lookup_results=[history, {"result": {"partition": rows, "interpretation": "partial"}}])
        task, steering = prompt.split("\n\nSTEERING\n")
        assert PRODUCT_PARTITION_TASK in task
        assert "60.3" not in steering and "39.7" not in steering and "0.603" not in steering and "0.397" not in steering
        assert "R5P" in steering and "Ru5P" in steering and "partial" in steering
        assert "number_start" not in steering and "partition_subject_" not in steering
        assert "withheld unrequested numbers" in steering
        without = {key: value for key, value in state.items() if key != "literature_product_partition_work"}
        assert PRODUCT_PARTITION_TASK not in render_literature_experimental_prompt(without, "Evaluate the experiment.").split("\n\nSTEERING\n")[0]
    finally: store.close()


def test_controlled_child_population_parent_return_one_action_and_source_free_reconstruction(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    assignment = {**plain(context.assignment), "requested_product_partition_components": COMPONENTS}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Evaluate the selected reported product composition.", "scope": plain(context.scope),
        "purpose": "Return only requested partition components and their meanings.",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.product_partition.populate", "arguments": args}, "report_update": {}}
    received, controllers = [], []
    def receives(inputs):
        form, = inputs["child_reports"]
        assert [row["component"] for row in form["partition"]] == COMPONENTS
        assert form["partition"][0]["value"] == 1
        received.append(form)
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        start = TEXT.index(b"Equilibrium")
        commit["source_subjects"] = [{"alias": "synthetic_partition_endpoint", "reference_type": "assay",
            "source_ref": args["source_ref"], "label": "Equilibrium", "anchor": {
                "source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len("Equilibrium"), "quote": "Equilibrium"}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        factories = (partial(LiteratureEpisodes, rate_population=True, product_partition_population=True,
            reference_parent_sources=[args["source_ref"]]),)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=factories,
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_product_partition_operations").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        run_id, = store.db.execute("SELECT run_id FROM literature_product_partition_operations").fetchone()
        episode_id, = store.db.execute("SELECT episode_id FROM literature_product_partition_received").fetchone()
        artifact = store.get(args["source_ref"])["artifact_ref"]
        original = store.get_artifact
        def get(ref):
            assert ref != artifact, "Reconstruction cannot reread scientific source"
            return original(ref)
        monkeypatch.setattr(store, "get_artifact", get)
        monkeypatch.setattr("gene_annotation_episode.literature_product_partition_storage.read_product_partition_inputs", lambda *a, **k: pytest.fail("Source reader rerun"))
        repo = LiteratureProductPartitionRepository(store, run_id)
        parent = replace(context, run_id=run_id, episode_id=episode_id, role="annotation", path=(("annotation", episode_id),),
            assignment={}, received_record_refs=(received[0]["partition"][0]["sheet_ref"],))
        store.db.execute("PRAGMA query_only=ON")
        assert repo.received_cells(parent) == received[0]["partition"]
        assert repo.fact_cells(parent, [received[0]["partition"][0]["sheet_ref"]], components=list(repo.components)) == received[0]["partition"]
    finally: store.close()
