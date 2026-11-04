"""Ordinary numeric-File controls with engineered worker observations.

The outer Workflow, actions, admissions, Sources and receipts are real. Inner
worker metadata is explicitly engineered; no native fit or process is started.
Only tests that require saved calculation call the existing pure calculator.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import molecular_measurement_tools as common
from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_result_contracts as stored
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import protease_kinetics_measurements as scientific
from gene_annotation_episode import protease_kinetics_result_contracts as contracts
from gene_annotation_episode import protease_kinetics_tools as host
from gene_annotation_episode.communication import ReportBoundaryError, plain, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_protease_kinetics_measurements import supplied_fixture
from tests.test_molecular_sequence_tools_native import _controller, _credit
from tests.test_runtime import ScriptedProvider


POLICY = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
TOOL = contracts.TOOL


def _forbidden(*args, **kwargs):
    raise AssertionError("unselected native/process/network/model work")


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False))


def _pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted([tuple(row) for row in store.db.execute('SELECT * FROM "' +
        name.replace('"', '""') + '"')], key=repr) for name in names}


def _rows():
    return [dict(row_id=dict(kind="protease_fit"), fields=["vmax", "km"])]


def _selected_deployment():
    # Pure request-schema fixture only; these paths attest no available runtime.
    _measurements, capture, _assay = supplied_fixture()
    return deepcopy(capture["request"]["deployment"])


def _resources(tmp_path, *, native_binding=False):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    resource = dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))
    environments = []
    if native_binding:
        resource["native_protease_kinetics"] = [dict(operation=TOOL, deployment=_selected_deployment())]
        environments.append(dict(operation=TOOL, resource_id="ordinary", binding_ordinal_0based=0))
    return {"ordinary": resource}, environments


def _dispatch(value, arguments, index):
    selected = dict(kind="tool", tool=TOOL, arguments=deepcopy(arguments))
    asyncio.run(value.caller.source.execute(selected, index))
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, index)
    assert json.loads(row["action"]) == selected and row["result"] is not None
    return json.loads(row["result"])


def _engineered_worker(value, monkeypatch):
    observations = {}
    async def work(operation, arguments, *, directory, owned_directory):
        assert not value.store.db.in_transaction and directory == owned_directory
        assert operation == "protease_kinetics_saved"
        request = deepcopy(arguments["request"])
        assert request["mode"] == "saved_sheet" and request["scientific_context"] is None
        value.worker_calls.append(deepcopy(request))
        raw = json.dumps(json.loads(canonical(request)), allow_nan=False).encode()
        (directory / "worker-request.json").write_bytes(raw)
        python = dict(path="/engineered/not-executed/python", sha256="0" * 64)
        selection = dict(version="ordinary_molecular_execution_v1", command=host._command(request, directory, python["path"]),
            cwd=str(directory), environment={"ENGINEERING_ONLY": "no process or native fit"}, policy=deepcopy(POLICY),
            request=dict(operation=operation, arguments=dict(request=request)), python=python, implementation_files=[])
        _write(directory / "execution-selection.json", selection)
        paths = {key: str(directory / name) for key, name in
            dict(request="job-request.json", ready="ready", release="release", result="result").items()}
        native_request = dict(command=selection["command"], cwd=str(directory), file_bytes=POLICY["scratch_bytes"],
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None,
            env=selection["environment"])
        _write(Path(paths["request"]), native_request)
        metadata = dict(policy=deepcopy(POLICY), native_returncode=value.returncode)
        handle = dict(version=native_lifecycle.VERSION, command=selection["command"], cwd=str(directory),
            stdout=str(directory / "stdout"), stderr=str(directory / "stderr"), paths=paths,
            request_sha256=_pin(Path(paths["request"]))["sha256"], metadata=metadata)
        _write(directory / "native-handle.json", handle)
        observations[str(directory / "native-handle.json")] = dict(state="returned", terminal=True,
            quiescent=True, metadata=deepcopy(metadata))
        output = directory / "driver-output"
        output.mkdir()  # The adapter must not precreate the private driver's destination.
        if not value.missing_declaration or value.partial_without_declaration:
            if not value.missing_sheet:
                sheet_raw = Path(request["selection"]["sheet_file"]["path"]).read_bytes()
                (output / "sheet.json").write_bytes(sheet_raw)
                sheet = scientific.validate_protease_kinetics_sheet(json.loads(sheet_raw))
                if not value.missing_components:
                    value.calculator_inputs.append(deepcopy(sheet))
                    _write(output / "components.json", scientific.calculate_protease_kinetics_components(sheet))
            declaration = dict(version=driver.DECLARATION_VERSION_V2, mode="saved_sheet", operation=TOOL,
                request_file=_pin(directory / "worker-request.json"), request_file_pin_verified=True,
                attempt_identity=request["attempt_identity"], native_call_state="not_requested", native_failure=None,
                driver_failure=None, files=driver._declarations(output),
                qualification="engineered terminal metadata; no process/native fit; existing pure saved calculator",
                native_outcome=None, observer_state="not_requested", observer_failures=[], verification_failures=[],
                native_output_completion="not_requested")
            if not value.missing_declaration:
                _write(output / "declaration.json", declaration)
            elif value.malformed_declaration:
                (output / "declaration.json").write_bytes(b"{interrupted original declaration")
        return SimpleNamespace(output_path=output / "declaration.json", metadata=metadata)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", work)
    monkeypatch.setattr(native_lifecycle, "status", lambda handle: deepcopy(observations[str(handle.path)]))


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    measurements, capture, assay = supplied_fixture()
    sheet = scientific.populate_protease_kinetics_sheet(native_capture=capture, measurements=measurements, assay_context=assay)
    store = Store(tmp_path / "store")
    store.create_problem(raw_sequence="ACGT", molecule="dna")
    material = store.register_material(data=canonical(sheet).encode(), name="explicit constructed saved Sheet", use="evidence")
    supplied = store.get(material["source_ref"])
    reference = supplied["artifact_ref"]
    registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
    resources, environments = _resources(tmp_path)
    factory = ExecutionServiceFactory(resources, {}, 1, 1, 1,
        protease_kinetics_environments=tuple(environments), protease_kinetics_saved_modes=True)
    restored = ExecutionServiceFactory.from_record(factory.as_record())
    assert restored.as_record() == factory.as_record()
    application = restored(store, run_id="protease-engineering", directory=tmp_path / "run", tool_registry=registry)
    provider = ScriptedProvider([])
    provider.complete = _forbidden
    flow = Workflow(store, registry, provider, tmp_path / "run", "protease-engineering", _controller, _credit,
        project_child_credit=_credit, root_role="improvement",
        episode_binding_descriptors=application.episode_binding_descriptors,
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=[reference])
    caller = flow.build("improvement", "caller", "Which qualified protease values are retained in the supplied numerical Sheet?",
        store.validate_scope())
    value = SimpleNamespace(store=store, registry=registry, flow=flow, caller=caller, provider=provider,
        sheet=sheet, reference=reference, factory=factory, worker_calls=[], calculator_inputs=[],
        returncode=0, missing_sheet=False, missing_components=False, missing_declaration=False,
        partial_without_declaration=False, malformed_declaration=False)
    monkeypatch.setattr(native, "execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr(driver, "execute_molecular_sequence_request", _forbidden)
    for name in ("prepare_job", "resume_start", "wait_job", "collect", "cancel", "release"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)
    monkeypatch.setattr(registry.clients, "_http", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    _engineered_worker(value, monkeypatch)
    try:
        yield value
    finally:
        assert provider.contexts == []
        store.close()


def test_saved_file_real_action_publication_and_new_rows_read_without_any_calculation(boundary, monkeypatch):
    value = boundary
    assert TOOL in {row["name"] for row in value.flow.catalog(value.caller.source.scope, source=value.caller.source)}
    original = _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[]), 0)
    assert original["status"] == "completed" and len(value.calculator_inputs) == len(value.worker_calls) == 1
    public = original["result"]
    assert public["values"]["rows"] == [] and public["values"]["source_kind"] == "selected_saved_calculation"
    assert public["values"]["original_attempt_association"] == "unavailable"
    assert public["values"]["context"]["population"]["value"]["substrate_count"] == 3
    source = value.store.get(public["source_ref"])
    control = json.loads(value.store.get_artifact(source["request_ref"]))
    assert control["intent"]["selected_resource"] is None and control["worker"]["declaration"]["native_call_state"] == "not_requested"
    assert value.reference not in source["auxiliary_artifact_refs"]  # Independently admitted input stays usable.
    known = set(value.flow.receipts.known(value.caller.source.episode_id))
    assert public["source_ref"] in known
    private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]} - {value.reference}
    assert private.isdisjoint(known)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
    get = Store.get_artifact
    allowed = {source["artifact_ref"], source["request_ref"], control["files"]["sheet"]["file"]["artifact_ref"],
        control["files"]["components"]["file"]["artifact_ref"]}
    opened = []
    def numeric_only(current, reference):
        assert reference in allowed
        opened.append(reference)
        return get(current, reference)
    monkeypatch.setattr(Store, "get_artifact", numeric_only)
    read = _dispatch(value, dict(mode="read_stored", result_ref=public["source_ref"], rows=_rows()), 1)
    assert read["result"]["source_ref"] == public["source_ref"] and read["changed_record_refs"] == []
    assert [row["value"] for row in read["result"]["values"]["rows"]] == [12., 3.]
    assert read["result"]["values"]["source_kind"] == "selected_saved_calculation"
    assert len(value.worker_calls) == len(value.calculator_inputs) == 1 and opened
    schema = contracts.ordinary_protease_kinetics_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    calls = []
    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return reference == public["source_ref"] and namespace == "source"
    wrapper = dict(type="object", properties=dict(values=schema), required=["values"], additionalProperties=False)
    assert validate_form(dict(values=[read["result"]]), wrapper, resolve) == dict(values=[read["result"]])
    assert set(calls) == {(public["source_ref"], "source")}


def test_derived_source_once_then_same_key_cache_and_public_packet_only_read(boundary, monkeypatch):
    value = boundary
    first = _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=_rows()), 0)
    arguments = dict(mode="calculate_saved", result_ref=first["result"]["source_ref"], rows=[])
    derived = _dispatch(value, arguments, 1)
    assert derived["result"]["source_ref"] != first["result"]["source_ref"] and len(value.calculator_inputs) == 2
    assert value.calculator_inputs[0] == value.calculator_inputs[1] == value.sheet
    source = value.store.get(derived["result"]["source_ref"])
    assert source["parent_source_refs"] == [first["result"]["source_ref"]]
    before = _tables(value.store)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    get = Store.get_artifact
    def packet_only(current, reference):
        assert reference == source["artifact_ref"]
        return get(current, reference)
    monkeypatch.setattr(Store, "get_artifact", packet_only)
    key = f"{value.flow.run_id}:{value.caller.source.episode_id}:1"
    cached = asyncio.run(value.flow.execute(value.caller.source, TOOL, arguments, decision_index=1, operation_key=key))
    assert cached == {key: item for key, item in derived.items() if key != "pending_work_after_action"}
    assert _tables(value.store) == before


@pytest.mark.parametrize("missing", ["sheet", "components", "declaration"])
def test_known_terminal_missing_outputs_publish_qualified_context_instead_of_orphan(boundary, missing):
    value = boundary
    setattr(value, "missing_" + missing, True)
    value.returncode = 1
    outcome = _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[]), 0)
    assert outcome["status"] == "partial" and outcome["record_refs"] == [outcome["result"]["source_ref"]]
    assert outcome["result"]["values"]["rows"] == [] and outcome["result"]["failures"]
    assert outcome["result"]["values"]["source_kind"] == "selected_saved_calculation"
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 1


@pytest.mark.parametrize("malformed", [False, True])
def test_terminal_partial_files_survive_absent_or_interrupted_declaration(boundary, malformed):
    value = boundary
    value.missing_declaration = value.partial_without_declaration = True
    value.malformed_declaration = malformed
    value.returncode = 1
    outcome = _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=_rows()), 0)
    assert outcome["status"] == "partial"
    public = outcome["result"]
    assert public["file_states"]["sheet"] == public["file_states"]["components"] == "retained_undeclared"
    assert [row["value"] for row in public["values"]["rows"]] == [12., 3.]
    assert "declaration_unavailable" in [issue["code"] for issue in public["failures"]]
    source = value.store.get(public["source_ref"])
    control = json.loads(value.store.get_artifact(source["request_ref"]))
    assert control["worker"]["declaration"] is None
    assert control["worker"]["declaration_hex"] == (b"{interrupted original declaration".hex() if malformed else None)
    assert len(value.calculator_inputs) == 1


def test_source_and_tool_operation_publication_roll_back_together(boundary, monkeypatch):
    value = boundary
    save = value.registry._save
    def fail_save(*args, **kwargs):
        if args[4].get("result") is not None:
            raise RuntimeError("engineered crash inside publication transaction")
        return save(*args, **kwargs)
    monkeypatch.setattr(value.registry, "_save", fail_save)
    arguments = dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[])
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 0)
    assert value.store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
    assert value.store.db.execute("SELECT count(*) FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?",
        (TOOL,)).fetchone()[0] == 0


def test_unreceived_numeric_file_denied_before_bytes_or_worker(boundary, monkeypatch):
    value = boundary
    unknown = value.store.artifact(b'{"unreceived":true}', "application/json")
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=unknown), rows=[]), 0)
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 0)
    result = json.loads(row["result"])
    assert result["result"] is None and result["record_refs"] == []
    directory = value.store.path / "cache/molecular-measurements" / digest(
        f"{value.flow.run_id}:{value.caller.source.episode_id}:0")
    assert not (directory / "protease-kinetics-intent.json").exists()


def test_admitted_raw_input_document_cannot_be_changed_before_dispatch(boundary, monkeypatch):
    value = boundary
    original = host._fresh_input
    def changed(*args, **kwargs):
        prepared = original(*args, **kwargs)
        prepared["document"]["measurements"]["enzyme_concentration"] = 123
        return prepared
    monkeypatch.setattr(host, "_fresh_input", changed)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[]), 0)
    assert value.worker_calls == []


def test_pending_same_handle_recovery_keeps_original_policy_without_current_configuration(boundary, monkeypatch):
    value = boundary
    worker = value.registry._sequence_worker_async
    class StopAfterTerminal(BaseException):
        pass
    async def terminal_then_stop(*args, **kwargs):
        await worker(*args, **kwargs)
        raise StopAfterTerminal()
    monkeypatch.setattr(value.registry, "_sequence_worker_async", terminal_then_stop)
    arguments = dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[])
    with pytest.raises(StopAfterTerminal):
        _dispatch(value, arguments, 0)
    assert len(value.calculator_inputs) == 1
    directory = value.store.path / "cache/molecular-measurements" / digest(
        f"{value.flow.run_id}:{value.caller.source.episode_id}:0") / "worker"
    original_handle = (directory / "native-handle.json").read_bytes()
    metadata = json.loads(original_handle)["metadata"]
    async def retained(*args, **kwargs):
        return SimpleNamespace(output_path=directory / "driver-output/declaration.json", metadata=metadata)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", retained)
    value.registry._protease_kinetics_configuration = None
    value.registry.local_job_policy = LocalJobPolicy(**{**POLICY, "memory_bytes": POLICY["memory_bytes"] // 2})
    recovered = _dispatch(value, arguments, 0)
    assert recovered["status"] == "completed" and len(value.calculator_inputs) == 1
    assert (directory / "native-handle.json").read_bytes() == original_handle


def test_pending_saved_selection_cannot_use_a_later_source_receipt_before_private_bytes(boundary, monkeypatch):
    value = boundary
    arguments = dict(mode="calculate_saved", input=dict(namespace="artifact", reference=value.reference), rows=[])
    receive = value.flow.receive_outcome
    def stop_delivery(*args, **kwargs):
        raise MolecularOperationUnpublished("engineered stop after publication before normal receipt")
    monkeypatch.setattr(value.flow, "receive_outcome", stop_delivery)
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, arguments, 5)
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 5)
    original = json.loads(row["result"])
    reference = original["result"]["source_ref"]
    assert reference not in value.flow.receipts.known(value.caller.source.episode_id)
    admission = host._source_admission
    def stop_admission(*args, **kwargs):
        raise MolecularOperationUnpublished("engineered stop after saved action selection")
    monkeypatch.setattr(host, "_source_admission", stop_admission)
    saved = dict(mode="read_stored", result_ref=reference, rows=[])
    with pytest.raises(MolecularOperationUnpublished):
        _dispatch(value, saved, 2)
    pending = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)
    assert pending["result"] is None
    monkeypatch.setattr(host, "_source_admission", admission)
    monkeypatch.setattr(value.flow, "receive_outcome", receive)
    assert _dispatch(value, arguments, 5) == original
    assert reference in value.flow.receipts.known(value.caller.source.episode_id)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    with pytest.raises(ActionFailure):
        _dispatch(value, saved, 2)
    after = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 2)
    assert after["action"] == pending["action"] and json.loads(after["result"])["record_refs"] == []
    assert len(value.calculator_inputs) == 1


@pytest.mark.parametrize("change", ["ordinal_bool", "wrong_operation", "duplicate_selection", "wrong_source", "old_version"])
def test_native_configuration_requires_explicit_matching_current_v3_binding(tmp_path, change):
    resources, environments = _resources(tmp_path, native_binding=True)
    if change == "ordinal_bool": environments[0]["binding_ordinal_0based"] = True
    elif change == "wrong_operation": resources["ordinary"]["native_protease_kinetics"][0]["operation"] = "find_orfs"
    elif change == "duplicate_selection": environments *= 2
    elif change == "wrong_source": resources["ordinary"]["native_protease_kinetics"][0]["deployment"]["module"]["sha256"] = "f" * 64
    else: resources["ordinary"]["native_protease_kinetics"][0]["deployment"]["version"] = "molecular_sequence_deployment_v2"
    with pytest.raises((ValueError, ContractError)):
        host.normalize_protease_kinetics_configuration(resources, environments, policy=deepcopy(POLICY))


def test_factory_round_trip_configures_real_current_builder_saved_surface(boundary):
    value = boundary
    record = value.factory.as_record()
    assert record["protease_kinetics_saved_modes"] is True and "protease_kinetics_environments" not in record
    configured = value.registry._protease_kinetics_configuration
    assert configured["resources"] == [] and configured["saved_modes"] is True
    assert ExecutionServiceFactory.from_record(record).as_record() == record
    assert value.registry.execution_owner_for(value.flow.run_id).store is value.store
    assert TOOL in {row["name"] for row in value.flow.catalog(value.caller.source.scope, source=value.caller.source)}


def test_native_request_uses_numeric_file_values_and_existing_driver_v2_without_ascii_adapter(tmp_path):
    supplied, _capture, context = supplied_fixture()
    supplied["substrate_concentrations"][0] = -1
    document = dict(schema=contracts.INPUT_VERSION, measurements=supplied, assay_context=context)
    invocation = dict(run_id="actual-action-label", episode_id="episode", operation_key="run:episode:0")
    request = host._request(invocation, dict(mode="run_native", input=dict(namespace="artifact", reference="artifact_" + "a" * 64), rows=[]),
        dict(document=document), dict(resource_id="explicit-selected-resource", deployment=_selected_deployment()), tmp_path / "worker")
    assert request["version"] == driver.REQUEST_VERSION_V2 and request["selection"]["version"] == native.REQUEST_VERSION_V3
    assert request["selection"]["arguments"]["substrate_concentrations"] == [-1, 3, 6]
    assert request["scientific_context"] == dict(assay_context=context)
    assert not (tmp_path / "worker/driver-output").exists()
    assert common._molecular_worker_module("protease_kinetics_native") == "gene_annotation_episode.molecular_sequence_driver"
    assert common._molecular_worker_module("protease_kinetics_saved") == "gene_annotation_episode.molecular_sequence_driver"


def _closed_group(value):
    outcome = _dispatch(value, dict(mode="calculate_saved",
        input=dict(namespace="artifact", reference=value.reference), rows=_rows()), 0)
    assert outcome["status"] == "completed" and len(value.calculator_inputs) == 1
    return outcome["result"]


def _registered_protease_form(public):
    field = contracts.ordinary_protease_kinetics_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    return dict(measurements=[deepcopy(public)]), dict(type="object", properties=dict(measurements=field),
        required=["measurements"], additionalProperties=False)


def test_registered_protease_whole_field_preserves_opaque_file_provenance(boundary, monkeypatch):
    public = _closed_group(boundary)
    payload, schema = _registered_protease_form(public)
    assert schema["properties"]["measurements"]["x-source"] == contracts.FACT_SOURCE
    assert public["values"]["source_sheet_ref"] == boundary.reference
    assert public["values"]["source_components_ref"].startswith("artifact_")
    assert public["values"]["context"]["assay"]["value"]["calibration"]["source_ref"] == "constructed-calibration-fixture"
    nested = {public["values"]["source_sheet_ref"], public["values"]["source_components_ref"]}
    assert {row["source_ref"] for row in public["values"]["rows"]} <= nested
    calls = []
    def only_source(reference, namespace):
        calls.append((reference, namespace))
        return reference == public["source_ref"] and namespace == "source"
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    monkeypatch.setattr(boundary.registry, "_sequence_worker_async", _forbidden)
    assert validate_form(payload, schema, only_source) == payload
    assert calls == [(public["source_ref"], "source")]
    assert nested.isdisjoint(reference for reference, _namespace in calls)


@pytest.mark.parametrize("change", ["source_namespace", "schema_member", "nested_field", "stripped_fact_binding"])
def test_registered_protease_form_rejects_changed_complete_or_nested_contract(boundary, change):
    public = _closed_group(boundary)
    payload, schema = _registered_protease_form(public)
    field = schema["properties"]["measurements"]
    if change == "source_namespace":
        field["items"]["properties"]["source_ref"]["x-reference-namespace"] = "artifact"
    elif change == "schema_member":
        field["maxItems"] = 1  # A valid narrower JSON schema is still a different source-owned contract.
    elif change == "nested_field":
        schema["properties"]["measurements"] = dict(type="object", properties=dict(nested=field),
            required=["nested"], additionalProperties=False)
        payload["measurements"] = dict(nested=payload["measurements"])
    else:
        del field["x-source"]
    calls = []
    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return True
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(payload, schema, resolve)
    assert error.value.diagnostic["code"] == "invalid_schema" and calls == []


@pytest.mark.parametrize("change", ["bool_population", "context_provenance", "row_provenance", "value_type", "value_unit"])
def test_registered_protease_form_rejects_invalid_literal_meaning_before_reference_resolution(boundary, change):
    public = _closed_group(boundary)
    payload, schema = _registered_protease_form(public)
    returned = payload["measurements"][0]
    if change == "bool_population":
        returned["values"]["context"]["population"]["value"]["substrate_count"] = True
    elif change == "context_provenance":
        returned["values"]["context"]["assay"]["source_pointer"] = "/measurements"
    elif change == "row_provenance":
        returned["values"]["rows"][0]["source_ref"] = "artifact_" + "f" * 64
    elif change == "value_type":
        returned["values"]["rows"][0]["value"] = "12.0"
    else:
        returned["values"]["rows"][0]["unit"] = "invented_units"
    calls = []
    def resolve(reference, namespace):
        calls.append((reference, namespace))
        return True
    with pytest.raises(ReportBoundaryError):
        validate_form(payload, schema, resolve)
    assert calls == []


def test_registered_protease_form_rejects_unknown_top_source_after_schema_cache(boundary):
    public = _closed_group(boundary)
    payload, schema = _registered_protease_form(public)
    assert validate_form(payload, schema,
        lambda reference, namespace: reference == public["source_ref"] and namespace == "source") == payload
    unknown = "source_" + "f" * 24
    assert unknown != public["source_ref"]
    payload["measurements"][0]["source_ref"] = unknown
    calls = []
    def admitted_only(reference, namespace):
        calls.append((reference, namespace))
        return reference == public["source_ref"] and namespace == "source"
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(payload, schema, admitted_only)
    assert error.value.diagnostic["code"] == "unknown_reference"
    assert error.value.diagnostic["field"] == "report.measurements[0].source_ref"
    assert calls == [(unknown, "source")]


_PROTEASE_PUBLICATION = "research/slotted_process_library/publications/2026-10-24-001"
_PROTEASE_ORIGINAL_MODULE = "reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/biochemistry.py"
_PROTEASE_NATIVE_QUESTION = (
    "For the supplied engineered fluorescence time courses and declared substrate concentrations, "
    "what native signal-space Vmax and KM, full reported parameter covariance, population and "
    "initial-window qualifications are supported? Under the explicitly supplied signal calibration, "
    "enzyme-concentration basis and product stoichiometry, which physical product-rate, turnover "
    "and efficiency quantities are supported, and do the original retained and saved-sheet results "
    "agree without a second fit? Preserve the original and derived Source-owned views, the supplied "
    "assay conditions, conditional versus unknown total uncertainty, and native versus calibrated "
    "unit meanings. These are engineered input traces, not a wet-lab observation or proof of an "
    "enzyme's biological identity, substrate specificity or physiological function.")


def _protease_native_input():
    return dict(schema=contracts.INPUT_VERSION, measurements=dict(time_points=[0, 1, 2, 3, 4],
        fluorescence_data=[[1, 4.2, 7.4, 10.6, 13.8], [2, 7.8, 13.6, 19.4, 25.2],
            [3, 11.5, 20, 28.5, 37], [4, 13.4, 22.8, 32.2, 41.6]],
        substrate_concentrations=[1, 3, 6, 12], enzyme_concentration=.5),
        assay_context=dict(sample_key="explicit-engineered-protease-time-courses", substrate_identity=None,
            enzyme_identity=None, conditions="Engineered input traces; no experimental reaction identity established.",
            replicate_ids=None, units=dict(time="s", signal="RFU", substrate="uM", enzyme="uM"),
            calibration=dict(schema="protease_signal_calibration_v1", response_per_product_concentration=2,
                signal_unit="RFU", product_concentration_unit="uM", curve_ordinals=[0, 1, 2, 3],
                applicability="supported", source_ref="caller-declared-integration-calibration"),
            enzyme_basis="active_site_concentration", product_per_cleavage=1))


def _protease_native_rows():
    return [dict(row_id=dict(kind="summary"), fields=["time_point_count", "substrate_count", "supplied_curve_count",
            "requested_initial_point_count", "actual_initial_point_count"]),
        dict(row_id=dict(kind="protease_fit"), fields=["vmax", "km", "residual_sum_squares", "residual_degrees_of_freedom"]),
        *[dict(row_id=dict(kind="protease_covariance", parameter_i=i, parameter_j=j), fields=["reported_matrix_entry"])
            for i, j in ((0, 0), (0, 1), (1, 0), (1, 1))],
        dict(row_id=dict(kind="protease_quantity", quantity="apparent_turnover"), fields=["value", "variance", "standard_uncertainty"]),
        dict(row_id=dict(kind="protease_quantity", quantity="catalytic_efficiency"), fields=["value", "variance", "standard_uncertainty"])]


def _protease_native_form():
    field = contracts.ordinary_protease_kinetics_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    return dict(type="object", properties=dict(measurements=field), required=["measurements"], additionalProperties=False)


def _protease_native_closure(directory):
    """Bind the new run's explicitly staged material; never discover a fallback."""
    import os
    import sys
    root = Path(__file__).resolve().parents[1]
    attempt = Path(os.environ["HMMER529_ATTEMPT"]).resolve(strict=True)
    assert root == attempt / "source_snapshot"
    request = json.loads((attempt / "selected_request.json").read_bytes())
    assert request["support_files"] == [_PROTEASE_ORIGINAL_MODULE]
    assert request["support_trees"] == [_PROTEASE_PUBLICATION] and request["default_hmmer_fixtures"] is False
    assert request["native_executables"] == request["existing_native_executables"] == request["native_libraries"] == []
    assert request["policy"] == POLICY and request["swap_bytes"] == 0
    material = os.environ["HMMER_NATIVE_ORACLE_PROTEASE_MATERIAL_INVENTORY_SHA256"]
    assert material == "944857e0c9c6b52d06fbb411aec9fabaabe10172af1901a7a7041104e749ac04"
    assert request["environment"]["HMMER_NATIVE_ORACLE_PROTEASE_MATERIAL_INVENTORY_SHA256"] == material
    python = _pin(attempt / "runtime/bin/python")
    assert python["sha256"] == request["selected_python_source_pin"]["sha256"]
    assert Path(sys.executable).resolve(strict=True) == Path(python["path"])
    assert Path(sys.prefix).resolve(strict=True) == attempt / "runtime"
    module = _pin(root / _PROTEASE_ORIGINAL_MODULE)
    assert module["sha256"] == scientific.SOURCE_FILE_SHA256 and module["size_bytes"] == 41579
    # Named required packages must be present in the explicitly supplied material.
    # This is not an installation, service lookup or source of version claims.
    for name in ("numpy", "scipy", "matplotlib"):
        assert (attempt / "dependencies" / name / "__init__.py").is_file(), name + " absent from selected material"
    files = {}
    for kind in ("source", "dependency", "stdlib", "binary"):
        for pin in json.loads((attempt / (kind + "_pins_before.json")).read_bytes()):
            assert not Path(pin["path"]).is_symlink() and _pin(Path(pin["path"])) == pin
            assert pin["path"] not in files
            files[pin["path"]] = pin
    manifest = directory / "selected-native-software-files.json"
    _write(manifest, [files[key] for key in sorted(files)])
    pin = _pin(manifest)
    roots = [str(root), str(attempt / "dependencies"), str(root / "reference/episode_tools/.venv/lib/python3.12/site-packages")]
    deployment = dict(version=native.DEPLOYMENT_VERSION_V3, runtime=dict(executable=python, home=str(attempt / "runtime")),
        module=module, import_roots=roots, software_files_file=pin, software_files_ref="artifact_" + pin["sha256"])
    native._deployment(deployment, version=native.DEPLOYMENT_VERSION_V3, source_sha256=native.BIOCHEMISTRY_SOURCE_SHA256)
    return deployment, dict(selected_request=_pin(attempt / "selected_request.json"), python=python, module=module,
        manifest_file=pin, manifest_entry_count=len(files), declared_material_inventory_sha256=material,
        qualification="New current explicitly selected runtime/dependency/source closure; no original239 paths or custody reused.")


