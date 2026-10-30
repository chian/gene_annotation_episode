"""Stage only selected bytes, invoke one worker and seal one immutable attempt.

The existing local lifecycle owns resource enforcement. This is a single native
primitive with no retry, scheduler, episode loop or numerical scoring logic.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import time
import traceback

from .execution_contracts import canonical
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .acquisition import AcquisitionError
from .protein_structure_contracts import issue, same
from .native_protein_structure_contracts import (
    BUNDLE_FILENAME, RUN_PLAN_FILENAME, WORKER_INPUT_FILENAME, OWNER_FILENAME,
    STARTED_FILENAME, _path, _require, compile_protein_structure_job, driver_argv,
    manifest_files, realized_environment, validate_protein_structure_bundle,
    validate_protein_structure_run_plan, validate_native_protein_structure_result,
    validate_protein_structure_worker_input,
)


def _directory(value):
    _path(str(value), absolute=True)
    path = Path(value)
    _require(path.resolve() == path and not path.is_symlink() and
        (not path.exists() or path.is_dir()), "invalid_output_path")
    return path


def confined_file(directory, relative_path):
    directory = _directory(directory)
    _path(relative_path, absolute=False)
    path = directory / relative_path
    _require(path.resolve() == path and not path.is_symlink() and
        (not path.exists() or stat.S_ISREG(path.lstat().st_mode)), "invalid_output_path")
    return path


def _regular(path):
    path = Path(path)
    _require(path.resolve() == path and not path.is_symlink(), "invalid_output_path")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def file_identity(path):
    with _regular(path) as stream:
        size = os.fstat(stream.fileno()).st_size
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"sha256": sha, "byte_length": size}


def _strict_json(path):
    from .native_protein_structure_worker import strict_json
    with _regular(path) as stream:
        return strict_json(stream.read())


def immutable_bytes(path: Path, data: bytes):
    """Exclusive publication with idempotent exact-byte replay."""
    path = confined_file(path.parent, path.name)
    if path.exists():
        with _regular(path) as stream:
            _require(stream.read() == data, "original_commission_mismatch")
        return
    temporary = confined_file(path.parent, "." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _immutable(path, value):
    immutable_bytes(path, canonical(value).encode("utf-8"))


def _stage(row, *, directory, policy, stderr):
    destination = confined_file(directory, row["staged_relative_path"])
    temporary = confined_file(directory, "inputs/.staging-" + row["input_id"])
    expected = {k: row["file_identity"][k] for k in ("sha256", "byte_length")}
    with _regular(row["path"]) as source:
        source_size = os.fstat(source.fileno()).st_size
        check_scratch_budget(directory, policy, additional_bytes=source_size)
        with temporary.open("xb") as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
    observed = file_identity(temporary)
    if observed != expected:
        # Reject the candidate as a scientific operand, but retain every original
        # byte in the complete stderr artifact for repair/audit.
        stderr.write((canonical({"version": "protein_structure_rejected_input_v1", "input_id": row["input_id"],
            "expected": expected, "observed": observed, "encoding": "base64_chunks_in_byte_order"}) + "\n").encode())
        with _regular(temporary) as source:
            offset = 0
            while chunk := source.read(48 * 1024):
                stderr.write((canonical({"input_id": row["input_id"], "offset_0based": offset,
                    "bytes_base64": base64.b64encode(chunk).decode("ascii")}) + "\n").encode())
                offset += len(chunk)
        stderr.flush()
        temporary.unlink()
        raise ValueError("input_digest_mismatch")
    os.link(temporary, destination)
    temporary.unlink()


def _replay(directory, plan):
    bundle = validate_protein_structure_bundle(_strict_json(confined_file(directory, BUNDLE_FILENAME)), plan=plan)
    for row in bundle["files"]:
        path = confined_file(directory, row["relative_path"])
        if row["state"] == "present":
            _require(file_identity(path) == {k: row[k] for k in ("sha256", "byte_length")}, "input_digest_mismatch")
        else:
            _require(not path.exists(), "capture_incomplete")
    return bundle


def run_protein_structure_driver(plan: dict) -> dict:
    """Execute an already selected, reserved attempt once in its local boundary."""
    plan = validate_protein_structure_run_plan(plan)
    directory = _directory(plan["attempt_directory"])
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner = confined_file(directory, OWNER_FILENAME)
    if owner.exists():
        _require(same(_strict_json(owner), plan), "original_commission_mismatch")
    else:
        _require(not any(directory.iterdir()), "invalid_output_path")
        _immutable(owner, plan)
    if confined_file(directory, BUNDLE_FILENAME).exists():
        return _replay(directory, plan)
    marker = confined_file(directory, STARTED_FILENAME)
    _require(not marker.exists(), "native_process_failed")
    started_at = datetime.now(timezone.utc).isoformat()
    driver_start = time.monotonic()
    _immutable(marker, {"plan": plan, "started_at": started_at})
    for name in ("inputs", "tmp", "cache"):
        _directory(directory / name).mkdir(exist_ok=True)
    job = plan["requested_job"]["native_protein_structure"]
    policy = LocalJobPolicy(**plan["policy"])
    compiled = compile_protein_structure_job(job,
        input_paths={r["input_id"]: str(directory / r["staged_relative_path"]) for r in job["inputs"]},
        output_directory=str(directory))
    environment = realized_environment(job, str(directory))
    bundle = {"version": "native_protein_structure_bundle_v1", "identity": plan["identity"],
        "requested_job": plan["requested_job"], "software": job["software"], "driver_argv": driver_argv(plan),
        "worker_argv": None, "realized_environment": environment,
        "files": [{**r, "state": "absent", "sha256": None, "byte_length": None} for r in manifest_files(job)],
        "returncode": None, "native_status": "failed", "started_at": started_at, "finished_at": started_at,
        "measured_duration": {"seconds": None, "kind": "unmeasured", "source": "none"}, "failures": [], "sealed": True}
    outputs = {r["role"]: confined_file(directory, r["relative_path"]) for r in job["outputs"]}
    _require(not any(p.exists() for p in outputs.values()), "invalid_output_path")
    with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
        controls_ready = True
        try:
            original_path = confined_file(Path(plan["identity"]["execution_id"]).parent, RUN_PLAN_FILENAME)
            with _regular(original_path) as stream:
                original_bytes = stream.read()
            _require(same(_strict_json(original_path), plan), "original_commission_mismatch")
            immutable_bytes(confined_file(directory, RUN_PLAN_FILENAME), original_bytes)
            worker_input = validate_protein_structure_worker_input({"version": "protein_structure_worker_input_v1",
                "request": job["request"], "software": job["software"], "files": [
                    {"input_id": r["input_id"], "role": r["role"], "file_identity": r["file_identity"],
                     "path": str(directory / r["staged_relative_path"])} for r in job["inputs"]]})
            _immutable(confined_file(directory, WORKER_INPUT_FILENAME), worker_input)
            # Interpreter paths commonly are virtualenv symlinks; selected input
            # data paths are separately required to be regular confined files.
            with open(job["software"]["python_executable"], "rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            _require(actual == job["software"]["python_sha256"] and os.access(job["software"]["python_executable"], os.X_OK), "software_identity_mismatch")
        except Exception as error:
            controls_ready = False
            stderr.write(traceback.format_exc().encode())
            code = str(error) if str(error) in ("original_commission_mismatch", "software_identity_mismatch", "invalid_output_path") else "capture_incomplete"
            bundle["failures"].append(issue(code, stage="native", field="software" if code == "software_identity_mismatch" else "request"))
        staged = True
        for row in job["inputs"]:
            try:
                _stage(row, directory=directory, policy=policy, stderr=stderr)
            except Exception as error:
                staged = False
                stderr.write(traceback.format_exc().encode())
                code = ("resource_budget_exceeded" if isinstance(error, AcquisitionError) else
                    str(error) if str(error) in ("input_digest_mismatch", "invalid_output_path") else "retained_artifact_missing")
                bundle["failures"].append(issue(code, stage="input", field="file_identity", artifact_role=row["role"]))
        if staged and controls_ready:
            try:
                check_scratch_budget(directory, policy)
                worker_start = time.monotonic()
                process = subprocess.Popen(compiled["argv"], cwd=directory, env={**os.environ, **environment},
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
                bundle["worker_argv"] = compiled["argv"]
                bundle["returncode"] = process.wait()
                bundle["measured_duration"] = {"seconds": time.monotonic() - worker_start, "kind": "worker_wall", "source": "monotonic_clock"}
                if bundle["returncode"] != 0:
                    bundle["failures"].append(issue("native_process_failed", stage="native", field="returncode"))
                check_scratch_budget(directory, policy)
            except Exception as error:
                stderr.write(traceback.format_exc().encode())
                code = "resource_budget_exceeded" if isinstance(error, AcquisitionError) else "native_process_failed"
                bundle["failures"].append(issue(code, stage="native", field="returncode"))
        stdout.flush()
        stderr.flush()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    valid_native = False
    if outputs["native_result"].exists():
        try:
            result = validate_native_protein_structure_result(_strict_json(outputs["native_result"]))
            _require(same(result["request"], job["request"]) and same(result["producer"], job["software"]), "original_commission_mismatch")
            valid_native = True
        except (ValueError, TypeError, OSError):
            bundle["failures"].append(issue("invalid_schema", stage="native", artifact_role="native_result"))
    for row in bundle["files"]:
        try:
            path = confined_file(directory, row["relative_path"])
            if path.exists():
                row.update(state="present", **file_identity(path))
                continue
        except (ValueError, OSError):
            pass
        bundle["failures"].append(issue("native_result_missing" if row["role"] == "native_result" else "capture_incomplete",
            stage="capture", field="manifest", artifact_role=row["role"]))
    # Scientific availability is in the native result. A valid partial sheet is
    # not rewritten to native process failure when its worker completed normally.
    bundle["native_status"] = ("complete" if valid_native and bundle["returncode"] == 0 and not bundle["failures"]
        else "partial" if valid_native else "failed")
    if not bundle["failures"] and bundle["native_status"] != "complete":
        bundle["failures"].append(issue("native_process_failed", stage="native"))
    if bundle["measured_duration"]["kind"] == "unmeasured":
        bundle["measured_duration"] = {"seconds": time.monotonic() - driver_start, "kind": "driver_wall", "source": "monotonic_clock"}
    bundle["finished_at"] = datetime.now(timezone.utc).isoformat()
    bundle = validate_protein_structure_bundle(bundle, plan=plan)
    _immutable(confined_file(directory, BUNDLE_FILENAME), bundle)
    return bundle


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    _require(len(args) == 1, "original_commission_mismatch")
    plan = validate_protein_structure_run_plan(_strict_json(Path(args[0])))
    _require(args[0] == driver_argv(plan)[-1], "original_commission_mismatch")
    bundle = run_protein_structure_driver(plan)
    return 0 if bundle["native_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
