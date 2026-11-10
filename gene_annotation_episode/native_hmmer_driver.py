"""One selected native HMMER attempt, run inside the caller's resource boundary.

The existing durable local/PBS lifecycle owns process lifetime and hard limits.
This producer stages exact operands, invokes one subprocess, retains complete
files and seals a manifest. It has no model, retry, polling or resource choice.
A killed producer can leave an unsealed attempt; that uncertainty never permits
another invocation of the selected command. The CLI accepts exactly one plan.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from ._local_job_worker import allocated_bytes
from .native_hmmer_contracts import (
    CHECKPOINT_ROLES, PRESSED_SUFFIXES, compile_native_hmmer_job,
    finite_json_copy, native_hmmer_digest, validate_native_hmmer_requested_job,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _atomic_new(path, value):
    """Atomic immutable publication: link cannot replace an existing manifest."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2).encode() + b"\n"
    temporary = path.with_name("." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_json(path):
    with path.open("rb") as stream:
        return finite_json_copy(json.load(stream))


def _digest_file(path):
    hasher, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("native_hmmer_regular_file_required")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            hasher.update(block)
    return size, hasher.hexdigest()


def _validate_plan(value):
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job", "attempt_directory", "policy"}
            or plan["version"] != "native_hmmer_run_plan_v1"):
        raise ValueError("native_hmmer_run_plan_required")
    identity = plan["identity"]
    keys = {"run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key", "requested_job_sha256"}
    if type(identity) is not dict or set(identity) != keys or any(type(v) is not str or not v or "\0" in v for v in identity.values()):
        raise ValueError("native_hmmer_complete_attempt_identity_required")
    request = validate_native_hmmer_requested_job(plan["requested_job"])
    if identity["requested_job_sha256"] != native_hmmer_digest(request):
        raise ValueError("native_hmmer_requested_job_digest_mismatch")
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        raise ValueError("native_hmmer_explicit_policy_required")
    from .local_jobs import LocalJobPolicy
    LocalJobPolicy(**policy)  # Validate the supplied allocation; never replace it.
    name = plan["attempt_directory"]
    if (type(name) is not str or not Path(name).is_absolute() or str(Path(name)) != name
            or ".." in Path(name).parts or any(c in name for c in ("\0", "\n", "\r"))):
        raise ValueError("native_hmmer_absolute_attempt_directory_required")
    root = Path(name)
    if root.resolve() != root:
        raise ValueError("native_hmmer_attempt_symlink_forbidden")
    return plan


def _failure(bundle, stage, code, role=None, **detail):
    bundle["failures"].append({"stage": stage, "code": code, "role": role, "detail": detail})


def _scratch(root, policy):
    observed = allocated_bytes(root)
    if observed > policy["scratch_bytes"]:
        raise _ScratchLimit(observed, policy["scratch_bytes"])


class _ScratchLimit(Exception):
    def __init__(self, observed, limit):
        self.observed, self.limit = observed, limit
        super().__init__("native_hmmer_scratch_limit")


def _staged_relative(operand):
    role = operand["role"]
    if role.startswith("profile_database_h3"):
        return "inputs/profile_database.hmm." + role.rsplit("_", 1)[1]
    extension = {"fasta": "fa", "stockholm": "sto", "hmmer3_ascii": "hmm"}[operand["format"]]
    return "inputs/" + role + "." + extension


