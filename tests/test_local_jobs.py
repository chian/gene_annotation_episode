"""Actual small resource failures; no model calls or biological workflow."""
import asyncio
import os
from pathlib import Path
import signal
import sys
import time

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.local_jobs import (
    LocalJobPolicy, check_scratch_budget, run_local_job, run_local_job_async,
)


MiB = 1024 ** 2


def policy(*, memory=64 * MiB, scratch=4 * MiB):
    return LocalJobPolicy(memory, scratch)


@pytest.fixture
def boundary(tmp_path):
    """Skip actual-unit tests where this operational boundary is unavailable."""
    probe = tmp_path / "preflight"
    probe.mkdir()
    try:
        run_local_job([sys.executable, "-c", "pass"], cwd=probe, policy=policy())
    except AcquisitionError as error:
        if error.code == "local_job_boundary_unavailable":
            pytest.skip("user systemd/cgroup boundary unavailable")
        raise
    return tmp_path


def test_configuration_is_caller_owned_and_closed():
    defaults = LocalJobPolicy.from_config()
    changed = LocalJobPolicy.from_config({"memory_bytes": 64 * MiB})
    assert changed.memory_bytes == 64 * MiB
    assert changed.scratch_bytes == defaults.scratch_bytes
    assert not hasattr(changed, 'wall_seconds')
    assert changed.to_dict() == {'memory_bytes': changed.memory_bytes, 'scratch_bytes': changed.scratch_bytes}
    for settings in ({"memory_bytes": True}, {"scratch_bytes": 0},
                     {"wall_seconds": float("nan")}, {"wall_seconds": -1}, {"wall_seconds": None},
                     {"wall_seconds": 3600}, {"max_turns": 3}, []):
        with pytest.raises(ValueError):
            LocalJobPolicy.from_config(settings)


def test_unavailable_boundary_does_not_execute_or_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.shutil.which", lambda _: None)
    marker = tmp_path / "executed"
    with pytest.raises(AcquisitionError) as caught:
        run_local_job([sys.executable, "-c", f"open({str(marker)!r},'w').close()"],
                      cwd=tmp_path, policy=policy())
    assert caught.value.code == "local_job_boundary_unavailable"
    assert not marker.exists()


def test_output_files_and_native_nonzero_are_not_reclassified(boundary):
    result = run_local_job([sys.executable, "-c",
        "import sys;print('native stdout');print('native stderr',file=sys.stderr);sys.exit(7)"],
        cwd=boundary, policy=policy())
    assert result.returncode == 7
    assert result.stdout_path.read_text() == "native stdout\n"
    assert result.stderr_path.read_text() == "native stderr\n"
    assert result.metadata["verified_cgroup"]["memory_max"] == 64 * MiB
    assert result.metadata["verified_cgroup"]["memory_swap_max"] == 0
    assert result.metadata["service_exit"]["SERVICE_RESULT"] == "exit-code"
    assert not list(boundary.glob(".local-job-*"))



def test_work_time_has_no_configuration_or_systemd_runtime_cap(boundary):
    result = run_local_job([sys.executable, "-c", "print('no work-time cap')"],
        cwd=boundary, policy=LocalJobPolicy(64 * MiB, 4 * MiB))
    assert result.returncode == 0
    assert 'wall_seconds' not in result.metadata['policy']
    assert 'wall_time' not in result.metadata['enforcement']
    assert 'runtime_max' not in result.metadata['verified_cgroup']

@pytest.mark.skipif(os.environ.get("GENE_EPISODE_TEST_OOM") != "1",
    reason="Explicit opt-in: a cgroup OOM test can trigger a desktop application-stopped notification")
def test_actual_memory_limit_reports_proved_cgroup_oom(boundary):
    with pytest.raises(AcquisitionError) as caught:
        run_local_job([sys.executable, "-c",
            "import time; chunks=[]\nwhile True:\n chunks.append(bytearray(8*1024**2));time.sleep(.01)"],
            cwd=boundary, policy=policy(memory=32 * MiB))
    error = caught.value
    assert error.code == "local_job_resource_limit"
    assert error.operational["resource"] == "memory_bytes"
    assert error.operational["limit"] == 32 * MiB
    assert error.operational["evidence"] == {"systemd_service_result": "oom-kill"}
    assert error.operational["verified_cgroup"]["memory_max"] == 32 * MiB
    assert error.operational["service_exit"]["EXIT_STATUS"] == "KILL"
    # Reaching this assertion is also evidence that the host survived intact.