def _protease_native_controller(path, initial):
    from tests.test_runtime import FixtureController
    return FixtureController(str(path), initial, 4 if path[-1][0] == "scientific_process" else 1)


def _protease_native_assemble(store, directory, proof, provider):
    factory = ExecutionServiceFactory.from_record(proof["factory"])
    registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=proof["run_id"], directory=directory, tool_registry=registry)
    resources = proof["factory"]["resources"]
    assert factory.as_record() == proof["factory"]
    execution_record = next(record for record in application.episode_binding_descriptors
        if record["binding_id"] == "execution_episodes")
    assert execution_record["configuration"]["resources"] == resources
    workflow = Workflow(store, registry, provider, directory, proof["run_id"], _protease_native_controller, _credit,
        project_child_credit=_credit, episode_record_receipts=True,
        initial_known_record_refs=proof["initial_known_record_refs"],
        episode_binding_descriptors=[proof["scientific_binding"], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    owner = registry.execution_owner_for(proof["run_id"])
    assert owner.resources == resources and owner.as_record() == execution_record
    assert owner.job_progress_provider.resources == owner.job_progress_provider.targets.resources == resources
    selected = registry._protease_kinetics_configuration["resources"]
    assert len(selected) == 1 and selected[0]["resource"] == resources[selected[0]["resource_id"]]
    assert selected[0]["binding_ordinal_0based"] == 0
    for resource_id, resource in resources.items():
        practical = owner._practical[resource_id]
        assert practical.resources == {"local": resource}
        assert practical.as_record()["configuration"]["resources"] == {"local": resource}
        projected = {key: value for key, value in resource.items() if key != "native_protease_kinetics"}
        assert practical._operations("local").configuration == projected
        assert owner.job_progress_provider.targets.operations[resource_id].configuration == projected
        assert "native_protease_kinetics" in resource
    resource_contracts = owner.resource_tool_contracts()
    assert TOOL not in {entry["name"] for entry in resource_contracts}
    assert registry.catalog()[TOOL] == proof["selected_tool_contract"]
    assert registry.catalog()[TOOL]["invocation_route"] == dict(kind="direct")
    proof["resource_preflight"] = dict(full_factory_and_execution_records_preserved=True,
        full_ordinary_binding_preserved=True, practical_leaf_excludes_only="native_protease_kinetics",
        practical_protease_advertised=False, practical_tool_names=[entry["name"] for entry in resource_contracts])
    return workflow, registry


def _protease_native_checkpoint(store, proof, path):
    from tests.test_molecular_sequence_n_glycosylation_native import _checkpoint
    _checkpoint(store, proof, path)


def _protease_native_operations(store, run_id):
    return [dict(row) for row in store.db.execute("SELECT * FROM tool_operations "
        "WHERE substr(operation_key,1,?)=? AND name=? ORDER BY rowid", (len(run_id) + 1, run_id + ":", TOOL))]


class _ProteaseNativeChoices:
    """Persisted decision indices select finite fixture choices, never a grader."""
    def __init__(self, store, library, proof, output, active):
        from gene_annotation_episode.providers import _SessionConnection
        self.store, self.library, self.proof, self.output, self.active = store, library, proof, output, active
        self.states = {}
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        from gene_annotation_episode.decision_context import state_frame
        from gene_annotation_episode.evidence_axis_instructions import instruction_view
        from tests.test_homer_motif_saved_workflow import _encode
        from tests.test_molecular_sequence_n_glycosylation_native import _files
        context = plain(context)
        if context.get("feedback"):
            raise RuntimeError("unexpected_protease_action_feedback:" + json.dumps(context["feedback"], sort_keys=True))
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        grain = json.loads(row["path"])[-1][0]
        turn = self.store.db.execute("SELECT count(*)+1 FROM runtime_model_calls "
            "WHERE run_id=? AND episode_id=? AND response IS NOT NULL", (self.proof["run_id"], episode_id)).fetchone()[0]
        assert role == "REASONING" and context["goal"]["objective"] == _PROTEASE_NATIVE_QUESTION
        assert context["goal"]["task_context"]["root_objective"] == _PROTEASE_NATIVE_QUESTION
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        call = dict(episode_id=episode_id, grain=grain, turn=turn, context=deepcopy(context), instructions=plain(instructions),
            schema=deepcopy(schema), wire=wire, wire_instructions=plain(wire_instructions),
            wire_sha256=hashlib.sha256(wire.encode()).hexdigest(), wire_size_bytes=len(wire.encode()))
        self.proof["calls"].append(call)
        previous = [json.loads(row["result"]) for row in _protease_native_operations(self.store, self.proof["run_id"])]
        if grain == "annotation" and turn == 1:
            selected = dict(kind="episode_child", role="scientific_process", goal=_PROTEASE_NATIVE_QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=_PROTEASE_NATIVE_QUESTION,
                schema_json=json.dumps(_protease_native_form()), initial_report_json="{}",
                assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A105"), thought_pattern=self.library.reference("P14"),
                    child_tool_info=[dict(name=TOOL, resources="local")]), evidence_refs=[], constraints={},
                    context=dict(protease_request=deepcopy(self.proof["arguments"]))))
        else:
            assert grain == "scientific_process"
            assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and _PROTEASE_NATIVE_QUESTION in wire
            assert str(Path(self.proof["case_directory"])) not in wire
            if grain == "scientific_process":
                assert 1 <= turn <= 4 and context["requested_form"] == _protease_native_form()
                process = context["scientific_process"]
                assert process["evidence_axis"] == instruction_view(self.library.resolve(self.library.reference("A105")))
                assert process["assignment"]["context"]["protease_request"] == self.proof["arguments"]
                entry, = [item for item in context["tools"] if item["name"] == TOOL]
                assert entry["resources"] == "local"
                assert self.proof["selected_tool_contract"]["instructions"] in wire
                assert self.proof["selected_tool_contract"]["description"] in wire
                if turn == 1:
                    arguments = deepcopy(self.proof["arguments"])
                elif turn == 2:
                    assert len(previous) == 1 and previous[0]["result"]["values"]["rows"] == []
                    arguments = dict(mode="read_stored", result_ref=previous[0]["result"]["source_ref"], rows=[])
                elif turn == 3:
                    assert len(previous) == 2 and previous[0]["result"] == previous[1]["result"]
                    self.proof["original_literal_read_verified"] = True
                    source = self.store.get(previous[0]["result"]["source_ref"])
                    control = self.active["controls"][source["id"]]
                    original = Path(control["worker"]["selection"]["cwd"]).parent
                    assert original.parent == self.store.path / "cache/molecular-measurements"
                    retained = Path(self.proof["case_directory"]) / "retained-native-action"
                    self.proof["native_action_files_before_move"] = _files(original)
                    assert not retained.exists()
                    original.rename(retained)
                    assert _files(retained) == self.proof["native_action_files_before_move"]
                    self.proof["retained_native_action_directory"] = str(retained)
                    file = self.proof["input_file"]
                    body = self.store.path / "artifacts" / file["sha256"][:2] / file["sha256"]
                    assert _pin(body)["sha256"] == file["sha256"]
                    body.unlink()
                    self.proof["owned_original_assay_body_removed"] = True
                    manifest = Path(self.proof["closure"]["manifest_file"]["path"])
                    assert _pin(manifest) == self.proof["closure"]["manifest_file"]
                    manifest.rename(Path(self.proof["case_directory"]) / "retained-selected-native-software-files.json")
                    self.proof["owned_native_manifest_moved"] = True
                    self.active["phase"] = "saved_prepare"
                    arguments = dict(mode="calculate_saved", result_ref=source["id"], rows=[])
                else:
                    assert len(previous) == 3 and previous[2]["result"]["source_ref"] != previous[0]["result"]["source_ref"]
                    self.active["phase"] = "numeric_read"
                    arguments = dict(mode="read_stored", result_ref=previous[2]["result"]["source_ref"], rows=_protease_native_rows())
                if turn > 1:
                    shown = contracts.validate_ordinary_protease_kinetics_return(context["last_local_outcome"]["result"])
                    assert shown == previous[-1]["result"]
            if previous:
                assert "Selected molecular result" in wire
                for required in ("complete_supplied_curve_population", "RFU", "no_total_uncertainty_or_function_probability"):
                    assert required in wire
            if arguments is not None:
                selected = dict(kind="tool", tool=TOOL, arguments=arguments)
        answer = _encode(dict(selection=selected, report_update={}), schema)
        call["response"] = deepcopy(answer)
        self.proof["phase"] = "decision_selected"
        _protease_native_checkpoint(self.store, self.proof, self.output)
        return answer

    async def release(self, episode_id):
        self.proof["provider_cleanup_callbacks"].append(episode_id)


