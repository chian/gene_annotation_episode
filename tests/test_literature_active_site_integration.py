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
from gene_annotation_episode.literature_active_site_storage import active_site_cells_schema, LiteratureActiveSiteRepository
from gene_annotation_episode.literature_active_site_prompt import ACTIVE_SITE_TASK
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_active_site_inputs import fixture, TEXT
from test_literature_active_site_storage import setup
from test_runtime import FixtureController, ScriptedProvider

COMPONENTS = ["sites_per_total_monomer", "conditional_nominal_to_active_denominator_factor"]
FORM = obj({"requested_times": active_site_cells_schema()})


def binding_for(store, context, *, enabled=True):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, active_site_population=enabled)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_c7_selected_operation_returns_only_explicit_requested_cells_and_preserves_meanings(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        binding = binding_for(store, context)
        assert "literature.active_site.populate" not in {entry["name"] for entry in binding_for(store, context, enabled=False).catalog(context)}
        context = replace(context, assignment={**plain(context.assignment), "requested_active_site_components": COMPONENTS})
        result = asyncio.run(binding.execute(context, "literature.active_site.populate", args, "selected"))
        assert result["status"] == "completed", result
        current = replace(context, received_record_refs=(*context.received_record_refs, *result["record_refs"]))
        facts = binding.facts(current, {"committed_record_refs": result["record_refs"]})
        form = form_with_facts({}, FORM, facts)
        assert [row["component"] for row in form["requested_times"]] == COMPONENTS
        binding.validate_report(current, form, FORM)
        omitted = replace(current, assignment={key: value for key, value in current.assignment.items() if key != "requested_active_site_components"})
        assert binding.facts(omitted, {"committed_record_refs": result["record_refs"]})["literature_active_site_cells"] == []
        with pytest.raises(ReportBoundaryError, match="unrequested"):
            binding.validate_report(omitted, form, FORM)
        parent = replace(current, episode_id="parent", role="annotation", path=(("annotation", "parent"),), assignment={})
        refs = binding.received_form_references(parent, form, FORM, "manual_trusted")
        assert refs and binding.received_report_facts(parent)["literature_active_site_cells"] == form["requested_times"]
        assert binding.as_record()["configuration"]["active_site_population"] is True
    finally:
        store.close()


@pytest.mark.parametrize("requested", [["sites_per_total_monomer"], ["protein_mass_concentration", "sites_per_total_monomer"]])
def test_renderer_check_exact_subset_across_own_history_lookup_and_hypothetical_full_forms(tmp_path, requested):
    # Runtime current_report_update carries interpretations only. Full forms
    # below deliberately exercise the pure renderer's admitted-input grammar.
    n, d = "4.1234567", "67.8765432"
    text = TEXT.replace("4 ng/uL", n + " ng/uL").replace("60 ± 3 nM", d + " ± 3 nM")
    args = fixture(text, mass=(n + " ng/uL", n, "ng/uL"), active=(d + " ± 3 nM", d, "nM"))[0]
    store, context, args = setup(tmp_path, text=text, arguments=args)
    try:
        repo = LiteratureActiveSiteRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        selected = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=requested)
        state = {"literature_experimental_work": {"version": "literature_experimental_task_v1"},
            "literature_active_site_work": {"version": "literature_active_site_task_v1"},
            "literature_assignment": {"requested_active_site_components": requested},
            "last_local_outcome": outcome, "working_state": {}, "requested_form": FORM,
            "child_reports": [{"amounts": selected, "interpretation": "partial"}],
            "current_report_update": {"amounts": selected, "interpretation": "partial"}}
        history = {"result": {"view": "records", "records": [{"selection": {"kind": "tool", "tool": "literature.active_site.populate", "arguments": args},
            "outcome": outcome, "admitted_report": {"amounts": selected, "interpretation": "partial"}}]}}
        prompt = render_literature_experimental_prompt(state, "Evaluate the synthetic active-site amounts.", lookup_results=[history, {"result": {"amounts": selected, "interpretation": "partial"}}])
        task, steering = prompt.split("\n\nSTEERING\n")
        assert ACTIVE_SITE_TASK in task
        assert (n in steering) is ("protein_mass_concentration" in requested)
        assert d not in steering
        assert "55 C" in steering and "Purification also changed" in steering
        assert "regression_sd" in steering and "same_preparation_aliquots" in steering
        assert "partial" in steering and "number_start" not in steering
        assert "active_site_measurement_" not in steering
    finally:
        store.close()


