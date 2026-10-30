"""Shared retained-target consumers with real 397/406/407 authority.

The native structures are small synthetic engineering fixtures. This uses the
real ExecutionEpisodes binding and Store/Journal, but not the outer Workflow
chooser or a configured model; packet410 owns that separate verification.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from importlib import import_module
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_protein_structure_acquisition import retained_protein_structure_file
from gene_annotation_episode.native_protein_structure_returns import (
    FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
)
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.state import Store


RUNTIME = import_module("verification.tool_graders_protein_structure_result_host_2026-10-27_407.fixture_helpers")


def forbidden(*args, **kwargs):
    raise AssertionError("retained target attempted fresh handoff, producer or native analysis access")


def selected(*, saved=None, parameters=None, return_saved=True):
    return {"version": "protein_structure_result_selector_v1",
        "acquisition": "complete_bound_bundle" if saved is None else "retained_sheet_only",
        "saved_sheet": deepcopy(saved), "parameters": deepcopy(parameters),
        "projections": [{"projection_id": "requested", "family": "comparison_summary",
            "members": {"kind": "comparison"}, "fields": ["evaluation_sse", "evaluation_rmsd", "evaluation_used_count"],
            "window": None, "delivery_kind": "values"}],
        "return_saved_sheet": return_saved, "sequence_allowed_uses": []}


def binding(f, resources=None):
    return ExecutionEpisodes(None, store=f.store, directory=f.directory / "runtime", run_id=f.run_id,
        resources=resources or {f.assignment["resource_id"]: f.config}, initial_information={},
        tool_registry={}, handoff_unit=2, acquired_record_unit=3,
        log_window_bytes=8192, log_roles=("stdout", "stderr"))


async def collect(f, child, *, commit=True):
    key = f.select(child)
    result = await f.owner.execute(child, "execution.results.collect", {}, key)
    assert result["status"] == "completed", result
    if commit:
        f.commit(child, result)
        f.episode_receipts.receive(child.episode_id, result["record_refs"], kind="own_action", source_index=0)
    return result


def child(f, *, selection=None):
    index = f.next_child
    f.next_child += 1
    return f.child(index=index, selector=selection or f.saved_selection,
        schema=RUNTIME.schema_for(PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE))


def artifact_path(store, reference):
    sha = store.get(reference)["sha256"]
    return store.path / "artifacts" / sha[:2] / sha


def action_rows(f):
    return [dict(row) for row in f.store.db.execute(
        "SELECT * FROM runtime_actions WHERE run_id=? ORDER BY episode_id,decision_index", (f.run_id,))]


@pytest.fixture(scope="module")
def actual(tmp_path_factory):
    directory = tmp_path_factory.mktemp("retained-target-actual")
    with Store(directory / "store") as store:
        f = RUNTIME.HostFixture(store, directory / "fixture", kind="compare", run_id="protein412-actual")
        asyncio.run(f.live())
        f.owner = binding(f)
        f.host, f.returns = f.owner.native_protein_structure_results, f.owner.native_protein_structure_returns
        original_assignment = {"version": "execution_results_assignment_v1", "handoff_ref": f.handoff,
            "selector": selected()}
        assert f.owner.prepare_assignment(f.root, "results", original_assignment, f.scope, "commission-original") == original_assignment
        f.original = f.child(index=1, assignment=original_assignment,
            schema=RUNTIME.schema_for(PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE))
        f.owner.initialize(f.original)
        f.original_result = asyncio.run(collect(f, f.original))
        f.descriptor, = f.original_result["result"]["publication"]["facts"][SAVED_SOURCE]
        f.parameters = deepcopy(f.requested["native_protein_structure"]["request"]["parameters"])
        f.parameters["distance_threshold_A"] = 2.0
        f.saved_selection = selected(saved=f.descriptor, parameters=f.parameters)
        # This sibling's original commission predates receipt of the descriptor.
        f.hidden = f.child(index=2, selector=f.saved_selection,
            schema=RUNTIME.schema_for(PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE))
        f.returned(f.original)
        f.pending = f.child(index=3, selector=selected(), schema=RUNTIME.schema_for(SAVED_SOURCE))
        f.owner.initialize(f.pending)
        f.pending_result = asyncio.run(collect(f, f.pending, commit=False))
        f.next_child = 4
        f.original_facts = f.owner.facts(f.original, {})
        f.original_credit = f.owner.credit_view(f.original, None)
        f.original_completion = f.host.completion(f.original)
        f.original_pair_bytes = {name: retained_protein_structure_file(store, f.descriptor[name]).read_bytes()
            for name in ("sheet_file", "original_components_file")}
        source = store.get(f.handoff)
        f.removed_handoff = {name: source[name] for name in ("artifact_ref", "request_ref")}
        for reference in f.removed_handoff.values():
            artifact_path(store, reference).unlink()
        assert all(retained_protein_structure_file(store, f.descriptor[name]).is_file()
            for name in f.original_pair_bytes)
        yield f


def deny_producer(monkeypatch, f):
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode import native_protein_structure_acquisition as acquisition
    from gene_annotation_episode import native_protein_structure_results as results
    from gene_annotation_episode import native_protein_structure_worker as worker
    for name in ("read_target", "describe_target", "observe_target", "read_file"):
        monkeypatch.setattr(f.owner.job_progress_provider.targets, name, forbidden)
    monkeypatch.setattr(acquisition, "_producer_file", forbidden)
    monkeypatch.setattr(results, "capture_local_protein_structure_bundle", forbidden)
    monkeypatch.setattr(worker, "execute_protein_structure_request", forbidden)
    prepare = native_lifecycle.prepare_job
    def saved_worker_only(command, **kwargs):
        assert command[1:4] == ["-B", "-m", "gene_annotation_episode.protein_structure_result_worker"]
        assert len(command) == 5
        assert json.loads(Path(command[4]).read_bytes())["mode"] == "saved_sheet_recalculation"
        return prepare(command, **kwargs)
    monkeypatch.setattr(native_lifecycle, "prepare_job", saved_worker_only)


def test_shared_saved_commission_initialize_execute_and_metadata(actual, monkeypatch):
    f = actual
    proposal = {"version": "execution_results_assignment_v1", "handoff_ref": f.handoff,
        "selector": f.saved_selection}
    deny_producer(monkeypatch, f)
    assert f.owner.prepare_assignment(f.root, "results", proposal, f.scope, "commission-saved") == proposal
    later = child(f)
    f.owner.initialize(later)
    expected_refs = [f.handoff, f.descriptor["custody"]["source_ref"],
        f.descriptor["custody"]["bundle_artifact_ref"], f.descriptor["sheet_file"]["artifact_ref"],
        f.descriptor["original_components_file"]["artifact_ref"]]
    assert f.owner.initial_references(later) == expected_refs
    before = f.owner.decision_context(later, {})
    assert before["execution_target"] == f.target
    description = before["execution_target_description"]
    assert description["called_operation"] == f.original_result["result"]["body"]["handoff_proof"]["body"]["receipt"]["tool_name"]
    assert description["result_selection"] == f.saved_selection
    assert description["status_meanings"]["fresh_native_observation"] is False
    assert description["extractors"][-1]["calculator_parameters"] == f.parameters
    result = asyncio.run(collect(f, later))
    receipt = result["result"]
    assert receipt["publication"]["delivery_complete"]
    assert receipt["body"]["worker"]["plan"]["mode"] == "saved_sheet_recalculation"
    assert receipt["publication"]["facts"][SAVED_SOURCE] == [f.descriptor]
    assert receipt["body"]["original_custody"] == f.descriptor["custody"]
    assert receipt["publication"]["custody"] != f.descriptor["custody"]
    files = receipt["body"]["qualified_files"]
    for name, raw in f.original_pair_bytes.items():
        assert files[name] == f.descriptor[name]
        assert retained_protein_structure_file(f.store, files[name]).read_bytes() == raw
    assert files["components_file"] != f.descriptor["original_components_file"]
    components = json.loads(retained_protein_structure_file(f.store, files["components_file"]).read_bytes())
    assert components["parameters"] == f.parameters
    baseline = json.loads(f.original_pair_bytes["original_components_file"])
    assert baseline["parameters"]["distance_threshold_A"] is None
    assert baseline["evaluation"]["above_threshold_count"]["state"] == "not_applicable"
    assert components["evaluation"]["distance_threshold_A"]["value"] == 2.0
    assert components["evaluation"]["above_threshold_count"]["value"] == 0
    assert components["evaluation"]["above_threshold_fraction"]["value"] == 0
    assert components["counts"]["evaluation_used_count"]["value"] == 4
    assert components["evaluation"]["evaluation_rmsd"] == baseline["evaluation"]["evaluation_rmsd"]
    assert f.owner.credit_view(later, None)["credit"] == 0
    assert f.owner.facts(f.original, {}) == f.original_facts
    assert f.owner.credit_view(f.original, None) == f.original_credit
    (f.directory / "shared-retained-result-example.json").write_text(canonical({
        "removed_handoff_artifacts": f.removed_handoff, "original_descriptor": f.descriptor,
        "original_parameters": baseline["parameters"], "selected_parameters": components["parameters"],
        "original_evaluation": baseline["evaluation"], "later_evaluation": components["evaluation"],
        "original_credit": f.original_credit, "later_credit": f.owner.credit_view(later, None),
        "later_custody": receipt["publication"]["custody"], "original_pair_unchanged": True,
        "description_called_operation": description["called_operation"]}) + "\n")


def test_original_completed_replay_and_description_need_no_artifact_bytes(actual, monkeypatch):
    f = actual
    deny_producer(monkeypatch, f)
    monkeypatch.setattr(f.store, "get_artifact", forbidden)
    monkeypatch.setattr(f.host, "_prepare_worker", forbidden)
    before = action_rows(f)
    assert f.owner._target(f.original) == f.target
    f.owner.initialize(f.original)
    description = f.owner.decision_context(f.original, {})["execution_target_description"]
    assert description["called_operation"] == "practical.job.start"
    key = f.original_result["result"]["body"]["intent"]["operation_key"]
    assert asyncio.run(f.owner.execute(f.original, "execution.results.collect", {}, key)) == f.original_result
    assert action_rows(f) == before
    assert f.owner.facts(f.original, {}) == f.original_facts
    assert f.owner.credit_view(f.original, None) == f.original_credit
    assert f.host.completion(f.original) == f.original_completion


def test_pending_private_controls_and_unrelated_completed_sibling_do_not_supply_target(actual):
    f = actual
    key = f.pending_result["result"]["body"]["intent"]["operation_key"]
    assert (f.host.receipts.action_directory(episode_id=f.pending.episode_id, operation_key=key) / "receipt.json").is_file()
    assert f.owner._retained_protein_result(f.pending, plain(f.pending.assignment), f.scope) is None
    assert f.host.receipts.completed_receipts(f.pending) == []
    with pytest.raises(ValueError, match="execution_target_unavailable_or_outside_scope"):
        f.owner._target(f.pending)
    assert f.owner._retained_protein_result(f.root, plain(f.original.assignment), f.scope) is None
    with pytest.raises(ValueError, match="execution_target_unavailable_or_outside_scope"):
        f.owner.prepare_assignment(f.root, "results", plain(f.original.assignment), f.scope, "fresh-original")


def test_changed_original_assignment_cannot_borrow_completed_context(actual):
    f = actual
    proposal = plain(f.original.assignment)
    proposal["selector"]["return_saved_sheet"] = False
    assert f.owner._retained_protein_result(f.original, proposal, f.scope) is None
    forged = replace(f.original, assignment=proposal)
    with pytest.raises(ProteinStructureOperandError, match="original_commission_mismatch"):
        f.owner._target(forged)


@pytest.mark.parametrize("case", ["hidden", "different_descriptor", "sibling_descriptor", "wrong_handoff"])
def test_saved_target_requires_exact_received_descriptor_and_handoff(actual, case):
    f = actual
    proposal = {"version": "execution_results_assignment_v1", "handoff_ref": f.handoff,
        "selector": deepcopy(f.saved_selection)}
    receiver, code = f.root, "saved_sheet_not_received"
    if case == "hidden":
        receiver = f.hidden
    elif case == "different_descriptor":
        proposal["selector"]["saved_sheet"]["sheet_file"]["byte_length"] += 1
    elif case == "sibling_descriptor":
        proposal["selector"]["saved_sheet"] = deepcopy(f.pending_result["result"]["publication"]["facts"][SAVED_SOURCE][0])
    else:
        proposal["handoff_ref"] = f.descriptor["custody"]["source_ref"]
        code = "original_commission_mismatch"
    with pytest.raises(ValueError, match=code):
        f.owner._retained_protein_result(receiver, proposal, f.scope)


def test_saved_target_checks_requested_scope(actual):
    f = actual
    wrong_scope = {**f.scope, "segments": [{"target_ref": f.scope["subject_refs"][0],
        "start": 0, "end": 2, "unit": "aa"}]}
    with pytest.raises(ValueError, match="scope_segments_outside_parent"):
        f.owner._retained_protein_result(f.root, plain(f.hidden.assignment), wrong_scope)


def test_saved_target_rejects_foreign_run_context(actual):
    f = actual
    foreign = replace(f.root, run_id="another-run")
    with pytest.raises(ProteinStructureOperandError, match="original_commission_mismatch"):
        f.owner._retained_protein_result(foreign, plain(f.hidden.assignment), f.scope)


@pytest.mark.parametrize("change,code", [
    ("missing_resource", "practical_execution_resource_identity_conflict"),
    ("workspace", "practical_write_outside_workspace"),
    ("operation", "native_protein_structure_operation_mode_software_not_bound"),
    ("mode", "native_protein_structure_operation_mode_software_not_bound"),
    ("software", "native_protein_structure_operation_mode_software_not_bound"),
])
def test_saved_target_requires_current_bound_resource(actual, change, code):
    f = actual
    resource = deepcopy(f.config)
    resource_id = f.assignment["resource_id"]
    if change == "missing_resource":
        resource_id = "another-configured-resource"
    elif change == "workspace":
        resource["workspace"] = str(f.directory / "different-workspace")
    elif change == "operation":
        resource["native_protein_structure"][0].update(operation="inspect", scientific_mode=None)
    elif change == "mode":
        resource["native_protein_structure"][0]["scientific_mode"] = "evaluate_declared_transform_ca"
    else:
        resource["native_protein_structure"][0]["software"]["python_sha256"] = "a" * 64
    changed = binding(f, {resource_id: resource})
    with pytest.raises(ValueError, match=code):
        changed._retained_protein_result(f.root, plain(f.hidden.assignment), f.scope)


@pytest.mark.parametrize("field", ["sheet_file", "original_components_file"])
@pytest.mark.parametrize("damage,code", [("missing", "retained_artifact_missing"), ("changed", "input_digest_mismatch")])
def test_current_saved_pair_failure_preserves_history(actual, monkeypatch, field, damage, code):
    f = actual
    later = child(f)
    f.owner.initialize(later)
    path = retained_protein_structure_file(f.store, f.descriptor[field])
    raw = path.read_bytes()
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed retained scientific operand")
    try:
        deny_producer(monkeypatch, f)
        assert f.owner._target(later) == f.target
        assert f.owner.decision_context(later, {})["execution_target"] == f.target
        with pytest.raises(ProteinStructureOperandError, match=code):
            f.owner.initial_references(later)
        failed = asyncio.run(collect(f, later))["result"]
        assert not failed["publication"]["delivery_complete"]
        assert any(row["issue"]["code"] == code for row in failed["publication"]["facts"][FAILURE_SOURCE])
        assert all(value is None for value in failed["body"]["qualified_files"].values())
        assert f.host.completion(later) is None
        assert f.owner.credit_view(later, None)["credit"] == 0
        assert f.owner.facts(f.original, {}) == f.original_facts
        assert f.owner.credit_view(f.original, None) == f.original_credit
        assert f.host.completion(f.original) == f.original_completion
    finally:
        path.write_bytes(raw)