def _protease_native_verify(store, workflow, registry, proof):
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from tests.test_homer_motif_saved_workflow import _archive
    from tests.test_molecular_sequence_n_glycosylation_native import _history
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" and row["completion"] and row["archive"] for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    operations = _protease_native_operations(store, proof["run_id"])
    assert len(operations) == 4 and len(history["tool_operations"]) == 4
    assert [json.loads(row["arguments"])["mode"] for row in operations] == ["run_native", "read_stored", "calculate_saved", "read_stored"]
    outcomes = [json.loads(row["result"]) for row in operations]
    assert all(outcome["status"] == "completed" for outcome in outcomes)
    values = [contracts.validate_ordinary_protease_kinetics_return(outcome["result"]) for outcome in outcomes]
    assert values[0] == values[1] and values[0]["values"]["rows"] == values[2]["values"]["rows"] == []
    assert values[0]["source_ref"] != values[2]["source_ref"] == values[3]["source_ref"]
    assert values[0]["values"]["context"] == values[2]["values"]["context"] == values[3]["values"]["context"]
    expected = [values[0], values[2], values[3]]
    records = EpisodeReturnRecords(store, proof["run_id"], failure_prefix="protease_native_proof_")
    parent, science = [records.context(row["episode_id"]) for row in episodes]
    for context in (parent, science): records.authenticate(context)
    assert workflow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == expected
    assert workflow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == expected
    assert workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == expected
    frozen, = history["runtime_forms"]
    reports = history["runtime_report_attempts"]
    assert len(reports) == 1
    assert json.loads(frozen["form"]) == dict(measurements=expected)
    assert json.loads(frozen["facts"])[contracts.FACT_SOURCE] == expected
    assert all(report["failure"] is None and json.loads(report["form"]) == dict(measurements=expected) for report in reports)
    assert all(report["parent_episode_id"] == parent.episode_id and report["child_episode_id"] == science.episode_id for report in reports)
    publications = [host.read_protease_kinetics_publication(registry, science, workflow.services.read_received_molecular_input,
        value["source_ref"], require_numeric=True) for value in (values[0], values[2])]
    controls = [publication["control"] for publication in publications]
    original, saved = controls
    assert [control["intent"]["request"]["mode"] for control in controls] == ["native", "saved_sheet"]
    assert [control["intent"]["worker_operation"] for control in controls] == ["protease_kinetics_native", "protease_kinetics_saved"]
    assert original["intent"]["selected_resource"] is not None and saved["intent"]["selected_resource"] is None
    assert original["intent"]["input"]["document"] == proof["input_document"]
    assert saved["intent"]["request"]["scientific_context"] is None
    assert saved["intent"]["input"]["sheet_ref"] == original["files"]["sheet"]["file"]["artifact_ref"]
    assert saved["files"]["sheet"]["file"] == original["files"]["sheet"]["file"]
    assert saved["files"]["components"]["file"] == original["files"]["components"]["file"]
    assert saved["files"]["capture"]["state"] == "not_requested"
    assert original["files"]["native_results"]["state"] == original["files"]["native_plot"]["state"] == "retained"
    for control, operation in zip(controls, (operations[0], operations[2])):
        worker = control["worker"]
        assert worker["observation"]["terminal"] is worker["observation"]["quiescent"] is True
        assert worker["observation"]["metadata"]["native_returncode"] == 0
        assert worker["selection"]["policy"] == POLICY and worker["handle"]["command"] == worker["selection"]["command"]
        assert worker["declaration"]["driver_failure"] is None
        assert worker["declaration"]["attempt_identity"]["operation_key"] == operation["operation_key"]
    sheet, components = publications[0]["sheet"], publications[0]["components"]
    capture = json.loads(store.get_artifact(original["files"]["capture"]["file"]["artifact_ref"]))
    assert capture == sheet["native_observation"] and capture["failure"] is None
    assert capture["native_call_state"] == "returned" and capture["native_record"]["outcome"] == "completed"
    assert capture["observer"]["selected_call_count"] == capture["observer"]["selected_terminal_event_count"] == 1
    assert capture["observer"]["state"] == "captured" and capture["observer"]["profile_restored"] is True
    assert capture["observer"]["failures"] == capture["verification_failures"] == []
    receipt = capture["execution_receipt"]
    assert receipt["module_load"]["source_file"]["sha256"] == scientific.SOURCE_FILE_SHA256
    assert receipt["observed_callable"]["sha256"] == scientific.SOURCE_FUNCTION_SHA256
    assert {row["module_name"] for row in receipt["libraries"]} == {"numpy", "scipy", "matplotlib"}
    assert all(row["distribution_version"] and row["module_version"] == row["distribution_version"] for row in receipt["libraries"])
    assert sheet["measurements"] == proof["input_document"]["measurements"]
    assert sheet["assay_context"] == proof["input_document"]["assay_context"]
    matrix, parameters = capture["observer"]["locals"]["covariance"], capture["observer"]["locals"]["params"]
    assert len(parameters) == 2 and len(matrix) == 2 and all(len(row) == 2 for row in matrix) and matrix[0][1] != 0
    assert components["fit_components"]["parameter_order"] == ["vmax", "km"]
    assert [components["fit_components"][name]["value"] for name in ("vmax", "km")] == parameters
    assert components["fit_components"]["covariance"] == matrix
    assert components["fit_components"]["residual_degrees_of_freedom"] == 2
    assert [sheet["population"][key] for key in ("time_point_count", "substrate_count", "supplied_curve_count",
        "requested_initial_point_count", "actual_initial_point_count")] == [5, 4, 4, 5, 5]
    assert components["population"] == sheet["population"] and components["function_probability"] is None
    context = values[3]["values"]["context"]
    assert context["assay"]["value"] == proof["input_document"]["assay_context"]
    assert context["method"]["native_unit_claims"]["value"] == scientific.SOURCE_METHOD["native_unit_claims"]
    assert context["parameters"]["vmax"]["unit"]["value"] == "RFU/s"
    assert context["covariance"]["raw_matrix"]["value"] == matrix
    assert context["qualifications"]["value"] == scientific.QUALIFICATIONS
    for quantity in stored.QUANTITIES:
        assert context["physical"][quantity]["uncertainty"]["total_uncertainty"]["value_state"] == "stored_null"
    cells = values[3]["values"]["rows"]
    covariance_cells = [row for row in cells if row["row_id"]["kind"] == "protease_covariance"]
    assert [row["value"] for row in covariance_cells] == [matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]]
    for row in cells:
        if row["row_id"]["kind"] == "protease_quantity":
            assert [cell["kind"] for cell in row["denominators"]][:3] == ["calibration_response", "enzyme_concentration", "product_per_cleavage"]
            assert [cell["value"] for cell in row["denominators"]][:3] == [2, .5, 1]
    for index, (outcome, value) in enumerate(zip(outcomes, values)):
        assert outcome["record_refs"] == [value["source_ref"]]
        assert outcome["changed_record_refs"] == ([value["source_ref"]] if index in (0, 2) else [])
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert {proof["input_file"]["artifact_ref"], values[0]["source_ref"], values[2]["source_ref"]} <= known
        resolver = workflow.resolver(plain(context.scope), context=context)
        assert resolver(proof["input_file"]["artifact_ref"], "artifact") is True
        for publication in publications:
            source = publication["source"]
            private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
            assert proof["input_file"]["artifact_ref"] not in private and private.isdisjoint(known)
            for reference in private:
                denied, path = workflow.services.read_received_molecular_input(context, reference, "artifact", file_format="json")
                assert path is None and denied["failure"] is not None
    archives = [_archive(row, workflow.directory) for row in episodes]
    assert [row["units_consumed"] for row in archives] == [1, 4]
    assert archives[0]["units"][0]["child_result"] == dict(form=dict(measurements=expected))
    assert len(proof["calls"]) == len(history["runtime_model_calls"]) == 5
    for recorded, row in zip(proof["calls"], history["runtime_model_calls"]):
        assert json.loads(row["request"])["context"] == recorded["context"]
        assert json.loads(row["response"]) == recorded["response"]
        assert recorded["wire_sha256"] == hashlib.sha256(recorded["wire"].encode()).hexdigest()
    return dict(returned=dict(measurements=expected), episode_ids=[parent.episode_id, science.episode_id],
        archives=archives, native_selected_call_count=1, saved_worker_count=1,
        original_files=deepcopy(original["files"]), derived_files=deepcopy(saved["files"]),
        original_native_handle=deepcopy(original["worker"]["handle"]), derived_handle=deepcopy(saved["worker"]["handle"]))


