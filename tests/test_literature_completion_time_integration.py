"""Controlled shared Episode work and deterministic subset presentation tests."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_completion_time_storage import completion_time_cells_schema, LiteratureCompletionTimeRepository
from gene_annotation_episode.literature_completion_time_prompt import COMPLETION_TIME_TASK
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_completion_time_inputs import fixture, TEXT
from test_literature_completion_time_storage import setup
from test_runtime import FixtureController, ScriptedProvider

COMPONENTS = ["completion_time_ratio", "inverse_completion_time_ratio"]
FORM = obj({"requested_times": completion_time_cells_schema()})


def binding_for(store, context, *, enabled=True):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, completion_time_population=enabled)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_c7_selected_operation_returns_only_explicit_requested_cells_and_preserves_meanings(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        binding = binding_for(store, context)
        assert "literature.completion_time.populate" not in {entry["name"] for entry in binding_for(store, context, enabled=False).catalog(context)}
        context = replace(context, assignment={**plain(context.assignment), "requested_completion_time_components": COMPONENTS})
        result = asyncio.run(binding.execute(context, "literature.completion_time.populate", args, "selected"))
        assert result["status"] == "completed", result
        current = replace(context, received_record_refs=(*context.received_record_refs, *result["record_refs"]))
        facts = binding.facts(current, {"committed_record_refs": result["record_refs"]})
        form = form_with_facts({}, FORM, facts)
        assert [row["component"] for row in form["requested_times"]] == COMPONENTS
        binding.validate_report(current, form, FORM)
        omitted = replace(current, assignment={key: value for key, value in current.assignment.items() if key != "requested_completion_time_components"})
        assert binding.facts(omitted, {"committed_record_refs": result["record_refs"]})["literature_completion_time_cells"] == []
        with pytest.raises(ReportBoundaryError, match="unrequested"):
            binding.validate_report(omitted, form, FORM)
        parent = replace(current, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
        refs = binding.received_form_references(parent, form, FORM, "manual_trusted")
        assert refs and binding.received_report_facts(parent)["literature_completion_time_cells"] == form["requested_times"]
        assert binding.as_record()["configuration"]["completion_time_population"] is True
    finally:
        store.close()


@pytest.mark.parametrize("requested", [["completion_time_ratio"], ["numerator_time", "completion_time_ratio"]])
def test_prompt_exact_subset_across_own_history_lookup_current_and_mixed_returns(tmp_path, requested):
    n, d = "53.1234567", "7.8765432"
    text = TEXT.replace("18 h", n + " h").replace("10 min", d + " min")
    args = fixture(text, first=n + " h", second=d + " min", n=n, d=d)[0]
    store, context, args = setup(tmp_path, text=text, arguments=args)
    try:
        repo = LiteratureCompletionTimeRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        selected = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=requested)
        state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
            "literature_completion_time_work": {"version": "literature_completion_time_task_v1"},
            "literature_assignment": {"requested_completion_time_components": requested},
            "last_local_outcome": outcome, "working_state": {}, "requested_form": FORM,
            "child_reports": [{"timings": selected, "interpretation": "partial"}],
            "current_report_update": {"timings": selected, "interpretation": "partial"}}
        history = {"result": {"view": "records", "records": [{"selection": {"kind": "tool", "tool": "literature.completion_time.populate", "arguments": args},
            "outcome": outcome, "admitted_report": {"timings": selected, "interpretation": "partial"}}]}}
        prompt = render_literature_experimental_prompt(state, "Evaluate the synthetic timing comparison.", lookup_results=[history, {"result": {"timings": selected, "interpretation": "partial"}}])
        task, steering = prompt.split("\n\nSTEERING\n")
        assert COMPLETION_TIME_TASK in task
        assert (n in steering) is ("numerator_time" in requested)
        assert d not in steering
        assert "purification" in steering and "Heat also changed" in steering
        assert "partial" in steering
        assert "completion_time_measurement_" not in steering
        assert "molecular activity retention" in steering
        assert "number_start" not in steering
        assert "interpretation" in steering  # Mixed-form sibling not dropped.
    finally:
        store.close()


def test_controlled_child_population_parent_return_and_reconstruction_are_single_actions(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    received, controllers = [], []
    assignment = {**plain(context.assignment), "requested_completion_time_components": COMPONENTS}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Compare source preparation equilibration times.", "scope": plain(context.scope),
        "purpose": "Return exactly the requested endpoint-time components and experimental meanings.",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.completion_time.populate", "arguments": args}, "report_update": {}}
    def receives(inputs):
        form, = inputs["child_reports"]
        assert [row["component"] for row in form["requested_times"]] == COMPONENTS
        assert form["requested_times"][0]["reported_domain"]["lower"] == 108
        assert all(operand["reading"] is None for row in form["requested_times"] for operand in row["operands"])
        prompt = render_literature_experimental_prompt(inputs, "Evaluate preparation timing.")
        assert COMPLETION_TIME_TASK in prompt.split("\n\nSTEERING\n")[0]
        received.append(form)
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        start = TEXT.index("equilibrium")
        commit["source_subjects"] = [{"alias": "synthetic_endpoint", "reference_type": "assay", "source_ref": args["source_ref"],
            "label": "equilibrium", "anchor": {"source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len("equilibrium"), "quote": "equilibrium"}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        factories = (partial(LiteratureEpisodes, rate_population=True, completion_time_population=True,
            reference_parent_sources=[args["source_ref"]]),)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=factories,
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_completion_time_operations").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        runtime_run = store.db.execute("SELECT run_id FROM literature_completion_time_operations").fetchone()[0]
        parent_episode = store.db.execute("SELECT episode_id FROM literature_completion_time_received").fetchone()[0]
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        outcome_row = store.db.execute("SELECT outcome FROM literature_completion_time_operations").fetchone()[0]
        sheet_ref = json.loads(outcome_row)["result"]["sheet_ref"]
        original_get = store.get_artifact
        def guarded(reference):
            assert reference != source_artifact, "reconstruction cannot reacquire original source"
            return original_get(reference)
        monkeypatch.setattr(store, "get_artifact", guarded)
        def forbidden(*args, **kwargs):
            raise AssertionError("reconstruction cannot reinterpret scientific source")
        monkeypatch.setattr("gene_annotation_episode.literature_completion_time_storage.read_completion_time_inputs", forbidden)
        repo = LiteratureCompletionTimeRepository(store, runtime_run)
        parent = replace(context, run_id=runtime_run, episode_id=parent_episode, role="annotation", path=(("annotation", parent_episode),), assignment={}, received_record_refs=(sheet_ref,))
        assert repo.received_cells(parent) == received[0]["requested_times"]
        assert repo.fact_cells(parent, [sheet_ref], components=list(repo.components)) == received[0]["requested_times"]
    finally:
        store.close()


def test_mixed_completion_time_and_existing_native_rate_view_keep_both_scientific_families(tmp_path):
    from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
    from gene_annotation_episode.literature_rate_meaning_delivery import source_meaning_projection
    from test_literature_rate_native_storage import setup_native_store
    store, context, args = setup(tmp_path / "times")
    rate_store, rate_context, rate_args = setup_native_store(tmp_path / "rates")
    try:
        repo = LiteratureCompletionTimeRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        times = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=["completion_time_ratio"])
        rates = LiteratureRateRepository(rate_store, rate_context.run_id)
        rate_result = rates.populate_native(rate_context, rate_args, "selected")
        native = source_meaning_projection(rates).project_cells([rate_result["result"]["sheet_ref"]],
            permitted_record_refs=rate_result["record_refs"], components=["rate_difference"])
        records = {row["id"]: row for kind in ("reference", "context", "term") for row in rate_store.list(kind)}
        mixed = {"requested_times": times, "existing_rates": native, "interpretation": "partial"}
        state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
            "working_state": {}, "child_reports": [mixed], "current_report_update": mixed,
            "literature_received_fact_display": {"records": records, "received_refs": list(records)}}
        direct = {"result": mixed}
        history = {"result": {"view": "records", "records": [{"admitted_report": mixed}]}}
        steering = render_literature_experimental_prompt(state, "Compare the source evidence.",
            lookup_results=[direct, history]).split("\n\nSTEERING\n")[1]
        assert steering.count("Requested preparation completion-time components") == 4
        assert steering.count("Requested native source-rate components") == 4
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "purification" in steering and "Reference − test rate" in steering
    finally:
        store.close()
        rate_store.close()
