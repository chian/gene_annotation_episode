"""CD adapter controls, using engineered host admission and the existing core.

These unit seams do not establish Store custody or native-worker execution.
The separate Workflow controls exercise the actual shared owner and lifecycle.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import circular_dichroism_contracts as contracts
from gene_annotation_episode import circular_dichroism_measurements as core
from gene_annotation_episode import circular_dichroism_tools as tools
from gene_annotation_episode import molecular_measurement_tools as owner
from gene_annotation_episode import native_file_capture
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.molecular_sequence_input_contracts import decode_molecular_sequence_input
from test_circular_dichroism_measurements import supplied


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
SOURCE = "source_" + "a" * 24
OPERATION = "unit:cd:3"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _request(raw):
    digest = hashlib.sha256(raw).hexdigest()
    return dict(version=contracts.REQUEST_VERSION, input_file=dict(
        artifact_ref="artifact_" + digest, sha256=digest, size_bytes=len(raw), format="json"))


def _raw(value=None):
    return json.dumps(supplied() if value is None else value, allow_nan=False).encode()


def _native(value=None):
    value = supplied() if value is None else value
    sheet = core.populate_circular_dichroism_sheet(measurements=value)
    return dict(version=contracts.RESULT_VERSION, request=_request(_raw(value)), sheet=sheet,
        components=core.calculate_circular_dichroism_components(sheet))


def _forbidden(*args, **kwargs):
    raise AssertionError("unexpected acquisition, calculation or publication")


def _worker_input(tmp_path, raw):
    directory = tmp_path / "worker"
    directory.mkdir()
    path = directory / "input.json"
    path.write_bytes(raw)
    return directory, path, _request(raw)


def test_worker_uses_one_existing_calculation_and_preserves_native_flag(tmp_path, monkeypatch):
    value = supplied()
    directory, path, request = _worker_input(tmp_path, _raw(value))
    expected = _native(value)
    calls = []
    calculate = core.calculate_circular_dichroism_components
    def counted(sheet):
        calls.append(deepcopy(sheet))
        return calculate(sheet)
    monkeypatch.setattr(core, "calculate_circular_dichroism_components", counted)
    result = tools.run_circular_dichroism_tool_request(request, input_path=path, output_directory=directory)
    assert result == expected and len(calls) == 1
    assert set(result) == {"version", "request", "sheet", "components"}
    assert result["sheet"]["source_method"]["native_execution"] is False
    assert sorted(p.name for p in directory.iterdir()) == ["input.json"]


@pytest.mark.parametrize("raw,code", [
    (b"\xff", "invalid_utf8"), (b'{"x":1,"x":2}', "duplicate_json_key"),
    (b'{"x":NaN}', "nonfinite_json"), (b'{"x":1e400}', "nonfinite_json"),
    (b'{"x":1e-4000}', "unrepresentable_json_number"), (b'{"x":', "invalid_json"),
    (b'{"x":"\\ud800"}', "invalid_json"),
])
def test_worker_shared_decode_failures_precede_any_sheet(tmp_path, monkeypatch, raw, code):
    directory, path, request = _worker_input(tmp_path, raw)
    monkeypatch.setattr(core, "populate_circular_dichroism_sheet", _forbidden)
    monkeypatch.setattr(core, "calculate_circular_dichroism_components", _forbidden)
    assert decode_molecular_sequence_input(raw, tag_key="schema")["failure"]["code"] == code
    with pytest.raises(ValueError, match="^circular_dichroism_input_" + code + "$"):
        tools.run_circular_dichroism_tool_request(request, input_path=path, output_directory=directory)
    assert sorted(p.name for p in directory.iterdir()) == ["input.json"]


@pytest.mark.parametrize("fault,code", [
    ("hash", "input_identity_conflict"), ("size", "input_identity_conflict"),
    ("symlink", "input_unavailable"), ("missing", "input_unavailable"),
    ("directory", "input_unavailable"), ("outside", "owned_input_conflict"),
])
def test_worker_file_identity_and_owned_location_precede_decode(tmp_path, monkeypatch, fault, code):
    directory, path, request = _worker_input(tmp_path, _raw())
    if fault == "hash":
        request["input_file"].update(sha256="0" * 64, artifact_ref="artifact_" + "0" * 64)
    elif fault == "size": request["input_file"]["size_bytes"] += 1
    elif fault == "symlink":
        target = tmp_path / "target.json"; target.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(target)
    elif fault == "missing": path.unlink()
    elif fault == "directory": path.unlink(); path.mkdir()
    else:
        outside = tmp_path / "outside.json"; outside.write_bytes(path.read_bytes()); path = outside
    monkeypatch.setattr(tools, "decode_molecular_sequence_input", _forbidden)
    monkeypatch.setattr(core, "calculate_circular_dichroism_components", _forbidden)
    with pytest.raises(ValueError, match="^circular_dichroism_" + code + "$"):
        tools.run_circular_dichroism_tool_request(request, input_path=path, output_directory=directory)


def test_worker_keeps_invalid_spectrum_and_independent_valid_thermal(tmp_path):
    value = supplied(); value["spectrum"]["cd_signal_data"].pop()
    directory, path, request = _worker_input(tmp_path, _raw(value))
    result = tools.run_circular_dichroism_tool_request(request, input_path=path, output_directory=directory)
    assert result == _native(value)
    assert result["components"]["spectrum"]["state"] == "invalid_input"
    assert result["components"]["thermal"]["state"] == "present"


def _host(tmp_path, monkeypatch, *, raw=None, mutate=None, reader_failure=None, worker_failure=None):
    raw = _raw() if raw is None else raw
    original = tmp_path / "received.json"; original.write_bytes(raw)
    scientific = _request(raw)
    item = dict(file=scientific["input_file"], content=decode_molecular_sequence_input(raw, tag_key="schema"))
    context = SimpleNamespace(run_id="unit-run", episode_id="unit-episode", request={"question": "supplied CD summaries"})
    events = []
    def reader(actual_context, reference, namespace, *, tag_key):
        assert actual_context is context
        assert (reference, namespace, tag_key) == (SOURCE, "source", "schema")
        events.append("reader")
        return dict(input=deepcopy(item), failure=reader_failure)
    def retained(store, selected):
        assert events and events[-1] == "reader"
        assert selected == scientific["input_file"]
        events.append("retained_file")
        return original
    monkeypatch.setattr(native_file_capture, "retained_native_file", retained)
    store = SimpleNamespace(path=tmp_path / "store")
    store.path.mkdir()
    async def worker(operation, arguments, *, directory, owned_directory):
        assert operation == "circular_dichroism" and directory == owned_directory
        assert set(arguments) == {"request", "input_path"} and arguments["request"] == scientific
        assert Path(arguments["input_path"]) == directory / "input.json"
        events.append("worker")
        path = directory / "worker-result.json"
        metadata = dict(native_returncode=0, molecular_failure=worker_failure)
        if worker_failure is None:
            result = tools.run_circular_dichroism_tool_request(arguments["request"],
                input_path=arguments["input_path"], output_directory=directory)
            if mutate is not None: mutate(result)
            path.write_text(_canonical(result))
        else:
            metadata["native_returncode"] = 1
            (directory / "stderr").write_text("ValueError: circular_dichroism_input_duplicate_json_key")
        return SimpleNamespace(output_path=path, metadata=metadata)
    registry = SimpleNamespace(store=store, _sequence_worker_async=worker)
    args = dict(mode="calculate", input=dict(namespace="source", reference=SOURCE), view=None)
    return registry, args, (context, reader), item, original, events


def _prepare(registry, arguments, authority, *, scope=None):
    return asyncio.run(tools.prepare_circular_dichroism_work(registry, arguments,
        scope={} if scope is None else scope, operation_key=OPERATION, authority=authority))


def _directory(registry):
    return registry.store.path / "cache" / "molecular-measurements" / hashlib.sha256(OPERATION.encode()).hexdigest()


def test_prepare_admits_before_private_copy_and_binds_exact_original_request(tmp_path, monkeypatch):
    registry, args, authority, item, original, events = _host(tmp_path, monkeypatch)
    prepared = _prepare(registry, args, authority)
    directory = _directory(registry)
    control = json.loads((directory / "host-binding.json").read_bytes())
    assert events == ["reader", "retained_file", "worker"]
    assert set(control) == {"version", "arguments", "invocation", "received_input", "request"}
    assert control["version"] == "ordinary_cd_request_v1" and control["arguments"] == args
    assert control["received_input"] == item and control["request"] == prepared["stored"]["request"]
    assert set(control["invocation"]) == {"run_id", "episode_id", "operation_key", "decision_index", "request_sha256", "scope"}
    assert control["invocation"]["decision_index"] == 3
    assert (directory / "input.json").read_bytes() == original.read_bytes()
    assert prepared["request"] == control and prepared["item"] == item
    assert prepared["stored"] == _native()


@pytest.mark.parametrize("code", ["reference_not_received", "scope_denied", "invalid_utf8", "duplicate_json_key"])
def test_prepare_rejects_actual_reader_failure_before_any_file_or_worker(tmp_path, monkeypatch, code):
    registry, args, authority, _, _, events = _host(tmp_path, monkeypatch,
        reader_failure=dict(stage="decode" if code in {"invalid_utf8", "duplicate_json_key"} else "authority", code=code))
    monkeypatch.setattr(native_file_capture, "retained_native_file", _forbidden)
    registry._sequence_worker_async = _forbidden
    with pytest.raises(ContractError, match="^molecular_tool_" + code + "$"):
        _prepare(registry, args, authority)
    assert events == ["reader"] and not (registry.store.path / "cache").exists()


@pytest.mark.parametrize("fault,code", [
    ("changed_binding", "original_binding_conflict"), ("invalid_binding", "original_binding_conflict"),
    ("binding_symlink", "original_binding_conflict"), ("missing_binding", "original_binding_missing"),
    ("partial_copy", "copied_input_conflict"), ("copied_symlink", "copied_input_conflict"),
])
def test_prepare_preserves_original_binding_and_never_replaces_partial_copy(tmp_path, monkeypatch, fault, code):
    registry, args, authority, _, _, events = _host(tmp_path, monkeypatch)
    _prepare(registry, args, authority)
    directory = _directory(registry); binding = directory / "host-binding.json"; copied = directory / "input.json"
    original_binding = binding.read_bytes()
    if fault == "changed_binding": args["view"] = dict(spectrum_ordinals=[], thermal_ordinals=[], issue_ordinals=[])
    elif fault == "invalid_binding": binding.write_bytes(b"{")
    elif fault == "binding_symlink":
        target = tmp_path / "binding.json"; target.write_bytes(original_binding)
        binding.unlink(); binding.symlink_to(target)
    elif fault == "missing_binding": binding.unlink()
    elif fault == "partial_copy": copied.write_bytes(b"partial")
    else:
        target = tmp_path / "copy.json"; target.write_bytes(copied.read_bytes())
        copied.unlink(); copied.symlink_to(target)
    events.clear(); registry._sequence_worker_async = _forbidden
    before = copied.read_bytes()
    with pytest.raises(ContractError, match="^circular_dichroism_" + code + "$"):
        _prepare(registry, args, authority)
    assert "worker" not in events and copied.read_bytes() == before
    if fault in {"changed_binding", "partial_copy", "copied_symlink"}:
        assert binding.read_bytes() == original_binding


@pytest.mark.parametrize("fault", ["wrong_request", "different_admitted_sheet", "extra_result_field"])
def test_prepare_rejects_worker_envelope_or_admitted_input_conflict_privately(tmp_path, monkeypatch, fault):
    def mutate(result):
        if fault == "wrong_request":
            result["request"]["input_file"].update(sha256="0" * 64, artifact_ref="artifact_" + "0" * 64)
        elif fault == "different_admitted_sheet":
            changed = supplied(); changed["sample_key"] = "another sample"
            other = _native(changed); result.update(sheet=other["sheet"], components=other["components"])
        else: result["findings"] = "not allowed"
    registry, args, authority, _, _, _ = _host(tmp_path, monkeypatch, mutate=mutate)
    from gene_annotation_episode import materials
    monkeypatch.setattr(materials, "artifact_file", lambda store, path, media_type: "private-artifact")
    with pytest.raises(AcquisitionError) as error:
        _prepare(registry, args, authority)
    assert error.value.code == "local_job_output_invalid"
    assert "native_output_validation" in error.value.diagnostic
    assert error.value.diagnostic["retained_artifacts"] == {"worker_output": "private-artifact"}
    assert error.value.operational["worker_operation"] == "circular_dichroism"
    assert error.value.operational["known_terminal"] is True
    assert "fit" not in error.value.operational and "conversion" not in error.value.operational


def test_prepare_retains_actual_worker_failure_and_decode_diagnostic(tmp_path, monkeypatch):
    failure = dict(code="local_job_failed", phase="local_execution", operational={"evidence": "actual worker exit"},
        diagnostic=dict(worker_error="circular_dichroism_input_duplicate_json_key"))
    registry, args, authority, _, _, _ = _host(tmp_path, monkeypatch, worker_failure=failure)
    from gene_annotation_episode import materials
    monkeypatch.setattr(materials, "artifact_file", lambda store, path, media_type: "private-artifact")
    with pytest.raises(AcquisitionError) as error: _prepare(registry, args, authority)
    assert error.value.code == failure["code"] and error.value.phase == failure["phase"]
    assert error.value.diagnostic["worker_error"] == "circular_dichroism_input_duplicate_json_key"
    assert error.value.diagnostic["retained_artifacts"] == {"stderr": "private-artifact"}
    assert error.value.operational["native_returncode"] == 1
    assert error.value.operational["evidence"] == "actual worker exit"
    assert "call_count" not in _canonical(error.value.operational)


@pytest.mark.parametrize("mode", ["read_stored", "calculate_saved"])
@pytest.mark.parametrize("view", [None, dict(spectrum_ordinals=[2, 0, 2], thermal_ordinals=[4], issue_ordinals=[])])
def test_saved_modes_keep_original_source_and_only_explicit_view_without_acquisition(tmp_path, monkeypatch, mode, view):
    stored = _native(); original = _canonical(stored); calls = []
    publication = dict(stored=stored, source=dict(id=SOURCE), received_input={"historical": "admission"})
    def read(registry, context, reader, reference, *, tool_name):
        assert reference == SOURCE and tool_name == tools.CD_TOOL
        calls.append("read_publication"); return publication
    monkeypatch.setattr(owner, "read_retained_molecular_publication", read)
    monkeypatch.setattr(owner, "retain_molecular_publication", _forbidden)
    monkeypatch.setattr(native_file_capture, "retained_native_file", _forbidden)
    monkeypatch.setattr(tools, "_copy_once", _forbidden)
    calculate = core.calculate_circular_dichroism_components
    def counted(sheet):
        assert sheet is stored["sheet"]
        calls.append("calculate"); return calculate(sheet)
    monkeypatch.setattr(core, "calculate_circular_dichroism_components", counted if mode == "calculate_saved" else _forbidden)
    if mode == "read_stored":
        monkeypatch.setattr(core, "_spectrum", _forbidden); monkeypatch.setattr(core, "_thermal", _forbidden)
    registry = SimpleNamespace(_sequence_worker_async=_forbidden)
    args = dict(mode=mode, result_ref=SOURCE, view=view)
    prepared = _prepare(registry, args, (object(), _forbidden))
    result, refs = tools.publish_circular_dichroism_work(registry, args, prepared)
    expected = (contracts.project_circular_dichroism_return(stored, source_ref=SOURCE) if view is None else
        contracts.project_circular_dichroism_view(stored, source_ref=SOURCE, view=view))
    assert result == expected and refs == [SOURCE]
    assert prepared["stored"] is stored and _canonical(stored) == original
    assert calls == (["read_publication", "calculate"] if mode == "calculate_saved" else ["read_publication"])
    assert "work" not in prepared and "request" not in prepared


def test_calculate_saved_conflict_does_not_replace_original_history_or_publish(monkeypatch):
    stored = _native(); original = _canonical(stored)
    monkeypatch.setattr(owner, "read_retained_molecular_publication", lambda *args, **kwargs:
        dict(stored=stored, source=dict(id=SOURCE), received_input={}))
    monkeypatch.setattr(owner, "retain_molecular_publication", _forbidden)
    calculate = core.calculate_circular_dichroism_components
    def different(sheet):
        result = calculate(sheet); result["qualifications"].append("injected mismatch")
        return result
    monkeypatch.setattr(core, "calculate_circular_dichroism_components", different)
    with pytest.raises(ContractError, match="^circular_dichroism_saved_components_conflict$"):
        _prepare(SimpleNamespace(_sequence_worker_async=_forbidden),
            dict(mode="calculate_saved", result_ref=SOURCE, view=None), (object(), _forbidden))
    assert _canonical(stored) == original


def test_publish_uses_shared_owner_and_returns_only_original_source_projection(monkeypatch):
    stored = _native(); calls = []
    prepared = dict(stored=stored, work=object(), item={"historical": "admission"}, request={"private": "binding"})
    registry = object()
    def retain(actual_registry, actual_prepared, *, tool_name):
        assert actual_registry is registry and actual_prepared is prepared and tool_name == tools.CD_TOOL
        calls.append("retain"); return dict(source=dict(id=SOURCE), native_artifact_ref="private-native", grading_ref="private-grade")
    monkeypatch.setattr(owner, "retain_molecular_publication", retain)
    arguments = dict(mode="calculate", input=dict(namespace="source", reference=SOURCE), view=None)
    result, refs = tools.publish_circular_dichroism_work(registry, arguments, prepared)
    assert calls == ["retain"] and refs == [SOURCE]
    assert result == contracts.project_circular_dichroism_return(stored, source_ref=SOURCE)
    assert "private" not in _canonical(result) and "artifact_ref" not in _canonical(result)
    descriptor = tools.circular_dichroism_tool_contract()
    assert descriptor["resources"] == "local"
    assert descriptor["input_schema"] == contracts.circular_dichroism_tool_argument_schema()


@pytest.mark.parametrize("authority", [None, (), (object(),), (object(), None), [object(), _forbidden]])
def test_prepare_requires_authenticated_reader_boundary(authority):
    with pytest.raises(ContractError, match="^circular_dichroism_authority_required$"):
        _prepare(SimpleNamespace(_sequence_worker_async=_forbidden),
            dict(mode="read_stored", result_ref=SOURCE, view=None), authority)
