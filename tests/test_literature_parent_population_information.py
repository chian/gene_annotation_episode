"""Synthetic capability information, real C7/provider paths; no model inference."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, ROLES, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import SAVED_NUMERICAL_RETURN_TASK
from gene_annotation_episode.literature_rate_storage import rate_cells_schema
from gene_annotation_episode.literature_reference_parent_prompt import (
    REFERENCE_PARENT_TASK, render_reference_evidence_parent_prompt,
)
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_experimental_prompt_delivery import (
    LiteratureWire, OUTPUT_SCHEMA, complete, snapshot,
)
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_storage import setup_store
from test_runtime import FixtureController, ScriptedProvider


EVIDENCE = (Path(__file__).resolve().parents[1] / "verification" /
    "literature_reference_evidence_2026-10-25_001/parent_population_information_023")
BASELINE_SHA256 = "cf6c09e480151012122c232641bad514bd4a2ab20ca4cc5a3af27f240e9a5faa"
TABLE_TITLE = "Population operations available within literature children"


def baseline():
    """Captured from the contract's original ddabb6d6 C7 implementation."""
    raw = (EVIDENCE / "population_catalog_before.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == BASELINE_SHA256
    return json.loads(raw)


def current_baseline():
    """Retain the fourteen historical operations and their current input guidance."""
    from gene_annotation_episode.literature_partner_native_inputs import partner_source_population_schema
    from gene_annotation_episode.literature_partner_operand_information import partner_source_population_schema_with_information
    rows = baseline()
    partner, = [row for row in rows if row["name"] == "literature.partner.source.populate"]
    assert partner["input_schema"] == partner_source_population_schema()
    partner["input_schema"] = partner_source_population_schema_with_information()
    reaction, = [row for row in rows if row["name"] == "literature.reaction.populate"]
    assert reaction["description"] == 'Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget components from an explicitly retained received dataset. Preserve unknown replication, missing alternatives and incomplete resource constraints. Product-pair ratios, supplied reagent budgets and usable capacity have distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing corrections or calculate target transfer/annotation credit.'
    reaction["description"] = 'Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget components from an explicitly retained received dataset or native source-selection recipe. Read exact report ratio points or author a:b expressions, summary uncertainty/counts and simple resource quantities with source units. Preserve unknown replication, missing alternatives, calibration basis and incomplete resource constraints. Product-pair ratios, instrument signals, supplied reagent budgets and usable capacity have distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing corrections or calculate target transfer/annotation credit.'
    return rows


def native_addition():
    """Only the new operation is additive; the historical fixture stays exact."""
    from gene_annotation_episode.literature_native_rate_operand_information import rate_source_population_schema_with_information
    entry, = [row for row in _population_catalog() if row["name"] == "literature.rate.source.populate"]
    assert entry["input_schema"] == rate_source_population_schema_with_information()
    assert "without a prepared CSV/TSV" in entry["description"]
    assert "Source-defined U/mg" in entry["description"]
    return entry


def amount_addition():
    """The A105 amount component operation is additive to baseline and024."""
    from gene_annotation_episode.literature_amount_inputs import amount_arguments_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.amount.populate"]
    assert entry["input_schema"] == amount_arguments_schema()
    assert "mass-fraction estimates" in entry["description"]
    return entry


def optical_addition():
    """Optical adds only existing q/Vq input population to the sixteen entries."""
    from gene_annotation_episode.literature_optical_inputs import optical_arguments_schema
    from gene_annotation_episode.literature_optical_storage import optical_cells_schema
    from gene_annotation_episode.communication import validate_closed_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.optical.populate"]
    assert entry["input_schema"] == optical_arguments_schema()
    assert "NADH-depletion" in entry["description"]
    validate_closed_schema(obj({"optical": optical_cells_schema()}))
    return entry


def kinetic_addition():
    """Native kinetic contrast is an additive finite A105 component route."""
    from gene_annotation_episode.literature_kinetic_inputs import kinetic_arguments_schema
    from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema
    from gene_annotation_episode.communication import validate_closed_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.kinetic.populate"]
    assert entry["input_schema"] == kinetic_arguments_schema()
    assert "no covariance/model source reader" in entry["description"]
    validate_closed_schema(obj({"kinetic": kinetic_cells_schema()}))
    return entry


def kinetic_model_addition():
    """The optional kinetic log-model operation preserves the native fixture."""
    from gene_annotation_episode.literature_kinetic_model_storage import kinetic_model_population_schema, kinetic_model_cells_schema
    from gene_annotation_episode.communication import validate_closed_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.kinetic.model.populate"]
    assert entry["input_schema"] == kinetic_model_population_schema()
    assert "actually received committed native kinetic sheet" in entry["description"]
    assert "Reported SD/SEM/counts never supply covariance" in entry["description"]
    validate_closed_schema(obj({"kinetic_model": kinetic_model_cells_schema()}))
    return entry


def interaction_addition():
    """The four-cell source binding comparison is a separate additive operation."""
    from gene_annotation_episode.literature_binding_interaction_inputs import binding_interaction_arguments_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.binding.interaction.populate"]
    assert entry["input_schema"] == binding_interaction_arguments_schema()
    assert "four selected original-image binding cells" in entry["description"]
    return entry


def interaction_model_addition():
    """Prepared-model supplemental operation leaves the frozen native route intact."""
    from gene_annotation_episode.literature_binding_interaction_model_storage import binding_interaction_model_population_schema, binding_interaction_model_cells_schema
    from gene_annotation_episode.communication import validate_closed_schema
    entry, = [row for row in _population_catalog() if row["name"] == "literature.binding.interaction.model.populate"]
    assert entry["input_schema"] == binding_interaction_model_population_schema()
    assert "actually received committed native interaction sheet" in entry["description"]
    assert "No paper-covariance packet producer" in entry["description"]
    validate_closed_schema(obj({"interaction_model": binding_interaction_model_cells_schema()}))
    return entry


def enabled_parent(store, child, source):
    services, _ = service_binding(store, child)
    binding = LiteratureEpisodes(services, rate_population=True,
        reference_parent_sources=[source])
    parent = replace(child, role="annotation", episode_id="source-parent",
        path=(("annotation", "root"),), assignment={})
    return binding, parent


def split(text):
    assert text.count("\n\nSTEERING\n") == 1
    return text.split("\n\nSTEERING\n")


@pytest.mark.parametrize("role", ROLES)
def test_all_child_population_entries_schemas_and_order_equal_prechange_catalog(tmp_path, role):
    store, child, args = setup_store(tmp_path)
    try:
        binding, _ = enabled_parent(store, child, args["source_ref"])
        context = replace(child, role=role, path=((role, "synthetic-catalog"),))
        services = binding.services
        disabled = LiteratureEpisodes(services)
        ordinary = disabled.catalog(context)
        expected = ordinary + current_baseline() + [native_addition(), amount_addition(), optical_addition(), kinetic_addition(), kinetic_model_addition(), interaction_addition(), interaction_model_addition()]
        before = deepcopy(expected)
        assert binding.catalog(context) == expected
        # No schema aliasing between separate catalog construction calls.
        changed = binding.catalog(context)
        changed[-1]["input_schema"].clear()
        assert binding.catalog(context) == before
        assert not any(row["name"].startswith("literature.") for row in ordinary)
    finally:
        store.close()


def test_explicit_initial_metadata_reconstructs_without_execution_or_episode_identity(tmp_path, monkeypatch):
    store, child, args = setup_store(tmp_path)
    try:
        binding, parent = enabled_parent(store, child, args["source_ref"])
        registry = EpisodeBindingRegistry((binding,))
        descriptor = binding.as_record()
        composition = compose_episode_bindings(binding.services, store=store,
            journal=Journal(store, parent.run_id), execution_backend=None,
            descriptors=[descriptor], job_episodes=None, resource_estimator=None,
            role_credit_bindings={})
        rebuilt, = composition.bindings
        assert rebuilt.as_record() == descriptor

        def forbidden(*_args, **_kwargs):
            raise AssertionError("Capability information must not select or execute work")

        # In particular, never fabricate a child BindingContext to invoke catalog.
        monkeypatch.setattr(LiteratureEpisodes, "catalog", forbidden)
        monkeypatch.setattr(binding.services, "tool_catalog", forbidden)
        monkeypatch.setattr(binding.services, "execute_tool", forbidden)
        monkeypatch.setattr(binding.services, "scientific_credit", forbidden)
        rows_before = store.db.total_changes
        def schema_state():
            return [tuple(row) for row in store.db.execute(
                "SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]

        schema_before = schema_state()
        original_parent = parent.as_record()
        information = registry.initial_decision_context(parent)
        initialized_schema = schema_state()
        # The first rate display initializes its existing empty repositories.
        # Admit exactly those tables/indexes; every prior schema row must survive.
        rate_tables = {"literature_rate_operations", "literature_rate_received",
                       "literature_rate_source_received"}
        assert set(schema_before) <= set(initialized_schema)
        expected_additions = {("table", name, name) for name in rate_tables} | {
            ("index", "sqlite_autoindex_" + name + "_1", name) for name in rate_tables}
        assert {row[:3] for row in set(initialized_schema) - set(schema_before)} == expected_additions
        assert all(store.db.execute("SELECT count(*) FROM " + name).fetchone()[0] == 0
                   for name in rate_tables)
        assert store.db.total_changes == rows_before
        schema_before = initialized_schema
        assert rebuilt.initial_decision_context(parent) == information
        descriptor_info = information["reference_evidence_parent"]
        assert descriptor_info["source_refs"] == [args["source_ref"]]
        assert descriptor_info["source_custody"][0]["artifact_ref"] == store.get(args["source_ref"])["artifact_ref"]
        expected = [{key: row[key] for key in ("name", "description")} for row in [*current_baseline(), native_addition(), amount_addition(), optical_addition(), kinetic_addition(), kinetic_model_addition(), interaction_addition(), interaction_model_addition()]]
        assert descriptor_info["child_population_operations"] == expected
        assert all(set(row) == {"name", "description"} for row in expected)
        assert store.db.total_changes == rows_before
        assert schema_state() == schema_before
        assert parent.as_record() == original_parent
        with pytest.raises(LookupError, match="episode_role_not_bound:annotation"):
            registry.for_role("annotation")
        assert "annotation" not in binding.roles
        assert composition.resource_capabilities == ()
        # Repeated projections do not retain mutable aliases or publish records.
        descriptor_info["child_population_operations"][0]["description"] = "changed fixture"
        assert rebuilt.initial_decision_context(parent)["reference_evidence_parent"]["child_population_operations"] == expected
        assert store.db.total_changes == rows_before
        assert schema_state() == schema_before
    finally:
        store.close()


def test_no_metadata_outside_explicit_received_source_parent_binding(tmp_path):
    store, child, args = setup_store(tmp_path)
    try:
        binding, parent = enabled_parent(store, child, args["source_ref"])
        disabled = LiteratureEpisodes(binding.services, rate_population=True)
        assert disabled.initial_decision_context(parent) == {}
        assert LiteratureEpisodes(binding.services).initial_decision_context(parent) == {}
        assert binding.initial_decision_context(child) == {}
        scoped = replace(parent, path=(("annotation", "root"), ("annotation", "scoped")))
        assert binding.initial_decision_context(scoped) == {}
        improvement = replace(parent, role="improvement", path=(("improvement", "root"),))
        assert binding.initial_decision_context(improvement) == {}
        ordinary_child = replace(child, role="literature", path=(("literature", "case"),),
            assignment={"version": "literature_assignment_v1", "question_context_refs": [],
                "source_refs": [args["source_ref"]]})
        Journal(store, child.run_id)
        # Children keep their existing assignment, custody and true tool catalog.
        assert binding.decision_context(ordinary_child, None) == disabled.decision_context(ordinary_child, None)
        assert "reference_evidence_parent" not in binding.decision_context(ordinary_child, None)
        with pytest.raises(ContractError, match="not_received"):
            binding.initial_decision_context(replace(parent, received_record_refs=()))
        with pytest.raises(ValueError, match="unsupported_literature_role"):
            binding.catalog(parent)
    finally:
        store.close()


@pytest.mark.parametrize("field", ["oxygen_measurements", "custom_reference_components"])
def test_provider_repeats_actual_capabilities_in_task_across_delta_lookup_and_reconstruction(tmp_path, field):
    store, child, args = setup_store(tmp_path / "state")
    try:
        binding, parent = enabled_parent(store, child, args["source_ref"])
        first = snapshot()
        first.pop("literature_assignment")
        first.pop("literature_source_custody")
        first.update(EpisodeBindingRegistry((binding,)).initial_decision_context(parent))
        first["goal"]["objective"] = "Compare the supplied reference experiment and preserve missing productive coupling."
        first["constraints"] = {"scope": "Use assigned source only; preserve the caller's oxygen endpoint."}
        first["requested_form"] = obj({field: rate_cells_schema()})
        first["available_report_facts"] = binding.received_report_sources("annotation")
        second = deepcopy(first)
        qualification = "The source endpoint remains oxygen consumption; product formation is unknown."
        second["child_reports"] = [{field: [{"component": "rate_difference", "value": None,
            "unit": "umol/min", "unavailable_reason": "productive_coupling_unreported",
            "qualification": qualification}]}]
        lookup_text = "A source qualification supplied by a completed own-history lookup."
        lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result",
            "decision_index": 2, "exchange_index": 1,
            "result": {"status": "completed", "text": lookup_text}}
        delta = state_frame(second, first)
        assert "reference_evidence_parent" not in delta["fields"]
        restored_frame = state_frame(second)
        restored_frame.update(restored_pending_decision_index=2, restored_public_exchanges=[{
            "exchange_index": 1, "response": {"private": "PRIVATE_UNREQUESTED_EXCHANGE"},
            "lookup_result": lookup["result"]}])
        wire = LiteratureWire(tmp_path / "wire")
        restarted = LiteratureWire(tmp_path / "restarted")
        before = deepcopy((first, second, delta, restored_frame))

        async def exercise():
            await complete(wire, state_frame(first), episode=parent.episode_id)
            await complete(wire, delta, episode=parent.episode_id)
            await complete(wire, lookup, episode=parent.episode_id)
            await complete(restarted, restored_frame, episode=parent.episode_id)

        changes = store.db.total_changes
        asyncio.run(exercise())
        tasks = []
        for transport in (wire, restarted):
            for call in transport.turns_sent():
                task, steering = split(call["input"][0]["text"])
                tasks.append(task)
                assert task.count(REFERENCE_PARENT_TASK) == 1
                assert task.count(SAVED_NUMERICAL_RETURN_TASK) == 1
                assert first["goal"]["objective"] in task
                assert first["constraints"]["scope"] in task
                assert "return." + field in task
                assert "child_return.literature_rate_cells" in task
                assert qualification not in task and lookup_text not in task
                assert TABLE_TITLE in task and TABLE_TITLE not in steering
                metadata = task.split(TABLE_TITLE, 1)[1].split("Permitted child investigations", 1)[0]
                rows = first["reference_evidence_parent"]["child_population_operations"]
                assert sum(line.startswith("| literature.") for line in metadata.splitlines()) == len(rows)
                for row in rows:
                    assert row["name"] in metadata and row["description"] in metadata
                    assert row["name"] not in steering
                for private in ("input_schema", "source_selected", "PRIVATE_", "schema_json", "implementation_sha256"):
                    assert private not in metadata
                assert "already acquired CSV/TSV summary" in metadata
                assert "does not read arbitrary prose/figures" in metadata
                assert "directly from selected literal source spans" in metadata
                assert "endpoint-specific definition" in metadata
                assert "no universal U conversion is assumed" in metadata
                own_tools = task.split("Available own operations", 1)[1].split(TABLE_TITLE, 1)[0]
                assert "literature.rate.populate" not in own_tools
                assert "literature.partner.source.populate" not in own_tools
                assert call["outputSchema"] == OUTPUT_SCHEMA
        assert all(task == tasks[0] for task in tasks)
        for call in wire.turns_sent()[1:] + restarted.turns_sent():
            _, steering = split(call["input"][0]["text"])
            assert qualification in steering and "productive_coupling_unreported" in steering
        assert lookup_text in split(wire.turns_sent()[-1]["input"][0]["text"])[1]
        assert lookup_text in split(restarted.turns_sent()[0]["input"][0]["text"])[1]
        assert "PRIVATE_UNREQUESTED_EXCHANGE" not in restarted.turns_sent()[0]["input"][0]["text"]
        assert (first, second, delta, restored_frame) == before
        assert store.db.total_changes == changes
        # The selected return remains the parent's form, not a population operation.
        assert set(first["requested_form"]["properties"]) == {field}
    finally:
        store.close()


def test_projection_renders_only_names_and_descriptions_and_preserves_task_dedup(tmp_path):
    store, child, args = setup_store(tmp_path)
    try:
        binding, parent = enabled_parent(store, child, args["source_ref"])
        value = snapshot()
        value.update(binding.initial_decision_context(parent))
        rows = value["reference_evidence_parent"]["child_population_operations"]
        for row in rows:
            row.update(input_schema={"secret": "PRIVATE_SCHEMA"}, sheet="PRIVATE_SHEET", id="PRIVATE_ID")
        task, steering = split(render_reference_evidence_parent_prompt(value,
            REFERENCE_PARENT_TASK + "\n" + SAVED_NUMERICAL_RETURN_TASK))
        assert task.count(REFERENCE_PARENT_TASK) == 1
        assert task.count(SAVED_NUMERICAL_RETURN_TASK) == 1
        assert "PRIVATE_SCHEMA" not in task + steering
        assert "PRIVATE_SHEET" not in task + steering
        assert "PRIVATE_ID" not in task + steering
    finally:
        store.close()


def test_rate_meaning_view_is_an_exact_optional_fact_without_a_new_population_operation(tmp_path):
    from gene_annotation_episode.communication import validate_closed_schema
    from gene_annotation_episode.literature_rate_meaning_delivery import NAMESPACE, rate_source_meaning_cells_schema
    store, child, args = setup_store(tmp_path)
    try:
        binding, parent = enabled_parent(store, child, args["source_ref"])
        # The immutable historical catalog/hash remains checked by baseline().
        expected = current_baseline() + [native_addition(), amount_addition(), optical_addition(),
            kinetic_addition(), kinetic_model_addition(), interaction_addition(), interaction_model_addition()]
        assert _population_catalog() == expected
        registered = binding.received_report_sources(parent.role)[NAMESPACE]
        assert registered["report_schema"] == rate_source_meaning_cells_schema()
        validate_closed_schema(obj({"caller_selected_scientific_meanings": registered["report_schema"]}))
        metadata = binding.initial_decision_context(parent)
        assert metadata["reference_evidence_parent"]["child_population_operations"] == [
            {key: row[key] for key in ("name", "description")} for row in expected]
        assert metadata["literature_rate_source_meaning_display"] == {"cells": [], "records": {}}
        assert store.db.execute("SELECT 1 FROM sqlite_master WHERE name='literature_rate_source_meaning_received'").fetchone() is None
    finally:
        store.close()


def test_runtime_information_does_not_create_actions_credit_or_change_requested_child_form(tmp_path):
    store, child, args = setup_store(tmp_path / "state")
    try:
        field = "caller_chosen_oxygen_cells"
        form = obj({field: rate_cells_schema()})
        components = ["rate_difference", "difference_se"]
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": [args["source_ref"]], "requested_rate_components": components}
        controllers, received = [], []

        def commission(inputs):
            descriptor = inputs["reference_evidence_parent"]
            assert descriptor["child_population_operations"] == [
                {key: row[key] for key in ("name", "description")} for row in [*current_baseline(), native_addition(), amount_addition(), optical_addition(), kinetic_addition(), kinetic_model_addition(), interaction_addition(), interaction_model_addition()]]
            assert not any(row["name"].startswith("literature.") for row in inputs["tools"])
            assert inputs["child_reports"] == []
            assert not store.list("observation") and not store.list("assessment")
            return {"selection": {"kind": "episode_child", "role": "literature",
                "assignment": assignment, "goal": "Compare the supplied synthetic oxygen rates.",
                "scope": plain(child.scope), "purpose": "Return only the caller's requested oxygen cells.",
                "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}

        def populate(inputs):
            assert "reference_evidence_parent" not in inputs
            assert inputs["literature_assignment"] == assignment
            assert inputs["requested_form"] == form
            assert any(row["name"] == "literature.rate.populate" for row in inputs["tools"])
            return {"selection": {"kind": "tool", "tool": "literature.rate.populate", "arguments": args},
                "report_update": {}}

        def receive(inputs):
            report, = inputs["child_reports"]
            assert set(report) == {field}
            assert [row["component"] for row in report[field]] == components
            assert report[field][0]["value"] == 1
            assert report[field][1]["value"] is None
            received.append(report)
            assert "child_population_operations" in inputs["reference_evidence_parent"]
            source = store.get(args["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            commit = {name: [] for name in store.reasoning_schema()["required"]}
            commit["source_subjects"] = [{"alias": "reported_subject", "reference_type": "assay",
                "source_ref": source["id"], "label": "source construct", "anchor": {
                    "source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                    "start": 0, "end": len(raw), "quote": raw.decode("utf-8")}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        def controller(path, initial):
            value = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(value)
            return value

        provider = ScriptedProvider([commission, populate, receive])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[args["source_ref"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),),
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0
        assert len(provider.contexts) == 3 and len(received) == 1
        assert [value.scores for value in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
        saved, = store.db.execute("SELECT form FROM runtime_forms").fetchall()
        assert json.loads(saved[0]) == received[0]
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()
