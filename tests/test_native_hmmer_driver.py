"""Synthetic process faults and custody checks; real native runs are retained separately."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.native_hmmer_contracts import native_hmmer_digest, requested_job_from_native
from gene_annotation_episode.native_hmmer_driver import main, run_native_hmmer, validate_native_hmmer_bundle_files
from test_native_hmmer_contracts import job_for


ROOT = Path(__file__).resolve().parents[1]
HMM = ROOT / "verification/tool_graders_hmmer_search_2026-10-24/native/model.hmm"
FASTA = ROOT / "verification/tool_graders_hmmer_search_2026-10-24/native/query.fa"


def plan_for(tmp_path, program="hmmsearch"):
    job = job_for(program)
    executable = tmp_path / "selected-executable"
    executable.write_text("synthetic test executable; subprocess is replaced by a test fixture\n")
    executable.chmod(0o700)
    job["software"] = {"executable": str(executable), "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(), "engine_version": "synthetic-test"}
    for row in job["operands"]:
        source = HMM if row["format"] == "hmmer3_ascii" else FASTA
        if row["role"].startswith("profile_database_h3"):
            source = Path(str(HMM) + "." + row["role"].rsplit("_", 1)[1])
        row.update(path=str(source), size_bytes=source.stat().st_size, sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    request = requested_job_from_native(job)
    return {"version": "native_hmmer_run_plan_v1", "identity": {"run_id": "synthetic-run", "episode_id": "resource-child",
        "resource_id": "local", "execution_id": "original-execution", "attempt_id": "attempt-one",
        "operation_key": "selected-start", "requested_job_sha256": native_hmmer_digest(request)},
        "requested_job": request, "attempt_directory": str(tmp_path / "attempt"),
        "policy": {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}}


def fake_native(monkeypatch, *, returncode=0, tables=True):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        kwargs["stdout"].write(b"synthetic complete retained stdout\n[ok]\n")
        kwargs["stderr"].write(b"native diagnostic retained\n")
        for flag in ("--tblout", "--domtblout"):
            if tables and flag in argv:
                Path(argv[argv.index(flag) + 1]).write_bytes(b"# no hits in synthetic native table\n")
        if "--chkhmm" in argv:
            prefix = argv[argv.index("--chkhmm")+1]
            Path(prefix + "-1.hmm").write_bytes(b"model one\n")
            Path(prefix + "-2.hmm").write_bytes(b"model two\n")
        return subprocess.CompletedProcess(argv, returncode)
    monkeypatch.setattr("gene_annotation_episode.native_hmmer_driver.subprocess.run", run)
    return calls


def seal(plan):
    plan["identity"]["requested_job_sha256"] = native_hmmer_digest(plan["requested_job"])
    return plan


def test_success_stages_exact_bytes_and_replays_without_new_process(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    bundle = run_native_hmmer(plan)
    assert bundle["returncode"] == 0 and bundle["failures"] == []
    assert len(calls) == 1
    assert bundle["requested_job"]["argv"] != bundle["realized_argv"]
    assert bundle["identity"] == plan["identity"]
    assert bundle["operand_bindings"] == plan["requested_job"]["native_hmmer"]["operand_bindings"]
    root = Path(plan["attempt_directory"])
    for row in bundle["inputs"]:
        assert (root / row["relative_path"]).read_bytes() == Path(row["original_path"]).read_bytes()
        assert row["expected_sha256"] == row["actual_sha256"]
    for env in ("TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"):
        assert Path(bundle["environment"][env]).is_relative_to(root)
    original = (root / "bundle.json").read_bytes()
    assert run_native_hmmer(plan) == bundle
    assert (root / "bundle.json").read_bytes() == original and len(calls) == 1


@pytest.mark.parametrize("fault,code", [("input_missing", "input_missing"), ("input_digest", "input_digest_mismatch"),
    ("input_size", "input_size_mismatch"), ("software_missing", "software_unavailable"),
    ("software_digest", "software_digest_mismatch"), ("scratch", "scratch_limit")])
def test_input_software_and_scratch_failures_seal_without_execution(tmp_path, monkeypatch, fault, code):
    plan = plan_for(tmp_path)
    job = plan["requested_job"]["native_hmmer"]
    if fault == "input_missing":
        job["operands"][0]["path"] = str(tmp_path / "missing")
    elif fault == "input_digest":
        job["operands"][0]["sha256"] = "0" * 64
    elif fault == "input_size":
        job["operands"][0]["size_bytes"] += 1
    elif fault == "software_missing":
        job["software"]["executable"] = str(tmp_path / "missing")
    elif fault == "software_digest":
        job["software"]["sha256"] = "0" * 64
    else:
        plan["policy"]["scratch_bytes"] = 1
    plan["requested_job"] = requested_job_from_native(job)
    seal(plan)
    calls = fake_native(monkeypatch)
    bundle = run_native_hmmer(plan)
    assert bundle["returncode"] is None and not calls
    assert any(code in failure["code"] for failure in bundle["failures"])
    assert Path(plan["attempt_directory"], "bundle.json").is_file()


def test_nonzero_exit_retains_partial_outputs_and_missing_roles(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch, returncode=7, tables=False)
    bundle = run_native_hmmer(plan)
    assert bundle["returncode"] == 7 and len(calls) == 1
    assert {a["role"] for a in bundle["artifacts"]} == {"stdout", "stderr"}
    assert {f["role"] for f in bundle["failures"] if f["code"].endswith("missing_output")} == {"tblout", "domtblout"}
    assert any(f["code"].endswith("nonzero_returncode") for f in bundle["failures"])
    assert run_native_hmmer(plan) == bundle and len(calls) == 1


def test_conflicting_request_and_unsealed_attempt_never_repeat(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    run_native_hmmer(plan)
    changed = deepcopy(plan)
    changed["requested_job"]["native_hmmer"]["options"] += ["--seed", "8"]
    changed["requested_job"] = requested_job_from_native(changed["requested_job"]["native_hmmer"])
    seal(changed)
    with pytest.raises(ValueError, match="attempt_identity_conflict"):
        run_native_hmmer(changed)
    Path(plan["attempt_directory"], "bundle.json").unlink()
    with pytest.raises(ValueError, match="unsealed_attempt_execution_uncertain"):
        run_native_hmmer(plan)
    assert len(calls) == 1


def test_changed_sealed_output_and_symlink_fail_custody_without_recapture(tmp_path, monkeypatch):
    plan = plan_for(tmp_path)
    calls = fake_native(monkeypatch)
    bundle = run_native_hmmer(plan)
    path = Path(plan["attempt_directory"]) / bundle["artifacts"][0]["relative_path"]
    path.write_text("changed")
    with pytest.raises(ValueError, match="sealed_artifact_digest_mismatch"):
        run_native_hmmer(plan)
    path.unlink()
    path.symlink_to(FASTA)
    with pytest.raises(ValueError, match="output_path_escape"):
        validate_native_hmmer_bundle_files(bundle, plan["attempt_directory"])
    assert len(calls) == 1


def test_hmmalign_checks_actual_profile_count(tmp_path, monkeypatch):
    plan = plan_for(tmp_path, "hmmalign")
    profile = tmp_path / "one-name-but-two-models.hmm"
    profile.write_bytes(HMM.read_bytes() * 2)
    job = plan["requested_job"]["native_hmmer"]
    row = next(r for r in job["operands"] if r["role"] == "profile")
    row.update(path=str(profile), size_bytes=profile.stat().st_size, sha256=hashlib.sha256(profile.read_bytes()).hexdigest())
    plan["requested_job"] = requested_job_from_native(job)
    calls = fake_native(monkeypatch)
    bundle = run_native_hmmer(seal(plan))
    assert not calls
    assert any(f["code"] == "native_hmmer_hmmalign_exactly_one_profile_required" for f in bundle["failures"])


def test_all_actual_checkpoint_files_are_retained_without_round_claims(tmp_path, monkeypatch):
    plan = plan_for(tmp_path, "jackhmmer")
    job = plan["requested_job"]["native_hmmer"]
    job["outputs"].append({"role": "checkpoint_hmm", "format": "hmmer3_ascii", "relative_path": "checkpoint/model"})
    plan["requested_job"] = requested_job_from_native(job)
    fake_native(monkeypatch)
    bundle = run_native_hmmer(seal(plan))
    checkpoints = [a for a in bundle["artifacts"] if a["role"] == "checkpoint_hmm"]
    assert len(checkpoints) == 2
    assert all(set(a) == {"role", "format", "relative_path", "size_bytes", "sha256"} for a in checkpoints)


def test_exact_cli_operand_and_existing_unowned_directory(tmp_path):
    with pytest.raises(ValueError, match="exact_plan_file_operand"):
        main([])
    plan = plan_for(tmp_path)
    Path(plan["attempt_directory"]).mkdir()
    with pytest.raises(ValueError, match="not_exclusively_owned"):
        run_native_hmmer(plan)