class _ProteaseNoNewDecisions:
    def __init__(self):
        self.cleanup_callbacks = []

    async def complete(self, *args, **kwargs):
        _forbidden()

    async def release(self, episode_id):
        self.cleanup_callbacks.append(episode_id)


def _protease_native_closed_replay(store, directory, proof, monkeypatch):
    from gene_annotation_episode.runtime import ReturnedActionUnit
    from tests.test_homer_motif_saved_workflow import _archive, _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history
    before_tables, before_files = _tables(store), _files(directory)
    before_artifacts = _files(store.path / "artifacts")
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    parent_archive, child_archive = [_archive(row, directory) for row in episodes]
    provider = _ProteaseNoNewDecisions()
    actual_get = Store.get_artifact
    returned = []
    with monkeypatch.context() as guarded:
        for module, names in ((native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release")),
                (native, ("execute_molecular_sequence_request", "_manifest", "_exact_file")),
                (driver, ("run_molecular_sequence_driver",)), (common, ("run_owned_molecular_worker",))):
            for name in names:
                guarded.setattr(module, name, _forbidden)
        guarded.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
        guarded.setattr(ToolRegistry, "execute_async", _forbidden)
        guarded.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
        guarded.setattr(Store, "get_artifact", _forbidden)
        guarded.setattr("socket.create_connection", _forbidden)
        workflow, registry = _protease_native_assemble(store, directory, proof, provider)
        guarded.setattr(registry.clients, "_http", _forbidden)
        selected = workflow._closed_child_commission
        def closed(*args, **kwargs):
            unit = selected(*args, **kwargs)
            assert isinstance(unit, ReturnedActionUnit)
            assert plain(unit.request.as_record()) == json.loads(episodes[1]["request"])
            assert _archive_value(unit.record) == child_archive
            assert plain(unit.result.as_record()) == dict(form=proof["delivery"]["returned"])
            returned.append(unit)
            return unit
        guarded.setattr(workflow, "_closed_child_commission", closed)
        root = workflow.build("annotation", "root", _PROTEASE_NATIVE_QUESTION, proof["scope"])
        record = asyncio.run(root.run_async(workflow.context))
        final = _archive_value(asyncio.run(root.build_result(record)))
        assert final == dict(credit=0, pending_handles=[]) and _archive_value(record) == parent_archive
        assert len(returned) == 1
        # The ordinary root already closed through its real controller. This
        # read-side reconstruction uses its actual admitted child report/view;
        # it is not a historical post-return decision or a new provider call.
        from gene_annotation_episode.runtime import DecisionSource
        from gene_annotation_episode.providers import _SessionConnection
        from gene_annotation_episode.decision_context import state_frame
        from method_loop.episode import EpisodeView
        receiver_scope = workflow.context.enter(root.grain, root.key)
        try:
            assert receiver_scope == root.source.path == record.path
            view = EpisodeView(grain=root.grain, key=root.key, path=receiver_scope,
                units_consumed=record.units_consumed,
                updates=tuple(workflow.context._child_updates.get(receiver_scope, ())),
                controller_state=record.controller_state, episode_ref=record.episode_ref, request=record.request)
            assert _archive_value(view.controller_state) == parent_archive["controller_state"]
            assert [plain(report.as_record()) for report in view.child_reports] == [proof["delivery"]["returned"]]
            packet_files = {source["artifact_ref"] for source in proof["publications"]}
            public_reads, receiver = [], {}
            def public_only(current, reference):
                assert reference in packet_files
                public_reads.append(reference)
                return actual_get(current, reference)
            class ReceiverCaptured(BaseException):
                pass
            async def capture_call(source, context, schema):
                assert source is root.source and context["child_reports"] == [proof["delivery"]["returned"]]
                instructions = source.instructions(context)
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                with guarded.context() as no_io:
                    no_io.setattr(Store, "get_artifact", _forbidden)
                    wire, wire_instructions = connection._presentation(source.episode_id, "REASONING", instructions,
                        state_frame(plain(context)))
                assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and _PROTEASE_NATIVE_QUESTION in wire
                assert "Selected molecular result" in wire and str(Path(proof["case_directory"])) not in wire
                for literal in ("complete_supplied_curve_population", "RFU", "no_total_uncertainty_or_function_probability"):
                    assert literal in wire
                receiver.update(context=plain(context), schema=deepcopy(schema), instructions=plain(instructions), wire=wire,
                    wire_instructions=plain(wire_instructions), wire_sha256=hashlib.sha256(wire.encode()).hexdigest(),
                    current_builder_verified=True, historical_post_return_decision_claimed=False, new_provider_decisions=0)
                raise ReceiverCaptured()
            guarded.setattr(Store, "get_artifact", public_only)
            guarded.setattr(DecisionSource, "call", capture_call)
            original_calls = root.source.calls
            with pytest.raises(ReceiverCaptured):
                asyncio.run(root.source.next(view))
            assert root.source.calls == original_calls and receiver
            receiver["public_packet_reads"] = public_reads
        finally:
            workflow.context.leave(receiver_scope)
    assert _tables(store) == before_tables and _history(store, proof["run_id"]) == history
    assert _files(directory) == before_files and _files(store.path / "artifacts") == before_artifacts
    return dict(new_native=0, new_calculations=0, new_tool_calls=0, new_provider_decisions=0,
        provider_cleanup_callbacks=provider.cleanup_callbacks, all_tables_unchanged=True,
        files_and_modes_unchanged=True, final=final, receiver_reconstruction=receiver)


def test_genuine_current_protease_native_saved_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    import os
    if os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_PROTEASE_KINETICS") != "1":
        pytest.skip("requires explicit bounded current ordinary protease native selection")
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from tests.test_homer_motif_saved_workflow import _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _sqlite_pins
    tag = os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_PROTEASE_KINETICS_ATTEMPT_ID")
    assert tag and Path(tag).name == tag and tag not in (".", "..")
    case = tmp_path / ("protease-kinetics-" + tag)
    case.mkdir()
    output = case / "PROTEASE_KINETICS_WORKFLOW.json"
    proof = dict(version="ordinary_protease_kinetics_workflow_v1", run_id="ordinary-protease-" + tag,
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=_PROTEASE_NATIVE_QUESTION, calls=[], workers=[], publications=[], body_reads=[],
        provider_cleanup_callbacks=[], phase="prepared", original_literal_read_verified=False,
        owned_original_assay_body_removed=False, owned_native_manifest_moved=False,
        native_custody_verified=False, typed_delivery_verified=False, closed_replay_verified=False, passed=False,
        qualification="One new current native fit on explicitly supplied engineered numeric traces; no historical239 rerun or biological measurement claim.")
    _write(output, proof)
    active = dict(phase="native", publications={}, controls={}, saved_output_refs=set())
    try:
        deployment, proof["closure"] = _protease_native_closure(case)
        workspace = case / "native-resource-workspace"
        workspace.mkdir()
        resources = {"selected-protease": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY),
            native_protease_kinetics=[dict(operation=TOOL, deployment=deployment)])}
        environments = [dict(operation=TOOL, resource_id="selected-protease", binding_ordinal_0based=0)]
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
            protease_kinetics_environments=environments, protease_kinetics_saved_modes=True)
        proof["factory"] = factory.as_record()
        with Store(case / "store") as store:
            store.create_problem(raw_sequence="ACGT", molecule="dna")
            document = contracts.validate_ordinary_protease_kinetics_input(_protease_native_input())
            material = store.register_material(data=canonical(document).encode(), name="explicit-engineered-protease-assay", use="evidence")
            supplied = store.get(material["source_ref"])
            file = store.get(supplied["artifact_ref"])
            proof.update(scope=store.validate_scope(), input_document=document, material_ref=material["id"],
                supplied_source_ref=supplied["id"], input_file=dict(artifact_ref=file["id"], sha256=file["sha256"], size_bytes=file["size"], format="json"),
                initial_known_record_refs=[file["id"]], arguments=dict(mode="run_native", input=dict(namespace="artifact", reference=file["id"]), rows=[]))
            configured = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(configured)
            proof["selected_tool_contract"] = configured.catalog()[TOOL]
            assert proof["selected_tool_contract"]["invocation_route"] == dict(kind="direct")
            proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run",
                source_directory=Path(__file__).resolve().parents[1] / _PROTEASE_PUBLICATION,
                tool_catalog=configured.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(case / "run/scientific-process-library")
            provider = _ProteaseNativeChoices(store, library, proof, output, active)
            workflow, registry = _protease_native_assemble(store, case / "run", proof, provider)
            get, worker, save = Store.get_artifact, registry._sequence_worker_async, registry._save
            def guarded_get(current, reference):
                phase = active["phase"]
                public = {source["artifact_ref"] for source in active["publications"].values()}
                allowed = set(public)
                controls = list(active["controls"].values())
                if phase in ("saved_prepare", "saved_publication"):
                    allowed.update(source["request_ref"] for source in active["publications"].values())
                    allowed.update(control["files"]["sheet"]["file"]["artifact_ref"] for control in controls)
                    allowed.update(active["saved_output_refs"])
                elif phase == "numeric_read":
                    allowed.update(source["request_ref"] for source in active["publications"].values())
                    allowed.update(control["files"][role]["file"]["artifact_ref"] for control in controls for role in ("sheet", "components"))
                if phase not in ("native", "audit"):
                    assert reference in allowed, "forbidden private/native/input body during " + phase
                proof["body_reads"].append(dict(phase=phase, reference=reference))
                return get(current, reference)
            async def observed_worker(operation, arguments, **kwargs):
                assert operation in ("protease_kinetics_native", "protease_kinetics_saved")
                assert [item["operation"] for item in proof["workers"]] == ([] if operation == "protease_kinetics_native" else ["protease_kinetics_native"])
                assert active["phase"] == ("native" if operation == "protease_kinetics_native" else "saved_prepare")
                observation = dict(operation=operation, directory=str(kwargs["directory"]), phase="selected", request=deepcopy(arguments["request"]))
                proof["workers"].append(observation)
                _protease_native_checkpoint(store, proof, output)
                result = await worker(operation, arguments, **kwargs)
                observation.update(phase="returned", output_path=str(result.output_path), metadata=deepcopy(result.metadata))
                if Path(result.output_path).is_file():
                    observation["declaration_file"] = _pin(Path(result.output_path))
                    if operation == "protease_kinetics_saved":
                        declaration = json.loads(Path(result.output_path).read_bytes())
                        active["saved_output_refs"].update("artifact_" + item["sha256"] for item in declaration["files"].values() if item["state"] == "present")
                        active["phase"] = "saved_publication"
                _protease_native_checkpoint(store, proof, output)
                return result
            def observed_save(key, name, arguments, scope, outcome):
                save(key, name, arguments, scope, outcome)
                if name == TOOL and arguments["mode"] in ("run_native", "calculate_saved") and outcome.get("result") is not None:
                    source = store.get(outcome["result"]["source_ref"])
                    active["publications"][source["id"]] = source
                    active["controls"][source["id"]] = json.loads(get(store, source["request_ref"]))
                    proof["body_reads"].append(dict(phase="producer_control_observation", reference=source["request_ref"]))
                    proof["publications"].append(deepcopy(source))
                    active["phase"] = "literal_original" if arguments["mode"] == "run_native" else "literal_derived"
            try:
                with monkeypatch.context() as measured:
                    measured.setattr(Store, "get_artifact", guarded_get)
                    measured.setattr(registry, "_sequence_worker_async", observed_worker)
                    measured.setattr(registry, "_save", observed_save)
                    measured.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
                    measured.setattr(driver, "run_molecular_sequence_driver", _forbidden)
                    measured.setattr(native, "execute_molecular_sequence_request", _forbidden)
                    measured.setattr(registry.clients, "_http", _forbidden)
                    measured.setattr("socket.create_connection", _forbidden)
                    root = workflow.build("annotation", "root", _PROTEASE_NATIVE_QUESTION, proof["scope"])
                    completed = asyncio.run(root.run_async(workflow.context))
                    proof.update(phase="workflow_returned", archive=_archive_value(completed))
                    _protease_native_checkpoint(store, proof, output)
                    active["phase"] = "audit"
                    proof["delivery"] = _protease_native_verify(store, workflow, registry, proof)
                    proof.update(native_custody_verified=True, typed_delivery_verified=True)
                    proof["final_result"] = _archive_value(asyncio.run(root.build_result(completed)))
                    assert proof["final_result"] == dict(credit=0, pending_handles=[])
                    assert [item["operation"] for item in proof["workers"]] == ["protease_kinetics_native", "protease_kinetics_saved"]
                proof["replay"] = _protease_native_closed_replay(store, case / "run", proof, monkeypatch)
                proof.update(closed_replay_verified=True, passed=True, phase="verified")
            finally:
                _protease_native_checkpoint(store, proof, output)
    except BaseException as error:
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        if (case / "store/state.sqlite3").is_file():
            proof["sqlite_pins"] = _sqlite_pins(case / "store")
            proof["sqlite_pins_sha256"] = digest(proof["sqlite_pins"])
        _write(output, proof)


