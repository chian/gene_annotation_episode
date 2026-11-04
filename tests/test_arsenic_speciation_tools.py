"""Ordinary arsenic custody and current Workflow controls over supplied data.

Engineered worker metadata is labelled explicitly. The opt-in worker case uses
the actual bounded calculator worker; neither case operates HPLC-ICP-MS.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import arsenic_speciation_result_contracts as contracts
from gene_annotation_episode import arsenic_speciation_tools as host
from gene_annotation_episode import calibrated_signal_calculations as calculations
from gene_annotation_episode import calibrated_signal_contracts as core
from gene_annotation_episode import calibrated_signal_sheet as inputs
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_calibrated_signal_measurements import supplied_inputs, selection
from tests.test_runtime import ScriptedProvider
from tests.test_vcf_result_workflow import _closed_child, _controller, _single_saved_result_controller, _tables, _zero


POLICY = dict(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"
QUESTION = ("For the supplied calibrated-signal Sheet, return the controlled aliquot and original-sample "
    "concentrations with retained units, association populations, censoring and uncertainty qualifications. "
    "Then calculate the explicitly empty species selection and read that stored result.")


def _forbidden(*args, **kwargs):
    raise AssertionError("ordinary arsenic control attempted forbidden work")


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


def _sheet():
    return inputs.populate_calibrated_signal_sheet(**supplied_inputs())


def _arguments(reference, *, namespace="artifact", mode="calculate", selected=None):
    if mode == "read_stored": return dict(mode=mode, result_ref=reference)
    return dict(mode=mode, **({"input": dict(namespace=namespace, reference=reference)}
        if mode == "calculate" else {"result_ref": reference}), selection=selection() if selected is None else deepcopy(selected))


def _dispatch(value, arguments, index):
    selected = dict(kind="tool", tool=host.TOOL, arguments=deepcopy(arguments))
    asyncio.run(value.caller.source.execute(selected, index))
    row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, index)
    assert json.loads(row["action"]) == selected and row["result"] is not None
    return json.loads(row["result"])


def _engineered_worker(value, monkeypatch):
    """Actual adapter/control files with explicitly fake terminal process facts."""
    observations = {}
    calculate = calculations.calculate_calibrated_signal_components
    def counted(sheet, *, selection):
        value.calculator_calls.append(deepcopy(selection))
        return calculate(sheet, selection=selection)
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", counted)
    async def worker(operation, arguments, *, directory, owned_directory):
        assert not value.store.db.in_transaction and directory == owned_directory
        assert operation == host.WORKER_OPERATION and set(arguments) == {"request"}
        value.worker_calls.append(deepcopy(arguments["request"]))
        output, selected_path = directory / "worker-result.json", directory / "execution-selection.json"
        if selected_path.exists():
            selected = json.loads(selected_path.read_bytes())
            assert selected["request"] == dict(operation=operation, arguments=arguments)
            metadata = json.loads((directory / "native-handle.json").read_bytes())["metadata"]
            return SimpleNamespace(output_path=output, metadata=metadata)
        python = dict(path="/engineering/runtime/bin/python", sha256="0" * 64)
        command = [python["path"], "-m", "gene_annotation_episode.sequence_worker",
            str(directory / "worker-request.json"), str(output)]
        payload = dict(operation=operation, arguments=deepcopy(arguments))
        selected = dict(version="ordinary_molecular_execution_v1", command=command, cwd=str(directory),
            environment={"ENGINEERING_ONLY": "no process, instrument or native wrapper"}, policy=deepcopy(POLICY),
            request=payload, python=python, implementation_files=[])
        _write(selected_path, selected); _write(directory / "worker-request.json", payload)
        paths = {name: str(directory / filename) for name, filename in dict(
            request="job-request.json", ready="ready", release="release", result="job-result.json").items()}
        native_request = dict(command=command, cwd=str(directory), file_bytes=POLICY["scratch_bytes"],
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None,
            env=selected["environment"])
        _write(Path(paths["request"]), native_request)
        metadata = dict(policy=deepcopy(POLICY), native_returncode=value.returncode)
        handle = dict(version=native_lifecycle.VERSION, command=command, cwd=str(directory),
            stdout=str(directory / "stdout"), stderr=str(directory / "stderr"), paths=paths,
            request_sha256=hashlib.sha256(Path(paths["request"]).read_bytes()).hexdigest(), metadata=metadata)
        _write(directory / "native-handle.json", handle)
        observations[str(directory / "native-handle.json")] = dict(state="returned", terminal=True,
            quiescent=True, metadata=deepcopy(metadata))
        if not value.missing_output:
            _write(output, host.run_arsenic_speciation_tool_request(arguments["request"]))
        return SimpleNamespace(output_path=output, metadata=metadata)
    monkeypatch.setattr(value.registry, "_sequence_worker_async", worker)
    monkeypatch.setattr(native_lifecycle, "status", lambda handle: deepcopy(observations[str(handle.path)]))


@contextmanager
def _owned(tmp_path, monkeypatch, *, namespace="artifact", document=None, provider=None, real_worker=False):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACGT", molecule="dna")
        supplied = store.register_material(data=canonical(_sheet() if document is None else document).encode(),
            name="supplied calibrated-signal engineering Sheet", use="evidence")
        source = store.get(supplied["source_ref"])
        reference = source["id"] if namespace == "source" else source["artifact_ref"]
        registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
        workspace = tmp_path / "workspace"; workspace.mkdir()
        factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))},
            {}, 2, .25, .5)
        factory.configure_tool_registry(registry)
        application = factory(store, run_id="arsenic-engineering", directory=tmp_path / "run", tool_registry=registry)
        provider = ScriptedProvider([]) if provider is None else provider
        flow = Workflow(store, registry, provider, tmp_path / "run", "arsenic-engineering", _single_saved_result_controller, _zero,
            project_child_credit=_zero, root_role="improvement", episode_binding_descriptors=application.episode_binding_descriptors,
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
            episode_record_receipts=True, initial_known_record_refs=[reference])
        caller = flow.build("improvement", "caller", QUESTION, store.validate_scope())
        value = SimpleNamespace(store=store, registry=registry, flow=flow, caller=caller, source=source,
            reference=reference, namespace=namespace, input_ref=source["artifact_ref"], factory=factory,
            worker_calls=[], calculator_calls=[], missing_output=False, returncode=0)
        monkeypatch.setattr(registry.clients, "_http", _forbidden)
        monkeypatch.setattr("socket.create_connection", _forbidden)
        if not real_worker:
            for name in ("prepare_job", "resume_start", "wait_job", "collect", "cancel", "release"):
                monkeypatch.setattr(native_lifecycle, name, _forbidden)
            _engineered_worker(value, monkeypatch)
        yield value


def test_store_free_worker_calls_the_existing_calculator_once_and_retains_exact_inputs(monkeypatch):
    sheet = _sheet(); raw = canonical(sheet).encode(); digest_value = hashlib.sha256(raw).hexdigest()
    request = dict(version=host.REQUEST_VERSION, sheet=sheet, selection=selection(),
        input_file=dict(artifact_ref="artifact_" + digest_value, sha256=digest_value, size_bytes=len(raw), format="json"))
    calls, calculate = [], calculations.calculate_calibrated_signal_components
    def counted(sheet, *, selection): calls.append(deepcopy(selection)); return calculate(sheet, selection=selection)
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", counted)
    monkeypatch.setattr(Path, "read_bytes", _forbidden)
    result = host.run_arsenic_speciation_tool_request(request)
    assert calls == [selection()] and result["sheet"] == sheet and result["request"] == request
    assert result["components"]["rows"][0]["aliquot_concentration"]["value"] == 10
    assert result["calculation"] == dict(state="completed", call_count=1, native_invocation="not_requested")
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
    assert host.validate_arsenic_speciation_worker_result(result, request=request) == result


def test_raised_calculation_is_unknown_count_and_does_not_publish_raw_error_text(monkeypatch):
    sheet = _sheet(); raw = canonical(sheet).encode(); sha = hashlib.sha256(raw).hexdigest()
    request = dict(version=host.REQUEST_VERSION, sheet=sheet, selection=selection(),
        input_file=dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format="json"))
    def fail(*args, **kwargs): raise RuntimeError("/private/engineering/diagnostic")
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", fail)
    result = host.run_arsenic_speciation_tool_request(request)
    assert result["components"] is None and result["calculation"]["call_count"] is None
    assert result["calculation"]["state"] == "calculation_failed"
    assert result["error"]["message"] == "/private/engineering/diagnostic"
    assert "/private/engineering/diagnostic" not in json.dumps(result["failures"])


@pytest.mark.parametrize("namespace", ["artifact", "source"])
def test_actual_input_receipts_and_file4_bind_an_ordinary_action_without_manual_grants(tmp_path, monkeypatch, namespace):
    with _owned(tmp_path, monkeypatch, namespace=namespace) as value:
        before = set(value.flow.receipts.known(value.caller.source.episode_id))
        assert value.reference in before and value.input_ref in before
        outcome = _dispatch(value, _arguments(value.reference, namespace=namespace), 0)
        assert outcome["status"] == "completed" and len(value.calculator_calls) == 1
        public = outcome["result"]; source = value.store.get(public["source_ref"])
        control = json.loads(value.store.get_artifact(source["request_ref"]))
        received = control["intent"]["input"]["evidence"]["received_input"]
        assert received["selection"] == dict(namespace=namespace, reference=value.reference)
        assert received["input"]["file"]["artifact_ref"] == value.input_ref
        assert control["intent"]["input"]["protected_input_artifact_refs"] == [value.input_ref]
        assert control["files"]["sheet"]["file"]["artifact_ref"] == value.input_ref
        assert value.input_ref not in source["auxiliary_artifact_refs"]
        assert source["parent_source_refs"] == ([value.reference] if namespace == "source" else [])
        assert public["values"]["rows"][0]["original_sample_concentration"]["value"] == 20
        assert value.input_ref in set(value.flow.receipts.known(value.caller.source.episode_id))


def test_saved_selection_is_new_source_and_literal_read_opens_only_primary_packet(tmp_path, monkeypatch):
    with _owned(tmp_path, monkeypatch) as value:
        first = _dispatch(value, _arguments(value.reference), 0)
        empty = selection(species=())
        saved = _dispatch(value, _arguments(first["result"]["source_ref"], mode="calculate_saved", selected=empty), 1)
        assert saved["status"] == "completed" and saved["result"]["source_ref"] != first["result"]["source_ref"]
        assert saved["result"]["values"]["rows"] == [] and saved["result"]["selection"] == empty
        assert len(value.calculator_calls) == 2
        source = value.store.get(saved["result"]["source_ref"]); primary = source["artifact_ref"]
        get = Store.get_artifact; reads = []
        def only_primary(current, ref):
            reads.append(ref); assert ref == primary
            return get(current, ref)
        monkeypatch.setattr(Store, "get_artifact", only_primary)
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
        monkeypatch.setattr(calculations, "validate_calibrated_signal_components", _forbidden)
        monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
        read = _dispatch(value, _arguments(source["id"], mode="read_stored"), 2)
        assert read["result"] == saved["result"] and read["changed_record_refs"] == []
        assert reads and set(reads) == {primary}


def test_unreceived_file_is_denied_before_bytes_or_worker(tmp_path, monkeypatch):
    with _owned(tmp_path, monkeypatch) as value:
        # A separate body is needed; the original supplied bytes already have a
        # legitimate grant and a same-hash alias would not be unreceived.
        unreceived = value.store.artifact(json.dumps(_sheet(), indent=3), "application/json")
        assert unreceived not in set(value.flow.receipts.known(value.caller.source.episode_id))
        monkeypatch.setattr(Store, "get_artifact", _forbidden)
        monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
        with pytest.raises(ActionFailure): _dispatch(value, _arguments(unreceived), 0)
        row = value.flow.journal.row("runtime_actions", value.caller.source.episode_id, 0)
        assert json.loads(row["result"])["record_refs"] == []
        assert value.calculator_calls == []


@pytest.mark.parametrize("kind", ["partial_roles", "unknown_selection", "missing_worker_output"])
def test_incomplete_evidence_preserves_context_without_claiming_zero_measurements(tmp_path, monkeypatch, kind):
    document = _sheet()
    if kind == "partial_roles": document["calibrations"] = None
    with _owned(tmp_path, monkeypatch, document=document) as value:
        selected = selection(samples=("not-in-sheet",)) if kind == "unknown_selection" else selection()
        value.missing_output = kind == "missing_worker_output"
        outcome = _dispatch(value, _arguments(value.reference, selected=selected), 0)
        assert outcome["status"] == "partial" and outcome["result"]["values"] is None
        context = outcome["result"]["context"]
        assert context["qualifications"] == core.QUALIFICATIONS
        assert context["calculation"]["call_count"] == (None if kind == "missing_worker_output" else 0)
        if kind == "partial_roles": assert context["role_states"]["calibrations"] == "invalid"
        assert "population" not in context
        source = value.store.get(outcome["result"]["source_ref"])
        control = json.loads(value.store.get_artifact(source["request_ref"]))
        missing_state = "producer_unavailable" if kind == "missing_worker_output" else "not_requested"
        assert (control["intent"]["request"] is None) == (kind != "missing_worker_output")
        assert control["files"]["components"] == host.stored.empty_file_state(missing_state)
        assert outcome["result"]["file_states"] == dict(sheet="retained_undeclared", components=missing_state)
        assert context["calculation"]["native_invocation"] == "not_requested"
        assert all(host.stored.validate_file_state(state) == state for state in control["files"].values())


def test_lost_publication_response_recovers_original_output_without_second_calculation(tmp_path, monkeypatch):
    with _owned(tmp_path, monkeypatch) as value:
        save = value.registry._save
        def lost(*args, **kwargs):
            if args[4].get("result") is not None: raise RuntimeError("engineering publication response loss")
            return save(*args, **kwargs)
        arguments = _arguments(value.reference)
        monkeypatch.setattr(value.registry, "_save", lost)
        with pytest.raises(MolecularOperationUnpublished): _dispatch(value, arguments, 0)
        assert len(value.calculator_calls) == 1
        assert value.store.db.execute("SELECT count(*) FROM tool_operations WHERE name=?", (host.TOOL,)).fetchone()[0] == 0
        directory = value.store.path / "cache/molecular-measurements" / digest(f"{value.flow.run_id}:{value.caller.source.episode_id}:0")
        handle = (directory / "worker/native-handle.json").read_bytes()
        monkeypatch.setattr(value.registry, "_save", save)
        value.registry.local_job_policy = LocalJobPolicy(**{**POLICY, "memory_bytes": POLICY["memory_bytes"] // 2})
        get = Store.get_artifact
        def no_original_input(current, reference):
            assert reference != value.input_ref
            return get(current, reference)
        monkeypatch.setattr(Store, "get_artifact", no_original_input)
        recovered = _dispatch(value, arguments, 0)
        assert recovered["status"] == "completed" and len(value.calculator_calls) == 1
        assert (directory / "worker/native-handle.json").read_bytes() == handle


@pytest.mark.parametrize("mode,tamper", [
    ("calculate", "request_sheet"), ("calculate", "all_decoded_observations"),
    ("calculate_saved", "request_sheet"), ("calculate_saved", "alternate_actual_file"),
    ("calculate_saved", "protected_inputs"),
])
def test_pending_input_tampering_rejects_before_worker_without_original_body_read(tmp_path, monkeypatch, mode, tamper):
    """Deliberately corrupt only this engineering action's pending intent."""
    with _owned(tmp_path, monkeypatch) as value:
        reference, index = value.reference, 0
        if mode == "calculate_saved":
            reference = _dispatch(value, _arguments(reference), 0)["result"]["source_ref"]
            index = 1
        arguments = _arguments(reference, mode=mode)
        async def interrupted(*args, **kwargs):
            raise MolecularOperationUnpublished("engineering_before_worker")
        monkeypatch.setattr(value.registry, "_sequence_worker_async", interrupted)
        with pytest.raises(MolecularOperationUnpublished, match="engineering_before_worker"):
            _dispatch(value, arguments, index)
        key = f"{value.flow.run_id}:{value.caller.source.episode_id}:{index}"
        intent_path = value.store.path / "cache/molecular-measurements" / digest(key) / "arsenic-speciation-intent.json"
        intent = json.loads(intent_path.read_bytes())
        original_raw = bytes.fromhex(intent["input"]["raw_hex"])
        assert hashlib.sha256(original_raw).hexdigest() == intent["input"]["file"]["sha256"]
        if tamper == "protected_inputs":
            intent["input"]["protected_input_artifact_refs"] = []
        else:
            changed = deepcopy(intent["input"]["sheet"])
            changed["samples"][0]["measurements"][0]["signal"]["value"] = 99
            intent["input"]["sheet"] = deepcopy(changed)
            intent["request"]["sheet"] = deepcopy(changed)
            if tamper == "all_decoded_observations":
                received = deepcopy(intent["input"]["evidence"]["received_input"])
                received["input"]["content"]["value"] = deepcopy(changed)
                evidence = inputs.read_calibrated_signal_inputs(reference, namespace="artifact",
                    read_input=lambda *args: received)
                intent["input"]["evidence"] = evidence
                intent["input"]["input_state"] = evidence["state"]
                intent["input"]["role_states"] = {name: role["state"] for name, role in evidence["roles"].items()}
            elif tamper == "alternate_actual_file":
                raw = canonical(changed).encode()
                actual = value.store.artifact(raw, "application/json")
                assert actual not in set(value.flow.receipts.known(value.caller.source.episode_id))
                file = dict(artifact_ref=actual, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), format="json")
                intent["input"]["raw_hex"] = raw.hex()
                intent["input"]["file"] = file
                intent["request"]["input_file"] = file
        mode_before = intent_path.stat().st_mode & 0o777
        intent_path.chmod(mode_before | 0o200)
        try: _write(intent_path, intent)
        finally: intent_path.chmod(mode_before)
        before_calls = len(value.calculator_calls)
        before_operations = value.store.db.execute("SELECT count(*) FROM tool_operations WHERE name=?", (host.TOOL,)).fetchone()[0]
        get = Store.get_artifact; reads = []
        def no_original_body(current, ref):
            assert ref != value.input_ref
            reads.append(ref)
            return get(current, ref)
        monkeypatch.setattr(Store, "get_artifact", no_original_body)
        monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
        with pytest.raises(MolecularOperationUnpublished, match="original_action_unpublished"):
            _dispatch(value, arguments, index)
        assert len(value.calculator_calls) == before_calls
        assert value.store.db.execute("SELECT count(*) FROM tool_operations WHERE name=?", (host.TOOL,)).fetchone()[0] == before_operations
        if mode == "calculate": assert reads == []


