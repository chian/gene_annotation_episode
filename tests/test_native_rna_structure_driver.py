import base64
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.library import native_rna_structure_driver as driver
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import BUNDLE_FILENAME, validate_rna_structure_bundle
from test_native_rna_structure_contracts import job, plan, rna_input


def read_role(bundle, attempt, role):
    row = next(row for row in bundle["files"] if row["role"] == role)
    return (attempt / row["relative_path"]).read_bytes() if row["state"] == "present" else None


def test_driver_invokes_once_stages_exact_bytes_and_replays_sealed_bundle(tmp_path, monkeypatch):
    selected, _, _ = plan(tmp_path)
    calls = []
    run = driver.subprocess.run
    def invoke(*args, **kwargs):
        calls.append((args, kwargs))
        return run(*args, **kwargs)
    monkeypatch.setattr(driver.subprocess, "run", invoke)
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    assert bundle["native_status"] == "complete" and bundle["returncode"] == 0
    assert len(calls) == 1 and calls[0][0][0] == bundle["realized_argv"]
    assert "shell" not in calls[0][1]
    original = Path(selected["requested_job"]["native_rna_structure"]["operands"][0]["path"])
    assert (attempt / "input.json").read_bytes() == original.read_bytes()
    assert bundle["realized_argv"] != selected["requested_job"]["argv"]
    assert json.loads(read_role(bundle, attempt, "native_result"))["topology"]["pairs"][0]["i"] == 0
    original.unlink()
    monkeypatch.setattr(driver.subprocess, "run", lambda *args, **kwargs: pytest.fail("sealed replay invoked work"))
    assert driver.run_rna_structure_driver(selected) == bundle
    assert (attempt / BUNDLE_FILENAME).read_bytes() == (canonical(bundle) + "\n").encode()


def test_rejected_input_bytes_are_diagnostics_not_original_scientific_input(tmp_path, monkeypatch):
    selected, _, _ = plan(tmp_path)
    operand = selected["requested_job"]["native_rna_structure"]["operands"][0]
    changed = b"changed original bytes\n\x00\xff" * 5000
    Path(operand["path"]).write_bytes(changed)
    monkeypatch.setattr(driver.subprocess, "run", lambda *args, **kwargs: pytest.fail("substituted input executed"))
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    assert bundle["returncode"] is None and bundle["native_status"] == "failed"
    assert not (attempt / "input.json").exists()
    assert next(row for row in bundle["files"] if row["role"] == "input")["state"] == "absent"
    assert any(row["code"] == "rna_input_identity_mismatch" for row in bundle["failures"])
    rows = [json.loads(line) for line in read_role(bundle, attempt, "stderr").decode().splitlines() if line.startswith("{")]
    header = next(row for row in rows if row["schema"] == "rna_rejected_input_v1")
    chunks = [row for row in rows if row["schema"] == "rna_rejected_input_chunk_v1"]
    assert header["expected"]["sha256"] == operand["sha256"] and header["observed"]["size_bytes"] == len(changed)
    assert b"".join(base64.b64decode(row["bytes_base64"]) for row in chunks) == changed


@pytest.mark.parametrize("raw", [b"not-json", b'{"record_key":"x","record_key":"y"}', b'{"schema":',
    canonical(rna_input()).encode("utf-16")])
def test_original_malformed_bytes_are_present_with_failed_native_record(tmp_path, raw):
    selected, _, _ = plan(tmp_path, job(tmp_path, raw=raw))
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    assert read_role(bundle, attempt, "input") == raw
    record = json.loads(read_role(bundle, attempt, "native_result"))
    assert record["input"] is None and record["record_key"] == "original-record" and record["status"] == "failed"
    assert any(row["code"] == "rna_invalid_input_schema" for row in record["issues"])