@pytest.mark.parametrize("conditions", [
    {"slot": "thought_pattern", "evidence": {"buffer": "declared"}},
    {"option_ref": {"salt": "literal"}, "entry": {"buffer": "declared"}, "temperature_C": 25},
    {"entries": [{"buffer": "declared"}], "library": {"plate_id": "supplied_plate"}},
    {"content_role": "tool_and_resource_instructions_not_scientific_evidence", "library_id": "declared_plate",
        "entry_count": 4, "section_sha256": "caller_literal_not_tracking"},
])
def test_protease_information_filter_preserves_opaque_supplied_assay_conditions(boundary, monkeypatch, conditions):
    """Engineered presentation value; no new custody or scientific claim."""
    from gene_annotation_episode.scientific_process_prompt import _information, _values
    public = deepcopy(_closed_group(boundary))
    public["values"]["context"]["assay"]["value"]["conditions"] = deepcopy(conditions)
    contracts.validate_ordinary_protease_kinetics_return(public)
    outcome = dict(status="completed", result=public, record_refs=[public["source_ref"]], changed_record_refs=[])
    before = deepcopy(outcome)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    shown = _information(outcome)
    assert shown == before and shown is not outcome
    assert shown["result"]["values"]["context"]["assay"]["value"]["conditions"] == conditions
    text = _values(shown)
    for key in conditions:
        assert key in text
    assert outcome == before


