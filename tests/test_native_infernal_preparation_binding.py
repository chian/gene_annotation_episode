"""Configured preparation jobs use the actual practical episode operations."""
import asyncio
import base64
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.native_infernal_preparation_job_schema import NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA
from gene_annotation_episode.native_infernal_preparation_local import local_infernal_preparation_plan
from gene_annotation_episode.native_infernal_preparation_tool_info import (
    native_infernal_preparation_tool_contracts, native_infernal_preparation_tool_information,
    validate_native_infernal_preparation_bindings,
)
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import ASSIGNMENT_SCHEMA, validate_assignment
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from test_native_infernal_preparation_driver import CASES, POLICY, native_job


def configured(tmp_path, program="cmemit", mode="consensus"):
    job = native_job(program, mode)
    config = {"kind": "local", "workspace": str(tmp_path), "policy": POLICY.to_dict(),
        "native_infernal_preparation": [{key: job[key] for key in ("program", "mode", "software")}]}
    return job, config


def assigned(tmp_path, job):
    run_id, episode_id, key = "binding247", "local-preparation", "selected-native-job"
    root = tmp_path / ".episode-operations" / native_infernal_digest({
        "run": run_id, "episode": episode_id}) / native_infernal_digest(key)
    attempt = root / "infernal-preparation-attempt"
    assignment = {"version": "practical_assignment_v1", "assignment_id": "prepare-model",
        "resource_kind": "local", "resource_id": "local247", "workspace": str(tmp_path),
        "endpoint": "completed_job_outputs", "requested_job": requested_job_from_infernal_preparation(job),
        "progress_requirements": [{"key": "outputs", "credit": 7,
            "predicate": {"kind": "requested_job_outputs", "output_paths": [
                str(attempt / row["relative_path"]) for row in job["outputs"]]}}],
        "completion_keys": ["outputs"], "initial_context": {"revision": 0,
            "cwd": str(tmp_path), "environment": {}}, "inventory_snapshot": {},
        "constraints": {"allocation": POLICY.to_dict()}}
    return SimpleNamespace(run_id=run_id, episode_id=episode_id, role="launch_local",
        assignment=assignment, scope={}), key, attempt


@pytest.mark.parametrize("case", CASES, ids=[row["program"] + "-" + row["mode"] for row in CASES])
def test_all_native_mode_requests_have_real_configured_four_field_information(tmp_path, case):
    job, config = configured(tmp_path, case["program"], case["mode"])
    bindings = config["native_infernal_preparation"]
    entries = native_infernal_preparation_tool_contracts(bindings, resource_kind="local", resource_id="local247")
    information = native_infernal_preparation_tool_information(bindings, resource_kind="local", resource_id="local247")
    assert len(entries) == len(information) == 1
    assert set(information[0]) == {"name", "description", "resources", "instructions"}
    assert information[0]["name"] == "native." + case["program"] + "." + case["mode"]
    assert "practical.job.start" in information[0]["instructions"]
    assert entries[0]["invocation_route"] == {"kind": "commission", "routes": [{
        "entry_role": "launch", "resource_id": "local247", "resource_role": "launch_local"}]}
    request = requested_job_from_infernal_preparation(job)
    for schema in (NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA, entries[0]["input_schema"]):
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(request)
    context, _, _ = assigned(tmp_path, job)
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(context.assignment)
    assert validate_assignment(context.assignment) == context.assignment
    LocalPracticalOperations(config).validate_assignment(context.assignment)


@pytest.mark.parametrize("fault", ["program", "mode", "software", "binding_missing", "resource", "resource_kind", "allocation", "argv", "environment"])
def test_unbound_or_changed_request_rejected_before_reservation(tmp_path, fault):
    job, config = configured(tmp_path)
    context, _, _ = assigned(tmp_path, job)
    request = context.assignment["requested_job"]
    if fault in {"program", "mode", "software"}:
        bound = config["native_infernal_preparation"][0]
        if fault == "program":
            bound["program"], bound["mode"] = "cmstat", "summary"
        elif fault == "mode":
            bound["mode"] = "sample_unaligned"
        else:
            bound["software"]["sha256"] = "0" * 64
    elif fault == "binding_missing":
        config.pop("native_infernal_preparation")
    elif fault == "resource":
        context.assignment.pop("resource_id")
    elif fault == "resource_kind":
        context.assignment["resource_kind"] = "hpc"
    elif fault == "allocation":
        context.assignment["constraints"]["allocation"]["memory_bytes"] -= 1
    elif fault == "argv":
        request["argv"][0] = "/bin/true"
    else:
        request["environment"]["INFERNAL_NCPU"] = "90"
    with pytest.raises(ValueError):
        LocalPracticalOperations(config).validate_assignment(context.assignment)
    assert not (tmp_path / ".episode-operations").exists()


