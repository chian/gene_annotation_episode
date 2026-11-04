"""Engineered controls for one ordinary HOMER reservation; no native science.

The deployment/handle/status records below are explicit protocol test doubles.
Received input bytes are the reusable 428 input fixture, never native results.
No test invokes a Perl helper, HOMER binary, scientific worker or systemd unit.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from threading import Event
from types import SimpleNamespace
import zipfile

import pytest

from gene_annotation_episode import native_homer_execution as e
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.local_jobs import LocalJobPolicy, LocalJobResult
from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(e._bytes(value))


def _pin(path):
    path = Path(path)
    return e._raw_pin(path, path.read_bytes())


def _copy_call(call):
    # BindingContext intentionally contains immutable mapping proxies.
    return {**call, **{key: deepcopy(call[key]) for key in ("arguments", "frozen_inputs", "selected")}}


@pytest.fixture
def selected_call(tmp_path, monkeypatch):
    """Actual immutable controls, with an explicitly non-executable runtime."""
    workspace, assets, software_root = (tmp_path / n for n in ("workspace", "assets", "software"))
    for directory in (workspace, assets, software_root): directory.mkdir()
    required = [*("deployment/bin/" + n for n in (*e.PATCH_NAMES, "homerTools", "homer2", "mergePeaks", "HomerSVGLogo.pm")),
        "deployment/config.txt", "selected_runtime/perl/bin/perl", "selected_runtime/elf/ld-linux-x86-64.so.2",
        "deployment/data/knownTFs/all/known.motifs", "deployment/data/knownTFs/vertebrates/known.motifs"]
    files = []
    for relative in required:
        path = assets / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("engineered identity only, never executed: " + relative + "\n").encode())
        path.chmod(0o444)
        pin = _pin(path)
        files.append(dict(relative_path=relative, sha256=pin["sha256"], size_bytes=pin["size_bytes"], mode=0o444))
    correction = assets / "engineered-correction.json"
    _write(correction, dict(engineering_only=True, native_execution=False))
    python = software_root / "engineering-python"
    python.write_bytes(b"engineering placeholder; must never execute\n")
    implementation = [Path(e.__file__).absolute(), Path(e.__file__).with_name("native_homer_worker.py").absolute()]
    inventory = software_root / "software-files.json"
    _write(inventory, dict(version="homer_native_software_files_v1", files=[_pin(python), *(_pin(p) for p in implementation)]))
    software = dict(version="homer_native_software_v1", python=_pin(python), python_home=str(software_root),
        python_version="engineering identity; not an interpreter", import_roots=[str(implementation[0].parent.parent)],
        software_files_file=_pin(inventory))
    deployment = dict(version="homer_native_deployment_v1", root=str(assets), files=files, system_files=[],
        corrections=dict(extractor_build_report=_pin(correction), svg_repair_record=_pin(correction)))
    binding = dict(version="homer_native_binding_v1", operation=e.OPERATION, variant=e.VARIANT,
        deployment=deployment, software=software, input_staging=dict(mode="verified_copy", max_total_bytes=1024 * 1024))
    frozen = []
    fixture = Path(__file__).with_name("fixtures") / "homer_v51_selected_region_inputs.zip"
    with zipfile.ZipFile(fixture) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for row, fmt in zip(manifest["files"], ("bed", "fasta", "bed")):
            raw = archive.read(row["member"])
            assert hashlib.sha256(raw).hexdigest() == row["sha256"] and len(raw) == row["size_bytes"]
            path = tmp_path / "received" / row["member"]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(raw)
            identity = dict(artifact_ref="artifact_" + row["sha256"], sha256=row["sha256"], size_bytes=len(raw), format=fmt)
            frozen.append(dict(role=row["role"], selection=dict(namespace="artifact", reference=identity["artifact_ref"]),
                file=identity, path=str(path)))
    context = BindingContext(run_id="engineered-homer-run", episode_id="engineered-science",
        role="scientific_process", path=(("scientific_process", "engineered-path"),),
        scope={"engineering": True}, assignment={"engineering": "one existing ordinary action"},
        request={"engineering": True}, received_record_refs=tuple(row["file"]["artifact_ref"] for row in frozen))
    call = dict(context=context, operation_key=context.run_id + ":" + context.episode_id + ":0",
        arguments=dict(window_bp=201, motif_lengths=[10, 8], num_motifs=0, threads=2, strand="forward",
            statistic="hypergeometric", normalization=dict(composition="cpg", oligo_length=2,
                max_iterations=37, neutral=True), motif_set="vertebrates"),
        frozen_inputs=dict(version="ordinary_homer_frozen_inputs_v1", inputs=frozen),
        selected=dict(resource_id="explicit-engineered-resource", binding_ordinal_0based=3,
            workspace=str(workspace), binding=binding, environment=deepcopy(e.ENVIRONMENT_SELECTION)),
        policy=LocalJobPolicy(**e.POLICY))
    calls = []

    def prepare(command, *, cwd, policy, handle_path, stdout_path, stderr_path, env):
        calls.append(dict(command=list(command), cwd=str(cwd), policy=policy.to_dict(), environment=deepcopy(env)))
        paths = {role: str(cwd / (".local-job-" + "1" * 32 + "." + role)) for role in e._NATIVE_PATHS}
        request = dict(command=list(command), cwd=str(cwd), file_bytes=policy.scratch_bytes,
            ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None, env=env)
        _write(paths["request"], request)
        Path(stdout_path).write_bytes(b""); Path(stderr_path).write_bytes(b"")
        body = dict(version=e.native.VERSION, unit="engineered-original-only.service", command=list(command), cwd=str(cwd),
            stdout=str(stdout_path), stderr=str(stderr_path), paths=paths, metadata=dict(policy=policy.to_dict(), engineering_only=True),
            stage="prepared", started_at=None, started_monotonic_ns=None, boot_id=None,
            request_sha256=_pin(paths["request"])["sha256"])
        _write(handle_path, body)
        return e.native.NativeJobHandle(Path(handle_path))

    monkeypatch.setattr(e.native, "prepare_job", prepare)
    for name in ("wait_job", "cancel", "release", "start_job", "run_blocking"):
        monkeypatch.setattr(e.native, name,
            lambda *a, _name=name, **k: pytest.fail("forbidden lifecycle operation: " + _name))
    return call, calls


def _lifecycle(monkeypatch, *, states=("prepared", "running", "returned"), code=0, error=None):
    events, ordinal = [], [0]
    metadata = dict(policy=deepcopy(e.POLICY), native_returncode=code, engineering_only=True)

    def status(handle):
        events.append("status")
        if error is not None: raise error
        state = states[min(ordinal[0], len(states) - 1)]
        ordinal[0] += 1
        return dict(state=state, terminal=state == "returned", quiescent=state in ("prepared", "returned", "execution_unknown"),
            metadata=deepcopy(metadata))

    def resume(handle):
        events.append("resume_start")
        body = handle.read(); body["stage"] = "released"
        _write(handle.path, body); Path(body["paths"]["release"]).touch()

    def collect(handle):
        events.append("collect")
        body = handle.read()
        return LocalJobResult(code, Path(body["stdout"]), Path(body["stderr"]), deepcopy(metadata))

    monkeypatch.setattr(e.native, "status", status)
    monkeypatch.setattr(e.native, "resume_start", resume)
    monkeypatch.setattr(e.native, "collect", collect)
    monkeypatch.setattr(e.time, "sleep", lambda delay: events.append(("sleep", delay)))
    return events


def _metadata(prepared):
    """A no-wrapper-invocation completion, not a scientific success carrier."""
    plan = prepared["plan"]; root = Path(plan["attempt_directory"])
    root.mkdir()
    completion = dict(version=e.COMPLETION_VERSION, identity=plan["identity"], request_file=plan["request_file"],
        selected_payload_sha256=plan["selected_payload_sha256"], wrapper_started_file=None, realization_file=None,
        wrapper=dict(**e.homer_native_invocation(plan), started_at=None, finished_at="engineered-no-call",
            returncode=None, outcome="not_started"), stdout=None, stderr=None,
        failure=e.failure_record("engineered_before_wrapper", "engineering_control"))
    _write(root / e.COMPLETION_FILENAME, completion)
    rows = [dict(row, observed_state="absent", sha256=None, size_bytes=None, failure=None)
        for row in e.homer_output_specifications(plan)]
    manifest = dict(version=e.MANIFEST_VERSION, identity=plan["identity"], selected_payload_sha256=plan["selected_payload_sha256"],
        completion_file=_pin(root / e.COMPLETION_FILENAME), files=rows, other_files=[], failures=[],
        execution=dict(wrapper_returncode=None, wrapper_outcome="not_run", known_outcome="not_run", denovo_outcome="not_run"))
    _write(root / e.OUTPUT_MANIFEST_FILENAME, manifest)
    return completion, manifest


def test_explicit_binding_ordinal_science_and_native_cache_are_preserved(selected_call):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    plan = prepared["plan"]
    assert plan["identity"]["binding_ordinal_0based"] == 3
    assert plan["identity"]["resource_id"] == call["selected"]["resource_id"]
    assert plan["request"]["arguments"] == call["arguments"]
    assert plan["request"]["frozen_inputs"] == call["frozen_inputs"]
    wrapper = e.homer_native_invocation(plan)
    argv = wrapper["argv"]
    for flag, value in (("-size", "201"), ("-len", "10,8"), ("-S", "0"), ("-p", "2"), ("-nlen", "2"), ("-nmax", "37")):
        assert argv[argv.index(flag) + 1] == value
    assert all(flag in argv for flag in ("-h", "-norevopp", "-neutral", "-cpg", "-useOldBg", "-keepFiles"))
    assert argv[argv.index("-preparsedDir") + 1] == str(Path(plan["attempt_directory"]) / "preparsed")
    assert call["frozen_inputs"]["inputs"][1]["path"] not in argv
    assert calls[0]["policy"] == e.POLICY and len(calls) == 1


def test_advertised_motif_sets_come_only_from_selected_inventory(selected_call, monkeypatch):
    call, _ = selected_call
    binding = call["selected"]["binding"]
    monkeypatch.setattr(e, "file_pin", lambda *a, **k: pytest.fail("pure schema opened a file"))
    assert e.homer_motif_sets(binding) == ["all", "vertebrates", "auto"]
    schema = e.homer_execution_schema("Arguments", binding=binding)
    assert schema["properties"]["motif_set"]["enum"] == ["all", "vertebrates", "auto"]
    assert schema["additionalProperties"] is False
    assert e.validate_homer_bindings([binding]) == [binding]


@pytest.mark.parametrize("change", ["ordinal_float", "motif_set", "variant", "staging", "bool_threads"])
def test_invalid_selected_controls_reject_before_reservation(selected_call, change):
    call, calls = selected_call
    call = _copy_call(call)
    if change == "ordinal_float": call["selected"]["binding_ordinal_0based"] = 3.0
    elif change == "motif_set": call["arguments"]["motif_set"] = "not-in-selected-inventory"
    elif change == "variant": call["selected"]["binding"]["variant"] = "unverified-installed-genome"
    elif change == "staging": call["selected"]["binding"]["input_staging"]["max_total_bytes"] = 1
    else: call["arguments"]["threads"] = True
    with pytest.raises(ValueError): e.prepare_ordinary_homer_attempt(**call)
    assert calls == []


def test_same_action_recovers_exact_original_handle_without_reserving_again(selected_call):
    call, calls = selected_call
    first = e.prepare_ordinary_homer_attempt(**call)
    second = e.prepare_ordinary_homer_attempt(**call)
    assert first == second and len(calls) == 1
    assert json.loads(Path(first["handle_path"]).read_bytes())["unit"] == "engineered-original-only.service"


@pytest.mark.parametrize("change", ["arguments", "request", "binding_ordinal", "frozen_file"])
def test_same_action_changed_data_never_replaces_original(selected_call, change):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    before = Path(prepared["handle_path"]).read_bytes()
    changed = _copy_call(call)
    if change == "arguments": changed["arguments"]["window_bp"] += 1
    elif change == "request": changed["context"] = replace(call["context"], request={"changed": True})
    elif change == "binding_ordinal": changed["selected"]["binding_ordinal_0based"] += 1
    else: changed["frozen_inputs"]["inputs"][0]["selection"]["reference"] = "changed-original-selection"
    with pytest.raises(ValueError): e.prepare_ordinary_homer_attempt(**changed)
    assert Path(prepared["handle_path"]).read_bytes() == before and len(calls) == 1


@pytest.mark.parametrize("change", ["plan", "native_sidecar", "handle_policy"])
def test_changed_original_controls_deny_before_status_or_release(selected_call, monkeypatch, change):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    body = json.loads(Path(prepared["handle_path"]).read_bytes())
    if change == "plan":
        owned_plan = Path(prepared["plan_file"]["path"])
        owned_plan.chmod(0o600)
        owned_plan.write_bytes(b"{}\n")
    elif change == "native_sidecar":
        request = json.loads(Path(body["paths"]["request"]).read_bytes()); request["env"]["INJECTED"] = "1"
        _write(body["paths"]["request"], request)
        body["request_sha256"] = _pin(body["paths"]["request"])["sha256"]
        _write(prepared["handle_path"], body)
    else:
        body["metadata"]["policy"]["wall_seconds"] = 1
        _write(prepared["handle_path"], body)
    monkeypatch.setattr(e.native, "status", lambda *a: pytest.fail("observed changed controls"))
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        e.run_ordinary_homer_attempt(prepared)
    assert len(calls) == 1


def test_observer_stops_preserving_original_released_unit(selected_call, monkeypatch):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    events = _lifecycle(monkeypatch, states=("prepared", "running"))
    event = Event()
    def stop(delay): events.append(("sleep", delay)); event.set()
    monkeypatch.setattr(e.time, "sleep", stop)
    with pytest.raises(MolecularOperationUnpublished, match="observation_stopped"):
        e.run_ordinary_homer_attempt(prepared, cancel_event=event)
    body = json.loads(Path(prepared["handle_path"]).read_bytes())
    assert body["stage"] == "released" and Path(body["paths"]["release"]).exists()
    assert body["unit"] == "engineered-original-only.service" and len(calls) == 1 and "collect" not in events


def test_already_stopped_observer_does_not_release_fresh_unit(selected_call, monkeypatch):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    events = _lifecycle(monkeypatch)
    event = Event(); event.set()
    with pytest.raises(MolecularOperationUnpublished, match="observation_stopped"):
        e.run_ordinary_homer_attempt(prepared, cancel_event=event)
    assert events == ["status"] and len(calls) == 1


def test_observer_stopped_during_software_verification_does_not_release_fresh_unit(selected_call, monkeypatch):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    events = _lifecycle(monkeypatch)
    event = Event()
    def verify(plan): event.set()
    monkeypatch.setattr(e, "verify_homer_start_inputs", verify)
    with pytest.raises(MolecularOperationUnpublished, match="observation_stopped"):
        e.run_ordinary_homer_attempt(prepared, cancel_event=event)
    assert events == ["status"] and len(calls) == 1


@pytest.mark.parametrize("error", [None, RuntimeError("engineered unavailable observation")])
def test_uncertain_original_unit_is_not_replaced_or_invented_closed(selected_call, monkeypatch, error):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    events = _lifecycle(monkeypatch, states=("execution_unknown",), error=error)
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        e.run_ordinary_homer_attempt(prepared)
    assert "resume_start" not in events and "collect" not in events and len(calls) == 1


@pytest.mark.parametrize("role,damage", [("completion", "missing"), ("completion", "invalid"),
    ("output_manifest", "missing"), ("output_manifest", "invalid")])
def test_metadata_controls_validate_independently(selected_call, role, damage):
    call, _ = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    completion, manifest = _metadata(prepared)
    root = Path(prepared["plan"]["attempt_directory"])
    path = root / (e.COMPLETION_FILENAME if role == "completion" else e.OUTPUT_MANIFEST_FILENAME)
    if damage == "missing": path.unlink()
    else: path.write_bytes(b'{"broken":')
    result = e.read_homer_attempt_metadata(prepared["plan"])
    assert result[role] is None and result[role + "_file"] is None
    sibling = "output_manifest" if role == "completion" else "completion"
    assert result[sibling] == (manifest if sibling == "output_manifest" else completion)
    assert len(result["metadata_failures"]) == 1
    assert result["metadata_failures"][0]["role"] == role
    assert result["execution"]["wrapper_returncode"] is None


def test_raw_metadata_adapter_rejects_available_original_carrier_disagreement(selected_call):
    call, _ = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    completion, manifest = _metadata(prepared)
    root = Path(prepared["plan"]["attempt_directory"])
    retained = {str(root / name): (root / name).read_bytes() for name in (e.COMPLETION_FILENAME, e.OUTPUT_MANIFEST_FILENAME)}
    forged = deepcopy(manifest); forged["identity"]["operation_key"] += "-other"
    retained[str(root / e.OUTPUT_MANIFEST_FILENAME)] = e._bytes(forged)
    result = e.read_homer_attempt_metadata(prepared["plan"], read_bytes=lambda p: retained[str(p)])
    assert result["completion"] == completion and result["output_manifest"] is None
    assert result["metadata_failures"][0]["code"] == "output_manifest_invalid"


def test_closed_collection_preserves_outer_code_and_unavailable_metadata_without_zero_calls(selected_call, monkeypatch):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    events = _lifecycle(monkeypatch, code=7)
    result = e.run_ordinary_homer_attempt(prepared)
    assert result["returncode"] == 7 and result["terminal"] is result["quiescent"] is True
    assert result["completion"] is result["output_manifest"] is None
    assert result["execution"] == dict(wrapper_returncode=None, wrapper_outcome="unknown", known_outcome="unknown", denovo_outcome="unknown")
    assert result["output_byte_validation"] == "deferred_to_result_owner"
    assert events == ["status", "resume_start", "status", ("sleep", .05), "status", "collect", "status"]
    assert len(calls) == 1


def test_selected_inventory_must_include_actual_entry_modules(selected_call):
    call, _ = selected_call
    software = call["selected"]["binding"]["software"]
    inventory = Path(software["software_files_file"]["path"])
    _write(inventory, dict(version="homer_native_software_files_v1", files=[software["python"]]))
    software["software_files_file"] = _pin(inventory)
    with pytest.raises(e.HomerPreflightRejected) as rejected:
        e.prepare_ordinary_homer_attempt(**call)
    assert "software_inventory_entry_closure_missing" in str(rejected.value.__cause__)


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_fresh_missing_or_changed_deployment_proves_preflight_rejection_before_reservation(selected_call, damage):
    call, calls = selected_call
    path = Path(call["selected"]["binding"]["deployment"]["root"]) / "deployment/bin/findMotifsGenome.pl"
    if damage == "missing": path.unlink()
    else:
        path.chmod(0o644); path.write_bytes(b"changed engineered selected bytes\n")
    with pytest.raises(e.HomerPreflightRejected):
        e.prepare_ordinary_homer_attempt(**call)
    assert calls == []
    assert not list(Path(call["selected"]["workspace"]).rglob("native.json"))
    assert not list(Path(call["selected"]["workspace"]).rglob(".local-job-*"))


def test_missing_selected_asset_cannot_reclassify_existing_original_unit_as_fresh_preflight(selected_call, monkeypatch):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    original = Path(prepared["handle_path"]).read_bytes()
    path = Path(call["selected"]["binding"]["deployment"]["root"]) / "deployment/bin/findMotifsGenome.pl"
    path.unlink()
    assert e.prepare_ordinary_homer_attempt(**call) == prepared
    events = _lifecycle(monkeypatch, states=("prepared",))
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        e.run_ordinary_homer_attempt(prepared)
    assert events == ["status", "status"] and Path(prepared["handle_path"]).read_bytes() == original
    assert len(calls) == 1


def test_orphan_original_controls_precede_fresh_preflight_classification(selected_call):
    call, calls = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    root = Path(prepared["plan"]["operation_directory"])
    Path(prepared["handle_path"]).unlink()
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(MolecularOperationUnpublished, match="original_attempt_unconfirmed"):
        e.prepare_ordinary_homer_attempt(**call)
    assert {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert len(calls) == 1


def test_selected_interpreter_rejects_unlisted_outside_module_and_accepts_explicit_pin(selected_call, monkeypatch):
    call, _ = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    plan = prepared["plan"]
    outside = Path(call["selected"]["workspace"]).parent / "outside-declared-import-roots.py"
    outside.write_bytes(b"# engineering module identity, never imported or executed\n")
    # Isolate this finite closure condition without changing Python's real
    # global sys.modules or executing the placeholder selected interpreter.
    monkeypatch.setattr(e, "sys", SimpleNamespace(executable=plan["software"]["python"]["path"],
        modules={"engineered_outside_module": SimpleNamespace(__file__=str(outside))}))
    # Host preparation does not select or validate unrelated host modules,
    # even when it uses the same Python executable as the native worker.
    e.verify_homer_start_inputs(plan)
    with pytest.raises(ValueError, match="verify_loaded_flag_invalid"):
        e.verify_homer_start_inputs(plan, verify_loaded=1)
    with pytest.raises(ValueError, match="software_inventory_loaded_module_missing"):
        e.verify_homer_start_inputs(plan, verify_loaded=True)
    inventory = Path(plan["software"]["software_files_file"]["path"])
    declared = json.loads(inventory.read_bytes())
    declared["files"].append(_pin(outside)); _write(inventory, declared)
    plan["software"]["software_files_file"] = _pin(inventory)
    e.verify_homer_start_inputs(plan, verify_loaded=True)


def test_final_motif_files_have_native_numeric_rank_and_other_representations_stay_separate(selected_call):
    from gene_annotation_episode import native_homer_worker as worker
    call, _ = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    completion, _manifest = _metadata(prepared)
    root = Path(prepared["plan"]["attempt_directory"])
    final = root / "native/homerResults"; final.mkdir(parents=True)
    for name in ("motif10.motif", "motif2.motif", "motif1.motif", "motif1RV.motif", "motif1.similar1.motif"):
        (final / name).write_bytes(("engineered byte-custody file: " + name + "\n").encode())
    manifest = worker._inventory_native(prepared["plan"], completion, _pin(root / e.COMPLETION_FILENAME))
    scientific = [row["native_relative_path"] for row in manifest["files"] if row["role"] == "denovo_nonredundant_pwm"]
    assert scientific == ["native/homerResults/motif1.motif", "native/homerResults/motif2.motif", "native/homerResults/motif10.motif"]
    assert {row["native_relative_path"] for row in manifest["other_files"]} == {
        "native/homerResults/motif1RV.motif", "native/homerResults/motif1.similar1.motif"}
    assert all(row["native_relative_path"] != "native/nonRedundant.motifs" for row in manifest["files"])
    # No helper was invoked; this explicitly engineered inventory cannot claim
    # a successful scientific branch merely because it contains motif files.
    assert manifest["execution"]["known_outcome"] == manifest["execution"]["denovo_outcome"] == "not_run"


def test_present_empty_output_is_retained_without_scientific_success_or_failure_inference(selected_call):
    from gene_annotation_episode import native_homer_worker as worker
    call, _ = selected_call
    prepared = e.prepare_ordinary_homer_attempt(**call)
    completion, _manifest = _metadata(prepared)
    root = Path(prepared["plan"]["attempt_directory"])
    (root / "native").mkdir()
    (root / "native/knownResults.txt").write_bytes(b"")
    manifest = worker._inventory_native(prepared["plan"], completion, _pin(root / e.COMPLETION_FILENAME))
    row = next(row for row in manifest["files"] if row["role"] == "known_results")
    assert row["observed_state"] == "present" and row["size_bytes"] == 0
    assert row["sha256"] == hashlib.sha256(b"").hexdigest() and row["failure"] is None


def test_explicit_empty_initial_selection_preserves_population_only_and_no_invented_series():
    from gene_annotation_episode import native_homer_worker as worker
    # This helper resolves metadata only; it does not invoke the calculator.
    sheet = dict(files=[], series=[], issues=[])
    assert worker._initial_selector(sheet, dict(series=[], offset=0, limit=0)) == dict(series_ids=[], offset=0, limit=0)
    assert sheet == dict(files=[], series=[], issues=[])


def test_literal_selected_libstdcpp_members_are_valid_deployment_data_without_relaxing_command_paths(selected_call, monkeypatch):
    call, calls = selected_call
    binding = deepcopy(call['selected']['binding'])
    # Exact metadata from the already retained 428 ELF closure; no native
    # library is loaded and no producing scientific attempt is asserted here.
    for name in ('libstdc++.so.6', 'libstdc++.so.6.0.35'):
        relative = 'selected_runtime/elf/' + name
        binding['deployment']['files'].append(dict(relative_path=relative,
            sha256='5bb0d21308f123b6ad46c6f35b42cedfcb8d6d439a53aa3dae04d880aaffdde3',
            size_bytes=2735712, mode=0o644))
        with pytest.raises(ValueError, match='native_relative_path_invalid'):
            e._relative(relative)
    monkeypatch.setattr(e, 'file_pin', lambda *a, **k: pytest.fail('metadata validator opened a native asset'))
    assert e.validate_homer_bindings([binding]) == [binding]
    assert calls == []


@pytest.mark.parametrize('relative', ['../selected_runtime/elf/libstdc++.so.6',
    '/selected_runtime/elf/libstdc++.so.6', 'selected_runtime/elf/../libstdc++.so.6',
    'selected_runtime//elf/libstdc++.so.6', 'selected_runtime/elf/libstdc++.so.6\n',
    'selected_runtime/elf/libstdc++.so.6;other', 'selected_runtime\\elf\\libstdc++.so.6'])
def test_deployment_member_data_keeps_traversal_and_shell_token_denials(selected_call, relative):
    call, calls = selected_call
    binding = deepcopy(call['selected']['binding'])
    binding['deployment']['files'].append(dict(relative_path=relative, sha256='a' * 64, size_bytes=0, mode=0o644))
    with pytest.raises(ValueError): e.validate_homer_bindings([binding])
    assert calls == []


def test_deployment_member_plus_does_not_relax_actual_workspace_shell_restriction(selected_call):
    call, calls = selected_call
    call = _copy_call(call)
    call['selected']['workspace'] += '+not-shell-path-policy'
    with pytest.raises(ValueError, match='native_workspace_not_shell_safe'):
        e.prepare_ordinary_homer_attempt(**call)
    assert calls == []


def test_copying_a_plus_named_data_member_preserves_exact_bytes_and_rejects_symlink(tmp_path):
    from gene_annotation_episode import native_homer_worker as worker
    source = tmp_path / 'selected-libstdc++.so.6'
    source.write_bytes(b'engineering data-copy bytes only; never loaded\n')
    selected = _pin(source)
    target = tmp_path / 'owned-libstdc++.so.6'
    actual = worker._copy_selected(selected, target, mode=0o444)
    assert actual == dict(path=str(target), sha256=selected['sha256'], size_bytes=selected['size_bytes'])
    assert target.read_bytes() == source.read_bytes()
    alias = tmp_path / 'alias-libstdc++.so.6'; alias.symlink_to(source)
    forbidden_target = tmp_path / 'not-created-libstdc++.so.6'
    with pytest.raises((OSError, ValueError)):
        worker._copy_selected(dict(selected, path=str(alias)), forbidden_target, mode=0o444)
    assert not forbidden_target.exists() and _pin(source) == selected
