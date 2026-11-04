"""Custody faults and actual selected native modes under the bounded test worker."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from gene_annotation_episode import native_infernal_preparation_driver as driver
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_infernal_contracts import native_infernal_digest
from gene_annotation_episode.native_infernal_preparation_contracts import (
    requested_job_from_infernal_preparation,
)


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "verification/tool_graders_infernal_preparation_2026-10-26_247/NATIVE_COMPILED_INDEX_001.json"
INDEX = json.loads(INDEX_PATH.read_text())
CASES = INDEX["cases"]
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_job(program, mode):
    case = next(c for c in CASES if (c["program"], c["mode"]) == (program, mode))
    path = ROOT / case["request_path"]
    assert digest(path) == case["request_sha256"]
    return json.loads(path.read_bytes())


def make_plan(tmp_path, selected=None):
    selected = native_job("cmconvert", "ascii") if selected is None else selected
    request = requested_job_from_infernal_preparation(selected)
    return {"version": driver.PLAN_VERSION, "identity": {"run_id": "producer251-test",
        "episode_id": "selected-local-child", "resource_id": "local", "execution_id": str(tmp_path / "native.json"),
        "operation_key": "selected-command", "attempt_id": native_infernal_digest("selected-command"),
        "requested_job_sha256": native_infernal_digest(request)}, "requested_job": request,
        "attempt_directory": str(tmp_path / "infernal-preparation-attempt"), "policy": POLICY.to_dict()}


def synthetic_plan(tmp_path, program="cmconvert", mode="ascii"):
    selected = native_job(program, mode)
    for row in selected["operands"]:
        path = tmp_path / (row["role"] + "-" + str(row["ordinal"]))
        path.write_bytes(Path(row["path"]).read_bytes())
        row["path"] = str(path)
    executable = tmp_path / "synthetic-executable"
    executable.write_bytes(b"Synthetic process boundary fixture; never executed.\n")
    executable.chmod(0o700)
    selected["software"].update(executable=str(executable), sha256=digest(executable), engine_version="synthetic")
    return make_plan(tmp_path, selected)


def reseal(plan):
    plan["requested_job"] = requested_job_from_infernal_preparation(plan["requested_job"]["native_infernal_preparation"])
    plan["identity"]["requested_job_sha256"] = native_infernal_digest(plan["requested_job"])
    return plan


def fake_native(monkeypatch, plan, *, returncode=0, callback=None, outputs=True):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout"].write(b"synthetic stdout\n")
        if outputs:
            for output in plan["requested_job"]["native_infernal_preparation"]["outputs"]:
                if output["role"] not in {"stdout", "stderr"}:
                    (kwargs["cwd"] / output["relative_path"]).write_bytes(b"synthetic retained output\n")
        if callback:
            callback(argv, kwargs)
        return subprocess.CompletedProcess(argv, returncode)
    monkeypatch.setattr(driver.subprocess, "run", run)
    return calls


def test_exact_selected_command_environment_and_offline_replay(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    plan["requested_job"]["native_infernal_preparation"]["environment"] = {"LC_ALL": "C"}
    reseal(plan)
    monkeypatch.setenv("INFERNAL_NCPU", "99")
    calls = fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(plan)
    root = Path(plan["attempt_directory"])
    assert bundle["returncode"] == 0 and bundle["failures"] == [] and len(calls) == 1
    assert calls[0][0] == bundle["realized_argv"]
    assert calls[0][1]["env"] == bundle["environment"]
    assert set(bundle["environment"]) == {"LC_ALL", "TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"}
    assert "timeout" not in calls[0][1] and calls[0][1]["cwd"] == root
    for row in bundle["inputs"]:
        assert row["expected_sha256"] == row["staged_sha256"] == row["final_sha256"]
        assert row["expected_size_bytes"] == row["staged_size_bytes"] == row["final_size_bytes"]
        Path(row["original_path"]).unlink()
    Path(bundle["software"]["executable"]).unlink()
    original = (root / "bundle.json").read_bytes()
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("replay executed native work"))
    monkeypatch.setattr("socket.socket", lambda *a, **k: pytest.fail("replay acquired inputs"))
    assert driver.run_native_infernal_preparation(plan) == bundle
    assert (root / "bundle.json").read_bytes() == original
    retained = tmp_path / "retained"
    shutil.copytree(root, retained)
    shutil.rmtree(root)
    assert driver.validate_preparation_bundle_files(bundle, retained) == bundle


@pytest.mark.parametrize("fault", ["missing", "size", "digest", "software", "software_missing", "not_executable", "scratch", "fifo", "directory"])
def test_preexecution_failures_retain_partial_custody_without_invocation(tmp_path, monkeypatch, fault):
    plan = synthetic_plan(tmp_path)
    job = plan["requested_job"]["native_infernal_preparation"]
    operand = job["operands"][0]
    path = Path(operand["path"])
    if fault == "missing":
        path.unlink()
    elif fault == "size":
        operand["size_bytes"] += 1
    elif fault == "digest":
        operand["sha256"] = "0" * 64
    elif fault == "software":
        job["software"]["sha256"] = "0" * 64
    elif fault == "software_missing":
        Path(job["software"]["executable"]).unlink()
    elif fault == "not_executable":
        Path(job["software"]["executable"]).chmod(0o600)
    elif fault == "scratch":
        plan["policy"]["scratch_bytes"] = 1
    else:
        path.unlink()
        os.mkfifo(path) if fault == "fifo" else path.mkdir()
    calls = fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(reseal(plan))
    assert bundle["returncode"] is None and not calls and bundle["failures"]
    assert all(f["code"] in driver.FAILURE_CODES for f in bundle["failures"])
    assert driver.run_native_infernal_preparation(plan) == bundle


def test_partial_input_copy_retains_actual_measurements(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    row = plan["requested_job"]["native_infernal_preparation"]["operands"][0]
    path = Path(row["path"])
    path.write_bytes(b"synthetic partial custody\n" * 100000)
    row.update(sha256=digest(path), size_bytes=path.stat().st_size)
    def limited(root, policy, additional=0):
        copied = root / "inputs/models.cm"
        if not additional and copied.exists() and copied.stat().st_size:
            raise driver._ScratchLimit(policy["scratch_bytes"] + 1, policy["scratch_bytes"])
    monkeypatch.setattr(driver, "_scratch", limited)
    calls = fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(reseal(plan))
    observed = bundle["inputs"][0]
    assert not calls and bundle["returncode"] is None
    assert observed["staged_size_bytes"] == observed["final_size_bytes"] == 1024**2
    assert observed["staged_sha256"] == hashlib.sha256(path.read_bytes()[:1024**2]).hexdigest()
    assert observed["staged_size_bytes"] < observed["expected_size_bytes"]


@pytest.mark.parametrize("target", ["input", "immutable_copy", "mutable_copy", "missing_mutable_copy"])
def test_before_and_after_custody_preserves_changes_and_partial_outputs(tmp_path, monkeypatch, target):
    program, mode = ("cmpress", "press") if target == "immutable_copy" else ("cmcalibrate", "calibrate")
    plan = synthetic_plan(tmp_path, program, mode)
    original = Path(plan["requested_job"]["native_infernal_preparation"]["operands"][0]["path"])
    original_bytes = original.read_bytes()
    def mutate(argv, kwargs):
        path = kwargs["cwd"] / "inputs/models.cm" if target == "input" else Path(argv[-1])
        if target == "missing_mutable_copy":
            path.unlink()
        else:
            path.write_bytes(b"synthetic changed or partial bytes\n")
    calls = fake_native(monkeypatch, plan, returncode=9, callback=mutate, outputs=False)
    bundle = driver.run_native_infernal_preparation(plan)
    assert len(calls) == 1 and bundle["returncode"] == 9 and original.read_bytes() == original_bytes
    assert any(f["code"].endswith("nonzero_returncode") for f in bundle["failures"])
    row = bundle["inputs"][0] if target == "input" else bundle["working_copies"][0]
    before = "staged" if target == "input" else "initial"
    assert row[before + "_sha256"] != row["final_sha256"]
    if target in {"input", "immutable_copy"}:
        assert any("immutable_" in f["code"] for f in bundle["failures"])
    if target == "mutable_copy":
        assert not any("immutable_" in f["code"] for f in bundle["failures"])
        assert next(a for a in bundle["artifacts"] if a["role"] == "calibrated_models")["size_bytes"] == 35
    assert driver.run_native_infernal_preparation(plan) == bundle


def test_missing_source_does_not_invent_a_working_copy(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path, "cmpress", "press")
    Path(plan["requested_job"]["native_infernal_preparation"]["operands"][0]["path"]).unlink()
    calls = fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(plan)
    assert not calls
    row = bundle["working_copies"][0]
    assert row["source_sha256"] is row["initial_sha256"] is row["final_sha256"] is None
    assert driver.run_native_infernal_preparation(plan) == bundle


@pytest.mark.parametrize("target", ["inputs", "working_copies", "artifacts"])
@pytest.mark.parametrize("corruption", ["bytes", "symlink", "directory", "missing"])
def test_retained_file_corruption_rejects_without_recapture(tmp_path, monkeypatch, target, corruption):
    plan = synthetic_plan(tmp_path, "cmpress", "press")
    calls = fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(plan)
    path = Path(plan["attempt_directory"]) / bundle[target][0]["relative_path"]
    if corruption == "bytes":
        path.write_bytes(b"changed saved bytes")
    else:
        path.unlink()
        if corruption == "symlink":
            path.symlink_to(Path(bundle["inputs"][0]["original_path"]))
        elif corruption == "directory":
            path.mkdir()
    with pytest.raises((ValueError, OSError)):
        driver.run_native_infernal_preparation(plan)
    assert len(calls) == 1


@pytest.mark.parametrize("fault", ["identity", "program", "mode", "operation", "argv", "environment", "path", "input_hash", "final_hash", "input_ordinal_type", "copy_ordinal_type", "copy_mutable", "copy_source", "failure_code", "failure_detail", "failure_returncode", "timestamp", "returncode"])
def test_manifest_relationships_reject_tampering(tmp_path, monkeypatch, fault):
    plan = synthetic_plan(tmp_path, "cmpress", "press")
    fake_native(monkeypatch, plan)
    bundle = driver.run_native_infernal_preparation(plan)
    changed = deepcopy(bundle)
    if fault == "identity":
        changed["identity"]["run_id"] = "other-owner"
    elif fault in {"program", "mode"}:
        changed[fault] = "changed"
    elif fault == "operation":
        changed["operation"]["settings"]["-F"] = True
    elif fault == "argv":
        changed["realized_argv"][0] = "/bin/true"
    elif fault == "environment":
        changed["environment"]["INFERNAL_NCPU"] = "4"
    elif fault == "path":
        changed["inputs"][0]["relative_path"] = "../outside"
    elif fault == "input_hash":
        changed["inputs"][0]["staged_sha256"] = "0" * 64
    elif fault == "final_hash":
        changed["inputs"][0]["final_sha256"] = "0" * 64
    elif fault == "input_ordinal_type":
        changed["inputs"][0]["ordinal"] = False
    elif fault == "copy_ordinal_type":
        changed["working_copies"][0]["operand_ordinal"] = False
    elif fault == "copy_mutable":
        changed["working_copies"][0]["mutable"] = True
    elif fault == "copy_source":
        changed["working_copies"][0]["source_sha256"] = "0" * 64
    elif fault == "failure_returncode":
        changed["failures"] = [{"stage": "execution", "code": driver._PREFIX + "nonzero_returncode",
            "role": None, "detail": {"returncode": 7}}]
    elif fault.startswith("failure"):
        changed["failures"] = [{"stage": "outputs", "code": "unknown" if fault == "failure_code" else driver._PREFIX + "missing_output",
            "role": "stdout", "detail": {"narrative": "not a typed native context"}}]
    elif fault == "timestamp":
        changed["finished_at"] = "1900-01-01T00:00:00+00:00"
    else:
        changed["returncode"] = 1
    with pytest.raises(ValueError):
        driver.validate_preparation_bundle_files(changed, plan["attempt_directory"])


def test_conflicting_unsealed_and_unowned_attempts_never_run_again(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    calls = fake_native(monkeypatch, plan)
    driver.run_native_infernal_preparation(plan)
    changed = deepcopy(plan)
    changed["identity"]["episode_id"] = "other"
    with pytest.raises(ValueError, match="attempt_identity_conflict"):
        driver.run_native_infernal_preparation(changed)
    root = Path(plan["attempt_directory"])
    (root / "bundle.json").unlink()
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        driver.run_native_infernal_preparation(plan)
    (root / driver.OWNER_NAME).unlink()
    with pytest.raises(ValueError, match="not_exclusively_owned"):
        driver.run_native_infernal_preparation(plan)
    assert len(calls) == 1


@pytest.mark.parametrize("fault", ["version", "attempt_identity", "job_hash", "policy", "path", "inside", "symlink"])
def test_strict_preparation_plan_rejects_before_attempt_creation(tmp_path, fault):
    plan = synthetic_plan(tmp_path)
    if fault == "version":
        plan["version"] = "native_infernal_run_plan_v1"
    elif fault == "attempt_identity":
        plan["identity"]["attempt_id"] = "invented"
    elif fault == "job_hash":
        plan["identity"]["requested_job_sha256"] = "0" * 64
    elif fault == "policy":
        plan["policy"]["wall_seconds"] = False
    elif fault == "path":
        plan["attempt_directory"] += "/../outside"
    elif fault == "inside":
        plan["requested_job"]["native_infernal_preparation"]["operands"][0]["path"] = plan["attempt_directory"] + "/original"
        reseal(plan)
    else:
        target = tmp_path / "elsewhere"
        target.mkdir()
        Path(plan["attempt_directory"]).symlink_to(target)
    with pytest.raises(ValueError):
        driver.run_native_infernal_preparation(plan)


def test_command_not_started_has_null_returncode_and_real_empty_logs(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    def failed(*args, **kwargs):
        raise OSError(8, "synthetic exec format error")
    monkeypatch.setattr(driver.subprocess, "run", failed)
    bundle = driver.run_native_infernal_preparation(plan)
    assert bundle["returncode"] is None
    assert {a["role"] for a in bundle["artifacts"]} == {"stdout", "stderr"}
    assert all(a["size_bytes"] == 0 for a in bundle["artifacts"])
    assert any(f["code"].endswith("command_unavailable") and f["detail"] == {"errno": 8} for f in bundle["failures"])


def test_zero_exit_with_missing_selected_output_is_not_complete_custody(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path)
    fake_native(monkeypatch, plan, outputs=False)
    bundle = driver.run_native_infernal_preparation(plan)
    assert bundle["returncode"] == 0
    assert {a["role"] for a in bundle["artifacts"]} == {"stdout", "stderr"}
    assert any(f["code"].endswith("missing_output") and f["role"] == "converted_models" for f in bundle["failures"])
    assert driver.run_native_infernal_preparation(plan) == bundle


def test_ambient_index_is_not_discovered_or_staged(tmp_path, monkeypatch):
    plan = synthetic_plan(tmp_path, "cmfetch", "single_key")
    models = plan["requested_job"]["native_infernal_preparation"]["operands"][0]
    Path(models["path"] + ".ssi").write_bytes(b"synthetic unselected ambient index\n")
    def inspect(argv, kwargs):
        assert not (kwargs["cwd"] / "inputs/models.cm.ssi").exists()
    fake_native(monkeypatch, plan, callback=inspect)
    bundle = driver.run_native_infernal_preparation(plan)
    assert [r["role"] for r in bundle["inputs"]] == ["models"]
    assert bundle["returncode"] == 0 and bundle["failures"] == []


@pytest.mark.parametrize("case", CASES, ids=[c["program"] + "-" + c["mode"] for c in CASES])
def test_actual_selected_native_mode_and_immutable_inputs(tmp_path, monkeypatch, case):
    selected = native_job(case["program"], case["mode"])
    original = {r["path"]: digest(Path(r["path"])) for r in selected["operands"]}
    plan = make_plan(tmp_path, selected)
    (tmp_path / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    bundle = driver.run_native_infernal_preparation(plan)
    assert bundle["returncode"] == 0 and bundle["failures"] == []
    assert {path: digest(Path(path)) for path in original} == original
    assert all(r["expected_sha256"] == r["staged_sha256"] == r["final_sha256"] for r in bundle["inputs"])
    assert len(bundle["artifacts"]) == len(selected["outputs"])
    root = Path(plan["attempt_directory"])
    if selected["program"] == "cmcalibrate" and selected["mode"] in {"calibrate", "merge_scores"}:
        row = next(r for r in bundle["working_copies"] if r["operand_role"] == "models")
        assert row["mutable"] and row["initial_sha256"] != row["final_sha256"]
        assert "ECMLC" in (root / row["relative_path"]).read_text()
        assert "ECMLC" not in Path(selected["operands"][0]["path"]).read_text()
    if selected["mode"] == "merge_scores":
        partitions = [r for r in bundle["working_copies"] if r["operand_role"] == "partition_scores"]
        assert [r["relative_path"] for r in partitions] == ["work/partition.1", "work/partition.2"]
        assert all(not r["mutable"] and r["source_sha256"] == r["initial_sha256"] == r["final_sha256"] for r in partitions)
    if selected["program"] == "cmfetch" and selected["mode"] == "key_file":
        keys = next(r for r in bundle["inputs"] if r["role"] == "keys")
        output = next(r for r in bundle["artifacts"] if r["role"] == "fetched_models")
        assert "absent_key" in (root / keys["relative_path"]).read_text()
        assert "absent_key" not in (root / output["relative_path"]).read_text()
    monkeypatch.setattr(driver.subprocess, "run", lambda *a, **k: pytest.fail("native replay executed"))
    assert driver.run_native_infernal_preparation(plan) == bundle


def test_actual_native_failure_keeps_partial_model_and_diagnostic(tmp_path):
    selected = native_job("cmcalibrate", "calibrate")
    # Native calibration rejects the zero-tail population for this explicit tiny
    # configuration; the producer retains the mutable input copy and diagnostics.
    selected["options"] = ["-L", "0.01", "--tailp", "0.00000001", "--seed", "181", "--cpu", "1", "--noforecast"]
    plan = make_plan(tmp_path, selected)
    (tmp_path / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    bundle = driver.run_native_infernal_preparation(plan)
    assert bundle["returncode"] != 0
    assert bundle["working_copies"][0]["initial_sha256"] == bundle["working_copies"][0]["final_sha256"]
    assert next(a for a in bundle["artifacts"] if a["role"] == "calibrated_models")["size_bytes"] > 0
    assert any(f["code"].endswith("nonzero_returncode") for f in bundle["failures"])
    assert driver.validate_preparation_bundle_files(bundle, plan["attempt_directory"]) == bundle


def test_actual_pressed_quartet_consumed_by_separately_selected_cmscan(tmp_path):
    from gene_annotation_episode.native_infernal_contracts import output_contract, requested_job_from_infernal
    from gene_annotation_episode.native_infernal_driver import run_native_infernal

    selected = native_job("cmpress", "press")
    calibrated = native_job("cmstat", "summary")["operands"][0]
    selected["operands"] = [calibrated]
    preparation = make_plan(tmp_path, selected)
    pressed = driver.run_native_infernal_preparation(preparation)
    assert pressed["returncode"] == 0 and not pressed["failures"]
    attempt = Path(preparation["attempt_directory"])
    models = attempt / pressed["working_copies"][0]["relative_path"]
    sequences = tmp_path / "query.fa"
    sequences.write_bytes(b">fixture251\nGCGCAAAAGCGC\n")
    def operand(role, path, fmt):
        return {"role": role, "path": str(path), "format": fmt, "size_bytes": path.stat().st_size,
            "sha256": digest(path), "artifact_ref": "fixture251:" + role}
    operands = [operand("models", models, "infernal_ascii"), operand("sequences", sequences, "fasta")]
    operands += [operand("models_" + suffix, Path(str(models) + "." + suffix), "infernal_" + suffix)
        for suffix in ("i1f", "i1i", "i1m", "i1p")]
    executable = Path(selected["software"]["executable"]).with_name("cmscan")
    job = {"version": "native_infernal_job_v1", "program": "cmscan",
        "software": {"executable": str(executable), "sha256": digest(executable), "engine_version": "1.1.5"},
        "environment": {}, "operands": operands, "operand_bindings": [], "options": ["--cpu", "1", "--max"],
        "outputs": [{"role": role, "format": fmt, "relative_path": role + ".out"}
            for role, fmt in output_contract("cmscan")[0].items()], "table_format": 1, "metadata": {}, "grading_parameters": {}}
    request = requested_job_from_infernal(job)
    plan = {**preparation, "version": "native_infernal_run_plan_v1", "requested_job": request,
        "identity": {**preparation["identity"], "operation_key": "separately-selected-scan",
            "attempt_id": native_infernal_digest("separately-selected-scan"), "requested_job_sha256": native_infernal_digest(request)},
        "attempt_directory": str(tmp_path / "separately-selected-cmscan")}
    (tmp_path / "press-plan.json").write_text(json.dumps(preparation, indent=2) + "\n")
    (tmp_path / "scan-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    scanned = run_native_infernal(plan)
    assert scanned["returncode"] == 0 and scanned["failures"] == []
    assert {r["role"] for r in scanned["inputs"]} == {"models", "sequences", "models_i1f", "models_i1i", "models_i1m", "models_i1p"}


def test_actual_explicit_ssi_is_staged_adjacent_for_separately_selected_fetch(tmp_path):
    indexed_plan = make_plan(tmp_path, native_job("cmfetch", "index"))
    indexed = driver.run_native_infernal_preparation(indexed_plan)
    assert indexed["returncode"] == 0 and not indexed["failures"]
    root = Path(indexed_plan["attempt_directory"])
    selected = native_job("cmfetch", "single_key")
    model = root / indexed["working_copies"][0]["relative_path"]
    index = Path(str(model) + ".ssi")
    selected["operands"] = [{"role": role, "ordinal": 0, "path": str(path), "format": fmt,
        "sha256": digest(path), "size_bytes": path.stat().st_size, "artifact_ref": "fixture251:" + role}
        for role, path, fmt in (("models", model, "infernal_cm_ascii"), ("ssi", index, "infernal_ssi"))]
    consumer = tmp_path / "separately-selected-fetch"
    consumer.mkdir()
    fetched_plan = make_plan(consumer, selected)
    fetched = driver.run_native_infernal_preparation(fetched_plan)
    assert fetched["returncode"] == 0 and not fetched["failures"]
    assert [r["relative_path"] for r in fetched["inputs"]] == ["inputs/models.cm", "inputs/models.cm.ssi"]
    assert fetched["inputs"][1]["final_sha256"] == indexed["artifacts"][-1]["sha256"]


def test_exact_cli_operand_count():
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main([])
    with pytest.raises(ValueError, match="exact_plan_file_operand_required"):
        driver.main(["one", "two"])
