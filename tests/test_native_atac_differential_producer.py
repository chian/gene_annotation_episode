"""Native-format and control-failure tests; callpeak mocks are not science."""
from copy import deepcopy
from pathlib import Path
import os
from types import SimpleNamespace

import pytest

from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_atac_differential_contracts import (
    POLICY, canonical, digest, validate_atac_command_seal, validate_atac_native_bundle,
)
from gene_annotation_episode import native_atac_differential_driver as driver
from gene_annotation_episode.native_atac_differential_reference import extract_atac_bam_header
from gene_annotation_episode.native_atac_differential_observations import atac_observed_files, read_atac_output
from gene_annotation_episode.native_atac_differential_local import prepare_local_atac_differential, local_atac_differential_plan
from gene_annotation_episode.practical_execution_state import PracticalState

from test_native_atac_differential_contracts import bam_bytes, identity, job_fixture, requested, plan_fixture, path_for


FIXTURES = Path(os.environ["ATAC_NATIVE_FIXTURES"])


def mock_commands(monkeypatch, *, fail_first=False, omit=None):
    calls = []
    monkeypatch.setattr(driver, "verify_software", lambda software: None)
    def run(argv, *, stdout, stderr, **kwargs):
        calls.append(argv)
        out = Path(argv[argv.index("--outdir") + 1])
        if "callpeak" in argv:
            i = int(argv[argv.index("-n") + 1][-1])
            original = FIXTURES / "bam_outputs"
            for suffix in ("peaks.xls", "peaks.narrowPeak", "summits.bed", "treat_pileup.bdg", "control_lambda.bdg"):
                if omit == (i, suffix) or fail_first and i == 1 and suffix != "treat_pileup.bdg":
                    continue
                raw = (original / f"condition{i}_{suffix}").read_bytes()
                if suffix == "peaks.xls":
                    lines = raw.splitlines(keepends=True)
                    raw = b"".join(("# ChIP-seq file = " + repr([argv[argv.index("-t") + 1]]) + "\n").encode() if line.startswith(b"# ChIP-seq file = ") else line for line in lines)
                (out / f"c{i}_{suffix}").write_bytes(raw)
            stderr.write(b"actual control mock invocation; no scientific execution\n")
            return SimpleNamespace(returncode=7 if fail_first and i == 1 else 0)
        for name, source in (("condition1.bed", "condition1_differential.bed"),
                ("condition2.bed", "condition2_differential.bed"), ("common.bed", "common.bed")):
            (out / name).write_bytes((FIXTURES / "bam_outputs" / source).read_bytes())
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(driver.subprocess, "run", run)
    return calls


def header(tmp_path, raw):
    source, output = tmp_path / "input.bam", tmp_path / "attempt/metadata/header.sam"
    source.write_bytes(raw)
    return extract_atac_bam_header(input_path=source, input_file=identity(raw), input_key="in1", callpeak_run_key="callpeak1",
        input_ordinal=0, output_path=output, output_relative_path="metadata/header.sam", policy=LocalJobPolicy(**POLICY)), output


def test_original_actual_headers_and_no_synthesized_sq(tmp_path):
    raw = (FIXTURES / "bam_inputs/condition1.bam").read_bytes()
    result, output = header(tmp_path, raw)
    assert result["producer_outcome"] == "succeeded"
    assert output.read_bytes() == b"@HD\tVN:1.6\tSO:coordinate\n@SQ\tSN:chrToy\tLN:12000\n"
    second = tmp_path / "synthesized-counterexample"
    second.mkdir()
    result, output = header(second, bam_bytes(text=b"@HD\tVN:1.6\n"))
    assert result["producer_outcome"] == "failed"
    assert output.read_bytes() == b"@HD\tVN:1.6\n"
    assert result["failures"][0]["code"] == "reference_conflict"