@pytest.mark.parametrize("fault", ["extra", "ordinal", "format", "key", "reserved_environment", "unknown_parameter"])
def test_typed_callable_schema_rejects_malformed_field_populations(tmp_path, fault):
    job, _ = configured(tmp_path)
    request = requested_job_from_infernal_preparation(job)
    selected = request["native_infernal_preparation"]
    if fault == "extra":
        selected["unscoped_task"] = "invented"
    elif fault == "ordinal":
        selected["operands"][0]["ordinal"] = False
    elif fault == "format":
        selected["operands"][0]["format"] = "invented"
    elif fault == "key":
        selected["key"] = "not_a_fetch"
    elif fault == "reserved_environment":
        selected["environment"]["TMPDIR"] = "/outside"
    else:
        selected["grading_parameters"]["confidence"] = .99
    assert list(Draft202012Validator(NATIVE_INFERNAL_PREPARATION_REQUESTED_JOB_SCHEMA).iter_errors(request))


def test_binding_never_claims_an_unimplemented_resource_or_duplicate_mode(tmp_path):
    _, config = configured(tmp_path)
    rows = config["native_infernal_preparation"]
    for resource in ("hpc", "api"):
        with pytest.raises(ValueError, match="resource_binding_unfinished"):
            native_infernal_preparation_tool_contracts(rows, resource_kind=resource, resource_id="other")
    with pytest.raises(ValueError, match="duplicate_bound_mode"):
        validate_native_infernal_preparation_bindings(rows + rows)


@pytest.mark.parametrize("program,mode", [("cmemit", "consensus"), ("cmbuild", "build"),
    ("cmcalibrate", "calibrate"), ("cmfetch", "key_file"), ("cmpress", "press")])
def test_actual_practical_action_stages_runs_observes_and_replays_original_job(tmp_path, monkeypatch, program, mode):
    job, config = configured(tmp_path, program, mode)
    context, operation_key, attempt = assigned(tmp_path, job)
    binding = PracticalResourceEpisodes(None, directory=tmp_path / "episodes", resources={"local": config})
    state = binding.initialize(context)
    assert state.completion_proof() is None and state.receipts() == []
    started = asyncio.run(binding.execute(context, "practical.job.start", {}, operation_key))
    assert started["status"] == "completed", started
    handle = native.NativeJobHandle(Path(started["result"]["outcome"]["facts"]["requested_job"]["execution_id"]))
    # The test explicitly waits for its selected native job. This is not a
    # hidden episode action, automatic poll itinerary, or production loop.
    native_result = native.wait_job(handle)
    assert native_result.returncode == 0, native_result.stderr_path.read_text()
    assert native_result.metadata["verified_cgroup"]["memory_max"] == POLICY.memory_bytes
    assert 'runtime_max' not in native_result.metadata["verified_cgroup"]
    plan = local_infernal_preparation_plan(context.assignment, str(handle.path))
    assert Path(plan["attempt_directory"]) == attempt
    assert handle.read()["command"][1:3] == ["-m", "gene_annotation_episode.native_infernal_preparation_driver"]
    bundle = json.loads((attempt / "bundle.json").read_bytes())
    assert bundle["returncode"] == 0 and bundle["failures"] == []
    assert all(row["expected_sha256"] == row["staged_sha256"] == row["final_sha256"] for row in bundle["inputs"])
    observed = LocalPracticalOperations(config).observe_execution(context.assignment, str(handle.path),
        log_window_bytes=4096, log_roles=("stdout", "stderr"))
    assert observed["state"] == "completed" and observed["result_available"]
    assert any(row["role"] == "native_infernal_preparation_bundle" for row in observed["outputs"])
    for log in observed["logs"]:
        raw = Path(log["path"]).read_bytes()
        assert Path(log["path"]).is_relative_to(attempt)
        assert base64.b64decode(log["bytes_base64"]) == raw[log["offset"]:]
    if state.completion_proof() is None:
        collected = asyncio.run(binding.execute(context, "practical.job.collect", {}, "selected-output-check"))
        assert collected["status"] == "completed"
    proof = state.completion_proof()
    assert proof and state.verify_completion(proof)
    receipts = state.receipts()
    assert len(receipts) in (1, 2)
    assert all(row["tool_name"] in {"practical.job.start", "practical.job.collect"} for row in receipts)
    assert state.credit_view()["satisfied_keys"] == ["outputs"]
    monkeypatch.setattr(LocalPracticalOperations, "execute", lambda *a, **k: pytest.fail("replay executed native work"))
    assert asyncio.run(binding.execute(context, "practical.job.start", {}, operation_key)) == started
    assert state.receipts() == receipts
    (tmp_path / "binding-evidence.json").write_text(json.dumps({"program": program, "mode": mode,
        "plan": plan, "observed": observed, "receipts": receipts, "completion": proof,
        "native_policy": native_result.metadata}, indent=2) + "\n")
