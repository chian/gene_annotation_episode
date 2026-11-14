"""Stage exact inputs, invoke one worker, and seal its actual terminal files.

The selected caller's existing native lifecycle owns execution and limits. This
driver has no loop, retries, independent resources, scientific grader or credit.
Unsealed interrupted work is uncertain; it cannot be silently invoked again.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import traceback

from .execution_contracts import canonical
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_rna_structure_contracts import (ATTEMPT_DIRECTORY_NAME, BUNDLE_FILENAME, INPUT_NAMES,
    OWNER_FILENAME, STARTED_FILENAME, _path, compile_rna_structure_job, realized_environment,
    validate_rna_structure_bundle, validate_rna_structure_run_plan)
from .practical_execution_state import _immutable, _read
from .rna_structure_contracts import issue, validate_rna_native_record


def _directory(value):
    _path(str(value), absolute=True)
    path = Path(value)
    if path.resolve() != path or path.is_symlink() or path.exists() and not path.is_dir():
        raise ValueError("rna_output_path_conflict")
    return path


def confined_file(directory, relative_path):
    """Reject traversal, any symlink component and nonregular file endpoints."""
    directory = _directory(directory)
    _path(relative_path, absolute=False)
    path = directory / relative_path
    if path.resolve() != path or path.is_symlink() or path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("rna_output_path_conflict")
    return path


def _regular(path):
    path = Path(path)
    if path.resolve() != path or path.is_symlink():
        raise ValueError("rna_output_path_conflict")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("rna_output_path_conflict")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


def file_identity(path):
    with _regular(path) as stream:
        size = os.fstat(stream.fileno()).st_size
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"sha256": sha, "size_bytes": size}


def _strict_json(path):
    from .native_rna_structure_worker import _strict_json as read_json
    with _regular(path) as stream:
        return read_json(stream.read())


def _stage(operand, *, index, directory, policy, stderr):
    destination = confined_file(directory, INPUT_NAMES[operand["role"]])
    temporary = confined_file(directory, ".staging-" + operand["role"])
    with _regular(operand["path"]) as source:
        check_scratch_budget(directory, policy, additional_bytes=os.fstat(source.fileno()).st_size)
        with temporary.open("xb") as target:
            while block := source.read(1024 * 1024):
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
    actual = file_identity(temporary)
    if actual != {key: operand[key] for key in ("sha256", "size_bytes")}:
        # A rejected candidate is NOT published as the original scientific
        # input. Its complete bytes remain lossless diagnostics, never parser
        # operands. Each base64 chunk is independently decodable and ordered.
        header = {"schema": "rna_rejected_input_v1", "role": operand["role"],
            "expected": {key: operand[key] for key in ("sha256", "size_bytes")},
            "observed": actual, "encoding": "base64_chunks_in_byte_order"}
        stderr.write((canonical(header) + "\n").encode())
        with temporary.open("rb") as source:
            offset = 0
            while block := source.read(48 * 1024):
                stderr.write((canonical({"schema": "rna_rejected_input_chunk_v1", "role": operand["role"],
                    "offset": offset, "bytes_base64": base64.b64encode(block).decode("ascii")}) + "\n").encode())
                offset += len(block)
        stderr.flush()
        raise ValueError("rna_input_identity_mismatch")
    os.link(temporary, destination)
    temporary.unlink()


def _manifest_rows(job):
    return [{"kind": "input", "role": row["role"], "format": row["format"],
        "relative_path": INPUT_NAMES[row["role"]], "state": "absent", "sha256": None, "size_bytes": None}
        for row in job["operands"]] + [{"kind": "output", **row,
        "state": "absent", "sha256": None, "size_bytes": None} for row in job["outputs"]]


def _replay(directory, plan):
    bundle = validate_rna_structure_bundle(_read(confined_file(directory, BUNDLE_FILENAME)), plan=plan)
    for row in bundle["files"]:
        path = confined_file(directory, row["relative_path"])
        if row["state"] == "present":
            if file_identity(path) != {key: row[key] for key in ("sha256", "size_bytes")}:
                raise ValueError("rna_capture_digest_mismatch")
        elif path.exists():
            raise ValueError("rna_capture_digest_mismatch")
    return bundle


def run_rna_structure_driver(plan: dict) -> dict:
    """Execute the already selected native worker once inside its existing job."""
    plan = validate_rna_structure_run_plan(plan)
    directory = _directory(plan["attempt_directory"])
    directory.mkdir(parents=True, exist_ok=True)
    owner = confined_file(directory, OWNER_FILENAME)
    if owner.exists():
        if _read(owner) != plan:
            raise ValueError("rna_original_attempt_mismatch")
    elif any(directory.iterdir()):
        raise ValueError("rna_output_path_conflict")
    _immutable(owner, plan)
    if confined_file(directory, BUNDLE_FILENAME).exists():
        return _replay(directory, plan)
    marker = confined_file(directory, STARTED_FILENAME)
    if marker.exists():
        raise ValueError("rna_unsealed_native_attempt")
    now = datetime.now(timezone.utc).isoformat()
    # Non-identical concurrent publication conflicts, and a prior unsealed
    # marker is never permission to start a replacement process.
    _immutable(marker, {"plan": plan, "started_at": now})
    job = plan["requested_job"]["native_rna_structure"]
    policy = LocalJobPolicy(**plan["policy"])
    compiled = compile_rna_structure_job(job, input_paths={row["role"]: str(directory / INPUT_NAMES[row["role"]])
        for row in job["operands"]}, output_directory=str(directory))
    environment = realized_environment(job, str(directory))
    bundle = {"version": "native_rna_structure_bundle_v1", "identity": plan["identity"],
        "requested_job": plan["requested_job"], **{key: job[key] for key in ("program", "operation", "mode", "record_key", "software")},
        "realized_argv": compiled["argv"], "environment": environment, "files": _manifest_rows(job),
        "returncode": None, "native_status": "failed", "failures": [], "started_at": now,
        "finished_at": now, "sealed": True}
    outputs = {row["role"]: confined_file(directory, row["relative_path"]) for row in job["outputs"]}
    for path in outputs.values():
        if path.exists():
            raise ValueError("rna_output_path_conflict")
        path.parent.mkdir(parents=True, exist_ok=True)
    for name in ("tmp", "cache"):
        _directory(directory / name).mkdir(exist_ok=True)
    with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
        staged = True
        for index, operand in enumerate(job["operands"]):
            try:
                _stage(operand, index=index, directory=directory, policy=policy, stderr=stderr)
            except Exception as error:
                staged = False
                stderr.write(traceback.format_exc().encode("utf-8"))
                code = str(error) if str(error) in ("rna_input_identity_mismatch", "rna_output_path_conflict") else "rna_capture_unavailable"
                bundle["failures"].append(issue(code, stage="input", record_key=job["record_key"],
                    field=f"/operands/{index}", artifact_role=operand["role"]))
        if staged:
            try:
                # This is one subprocess within the already bounded selected
                # lifecycle, not a second resource selection or submission.
                result = subprocess.run(compiled["argv"], cwd=directory, env={**os.environ, **environment},
                    stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL, check=False)
                bundle["returncode"] = result.returncode
            except Exception:
                stderr.write(traceback.format_exc().encode("utf-8"))
                bundle["failures"].append(issue("rna_native_failed", stage="native", record_key=job["record_key"]))
        stdout.flush()
        stderr.flush()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    native_path = outputs["native_result"]
    if native_path.exists():
        try:
            record = validate_rna_native_record(_strict_json(native_path), expected_mode=job["mode"])
            if record["record_key"] != job["record_key"]:
                raise ValueError("rna_input_identity_mismatch")
            bundle["native_status"] = record["status"]
            bundle["failures"].extend(record["issues"])
        except (ValueError, TypeError, OSError):
            bundle["failures"].append(issue("rna_invalid_native_schema", stage="native", record_key=job["record_key"],
                artifact_role="native_result"))
    if bundle["returncode"] != 0 and not any(row["code"] != "no_sequence_supplied" for row in bundle["failures"]):
        bundle["failures"].append(issue("rna_native_failed", stage="native", record_key=job["record_key"]))
    for index, row in enumerate(bundle["files"]):
        path = confined_file(directory, row["relative_path"])
        if path.exists():
            row.update(state="present", **file_identity(path))
        else:
            bundle["failures"].append(issue("rna_native_result_missing" if row["role"] == "native_result" else
                "rna_model_snapshot_missing" if row["role"] in ("model", "effective_parameters") else "rna_capture_unavailable",
                stage="native" if row["kind"] == "output" else "input", record_key=job["record_key"],
                field=f"/files/{index}", artifact_role=row["role"]))
    if bundle["native_status"] == "complete" and (bundle["returncode"] != 0 or
            any(row["state"] == "absent" for row in bundle["files"])):
        bundle["native_status"] = "failed"
    # A zero worker exit without a complete declared native record is an
    # inconsistent worker outcome. Preserve the actual exit, never rewrite it.
    if bundle["returncode"] == 0 and bundle["native_status"] != "complete":
        bundle["failures"].append(issue("rna_native_result_incompatible", stage="native", record_key=job["record_key"]))
    bundle["finished_at"] = datetime.now(timezone.utc).isoformat()
    bundle = validate_rna_structure_bundle(bundle, plan=plan)
    _immutable(confined_file(directory, BUNDLE_FILENAME), bundle)
    return bundle


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise ValueError("rna_original_attempt_mismatch")
    plan = validate_rna_structure_run_plan(_read(Path(args[0])))
    bundle = run_rna_structure_driver(plan)
    return 0 if bundle["native_status"] == "complete" and bundle["returncode"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