def test_protease_failure_presentation_uses_diagnostic_role_without_private_address(boundary, monkeypatch):
    """A valid engineered failure association is not successful-native evidence."""
    from gene_annotation_episode.scientific_process_prompt import _selected_molecular_text
    public = deepcopy(_closed_group(boundary))
    diagnostic = "artifact_" + "e" * 64
    public["failures"].append(stored.failure("schema_invalid", "load", role="components", diagnostic_ref=diagnostic))
    public = contracts.validate_ordinary_protease_kinetics_return(public)
    monkeypatch.setattr(Store, "get_artifact", _forbidden)
    monkeypatch.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
    text = _selected_molecular_text(public, 1)
    assert diagnostic not in text and "diagnostic_ref" not in text
    assert "diagnostic_role" in text and "retained diagnostic association" in text and "schema_invalid" in text


def test_practical_leaf_projects_only_ordinary_protease_metadata_and_rejects_unknown_keys(tmp_path):
    from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
    resources, _ = _resources(tmp_path, native_binding=True)
    resource = resources["ordinary"]
    original = deepcopy(resource)
    operations = LocalPracticalOperations(resource)
    assert operations.configuration == {key: value for key, value in original.items()
        if key != "native_protease_kinetics"}
    assert resource == original
    operations.configuration["policy"]["scratch_bytes"] = 1
    assert resource == original
    invalid = deepcopy(resource)
    invalid["native_protease_kinetics_unknown"] = deepcopy(resource["native_protease_kinetics"])
    before = deepcopy(invalid)
    with pytest.raises(ValueError, match="^explicit_local_practical_configuration_required$"):
        LocalPracticalOperations(invalid)
    assert invalid == before


def _protease_retained_load():
    import os
    path = Path(os.environ["HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_PROOF"])
    assert path.is_absolute() and not path.is_symlink()
    raw = path.read_bytes()
    expected = os.environ["HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_PROOF_SHA256"]
    assert expected == "285b794017e8ea25712252edfb22c2be4deb644b1d216851526cdfe232c02c1c"
    assert hashlib.sha256(raw).hexdigest() == expected and len(raw) == 38438411
    original = json.loads(raw)
    assert path.parent == Path(original["case_directory"])
    assert original["phase"] == "workflow_returned" and original["passed"] is False
    assert original["typed_delivery_verified"] is original["closed_replay_verified"] is False
    assert original["failure"]["exception_type"] == "AssertionError"
    assert original["run_id"] == "ordinary-protease-current542"
    assert [row["operation"] for row in original["workers"]] == ["protease_kinetics_native", "protease_kinetics_saved"]
    assert all(row["phase"] == "returned" and row["metadata"]["native_returncode"] == 0 for row in original["workers"])
    pins = original["sqlite_pins"]
    assert pins == [dict(name="state.sqlite3", sha256="bd6d4644721f34addc7bb7d414e4d351f8cd61233d822ba9f9a1789be4a14a4b", size_bytes=19988480)]
    assert digest(pins) == original["sqlite_pins_sha256"]
    directory = Path(original["store_directory"])
    assert sorted(item.name for item in directory.glob("state.sqlite3*")) == ["state.sqlite3"]
    assert _pin(directory / "state.sqlite3") == dict(path=str(directory / "state.sqlite3"),
        sha256=pins[0]["sha256"], size_bytes=pins[0]["size_bytes"])
    return path, original


def _protease_retained_original(store, original):
    from tests.test_homer_motif_saved_workflow import _archive
    from tests.test_molecular_sequence_n_glycosylation_native import _history
    history = _history(store, original["run_id"])
    assert history == original["history"]
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
    assert [json.loads(row["completion"])["actions"] for row in episodes] == [1, 4]
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    assert len(history["tool_operations"]) == 4
    form, = history["runtime_forms"]
    expected = json.loads(form["form"])["measurements"]
    assert json.loads(form["facts"])[contracts.FACT_SOURCE] == expected and len(expected) == 3
    assert [len(item["values"]["rows"]) for item in expected] == [0, 0, 19]
    assert [item["source_ref"] for item in expected] == [original["publications"][0]["id"],
        original["publications"][1]["id"], original["publications"][1]["id"]]
    attempt, = history["runtime_report_attempts"]
    failure = json.loads(attempt["failure"])
    assert attempt["form"] is None and failure["kind"] == "report_delivery_failure"
    assert failure["field"] == "measurements.2.values.rows.13" and failure["reason"] == "anyOf"
    parent_refs = {row[0] for row in store.db.execute("SELECT record_ref FROM runtime_record_receipts "
        "WHERE run_id=? AND episode_id=?", (original["run_id"], episodes[0]["episode_id"]))}
    assert not parent_refs.intersection(item["id"] for item in original["publications"])
    outcomes = [json.loads(row["result"]) for row in _protease_native_operations(store, original["run_id"])]
    assert [json.loads(row["arguments"])["mode"] for row in _protease_native_operations(store, original["run_id"])] == [
        "run_native", "read_stored", "calculate_saved", "read_stored"]
    assert all(row["status"] == "completed" for row in outcomes)
    assert [outcomes[index]["result"] for index in (0, 2, 3)] == expected
    for source in original["publications"]:
        assert store.get(source["id"]) == source
    archives = [_archive(row, Path(original["workflow_directory"])) for row in episodes]
    assert archives[0] == original["archive"]
    return expected, dict(history=history, episodes=episodes, failed_attempt=attempt,
        original_archives=archives, original_delivery_failed=True)


