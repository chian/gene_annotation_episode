"""Engineered backend controls with real receipt/action readers, no native science.

The selected runtime identities are labelled test fixtures. Lifecycle calls are
replaced by the existing explicit engineering controls; no native unit starts.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import shutil
import threading
from types import MethodType, SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.genomic_overlap_result_receipts import read_control
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.molecular_measurement_tools import authenticate_molecular_invocation, MolecularOperationUnpublished
from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_tools as tools
from tests.test_molecular_sequence_ordinary import selected_call, _lifecycle
from tests.test_molecular_sequence_ordinary_results import ordinary_owner, _roles
from tests.test_orf_sequence_operand import _external, _feature


def _configuration(call, *, resource_id="chosen-resource", ordinal=0, two_bindings=False):
    selected = call["selected"]
    binding = dict(version=tools.BINDING_VERSION, operation=tools.ORF_TOOL,
        deployment=deepcopy(selected["deployment"]), software=deepcopy(selected["software"]))
    bindings = [deepcopy(binding), deepcopy(binding)] if two_bindings else [binding]
    if two_bindings:
        bindings[1]["software"]["python_version"] = "second explicit engineering deployment"
    resources = {resource_id: dict(kind="local", workspace=selected["workspace"], policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=bindings)}
    environments = [dict(operation=tools.ORF_TOOL, resource_id=resource_id,
        binding_ordinal_0based=ordinal, environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


@pytest.fixture
def backend_case(ordinary_owner, monkeypatch):
    value = ordinary_owner
    # Replace the earlier fixture's unstarted engineering reservation after
    # recording the real receipt manifest in this fixture's original context.
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    value.calls.clear()
    manifest = value.receipts.manifest(value.context.episode_id)
    request = value.context.as_record()["request"]
    request["message"]["knowledge_inheritance"] = manifest
    value.context = BindingContext(value.context.run_id, value.context.episode_id, value.context.role,
        value.context.path, value.context.scope, value.context.assignment, request)
    value.call["context"] = value.context
    value.store.db.execute("UPDATE runtime_episodes SET request=? WHERE run_id=? AND episode_id=?",
        (canonical(request), value.context.run_id, value.context.episode_id))
    value.receipts.receive(value.context.episode_id, [value.call["arguments"]["subject_ref"]], kind="initial")
    value.store.db.commit()
    value.owner.services = SimpleNamespace(engineering_fixture=True)
    value.registry.bind_molecular_sequence_results(value.host)
    input_owner = SimpleNamespace(store=value.store, run_id=value.context.run_id,
        resolve_received_reference=lambda *_: None)
    value.input_binding = MolecularSequenceInputBindings(input_owner)
    value.events = []
    def reader(context, reference, namespace, **kwargs):
        value.events.append(("subject_admission", namespace))
        assert kwargs == {"subject_metadata_only": True}
        return value.input_binding.read_received_subject(context, reference, namespace)
    value.reader = reader
    resources, environments = _configuration(value.call)
    value.owner.resources = deepcopy(resources)
    value.configuration = tools.normalize_molecular_sequence_configuration(resources, environments, value.registry.local_job_policy)
    value.backend = tools.OrdinaryMolecularSequenceTools(value.registry, configuration=value.configuration)
    freeze = value.registry._prepare_orf_sequence_operand
    def freeze_once(*args, **kwargs):
        assert value.events and value.events[-1][0] == "subject_admission"
        value.events.append("freeze_existing_sequence_owner")
        assert len(value.host._active) == 1
        return freeze(*args, **kwargs)
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", freeze_once)
    prepare = ordinary.prepare_ordinary_orf_attempt
    def prepare_existing(**kwargs):
        value.events.append("prepare_original")
        assert len(value.host._active) == 1 and not value.store.db.in_transaction
        prepared = prepare(**kwargs)
        value.prepared = prepared
        if not (Path(prepared["plan"]["attempt_directory"]) / "attempt-bundle.json").exists():
            _roles(value)
        _lifecycle(monkeypatch, prepared, views=("returned",))
        return prepared
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", prepare_existing)
    save = value.registry._save
    def save_inside_lease(*args, **kwargs):
        assert len(value.host._active) == 1 and value.store.db.in_transaction
        value.events.append("save_under_same_lease")
        return save(*args, **kwargs)
    monkeypatch.setattr(value.registry, "_save", save_inside_lease)
    publish = value.host.publish_ordinary_orf
    def publish_inside_lease(*args, **kwargs):
        assert len(value.host._active) == 1 and value.store.db.in_transaction
        value.events.append("publish_under_same_lease")
        return publish(*args, **kwargs)
    monkeypatch.setattr(value.host, "publish_ordinary_orf", publish_inside_lease)
    return value


async def _execute(value, *, backend=None):
    context = value.context
    with value.registry.current_invocation(context, read_received=value.reader, tool_name=tools.ORF_TOOL,
            arguments=value.call["arguments"], operation_key=value.operation_key):
        authority = authenticate_molecular_invocation(value.registry, tools.ORF_TOOL, value.call["arguments"],
            context.as_record()["scope"], value.operation_key)
        return await (backend or value.backend).execute(value.call["arguments"], scope=context.as_record()["scope"],
            operation_key=value.operation_key, authority=authority)


def test_configuration_selects_explicit_ordinal_and_does_not_choose_first(selected_call):
    call, _calls = selected_call
    resources, environments = _configuration(call, ordinal=1, two_bindings=True)
    configuration = tools.normalize_molecular_sequence_configuration(resources, environments, call["policy"])
    selected = tools.compile_ordinary_orf_selection(configuration)
    assert configuration["bindings"][0]["binding_ordinal_0based"] == 1
    assert selected["software"]["python_version"] == "second explicit engineering deployment"
    assert set(selected) == {"resource_id", "workspace", "deployment", "software", "environment"}
    resources["chosen-resource"]["native_molecular_sequence"][1]["software"]["python_version"] = "changed caller dict"
    assert selected["software"]["python_version"] == "second explicit engineering deployment"


def test_no_selection_has_no_advertised_tool_even_with_available_bindings(selected_call):
    call, _calls = selected_call
    resources, _environments = _configuration(call, two_bindings=True)
    assert tools.normalize_molecular_sequence_configuration(resources, [], call["policy"]) is None
    assert tools.molecular_sequence_tool_catalog(None) == {}
    with pytest.raises(ValueError, match="configuration_required"): tools.compile_ordinary_orf_selection(None)


@pytest.mark.parametrize("attack", ("duplicate_operation", "different_resource_duplicate", "ordinal_bool", "ordinal_missing",
    "resource_policy", "caller_policy", "wall", "environment", "nonlocal", "operation", "extra_binding", "runtime"))
def test_configuration_rejects_ambiguity_or_unselected_constraints(selected_call, attack):
    call, _calls = selected_call
    resources, environments = _configuration(call)
    policy = call["policy"]
    if attack == "duplicate_operation": environments.append(deepcopy(environments[0]))
    elif attack == "different_resource_duplicate":
        resources["other-resource"] = deepcopy(resources["chosen-resource"])
        environments.append({**deepcopy(environments[0]), "resource_id": "other-resource"})
    elif attack == "ordinal_bool": environments[0]["binding_ordinal_0based"] = False
    elif attack == "ordinal_missing": environments[0]["binding_ordinal_0based"] = 10
    elif attack == "resource_policy": resources["chosen-resource"]["policy"]["memory_bytes"] //= 2
    elif attack == "caller_policy": policy = LocalJobPolicy(memory_bytes=1024, scratch_bytes=ordinary.POLICY["scratch_bytes"])
    elif attack == "wall": resources["chosen-resource"]["policy"]["wall_seconds"] = 60
    elif attack == "environment": environments[0]["environment"]["extra"] = "not selected"
    elif attack == "nonlocal": resources["chosen-resource"]["kind"] = "hpc"
    elif attack == "operation": environments[0]["operation"] = "align_sequences"
    elif attack == "extra_binding": resources["chosen-resource"]["native_molecular_sequence"][0]["extra"] = True
    else: resources["chosen-resource"]["native_molecular_sequence"][0]["software"]["python_home"] += "/different"
    with pytest.raises(ValueError): tools.normalize_molecular_sequence_configuration(resources, environments, policy)


def test_tool_info_has_fixed_five_arguments_and_original_nucleotide_semantics(selected_call):
    call, _calls = selected_call
    configuration = tools.normalize_molecular_sequence_configuration(*_configuration(call), call["policy"])
    entry = tools.molecular_sequence_tool_catalog(configuration)[tools.ORF_TOOL]
    assert set(entry["input_schema"]["properties"]) == {"subject_ref", "min_length", "search_reverse", "filter_subsets", "rows"}
    assert entry["input_schema"]["additionalProperties"] is False
    assert "including the terminal stop codon" in entry["instructions"]
    assert "zero-based half-open" in entry["instructions"]
    assert "translate(to_stop=True)" in entry["instructions"]
    assert entry["configuration"]["bindings"][0]["binding_ordinal_0based"] == 0


def test_backend_uses_actual_receipt_before_bytes_and_holds_lease_through_save(backend_case):
    value = backend_case
    outcome = asyncio.run(_execute(value))
    assert outcome["status"] == "partial"  # Explicit incomplete engineered scientific fixture.
    assert outcome["record_refs"] == [outcome["result"]["source_ref"]]
    assert value.events[0] == ("subject_admission", "input")
    assert value.events.index("freeze_existing_sequence_owner") < value.events.index("prepare_original")
    assert value.events.index("publish_under_same_lease") < value.events.index("save_under_same_lease")
    assert value.host._active == {}
    stored = value.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (value.operation_key,)).fetchone()[0]
    assert json.loads(stored) == outcome and len(value.calls) == 1


def test_store_membership_and_scope_without_subject_receipt_never_reach_bytes(backend_case, monkeypatch):
    value = backend_case
    reference = value.call["arguments"]["subject_ref"]
    value.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
        (value.context.run_id, value.context.episode_id, reference))
    value.store.db.commit()
    assert value.store.get(reference)["record_type"] == "input"
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("unreceived subject read bytes"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("unreceived subject reserved native work"))
    outcome = asyncio.run(_execute(value))
    assert outcome["status"] == "invalid" and outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == "ordinary_orf_subject_not_received"
    assert value.events[-1] == "save_under_same_lease" and value.calls == []


def test_saved_replay_uses_same_owner_without_subject_or_software_reads(backend_case, monkeypatch):
    value = backend_case
    original = asyncio.run(_execute(value))
    value.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical({**original, "pending_work_after_action": {"engineering_fixture": True}}), value.context.run_id, value.context.episode_id))
    value.store.db.commit()
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("saved replay froze bytes"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("saved replay reserved another handle"))
    def forbidden_reader(*args, **kwargs): pytest.fail("saved replay re-admitted original subject")
    value.reader = forbidden_reader
    restored = tools.OrdinaryMolecularSequenceTools(value.registry, configuration=None)
    assert asyncio.run(_execute(value, backend=restored)) == original
    assert len(value.calls) == 1


def test_frozen_host_binding_reuses_original_selection_and_operand_after_observation_stop(backend_case, monkeypatch):
    value = backend_case
    actual = ordinary.run_ordinary_orf_attempt
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", lambda *a, **k: (_ for _ in ()).throw(
        MolecularOperationUnpublished("engineering_observation_stopped")))
    with pytest.raises(MolecularOperationUnpublished): asyncio.run(_execute(value))
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    frozen = read_control(directory / tools.HOST_BINDING_FILENAME)
    assert frozen["frozen_operand"] == value.call["frozen_operand"]
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", actual)
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("restore recomputed original operand"))
    value.owner.resources = {}
    value.registry.local_job_policy = LocalJobPolicy(memory_bytes=1024, scratch_bytes=2048, wall_seconds=1)
    restored = tools.OrdinaryMolecularSequenceTools(value.registry, configuration=None)
    result = asyncio.run(_execute(value, backend=restored))
    assert result["record_refs"] and read_control(directory / tools.HOST_BINDING_FILENAME) == frozen
    assert len(value.calls) == 1


@pytest.mark.parametrize("route", ("direct_backend", "registry"))
@pytest.mark.parametrize("conflict", ("arguments", "name", "scope", "outcome"))
def test_occupied_operation_key_conflict_is_nonmutating_before_input_or_native_reads(backend_case, monkeypatch, conflict, route):
    value = backend_case
    arguments = deepcopy(value.call["arguments"])
    if conflict == "arguments": arguments["min_length"] += 1
    name = "different-recorded-tool" if conflict == "name" else tools.ORF_TOOL
    operation_scope = {} if conflict == "scope" else value.context.as_record()["scope"]
    from gene_annotation_episode.domain import identity
    operation_ref = identity("operation", {"key": value.operation_key, "name": name, "arguments": arguments})
    outcome = dict(status="invalid", operation_ref="incorrect-operation-ref" if conflict == "outcome" else operation_ref,
        record_refs=[], changed_record_refs=[], result=None, feedback={"code": "original_recorded_failure"})
    value.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)", (value.operation_key, operation_ref,
        name, canonical(arguments), canonical(operation_scope), canonical(outcome)))
    value.store.db.commit()
    original = tuple(value.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (value.operation_key,)).fetchone())
    value.reader = lambda *a, **k: pytest.fail("conflicting saved operation read input")
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("conflicting saved operation read bytes"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("conflicting saved operation reserved work"))
    monkeypatch.setattr(value.registry, "_save", lambda *a, **k: pytest.fail("conflicting key attempted duplicate INSERT"))
    async def invoke():
        if route == "direct_backend":
            return await _execute(value)
        with value.registry.current_invocation(value.context, read_received=value.reader, tool_name=tools.ORF_TOOL,
                arguments=value.call["arguments"], operation_key=value.operation_key):
            return await value.registry.execute_async(tools.ORF_TOOL, value.call["arguments"],
                scope=value.context.as_record()["scope"], operation_key=value.operation_key)
    with pytest.raises(ValueError, match="saved_operation_conflict"):
        asyncio.run(invoke())
    assert tuple(value.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (value.operation_key,)).fetchone()) == original
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    assert not (directory / tools.HOST_BINDING_FILENAME).exists()
    assert value.events == [] and value.calls == [] and value.host._active == {}


def _run_b_owner(value, resources):
    """Actual Store/receipt/action records for another engineered run owner."""
    run = "engineering-run-b-resource-join"
    episode = EpisodeRef(run, value.context.path).episode_id
    receipts = type(value.receipts)(value.store, run)
    manifest = receipts.bind(episode)
    request = value.context.as_record()["request"]
    request["message"]["knowledge_inheritance"] = manifest
    context = BindingContext(run, episode, value.context.role, value.context.path, value.context.scope,
        value.context.assignment, request)
    value.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, episode, canonical(context.path), canonical(request)))
    value.store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,NULL)", (run, episode, 0,
        canonical(dict(kind="tool", tool=tools.ORF_TOOL, arguments=value.call["arguments"]))))
    receipts.receive(episode, [value.call["arguments"]["subject_ref"]], kind="initial")
    owner = SimpleNamespace(store=value.store, run_id=run, directory=value.owner.directory / "run-b",
        tool_registry=value.registry, services=SimpleNamespace(engineering_fixture=True), resources=deepcopy(resources))
    owner._selected_result_action = MethodType(value.owner._selected_result_action.__func__, owner)
    host = type(value.host)(owner)
    value.registry.bind_molecular_sequence_results(host)
    value.context, value.owner, value.host, value.receipts = context, owner, host, receipts
    value.call["context"], value.operation_key = context, run + ":" + episode + ":0"
    value.call["operation_key"] = value.operation_key
    value.input_binding = MolecularSequenceInputBindings(SimpleNamespace(store=value.store, run_id=run,
        resolve_received_reference=lambda *_: None))
    value.store.db.commit()


@pytest.mark.parametrize("mismatch", ("missing_resource", "different_resource", "kind", "workspace", "policy", "ordinal", "deployment", "software"))
def test_actual_run_b_resource_mismatch_denies_new_work_before_bytes(backend_case, monkeypatch, mismatch):
    value = backend_case
    resources = deepcopy(value.owner.resources)
    resource = resources["chosen-resource"]
    if mismatch == "missing_resource": resources = {}
    elif mismatch == "different_resource": resources = {"run-b-other-resource": resource}
    elif mismatch == "kind": resource["kind"] = "hpc"
    elif mismatch == "workspace": resource["workspace"] += "/other-run-workspace"
    elif mismatch == "policy": resource["policy"]["memory_bytes"] //= 2
    elif mismatch == "ordinal": resource["native_molecular_sequence"] = []
    elif mismatch == "deployment": resource["native_molecular_sequence"][0]["deployment"]["module"]["path"] += ".other"
    else: resource["native_molecular_sequence"][0]["software"]["python_version"] = "different run-b software"
    _run_b_owner(value, resources)
    assert value.registry.molecular_sequence_results_for(value.context.run_id) is value.host
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("wrong-run resource read operand bytes"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("wrong-run resource prepared native unit"))
    outcome = asyncio.run(_execute(value))
    assert outcome["status"] == "invalid" and outcome["feedback"]["code"] == "ordinary_orf_run_resource_selection_conflict"
    assert value.events[-1] == "save_under_same_lease" and value.calls == []
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    assert not (directory / tools.HOST_BINDING_FILENAME).exists() and value.host._active == {}


def test_actual_run_b_matching_resource_passes_exact_join(backend_case):
    value = backend_case
    _run_b_owner(value, value.owner.resources)
    outcome = asyncio.run(_execute(value))
    assert outcome["record_refs"] and len(value.calls) == 1
    assert value.prepared["plan"]["identity"]["run_id"] == value.context.run_id
    assert value.prepared["plan"]["identity"]["resource_id"] == "chosen-resource"
    assert value.host._active == {}


def test_actual_factory_configures_registry_and_registry_owns_dispatch_and_cached_replay(backend_case, monkeypatch):
    value = backend_case
    resources, environments = _configuration(value.call)
    factory = ExecutionServiceFactory(resources=resources, initial_information={}, handoff_unit=1,
        acquired_record_unit=1, monitoring_information_unit=1, molecular_sequence_environments=tuple(environments))
    recorded = factory.as_record()
    assert recorded["molecular_sequence_environments"] == environments
    restored = ExecutionServiceFactory.from_record(recorded)
    assert restored.as_record() == recorded
    empty = ExecutionServiceFactory(resources=resources, initial_information={}, handoff_unit=1,
        acquired_record_unit=1, monitoring_information_unit=1)
    assert "molecular_sequence_environments" not in empty.as_record()
    restored.configure_tool_registry(value.registry)
    assert value.registry._molecular_sequence_configuration == value.configuration
    assert isinstance(value.registry.ordinary_molecular_sequence_backend, tools.OrdinaryMolecularSequenceTools)
    assert tools.ORF_TOOL in value.registry.catalog(value.context.as_record()["scope"])
    monkeypatch.setattr(value.registry, "_perform", lambda *a, **k: pytest.fail("ORF entered generic publication/save path"))
    async def dispatch():
        with value.registry.current_invocation(value.context, read_received=value.reader, tool_name=tools.ORF_TOOL,
                arguments=value.call["arguments"], operation_key=value.operation_key):
            return await value.registry.execute_async(tools.ORF_TOOL, value.call["arguments"],
                scope=value.context.as_record()["scope"], operation_key=value.operation_key)
    original = asyncio.run(dispatch())
    assert original["record_refs"] and value.events.count("save_under_same_lease") == 1
    # Exercise the actual registry's configuration=None fallback before its
    # generic cached/catalog path, with no live source/sequence reopening.
    value.registry._molecular_sequence_configuration = None
    value.registry.ordinary_molecular_sequence_backend = None
    shutil.rmtree(Path(value.prepared["handle_path"]).parent)
    value.reader = lambda *a, **k: pytest.fail("cached registry dispatch read subject")
    monkeypatch.setattr(value.registry, "catalog", lambda *a, **k: pytest.fail("cached ORF entered generic catalog"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("cached ORF prepared new work"))
    assert asyncio.run(dispatch()) == original
    assert value.events.count("save_under_same_lease") == 1 and len(value.calls) == 1


def test_async_cancellation_joins_observer_before_unlock_and_preserves_unit(backend_case, monkeypatch):
    value = backend_case
    started, ended = threading.Event(), threading.Event()
    def observe(prepared, *, cancel_event):
        started.set()
        assert len(value.host._active) == 1
        cancel_event.wait()
        assert len(value.host._active) == 1
        ended.set()
        raise MolecularOperationUnpublished("engineering_observation_stopped")
    monkeypatch.setattr(ordinary, "run_ordinary_orf_attempt", observe)
    async def run():
        task = asyncio.create_task(_execute(value))
        assert await asyncio.to_thread(started.wait, 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
    asyncio.run(run())
    assert ended.is_set() and value.host._active == {}
    assert Path(value.prepared["handle_path"]).exists()
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert len(value.calls) == 1


def test_publication_or_save_failure_rolls_back_operation_and_preserves_original(backend_case, monkeypatch):
    value = backend_case
    save = value.registry._save
    monkeypatch.setattr(value.registry, "_save", lambda *a, **k: (_ for _ in ()).throw(OSError("engineered save interruption")))
    with pytest.raises(MolecularOperationUnpublished): asyncio.run(_execute(value))
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert Path(value.prepared["handle_path"]).exists()
    monkeypatch.setattr(value.registry, "_save", save)
    result = asyncio.run(_execute(value))
    assert result["record_refs"] and len(value.calls) == 1


def test_wrong_run_or_unbound_owner_rejects_before_subject_read(backend_case, monkeypatch):
    value = backend_case
    value.registry._molecular_sequence_results_by_run.clear()
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("unbound owner read bytes"))
    with pytest.raises(ValueError, match="owner_unavailable"): asyncio.run(_execute(value))
    assert value.events == [] and value.calls == []


def test_missing_configuration_without_original_work_is_unavailable_under_owner_lock(backend_case, monkeypatch):
    value = backend_case
    value.reader = lambda *a, **k: pytest.fail("missing configuration read a subject")
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("missing configuration read bytes"))
    backend = tools.OrdinaryMolecularSequenceTools(value.registry, configuration=None)
    outcome = asyncio.run(_execute(value, backend=backend))
    assert outcome["status"] == "unavailable" and outcome["feedback"]["code"] == "ordinary_orf_configuration_required"
    assert outcome["record_refs"] == [] and value.events == ["save_under_same_lease"] and value.calls == []


def test_unreceived_external_reference_with_empty_footprint_is_not_authority(backend_case, monkeypatch):
    value = backend_case
    _source, reference = _external(value.store)
    assert value.store.coverage(reference["id"]) == []
    value.call["arguments"]["subject_ref"] = reference["id"]
    value.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(dict(kind="tool", tool=tools.ORF_TOOL, arguments=value.call["arguments"])), value.context.run_id, value.context.episode_id))
    value.store.db.commit()
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("unreceived external reference read bytes"))
    outcome = asyncio.run(_execute(value))
    assert outcome["status"] == "invalid" and value.events[0] == ("subject_admission", "reference")
    assert outcome["feedback"]["code"] == "ordinary_orf_subject_not_received" and value.calls == []


@pytest.mark.parametrize("kind", ("reference", "feature", "product"))
def test_actual_received_noninput_namespace_reaches_existing_operand_owner_without_native_work(backend_case, monkeypatch, kind):
    value = backend_case
    target = value.call["arguments"]["subject_ref"]
    if kind == "reference":
        _source, record = _external(value.store)
        expected = "aCgTuN"
    elif kind == "feature":
        record = _feature(value.store, target, [{"start": 0, "end": 3}])
        expected = "ATG"
    else:
        record = value.store.put("product", dict(parent_refs=[target], molecule="dna",
            sequence_ref=value.store.artifact("ATG", "text/plain"), derivation="extraction", context_refs=[],
            footprint=[dict(target_ref=target, start=0, end=3, unit="nt")]), origin="caller")
        expected = "ATG"
    value.receipts.receive(value.context.episode_id, [record["id"]], kind="initial")
    value.call["arguments"]["subject_ref"] = record["id"]
    value.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(dict(kind="tool", tool=tools.ORF_TOOL, arguments=value.call["arguments"])), value.context.run_id, value.context.episode_id))
    value.store.db.commit()
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **kwargs: (_ for _ in ()).throw(
        MolecularOperationUnpublished("engineering_stop_before_native_preparation")))
    with pytest.raises(MolecularOperationUnpublished): asyncio.run(_execute(value))
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    frozen = read_control(directory / tools.HOST_BINDING_FILENAME)["frozen_operand"]
    assert value.events[0] == ("subject_admission", kind)
    assert frozen["subject"] == record and frozen["sequence"] == expected and value.calls == []
    if kind == "product":
        assert frozen["parent_mapping"] is None and frozen["mapping_failure"] == {"code": "subregion_mapping_unavailable"}


def _saved_seed(value, monkeypatch, *, missing_components=False, missing_sheet=False):
    """Real metadata custody of engineered native rows; no native science."""
    import sys
    from gene_annotation_episode import orf_measurements as core
    original_roles = _roles
    def populate(item):
        roles = original_roles(item)
        native = dict(schema=core.NATIVE_SCHEMA, outcome="completed", failure=None,
            source_identity=dict(callable=tools.ORF_TOOL, path=item.call["selected"]["deployment"]["module"]["path"],
                sha256=item.call["selected"]["deployment"]["module"]["sha256"]),
            biopython_version="engineering fixture", translation=dict(table="Standard", to_stop=True, cds=False),
            result=dict(orfs=[["ATGAAATAA", "MK", 0, 9, "+", 1]],
                summary_stats=dict(total_orfs=1, forward_orfs=1, reverse_orfs=0, avg_length=9.0)))
        roles.documents["sheet"] = core.build_orf_sheet(native, input_sequence="ATGAAATAA",
            subject_ref=item.call["arguments"]["subject_ref"], parent_mapping=item.call["frozen_operand"]["parent_mapping"],
            request={key: item.call["arguments"][key] for key in ("min_length", "search_reverse", "filter_subsets")})
        roles.documents["components"] = core.calculate_orf_components(roles.documents["sheet"])
        # A deliberately older engineered component value proves a later
        # calculation need not agree with the original retained calculation.
        roles.documents["components"]["summary"]["reported_row_count"] = 99
        roles.seal()
        if missing_components:
            (roles.output / "components.json").unlink()
        if missing_sheet:
            (roles.output / "sheet.json").unlink()
        return roles
    monkeypatch.setattr(sys.modules[__name__], "_roles", populate)
    original = asyncio.run(_execute(value))
    value.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(original), value.context.run_id, value.context.episode_id))
    reference = original["result"]["source_ref"]
    value.receipts.receive(value.context.episode_id, [reference], kind="own_action", source_index=0)
    value.store.db.commit()
    def reader(context, ref, namespace, **kwargs):
        assert namespace == "source" and kwargs == {"source_metadata_only": True}
        return value.input_binding.read_received_source(context, ref)
    value.reader = reader
    return reference, original


def _saved_execute(value, arguments, *, index, backend=None, commit=True):
    value.operation_key = f'{value.context.run_id}:{value.context.episode_id}:{index}'
    value.call["arguments"] = deepcopy(arguments)
    value.store.db.execute("INSERT OR IGNORE INTO runtime_actions VALUES(?,?,?,?,NULL)",
        (value.context.run_id, value.context.episode_id, index,
            canonical(dict(kind="tool", tool=tools.ORF_TOOL, arguments=arguments))))
    value.store.db.commit()
    outcome = asyncio.run(_execute(value, backend=backend or tools.OrdinaryMolecularSequenceTools(
        value.registry, configuration=None, saved_modes=True)))
    if commit:
        value.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(outcome), value.context.run_id, value.context.episode_id, index))
        if outcome["record_refs"]:
            value.receipts.receive(value.context.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        value.store.db.commit()
    return outcome


def _saved_rows():
    return [dict(row_id={"kind": "summary"}, fields=["reported_row_count", "mean_retained_orf_length_nt"])]


def test_saved_only_catalog_is_explicit_and_preserves_native_contract(selected_call):
    call, _calls = selected_call
    configuration = tools.normalize_molecular_sequence_configuration(*_configuration(call), call["policy"])
    native = tools.molecular_sequence_tool_catalog(configuration)[tools.ORF_TOOL]
    combined = tools.molecular_sequence_tool_catalog(configuration, saved_modes=True)[tools.ORF_TOOL]
    saved = tools.molecular_sequence_tool_catalog(None, saved_modes=True)[tools.ORF_TOOL]
    assert combined["input_schema"]["anyOf"][0] == {k: v for k, v in native["input_schema"].items() if k != "$id"}
    assert len(saved["input_schema"]["anyOf"]) == 2
    assert [row["properties"]["mode"]["const"] for row in saved["input_schema"]["anyOf"]] == ["read_stored", "calculate_saved"]
    assert tools.molecular_sequence_tool_catalog(None) == {}
    assert "Saved reads and recalculation are not exposed here." in native["instructions"]
    assert "distinct derived Source" in saved["instructions"]


@pytest.mark.parametrize("damage", ("native_parameter", "file_ref", "duplicate_row", "float_min_length", "null", "list", "boolean"))
def test_saved_orf_arguments_preserve_closed_selection_rules(damage):
    arguments = dict(mode="calculate_saved", result_ref="source_" + "1" * 24, rows=_saved_rows())
    if damage == "native_parameter": arguments["search_reverse"] = False
    elif damage == "file_ref": arguments["result_ref"] = "artifact_" + "1" * 64
    elif damage == "duplicate_row": arguments["rows"].append(deepcopy(arguments["rows"][0]))
    elif damage == "float_min_length": arguments = dict(subject_ref="input", min_length=0.0, search_reverse=True, filter_subsets=False, rows=[])
    else: arguments = {"null": None, "list": [], "boolean": False}[damage]
    from gene_annotation_episode.molecular_sequence_result_contracts import validate_ordinary_orf_arguments
    with pytest.raises(ValueError): validate_ordinary_orf_arguments(arguments)


def test_saved_read_keeps_source_and_original_values_after_deployment_removal(backend_case, monkeypatch):
    value = backend_case
    reference, original = _saved_seed(value, monkeypatch)
    source_before = deepcopy(value.store.get(reference))
    shutil.rmtree(value.call["selected"]["software"]["python_home"])
    value.owner.resources = {}
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("saved read reopened subject"))
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("saved read prepared native work"))
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("saved read calculated"))
    arguments = dict(mode="read_stored", result_ref=reference, rows=_saved_rows())
    outcome = _saved_execute(value, arguments, index=1)
    assert outcome["record_refs"] == [reference] and outcome["changed_record_refs"] == []
    assert outcome["result"]["values"]["rows"][0]["value"] == 99
    assert value.store.get(reference) == source_before
    assert _saved_execute(value, arguments, index=1) == outcome
    assert value.host.read_ordinary_orf_action_result(value.context, arguments, value.operation_key,
        read_received=value.reader) == outcome["result"]
    assert len(value.calls) == 1 and value.host._active == {}
    assert json.loads(value.store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0]) == original


@pytest.mark.parametrize("missing_components", (False, True))
def test_saved_calculation_owns_distinct_source_and_private_outputs(backend_case, monkeypatch, missing_components):
    from gene_annotation_episode import orf_measurements as core
    from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
    value = backend_case
    reference, original = _saved_seed(value, monkeypatch, missing_components=missing_components)
    source_before = deepcopy(value.store.get(reference))
    actual, calls = core.calculate_orf_components, []
    def calculate(sheet):
        calls.append(deepcopy(sheet)); assert len(value.host._active) == 1
        return actual(sheet)
    monkeypatch.setattr(core, "calculate_orf_components", calculate)
    monkeypatch.setattr(ordinary, "prepare_ordinary_orf_attempt", lambda **k: pytest.fail("saved calculation prepared native work"))
    monkeypatch.setattr(value.registry, "_prepare_orf_sequence_operand", lambda *a, **k: pytest.fail("saved calculation read subject"))
    shutil.rmtree(value.call["selected"]["software"]["python_home"])
    value.owner.resources = {}
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows())
    outcome = _saved_execute(value, arguments, index=1, commit=False)
    derived = outcome["result"]["source_ref"]
    assert derived != reference and outcome["record_refs"] == outcome["changed_record_refs"] == [derived]
    assert outcome["result"]["values"]["source_kind"] == "selected_saved_calculation"
    assert outcome["result"]["values"]["rows"][0]["value"] == 1
    assert value.store.get(reference) == source_before and len(calls) == 1
    # Recover the same saved ToolOperation while its RuntimeAction is NULL.
    assert _saved_execute(value, arguments, index=1) == outcome and len(calls) == 1
    publication = value.host.read_ordinary_orf_publication(value.context, derived, read_received=value.reader)
    assert publication["control"]["calculation"]["native_call_state"] == "not_requested"
    assert publication["control"]["calculation"]["call_count"] == 1
    assert value.store.get(derived)["parent_source_refs"] == [reference]
    for private_ref in [value.store.get(derived)["request_ref"], *value.store.get(derived)["auxiliary_artifact_refs"]]:
        assert molecular_reference_restriction(value.store, value.context, private_ref, "artifact") is False
        assert private_ref not in set(value.receipts.known(value.context.episode_id))
    monkeypatch.setattr(core, "calculate_orf_components", lambda *a: pytest.fail("derived read recalculated"))
    read = _saved_execute(value, dict(mode="read_stored", result_ref=derived, rows=_saved_rows()), index=2)
    assert read["result"] == outcome["result"] and read["record_refs"] == [derived]
    assert value.host.read_ordinary_orf_publication(value.context, reference, read_received=value.reader)["stored"] == original["result"]
    assert len(value.calls) == 1


def test_saved_calculation_uncertain_marker_never_reissues(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows())
    key = f'{value.context.run_id}:{value.context.episode_id}:1'
    directory = value.host.action_directory(value.context.episode_id, key)
    from gene_annotation_episode.genomic_overlap_result_receipts import immutable
    immutable(directory / "ordinary-calculation-started.json", {"engineering_interrupted_marker": True})
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("uncertain action recalculated"))
    with pytest.raises(MolecularOperationUnpublished, match="outcome_unknown"):
        _saved_execute(value, arguments, index=1)
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


def test_saved_calculation_save_rollback_recovers_without_recalculation(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows())
    save = value.registry._save
    monkeypatch.setattr(value.registry, "_save", lambda *a, **k: (_ for _ in ()).throw(OSError("engineered save interruption")))
    with pytest.raises((OSError, MolecularOperationUnpublished)):
        _saved_execute(value, arguments, index=1)
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
    monkeypatch.setattr(value.registry, "_save", save)
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("rollback repeated calculation"))
    result = _saved_execute(value, arguments, index=1)
    assert result["record_refs"] and result["result"]["values"]["rows"][0]["value"] == 1


def test_unreceived_saved_source_denies_before_private_bytes(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    value.store.db.execute("DELETE FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref=?",
        (value.context.run_id, value.context.episode_id, reference))
    value.store.db.commit()
    monkeypatch.setattr(value.store, "get_artifact", lambda *a: pytest.fail("unreceived Source opened private bytes"))
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("unreceived Source calculated"))
    result = _saved_execute(value, dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows()), index=1)
    assert result["status"] == "invalid" and result["record_refs"] == [] and result["result"] is None


def test_saved_source_without_sheet_never_calls_calculator(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch, missing_sheet=True)
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("missing sheet calculated"))
    result = _saved_execute(value, dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows()), index=1)
    assert result["status"] == "invalid" and result["record_refs"] == []
    assert not (value.host.action_directory(value.context.episode_id, value.operation_key) / "ordinary-calculation-started.json").exists()


def test_saved_calculator_exception_is_partial_with_private_diagnostic(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    def failed_calculator(sheet):
        raise ValueError("engineered private diagnostic only")
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", failed_calculator)
    result = _saved_execute(value, dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows()), index=1)
    assert result["status"] == "partial" and result["record_refs"]
    assert all(row["value_state"] == "source_unavailable" for row in result["result"]["values"]["rows"])
    publication = value.host.read_ordinary_orf_publication(value.context, result["result"]["source_ref"], read_received=value.reader)
    calculation = publication["control"]["calculation"]
    assert calculation["state"] == "raised" and calculation["call_count"] == 1 and calculation["native_call_state"] == "not_requested"
    diagnostic = value.host._ordinary_value(calculation["diagnostic_file"])
    assert diagnostic["exception_message"] == "engineered private diagnostic only"
    assert "engineered private diagnostic only" not in canonical(result)


@pytest.mark.parametrize("damage", ("native_state", "count_bool", "source_identity", "replacement_components", "diagnostic_count_bool", "diagnostic_count_float"))
def test_saved_publication_rejects_control_or_component_relationship_tampering(backend_case, monkeypatch, damage):
    from gene_annotation_episode import molecular_sequence_result_contracts as contracts
    from gene_annotation_episode.native_file_capture import _identity
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    outcome = _saved_execute(value, dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows()), index=1)
    publication = value.host.read_ordinary_orf_publication(value.context, outcome["result"]["source_ref"], read_received=value.reader)
    changed = deepcopy(publication["control"])
    if damage == "native_state": changed["calculation"]["native_call_state"] = "returned"
    elif damage == "count_bool": changed["calculation"]["call_count"] = True
    elif damage == "source_identity": changed["original_source"]["record_sha256"] = "0" * 64
    elif damage == "replacement_components":
        original = value.host._ordinary_value(changed["source_files"]["components"]["file"])
        original["summary"]["reported_row_count"] = 2
        raw = canonical(original).encode()
        ref = value.store.artifact(raw, "application/json")
        metadata = value.store.get(ref)
        file = _identity(dict(artifact_ref=ref, sha256=metadata["sha256"], size_bytes=metadata["size"], format="orf_measurement_components_v1"))
        changed["source_files"]["components"] = dict(state="retained", file=file, declared=None,
            observed_identity={key: file[key] for key in ("sha256", "size_bytes")}, failure=None)
        changed["projection"] = value.host._admit_projection(selector=changed["projection"]["selector"],
            sources=changed["source_files"], association=changed["projection"]["association"],
            calculation=changed["projection"]["calculation"])
    else:
        def retained(document, format_name):
            ref = value.store.artifact(canonical(document), "application/json")
            metadata = value.store.get(ref)
            return _identity(dict(artifact_ref=ref, sha256=metadata["sha256"], size_bytes=metadata["size"], format=format_name))
        diagnostic = value.host._ordinary_value(changed["calculation"]["diagnostic_file"])
        diagnostic["call_count"] = True if damage == "diagnostic_count_bool" else 1.0
        changed["calculation"]["diagnostic_file"] = retained(diagnostic, "ordinary_orf_calculation_diagnostic_v1")
        result = value.host._ordinary_value(changed["calculation"]["result_file"])
        result["diagnostic_pin"].update({key: changed["calculation"]["diagnostic_file"][key] for key in ("sha256", "size_bytes")})
        changed["calculation"]["result_file"] = retained(result, "ordinary_orf_calculation_result_v1")
    before = value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0]
    with pytest.raises(ValueError):
        value.host._validate_ordinary_orf_custody(changed, changed["intent"])
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == before
    contracts.validate_ordinary_orf_return(outcome["result"])


def test_original_and_recalculated_source_groups_freeze_without_private_reads(backend_case, monkeypatch):
    """Engineered own frozen-row control; genuine parent delivery is separate."""
    from gene_annotation_episode import molecular_result_facts as facts
    from gene_annotation_episode import molecular_sequence_result_contracts as contracts
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    old = _saved_execute(value, dict(mode="read_stored", result_ref=reference, rows=_saved_rows()), index=1)
    new = _saved_execute(value, dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows()), index=2)
    groups = facts.merge_molecular_facts([old["result"]], [new["result"]], fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)
    assert len(groups) == 2 and [row["values"]["rows"][0]["value"] for row in groups] == [99, 1]
    schema = dict(type="object", additionalProperties=False, required=["measurements"], properties=dict(
        measurements=deepcopy(contracts.ordinary_orf_fact_sources()[contracts.ORDINARY_ORF_FACT_SOURCE]["report_schema"])))
    value.store.db.execute("CREATE TABLE runtime_forms(run_id TEXT,episode_id TEXT,facts TEXT,form TEXT,PRIMARY KEY(run_id,episode_id))")
    value.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)", (value.context.run_id, value.context.episode_id,
        canonical({contracts.ORDINARY_ORF_FACT_SOURCE: groups}), canonical({"measurements": groups})))
    value.store.db.commit()
    monkeypatch.setattr(value.store, "get_artifact", lambda *a: pytest.fail("frozen derived values read private bytes"))
    monkeypatch.setattr(value.host, "read_ordinary_orf_publication", lambda *a, **k: pytest.fail("frozen values reopened a publication"))
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("frozen values calculated"))
    frozen = facts.frozen_molecular_facts(value.store, value.context.run_id, value.context, fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)
    assert frozen == groups
    facts.validate_frozen_molecular_return({"measurements": groups}, schema, frozen, fact_source=contracts.ORDINARY_ORF_FACT_SOURCE)


def _saved_receiver(value, *, run, source_ref):
    """Engineering root records and actual Source receipts, no child-return claim."""
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    manifest_reader = EpisodeReceipts(value.store, run)
    episode = EpisodeRef(run, value.context.path).episode_id
    manifest = manifest_reader.bind(episode)
    request = value.context.as_record()["request"]
    request["message"]["knowledge_inheritance"] = manifest
    context = BindingContext(run, episode, value.context.role, value.context.path, value.context.scope,
        value.context.assignment, request)
    value.store.db.execute("INSERT INTO runtime_episodes VALUES(?,?,?,?)", (run, episode, canonical(context.path), canonical(request)))
    manifest_reader.receive(episode, [source_ref], kind="initial")
    owner = SimpleNamespace(store=value.store, run_id=run, directory=value.owner.directory / run,
        tool_registry=value.registry, services=SimpleNamespace(engineering_fixture=True), resources={})
    owner._selected_result_action = MethodType(value.owner._selected_result_action.__func__, owner)
    host = type(value.host)(owner)
    value.registry.bind_molecular_sequence_results(host)
    value.context, value.owner, value.host, value.receipts = context, owner, host, manifest_reader
    value.call["context"] = context
    value.input_binding = MolecularSequenceInputBindings(SimpleNamespace(store=value.store, run_id=run,
        resolve_received_reference=lambda *_: None))
    value.store.db.commit()
    value.reader = lambda current, reference, namespace, **kwargs: value.input_binding.read_received_source(current, reference)


def test_foreign_derived_source_authenticates_original_admission_without_file_receipts(backend_case, monkeypatch):
    value = backend_case
    original_ref, _original = _saved_seed(value, monkeypatch)
    original_source = deepcopy(value.store.get(original_ref))
    _saved_receiver(value, run="engineering-saved-calculator-B", source_ref=original_ref)
    calculated = _saved_execute(value, dict(mode="calculate_saved", result_ref=original_ref, rows=_saved_rows()), index=0)
    derived = calculated["result"]["source_ref"]
    _saved_receiver(value, run="engineering-saved-reader-C", source_ref=derived)
    known = set(value.receipts.known(value.context.episode_id))
    assert derived in known and original_ref not in known and not any(ref.startswith("artifact_") for ref in known)
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("foreign read calculated"))
    read = _saved_execute(value, dict(mode="read_stored", result_ref=derived, rows=_saved_rows()), index=0)
    assert read["result"] == calculated["result"] and value.store.get(original_ref) == original_source
    assert len(value.calls) == 1


def test_sealed_calculation_without_original_start_anchor_is_not_repriced(backend_case, monkeypatch):
    value = backend_case
    reference, _original = _saved_seed(value, monkeypatch)
    arguments = dict(mode="calculate_saved", result_ref=reference, rows=_saved_rows())
    save = value.registry._save
    monkeypatch.setattr(value.registry, "_save", lambda *a, **k: (_ for _ in ()).throw(OSError("engineered rollback")))
    with pytest.raises(MolecularOperationUnpublished): _saved_execute(value, arguments, index=1)
    directory = value.host.action_directory(value.context.episode_id, value.operation_key)
    (directory / "ordinary-calculation-started.json").unlink()
    monkeypatch.setattr(value.registry, "_save", save)
    monkeypatch.setattr("gene_annotation_episode.orf_measurements.calculate_orf_components", lambda *a: pytest.fail("orphan result recalculated"))
    with pytest.raises(MolecularOperationUnpublished): _saved_execute(value, arguments, index=1)
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1