def test_elapsed_time_is_measured_without_a_termination_policy(boundary):
    result = run_local_job(['/bin/sleep', '.15'], cwd=boundary, policy=policy())
    assert result.returncode == 0
    assert result.metadata['elapsed_seconds'] >= .15



def test_normal_native_parent_exit_still_stops_detached_child(boundary):
    child_pid = boundary / "normal-child.pid"
    delayed_marker = boundary / "should-not-be-written"
    child_script = ("import pathlib,time;time.sleep(.3);"
                    f"pathlib.Path({str(delayed_marker)!r}).write_text('escaped')")
    script = ("import pathlib,subprocess,sys;"
              f"child=subprocess.Popen([sys.executable,'-c',{child_script!r}],start_new_session=True);"
              f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid))")
    result = run_local_job([sys.executable, "-c", script], cwd=boundary, policy=policy())
    assert result.returncode == 0
    assert_not_executing(int(child_pid.read_text()))
    time.sleep(.35)
    assert not delayed_marker.exists()

def test_aggregate_scratch_monitor_is_distinct_from_per_file_limit(boundary):
    script = ("import pathlib,time;"
        "pathlib.Path('a').write_bytes(b'x'*700000);"
        "pathlib.Path('b').write_bytes(b'x'*700000);time.sleep(20)")
    with pytest.raises(AcquisitionError) as caught:
        run_local_job([sys.executable, "-c", script], cwd=boundary,
                      policy=policy(scratch=MiB))
    info = caught.value.operational
    assert info["resource"] == "scratch_bytes"
    assert info["evidence"]["observed_allocated_bytes"] > MiB
    assert info["enforcement"]["scratch"] == "monitored_visible_allocated_bytes_with_possible_overshoot"
    assert (boundary / "a").stat().st_size < MiB
    assert (boundary / "b").stat().st_size < MiB


def test_actual_hard_per_file_limit_holds_independently_of_monitor_timing(boundary):
    # CPython normally ignores SIGXFSZ and exposes EFBIG to the application.
    # Default signal disposition makes this kernel-enforced limit observable.
    script = ("import os,signal;signal.signal(signal.SIGXFSZ,signal.SIG_DFL);"
              "fd=os.open('large',os.O_WRONLY|os.O_CREAT,0o600);"
              f"os.write(fd,b'x'*{2*MiB});os.write(fd,b'x')")
    with pytest.raises(AcquisitionError) as caught:
        run_local_job([sys.executable, "-c", script], cwd=boundary,
                      policy=policy(scratch=MiB))
    # The aggregate monitor may notice this file plus control-file blocks
    # before the service publishes its XFSZ status. Neither is a memory failure.
    assert caught.value.operational["resource"] in {"file_bytes", "scratch_bytes"}
    # One oversized write was truncated by the kernel, independently of polling.
    assert (boundary / "large").stat().st_size == MiB


def test_staged_input_check_prevents_known_oversized_copy(tmp_path):
    (tmp_path / "input").write_bytes(b"x" * 4096)
    with pytest.raises(AcquisitionError) as caught:
        check_scratch_budget(tmp_path, policy(scratch=8192), additional_bytes=8192)
    assert caught.value.phase == "local_preflight"
    assert caught.value.operational["evidence"]["stage"] == "staged_inputs"


def test_async_cancellation_waits_for_detached_native_child_cleanup(boundary):
    child_pid = boundary / "async-child.pid"
    script = ("import pathlib,subprocess,sys,time;"
              "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True);"
              f"pathlib.Path({str(child_pid)!r}).write_text(str(child.pid));time.sleep(30)")

    async def exercise():
        task = asyncio.create_task(run_local_job_async([sys.executable, "-c", script],
                                  cwd=boundary, policy=policy()))
        for _ in range(200):
            if child_pid.exists():
                break
            if task.done():
                await task
            await asyncio.sleep(.01)
        assert child_pid.exists()
        task.cancel()
        asyncio.get_running_loop().call_later(.001, task.cancel)
        with pytest.raises(asyncio.CancelledError):
            await task
        assert_not_executing(int(child_pid.read_text()))

    asyncio.run(exercise())


def assert_not_executing(pid):
    path = Path(f"/proc/{pid}/status")
    if path.exists():
        # A dead child may briefly be a zombie awaiting its system reaper.
        state = next(line for line in path.read_text().splitlines() if line.startswith("State:"))
        assert "Z" in state