class _ProteaseRetainedChoices:
    """New current choices admit metadata, then read the three original views."""
    def __init__(self, store, library, proof, output, expected):
        from gene_annotation_episode.providers import _SessionConnection
        self.store, self.library, self.proof, self.output, self.expected = store, library, proof, output, expected
        self.states = {}
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    async def complete(self, episode_id, role, instructions, context, schema):
        from gene_annotation_episode.decision_context import state_frame
        from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
        from tests.test_homer_motif_saved_workflow import _encode
        context = plain(context)
        if context.get("feedback"):
            raise RuntimeError("unexpected_retained_protease_feedback:" + json.dumps(context["feedback"], sort_keys=True))
        row = self.store.db.execute("SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (self.proof["run_id"], episode_id)).fetchone()
        grain = json.loads(row["path"])[-1][0]
        turn = self.store.db.execute("SELECT count(*)+1 FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND response IS NOT NULL", (self.proof["run_id"], episode_id)).fetchone()[0]
        assert role == "REASONING" and context["goal"]["objective"] == _PROTEASE_NATIVE_QUESTION
        wire, wire_instructions = self.connection._presentation(episode_id, role, instructions,
            state_frame(context, self.states.get(episode_id)))
        self.states[episode_id] = deepcopy(context)
        assert wire.startswith("TASK\n") and "\n\nSTEERING\n" in wire and _PROTEASE_NATIVE_QUESTION in wire
        call = dict(episode_id=episode_id, grain=grain, turn=turn, context=context, instructions=plain(instructions),
            schema=deepcopy(schema), wire=wire, wire_instructions=plain(wire_instructions),
            wire_sha256=hashlib.sha256(wire.encode()).hexdigest())
        self.proof["calls"].append(call)
        sources = [item["id"] for item in self.proof["publications"]]
        if grain == "annotation":
            assert turn == 1
            selected = dict(kind="episode_child", role="scientific_process", goal=_PROTEASE_NATIVE_QUESTION,
                scope=deepcopy(self.proof["scope"]), purpose=_PROTEASE_NATIVE_QUESTION,
                schema_json=json.dumps(_protease_native_form()), initial_report_json="{}",
                assignment=dict(selection=dict(version="scientific_process_selection_v3",
                    evidence_axis=self.library.reference("A105"), thought_pattern=self.library.reference("P14"),
                    child_tool_info=[{key: item[key] for key in ("name", "resources")}
                        for item in self.proof["current_selected_tool_infos"]]),
                    evidence_refs=[], constraints={}, context=dict(retained_result_source_refs=sources,
                        qualification="Retained542 evidence; original delivery failed. No new fit or saved calculation.")))
        else:
            assert grain == "scientific_process" and 1 <= turn <= 4
            assert context["requested_form"] == _protease_native_form()
            actual = EpisodeReturnRecords(self.store, self.proof["run_id"], failure_prefix="retained_protease_").context(episode_id)
            known = set(self.workflow.receipts.known(episode_id))
            if turn == 1:
                assert not known.intersection(sources)
                for reference in sources:
                    denied = self.workflow.services.read_received_molecular_input(actual, reference, "source", source_metadata_only=True)
                    assert denied["failure"] is not None
                self.proof["sources_denied_before_query"] = True
                # The provider schema represents omitted optional query fields
                # as null; the ordinary decoder restores the refs-only call.
                selected = dict(kind="tool", tool="state.query", arguments=dict(refs=sources,
                    kind=None, offset=None, limit=None, current_only=None, references=None))
            else:
                assert set(sources) <= known
                receipts = [dict(row) for row in self.store.db.execute("SELECT record_ref,receipt_kind,source_index "
                    "FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND record_ref IN (?,?) ORDER BY record_ref",
                    (self.proof["run_id"], episode_id, *sources))]
                assert len(receipts) == 2 and all(item["receipt_kind"] == "own_action" and item["source_index"] == 0 for item in receipts)
                self.proof["source_metadata_admission"] = receipts
                if turn == 2:
                    assert context["last_local_outcome"]["result"]["records"] == self.proof["publications"]
                    private_refs = {reference for source in self.proof["publications"] for reference in (
                        source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
                    assert all(reference not in wire for reference in private_refs)
                    assert all(reference in wire for reference in sources)
                    assert all(reference in wire for source in self.proof["publications"]
                        for reference in source["parent_source_refs"])
                    assert all(source["version"] not in wire and source["retrieved_at"] not in wire
                        for source in self.proof["publications"])
                    self.proof["source_metadata_wire"] = dict(private_file_addresses_hidden=True,
                        callable_sources_preserved=sources, stored_source_records_unchanged=True,
                        internal_version_and_retrieval_time_hidden=True, wire_sha256=call["wire_sha256"])
                else:
                    assert context["last_local_outcome"]["result"] == self.expected[turn - 3]
                    assert "Selected molecular result" in wire and "complete_supplied_curve_population" in wire
                value = self.expected[turn - 2]
                selected = dict(kind="tool", tool=TOOL, arguments=dict(mode="read_stored",
                    result_ref=value["source_ref"], rows=deepcopy(value["selection"]["rows"])))
        answer = _encode(dict(selection=selected, report_update={}), schema)
        if grain == "scientific_process":
            if turn == 1:
                assert answer["selection"]["arguments"] == selected["arguments"]
            else:
                assert type(answer["selection"]["arguments"]) is str
                assert json.loads(answer["selection"]["arguments"]) == selected["arguments"]
        call["response"] = deepcopy(answer)
        _protease_native_checkpoint(self.store, self.proof, self.output)
        return answer

    async def release(self, episode_id):
        self.proof["provider_cleanup_callbacks"].append(episode_id)


def _protease_retained_native_values(store, registry, workflow, context, original, expected):
    """Authenticate numerical evidence without native or assay/capture/software reads."""
    with pytest.raises(ContractError, match="^execution_owner_unavailable$"):
        registry.execution_owner_for(original["run_id"])
    publications = [host.read_protease_kinetics_publication(registry, context,
        workflow.services.read_received_molecular_input, source["id"], require_numeric=True)
        for source in original["publications"]]
    native_publication, saved_publication = publications
    native_control, saved_control = [item["control"] for item in publications]
    assert native_control["intent"]["request"]["mode"] == "native"
    assert saved_control["intent"]["request"]["mode"] == "saved_sheet"
    assert saved_control["intent"]["selected_resource"] is None
    saved_capture = saved_control["files"]["capture"]
    assert saved_capture == dict(state="producer_absent", file=None, observed_identity=None, failure=None,
        declared=dict(state="absent", relative_path="capture.json", sha256=None, size_bytes=None, format="json"))
    assert expected[1]["file_states"]["capture"] == "producer_absent"
    saved_declaration = saved_control["worker"]["declaration"]
    assert saved_declaration["mode"] == "saved_sheet" and saved_declaration["native_outcome"] is None
    assert saved_declaration["native_call_state"] == saved_declaration["native_output_completion"] == (
        saved_declaration["observer_state"]) == "not_requested"
    assert saved_declaration["files"]["capture"] == saved_capture["declared"]
    assert native_publication["sheet"] == saved_publication["sheet"]
    assert native_publication["components"] == saved_publication["components"]
    assert all(native_control["files"][role]["file"] == saved_control["files"][role]["file"] for role in ("sheet", "components"))
    sheet, components = native_publication["sheet"], native_publication["components"]
    assert sheet["measurements"] == original["input_document"]["measurements"]
    assert sheet["assay_context"] == original["input_document"]["assay_context"]
    capture = sheet["native_observation"]
    assert capture["failure"] is None and capture["native_call_state"] == "returned"
    assert capture["native_record"]["outcome"] == "completed"
    observer = capture["observer"]
    assert observer["selected_call_count"] == observer["selected_terminal_event_count"] == 1
    assert observer["state"] == "captured" and observer["profile_restored"] is True
    assert observer["failures"] == capture["verification_failures"] == []
    receipt = capture["execution_receipt"]
    assert receipt["module_load"]["source_file"]["sha256"] == scientific.SOURCE_FILE_SHA256
    assert receipt["observed_callable"]["sha256"] == scientific.SOURCE_FUNCTION_SHA256
    assert {item["module_name"] for item in receipt["libraries"]} == {"numpy", "scipy", "matplotlib"}
    assert all(item["module_version"] == item["distribution_version"] and item["distribution_version"] for item in receipt["libraries"])
    parameter_array, covariance_array = observer["locals"]["params"], observer["locals"]["covariance"]
    assert {key: value for key, value in parameter_array.items() if key != "values"} == dict(
        type="ndarray", dtype="float64", shape=[2])
    assert {key: value for key, value in covariance_array.items() if key != "values"} == dict(
        type="ndarray", dtype="float64", shape=[2, 2])
    parameters, matrix = parameter_array["values"], covariance_array["values"]
    assert len(parameters) == len(matrix) == 2 and all(len(row) == 2 for row in matrix) and matrix[0][1] != 0
    assert components["fit_components"]["parameter_order"] == ["vmax", "km"]
    assert [components["fit_components"][name]["value"] for name in ("vmax", "km")] == parameters
    assert components["fit_components"]["covariance"] == matrix
    assessment = components["fit_components"]["covariance_assessment"]
    assert matrix[0][1] != matrix[1][0] and assessment["native_symmetry"] == "asymmetric"
    assert assessment["statistical_covariance_validity"] == "unestablished"
    assert assessment["propagation_basis"] == "symmetric_bilinear_part_of_observed_native_matrix"
    assert components["fit_components"]["residual_degrees_of_freedom"] == 2
    assert [sheet["population"][name] for name in ("time_point_count", "substrate_count", "supplied_curve_count",
        "requested_initial_point_count", "actual_initial_point_count")] == [5, 4, 4, 5, 5]
    assert components["population"] == sheet["population"] and components["function_probability"] is None
    values = expected[2]["values"]
    assert values["context"] == expected[0]["values"]["context"] == expected[1]["values"]["context"]
    assert values["context"]["covariance"]["raw_matrix"]["value"] == matrix
    assert values["context"]["parameters"]["vmax"]["unit"]["value"] == "RFU/s"
    assert values["context"]["assay"]["value"] == original["input_document"]["assay_context"]
    assert values["context"]["method"]["native_unit_claims"]["value"] == scientific.SOURCE_METHOD["native_unit_claims"]
    assert values["context"]["qualifications"]["value"] == scientific.QUALIFICATIONS
    covariance = [row["value"] for row in values["rows"] if row["row_id"]["kind"] == "protease_covariance"]
    assert covariance == [matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]]
    for row in values["rows"]:
        if row["row_id"]["kind"] == "protease_quantity":
            quantity = row["row_id"]["quantity"]
            item = components["physical_components"][quantity]
            field = item[row["field"]] if row["field"] == "value" else item["uncertainty"][row["field"]]
            assert row["value"] == field
            assert [cell["kind"] for cell in row["denominators"]][:3] == ["calibration_response", "enzyme_concentration", "product_per_cleavage"]
            assert [cell["value"] for cell in row["denominators"]][:3] == [2, .5, 1]
            assert len(row["denominators"]) == (4 if quantity == "catalytic_efficiency" else 3)
            if quantity == "catalytic_efficiency":
                assert row["denominators"][3]["kind"] == "denominator"
                assert row["denominators"][3]["value"] == parameters[1]
    for quantity in stored.QUANTITIES:
        assert values["context"]["physical"][quantity]["uncertainty"]["total_uncertainty"]["value_state"] == "stored_null"
    invocation, input = native_control["invocation"], native_control["intent"]["input"]
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    producer = EpisodeReturnRecords(store, original["run_id"], failure_prefix="retained_protease_").context(invocation["episode_id"])
    directory = Path(native_control["worker"]["selection"]["cwd"])
    assert host._check_input(registry, producer, native_control["arguments"], invocation, input, producer_directory=directory) == input
    for change in ("frozen_path", "producer_key", "relative_directory"):
        changed, changed_invocation, changed_directory = deepcopy(input), deepcopy(invocation), directory
        if change == "frozen_path": changed["frozen"]["path"] = str(directory.parent / "different-input.json")
        elif change == "producer_key": changed_invocation["operation_key"] = invocation["operation_key"] + "0"
        else: changed_directory = Path("cache") / "molecular-measurements" / directory.parent.name / "worker"
        with pytest.raises(ContractError, match="^protease_kinetics_(input_admission_conflict|worker_directory_conflict)$"):
            host._check_input(registry, producer, native_control["arguments"], changed_invocation, changed,
                producer_directory=changed_directory)
    return dict(original_native_selected_call_count=1, new_native_calls=0, new_saved_calculations=0,
        saved_capture_file_state="producer_absent", saved_native_call_state="not_requested",
        original_parameter_array=deepcopy(parameter_array), original_covariance_array=deepcopy(covariance_array),
        full_parameter_covariance_preserved=True, sheet_and_components_equal=True,
        old_input_paths_preserved=True, historical_path_negative_controls=3,
        native_observation_from_authenticated_sheet=True, native_capture_body_opened=False,
        original_execution_owner_required=False, parameters=parameters, covariance=matrix,
        covariance_assessment=assessment, original_files=deepcopy(native_control["files"]),
        derived_files=deepcopy(saved_control["files"]))


def test_retained542_protease_current_admission_typed_receiver_and_closed_replay(tmp_path, monkeypatch):
    import os
    import shutil
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    from tests.test_homer_motif_saved_workflow import _archive, _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history, _sqlite_pins
    if not os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_RETAINED_PROOF"):
        pytest.skip("requires the explicitly pinned terminal542 retained ordinary protease evidence")
    assert os.environ.get("HMMER529_ATTEMPT"), "requires the selected bounded retained-data runtime"
    proof_path, original = _protease_retained_load()
    original_directory = Path(original["case_directory"])
    original_inventory = _files(original_directory)
    case = tmp_path / "retained542-protease-current-receiver"
    case.mkdir()
    shutil.copytree(original["store_directory"], case / "store", copy_function=shutil.copy2, symlinks=True)
    shutil.copytree(original["workflow_directory"], case / "original-run", copy_function=shutil.copy2, symlinks=True)
    assert _files(case / "store") == _files(Path(original["store_directory"]))
    assert _files(case / "original-run") == _files(Path(original["workflow_directory"]))
    output = case / "PROTEASE_RETAINED542_RECEIVER.json"
    proof = dict(version="ordinary_protease_retained542_receiver_v1", run_id="retained542-protease-current-receiver",
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        question=_PROTEASE_NATIVE_QUESTION, original_proof=_pin(proof_path), original_run_id=original["run_id"],
        original_delivery_failed=True, original_closed_replay_verified=False,
        phase="copied", calls=[], body_reads=[], workers=[], provider_cleanup_callbacks=[],
        scope=deepcopy(original["scope"]), factory=deepcopy(original["factory"]), initial_known_record_refs=[],
        publications=deepcopy(original["publications"]), passed=False,
        qualification="New current metadata admission and literal reads of authentic542 Sources. Original failed typed delivery remains failed; no fit or saved calculation repeats.")
    _write(output, proof)
    original_get = Store.get_artifact
    try:
        with Store(case / "store") as store:
            expected, retained = _protease_retained_original(store, original)
            original_rows, original_artifacts = _tables(store), _files(store.path / "artifacts")
            sources_before = deepcopy(store.list("source"))
            allowed, controls = set(), []
            for source in original["publications"]:
                allowed.update((source["artifact_ref"], source["request_ref"]))
                raw = original_get(store, source["request_ref"])
                assert "artifact_" + hashlib.sha256(raw).hexdigest() == source["request_ref"]
                control = json.loads(raw)
                controls.append(control)
                allowed.update(control["files"][role]["file"]["artifact_ref"] for role in ("sheet", "components"))
            private = {reference for source in original["publications"]
                for reference in (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
            forbidden_bodies = {original["input_file"]["artifact_ref"], *(control["files"][role]["file"]["artifact_ref"]
                for control in controls for role in ("capture", "native_results", "native_plot")
                if control["files"][role]["file"] is not None)}
            assert allowed.isdisjoint(forbidden_bodies)
            def retained_only(current, reference):
                assert reference in allowed and reference not in forbidden_bodies, "forbidden original/input/capture/software body: " + reference
                proof["body_reads"].append(reference)
                return original_get(current, reference)
            with monkeypatch.context() as guarded:
                for module, names in ((native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release")),
                        (native, ("execute_molecular_sequence_request", "_manifest", "_exact_file")),
                        (driver, ("run_molecular_sequence_driver",)), (common, ("run_owned_molecular_worker",))):
                    for name in names:
                        guarded.setattr(module, name, _forbidden)
                guarded.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
                guarded.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                guarded.setattr(Store, "get_artifact", retained_only)
                guarded.setattr("socket.create_connection", _forbidden)
                factory = ExecutionServiceFactory.from_record(proof["factory"])
                configured = ToolRegistry(store, job_limits=deepcopy(POLICY))
                factory.configure_tool_registry(configured)
                proof["selected_tool_contract"] = deepcopy(configured.catalog()[TOOL])
                proof["scientific_binding"] = prepare_scientific_binding(run_directory=case / "run",
                    source_directory=Path(__file__).resolve().parents[1] / _PROTEASE_PUBLICATION,
                    tool_catalog=configured.catalog(), child_roles=["scientific_process"])
                selected_tools = ScientificToolLibrary(case / "run/scientific-tool-library")
                proof["current_selected_tool_infos"] = selected_tools.resolve_tool_info(
                    [dict(name=name, resources="local") for name in ("state.query", TOOL)], configured.catalog())
                assert [(item["name"], item["resources"]) for item in proof["current_selected_tool_infos"]] == [
                    ("state.query", "local"), (TOOL, "local")]
                from gene_annotation_episode.domain import validate_schema
                validate_schema(dict(refs=[source["id"] for source in original["publications"]]),
                    configured.catalog()["state.query"]["input_schema"])
                library = ScientificProcessLibrary(case / "run/scientific-process-library")
                provider = _ProteaseRetainedChoices(store, library, proof, output, expected)
                workflow, registry = _protease_native_assemble(store, case / "run", proof, provider)
                provider.workflow = workflow
                guarded.setattr(registry.clients, "_http", _forbidden)
                execute = registry.execute_async
                async def literal_action(name, arguments, **kwargs):
                    assert name == "state.query" and arguments == dict(refs=[source["id"] for source in original["publications"]]) or (
                        name == TOOL and arguments["mode"] == "read_stored")
                    return await execute(name, arguments, **kwargs)
                guarded.setattr(registry, "execute_async", literal_action)
                root = workflow.build("annotation", "root", _PROTEASE_NATIVE_QUESTION, proof["scope"])
                record = asyncio.run(root.run_async(workflow.context))
                proof.update(phase="current_workflow_returned", archive=_archive_value(record))
                _protease_native_checkpoint(store, proof, output)
                _protease_retained_verify_completed(store, workflow, registry, proof, original, expected, retained,
                    case, output, original_rows, original_artifacts, sources_before, monkeypatch, guarded, root=root, record=record)
    except BaseException as error:
        proof["passed"] = False
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["original_inventory_before"] = original_inventory
        proof["original_inventory_after"] = _files(original_directory)
        proof["original_files_and_modes_unchanged"] = proof["original_inventory_after"] == original_inventory
        proof["sqlite_pins"] = _sqlite_pins(case / "store")
        _write(output, proof)
        assert proof["original_files_and_modes_unchanged"]



def _protease_retained_verify_completed(store, workflow, registry, proof, original, expected, retained,
        case, output, original_rows, original_artifacts, sources_before, monkeypatch, guarded, *, root=None, record=None):
    """Authenticate completed records and replay them; never acquire another result."""
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
    from tests.test_homer_motif_saved_workflow import _archive, _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history
    private = {reference for source in original["publications"]
        for reference in (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
    history = _history(store, proof["run_id"])
    episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
    assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
    assert all(len(history[name]) == 5 for name in ("runtime_actions", "runtime_observations", "runtime_model_calls"))
    assert len(history["runtime_forms"]) == len(history["runtime_report_attempts"]) == 1
    assert len(history["tool_operations"]) == 4 and len(proof["calls"]) == 5
    parent, science = [EpisodeReturnRecords(store, proof["run_id"], failure_prefix="retained_protease_").context(row["episode_id"]) for row in episodes]
    for context in (parent, science):
        EpisodeReturnRecords(store, proof["run_id"], failure_prefix="retained_protease_").authenticate(context)
    assert workflow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == expected
    assert workflow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == expected
    assert workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == expected
    frozen, = history["runtime_forms"]
    attempt, = history["runtime_report_attempts"]
    assert json.loads(frozen["form"]) == json.loads(attempt["form"]) == dict(measurements=expected)
    assert json.loads(frozen["facts"])[contracts.FACT_SOURCE] == expected and attempt["failure"] is None
    operations = _protease_native_operations(store, proof["run_id"])
    assert len(operations) == 3 and all(json.loads(row["arguments"])["mode"] == "read_stored" for row in operations)
    for operation, value in zip(operations, expected):
        outcome = json.loads(operation["result"])
        assert outcome["status"] == "completed" and outcome["result"] == value
        assert outcome["record_refs"] == [value["source_ref"]] and outcome["changed_record_refs"] == []
    for context in (parent, science):
        known = set(workflow.receipts.known(context.episode_id))
        assert {item["id"] for item in original["publications"]} <= known and private.isdisjoint(known)
        resolver = workflow.resolver(plain(context.scope), context=context)
        for reference in private:
            assert resolver(reference, "artifact") is False
            denied, path = workflow.services.read_received_molecular_input(context, reference, "artifact", file_format="json")
            assert path is None and denied["failure"] is not None
    proof["retained_native_values"] = _protease_retained_native_values(store, registry, workflow, science, original, expected)
    proof["delivery"] = dict(returned=dict(measurements=expected),
        episode_ids=[parent.episode_id, science.episode_id],
        archives=[_archive(row, case / "run") for row in episodes], same_original_three_groups=True)
    assert (root is None) == (record is None)
    if root is not None:
        proof["final_result"] = _archive_value(asyncio.run(root.build_result(record)))
        assert proof["final_result"] == dict(credit=0, pending_handles=[])
    assert store.list("source") == sources_before and _files(store.path / "artifacts") == original_artifacts
    proof["phase"] = "current_typed_return_verified"
    _protease_native_checkpoint(store, proof, output)
    proof["replay"] = _protease_native_closed_replay(store, case / "run", proof, monkeypatch)
    if root is None:
        proof["final_result"] = deepcopy(proof["replay"]["final"])
    assert proof["final_result"] == dict(credit=0, pending_handles=[])
    # Successful-delivery fast replay is deliberately unavailable
    # for the old failed attempt; authenticate that literal denial.
    old_before, old_files = _tables(store), _files(case / "original-run")
    old_provider = _ProteaseNoNewDecisions()
    with guarded.context() as no_old_work:
        no_old_work.setattr(Store, "get_artifact", _forbidden)
        no_old_work.setattr(ToolRegistry, "execute_async", _forbidden)
        old_flow, old_registry = _protease_native_assemble(store, case / "original-run", original, old_provider)
        no_old_work.setattr(old_registry.clients, "_http", _forbidden)
        old_root = old_flow.build("annotation", "root", _PROTEASE_NATIVE_QUESTION, original["scope"])
        old_action = json.loads(next(row["action"] for row in retained["history"]["runtime_actions"]
            if row["episode_id"] == retained["episodes"][0]["episode_id"]))
        with pytest.raises(ValueError, match="^closed_commission_successful_return_required$"):
            old_flow._closed_child_commission(old_root.source, old_action, 0)
    assert _tables(store) == old_before and _files(case / "original-run") == old_files
    assert _history(store, original["run_id"]) == retained["history"]
    after = _tables(store)
    assert all(name in after and set(rows) <= set(after[name]) for name, rows in original_rows.items())
    assert store.list("source") == sources_before and _files(store.path / "artifacts") == original_artifacts
    proof.update(original_closed_commission_denial="closed_commission_successful_return_required",
        original_closed_replay_verified=False, original_rows_preserved=True,
        original_no_new_rows=True, no_new_sources=True, no_new_native_calls=True,
        no_new_saved_calculations=True, new_typed_return_verified=True,
        new_closed_replay_verified=True, passed=True, phase="verified")


def test_retained545_protease_completed_delivery_postcheck_without_new_actions(tmp_path, monkeypatch):
    import os
    import shutil
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history, _sqlite_pins
    configured = os.environ.get("HMMER_NATIVE_ORACLE_PROTEASE_COMPLETED_RECEIVER_PROOF")
    if not configured:
        pytest.skip("requires the explicitly pinned completed545 Workflow and its preserved failed verifier")
    assert os.environ.get("HMMER529_ATTEMPT"), "requires the selected bounded retained-data runtime"
    original_path, original = _protease_retained_load()
    path = Path(configured)
    assert path.is_absolute() and not path.is_symlink()
    raw = path.read_bytes()
    assert os.environ["HMMER_NATIVE_ORACLE_PROTEASE_COMPLETED_RECEIVER_PROOF_SHA256"] == (
        "f37c6209c829c98267bfe99dc9acea686fcbeaee78f8300c63e92f4156c5e1c7")
    assert len(raw) == 48261014 and hashlib.sha256(raw).hexdigest() == (
        "f37c6209c829c98267bfe99dc9acea686fcbeaee78f8300c63e92f4156c5e1c7")
    completed = json.loads(raw)
    assert completed["version"] == "ordinary_protease_retained542_receiver_v1"
    assert completed["phase"] == "current_workflow_returned" and completed["passed"] is False
    assert completed["failure"] == dict(exception_type="TypeError",
        message="EpisodeReturnRecords.__init__() missing 1 required keyword-only argument: 'failure_prefix'")
    assert completed["workers"] == [] and completed["original_files_and_modes_unchanged"] is True
    assert completed["original_proof"] == _pin(original_path)
    assert completed["run_id"] == "retained542-protease-current-receiver"
    assert path.parent == Path(completed["case_directory"])
    database = Path(completed["store_directory"]) / "state.sqlite3"
    assert sorted(item.name for item in database.parent.glob("state.sqlite3*")) == ["state.sqlite3"]
    expected_pin = dict(name="state.sqlite3", sha256="a6d9c4151887092ef784582914119674975e0ef6e4550830cd8fe3a3676b398c", size_bytes=42029056)
    assert completed["sqlite_pins"] == [expected_pin]
    assert _pin(database) == dict(path=str(database), **{key: value for key, value in expected_pin.items() if key != "name"})
    inventories = {str(directory): _files(directory) for directory in (path.parent, Path(original["case_directory"]))}
    case = tmp_path / "retained545-protease-postcheck"
    shutil.copytree(path.parent, case, copy_function=shutil.copy2, symlinks=True)
    assert _files(case) == inventories[str(path.parent)]
    assert _pin(case / path.name)["sha256"] == hashlib.sha256(raw).hexdigest()
    output = case / "PROTEASE_RETAINED545_POSTCHECK.json"
    proof = deepcopy(completed)
    proof.update(version="ordinary_protease_retained545_postcheck_v1", phase="copied_completed545",
        case_directory=str(case), store_directory=str(case / "store"), workflow_directory=str(case / "run"),
        completed545_proof=_pin(path), recorded_completed545_test_failure=deepcopy(completed["failure"]),
        recorded_completed545_test_passed=False, new_workflow_executed=False,
        new_provider_decisions=0, new_tool_actions=0, body_reads=[], provider_cleanup_callbacks=[], passed=False,
        qualification="Authenticate and replay the actual completed545 delivery; its original failed verifier remains failed. No new decisions, actions, fit or saved calculation.")
    proof.pop("failure")
    _write(output, proof)
    original_get = Store.get_artifact
    try:
        with Store(case / "store") as store:
            assert _history(store, proof["run_id"]) == completed["history"]
            expected, retained = _protease_retained_original(store, original)
            original_rows, original_artifacts = _tables(store), _files(store.path / "artifacts")
            sources_before = deepcopy(store.list("source"))
            before_run, before_old_run = _files(case / "run"), _files(case / "original-run")
            allowed, forbidden_bodies = set(), {original["input_file"]["artifact_ref"]}
            for source in original["publications"]:
                allowed.update((source["artifact_ref"], source["request_ref"]))
                control_raw = original_get(store, source["request_ref"])
                assert "artifact_" + hashlib.sha256(control_raw).hexdigest() == source["request_ref"]
                control = json.loads(control_raw)
                allowed.update(control["files"][role]["file"]["artifact_ref"] for role in ("sheet", "components"))
                forbidden_bodies.update(control["files"][role]["file"]["artifact_ref"]
                    for role in ("capture", "native_results", "native_plot") if control["files"][role]["file"] is not None)
            assert allowed.isdisjoint(forbidden_bodies)
            def retained_only(current, reference):
                assert reference in allowed and reference not in forbidden_bodies
                proof["body_reads"].append(reference)
                return original_get(current, reference)
            with monkeypatch.context() as guarded:
                for module, names in ((native_lifecycle, ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release")),
                        (native, ("execute_molecular_sequence_request", "_manifest", "_exact_file")),
                        (driver, ("run_molecular_sequence_driver",)), (common, ("run_owned_molecular_worker",))):
                    for name in names:
                        guarded.setattr(module, name, _forbidden)
                guarded.setattr(scientific, "calculate_protease_kinetics_components", _forbidden)
                guarded.setattr(ToolRegistry, "execute_async", _forbidden)
                guarded.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                guarded.setattr(Store, "get_artifact", retained_only)
                guarded.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
                guarded.setattr("socket.create_connection", _forbidden)
                provider = _ProteaseNoNewDecisions()
                # The real original descriptor/library/callable records enter
                # the ordinary constructor unchanged. Compatibility remains a
                # production decision; no actual-as-record override is used.
                workflow, registry = _protease_native_assemble(store, case / "run", proof, provider)
                _protease_retained_verify_completed(store, workflow, registry, proof, original, expected, retained,
                    case, output, original_rows, original_artifacts, sources_before, monkeypatch, guarded)
                assert _tables(store) == original_rows
                assert _history(store, proof["run_id"]) == completed["history"]
                assert _files(case / "run") == before_run and _files(case / "original-run") == before_old_run
                proof.update(all_completed545_rows_unchanged=True, all_completed545_archives_and_libraries_unchanged=True,
                    no_new_model_calls=True, no_new_provider_decisions=True, no_new_tool_actions=True,
                    replay_constructor_cleanup_callbacks=provider.cleanup_callbacks)
    except BaseException as error:
        proof["passed"] = False
        proof["failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["original_input_inventories_before"] = inventories
        proof["original_input_inventories_after"] = {directory: _files(Path(directory)) for directory in inventories}
        proof["original542_and545_files_and_modes_unchanged"] = proof["original_input_inventories_after"] == inventories
        proof["sqlite_pins"] = _sqlite_pins(case / "store")
        _write(output, proof)
        assert proof["original542_and545_files_and_modes_unchanged"]