def test_original_plan_pending_start_and_read_after_input_loss(tmp_path):
    job = job_fixture(tmp_path)
    assignment = dict(version="practical_assignment_v1", assignment_id="assignment", resource_kind="local", resource_id="local",
        workspace=str(tmp_path), endpoint="usable_handoff", requested_job=requested(job, tmp_path),
        progress_requirements=[dict(key="handoff", credit=1, predicate=dict(kind="requested_job_handoff"))],
        completion_keys=["handoff"], initial_context=dict(revision=0, cwd=str(tmp_path), environment={}), inventory_snapshot={}, constraints=POLICY)
    state = PracticalState(tmp_path / "state", "run", "child", assignment)
    root = tmp_path / ".episode-operations" / digest(dict(run="run", episode="child")) / digest("start")
    with pytest.raises(ValueError, match="selected_pending_start_required"):
        prepare_local_atac_differential(state, "start", root=root, policy=LocalJobPolicy(**POLICY))
    state.begin("start", "practical.job.start", {})
    handle = prepare_local_atac_differential(state, "start", root=root, policy=LocalJobPolicy(**POLICY))
    plan = local_atac_differential_plan(assignment, str(handle.path))
    for row in job["input_bindings"]:
        Path(row["path"]).unlink()
    assert local_atac_differential_plan(assignment, str(handle.path)) == plan
    assert prepare_local_atac_differential(state, "start", root=root, policy=LocalJobPolicy(**POLICY)).path == handle.path


def test_finite_pipeline_binds_actual_100_200_depths(tmp_path, monkeypatch):
    calls = mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    result = driver.run_atac_differential_driver(plan)
    assert [r["count"] for r in result["depth_selection"]["conditions"]] == [100, 200]
    assert all(r["source_locations"] for r in result["depth_selection"]["conditions"])
    assert len(calls) == 3 and all(s["outcome"] == "succeeded" for s in result["steps"])
    assert calls[2][calls[2].index("--d1") + 1] == "0.0001"
    assert calls[2][calls[2].index("--d2") + 1] == "0.0002"
    assert driver.run_atac_differential_driver(plan) == result and len(calls) == 3
    assert path_for(plan, "bdgdiff.common").stat().st_size == 89


def test_failed_first_preserves_partial_and_runs_second(tmp_path, monkeypatch):
    calls = mock_commands(monkeypatch, fail_first=True)
    plan = plan_fixture(tmp_path)
    result = driver.run_atac_differential_driver(plan)
    assert [s["outcome"] for s in result["steps"]] == ["failed", "succeeded", "not_run"]
    assert len(calls) == 2 and path_for(plan, "callpeak1.signal").exists()
    assert result["steps"][2]["argv"] == []
    assert result["steps"][2]["started_at"] is None


@pytest.mark.parametrize("changed", ["missing", "wrong_bytes", "wrong_pin"])
def test_failed_input_or_runtime_never_substitutes(tmp_path, monkeypatch, changed):
    calls = mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    source = Path(plan["requested_job"]["native_atac_differential"]["input_bindings"][0]["path"])
    if changed == "missing":
        source.unlink()
    elif changed == "wrong_bytes":
        source.write_bytes(b"changed")
    else:
        def reject(_):
            raise ValueError("native_dependency_unavailable")
        monkeypatch.setattr(driver, "verify_software", reject)
    result = driver.run_atac_differential_driver(plan)
    assert result["steps"][0]["outcome"] == "not_run"
    assert len(calls) == (0 if changed == "wrong_pin" else 1)
    assert result["steps"][2]["outcome"] == "not_run"
    assert any(p["code"] == {"missing": "input_unavailable", "wrong_bytes": "artifact_digest_mismatch", "wrong_pin": "native_dependency_unavailable"}[changed] for p in result["failures"])
    if changed == "wrong_pin":
        assert all(row["producer_outcome"] == "not_run" and row["header"]["state"] == "absent"
            for row in result["input_inspections"])


def test_live_writer_and_output_allowlist(tmp_path, monkeypatch):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    driver.run_atac_differential_driver(plan)
    files, logs, _ = atac_observed_files(plan, {"terminal": True, "quiescent": False}, log_window_bytes=32, log_roles=("stderr",))
    assert not any(row["writer_closed"] for row in files)
    assert len(logs) == 4
    result = read_atac_output(plan, path=str(path_for(plan, "callpeak1.stderr")), offset=0, limit=32)
    assert result["returned_bytes"] == 32
    with pytest.raises(ValueError):
        read_atac_output(plan, path=str(tmp_path / "original1.bam"), offset=0, limit=32)