def test_controlled_child_population_parent_return_and_reconstruction_are_single_actions(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    received, controllers = [], []
    assignment = {**plain(context.assignment), "requested_active_site_components": COMPONENTS}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Compare source active-site titration amounts.", "scope": plain(context.scope),
        "purpose": "Return exactly the requested active-site amount components and experimental meanings.",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.active_site.populate", "arguments": args}, "report_update": {}}
    def receives(inputs):
        form, = inputs["child_reports"]
        assert [row["component"] for row in form["requested_times"]] == COMPONENTS
        assert form["requested_times"][0]["value"] == .6
        assert all(operand["reading"] is None for row in form["requested_times"] for operand in row["operands"])
        prompt = render_literature_experimental_prompt(inputs, "Evaluate source active-site amounts.")
        assert ACTIVE_SITE_TASK in prompt.split("\n\nSTEERING\n")[0]
        received.append(form)
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        start = TEXT.index("active sites")
        commit["source_subjects"] = [{"alias": "synthetic_endpoint", "reference_type": "assay", "source_ref": args["source_ref"],
            "label": "active sites", "anchor": {"source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len("active sites"), "quote": "active sites"}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        factories = (partial(LiteratureEpisodes, rate_population=True, active_site_population=True,
            reference_parent_sources=[args["source_ref"]]),)
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs), episode_binding_factories=factories,
            binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1 and summary["credit"] == 0
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_active_site_operations").fetchone()[0] == 1
        assert not store.list("observation") and not store.list("assessment")
        runtime_run = store.db.execute("SELECT run_id FROM literature_active_site_operations").fetchone()[0]
        parent_episode = store.db.execute("SELECT episode_id FROM literature_active_site_received").fetchone()[0]
        source_artifact = store.get(args["source_ref"])["artifact_ref"]
        outcome_row = store.db.execute("SELECT outcome FROM literature_active_site_operations").fetchone()[0]
        sheet_ref = json.loads(outcome_row)["result"]["sheet_ref"]
        original_get = store.get_artifact
        def guarded(reference):
            assert reference != source_artifact, "reconstruction cannot reacquire original source"
            return original_get(reference)
        monkeypatch.setattr(store, "get_artifact", guarded)
        def forbidden(*args, **kwargs):
            raise AssertionError("reconstruction cannot reinterpret scientific source")
        monkeypatch.setattr("gene_annotation_episode.literature_active_site_storage.read_active_site_inputs", forbidden)
        repo = LiteratureActiveSiteRepository(store, runtime_run)
        parent = replace(context, run_id=runtime_run, episode_id=parent_episode, role="annotation", path=(("annotation", parent_episode),), assignment={}, received_record_refs=(sheet_ref,))
        assert repo.received_cells(parent) == received[0]["requested_times"]
        assert repo.fact_cells(parent, [sheet_ref], components=list(repo.components)) == received[0]["requested_times"]
    finally:
        store.close()


def test_mixed_active_site_and_existing_native_rate_view_keep_both_scientific_families(tmp_path):
    from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository
    from gene_annotation_episode.literature_rate_meaning_delivery import source_meaning_projection
    from test_literature_rate_native_storage import setup_native_store
    store, context, args = setup(tmp_path / "times")
    rate_store, rate_context, rate_args = setup_native_store(tmp_path / "rates")
    try:
        repo = LiteratureActiveSiteRepository(store, context.run_id)
        outcome = repo.populate(context, args, "selected")
        times = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"], components=["sites_per_total_monomer"])
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
        assert steering.count("Requested active-site titration amount components") == 4
        assert steering.count("Requested native source-rate components") == 4
        assert "enzyme Alpha" in steering and "enzyme Beta" in steering
        assert "Purification also changed" in steering and "Reference − test rate" in steering
    finally:
        store.close()
        rate_store.close()


def test_disabled_binding_preserves_contracts_and_enabled_descriptor_hashes_dependencies(tmp_path, monkeypatch):
    from pathlib import Path
    store, context, args = setup(tmp_path)
    try:
        binding = binding_for(store, context)
        disabled = binding_for(store, context, enabled=False)
        default = LiteratureEpisodes(disabled.services, rate_population=True)
        assert disabled.catalog(context) == default.catalog(context)
        assert disabled.assignment_schema("literature") == default.assignment_schema("literature")
        assert "requested_active_site_components" not in disabled.assignment_schema("literature")["properties"]
        assert "literature_active_site_cells" not in disabled.fact_sources("literature")
        assert "active_site_population" not in disabled.as_record()["configuration"]
        original = binding.as_record()
        rebound = LiteratureEpisodes(binding.services, **original["configuration"])
        assert rebound.as_record() == original
        read_bytes = Path.read_bytes
        dependencies = ("literature_active_site_inputs.py", "literature_active_site_calculations.py", "literature_active_site_storage.py",
            "literature_active_site_render.py", "literature_active_site_prompt.py", "literature_product_partition_inputs.py",
            "literature_rate_native_inputs.py", "literature_partner_source_fields.py", "literature_assay_inputs.py", "literature_rate_domains.py")
        for selected in dependencies:
            def altered(path, selected=selected):
                data = read_bytes(path)
                return data + b"\n# virtual dependency hash contrast\n" if path.name == selected else data
            monkeypatch.setattr(Path, "read_bytes", altered)
            assert binding.as_record()["implementation_sha256"] != original["implementation_sha256"], selected
        monkeypatch.setattr(Path, "read_bytes", read_bytes)
        store.db.execute("PRAGMA query_only=ON")
        assert rebound.as_record() == original
        repo = rebound._active_site_repository()
        assert not repo._installed(repo.operations_table)
    finally:
        store.close()


def test_enabled_reference_parent_keeps_complete_active_site_task(tmp_path):
    store, context, args = setup(tmp_path)
    try:
        binding = LiteratureEpisodes(binding_for(store, context).services, rate_population=True,
            active_site_population=True, reference_parent_sources=[args["source_ref"]])
        parent = replace(context, role="annotation", path=(("annotation", context.episode_id),), assignment={})
        state = binding.initial_decision_context(parent)
        state.update(working_state={}, goal={"objective": "Evaluate source active-site amount."})
        task, steering = render_literature_experimental_prompt(state, "Evaluate source active-site amount.").split("\n\nSTEERING\n")
        assert ACTIVE_SITE_TASK in task
        assert "one functional site per protein monomer" in task
        assert "nominal titrant concentration" in task
    finally:
        store.close()