def _stage_input(root, operand, policy, row):
    source, destination = Path(operand["path"]), root / row["relative_path"]
    with source.open("rb") as reader:
        info = os.fstat(reader.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("native_hmmer_regular_input_required")
        row["size_bytes"] = info.st_size
        if info.st_size != operand["size_bytes"]:
            raise ValueError("native_hmmer_input_size_mismatch")
        observed = allocated_bytes(root)
        if observed + info.st_size > policy["scratch_bytes"]:
            raise _ScratchLimit(observed + info.st_size, policy["scratch_bytes"])
        hasher, copied = hashlib.sha256(), 0
        with destination.open("xb") as writer:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                copied += len(block)
                writer.write(block)
                writer.flush()
                hasher.update(block)
                _scratch(root, policy)
            os.fsync(writer.fileno())
        row["size_bytes"], row["actual_sha256"] = copied, hasher.hexdigest()
        if copied != operand["size_bytes"]:
            raise ValueError("native_hmmer_input_changed_size_during_capture")
        if row["actual_sha256"].lower() != operand["sha256"].lower():
            raise ValueError("native_hmmer_input_digest_mismatch")


def _validate_input_format(path, fmt, *, single_profile=False):
    """Validate format framing; scientific parsing remains with native/readers."""
    if fmt.startswith("hmmer_h3"):
        if path.stat().st_size == 0:
            raise ValueError("native_hmmer_empty_pressed_index")
        return
    if fmt == "hmmer3_ascii":
        starts, ends, opened = 0, 0, False
        with path.open("rb") as stream:
            for line in stream:
                if line.startswith(b"HMMER3/"):
                    if opened:
                        raise ValueError("native_hmmer_unterminated_profile")
                    starts += 1
                    opened = True
                elif line.strip() == b"//":
                    if not opened:
                        raise ValueError("native_hmmer_invalid_profile_framing")
                    ends += 1
                    opened = False
                elif line.strip() and not opened:
                    raise ValueError("native_hmmer_invalid_profile_framing")
        if starts == 0 or starts != ends or opened:
            raise ValueError("native_hmmer_incomplete_profile_input")
        if single_profile and starts != 1:
            raise ValueError("native_hmmer_hmmalign_exactly_one_profile_required")
    elif fmt == "stockholm":
        with path.open("rb") as stream:
            first = next((line.strip() for line in stream if line.strip()), b"")
            if first != b"# STOCKHOLM 1.0":
                raise ValueError("native_hmmer_stockholm_input_required")
    else:
        with path.open("rb") as stream:
            first = next((line.strip() for line in stream if line.strip()), b"")
            if not first.startswith(b">") or len(first) == 1:
                raise ValueError("native_hmmer_fasta_input_required")


def _confined_file(root, relative):
    path = root / relative
    if path.resolve() != path or not path.is_relative_to(root) or path == root:
        raise ValueError("native_hmmer_output_path_escape")
    if path.exists() and not path.is_file():
        raise ValueError("native_hmmer_output_not_regular_file")
    return path


def validate_native_hmmer_bundle_files(bundle, directory):
    """Verify saved bytes without changing a manifest or recapturing an output."""
    root = Path(directory)
    for row in bundle["artifacts"]:
        path = _confined_file(root, row["relative_path"])
        size, digest = _digest_file(path)
        if size != row["size_bytes"] or digest != row["sha256"]:
            raise ValueError("native_hmmer_sealed_artifact_digest_mismatch:" + row["relative_path"])
    return finite_json_copy(bundle)


def _collect_outputs(root, job, bundle):
    for output in job["outputs"]:
        role, relative = output["role"], output["relative_path"]
        if role in CHECKPOINT_ROLES:
            prefix = root / relative
            pattern = re.compile(re.escape(prefix.name) + r"-[1-9][0-9]*" + re.escape(CHECKPOINT_ROLES[role]) + r"$")
            try:
                if prefix.parent.resolve() != prefix.parent or not prefix.parent.is_relative_to(root):
                    raise ValueError("native_hmmer_checkpoint_directory_escape")
                paths = sorted(path for path in prefix.parent.iterdir() if pattern.fullmatch(path.name))
            except (OSError, ValueError) as error:
                _failure(bundle, "outputs", "native_hmmer_checkpoint_files_unavailable", role, reason=str(error))
                continue
        else:
            paths = [root / relative]
        if not paths:
            _failure(bundle, "outputs", "native_hmmer_missing_output", role, relative_path=relative)
        for candidate in paths:
            name = candidate.relative_to(root).as_posix()
            try:
                path = _confined_file(root, name)
                size, digest = _digest_file(path)
            except FileNotFoundError:
                _failure(bundle, "outputs", "native_hmmer_missing_output", role, relative_path=name)
            except (OSError, ValueError) as error:
                _failure(bundle, "outputs", "native_hmmer_invalid_output", role,
                         relative_path=name, reason=str(error))
            else:
                bundle["artifacts"].append({"role": role, "format": output["format"],
                    "relative_path": name, "size_bytes": size, "sha256": digest})


def run_native_hmmer(plan) -> dict:
    plan = _validate_plan(plan)
    root, request = Path(plan["attempt_directory"]), plan["requested_job"]
    job = request["native_hmmer"]
    owner, manifest_path = root / ".native-hmmer-owner.json", root / "bundle.json"
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if not owner.is_file():
            raise ValueError("native_hmmer_attempt_not_exclusively_owned")
        if _read_json(owner) != plan:
            raise ValueError("native_hmmer_attempt_identity_conflict")
        if not manifest_path.is_file():
            raise ValueError("native_hmmer_unsealed_attempt_execution_uncertain")
        saved = _read_json(manifest_path)
        if (saved.get("identity") != plan["identity"] or saved.get("requested_job") != request
                or saved.get("version") != "native_hmmer_bundle_v1"):
            raise ValueError("native_hmmer_sealed_manifest_identity_conflict")
        return validate_native_hmmer_bundle_files(saved, root)
    _atomic_new(owner, plan)
    bundle = {"version": "native_hmmer_bundle_v1", "identity": plan["identity"],
        "requested_job": request, "program": job["program"], "mode": job["mode"],
        "software": {"executable": job["software"]["executable"], "expected_sha256": job["software"]["sha256"],
                     "actual_sha256": None, "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": [], "environment": {}, "inputs": [], "operand_bindings": job["operand_bindings"],
        "returncode": None, "artifacts": [], "failures": [], "started_at": _now(), "finished_at": None}
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    paths = {row["role"]: str(root / _staged_relative(row)) for row in job["operands"]}
    compiled = compile_native_hmmer_job(job, input_paths=paths, output_directory=str(root))
    bundle["realized_argv"] = compiled["argv"]
    bundle["environment"] = {**compiled["environment"], "TMPDIR": str(root / "tmp"),
        "TMP": str(root / "tmp"), "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache")}
    try:
        _, actual_sha = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual_sha
        if actual_sha.lower() != job["software"]["sha256"].lower():
            _failure(bundle, "software", "native_hmmer_software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software", "native_hmmer_software_not_executable")
    except (OSError, ValueError) as error:
        _failure(bundle, "software", "native_hmmer_software_unavailable", reason=str(error))
    for operand in job["operands"]:
        row = {"role": operand["role"], "format": operand["format"], "original_path": operand["path"],
            "relative_path": _staged_relative(operand), "artifact_ref": operand["artifact_ref"],
            "expected_sha256": operand["sha256"], "actual_sha256": None,
            "expected_size_bytes": operand["size_bytes"], "size_bytes": None}
        bundle["inputs"].append(row)
        try:
            _stage_input(root, operand, plan["policy"], row)
            _validate_input_format(root / row["relative_path"], operand["format"],
                                   single_profile=job["program"] == "hmmalign" and operand["role"] == "profile")
        except _ScratchLimit as error:
            _failure(bundle, "staging", "native_hmmer_scratch_limit", operand["role"],
                     observed_bytes=error.observed, limit_bytes=error.limit)
        except FileNotFoundError:
            _failure(bundle, "inputs", "native_hmmer_input_missing", operand["role"])
        except (OSError, ValueError) as error:
            _failure(bundle, "inputs", str(error) if isinstance(error, ValueError) else "native_hmmer_input_io_error",
                     operand["role"], **({"errno": error.errno} if isinstance(error, OSError) else {}))
    outputs = {row["role"]: root / row["relative_path"] for row in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            stdout_role = "stockholm" if job["program"] == "hmmalign" else "stdout"
            with outputs[stdout_role].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                # This single wait is for this selected native command only. The
                # caller's existing lifecycle enforces its supplied allocation.
                outcome = subprocess.run(compiled["argv"], cwd=root, env=bundle["environment"],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
            bundle["returncode"] = outcome.returncode
            if outcome.returncode:
                _failure(bundle, "execution", "native_hmmer_nonzero_returncode", returncode=outcome.returncode)
            _scratch(root, plan["policy"])
        except _ScratchLimit as error:
            _failure(bundle, "execution", "native_hmmer_scratch_limit",
                     observed_bytes=error.observed, limit_bytes=error.limit)
        except OSError as error:
            _failure(bundle, "execution", "native_hmmer_command_unavailable", errno=error.errno)
    _collect_outputs(root, job, bundle)
    bundle["finished_at"] = _now()
    _atomic_new(manifest_path, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise ValueError("native_hmmer_exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_hmmer(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / "bundle.json")}))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