def test_dependency_missing_is_partial_and_missing_model_files_are_explicit(tmp_path):
    selected, _, _ = plan(tmp_path, energy=True)
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    record = json.loads(read_role(bundle, attempt, "native_result"))
    assert bundle["returncode"] == 1 and bundle["native_status"] == "partial"
    assert len(record["topology"]["pairs"]) == 3
    assert record["native_evaluation"]["reason"] == "rna_native_dependency_missing"
    absent = [row["role"] for row in bundle["files"] if row["state"] == "absent"]
    assert absent == ["model", "effective_parameters"]
    assert all(row["sha256"] is None and row["size_bytes"] is None for row in bundle["files"] if row["state"] == "absent")
    assert b"ModuleNotFoundError" in read_role(bundle, attempt, "stderr")


@pytest.mark.parametrize("field,bad", [("python_sha256", "0" * 64)])
def test_actual_cli_software_mismatch_prevents_energy_and_keeps_topology(tmp_path, field, bad):
    selected_job = job(tmp_path, energy=True)
    selected_job["software"][field] = bad
    selected, _, _ = plan(tmp_path, selected_job)
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    value = json.loads(read_role(bundle, attempt, "native_result"))
    assert value["native_evaluation"]["reason"] == "rna_software_identity_mismatch"
    assert len(value["topology"]["pairs"]) == 3 and value["model"] is None
    assert b"rna_raw_native_return_v1" not in read_role(bundle, attempt, "stdout")
    assert any(row["field"] == "/software/" + field for row in bundle["failures"])


def test_unsealed_attempt_never_retries(tmp_path, monkeypatch):
    selected, _, _ = plan(tmp_path)
    run = driver.subprocess.run
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(driver.subprocess, "run", interrupted)
    with pytest.raises(KeyboardInterrupt):
        driver.run_rna_structure_driver(selected)
    monkeypatch.setattr(driver.subprocess, "run", lambda *args, **kwargs: pytest.fail("interrupted attempt repeated"))
    with pytest.raises(ValueError, match="rna_unsealed_native_attempt"):
        driver.run_rna_structure_driver(selected)


def test_sealed_replay_detects_changed_present_and_new_absent_files(tmp_path):
    selected, _, _ = plan(tmp_path, energy=True)
    bundle = driver.run_rna_structure_driver(selected)
    attempt = Path(selected["attempt_directory"])
    (attempt / "model.json").write_text("unexpected")
    with pytest.raises(ValueError, match="rna_capture_digest_mismatch"):
        driver.run_rna_structure_driver(selected)
    (attempt / "model.json").unlink()
    (attempt / "stdout.txt").write_text("changed")
    with pytest.raises(ValueError, match="rna_capture_digest_mismatch"):
        driver.run_rna_structure_driver(selected)


@pytest.mark.parametrize("mutation", [lambda x: x["files"].reverse(),
    lambda x: x["files"][0].update(role="native_result"),
    lambda x: x["files"][0].update(sha256="0" * 64),
    lambda x: x["identity"].update(attempt_id="0" * 64),
    lambda x: x.update(sealed=False), lambda x: x["realized_argv"].append("extra"),
    lambda x: x["environment"].update(TMPDIR="/elsewhere")])
def test_manifest_relationships_reject_wrong_role_identity_and_realized_call(tmp_path, mutation):
    selected, _, _ = plan(tmp_path)
    bundle = driver.run_rna_structure_driver(selected)
    mutation(bundle)
    with pytest.raises(ValueError):
        validate_rna_structure_bundle(bundle, plan=selected)


def test_input_symlink_cannot_be_staged(tmp_path):
    selected, _, _ = plan(tmp_path)
    original = Path(selected["requested_job"]["native_rna_structure"]["operands"][0]["path"])
    target = tmp_path / "other.json"
    original.rename(target)
    original.symlink_to(target)
    bundle = driver.run_rna_structure_driver(selected)
    assert bundle["returncode"] is None
    assert any(row["code"] == "rna_output_path_conflict" for row in bundle["failures"])


def test_attempt_and_output_symlinks_are_rejected(tmp_path):
    selected, _, root = plan(tmp_path)
    root.mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    Path(selected["attempt_directory"]).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(ValueError, match="rna_output_path_conflict"):
        driver.run_rna_structure_driver(selected)


