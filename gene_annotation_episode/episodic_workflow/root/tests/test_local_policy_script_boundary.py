"""Harmless actual launcher-script compatibility; no systemd or native job."""
import json
import os
from pathlib import Path
import subprocess
import sys

from gene_annotation_episode import acquisition, acquisition_types, local_jobs, local_job_policy
from gene_annotation_episode import _local_job_worker, local_scratch


def test_original_public_types_and_safepath_script_report(tmp_path):
    assert local_jobs.LocalJobPolicy is local_job_policy.LocalJobPolicy
    assert local_jobs.check_scratch_budget is local_job_policy.check_scratch_budget
    assert acquisition.AcquisitionError is acquisition_types.AcquisitionError
    assert acquisition.SourceSnapshot is acquisition_types.SourceSnapshot
    assert _local_job_worker.allocated_bytes is local_scratch.allocated_bytes
    policy = local_jobs.LocalJobPolicy(memory_bytes=128 * 1024 ** 2, scratch_bytes=64 * 1024 ** 2)
    assert type(policy) is local_job_policy.LocalJobPolicy
    assert policy.to_dict() == {"memory_bytes": 128 * 1024 ** 2, "scratch_bytes": 64 * 1024 ** 2}
    error = acquisition_types.AcquisitionError("script_boundary_control", phase="local_preflight")
    assert isinstance(error, acquisition.AcquisitionError)
    assert error.code == "script_boundary_control" and error.phase == "local_preflight"

    status = tmp_path / "native-report.json"
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONSAFEPATH"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.update(SERVICE_RESULT="success", EXIT_CODE="exited", EXIT_STATUS="0")
    result = subprocess.run([sys.executable, "-B", str(Path(_local_job_worker.__file__)),
        "report", str(status)], cwd=tmp_path, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "" and result.stderr == ""
    observed = json.loads(status.read_bytes())
    assert set(observed) == {"SERVICE_RESULT", "EXIT_CODE", "EXIT_STATUS", "ended"}
    assert {name: observed[name] for name in ("SERVICE_RESULT", "EXIT_CODE", "EXIT_STATUS")} == {
        "SERVICE_RESULT": "success", "EXIT_CODE": "exited", "EXIT_STATUS": "0"}
    assert set(observed["ended"]) == {"at", "monotonic_ns", "boot_id"}
    assert isinstance(observed["ended"]["at"], str) and observed["ended"]["at"]
    assert type(observed["ended"]["monotonic_ns"]) is int
    assert observed["ended"]["boot_id"] == Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    assert not status.with_name(status.name + ".writing").exists()
