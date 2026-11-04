"""Reconstruct a commissioned three-slot child with actual application state.

These are engineering fixtures. No provider inference, scientific operation,
controller observation or native job runs in this module.
"""
import asyncio
from copy import deepcopy
import json
import shutil

import pytest

from method_loop import Episode
from method_loop.durable import DurableExecutionError, content_digest, validate_commission

from gene_annotation_episode import independent_execution as independent
from gene_annotation_episode import providers
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_composition import reopen_scientific_binding
from gene_annotation_episode.investigation_progress import ScientificFindingProgress
from gene_annotation_episode.numerical import YieldController
from gene_annotation_episode.runtime import Workflow, TypedReportContract, assemble_workflow, run_workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from test_scientific_process_library import independent_source, write


def forbidden(*args, **kwargs):
    raise AssertionError("reconstruction must not execute work")


class UnusedProvider:
    complete = forbidden


class SavedBeforeRoot(Exception):
    pass


def persist_scientific_run(tmp_path, monkeypatch):
    """Save real entrypoint configuration, before any root is constructed."""
    source, workspace, directory = tmp_path / "source", tmp_path / "workspace", tmp_path / "run"
    independent_source(source, extra=True)
    library = ScientificProcessLibrary.freeze(directory / "scientific-process-library", source=source)
    with Store(workspace) as store:
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=source,
            tool_catalog=build_tools(store).catalog(), child_roles=("scientific_process",))
        target = store.create_problem(raw_sequence="ATGAAATAA", molecule="dna", role="gene")["subject_refs"][0]
        with monkeypatch.context() as setup:
            def stop_before_root(*args, **kwargs):
                raise SavedBeforeRoot()
            setup.setattr(Workflow, "build", stop_before_root)
            with pytest.raises(SavedBeforeRoot):
                asyncio.run(run_workflow(store, build_tools(store), run_dir=directory,
                    provider=UnusedProvider(), initial_known_record_refs=[target],
                    episode_binding_descriptors=[descriptor]))
        manifest = json.loads((directory / "run.json").read_text())
        assert manifest["episode_bindings"] == [descriptor]
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == 0
    return {"source": source, "workspace": workspace, "directory": directory,
        "manifest": manifest, "descriptor": descriptor, "target": target}