def _schema():
    return obj(dict(outcomes=contracts.ordinary_arsenic_fact_sources()[contracts.FACT_SOURCE]["report_schema"]))


class _Choices:
    """Actual current Session rendering with explicitly scripted decisions."""
    def __init__(self, store, library, scope, input_ref):
        self.store, self.library, self.scope, self.input_ref = store, library, scope, input_ref
        self.contexts, self.wire = [], []
        self.connection = object.__new__(_SessionConnection)
        self.connection.scientific_prompt_states = {}

    def outcomes(self):
        return [json.loads(row[0]) for row in self.store.db.execute("SELECT result FROM tool_operations WHERE name=? ORDER BY rowid", (host.TOOL,))]

    async def complete(self, episode_id, role, instructions, context, output_schema):
        index = len(self.contexts); assert index < 4
        self.contexts.append(deepcopy(context))
        rendered, wire_instructions = self.connection._presentation(episode_id, role, instructions, context)
        self.wire.append(dict(rendered=rendered, instructions=wire_instructions))
        assert rendered.startswith("TASK\n") and "STEERING" in rendered and QUESTION in rendered
        assert context["goal"]["objective"] == QUESTION and context["feedback"] is None
        if index == 0:
            chosen = dict(kind="episode_child", role="scientific_process", goal=QUESTION, scope=deepcopy(self.scope),
                purpose="Return the controlled supplied arsenic calculation groups.", schema_json=json.dumps(_schema()), initial_report_json="{}",
                assignment=dict(selection=dict(version="scientific_process_selection_v3", evidence_axis=self.library.reference("A101"),
                    thought_pattern=self.library.reference("P01"), child_tool_info=[dict(name=host.TOOL, resources="local")]),
                    evidence_refs=[self.input_ref], constraints=dict(no_external_acquisition=True), context=dict(supplied_measurements=True)))
        else:
            assert context["requested_form"] == _schema() and "Selected tool: " + host.TOOL + " (local)" in rendered
            if index == 1: arguments = _arguments(self.input_ref)
            elif index == 2:
                original, = self.outcomes(); assert original["status"] == "completed"
                arguments = _arguments(original["result"]["source_ref"], mode="calculate_saved", selected=selection(species=()))
                assert "supplied_mass_per_volume_unit" in rendered and "no_uncertainty_propagation_or_independence_assumption" in rendered
            else:
                original, derived = self.outcomes(); assert derived["status"] == "completed"
                arguments = _arguments(derived["result"]["source_ref"], mode="read_stored")
                assert "selected_species_count" in rendered and "no_peak_picking_integration_or_calibration_fitting" in rendered
            chosen = dict(kind="tool", tool=host.TOOL, arguments=arguments)
        response = dict(selection=chosen, report_update={})
        branches = [branch for branch in output_schema["properties"]["selection"]["anyOf"]
            if all(chosen[key] in branch["properties"].get(key, {}).get("enum", []) for key in ("kind", "role", "tool") if key in chosen)]
        assert len(branches) == 1
        fields = branches[0]["properties"]
        for name in ("assignment", "arguments"):
            if name in chosen and fields[name].get("type") == "string": chosen[name] = json.dumps(chosen[name], allow_nan=False)
        if chosen["kind"] == "episode_child":
            for name in fields["scope"]["required"]:
                if name not in chosen["scope"]:
                    assert {"type": "null"} in fields["scope"]["properties"][name]["anyOf"]
                    chosen["scope"][name] = None
        Draft202012Validator(output_schema).validate(response)
        return response

    async def release(self, episode_id):
        pass


