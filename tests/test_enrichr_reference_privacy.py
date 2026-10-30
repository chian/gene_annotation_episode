"""Resource-independent negative File authority over an actual publication.

Run A uses the existing registered-API engineering Harness (no live HTTP).
Run B has no API owner, resource configuration, selected work or model call.
Runtime/Services cases call their actual resolver methods on an explicitly
assembled Workflow inspection shell; they do not prove Workflow construction,
an episode run, positive Enrichr facts, or actual scientific service access.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from method_loop import EpisodeGoal, EpisodeRef, EpisodeRequest, EpisodeTree, Grain
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode import enrichr_reference_privacy as privacy
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.runtime import Record, ReleasingContext, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.waiting import PENDING_VERSION
from test_enrichr_returns import Harness


def forbidden(*args, **kwargs):
    raise AssertionError("privacy classification must not acquire, parse, read payloads or run decisions")


def receiver(store, scope, *, run_id="no-api-receiver", saved=True, parent=None):
    scope = plain(scope)
    journal, receipts = Journal(store, run_id), EpisodeReceipts(store, run_id)
    path = (("annotation", "root"),) if parent is None else (*parent.context.path, ("annotation", "child_0"))
    episode_id = EpisodeRef(run_id, path).episode_id
    manifest = receipts.bind(episode_id, None if parent is None else parent.context.episode_id)
    request = EpisodeRequest(EpisodeGoal.root(objective="Verify original publication File privacy",
        result_contract={"role": "annotation"}), Record({"scope": deepcopy(scope),
            "initial_report": {}, "episode_assignment": {}, "knowledge_inheritance": manifest})).as_record()
    context = BindingContext(run_id, episode_id, "annotation", path, scope, {}, request)
    if saved:
        journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active",
            "completion": None, "archive": None})
    return SimpleNamespace(context=context, receipts=receipts, journal=journal, run_id=run_id)


def inspection_workflow(store, receiving, *, initial_record_refs=()):
    """Actual resolver methods, without a service factory or episode execution."""
    workflow = Workflow.__new__(Workflow)
    workflow.store, workflow.run_id = store, receiving.run_id
    workflow.tools = ToolRegistry(store, clients=SimpleNamespace(_http=forbidden))
    workflow.journal = receiving.journal
    workflow.initial_known_record_refs = list(initial_record_refs)
    workflow.episode_bindings = EpisodeBindingRegistry(())
    workflow.native_event_information = workflow.scientific_provenance = None
    workflow.progress_provider = workflow.execution_expectations = workflow.job_episodes = None
    grain = Grain("annotation", "One original selected action", "One original typed return", forbidden)
    workflow.grains = {"annotation": grain}
    workflow.context = ReleasingContext(tree=EpisodeTree(grain), run_id=receiving.run_id)
    workflow.services = WorkflowServices(workflow)
    return workflow


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path / "store") as store:
        original = Harness(store, tmp_path / "run-a")
        child = original.child(original.root)
        outcome = original.action(child)
        source = store.get(outcome["result"]["source_ref"])
        original.returned(original.root, child)
        control = json.loads(store.get_artifact(source["request_ref"]))
        upload = control["transport"]["enrichr_protocol"]["stages"][0]["snapshot"]["content_ref"]
        # Expose the ordinary Store fallback for this protocol File too.
        attachment = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        attachment.update(provider="engineering_attachment", artifact_ref=upload,
            request_ref=None, auxiliary_artifact_refs=[])
        store.put("source", attachment, origin="external")
        other = receiver(store, original.scope)
        other.receipts.receive(other.context.episode_id, [source["id"]], kind="initial")
        yield SimpleNamespace(store=store, original=original, child=child, source=source,
            upload=upload, other=other, private=[source["request_ref"], source["auxiliary_artifact_refs"][0], upload])


def metadata_only(case, monkeypatch):
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr(case.original.client, "_http", forbidden)
    monkeypatch.setattr(case.original.api, "read_result", forbidden)
    monkeypatch.setattr(case.original.api, "_context", forbidden)
    monkeypatch.setattr(case.original.api, "_episode_directory", forbidden)


@pytest.mark.parametrize("role,expected", [("source", "source"), ("native", "raw"),
    ("request", "private"), ("grading", "private"), ("upload", "private")])
def test_extracted_classifier_uses_original_committed_chain(case, monkeypatch, role, expected):
    refs = {"source": case.source["id"], "native": case.source["artifact_ref"],
        "request": case.source["request_ref"], "grading": case.source["auxiliary_artifact_refs"][0],
        "upload": case.upload}
    metadata_only(case, monkeypatch)
    rows = privacy.matching_enrichr_publications(case.store, refs[role])
    assert len(rows) == 1
    assert privacy.committed_enrichr_reference_kind(case.store, rows[0], refs[role]) == expected
    assert privacy.validated_enrichr_source(case.store, case.source["id"]) == case.source


def test_no_resource_source_only_receipt_does_not_grant_any_file(case, monkeypatch):
    metadata_only(case, monkeypatch)
    before = case.store.db.total_changes
    statements = []
    case.store.db.set_trace_callback(statements.append)
    try:
        assert privacy.enrichr_reference_restriction(case.store, case.other.context, case.source["id"], "source") is None
        for reference in [*case.private, case.source["artifact_ref"]]:
            assert case.store.reference_subset([reference], plain(case.other.context.scope)) == [reference]
            assert privacy.enrichr_reference_restriction(case.store, case.other.context, reference, "artifact") is False
    finally:
        case.store.db.set_trace_callback(None)
    assert all(sql.lstrip().upper().startswith("SELECT") for sql in statements)
    assert case.store.db.total_changes == before
    assert set(case.other.receipts.known(case.other.context.episode_id)) == {case.source["id"]}
    assert not case.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=?", (case.other.run_id,)).fetchall()


def test_received_native_file_defers_without_private_file_expansion(case, monkeypatch):
    native = case.source["artifact_ref"]
    case.other.receipts.receive(case.other.context.episode_id, [native], kind="decision_input", source_index=0)
    inherited = receiver(case.store, case.other.context.scope, run_id=case.other.run_id, parent=case.other)
    metadata_only(case, monkeypatch)
    for context in (case.other.context, inherited.context):
        assert privacy.enrichr_reference_restriction(case.store, context, native, "artifact") is None
        assert all(privacy.enrichr_reference_restriction(case.store, context, ref, "artifact") is False
            for ref in case.private)
    assert privacy.enrichr_reference_restriction(case.store, case.other.context, native, "source") is False


@pytest.mark.parametrize("seed_role,expected", [("source", False), ("native", None)])
def test_original_unsaved_root_file_seed_is_literal_and_does_not_expand_sources(case, monkeypatch, seed_role, expected):
    fresh = receiver(case.store, case.other.context.scope, run_id="original-root-bootstrap", saved=False)
    metadata_only(case, monkeypatch)
    seed = case.source["id"] if seed_role == "source" else case.source["artifact_ref"]
    assert privacy.enrichr_reference_restriction(case.store, fresh.context, case.source["artifact_ref"],
        "artifact", initial_record_refs=[seed]) is expected
    assert all(privacy.enrichr_reference_restriction(case.store, fresh.context, ref, "artifact",
        initial_record_refs=[ref]) is False for ref in case.private)
    assert set(fresh.receipts.known(fresh.context.episode_id)) == set()


def test_a_child_cannot_claim_the_root_bootstrap_seed(case, monkeypatch):
    child = receiver(case.store, case.other.context.scope, run_id=case.other.run_id, parent=case.other)
    metadata_only(case, monkeypatch)
    assert privacy.enrichr_reference_restriction(case.store, child.context, case.source["artifact_ref"],
        "artifact", initial_record_refs=[case.source["artifact_ref"]]) is False


def test_private_only_scope_check_defers_native_file_authority(case, monkeypatch):
    metadata_only(case, monkeypatch)
    assert all(privacy.enrichr_reference_restriction(case.store, None, ref, "artifact", private_only=True) is False
        for ref in case.private)
    assert privacy.enrichr_reference_restriction(case.store, None, case.source["artifact_ref"],
        "artifact", private_only=True) is None
    assert privacy.enrichr_reference_restriction(case.store, None, case.source["artifact_ref"], "artifact") is False


def test_registry_runtime_and_services_apply_negative_guard_without_an_api_owner(case, monkeypatch):
    workflow = inspection_workflow(case.store, case.other)
    context = case.other.context
    metadata_only(case, monkeypatch)
    resolve = workflow.resolver(plain(context.scope), context=context)
    for ref in [*case.private, case.source["artifact_ref"]]:
        assert workflow.tools.retained_molecular_reference_access(context, ref, "artifact") is False
        assert resolve(ref, "artifact") is False
        assert workflow.services.reference_in_context(context, ref, "artifact") is False
    assert all(workflow.services.reference_in_scope(ref, context.scope, "artifact") is False for ref in case.private)
    native = case.source["artifact_ref"]
    case.other.receipts.receive(context.episode_id, [native], kind="decision_input", source_index=1)
    assert workflow.tools.retained_molecular_reference_access(context, native, "artifact") is None
    assert resolve(native, "artifact") is True
    assert workflow.services.reference_in_context(context, native, "artifact") is True
    assert workflow.episode_bindings.roles == () and not hasattr(workflow, "api_execution")
    assert not case.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=?", (context.run_id,)).fetchall()


@pytest.mark.parametrize("seed_role,expected", [("source", False), ("native", True)])
def test_runtime_bootstrap_uses_original_explicit_file_selection(case, monkeypatch, seed_role, expected):
    fresh = receiver(case.store, case.other.context.scope, run_id="runtime-bootstrap", saved=False)
    seed = case.source["id"] if seed_role == "source" else case.source["artifact_ref"]
    workflow = inspection_workflow(case.store, fresh, initial_record_refs=[seed])
    metadata_only(case, monkeypatch)
    assert workflow.resolver(plain(fresh.context.scope), context=fresh.context)(case.source["artifact_ref"], "artifact") is expected
    assert workflow.services.reference_in_context(fresh.context, case.source["artifact_ref"], "artifact") is expected
    assert set(fresh.receipts.known(fresh.context.episode_id)) == set()


def test_candidate_prefilter_ignores_unrelated_lookalikes_and_unrelated_damage(case, monkeypatch):
    unrelated = case.store.artifact(b"independent supplied File")
    fake = {key: value for key, value in case.source.items() if key not in {"id", "record_type", "origin"}}
    fake["auxiliary_artifact_refs"] = [unrelated]
    case.store.put("source", fake, origin="external")
    case.store.db.execute("UPDATE tool_operations SET scope=? WHERE name=?",
        ('{damaged', "internal.api_service.enrichr.result"))
    metadata_only(case, monkeypatch)
    monkeypatch.setattr(privacy, "committed_enrichr_reference_kind", forbidden)
    assert privacy.matching_enrichr_publications(case.store, unrelated) == []
    assert privacy.enrichr_reference_restriction(case.store, case.other.context, unrelated, "artifact") is None


def test_pending_own_row_is_not_a_committed_global_publication(case, monkeypatch):
    case.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=?",
        (case.original.run_id, case.child.episode_id))
    metadata_only(case, monkeypatch)
    assert privacy.matching_enrichr_publications(case.store, case.source["request_ref"]) == []
    assert len(privacy.matching_enrichr_publications(case.store, case.source["request_ref"],
        current_run_id=case.original.run_id)) == 1
    assert privacy.matching_enrichr_publications(case.store, case.source["request_ref"],
        current_run_id=case.other.run_id) == []


def test_fresh_store_without_runtime_tables_defers_without_creating_them(tmp_path):
    with Store(tmp_path / "fresh") as store:
        before = list(store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
        assert privacy.matching_enrichr_publications(store, "artifact_" + "a" * 64) == []
        assert privacy.enrichr_reference_restriction(store, None, "artifact_" + "a" * 64, "artifact") is None
        assert list(store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")) == before


@pytest.mark.parametrize("change", ["source_identity", "selected_action", "receipt", "native_sha", "protocol", "pending"])
def test_original_chain_tampering_is_an_integrity_failure_not_store_fallback(case, monkeypatch, change):
    key = f"{case.original.run_id}:{case.child.episode_id}:0"
    if change == "source_identity":
        value = deepcopy(case.source)
        value["retrieved_at"] = "2026-10-31T00:00:00+00:00"
        case.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(value), case.source["id"]))
    elif change in ("selected_action", "receipt", "pending"):
        if change == "selected_action":
            field, value = "action", {"kind": "tool", "tool": "api.enrichr.query", "arguments": {}}
        else:
            field = "result"
            value = json.loads(case.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=?",
                (case.original.run_id, case.child.episode_id)).fetchone()[0])
            if change == "receipt":
                value["result"]["acquisition_receipt"]["operation_key"] += ":foreign"
            else:
                value["pending_work_after_action"] = {"version": PENDING_VERSION, "captured_at": "bad", "items": []}
        case.store.db.execute("UPDATE runtime_actions SET " + field + "=? WHERE run_id=? AND episode_id=?",
            (canonical(value), case.original.run_id, case.child.episode_id))
    else:
        value = json.loads(case.store.db.execute("SELECT arguments FROM tool_operations WHERE operation_key=?",
            (key + ":publication",)).fetchone()[0])
        if change == "native_sha":
            value["snapshot_sha256"] = "0" * 64
        else:
            value["transport"]["enrichr_protocol"]["wire_profile"] = "foreign"
        case.store.db.execute("UPDATE tool_operations SET arguments=? WHERE operation_key=?",
            (canonical(value), key + ":publication"))
    metadata_only(case, monkeypatch)
    with pytest.raises(ReportBoundaryError):
        privacy.enrichr_reference_restriction(case.store, case.other.context, case.source["request_ref"], "artifact")


def test_pending_normalization_is_validated_and_never_silently_discarded():
    value = {"status": "completed", "pending_work_after_action": {"version": PENDING_VERSION,
        "captured_at": "2026-10-30T00:00:00+00:00", "items": []}}
    assert privacy.normalized_enrichr_outcome(value) == {"status": "completed"}
    assert "pending_work_after_action" in value
    value["pending_work_after_action"]["items"] = False
    with pytest.raises(ValueError):
        privacy.normalized_enrichr_outcome(value)


@pytest.mark.parametrize("change", ["run", "scope", "path"])
def test_raw_file_receipt_does_not_override_a_substituted_receiver_context(case, monkeypatch, change):
    native = case.source["artifact_ref"]
    case.other.receipts.receive(case.other.context.episode_id, [native], kind="initial")
    context = case.other.context
    if change == "run":
        context = replace(context, run_id="foreign-receiver")
    elif change == "scope":
        context = replace(context, scope={"subject_refs": []})
    else:
        context = replace(context, path=(("annotation", "other-root"),))
    metadata_only(case, monkeypatch)
    assert privacy.enrichr_reference_restriction(case.store, context, native, "artifact") is False