def commission_fixture(saved, *, revision=False):
    """Construct parent/child records without running either Episode loop."""
    workspace, directory = saved["workspace"], saved["directory"]
    with Store(workspace) as store:
        run_id, settings = independent._settings(store, directory)
        options = independent._standard_bindings(store, directory, settings)
        workflow = assemble_workflow(store, build_tools(store), UnusedProvider(), directory,
            run_id, settings, episode_binding_descriptors=settings["episode_bindings"],
            **{key: value for key, value in options.items() if key != "binding_definitions"})
        scope = store.validate_scope({"subject_refs": [saved["target"]]})
        parent = workflow.build("annotation", "root", settings["goal"], scope)
        binding = workflow.episode_bindings.for_role("scientific_process")
        schema = obj({"finding": {"type": "string", "enum": ["unknown", "qualified"]},
            "subjects": {"type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "input"}, "x-source": "subject_refs"},
            "approaches": binding.fact_sources("scientific_process")["scientific_process_results"]["report_schema"]})
        purpose = "Return the original bounded fixture interpretation"
        initial = {"finding": "unknown"}
        contract = TypedReportContract(purpose, schema, workflow.resolver(scope, grain="scientific_process"))
        selection = {"version": "scientific_process_selection_v2",
            "annotation_ref": binding.library.reference("A01"),
            "thought_ref": binding.library.reference("P77"),
            "tools": ["state.query"]}
        assignment = {"selection": selection, "evidence_refs": [saved["target"]],
            "constraints": {"fixture_only": True}, "context": {"condition": "initial"}}
        objective = "Investigate the original assigned relationship"
        prepared = binding.prepare_invocation(workflow.binding_context(parent.source),
            "scientific_process", assignment, scope, "fixture:construct", invocation={
                "objective": objective, "purpose": purpose, "report_schema": contract.schema,
                "initial_report": initial})
        child = workflow.build("scientific_process", "selected_child", objective, scope,
            parent=parent.goal, parent_path=parent.source.path, contract=contract, initial=initial,
            episode_assignment=prepared["assignment"], scientific_process=prepared["scientific_process"])
        if revision:
            # Preparation is a completed ordinary action; it executes no science
            # and supplies no controller observation or implicit commission.
            arguments = {"thought_ref": binding.library.reference("P01"),
                "tools": ["state.query"]}
            selected = {"kind": "tool", "tool": "process.revise", "arguments": arguments}
            outcome = asyncio.run(workflow.execute(child.source, "process.revise", arguments,
                decision_index=0, operation_key=f"{run_id}:{child.source.episode_id}:0"))
            assert outcome["status"] == "completed"
            workflow.journal.save("runtime_actions", {"episode_id": child.source.episode_id,
                "decision_index": 0, "action": json.dumps(selected), "result": json.dumps(outcome),
                "credit": 0})
            saved["preparation"] = deepcopy(outcome)
            parent = child
            revision_selection = {"kind": "episode_child", "role": "scientific_process",
                "goal": "Investigate the separately assigned alternative explanation", "scope": scope,
                "purpose": "Return the alternative interpretation and recorded process results",
                "schema_json": json.dumps(schema), "initial_report_json": json.dumps(initial),
                "assignment": {**assignment, "selection": outcome["result"]["selection"],
                    "revision_origin": outcome["revision_origin"]}}
            child = workflow.selected(parent.source, revision_selection, 1).child
        saved["original_known_refs"] = tuple(workflow.receipts.known(child.source.episode_id))
        spec = {"version": "episode_commission_v1", "handle": "episode:scientific_fixture_child",
            "operation_key": run_id + ":scientific_fixture", "run_id": run_id,
            "parent": {"episode_id": parent.source.episode_id, "goal_id": parent.goal.goal_id,
                "path": [list(part) for part in parent.source.path]},
            "child": {"episode_id": child.source.episode_id, "role": "scientific_process", "key": child.key,
                "path": [list(part) for part in child.source.path], "request": child.request.as_record(),
                "scope": scope},
            "input_versions": [{"reference": saved["target"], "version": None,
                "content_sha256": content_digest(store.get(saved["target"]))}],
            "runtime_binding": independent.make_runtime_binding(store, directory),
            "constraints": {"fixture_only": True}, "resource_selection": None,
            "expectation_snapshot_refs": []}
        validate_commission(spec)
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    return spec


def provider_fixture(monkeypatch):
    events = []

    class FixtureProvider:
        def __init__(self, *args, **kwargs):
            events.append(("constructed", None))

        async def __aenter__(self):
            events.append(("entered", None))
            return self

        async def __aexit__(self, *exception):
            events.append(("exited", None))

        async def release(self, episode_id):
            events.append(("released", episode_id))

        complete = forbidden

    monkeypatch.setattr(providers, "ModelConnection", FixtureProvider)
    return events


@pytest.mark.parametrize("source_change", ["changed", "deleted"])
def test_saved_factory_uses_original_snapshot_and_literal_mapping(tmp_path, monkeypatch, source_change):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    original = deepcopy(saved["descriptor"])
    if source_change == "changed":
        path = saved["source"] / "entries/P77.json"
        body = json.loads(path.read_text())
        body["decision_guidance"] = ["A later instruction must not replace the commissioned process."]
        write(path, body)
    else:
        shutil.rmtree(saved["source"])
    services = object()
    factory, = independent._saved_episode_factories(saved["manifest"], saved["directory"])
    restored = factory(services)
    assert restored.services is services
    assert restored.as_record() == original
    assert restored.library.resolve(restored.library.reference("P77"))["decision_guidance"] == [
        "Retain two rival explanations after a mixed result."]
    assert restored.tool_library.as_record() == original["configuration"]["tool_library"]
    assert restored.roles == ("scientific_process",)


def test_known_scientific_descriptor_restores_standard_capability_without_executing(tmp_path, monkeypatch):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    before = deepcopy(saved["manifest"])
    for owner, names in ((providers.ModelConnection, ("__init__", "__aenter__", "complete")),
            (Episode, ("run_async",)), (Workflow, ("build",)),
            (YieldController, ("__init__", "observe", "state")),
            (ScientificFindingProgress, ("__call__",))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)
    binding = independent.make_runtime_binding(saved["workspace"], saved["directory"])
    assert binding["arguments"]["kind"] == "standard_default"
    assert binding["settings_sha256"] == content_digest({
        key: value for key, value in before.items() if key != "run_id"})
    with Store(saved["workspace"]) as store:
        _, settings = independent._settings(store, saved["directory"])
        options = independent._standard_bindings(store, saved["directory"], settings)
        independent._check_bindings(options, settings)
        assert options['project_annotation_score'] is None
        assert 'annotation_score' not in settings['bindings']
        assert options["binding_definitions"] == settings["binding_definitions"]
        assert options["initial_known_record_refs"] == [saved["target"]]
        for table in ("runtime_episodes", "runtime_model_calls", "runtime_actions", "runtime_observations"):
            assert store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert json.loads((saved["directory"] / "run.json").read_text()) == before
    assert not (saved["directory"] / "providers").exists()


def test_reopening_descriptor_requires_actual_run_directory(tmp_path, monkeypatch):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    with pytest.raises(DurableExecutionError) as error:
        reopen_scientific_binding(None, descriptor=saved["descriptor"], directory=None)
    assert error.value.failure["code"] == "unavailable_binding"


@pytest.mark.parametrize("identity", ["library", "tool_library", "mother", "old_v1"])
def test_descriptor_identity_drift_is_rejected_by_known_factory(tmp_path, monkeypatch, identity):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    descriptor = deepcopy(saved["descriptor"])
    if identity == "library":
        descriptor["configuration"]["library"]["library_id"] = "0" * 64
    elif identity == "tool_library":
        descriptor["configuration"]["tool_library"]["catalog_sha256"] = "0" * 64
    elif identity == "mother":
        descriptor["implementation_sha256"] = "0" * 64
    else:
        descriptor["version"] = "scientific_process_episodes_v1"
    events = provider_fixture(monkeypatch)
    with pytest.raises(DurableExecutionError) as error:
        reopen_scientific_binding(None, descriptor=descriptor, directory=saved["directory"])
    assert error.value.failure["code"] == (
        "unavailable_binding" if identity == "old_v1" else "identity_conflict")
    assert events == []


@pytest.mark.parametrize("drift", ["entry", "sources", "manifest", "missing_snapshot", "caller_mapping", "old_v1"])
def test_commission_rejects_snapshot_or_original_mapping_drift_before_provider_entry(tmp_path, monkeypatch, drift):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    spec = commission_fixture(saved)
    if drift in {"caller_mapping", "old_v1"}:
        # Both current settings copies agree. The original C1 settings pin must
        # still reject this changed caller map before constructing a provider.
        manifest = json.loads((saved["directory"] / "run.json").read_text())
        descriptor = manifest["episode_bindings"][0]
        if drift == "caller_mapping":
            descriptor["configuration"]["tool_library"]["catalog_sha256"] = "0" * 64
        else:
            descriptor["version"] = "scientific_process_episodes_v1"
        with Store(saved["workspace"]) as store:
            settings = {key: value for key, value in manifest.items() if key != "run_id"}
            store.db.execute("UPDATE runtime_runs SET settings=? WHERE run_id=?",
                (json.dumps(settings), manifest["run_id"]))
            store.db.commit()
        write(saved["directory"] / "run.json", manifest)
    elif drift == "missing_snapshot":
        shutil.rmtree(saved["directory"] / "scientific-process-library")
    else:
        relative = {"entry": "entries/P77.json", "sources": "sources/P77.json", "manifest": "index.json"}[drift]
        path = saved["directory"] / "scientific-process-library" / relative
        path.write_bytes(path.read_bytes() + b" \n")
    events = provider_fixture(monkeypatch)

    async def reopen():
        async with independent.open_commission(spec):
            pytest.fail("a drifted commission was reconstructed")

    with pytest.raises(DurableExecutionError) as error:
        asyncio.run(reopen())
    assert error.value.failure["code"] in {"identity_conflict", "unavailable_binding"}
    assert events == []
    assert not (saved["directory"] / "providers").exists()


@pytest.mark.parametrize("revision", [False, True], ids=["ordinary", "revision"])
def test_open_commission_preserves_full_filled_request_after_source_deletion(tmp_path, monkeypatch, revision):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    spec = commission_fixture(saved, revision=revision)
    original = deepcopy(spec)
    shutil.rmtree(saved["source"])
    events = provider_fixture(monkeypatch)

    async def reopen():
        async with independent.open_commission(spec) as reconstructed:
            child = reconstructed["episode"]
            workflow = child.source.workflow
            assert child.request.as_record() == original["child"]["request"]
            assert child.source.path == tuple(tuple(part) for part in original["child"]["path"])
            assert workflow.execution_binding == original["runtime_binding"]
            assert workflow.episode_bindings.as_record() == [saved["descriptor"]]
            binding = workflow.episode_bindings.for_role("scientific_process")
            frame = binding.decision_context(workflow.binding_context(child.source), {})["scientific_process"]
            assert frame["thought"]["id"] == ("P01" if revision else "P77")
            assert frame["selection"] == original["child"]["request"]["message"]["scientific_process"]["selection"]
            assert [entry["name"] for entry in frame["tools"]] == ["state.query"]
            assert child.request.report_contract.as_record() == original["child"]["request"]["report_contract"]
            assert child.request.message.as_record()["scientific_invocation_ref"] == scientific_invocation_ref(
                spec["run_id"], spec["child"]["path"])
            if revision:
                origin = child.request.message.as_record()["episode_assignment"]["revision_origin"]
                assert origin == saved["preparation"]["revision_origin"]
                prepared = workflow.services.scientific_preparation(workflow.binding_context(child.source),
                    origin["preparation_operation_ref"], owner="parent")
                assert prepared["revision_origin"] == origin
                assert prepared["proposal"] == saved["preparation"]["result"]
            assert reconstructed["context"].path == tuple(tuple(part) for part in original["parent"]["path"])
            assert set(workflow.receipts.known(child.source.episode_id)) == set(saved["original_known_refs"])
            assert saved["target"] in saved["original_known_refs"]
            assert workflow.journal.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0

    asyncio.run(reopen())
    assert spec == original
    assert events == [("constructed", None), ("entered", None),
        ("released", spec["child"]["episode_id"]), ("exited", None)]
    with Store(saved["workspace"]) as store:
        assert store.db.execute("SELECT count(*) FROM runtime_episodes").fetchone()[0] == (3 if revision else 2)
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == (2 if revision else 0)
        for table in ("runtime_model_calls", "runtime_observations"):
            assert store.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


@pytest.mark.parametrize("field", ["parent_invocation_ref", "preparation_operation_ref"])
def test_commission_rejects_replaced_original_revision_origin_before_provider_entry(tmp_path, monkeypatch, field):
    saved = persist_scientific_run(tmp_path, monkeypatch)
    spec = commission_fixture(saved, revision=True)
    original = deepcopy(spec)
    prefix = "scientific_invocation_" if field == "parent_invocation_ref" else "operation_"
    spec["child"]["request"]["message"]["episode_assignment"]["revision_origin"][field] = prefix + "0" * 24
    events = provider_fixture(monkeypatch)

    async def reopen():
        async with independent.open_commission(spec):
            pytest.fail("a replaced original revision origin was reconstructed")

    with pytest.raises(DurableExecutionError) as error:
        asyncio.run(reopen())
    assert error.value.failure["code"] == "identity_conflict"
    assert events == []
    assert not (saved["directory"] / "providers").exists()
    with Store(saved["workspace"]) as store:
        assert json.loads(store.db.execute("SELECT request FROM runtime_episodes WHERE episode_id=?",
            (original["child"]["episode_id"],)).fetchone()[0]) == original["child"]["request"]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
