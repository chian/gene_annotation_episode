"""Synthetic faults and retained real bounded runs; native jobs are not repeated."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import (
    native_infernal_digest, output_contract, requested_job_from_infernal,
)
from gene_annotation_episode.native_infernal_driver import (
    main, run_native_infernal, validate_native_infernal_bundle_files,
)
from gene_annotation_episode.native_infernal_local import local_infernal_plan, prepare_local_infernal
from gene_annotation_episode.practical_execution_state import _immutable


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/native_infernal_execution"
RETAINED = ROOT / "verification/tool_graders_infernal_native_execution_2026-10-26_222/runs"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def _file(path, role, fmt):
    raw = path.read_bytes()
    return {"role": role, "path": str(path), "format": fmt, "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw), "artifact_ref": "source_supplied_" + role}


def plan_for(tmp_path, program="cmsearch"):
    executable = tmp_path / "synthetic-executable"
    executable.write_text("synthetic test only; process call is replaced\n")
    executable.chmod(0o700)
    model = tmp_path / "models.cm"
    model.write_bytes((FIXTURES / "synthetic_model.cm").read_bytes())
    sequences = tmp_path / "sequences.fa"
    sequences.write_bytes((FIXTURES / "synthetic_sequences.fa").read_bytes())
    operands = [_file(model, "models", "infernal_ascii"), _file(sequences, "sequences", "fasta")]
    if program == "cmscan":
        for suffix in ("i1f", "i1i", "i1m", "i1p"):
            path = Path(str(model) + "." + suffix)
            path.write_bytes(b"synthetic pressed-index placeholder; not scientific data\n")
            operands.append(_file(path, "models_" + suffix, "infernal_" + suffix))
    outputs = [{"role": role, "format": fmt, "relative_path": "outputs/" + role + ".out"}
        for role, fmt in output_contract(program)[0].items()]
    job = {"version": "native_infernal_job_v1", "program": program,
        "software": {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "engine_version": "synthetic declaration"}, "environment": {"LC_ALL": "C"},
        "operands": operands, "operand_bindings": [{"operand_role": "sequences", "record_ordinal": 0,
            "native_name": "synthetic", "native_accession": None, "subject_ref": "subject_original",
            "reference_ref": None}], "options": ["--cpu", "1"], "outputs": outputs,
        "table_format": None if program == "cmalign" else 1, "metadata": {}, "grading_parameters": {}}
    request = requested_job_from_infernal(job)
    return {"version": "native_infernal_run_plan_v1", "identity": {"run_id": "synthetic-run",
        "episode_id": "local-child", "resource_id": "local", "execution_id": str(tmp_path / "native.json"),
        "attempt_id": native_infernal_digest("selected-start"), "operation_key": "selected-start",
        "requested_job_sha256": native_infernal_digest(request)}, "requested_job": request,
        "attempt_directory": str(tmp_path / "infernal-attempt"), "policy": POLICY.to_dict()}


def _reseal(plan):
    plan["requested_job"] = requested_job_from_infernal(plan["requested_job"]["native_infernal"])
    plan["identity"]["requested_job_sha256"] = native_infernal_digest(plan["requested_job"])
    return plan


def fake_native(monkeypatch, *, returncode=0, tables=True):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout"].write(b"synthetic native stdout\n")
        kwargs["stderr"].write(b"synthetic native diagnostic\n")
        if tables:
            for flag in ("--tblout", "-o", "--sfile", "--ifile", "--elfile", "--tfile", "-A"):
                if flag in argv:
                    Path(argv[argv.index(flag) + 1]).write_bytes(b"synthetic result fixture\n")
        return subprocess.CompletedProcess(argv, returncode)
    monkeypatch.setattr("gene_annotation_episode.native_infernal_driver.subprocess.run", run)
    return calls


@pytest.mark.parametrize("program", ["cmsearch", "cmscan", "cmalign"])
def test_exact_staging_selected_command_and_replay_without_subprocess(tmp_path, monkeypatch, program):
    plan = plan_for(tmp_path, program)
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(plan)
    assert bundle["returncode"] == 0 and bundle["failures"] == [] and len(calls) == 1
    root = Path(plan["attempt_directory"])
    assert bundle["requested_job"] == plan["requested_job"]
    assert bundle["operand_bindings"] == plan["requested_job"]["native_infernal"]["operand_bindings"]
    assert bundle["realized_argv"] != bundle["requested_job"]["argv"]
    assert calls[0][0] == bundle["realized_argv"]
    assert calls[0][1]["cwd"] == root and "timeout" not in calls[0][1]
    for row in bundle["inputs"]:
        assert (root / row["relative_path"]).read_bytes() == Path(row["original_path"]).read_bytes()
        assert row["actual_sha256"] == row["expected_sha256"]
        assert row["size_bytes"] == row["expected_size_bytes"]
    if program == "cmscan":
        model = next(row["relative_path"] for row in bundle["inputs"] if row["role"] == "models")
        assert {r["relative_path"] for r in bundle["inputs"] if r["role"].startswith("models_")} == {
            model + "." + suffix for suffix in ("i1f", "i1i", "i1m", "i1p")}
    original_manifest = (root / "bundle.json").read_bytes()
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("replayed execution"))
    # Replay depends only on retained files, not today's input/software location.
    for row in bundle["inputs"]:
        Path(row["original_path"]).unlink()
    Path(bundle["software"]["executable"]).unlink()
    assert run_native_infernal(plan) == bundle
    assert (root / "bundle.json").read_bytes() == original_manifest and len(calls) == 1
    assert validate_native_infernal_bundle_files(bundle, root) == bundle


@pytest.mark.parametrize("fault,code", [("missing", "input_missing"), ("size", "input_size_mismatch"),
    ("digest", "input_digest_mismatch"), ("software", "software_digest_mismatch"),
    ("software_missing", "software_unavailable"), ("not_executable", "software_not_executable"),
    ("scratch", "scratch_limit"), ("directory", "regular_file_required"),
    ("fifo", "regular_file_required"), ("framing", "incomplete_model_input")])
def test_preexecution_failure_retains_partial_work_and_seals(tmp_path, monkeypatch, fault, code):
    plan = plan_for(tmp_path)
    job = plan["requested_job"]["native_infernal"]
    row = job["operands"][0]
    if fault == "missing":
        Path(row["path"]).unlink()
    elif fault == "size":
        row["size_bytes"] += 1
    elif fault == "digest":
        row["sha256"] = "0" * 64
    elif fault == "software":
        job["software"]["sha256"] = "0" * 64
    elif fault == "software_missing":
        Path(job["software"]["executable"]).unlink()
    elif fault == "not_executable":
        Path(job["software"]["executable"]).chmod(0o600)
    elif fault == "scratch":
        plan["policy"]["scratch_bytes"] = 1
    elif fault in {"directory", "fifo"}:
        Path(row["path"]).unlink()
        Path(row["path"]).mkdir() if fault == "directory" else os.mkfifo(row["path"])
    else:
        Path(row["path"]).write_bytes(b"INFERNAL1/a\nNAME broken\n")
        job["operands"][0] = _file(Path(row["path"]), row["role"], row["format"])
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(_reseal(plan))
    assert not calls and bundle["returncode"] is None
    assert any(code in f["code"] for f in bundle["failures"])
    assert run_native_infernal(plan) == bundle


def test_nonzero_is_retained_with_diagnostics_and_missing_outputs(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch, returncode=7, tables=False)
    bundle = run_native_infernal(plan)
    assert bundle["returncode"] == 7 and len(calls) == 1
    assert {a["role"] for a in bundle["artifacts"]} == {"stdout", "stderr"}
    assert any(f["code"] == "native_infernal_nonzero_returncode" and f["detail"] == {"returncode": 7}
        for f in bundle["failures"])
    assert any(f["role"] == "tblout" and f["code"] == "native_infernal_missing_output" for f in bundle["failures"])
    assert run_native_infernal(plan) == bundle and len(calls) == 1


def test_partial_copy_retains_actual_partial_hash_and_never_executes(tmp_path, monkeypatch):
    from gene_annotation_episode import native_infernal_driver as driver
    plan = plan_for(tmp_path)
    job = plan["requested_job"]["native_infernal"]
    sequence = Path(job["operands"][1]["path"])
    sequence.write_bytes(b">partial\n" + b"A" * (2 * 1024**2) + b"\n")
    job["operands"][1] = _file(sequence, "sequences", "fasta")
    def fail_after_partial_copy(root, policy, additional=0):
        path = root / "inputs/sequences.fa"
        if not additional and path.exists() and path.stat().st_size:
            raise driver._ScratchLimit(policy["scratch_bytes"] + 1, policy["scratch_bytes"])
    monkeypatch.setattr(driver, "_scratch", fail_after_partial_copy)
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(_reseal(plan))
    row = next(row for row in bundle["inputs"] if row["role"] == "sequences")
    assert not calls and bundle["returncode"] is None
    assert row["size_bytes"] == 1024**2 < row["expected_size_bytes"]
    assert row["actual_sha256"] == hashlib.sha256(sequence.read_bytes()[:1024**2]).hexdigest()
    assert run_native_infernal(plan) == bundle


def test_empty_supplied_index_is_not_implicitly_built(tmp_path, monkeypatch):
    plan = plan_for(tmp_path, "cmscan")
    job = plan["requested_job"]["native_infernal"]
    row = job["operands"][2]
    Path(row["path"]).write_bytes(b"")
    job["operands"][2] = _file(Path(row["path"]), row["role"], row["format"])
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(_reseal(plan))
    assert not calls and bundle["returncode"] is None
    assert any(f["code"] == "native_infernal_empty_pressed_index" for f in bundle["failures"])
    assert run_native_infernal(plan) == bundle


@pytest.mark.parametrize("program", ["cmsearch", "cmscan", "cmalign"])
def test_model_filter_pair_count_has_program_specific_meaning(tmp_path, monkeypatch, program):
    plan = plan_for(tmp_path, program)
    job = plan["requested_job"]["native_infernal"]
    path = Path(job["operands"][0]["path"])
    path.write_bytes(path.read_bytes() * 2)
    job["operands"][0] = _file(path, "models", "infernal_ascii")
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(_reseal(plan))
    if program == "cmalign":
        assert not calls
        assert any(f["code"] == "native_infernal_cmalign_exactly_one_model_required" for f in bundle["failures"])
    else:
        assert len(calls) == 1 and not bundle["failures"]


@pytest.mark.parametrize("target", ["inputs", "artifacts"])
@pytest.mark.parametrize("corruption", ["bytes", "symlink", "directory", "missing"])
def test_saved_file_corruption_is_rejected_without_recapture(tmp_path, monkeypatch, target, corruption):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(plan)
    path = Path(plan["attempt_directory"]) / bundle[target][0]["relative_path"]
    if corruption == "bytes":
        path.write_bytes(b"changed saved bytes")
    else:
        path.unlink()
        if corruption == "symlink":
            path.symlink_to(FIXTURES / "synthetic_sequences.fa")
        elif corruption == "directory":
            path.mkdir()
    with pytest.raises((ValueError, FileNotFoundError)):
        run_native_infernal(plan)
    assert len(calls) == 1


def test_conflict_unsealed_and_unowned_attempts_never_repeat(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    run_native_infernal(plan)
    changed = deepcopy(plan)
    changed["identity"]["run_id"] = "other-run"
    with pytest.raises(ValueError, match="attempt_identity_conflict"):
        run_native_infernal(changed)
    root = Path(plan["attempt_directory"])
    (root / "bundle.json").unlink()
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        run_native_infernal(plan)
    (root / ".native-infernal-owner.json").unlink()
    with pytest.raises(ValueError, match="not_exclusively_owned"):
        run_native_infernal(plan)
    assert len(calls) == 1


def test_strict_cli_plan_and_confined_attempt(tmp_path):
    with pytest.raises(ValueError, match="exact_plan_file_operand"):
        main([])
    with pytest.raises(ValueError, match="exact_plan_file_operand"):
        main(["one", "two"])
    plan = plan_for(tmp_path)
    plan["identity"]["attempt_id"] = "invented"
    with pytest.raises(ValueError, match="attempt_operation_identity"):
        run_native_infernal(plan)
    plan["identity"]["attempt_id"] = native_infernal_digest(plan["identity"]["operation_key"])
    target = tmp_path / "outside"
    target.mkdir()
    Path(plan["attempt_directory"]).symlink_to(target)
    with pytest.raises(ValueError, match="attempt_symlink_forbidden"):
        run_native_infernal(plan)


def test_manifest_relationships_and_path_escape_are_not_accepted(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    bundle = run_native_infernal(plan)
    for field in ("inputs", "artifacts"):
        changed = deepcopy(bundle)
        changed[field][0]["relative_path"] = "../outside"
        with pytest.raises(ValueError):
            validate_native_infernal_bundle_files(changed, plan["attempt_directory"])
    changed = deepcopy(bundle)
    changed["inputs"] = []
    with pytest.raises(ValueError, match="bundle_inputs_required"):
        validate_native_infernal_bundle_files(changed, plan["attempt_directory"])
    changed = deepcopy(bundle)
    changed["realized_argv"][0] = "/other/program"
    with pytest.raises(ValueError, match="realized_command_conflict"):
        validate_native_infernal_bundle_files(changed, plan["attempt_directory"])
    assert len(calls) == 1


def test_retained_copy_validates_without_original_location(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    fake_native(monkeypatch)
    bundle = run_native_infernal(plan)
    copied = tmp_path / "retained-copy"
    shutil.copytree(plan["attempt_directory"], copied)
    assert validate_native_infernal_bundle_files(bundle, copied) == bundle
    manifest = Path(plan["attempt_directory"]) / "bundle.json"
    manifest.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="sealed_record_bytes_changed"):
        run_native_infernal(plan)


def _local_state(tmp_path):
    plan = plan_for(tmp_path)
    state = SimpleNamespace(run_id="synthetic-run", episode_id="local-child", assignment={
        "requested_job": plan["requested_job"], "workspace": str(tmp_path),
        "resource_kind": "local", "resource_id": "local"})
    operation = "selected-start"
    root = tmp_path / ".episode-operations" / native_infernal_digest({
        "run": state.run_id, "episode": state.episode_id}) / native_infernal_digest(operation)
    root.mkdir(parents=True)
    return state, operation, root


def test_bridge_prepares_original_plan_without_starting(tmp_path, monkeypatch):
    state, operation, root = _local_state(tmp_path)
    monkeypatch.setattr(native, "start_prepared", lambda *a, **k: pytest.fail("prepare started native work"))
    handle = prepare_local_infernal(state, operation, root=root, policy=POLICY)
    assert handle.read()["stage"] == "prepared"
    assert not (root / "infernal-attempt").exists()
    assert prepare_local_infernal(state, operation, root=root, policy=POLICY) == handle
    plan = local_infernal_plan(state.assignment, str(handle.path))
    assert plan["requested_job"] == state.assignment["requested_job"]
    assert plan["policy"] == POLICY.to_dict()
    assert json.loads((root / "invoke.json").read_bytes())["argv"] == state.assignment["requested_job"]["argv"]


@pytest.mark.parametrize("fault", ["command", "policy", "resource", "invoke", "request", "request_rehashed", "owner"])
def test_bridge_detects_original_handle_or_plan_conflicts(tmp_path, fault):
    state, operation, root = _local_state(tmp_path)
    handle = prepare_local_infernal(state, operation, root=root, policy=POLICY)
    body = handle.read()
    assignment = deepcopy(state.assignment)
    if fault == "command":
        body["command"] = ["/bin/true"]
    elif fault == "policy":
        body["metadata"]["policy"]["memory_bytes"] += 1
    elif fault == "resource":
        assignment["resource_id"] = "other"
    elif fault == "invoke":
        invoke = json.loads((root / "invoke.json").read_bytes())
        invoke["argv"] = ["/bin/true"]
        (root / "invoke.json").unlink()
        _immutable(root / "invoke.json", invoke)
    elif fault.startswith("request"):
        path = Path(body["paths"]["request"])
        request = json.loads(path.read_bytes())
        request["env"]["UNSELECTED"] = "changed"
        path.write_text(json.dumps(request))
        if fault == "request_rehashed":
            body["request_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        attempt = root / "infernal-attempt"
        attempt.mkdir()
        (attempt / ".native-infernal-owner.json").write_text("{}\n")
    handle.path.write_text(json.dumps(body))
    with pytest.raises(ValueError):
        local_infernal_plan(assignment, str(handle.path))


@pytest.mark.parametrize("case", ["cmsearch", "cmscan", "cmalign", "cmalign_native_failure"])
def test_retained_actual_native_examples_replay_offline(case, monkeypatch):
    index = RETAINED / "index.json"
    if not index.exists():
        pytest.skip("native verification artifacts have not been produced")
    root = Path(json.loads(index.read_bytes())[case]["action_directory"])
    plan = json.loads((root / "infernal-plan.json").read_bytes())
    bundle = json.loads((root / "infernal-attempt/bundle.json").read_bytes())
    receipt = json.loads((root / "verification-receipt.json").read_bytes())
    assert receipt["metadata"]["policy"] == POLICY.to_dict()
    assert receipt["metadata"]["verified_cgroup"]["memory_max"] == POLICY.memory_bytes
    assert receipt["metadata"]["verified_cgroup"]["runtime_max"] == "infinity"
    assert bundle["returncode"] != 0 if case.endswith("failure") else bundle["returncode"] == 0
    monkeypatch.setattr("subprocess.Popen", lambda *a, **k: pytest.fail("native replay reran process"))
    monkeypatch.setattr("socket.socket", lambda *a, **k: pytest.fail("native replay acquired remote data"))
    assert run_native_infernal(plan) == bundle
    assert validate_native_infernal_bundle_files(bundle, root / "infernal-attempt") == bundle
    if not case.endswith("failure"):
        assert bundle["failures"] == []
        if case in {"cmsearch", "cmscan"}:
            rows = [line.split() for line in (root / "infernal-attempt/hits.tblout").read_text().splitlines()
                if line and not line.startswith("#")]
            assert len(rows) == 10
            if case == "cmsearch":
                assert rows[0][:5] == ["mrum-tRNA.1", "-", "tRNA5", "-", "cm"]
                assert rows[0][14:19] == ["71.4", "3.6e-22", "!", "72", "72"]
            else:
                assert rows[0][:7] == ["1", "tRNA5", "-", "mrum-tRNA.1", "-", "-", "cm"]
                assert rows[0][16:19] == ["71.4", "1e-22", "!"]
            assert (root / "infernal-attempt/inputs/models.cm").read_text().count("INFERNAL1/a") == 3
        else:
            scores = [line.split() for line in (root / "infernal-attempt/scores.txt").read_text().splitlines()
                if line.strip() and not line.startswith("#")]
            assert len(scores) == 10 and scores[0][1:8] == ["mrum-tRNA.1", "72", "1", "72", "no", "60.03", "1.000"]
            assert "mrum-tRNA.9 110 1 72  37 36 40" in (root / "infernal-attempt/local-ends.txt").read_text()
    else:
        assert any(f["code"] == "native_infernal_nonzero_returncode" for f in bundle["failures"])
        assert sum(a["size_bytes"] for a in bundle["artifacts"] if a["role"] in {"stdout", "stderr"}) > 0
        assert "--sample requires --cpu 0" in (root / "infernal-attempt/stdout.log").read_text()
        assert bundle["requested_job"]["native_infernal"]["options"] == ["--cpu", "1", "--sample", "--seed", "42"]
