"""Engineered lifecycle controls; these fixtures are not native science proof.

All service preparation, dispatch, observation and collection are replaced by
explicit unit controls. No original molecular module or science is executed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from threading import Event

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
from gene_annotation_episode.molecular_sequence_execution_contracts import (
    ATTEMPT_DIRECTORY, BASE_ROLES, BUNDLE_FILENAME, BUNDLE_VERSION, OUTPUT_DIRECTORY,
    OWNER_FILENAME, PLAN_FILENAME, REQUEST_RELATIVE, SOFTWARE_VERSION,
    molecular_sequence_adapter_argv, output_specifications,
)


def _raw(value):
    return (canonical(value) + "\n").encode("utf-8")


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_raw(value))


def _pin(path, raw):
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


@pytest.fixture
def selected_call(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    software_root = tmp_path / "selected-software"
    software_root.mkdir()
    python = software_root / "python"
    python.write_bytes(b"engineering runtime identity only\n")
    manifest = software_root / "manifest.json"
    manifest.write_bytes(b"[]\n")
    python_pin = _pin(python, python.read_bytes())
    manifest_pin = _pin(manifest, manifest.read_bytes())
    software = dict(version=SOFTWARE_VERSION, python=python_pin,
        python_home=str(software_root), python_version="engineering fixture; never executed",
        import_roots=[str(software_root)], software_files_file=manifest_pin,
        software_files_ref="artifact_" + manifest_pin["sha256"])
    deployment = dict(version=ordinary.source.DEPLOYMENT_VERSION,
        runtime=dict(executable=python_pin, home=str(software_root)),
        module=dict(path=str(software_root / "original-molecular.py"),
            sha256=ordinary.source.SOURCE_SHA256, size_bytes=91223),
        import_roots=[str(software_root)], software_files_file=manifest_pin,
        software_files_ref="artifact_" + manifest_pin["sha256"])
    sequence = "atgAAAtAA"
    sequence_sha = hashlib.sha256(sequence.encode("ascii")).hexdigest()
    subject = dict(id="engineering-subject", record_type="input",
        sequence_ref=dict(artifact_ref="artifact_" + sequence_sha, format="ascii_sequence"))
    operand = dict(version=ordinary.OPERAND_VERSION, subject=subject, sequence=sequence,
        parent_mapping={"subject_ref": subject["id"], "segments": [
            {"start": 0, "end": 9, "strand": "+", "unit": "nt"}]}, mapping_failure=None,
        input_file=dict(artifact_ref="artifact_" + sequence_sha, sha256=sequence_sha,
            size_bytes=len(sequence), format="ascii_sequence"),
        associations={"engineering_fixture": True, "source_refs": ["original-associated-record"]},
        footprint=[{"ref": subject["id"], "measurement": "literal original operand metadata"}])
    context = BindingContext(run_id="engineering-run", episode_id="engineering-episode",
        role="scientific_process", path=(("scientific_process", "engineered-path"),),
        scope={"subject_refs": [subject["id"]]}, assignment={"engineering_control": "ordinary ORF"},
        request={"engineering_control": True}, received_record_refs=(subject["id"],))
    call = dict(context=context, operation_key="engineering-run:engineering-episode:0",
        arguments=dict(subject_ref=subject["id"], min_length=0, search_reverse=True,
            filter_subsets=False, rows=[dict(row_id={"kind": "orf", "row_index": 0},
                fields=["native_row", "orf_source_path"])]),
        frozen_operand=operand,
        selected=dict(resource_id="engineering-selected-resource", workspace=str(workspace),
            deployment=deployment, software=software, environment=deepcopy(ordinary.ENVIRONMENT_SELECTION)),
        policy=LocalJobPolicy(**ordinary.POLICY))
    calls = []

    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls.append(deepcopy(dict(command=command, cwd=str(cwd), policy=policy.to_dict(), env=env)))
        paths = {role: str(cwd / (".local-job-" + "1" * 32 + "." + role))
            for role in ("request", "ready", "release", "status", "result", "launcher")}
        request = dict(command=list(command), cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"],
            stdin_path=None, env=deepcopy(env))
        _write(paths["request"], request)
        Path(stdout_path).write_bytes(b"")
        Path(stderr_path).write_bytes(b"")
        body = dict(version=ordinary.native.VERSION, unit="engineering-original.service",
            command=list(command), cwd=str(cwd), stdout=str(stdout_path), stderr=str(stderr_path),
            paths=paths, metadata={"policy": policy.to_dict(), "engineering_fixture": True},
            stage="prepared", started_at=None, started_monotonic_ns=None, boot_id=None,
            request_sha256=hashlib.sha256(Path(paths["request"]).read_bytes()).hexdigest())
        _write(handle_path, body)
        return ordinary.native.NativeJobHandle(Path(handle_path))

    monkeypatch.setattr(ordinary.native, "prepare_job", prepare)
    for name in ("wait_job", "cancel", "release", "start_job", "run_blocking"):
        monkeypatch.setattr(ordinary.native, name,
            lambda *a, _name=name, **k: pytest.fail("forbidden lifecycle API: " + _name))
    return call, calls


def _prepared(selected_call):
    call, calls = selected_call
    return ordinary.prepare_ordinary_orf_attempt(**call), calls


def _lifecycle(monkeypatch, prepared, *, views=("prepared", "running", "returned"), code=0,
        collect_error=None, observation_error=None):
    events, index = [], [0]
    metadata = {"policy": deepcopy(ordinary.POLICY), "native_returncode": code,
        "engineering_fixture": True}

    def status(handle):
        events.append("status")
        if observation_error is not None:
            raise observation_error
        state = views[min(index[0], len(views) - 1)]
        index[0] += 1
        return dict(version=ordinary.native.VERSION, state=state,
            terminal=state == "returned", quiescent=state in ("returned", "prepared", "execution_unknown"),
            metadata=deepcopy(metadata), native_receipt={"engineering_fixture": True}, files={})

    def resume(handle):
        events.append("resume_start")
        body = handle.read()
        body["stage"] = "released"
        _write(handle.path, body)
        Path(body["paths"]["release"]).touch()
        return handle

    def collect(handle):
        events.append("collect")
        if collect_error is not None:
            raise collect_error
        body = handle.read()
        return LocalJobResult(code, Path(body["stdout"]), Path(body["stderr"]), deepcopy(metadata))

    monkeypatch.setattr(ordinary.native, "status", status)
    monkeypatch.setattr(ordinary.native, "resume_start", resume)
    monkeypatch.setattr(ordinary.native, "collect", collect)
    monkeypatch.setattr(ordinary.time, "sleep", lambda delay: events.append(("sleep", delay)))
    return events


def test_preparation_copies_original_operand_and_selected_request(selected_call, monkeypatch):
    call, calls = selected_call
    monkeypatch.setenv("UNSELECTED_AMBIENT_VALUE", "must not enter selected environment")
    prepared = ordinary.prepare_ordinary_orf_attempt(**call)
    plan, binding = prepared["plan"], prepared["binding"]
    root = Path(call["selected"]["workspace"]) / ".episode-operations" / digest(
        {"run": call["context"].run_id, "episode": call["context"].episode_id}) / digest(call["operation_key"])
    assert prepared["handle_path"] == str(root / "native.json")
    assert plan["attempt_directory"] == str(root / ATTEMPT_DIRECTORY)
    assert plan["identity"]["assignment_sha256"] == digest(call["context"].as_record()["assignment"])
    assert binding["frozen_operand"] == call["frozen_operand"]
    assert binding["arguments"] == call["arguments"]
    request = plan["selection"]["driver_request"]
    assert request["selection"]["arguments"] == dict(sequence="atgAAAtAA", min_length=0,
        search_reverse=True, filter_subsets=False)
    assert request["scientific_context"] == dict(subject_ref="engineering-subject",
        parent_mapping=call["frozen_operand"]["parent_mapping"])
    assert request["attempt_identity"]["execution_id"] == prepared["handle_path"]
    assert calls == [dict(command=molecular_sequence_adapter_argv(plan), cwd=str(root),
        policy=ordinary.POLICY, env=plan["selected_environment"])]
    env = plan["selected_environment"]
    assert "UNSELECTED_AMBIENT_VALUE" not in env
    assert env["PYTHONHOME"] == call["selected"]["software"]["python_home"]
    assert env["PYTHONPATH"] == ":".join(call["selected"]["software"]["import_roots"])
    assert all(env[key] == "1" for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONNOUSERSITE", "PYTHONSAFEPATH"))
    for key in ("TMPDIR", "TMP", "TEMP", "PYTHONPYCACHEPREFIX", "XDG_CACHE_HOME", "MPLCONFIGDIR"):
        assert Path(env[key]).is_relative_to(root)
    assert all(env[key] == str(root) for key in ("TMPDIR", "TMP", "TEMP"))
    assert json.loads((root / PLAN_FILENAME).read_bytes()) == plan
    call["frozen_operand"]["associations"]["engineering_fixture"] = False
    assert binding["frozen_operand"]["associations"]["engineering_fixture"] is True


def test_same_action_reuses_original_handle_without_new_reservation(selected_call):
    prepared, calls = _prepared(selected_call)
    original = Path(prepared["handle_path"]).read_bytes()
    assert ordinary.prepare_ordinary_orf_attempt(**selected_call[0]) == prepared
    assert len(calls) == 1
    assert Path(prepared["handle_path"]).read_bytes() == original


@pytest.mark.parametrize("change", ("arguments", "rows", "mapping", "associations", "context", "selection"))
def test_same_action_changed_selected_data_rejects_without_replacement(selected_call, change):
    prepared, calls = _prepared(selected_call)
    call = dict(selected_call[0])
    if change in ("arguments", "rows"):
        call["arguments"] = deepcopy(call["arguments"])
        if change == "arguments":
            call["arguments"]["min_length"] = 3
        else:
            call["arguments"]["rows"] = []
    elif change in ("mapping", "associations"):
        call["frozen_operand"] = deepcopy(call["frozen_operand"])
        key = "parent_mapping" if change == "mapping" else "associations"
        call["frozen_operand"][key]["changed_engineering_metadata"] = True
    elif change == "context":
        original = call["context"]
        call["context"] = BindingContext(run_id=original.run_id, episode_id=original.episode_id,
            role=original.role, path=original.path, scope={}, assignment={"different": True}, request={})
    else:
        call["selected"] = deepcopy(call["selected"])
        call["selected"]["resource_id"] = "different-engineering-resource"
    handle_raw = Path(prepared["handle_path"]).read_bytes()
    with pytest.raises(ValueError):
        ordinary.prepare_ordinary_orf_attempt(**call)
    assert len(calls) == 1
    assert Path(prepared["handle_path"]).read_bytes() == handle_raw


@pytest.mark.parametrize("change", ("extra_argument", "implicit_rows", "boolean_length", "subject", "identity",
    "mapping_absent", "mapping_failure", "mapping_failure_with_mapping", "extra_operand", "nonfinite", "environment", "policy"))
def test_invalid_input_controls_reject_before_reservation(selected_call, change):
    original, calls = selected_call
    call = dict(original, arguments=deepcopy(original["arguments"]),
        frozen_operand=deepcopy(original["frozen_operand"]), selected=deepcopy(original["selected"]))
    if change == "extra_argument":
        call["arguments"]["parent_mapping"] = {}
    elif change == "implicit_rows":
        del call["arguments"]["rows"]
    elif change == "boolean_length":
        call["arguments"]["min_length"] = True
    elif change == "subject":
        call["frozen_operand"]["subject"]["id"] = "different-subject"
    elif change == "identity":
        call["frozen_operand"]["sequence"] = "ATGAAATAA"
    elif change == "mapping_absent":
        call["frozen_operand"]["parent_mapping"] = None
    elif change == "mapping_failure":
        call["frozen_operand"]["parent_mapping"] = None
        call["frozen_operand"]["mapping_failure"] = {"code": "different_failure"}
    elif change == "mapping_failure_with_mapping":
        call["frozen_operand"]["mapping_failure"] = {"code": "subregion_mapping_unavailable"}
    elif change == "extra_operand":
        call["frozen_operand"]["caller_editable_mapping"] = {}
    elif change == "nonfinite":
        call["frozen_operand"]["associations"]["value"] = float("nan")
    elif change == "environment":
        call["selected"]["environment"]["extra"] = "not selected"
    else:
        call["policy"] = LocalJobPolicy(memory_bytes=ordinary.POLICY['memory_bytes'], scratch_bytes=ordinary.POLICY['scratch_bytes'] + 1)
    with pytest.raises(ValueError):
        ordinary.prepare_ordinary_orf_attempt(**call)
    assert calls == []


def test_known_unavailable_mapping_is_explicit_and_unchanged(selected_call):
    call, _calls = selected_call
    call["frozen_operand"]["parent_mapping"] = None
    call["frozen_operand"]["mapping_failure"] = {"code": "subregion_mapping_unavailable"}
    prepared = ordinary.prepare_ordinary_orf_attempt(**call)
    assert prepared["binding"]["frozen_operand"]["mapping_failure"] == {"code": "subregion_mapping_unavailable"}
    assert prepared["plan"]["selection"]["driver_request"]["scientific_context"]["parent_mapping"] is None


@pytest.mark.parametrize("filename", (ordinary.BINDING_FILENAME, ordinary.DRIVER_REQUEST_FILENAME, PLAN_FILENAME))
def test_missing_original_control_is_never_recreated(selected_call, filename):
    prepared, calls = _prepared(selected_call)
    path = Path(prepared["handle_path"]).parent / filename
    path.unlink()
    with pytest.raises(FileNotFoundError):
        ordinary.prepare_ordinary_orf_attempt(**selected_call[0])
    assert not path.exists()
    assert len(calls) == 1


@pytest.mark.parametrize("field", ("command", "cwd", "env", "file_bytes"))
def test_exact_original_native_sidecar_is_checked_even_with_updated_handle_hash(selected_call, field):
    prepared, calls = _prepared(selected_call)
    handle = Path(prepared["handle_path"])
    body = json.loads(handle.read_bytes())
    request = json.loads(Path(body["paths"]["request"]).read_bytes())
    request[field] = {"unexpected": "environment"} if field == "env" else 1 if field == "file_bytes" else "changed"
    _write(body["paths"]["request"], request)
    body["request_sha256"] = hashlib.sha256(Path(body["paths"]["request"]).read_bytes()).hexdigest()
    _write(handle, body)
    with pytest.raises(ValueError, match="original_native_request_conflict"):
        ordinary.prepare_ordinary_orf_attempt(**selected_call[0])
    assert len(calls) == 1


def test_orphan_attempt_directory_prevents_new_reservation(selected_call):
    call, calls = selected_call
    root = Path(call["selected"]["workspace"]) / ".episode-operations" / digest(
        {"run": call["context"].run_id, "episode": call["context"].episode_id}) / digest(call["operation_key"])
    (root / ATTEMPT_DIRECTORY).mkdir(parents=True)
    with pytest.raises(MolecularOperationUnpublished):
        ordinary.prepare_ordinary_orf_attempt(**call)
    assert calls == []


def test_run_rejects_changed_plan_pin_before_observing_or_releasing(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    prepared["plan_file"]["sha256"] = "0" * 64
    for name in ("status", "resume_start", "collect"):
        monkeypatch.setattr(ordinary.native, name,
            lambda *a, _name=name, **k: pytest.fail("unverified lifecycle API: " + _name))
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        ordinary.run_ordinary_orf_attempt(prepared)
    assert len(calls) == 1


def test_run_observes_original_lifecycle_without_cancelling_waiter(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    events = _lifecycle(monkeypatch, prepared, code=7)
    result = ordinary.run_ordinary_orf_attempt(prepared)
    assert events == ["status", "resume_start", "status", ("sleep", 0.05), "status", "collect", "status"]
    assert result["version"] == ordinary.EXECUTION_VERSION
    assert result["terminal"] is result["quiescent"] is True
    assert result["returncode"] == 7
    assert result["metadata"]["native_returncode"] == 7
    assert result["failure"] is None
    assert result["plan"] == prepared["plan"]
    assert result["handle"]["unit"] == "engineering-original.service"
    assert result["output_byte_validation"] == "deferred_to_result_owner"
    assert result["bundle"] is result["declaration"] is None
    assert result["declarations"] == {}
    assert len(calls) == 1


def test_already_set_cancellation_event_does_not_release_fresh_work(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    events = _lifecycle(monkeypatch, prepared, views=("prepared",))
    event = Event(); event.set()
    with pytest.raises(MolecularOperationUnpublished, match="observation_stopped"):
        ordinary.run_ordinary_orf_attempt(prepared, cancel_event=event)
    assert events == ["status"]
    assert json.loads(Path(prepared["handle_path"]).read_bytes())["stage"] == "prepared"
    assert len(calls) == 1


def test_cancellation_stops_only_observation_of_original_released_unit(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    events = _lifecycle(monkeypatch, prepared, views=("prepared", "running"))
    event = Event()
    def stop(delay):
        events.append(("sleep", delay)); event.set()
    monkeypatch.setattr(ordinary.time, "sleep", stop)
    with pytest.raises(MolecularOperationUnpublished, match="observation_stopped"):
        ordinary.run_ordinary_orf_attempt(prepared, cancel_event=event)
    body = json.loads(Path(prepared["handle_path"]).read_bytes())
    assert body["stage"] == "released" and Path(body["paths"]["release"]).exists()
    assert body["unit"] == "engineering-original.service"
    assert "collect" not in events and len(calls) == 1


@pytest.mark.parametrize("failure", (None, RuntimeError("engineered observation unavailable")))
def test_uncertain_observation_leaves_original_attempt_unpublished(selected_call, monkeypatch, failure):
    prepared, calls = _prepared(selected_call)
    original = Path(prepared["handle_path"]).read_bytes()
    events = _lifecycle(monkeypatch, prepared, views=("execution_unknown",), observation_error=failure)
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        ordinary.run_ordinary_orf_attempt(prepared)
    assert "resume_start" not in events and "collect" not in events
    assert Path(prepared["handle_path"]).read_bytes() == original
    assert len(calls) == 1


def test_closed_resource_failure_remains_a_real_failed_carrier(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    error = AcquisitionError("local_job_resource_limit", phase="local_execution",
        diagnostic={"engineering_fixture": True}, operational={"resource": "memory_bytes", "limit": 21474836480})
    _lifecycle(monkeypatch, prepared, views=("returned",), code=-9, collect_error=error)
    result = ordinary.run_ordinary_orf_attempt(prepared)
    assert result["returncode"] == -9
    assert result["failure"] == dict(code=error.code, phase=error.phase,
        diagnostic=error.diagnostic, operational=error.operational)
    assert result["bundle"] is None and "invocation_count" not in result
    assert len(calls) == 1


def _metadata_fixture(prepared):
    """Schema-valid engineered metadata, with no asserted scientific execution."""
    plan = prepared["plan"]
    root = Path(plan["attempt_directory"])
    output = root / OUTPUT_DIRECTORY
    output.mkdir(parents=True)
    declarations = {}
    for role in ("capture", "sheet", "components"):
        raw = _raw({"engineering_fixture": role})
        (output / (role + ".json")).write_bytes(raw)
        declarations[role] = dict(relative_path=role + ".json", format="json", state="present",
            sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    declaration = dict(version=ordinary.driver.DECLARATION_VERSION, mode="native", operation=ordinary.OPERATION,
        request_file={**plan["selection"]["request_file"], "path": str(root / REQUEST_RELATIVE)},
        request_file_pin_verified=True, attempt_identity=plan["selection"]["driver_request"]["attempt_identity"],
        native_call_state="not_invoked", native_failure=None, driver_failure=None,
        files=declarations, qualification="engineered metadata, not native scientific proof")
    _write(output / "declaration.json", declaration)
    files = []
    for role in BASE_ROLES:
        relative, fmt = output_specifications(plan)[role]
        path = root / relative
        observed = _pin(path, path.read_bytes()) if path.exists() else None
        declared = declarations.get(role)
        state = "present" if observed is not None else "absent"
        files.append(dict(role=role, relative_path=relative, format=fmt, observed_state=state,
            observed=observed, declared=deepcopy(declared), comparison="matches" if declared else "not_declared", failure=None))
    bundle = dict(version=BUNDLE_VERSION, plan_sha256=digest(plan), identity=plan["identity"],
        selected_payload_sha256=plan["selected_payload_sha256"],
        retained_inputs=dict(plan_file=_pin(root / OWNER_FILENAME, b"engineering owner metadata"),
            request=None, software_manifest=None), selected_request_file=plan["selection"]["request_file"],
        observed_request_file=None, private_asserted_attempt_identity=declaration["attempt_identity"],
        adapter_argv=molecular_sequence_adapter_argv(plan), private_driver_argv=None, cwd=str(root.parent),
        selected_environment=plan["selected_environment"], realized_environment=plan["selected_environment"],
        software_verification=dict(before="not_checked", after="not_checked", adapter_imported_files=[],
            inner_complete_import_closure_observed=False, failures=[]),
        invocation=dict(launch_attempt_count=0, invocation_count=0, pid=None, returncode=None,
            started_at=None, finished_at=None, process_exit_observed=False),
        files=files, failures=[], sealed=True)
    _write(root / BUNDLE_FILENAME, bundle)
    return bundle, declaration


@pytest.mark.parametrize("damage", ("changed", "missing"))
def test_one_role_byte_failure_does_not_discard_other_metadata(selected_call, monkeypatch, damage):
    prepared, _calls = _prepared(selected_call)
    bundle, declaration = _metadata_fixture(prepared)
    path = Path(prepared["plan"]["attempt_directory"]) / OUTPUT_DIRECTORY / "components.json"
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed engineering bytes")
    _lifecycle(monkeypatch, prepared, views=("returned",))
    result = ordinary.run_ordinary_orf_attempt(prepared)
    assert result["bundle"] == bundle
    assert result["declaration"] == declaration
    assert result["declarations"] == declaration["files"]
    assert result["metadata_failures"] == []
    assert result["bundle"]["invocation"]["invocation_count"] == 0
    assert result["output_byte_validation"] == "deferred_to_result_owner"


@pytest.mark.parametrize("damage", ("bundle", "declaration", "one_declaration_role"))
def test_bundle_and_declarations_fail_independently(selected_call, monkeypatch, damage):
    prepared, _calls = _prepared(selected_call)
    bundle, declaration = _metadata_fixture(prepared)
    root = Path(prepared["plan"]["attempt_directory"])
    if damage == "bundle":
        (root / BUNDLE_FILENAME).write_bytes(b"{malformed engineering metadata")
    elif damage == "declaration":
        (root / OUTPUT_DIRECTORY / "declaration.json").unlink()
    else:
        declaration["files"]["components"]["size_bytes"] = None
        _write(root / OUTPUT_DIRECTORY / "declaration.json", declaration)
    _lifecycle(monkeypatch, prepared, views=("returned",))
    result = ordinary.run_ordinary_orf_attempt(prepared)
    assert (result["bundle"] == bundle) is (damage != "bundle")
    if damage == "declaration":
        assert result["declaration"] is None and result["declarations"] == {}
    else:
        assert result["declaration"] == declaration
        assert result["declarations"]["capture"] == declaration["files"]["capture"]
        assert result["declarations"]["sheet"] == declaration["files"]["sheet"]
        assert ("components" in result["declarations"]) is (damage != "one_declaration_role")
    assert len(result["metadata_failures"]) == 1


def test_closed_reuse_does_not_recheck_or_replace_original_software(selected_call, monkeypatch):
    prepared, calls = _prepared(selected_call)
    for key in ("python", "software_files_file"):
        Path(selected_call[0]["selected"]["software"][key]["path"]).unlink()
    assert ordinary.prepare_ordinary_orf_attempt(**selected_call[0]) == prepared
    events = _lifecycle(monkeypatch, prepared, views=("returned",))
    result = ordinary.run_ordinary_orf_attempt(prepared)
    assert result["terminal"] and result["quiescent"]
    assert "resume_start" not in events and len(calls) == 1
