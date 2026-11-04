"""Scripted ordinary Episodes over real rate population, custody and returns.

The source table, model responses and stopping controllers are synthetic. These
are Workflow integration checks, not primary-paper or model-backed validation.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, plain
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_rate_storage import rate_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_storage import setup_store
from test_runtime import FixtureController, ScriptedProvider


COMPONENTS = ["rate_difference", "difference_se", "source_signed_index"]
FORM = obj({"measurements": rate_cells_schema()})


def assignment(source_ref):
    return {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": [source_ref], "requested_rate_components": COMPONENTS}


def work(arguments):
    return {"selection": {"kind": "tool", "tool": "literature.rate.populate",
                           "arguments": arguments}, "report_update": {}}


def child_selection(scope, source_ref):
    return {"selection": {"kind": "episode_child", "role": "literature",
        "assignment": assignment(source_ref), "goal": "Measure the synthetic source preparation's rate contrast",
        "scope": scope, "purpose": "Return the requested rate contrast and unavailable uncertainty cells",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}


@pytest.mark.parametrize("repair_first", [False, True])
def test_workflow_delivers_exact_requested_cells_without_credit_or_extra_observations(tmp_path, repair_first):
    store, context, args = setup_store(tmp_path / "state")
    try:
        tools = ToolRegistry(store)
        received, controllers = [], []

        def choose_population(inputs):
            assert inputs["literature_assignment"] == assignment(args["source_ref"])
            assert "literature.rate.populate" in {row["name"] for row in inputs["tools"]}
            return work(args)

        def repair_condition(inputs):
            assert inputs["feedback"]["code"] == "condition_mismatch:test_condition"
            assert inputs["last_local_outcome"]["status"] == "invalid"
            assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 0
            return choose_population(inputs)

        def parent_uses_return(inputs):
            report, = inputs["child_reports"]
            received.append(report)
            cells = report["measurements"]
            assert [cell["component"] for cell in cells] == COMPONENTS
            assert cells[0]["value"] == 1
            assert cells[0]["unit"] == "umol/min"
            assert cells[1]["value"] is None
            assert cells[1]["unavailable_reason"] is not None
            assert cells[2]["value"] is None
            assert cells[2]["unavailable_reason"] == "observation_model_unspecified"
            assert all(cell["evidence_source_ref"] == args["source_ref"] for cell in cells)
            identities = cells[0]
            assert store.get(identities["assayed_subject_ref"])["label"] == "source construct"
            assert store.get(identities["experiment_ref"])["label"] == "experiment 1"
            assert store.get(identities["reference_condition_ref"])["name"] == "without inhibitor"
            assert store.get(identities["test_condition_ref"])["name"] == "with inhibitor"
            assert store.get(identities["endpoint_ref"])["label"] == "oxygen_rate"
            assert store.get(identities["normalization_ref"])["label"] == "per_preparation"
            for cell in cells:
                for key in ("assayed_subject_ref", "experiment_ref", "reference_condition_ref",
                            "test_condition_ref", "endpoint_ref", "normalization_ref"):
                    assert cell[key] == identities[key]
            assert "retained_fraction" not in {cell["component"] for cell in cells}
            # The synthetic receiver records the actual assayed subject, not a
            # target activity assertion or transfer. This is its own selected
            # reasoning action, not a report-composition call.
            source = store.get(args["source_ref"])
            raw = store.get_artifact(source["artifact_ref"])
            commit = {field: [] for field in store.reasoning_schema()["required"]}
            commit["source_subjects"] = [{"alias": "assayed_source", "reference_type": "assay",
                "source_ref": source["id"], "label": "source construct", "anchor": {
                    "source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                    "start": 0, "end": len(raw), "quote": raw.decode("utf-8")}}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        script = [child_selection(plain(context.scope), args["source_ref"])]
        if repair_first:
            script.extend([work({**args, "test_condition": "wrong condition"}), repair_condition])
        else:
            script.append(choose_population)
        script.append(parent_uses_return)
        provider = ScriptedProvider(script)

        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(result)
            return result

        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, tools, provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[args["source_ref"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0
        assert len(received) == 1
        assert [controller.scores for controller in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert len(provider.contexts) == 3 + int(repair_first)
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 1
        saved_form, = store.db.execute("SELECT form FROM runtime_forms").fetchall()
        assert json.loads(saved_form[0]) == received[0]
        delivery, = store.db.execute("SELECT cells FROM literature_rate_received").fetchall()
        assert json.loads(delivery[0]) == received[0]["measurements"]
        # The complete sheet remains durable, but the receiver receives only
        # its requested three cells and cannot silently inherit private cells.
        sheet_ref = received[0]["measurements"][0]["sheet_ref"]
        sheet = store.get(sheet_ref)
        saved = json.loads(store.get_artifact(sheet["artifact_ref"]))
        assert len(saved["sheet"]["cells"]) == 10
        assert saved["sheet"]["annotation_credit"] is None
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def service_binding(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    services = WorkflowServices(host)
    binding = LiteratureEpisodes(services, rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return services, binding


def test_opt_in_catalog_wrong_condition_and_unreceived_source(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        services, enabled = service_binding(store, context)
        bound = replace(context, role="literature", path=(("literature", "case"),),
                        assignment=assignment(args["source_ref"]))
        disabled = LiteratureEpisodes(services)
        assert "literature.rate.populate" not in {row["name"] for row in disabled.catalog(bound)}
        assert "literature.rate.populate" in {row["name"] for row in enabled.catalog(bound)}
        wrong = asyncio.run(enabled.execute(bound, "literature.rate.populate",
            {**args, "test_condition": "different condition"}, "bad-condition"))
        assert wrong["status"] == "invalid"
        assert wrong["feedback"]["code"] == "condition_mismatch:test_condition"
        assert wrong["record_refs"] == []
        denied = asyncio.run(enabled.execute(replace(bound, received_record_refs=()),
            "literature.rate.populate", args, "missing-receipt"))
        assert denied["status"] == "invalid"
        assert denied["feedback"]["code"] == "literature_source_not_received"
        assert store.db.execute("SELECT count(*) FROM literature_rate_operations").fetchone()[0] == 0
    finally:
        store.close()


def test_binding_validates_saved_values_and_forwarding_copies_only_admitted_subset(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        services, binding = service_binding(store, context)
        bound = replace(context, role="literature", path=(("literature", "case"),),
                        assignment=assignment(args["source_ref"]))
        outcome = asyncio.run(binding.execute(bound, "literature.rate.populate", args, "selected"))
        assert outcome["status"] == "completed"
        sheet_ref = outcome["result"]["sheet_ref"]
        bound = replace(bound, received_record_refs=(*bound.received_record_refs, *outcome["record_refs"]))
        facts = binding.facts(bound, {"committed_record_refs": [sheet_ref]})
        form = form_with_facts({}, FORM, facts)
        binding.validate_report(bound, form, FORM)
        wrong = deepcopy(form)
        wrong["measurements"][0]["value"] = 999
        with pytest.raises(ReportBoundaryError, match="differs_from_saved"):
            binding.validate_report(bound, wrong, FORM)
        parent = replace(bound, role="annotation", episode_id="receiving-parent",
                         path=(("annotation", "root"),), assignment={})
        assert binding.received_report_facts(parent) == {"literature_rate_cells": []}
        binding.received_form_references(parent, form, FORM, "admitted-subset")
        forwarded = binding.received_report_facts(parent)["literature_rate_cells"]
        assert forwarded == form["measurements"]
        assert len(forwarded) == 3
        # Repeated delivery has no extra contribution or extra copied row.
        binding.received_form_references(parent, form, FORM, "admitted-subset")
        assert binding.received_report_facts(parent)["literature_rate_cells"] == forwarded
    finally:
        store.close()


def test_saved_descriptor_reconstructs_original_opt_in_and_replay_avoids_refit(tmp_path, monkeypatch):
    store, context, args = setup_store(tmp_path)
    try:
        services, binding = service_binding(store, context)
        bound = replace(context, role="literature", path=(("literature", "case"),),
                        assignment=assignment(args["source_ref"]))
        outcome = asyncio.run(binding.execute(bound, "literature.rate.populate", args, "selected"))
        descriptor = binding.as_record()
        journal = Journal(store, context.run_id)
        composition = compose_episode_bindings(services, store=store, journal=journal,
            execution_backend=None, descriptors=[descriptor], job_episodes=None,
            resource_estimator=None, role_credit_bindings={})
        reopened, = composition.bindings
        assert reopened.rate_population is True
        assert reopened.as_record() == descriptor

        def forbidden(*_args, **_kwargs):
            raise AssertionError("replay must use original saved sheet, not refit")
        monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.read_rate_table", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_rate_storage.populate_rate_contrast", forbidden)
        assert asyncio.run(reopened.execute(bound, "literature.rate.populate", args, "selected")) == outcome
    finally:
        store.close()


def test_frozen_commission_refreshes_only_exact_child_durable_receipts(tmp_path):
    store, context, args = setup_store(tmp_path)
    try:
        services, binding = service_binding(store, context)
        original = replace(context, role="literature", path=(("literature", "case"),),
                           assignment=assignment(args["source_ref"]))
        receipts = EpisodeReceipts(store, context.run_id)
        receipts.bind(original.episode_id)
        receipts.receive(original.episode_id, [args["source_ref"]], kind="initial")
        outcome = asyncio.run(binding.execute(original, "literature.rate.populate", args, "selected"))
        sheet_ref = outcome["result"]["sheet_ref"]
        receipts.receive(original.episode_id, outcome["record_refs"], kind="own_action", source_index=0)
        services.workflow.record_selection = lambda episode_id: {
            "run_id": context.run_id, "episode_id": episode_id,
            "known_record_refs": list(receipts.known(episode_id))}
        current = replace(original, received_record_refs=tuple(receipts.known(original.episode_id)))
        form = form_with_facts({}, FORM,
            binding.facts(current, {"committed_record_refs": [sheet_ref]}))
        assert sheet_ref not in original.received_record_refs
        binding.validate_report(original, form, FORM)

        stranger = replace(original, episode_id="different-child", path=(("literature", "stranger"),))
        receipts.bind(stranger.episode_id)
        receipts.receive(stranger.episode_id, [args["source_ref"]], kind="initial")
        with pytest.raises(ReportBoundaryError) as missing:
            binding.validate_report(stranger, form, FORM)
        assert missing.value.diagnostic["code"] == "literature_sheet_not_received"
        services.workflow.record_selection = lambda episode_id: {
            "run_id": context.run_id, "episode_id": original.episode_id,
            "known_record_refs": [sheet_ref]}
        with pytest.raises(ReportBoundaryError) as wrong_receiver:
            binding.validate_report(stranger, form, FORM)
        assert wrong_receiver.value.diagnostic["code"] == "literature_rate_receiver_mismatch"
    finally:
        store.close()