@pytest.mark.parametrize("real_worker", [False, True], ids=["engineered-worker", "bounded-owned-worker"])
def test_current_workflow_session_typed_sources_saved_empty_and_closed_replay(tmp_path, monkeypatch, real_worker):
    if real_worker and os.environ.get("HMMER_NATIVE_ORACLE_ORDINARY_ARSENIC") != "1":
        pytest.skip("requires explicit bounded ordinary calibrated-signal worker selection")
    proof = dict(scope="current Workflow over supplied engineering measurements; no instrument/native wrapper",
        real_owned_worker=real_worker, passed=False)
    try:
        with Store(tmp_path / "store") as store:
            store.create_problem(raw_sequence="ACGT", molecule="dna")
            material = store.register_material(data=canonical(_sheet()).encode(), name="supplied calibrated-signal Sheet", use="evidence")
            input_ref = store.get(material["source_ref"])["artifact_ref"]
            workspace = tmp_path / "workspace"; workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            registry = ToolRegistry(store, job_limits=deepcopy(POLICY)); factory.configure_tool_registry(registry)
            scientific = prepare_scientific_binding(run_directory=tmp_path / "run", source_directory=PUBLICATION,
                tool_catalog=registry.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(tmp_path / "run/scientific-process-library")
            provider = _Choices(store, library, store.validate_scope(), input_ref)
            application = factory(store, run_id="current-ordinary-arsenic", directory=tmp_path / "run", tool_registry=registry)
            flow = Workflow(store, registry, provider, tmp_path / "run", "current-ordinary-arsenic", _controller, _zero,
                project_child_credit=_zero, episode_binding_descriptors=[scientific, *application.episode_binding_descriptors],
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                episode_record_receipts=True, initial_known_record_refs=[input_ref])
            state = SimpleNamespace(store=store, registry=registry, worker_calls=[], calculator_calls=[], missing_output=False, returncode=0)
            monkeypatch.setattr(registry.clients, "_http", _forbidden)
            monkeypatch.setattr("socket.create_connection", _forbidden)
            if not real_worker:
                for name in ("prepare_job", "resume_start", "wait_job", "collect", "cancel", "release"):
                    monkeypatch.setattr(native_lifecycle, name, _forbidden)
                _engineered_worker(state, monkeypatch)
            root = flow.build("annotation", "root", QUESTION, provider.scope)
            completed = asyncio.run(root.run_async(flow.context))
            assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
            original, derived, read = provider.outcomes()
            assert all(item["status"] == "completed" for item in (original, derived, read))
            groups = [original["result"], derived["result"]]
            assert read["result"] == derived["result"] and read["changed_record_refs"] == []
            assert groups[0]["source_ref"] != groups[1]["source_ref"]
            assert groups[0]["values"]["rows"][0]["aliquot_concentration"]["value"] == 10
            assert groups[0]["values"]["rows"][0]["original_sample_concentration"]["value"] == 20
            assert groups[1]["values"]["rows"] == [] and groups[1]["context"]["qualifications"] == core.QUALIFICATIONS
            assert groups[1]["values"]["population"]["selected_species_count"] == 0
            records = EpisodeReturnRecords(store, flow.run_id, failure_prefix="arsenic_workflow_")
            episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (flow.run_id,)))
            assert len(episodes) == 2
            parent, science = [records.context(row[0]) for row in episodes]
            with monkeypatch.context() as guards:
                guards.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
                guards.setattr(calculations, "validate_calibrated_signal_components", _forbidden)
                assert flow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == groups
                assert flow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == groups
                assert flow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == groups
            forms = list(store.db.execute("SELECT facts,form FROM runtime_forms WHERE run_id=?", (flow.run_id,)))
            assert len(forms) == 1 and json.loads(forms[0][0])[contracts.FACT_SOURCE] == groups
            assert json.loads(forms[0][1]) == dict(outcomes=groups)
            attempts = list(store.db.execute("SELECT failure,form FROM runtime_report_attempts WHERE run_id=?", (flow.run_id,)))
            assert len(attempts) == 1 and attempts[0][0] is None and json.loads(attempts[0][1]) == dict(outcomes=groups)
            sources = [store.get(item["source_ref"]) for item in groups]
            assert sources[1]["parent_source_refs"] == [sources[0]["id"]]
            controls = [json.loads(store.get_artifact(source["request_ref"])) for source in sources]
            assert [control["worker"]["result"]["calculation"] for control in controls] == [
                dict(state="completed", call_count=1, native_invocation="not_requested")] * 2
            assert controls[0]["intent"]["input"]["file"] == controls[1]["intent"]["input"]["file"]
            assert controls[0]["intent"]["input"]["raw_hex"] == controls[1]["intent"]["input"]["raw_hex"]
            assert bytes.fromhex(controls[0]["intent"]["input"]["raw_hex"]) == canonical(_sheet()).encode()
            assert len({control["worker"]["selection"]["cwd"] for control in controls}) == 2
            private = {ref for source in sources for ref in (source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"])}
            for context in (parent, science):
                known = set(flow.receipts.known(context.episode_id))
                assert {item["source_ref"] for item in groups} <= known and private.isdisjoint(known)
            assert input_ref in set(flow.receipts.known(science.episode_id))
            resolved = []
            def resolve(ref, namespace): resolved.append((ref, namespace)); return namespace == "source" and ref in {item["source_ref"] for item in groups}
            assert validate_form(dict(outcomes=groups), _schema(), resolve) == dict(outcomes=groups)
            assert set(resolved) == {(item["source_ref"], "source") for item in groups}
            before = _tables(store)
            with monkeypatch.context() as guards:
                guards.setattr(provider, "complete", _forbidden)
                guards.setattr(ToolRegistry, "execute_async", _forbidden)
                guards.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
                guards.setattr(Store, "get_artifact", _forbidden)
                guards.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
                guards.setattr(calculations, "validate_calibrated_signal_components", _forbidden)
                for name in ("prepare_job", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
                    guards.setattr(native_lifecycle, name, _forbidden)
                reopened_factory = ExecutionServiceFactory.from_record(factory.as_record())
                reopened_registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
                reopened_factory.configure_tool_registry(reopened_registry)
                reopened_provider = _Choices(store, ScientificProcessLibrary(tmp_path / "run/scientific-process-library"),
                    deepcopy(provider.scope), input_ref)
                guards.setattr(reopened_provider, "complete", _forbidden)
                reopened_application = reopened_factory(store, run_id=flow.run_id, directory=tmp_path / "run",
                    tool_registry=reopened_registry)
                assert reopened_factory.as_record() == factory.as_record()
                assert reopened_application.episode_binding_descriptors == application.episode_binding_descriptors
                reopened = Workflow(store, reopened_registry, reopened_provider, tmp_path / "run", flow.run_id, _controller, _zero,
                    project_child_credit=_zero, episode_binding_descriptors=[deepcopy(scientific), *reopened_application.episode_binding_descriptors],
                    role_credit_bindings=reopened_application.role_credit_bindings,
                    job_progress_provider=reopened_application.job_progress_provider,
                    episode_record_receipts=True, initial_known_record_refs=[input_ref])
                again_root = reopened.build("annotation", "root", QUESTION, provider.scope)
                again = asyncio.run(again_root.run_async(reopened.context))
                assert plain(asyncio.run(again_root.build_result(again)).as_record()) == dict(credit=0, pending_handles=[])
                assert _closed_child(reopened, again_root, parent, science) == dict(form=dict(outcomes=groups))
                assert reopened_provider.contexts == reopened_provider.wire == []
            assert _tables(store) == before and len(provider.contexts) == 4
            if not real_worker: assert len(state.calculator_calls) == 2
            proof.update(passed=True, groups=groups, provider_calls=len(provider.contexts), source_records=sources,
                calculator_calls=state.calculator_calls, controlled_calculation_returns=2,
                typed_source_only=True, parent_original_input_authority=True, closed_replay_rows_unchanged=True)
    finally:
        _write(tmp_path / "ARSENIC_WORKFLOW.json", proof)


def _input_view(sheet=None, *, unavailable=False):
    """Pure contract example; this constructs no Source or custody evidence."""
    sheet = _sheet() if sheet is None else sheet
    roles = {name: "empty" if type(sheet[name]) is list and not sheet[name] else "present"
        for name in contracts.INPUT_ROLES}
    if unavailable: roles["calibrations"] = "invalid"
    return contracts.ordinary_arsenic_input_view(source_ref="source_" + "1" * 24,
        result_selection=selection(species=()), input_state="partial" if unavailable else "complete",
        role_states=roles, sheet=None if unavailable else sheet)


@pytest.mark.parametrize("extra", ["selection", "input", "calibrations", "sheet", "resource_id"])
def test_input_inspection_arguments_accept_no_replacement_operands(extra):
    arguments = dict(mode="read_inputs", result_ref="source_" + "1" * 24)
    assert contracts.validate_ordinary_arsenic_arguments(arguments) == arguments
    with pytest.raises(ValueError, match="closed_shape_required"):
        contracts.validate_ordinary_arsenic_arguments({**arguments, extra: None})


def test_input_view_preserves_full_master_sheet_and_only_enclosing_source_is_reference_bearing(monkeypatch):
    monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
    monkeypatch.setattr(calculations, "validate_calibrated_signal_components", _forbidden)
    original = _sheet()
    view = _input_view(original)
    assert view["sheet"] == original and view["result_selection"]["species_ids"] == []
    assert view["sheet"]["association"]["analysis_species_ids"] == original["association"]["analysis_species_ids"]
    assert view["sheet"]["samples"][0]["measurements"][0]["signal"]["value"] == 23
    assert view["sheet"]["calibrations"][0]["offset"]["value"] == 3
    assert view["sheet"]["calibrations"][0]["concentration_per_signal"]["value"] == .5
    assert view["sheet"]["samples"][0]["dilution"]["factor"]["value"] == 2
    references = []
    def collect(schema, path=()):
        if isinstance(schema, dict):
            if schema.get("format") == "reference" or "x-reference-namespace" in schema:
                references.append(path)
            for key, value in schema.items(): collect(value, (*path, key))
        elif isinstance(schema, list):
            for index, value in enumerate(schema): collect(value, (*path, index))
    collect(contracts.ordinary_arsenic_input_view_schema())
    assert references == [("properties", "source_ref")]
    checked = contracts.validate_ordinary_arsenic_input_view(view)
    checked["sheet"]["samples"][0]["measurements"][0]["signal"]["value"] = 99
    assert view["sheet"] == original
    assert _input_view(unavailable=True)["unavailable_reason"] == "validated_sheet_unavailable"


@pytest.mark.parametrize("change", ["private_field", "wrong_version", "bad_source", "empty_reason",
    "complete_without_sheet", "partial_with_sheet", "boolean_signal", "role_conflict"])
def test_input_view_rejects_control_fields_and_inconsistent_supplied_shapes(change):
    view = _input_view()
    if change == "private_field": view["raw_hex"] = "00"
    elif change == "wrong_version": view["version"] = contracts.PACKET_VERSION
    elif change == "bad_source": view["source_ref"] = "artifact_" + "1" * 64
    elif change == "empty_reason": view["unavailable_reason"] = "validated_sheet_unavailable"
    elif change == "complete_without_sheet": view["sheet"] = None
    elif change == "partial_with_sheet": view["input_state"] = "partial"
    elif change == "boolean_signal": view["sheet"]["samples"][0]["measurements"][0]["signal"]["value"] = True
    else: view["role_states"]["samples"] = "empty"
    with pytest.raises(ValueError): contracts.validate_ordinary_arsenic_input_view(view)


def test_input_inspection_preserves_unavailable_partial_sheet_without_starting_worker(tmp_path, monkeypatch):
    document = _sheet(); document["calibrations"] = None
    with _owned(tmp_path, monkeypatch, document=document) as value:
        original = _dispatch(value, _arguments(value.reference), 0)
        assert original["status"] == "partial" and value.worker_calls == value.calculator_calls == []
        source = value.store.get(original["result"]["source_ref"])
        control = json.loads(value.store.get_artifact(source["request_ref"]))
        assert control["intent"]["request"] is None and control["worker"] is None
        assert control["files"]["components"] == host.stored.empty_file_state("not_requested")
        assert original["result"]["file_states"] == dict(sheet="retained_undeclared", components="not_requested")
        assert original["result"]["context"]["calculation"] == dict(
            state="input_unavailable", call_count=0, native_invocation="not_requested")
        assert all(host.stored.validate_file_state(state) == state for state in control["files"].values())
        before = deepcopy(value.store.list("source"))
        get = Store.get_artifact
        def controlled(current, reference):
            assert reference in {source["artifact_ref"], source["request_ref"]}
            return get(current, reference)
        monkeypatch.setattr(Store, "get_artifact", controlled)
        monkeypatch.setattr(value.registry, "_sequence_worker_async", _forbidden)
        monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
        outcome = _dispatch(value, dict(mode="read_inputs", result_ref=source["id"]), 1)
        view = contracts.validate_ordinary_arsenic_input_view(outcome["result"])
        assert outcome["status"] == "partial" and outcome["changed_record_refs"] == []
        assert outcome["record_refs"] == [source["id"]] and view["sheet"] is None
        assert view["input_state"] == "partial" and view["role_states"]["calibrations"] == "invalid"
        assert view["unavailable_reason"] == "validated_sheet_unavailable"
        saved_operations = [tuple(row) for row in value.store.db.execute("SELECT * FROM tool_operations ORDER BY rowid")]
        assert _dispatch(value, dict(mode="read_inputs", result_ref=source["id"]), 1) == outcome
        assert [tuple(row) for row in value.store.db.execute("SELECT * FROM tool_operations ORDER BY rowid")] == saved_operations
        assert value.store.list("source") == before and value.worker_calls == value.calculator_calls == []


def _arsenic_inputs_controller(path, initial):
    from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate
    horizon = 1 if path[-1][0] == "annotation" else 2
    def estimate(history, parameters, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= horizon else 1),
            parameters, dict(engineering_fixture="retained_inputs_then_literal_stored_values"))
    return YieldController(str(path), initial, 0, estimate_with_context=estimate)


@pytest.mark.parametrize("source_ordinal", [0, 1])
def test_authentic549_source_only_input_inspection_without_workers_or_original_file(tmp_path, monkeypatch, source_ordinal):
    """A new current reader; the two authentic549 calculator workers never repeat."""
    import shutil
    from gene_annotation_episode.decision_context import state_frame
    from tests.test_homer_motif_saved_workflow import _encode
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history, _sqlite_pins
    configured = os.environ.get("HMMER_NATIVE_ORACLE_ARSENIC_INPUT_VIEW_PROOF")
    if not configured: pytest.skip("requires the explicitly pinned successful549 supplied-result evidence")
    path = Path(configured)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    expected_hash = "a514e788d39334a7b3a0cc31b72c5419c41835dd7f078e8f4c6a5a43ecbc9fdd"
    assert os.environ["HMMER_NATIVE_ORACLE_ARSENIC_INPUT_VIEW_PROOF_SHA256"] == expected_hash
    raw = path.read_bytes()
    assert len(raw) == 7617 and hashlib.sha256(raw).hexdigest() == expected_hash
    original = json.loads(raw)
    assert original["passed"] is original["real_owned_worker"] is original["typed_source_only"] is True
    assert original["controlled_calculation_returns"] == 2 and len(original["groups"]) == 2
    original_case = path.parent
    assert _sqlite_pins(original_case / "store") == [dict(name="state.sqlite3",
        sha256="08ac8e3a0c27dd700dff25e5d22c2f5bbf830c76a689e993a0763ef05d04fc0f", size_bytes=13463552)]
    before_original = _files(original_case)
    shutil.copytree(original_case / "store", tmp_path / "retained-store", copy_function=shutil.copy2, symlinks=True)
    assert _files(tmp_path / "retained-store") == _files(original_case / "store")
    output = tmp_path / "ARSENIC_RETAINED549_INPUT_INSPECTION.json"
    proof = dict(version="ordinary_arsenic_retained_input_inspection_v1", original_proof_sha256=expected_hash,
        source_ordinal=source_ordinal, calls=[], body_reads=[], passed=False,
        new_calculations=0, new_workers=0, new_native_calls=0, new_sources=0,
        qualification="New explicit Source-only inspection and literal stored read over successful549 evidence; no original worker, instrument or calculation repeats.")
    actual_get = Store.get_artifact
    try:
        with Store(tmp_path / "retained-store") as store:
            original_history = _history(store, "current-ordinary-arsenic")
            original_tables, artifacts_before = _tables(store), _files(store.path / "artifacts")
            sources_before = deepcopy(store.list("source"))
            selected_source = original["source_records"][source_ordinal]
            assert store.get(selected_source["id"]) == selected_source
            controls = [json.loads(actual_get(store, source["request_ref"])) for source in original["source_records"]]
            stored_input = controls[source_ordinal]["intent"]["input"]
            original_file = stored_input["file"]["artifact_ref"]
            assert stored_input["sheet"] == _sheet()
            allowed = {source["request_ref"] for source in original["source_records"]} | {selected_source["artifact_ref"]}
            assert original_file not in allowed
            def stored_only(current, reference):
                assert reference in allowed, "original input/components/native/software body forbidden: " + reference
                proof["body_reads"].append(reference)
                return actual_get(current, reference)
            for name in ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release"):
                monkeypatch.setattr(native_lifecycle, name, _forbidden)
            monkeypatch.setattr(calculations, "calculate_calibrated_signal_components", _forbidden)
            monkeypatch.setattr(calculations, "validate_calibrated_signal_components", _forbidden)
            monkeypatch.setattr(host, "run_arsenic_speciation_tool_request", _forbidden)
            monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
            monkeypatch.setattr(Store, "artifact", _forbidden)
            monkeypatch.setattr(Store, "put", _forbidden)
            monkeypatch.setattr(Store, "get_artifact", stored_only)
            monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
            monkeypatch.setattr("socket.create_connection", _forbidden)
            workspace = tmp_path / "workspace"; workspace.mkdir()
            factory = ExecutionServiceFactory({"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(POLICY))}, {}, 2, .25, .5)
            registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
            factory.configure_tool_registry(registry)
            run, run_id = tmp_path / "run", "retained-arsenic-input-view-" + str(source_ordinal)
            binding = prepare_scientific_binding(run_directory=run, source_directory=PUBLICATION,
                tool_catalog=registry.catalog(), child_roles=["scientific_process"])
            library = ScientificProcessLibrary(run / "scientific-process-library")
            scope = store.validate_scope()
            question = ("Which supplied signal, retention-time, calibration, dilution, units and association-population "
                "operands underlie the retained result, and what result selection and unchanged qualified values does it retain? "
                "Distinguish supplied inputs from measured chemical identity or a new instrument run.")
            class Choices:
                def __init__(self): self.cleanup_callbacks = []
                async def complete(self, episode_id, role, instructions, context, schema):
                    index = len(proof["calls"])
                    assert role == "REASONING" and index < 3 and not context.get("feedback"), context.get("feedback")
                    connection = object.__new__(_SessionConnection); connection.scientific_prompt_states = {}
                    wire, wire_instructions = connection._presentation(episode_id, role, instructions, state_frame(plain(context)))
                    assert wire.startswith("TASK\n") and "STEERING" in wire and question in wire
                    proof["calls"].append(dict(episode_id=episode_id, context=plain(context), instructions=plain(instructions),
                        wire=wire, wire_instructions=plain(wire_instructions)))
                    if index == 0:
                        chosen = dict(kind="episode_child", role="scientific_process", goal=question, scope=deepcopy(scope),
                            purpose="Return the retained numerical result without creating another calculation.", schema_json=json.dumps(_schema()), initial_report_json="{}",
                            assignment=dict(selection=dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A101"),
                                thought_pattern=library.reference("P01"), child_tool_info=[dict(name=host.TOOL, resources="local")]),
                                evidence_refs=[selected_source["id"]], constraints=dict(no_new_calculation=True), context={}))
                    else:
                        known = set(flow.receipts.known(episode_id))
                        assert selected_source["id"] in known and original_file not in known
                        if index == 1: arguments = dict(mode="read_inputs", result_ref=selected_source["id"])
                        else:
                            view = context["last_local_outcome"]["result"]
                            assert view["version"] == contracts.INPUT_VIEW_VERSION and view["sheet"] == stored_input["sheet"]
                            assert view["result_selection"] == original["groups"][source_ordinal]["selection"]
                            assert "| Field | Supplied value |" in wire and "sheet.samples[0].measurements[0].signal.value" in wire
                            assert "concentration_per_signal.value" in wire and "dilution.factor.value" in wire
                            assert "association.analysis_species_ids" in wire
                            for private in (selected_source["request_ref"], original_file, str(original_case)):
                                assert private not in wire
                            arguments = dict(mode="read_stored", result_ref=selected_source["id"])
                        chosen = dict(kind="tool", tool=host.TOOL, arguments=arguments)
                    return _encode(dict(selection=chosen, report_update={}), schema)
                async def release(self, episode_id): self.cleanup_callbacks.append(episode_id)
            provider = Choices()
            application = factory(store, run_id=run_id, directory=run, tool_registry=registry)
            flow = Workflow(store, registry, provider, run, run_id, _arsenic_inputs_controller, _zero,
                project_child_credit=_zero, annotation_child_roles=("scientific_process",),
                episode_binding_descriptors=[binding, *application.episode_binding_descriptors],
                role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
                episode_record_receipts=True, initial_known_record_refs=[selected_source["id"]])
            root = flow.build("annotation", "root", question, scope)
            current_parent = flow.binding_context(root.source)
            before_denied_reads = list(proof["body_reads"])
            other_source = original["source_records"][1 - source_ordinal]["id"]
            assert other_source not in set(flow.receipts.known(current_parent.episode_id))
            with pytest.raises(ValueError, match="arsenic_speciation_source_not_received"):
                host.read_arsenic_speciation_inputs(registry, current_parent,
                    flow.services.read_received_molecular_input, other_source)
            assert proof["body_reads"] == before_denied_reads
            record = asyncio.run(root.run_async(flow.context))
            assert plain(asyncio.run(root.build_result(record)).as_record()) == dict(credit=0, pending_handles=[])
            history = _history(store, run_id)
            episodes = sorted(history["runtime_episodes"], key=lambda row: len(json.loads(row["path"])))
            parent, science = [EpisodeReturnRecords(store, run_id, failure_prefix="arsenic_inputs_").context(row["episode_id"]) for row in episodes]
            actions = [row for row in history["runtime_actions"] if row["episode_id"] == science.episode_id]
            assert [json.loads(row["action"])["arguments"]["mode"] for row in actions] == ["read_inputs", "read_stored"]
            inspection, literal = [json.loads(row["result"]) for row in actions]
            assert inspection["status"] == literal["status"] == "completed"
            view = inspection["result"]
            assert view == contracts.ordinary_arsenic_input_view(source_ref=selected_source["id"],
                result_selection=original["groups"][source_ordinal]["selection"], input_state="complete",
                role_states=stored_input["role_states"], sheet=stored_input["sheet"])
            assert inspection["record_refs"] == [selected_source["id"]] and inspection["changed_record_refs"] == []
            assert literal["result"] == original["groups"][source_ordinal]
            assert flow.services.molecular_own_facts(science, fact_source=contracts.FACT_SOURCE) == [literal["result"]]
            assert flow.services.molecular_frozen_facts(science, fact_source=contracts.FACT_SOURCE) == [literal["result"]]
            assert flow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE) == [literal["result"]]
            for context in (parent, science):
                known = set(flow.receipts.known(context.episode_id))
                assert selected_source["id"] in known and original_file not in known
                denied, _ = flow.services.read_received_molecular_input(context, original_file, "artifact", file_format="json")
                assert denied["failure"] is not None
                for reference in (selected_source["artifact_ref"], selected_source["request_ref"], *selected_source["auxiliary_artifact_refs"]):
                    assert reference not in known and flow.resolver(plain(context.scope), context=context)(reference, "artifact") is False
            # Authenticated action-reader reuse does not mint a result Source
            # or add an input-inspection group to numerical facts.
            key = f"{run_id}:{science.episode_id}:{actions[0]['decision_index']}"
            assert host.read_arsenic_speciation_action_result(registry, science,
                dict(mode="read_inputs", result_ref=selected_source["id"]), key,
                reader=flow.services.read_received_molecular_input) == view
            assert _history(store, "current-ordinary-arsenic") == original_history
            assert store.list("source") == sources_before and _files(store.path / "artifacts") == artifacts_before
            after = _tables(store)
            assert all(set(rows) <= set(after[name]) for name, rows in original_tables.items())
            proof.update(passed=True, view=view, literal_result=literal["result"], new_numerical_groups=0,
                old_history_unchanged=True, original_input_File_not_granted=True,
                no_new_Source_or_Artifact=True, provider_cleanup_callbacks=provider.cleanup_callbacks,
                history=history)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["original_inventory_before"] = before_original
        proof["original_inventory_after"] = _files(original_case)
        proof["original_files_and_modes_unchanged"] = proof["original_inventory_before"] == proof["original_inventory_after"]
        _write(output, proof)
        assert proof["original_files_and_modes_unchanged"]
