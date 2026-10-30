"""Synthetic exact saved reconstruction with scientific computation disabled.

The retained v1 records were written by the actual original implementation
before this correction; they are not relabeled outputs from the new code.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_active_site_storage import LiteratureActiveSiteRepository, active_site_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from method_loop.durable import DurableExecutionError
from test_literature_active_site_inputs import TEXT
from test_literature_active_site_storage import setup
from test_runtime import FixtureController, ScriptedProvider


HERE = Path(__file__).resolve().parents[1] / "verification/literature_reference_evidence_2026-10-25_001/a105_active_site_reconstruction_182"
LEGACY = json.loads((HERE / "LEGACY_RECEIPT_001.json").read_text())
REQUESTED = ["sites_per_total_monomer", "conditional_nominal_to_active_denominator_factor"]
FORM = obj({"amounts": active_site_cells_schema()})


def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


def readonly(path):
    assert not Path(str(path / "state.sqlite3") + "-wal").exists()
    store = Store.__new__(Store)
    store.path, store._savepoint = path, 0
    store.db = sqlite3.connect((path / "state.sqlite3").resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    store.db.row_factory = sqlite3.Row
    store.db.execute("PRAGMA query_only=ON")
    return store


def forbidden(*_args, **_kwargs):
    raise AssertionError("saved reconstruction must not parse, convert or calculate scientific values")


def disable_science(monkeypatch):
    modules = {
        "literature_active_site_storage": ("read_active_site_inputs", "populate_active_site_components"),
        "literature_active_site_inputs": ("read_active_site_inputs", "validate_active_site_extraction", "unit_scale", "_derived_quantity", "_number", "_fraction_number"),
        "literature_active_site_calculations": ("populate_active_site_components", "validate_active_site_extraction", "_operand", "_reason", "_divide", "_multiply", "_subtract", "_point", "_encode", "_project"),
        "literature_rate_domains": ("_divide", "_multiply", "_subtract", "_point", "_encode", "_project"),
        "literature_rate_native_inputs": ("_number", "_saved_number", "_plain_unit", "_converted"),
        "literature_partner_source_fields": ("read_source_number", "convert_source_number"),
    }
    for module, names in modules.items():
        for name in names:
            monkeypatch.setattr(f"gene_annotation_episode.{module}.{name}", forbidden)


def saved_artifacts_only(monkeypatch, store):
    allowed = {row[field] for row in store.list("source") if row["origin"] == "tool"
               for field in ("artifact_ref", "request_ref")}
    original = store.get_artifact
    def read(reference):
        assert reference in allowed, "original scientific artifacts must remain closed"
        return original(reference)
    monkeypatch.setattr(store, "get_artifact", read)


def services_for(store, run_id):
    # Composition/projection requires no tool-registry construction. Installing
    # unrelated registry tables would invalidate a cold read-only proof.
    host = SimpleNamespace(store=store, run_id=run_id, tools=None)
    return host, WorkflowServices(host)


@pytest.mark.parametrize("name", sorted(LEGACY))
def test_authentic_v1_original_payload_rows_and_admitted_subset_without_science(name, monkeypatch):
    item = LEGACY[name]
    path = HERE / "legacy" / name
    before = hashes(path)
    disable_science(monkeypatch)
    with readonly(path) as store:
        saved_artifacts_only(monkeypatch, store)
        # All scientific operations are disabled before either construction.
        repo = LiteratureActiveSiteRepository(store, item["run_id"])
        host, services = services_for(store, item["run_id"])
        binding = LiteratureEpisodes(services, **item["binding_descriptor"]["configuration"])
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        assert binding.as_record()["implementation_sha256"] != item["binding_descriptor"]["implementation_sha256"]
        assert binding.as_record()["configuration"] == item["binding_descriptor"]["configuration"]
        ref = item["outcome"]["result"]["sheet_ref"]
        context, receiver = BindingContext(**item["context"]), BindingContext(**item["receiver"])
        assert repo.read(ref) == item["payload"]
        assert repo.populate(context, item["arguments"], "original-v1-selected") == item["outcome"]
        assert repo.project_cells([ref], permitted_record_refs=[ref]) == item["all_rows"]
        assert repo.received_cells(receiver) == item["admitted_rows"]
        assert repo.fact_cells(receiver, [ref], components=repo.components) == item["admitted_rows"]
        assert binding._active_site_repository().received_cells(receiver) == item["admitted_rows"]
        for schema in (item["schema"], active_site_cells_schema()):
            contract = obj({"amounts": schema})
            form = form_with_facts({}, contract, {"literature_active_site_cells": item["admitted_rows"]})
            assert validate_form(form, contract, lambda r, namespace: store.get(r)["record_type"] == namespace) == form
        private = repo.project_cells([ref], permitted_record_refs=[ref], components=["protein_mass_concentration"])
        with pytest.raises(ContractError, match="cell_not_received"):
            repo.validate_fact_values(receiver, private)
        with pytest.raises(ContractError, match="not_received"):
            repo.project_cells([ref], permitted_record_refs=[])
        with pytest.raises(ContractError, match="not_received"):
            repo.populate(replace(context, received_record_refs=()), item["arguments"], "original-v1-selected")
        altered = deepcopy(item["admitted_rows"])
        altered[0]["interpretations"]["amount_linkage"]["value"] = "different"
        with pytest.raises(ContractError, match="differs_from_saved"):
            repo.validate_fact_values(receiver, altered)
        assert store.db.total_changes == 0
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            store.db.execute("DELETE FROM records")
    assert hashes(path) == before


def test_original_implementation_demonstrates_the_recalculation_gap(monkeypatch):
    spec = importlib.util.spec_from_file_location("gene_annotation_episode._active_site_storage_baseline182",
        HERE / "baseline/literature_active_site_storage.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "validate_active_site_extraction", forbidden)
    with readonly(HERE / "legacy/point") as store:
        saved_artifacts_only(monkeypatch, store)
        repo = module.LiteratureActiveSiteRepository(store, LEGACY["point"]["run_id"])
        with pytest.raises(AssertionError, match="must not parse"):
            repo.read(LEGACY["point"]["outcome"]["result"]["sheet_ref"])


def test_old_frozen_descriptor_still_rejects_changed_implementation(monkeypatch):
    item = LEGACY["point"]
    before = hashes(HERE / "legacy/point")
    disable_science(monkeypatch)
    with readonly(HERE / "legacy/point") as store:
        saved_artifacts_only(monkeypatch, store)
        _, services = services_for(store, item["run_id"])
        with pytest.raises(DurableExecutionError, match="identity_conflict"):
            compose_episode_bindings(services, store=store,
                journal=SimpleNamespace(store=store, run_id=item["run_id"]),
                execution_backend=None, descriptors=[item["binding_descriptor"]], job_episodes=None,
                resource_estimator=None, role_credit_bindings={})
        assert store.db.total_changes == 0
    assert before == hashes(HERE / "legacy/point")


@pytest.mark.parametrize("mutation", ["signature", "outcome_value", "outcome_meaning", "outcome_omission", "outcome_status", "operation_ref", "provider", "origin", "source_identity", "unselected_copy"])
def test_selected_output_authentication_rejects_corruption(tmp_path, mutation):
    path = tmp_path / mutation
    shutil.copytree(HERE / "legacy/point", path)
    item = LEGACY["point"]
    ref = item["outcome"]["result"]["sheet_ref"]
    with Store(path) as store:
        repo = LiteratureActiveSiteRepository(store, item["run_id"])
        if mutation == "signature":
            store.db.execute("UPDATE literature_active_site_operations SET signature='{}'")
        elif mutation.startswith("outcome") or mutation == "operation_ref":
            changed = deepcopy(item["outcome"])
            if mutation == "outcome_value": changed["result"]["cells"][0]["value"] = 900
            elif mutation == "outcome_meaning": changed["result"]["cells"][0]["interpretations"]["amount_linkage"]["value"] = "different"
            elif mutation == "outcome_omission": changed["result"]["cells"].pop()
            elif mutation == "outcome_status": changed["status"] = "attempted"
            else: changed["operation_ref"] = "operation_" + "0" * 24
            store.db.execute("UPDATE literature_active_site_operations SET outcome=?", (canonical(changed),))
        elif mutation == "unselected_copy":
            source = store.get(ref)
            record = {k: v for k, v in source.items() if k not in ("id", "origin", "record_type")}
            record["accession"] = "synthetic-unselected-copy"
            ref = store.put("source", record, origin="tool")["id"]
        else:
            source = store.get(ref)
            if mutation == "provider": source["provider"] = "copied-provider"
            elif mutation == "origin": source["origin"] = "caller"
            else: source["accession"] = "identity-mutation"
            store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(source), ref))
        with pytest.raises(ContractError):
            repo.read(ref)


@pytest.mark.parametrize("which", ["artifact_ref", "request_ref"])
def test_corrupt_saved_artifact_bytes_are_rejected(tmp_path, which):
    path = tmp_path / which
    shutil.copytree(HERE / "legacy/point", path)
    with Store(path) as store:
        item = LEGACY["point"]; ref = item["outcome"]["result"]["sheet_ref"]
        digest = store.get(ref)[which].removeprefix("artifact_")
        artifact = path / "artifacts" / digest[:2] / digest
        artifact.write_bytes(artifact.read_bytes() + b" ")
        with pytest.raises(ContractError, match="digest_mismatch"):
            LiteratureActiveSiteRepository(store, item["run_id"]).read(ref)


def test_foreign_run_and_changed_selected_scope_are_rejected(tmp_path):
    shutil.copytree(HERE / "legacy/point", tmp_path / "state")
    item = LEGACY["point"]
    with Store(tmp_path / "state") as store:
        ref = item["outcome"]["result"]["sheet_ref"]
        with pytest.raises(ContractError, match="run_mismatch"):
            LiteratureActiveSiteRepository(store, "foreign-run").read(ref)
        context = BindingContext(**item["context"])
        changed_scope = {"subject_refs": []}
        with pytest.raises(ContractError, match="operation_key_reused"):
            LiteratureActiveSiteRepository(store, item["run_id"]).populate(
                replace(context, scope=changed_scope), item["arguments"], "original-v1-selected")


def test_genuine_empty_cold_binding_does_not_install_tables(tmp_path, monkeypatch):
    store, context, _ = setup(tmp_path)
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.close()
    before = hashes(tmp_path)
    disable_science(monkeypatch)
    with readonly(tmp_path) as store:
        host, services = services_for(store, context.run_id)
        binding = LiteratureEpisodes(services, rate_population=True, active_site_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        repo = binding._active_site_repository()
        assert not repo._installed(repo.operations_table)
        assert repo.received_cells(context) == []
        assert repo.project_cells([], permitted_record_refs=[]) == []
        assert store.db.total_changes == 0
    assert hashes(tmp_path) == before


def test_current_selected_shared_loop_then_cold_readonly_factory_without_calculators(tmp_path, monkeypatch):
    store, context, args = setup(tmp_path / "state")
    forms, controllers = [], []
    assignment = {**plain(context.assignment), "requested_active_site_components": REQUESTED}
    child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
        "goal": "Determine the synthetic preparation's active-site denominator.", "scope": plain(context.scope),
        "purpose": "Return the specified active-site amount components with their scientific meanings.",
        "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.active_site.populate", "arguments": args}, "report_update": {}}
    def integrate(inputs):
        form, = inputs["child_reports"]; forms.append(deepcopy(form))
        assert [row["component"] for row in form["amounts"]] == REQUESTED
        commit = {key: [] for key in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"]); start = TEXT.index("active sites")
        commit["source_subjects"] = [{"alias": "synthetic_amount", "reference_type": "assay", "source_ref": args["source_ref"],
            "label": "active sites", "anchor": {"source_ref": args["source_ref"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": start + len("active sites"), "quote": "active sites"}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result); return result
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, integrate]),
        run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
        initial_known_record_refs=list(context.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True, active_site_population=True,
            reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
    assert summary["credit"] == 0 and [c.scores for c in controllers] == [[0, 0], [0]]
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
    assert store.db.execute("SELECT count(*) FROM literature_active_site_operations").fetchone()[0] == 1
    run_id, parent_id = store.db.execute("SELECT run_id,episode_id FROM literature_active_site_received").fetchone()
    # Only public saved binding metadata; no provider conversations are read.
    descriptors = json.loads(store.db.execute("SELECT settings FROM runtime_runs WHERE run_id=?", (run_id,)).fetchone()[0])["episode_bindings"]
    receiver = replace(context, run_id=run_id, episode_id=parent_id, role="annotation",
        path=(("annotation", parent_id),), assignment={}, received_record_refs=tuple(row["sheet_ref"] for row in forms[0]["amounts"]))
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)"); store.close()
    before = hashes(tmp_path / "state")
    disable_science(monkeypatch)
    with readonly(tmp_path / "state") as store:
        saved_artifacts_only(monkeypatch, store)
        host, services = services_for(store, run_id)
        restored = compose_episode_bindings(services, store=store,
            journal=SimpleNamespace(store=store, run_id=run_id), execution_backend=None,
            descriptors=descriptors, job_episodes=None, resource_estimator=None, role_credit_bindings={})
        binding, = restored.bindings
        host.episode_bindings = EpisodeBindingRegistry(restored.bindings)
        assert binding.received_report_facts(receiver)["literature_active_site_cells"] == forms[0]["amounts"]
        repo = binding._active_site_repository()
        assert repo.fact_cells(receiver, receiver.received_record_refs, components=repo.components) == forms[0]["amounts"]
        assert store.db.total_changes == 0
    assert before == hashes(tmp_path / "state")
