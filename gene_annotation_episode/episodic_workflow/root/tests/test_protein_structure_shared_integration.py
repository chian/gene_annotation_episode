"""Shared protein dispatch and metadata boundaries using real production owners.

These cases establish routing and rejection before native work. Actual native
collection and full Workflow delivery are tested separately, not simulated here.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_protein_structure_contracts import POLICY
from gene_annotation_episode.native_protein_structure_returns import FACT_SOURCES
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


SELECTOR = {"version": "protein_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
    "saved_sheet": None, "parameters": None, "projections": [],
    "return_saved_sheet": False, "sequence_allowed_uses": []}


class Contexts:
    def __init__(self, store, directory):
        self.store, self.run_id = store, "protein409-shared-boundaries"
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="AGST", molecule="protein")["subject_refs"]}
        self.family = ExecutionEpisodes(None, store=store, directory=directory / "runtime", run_id=self.run_id,
            resources={"local": {"kind": "local", "workspace": str(directory), "policy": deepcopy(POLICY)}},
            initial_information={}, tool_registry=ToolRegistry(store), handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=128, log_roles=["stdout", "stderr"])
        self.root = self.context((("annotation", "root"),), {}, None)
        self.receipts.receive(self.root.episode_id, self.scope["subject_refs"], kind="initial")

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        manifest = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        request = {"goal": {"goal_id": "shared-boundary-fixture", "objective": "Check the assigned return"},
            "message": {"scope": deepcopy(self.scope), "episode_assignment": deepcopy(assignment),
                "knowledge_inheritance": manifest, "initial_report": {}}, "report_contract": deepcopy(contract)}
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)

    def child(self, *, role="results"):
        schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        contract = {"decision": "Return exactly the requested fields", "measurements": {"schema": schema}}
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": "not-collected",
            "selector": deepcopy(SELECTOR)} if role == "results" else {}
        child = self.context((*self.root.path, (role, "child_0")), assignment, contract, self.root)
        action = {"kind": "episode_child", "role": role, "assignment": assignment,
            "scope": deepcopy(self.scope), "purpose": contract["decision"], "schema_json": canonical(schema),
            "goal": child.request["goal"]["objective"], "initial_report_json": "{}"}
        self.journal.save("runtime_actions", {"episode_id": self.root.episode_id, "decision_index": 0,
            "action": canonical(action), "result": None, "credit": None})
        return child

    def unreceived_source(self):
        artifact = self.store.artifact(b'{"test":"unqualified bytes"}', "application/json")
        return self.store.put("source", {"provider": "episode.execution_result", "accession": "unreceived-protein",
            "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
            "version": "native_protein_structure_bundle_v1", "retrieved_at": "2026-10-27T00:00:00+00:00",
            "auxiliary_artifact_refs": []}, origin="tool")["id"]


@pytest.fixture
def f(tmp_path):
    with Store(tmp_path / "store") as store:
        yield Contexts(store, tmp_path)


def no_io(*args, **kwargs):
    raise AssertionError("metadata routing opened an artifact or inspected a live target")


def test_pending_protein_facts_credit_catalog_and_completion_do_not_open_a_target(f, monkeypatch):
    child = f.child()
    monkeypatch.setattr(f.family, "_target", no_io)
    monkeypatch.setattr(f.store, "get_artifact", no_io)
    monkeypatch.setattr(f.family.job_progress_provider.targets, "observe_target", no_io)
    assert {row["name"] for row in f.family.catalog(child)} == {
        "execution.results.status", "execution.results.collect"}
    assert f.family.permitted_common_actions(child) == ("tool",)
    facts = f.family.facts(child, {})
    assert all(facts[name] == [] for name in FACT_SOURCES)
    assert facts["execution_result_refs"] == [] and facts["execution_completed"] is False
    assert f.family.project_credit(child, None)["credit"] == 0
    key = f"{f.run_id}:{child.episode_id}:0"
    assert f.family.completion_for_action(child, key) is None
    assert f.family._proof_for_action(child, key) is None
    assert f.family._native_results_complete(child, []) is False
    assert f.family.verify_completion(child, None) is False


@pytest.mark.parametrize("role", ["annotation", "scientific_process", "results"])
def test_exact_four_d1_return_sources_are_available_at_their_shared_boundary(f, role):
    actual = f.family.fact_sources(role) if role == "results" else f.family.received_report_sources(role)
    expected = protein_structure_fact_sources()
    assert {key: value for key, value in actual.items() if key.startswith("execution_protein_structure_")} == expected


@pytest.mark.parametrize("role", ["annotation", "scientific_process"])
def test_empty_scientific_returns_do_not_create_received_values(f, role):
    context = f.root if role == "annotation" else f.child(role=role)
    assert not set(f.family.received_report_facts(context)).intersection(FACT_SOURCES)
    schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    f.family.validate_received_report(context, {}, schema)
    assert f.family.received_form_references(context, {}, schema, "unused-empty-form") == []


@pytest.mark.parametrize("namespace", [None, "source", "execution_result", "artifact"])
@pytest.mark.parametrize("old_recursive_receipt", [False, True])
def test_visible_or_old_recursively_received_source_does_not_grant_its_use(f, monkeypatch, namespace, old_recursive_receipt):
    source = f.unreceived_source()
    if old_recursive_receipt:
        f.receipts.receive(f.root.episode_id, [source], kind="initial")
    monkeypatch.setattr(f.store, "get_artifact", no_io)
    assert f.family.resolve_received_reference(f.root, source, namespace) is False
    assert f.family.resolve(f.root, source, namespace) is False


def test_protein_permission_denial_precedes_input_version_hash_read(f, monkeypatch):
    source = f.unreceived_source()
    f.receipts.receive(f.root.episode_id, [source], kind="initial")
    monkeypatch.setattr(f.store, "get_artifact", no_io)
    with pytest.raises(ProteinStructureOperandError, match="original_commission_mismatch"):
        f.family._versions([{"reference": source, "version": None, "content_sha256": "0" * 64}],
            f.scope, context=f.root)


def test_ordinary_input_version_hash_still_checks_actual_original_bytes(f):
    reference = f.scope["subject_refs"][0]
    record = f.store.get(reference)
    artifact = record.get("sequence_ref", record.get("artifact_ref"))
    value = {"reference": reference, "version": None,
        "content_sha256": hashlib.sha256(f.store.get_artifact(artifact)).hexdigest()}
    f.family._versions([value], f.scope, context=f.root)
    value["content_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="execution_input_version_conflict"):
        f.family._versions([value], f.scope, context=f.root)


@pytest.mark.parametrize("namespace", ["protein_structure_projection", "protein_structure_calculation", "protein_structure_receipt"])
def test_semantic_locators_never_become_generic_read_permissions(f, namespace):
    reference = f.scope["subject_refs"][0]
    assert f.family.resolve_received_reference(f.root, reference, namespace) is False
    assert f.family.resolve(f.root, reference, namespace) is False
    assert f.family.resolve(f.root, "protein_structure_result_receipt:some-locator", None) is False