def test_unsealed_attempt_never_restarts(tmp_path, monkeypatch):
    calls = mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    directory = Path(plan["attempt_directory"])
    directory.mkdir(parents=True)
    driver._immutable(directory / ".native-atac-owner.json", plan)
    with pytest.raises(ValueError, match="unsealed_native_attempt"):
        driver.run_atac_differential_driver(plan)
    assert calls == []


@pytest.mark.parametrize("mutation", [
    lambda s: s["argv"].__setitem__(s["argv"].index("--t2") + 1, "/unrelated/input.bdg"),
    lambda s: s["argv"].__setitem__(s["argv"].index("--d1") + 1, "0"),
    lambda s: s["argv"].__setitem__(s["argv"].index("--d1") + 1, "1e999999999"),
    lambda s: s["inputs"][2].update(role="background"),
    lambda s: s["inputs"][0]["file"].update(artifact_ref="artifact_" + "f" * 64),
    lambda s: s.update(outcome="failed", returncode=0),
    lambda s: s.update(finished_at="2000-01-01T00:00:00+00:00"),
])
def test_native_seal_rejects_changed_operands_or_outcome(tmp_path, monkeypatch, mutation):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    result = driver.run_atac_differential_driver(plan)
    seal = deepcopy(result["steps"][2])
    mutation(seal)
    with pytest.raises(ValueError, match="original_attempt_mismatch"):
        validate_atac_command_seal(seal, plan=plan, step_key="bdgdiff")


def test_bundle_rejects_identity_bound_to_wrong_native_role(tmp_path, monkeypatch):
    mock_commands(monkeypatch)
    plan = plan_fixture(tmp_path)
    result = driver.run_atac_differential_driver(plan)
    changed = deepcopy(result)
    seal = changed["steps"][2]
    seal["inputs"][0]["file"] = deepcopy(seal["inputs"][2]["file"])
    # Rehash the seal declaration, so the failed check is its actual producer
    # operand relation, not merely the control artifact's byte digest.
    declaration = next(r["declaration"] for r in changed["outputs"]
        if r["specification"]["file_key"] == "bdgdiff.seal")
    declaration.update({k: v for k, v in identity(canonical(seal)).items() if k in ("sha256", "size_bytes")})
    with pytest.raises(ValueError, match="original_attempt_mismatch"):
        validate_atac_native_bundle(changed, plan=plan)


def test_header_truncation_preserves_original_prefix_and_source_symlink_rejects(tmp_path):
    import gzip
    import struct
    raw_text = b"@HD\tVN:1.6\n"
    raw = gzip.compress(b"BAM\x01" + struct.pack("<i", len(raw_text) + 20) + raw_text, mtime=0)
    result, output = header(tmp_path, raw)
    assert result["producer_outcome"] == "failed" and result["supplied_extent"] == "partial"
    assert output.read_bytes() == raw_text
    linked = tmp_path / "linked.bam"
    linked.symlink_to(tmp_path / "input.bam")
    second = extract_atac_bam_header(input_path=linked, input_file=identity(raw), input_key="in1",
        callpeak_run_key="callpeak1", input_ordinal=0, output_path=tmp_path / "other/metadata/header.sam",
        output_relative_path="metadata/header.sam", policy=LocalJobPolicy(**POLICY))
    assert second["header"]["state"] == "absent" and second["producer_outcome"] == "failed"


def test_corrupt_compressed_input_preserves_second_condition(tmp_path, monkeypatch):
    # A gzip header followed by the reserved DEFLATE block type. Its expected
    # byte identity matches; it is a real decoding failure, not a pin mismatch.
    corrupt = b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff\x07" + b"\x00" * 8
    job = job_fixture(tmp_path, inputs=[corrupt, bam_bytes()])
    plan = plan_fixture(tmp_path, job=job)
    calls = mock_commands(monkeypatch)
    result = driver.run_atac_differential_driver(plan)
    assert [r["outcome"] for r in result["steps"]] == ["not_run", "succeeded", "not_run"]
    assert len(calls) == 1 and calls[0][calls[0].index("-n") + 1] == "c2"
    assert result["input_inspections"][0]["failures"][0]["code"] == "input_unavailable"
