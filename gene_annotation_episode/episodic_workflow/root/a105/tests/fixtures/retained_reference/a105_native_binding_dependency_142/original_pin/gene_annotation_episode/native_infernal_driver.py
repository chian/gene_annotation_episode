"""Produce the retained files from one selected Infernal invocation.

The existing native lifecycle owns process lifetime and the supplied allocation.
This module stages exact inputs, invokes one command, and seals its original
outcome. It does not grade, poll, retry, prepare indexes, or select resources.
An interrupted, unsealed attempt is uncertain and is never invoked again.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys

from ._local_job_worker import allocated_bytes
from .local_jobs import LocalJobPolicy
from .native_infernal_contracts import (
    PRESSED_SUFFIXES, compile_native_infernal_job, finite_json_copy,
    native_infernal_digest, validate_native_infernal_requested_job,
)


_IDENTITY_FIELDS = {"run_id", "episode_id", "resource_id", "execution_id",
    "attempt_id", "operation_key", "requested_job_sha256"}
_BUNDLE_FIELDS = {"version", "identity", "requested_job", "program", "table_format",
    "software", "realized_argv", "environment", "inputs", "operand_bindings",
    "returncode", "artifacts", "failures", "started_at", "finished_at"}
_INPUT_FIELDS = {"role", "format", "original_path", "relative_path", "artifact_ref",
    "expected_sha256", "actual_sha256", "expected_size_bytes", "size_bytes"}
_ARTIFACT_FIELDS = {"role", "format", "relative_path", "size_bytes", "sha256"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
        allow_nan=False, indent=2) + "\n").encode("utf-8")


def _atomic_new(path, value):
    """Publish fully written bytes without replacing an existing record."""
    temporary = path.with_name("." + path.name + ".writing")
    with temporary.open("xb") as stream:
        stream.write(_encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _regular_reader(path):
    # O_NONBLOCK prevents a FIFO supplied as a file from hanging validation.
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("native_infernal_regular_file_required")
        return os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise


def _read_json(path, *, sealed=False):
    with _regular_reader(path) as stream:
        raw = stream.read()
    value = finite_json_copy(json.loads(raw))
    if sealed and raw != _encoded(value):
        raise ValueError("native_infernal_sealed_record_bytes_changed")
    return value


def _digest_file(path):
    hasher, size = hashlib.sha256(), 0
    with _regular_reader(path) as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(block)
            hasher.update(block)
    return size, hasher.hexdigest()


def _absolute_directory(value):
    if (type(value) is not str or not Path(value).is_absolute()
            or str(Path(value)) != value or ".." in Path(value).parts
            or value == "/" or any(c in value for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_infernal_absolute_attempt_directory_required")
    root = Path(value)
    if root.resolve() != root or root.is_symlink():
        raise ValueError("native_infernal_attempt_symlink_forbidden")
    if root.exists() and not root.is_dir():
        raise ValueError("native_infernal_attempt_directory_required")
    return root


def _validate_identity(identity, request):
    if (type(identity) is not dict or set(identity) != _IDENTITY_FIELDS
            or any(type(v) is not str or not v or "\0" in v for v in identity.values())):
        raise ValueError("native_infernal_complete_attempt_identity_required")
    if identity["requested_job_sha256"] != native_infernal_digest(request):
        raise ValueError("native_infernal_requested_job_digest_mismatch")
    if identity["attempt_id"] != native_infernal_digest(identity["operation_key"]):
        raise ValueError("native_infernal_attempt_operation_identity_conflict")


def _validate_plan(value):
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job",
            "attempt_directory", "policy"} or plan["version"] != "native_infernal_run_plan_v1"):
        raise ValueError("native_infernal_run_plan_required")
    request = validate_native_infernal_requested_job(plan["requested_job"])
    _validate_identity(plan["identity"], request)
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {"memory_bytes", "scratch_bytes", "wall_seconds"}:
        raise ValueError("native_infernal_explicit_policy_required")
    LocalJobPolicy(**policy)
    _absolute_directory(plan["attempt_directory"])
    return plan


def _confined_file(root, relative):
    if (type(relative) is not str or not relative or PurePosixPath(relative).is_absolute()
            or str(PurePosixPath(relative)) != relative or relative == "."
            or ".." in relative.split("/") or any(c in relative for c in ("\0", "\n", "\r", "\\"))):
        raise ValueError("native_infernal_artifact_path_escape")
    path = root / relative
    if path.resolve() != path or path.is_symlink() or not path.is_relative_to(root):
        raise ValueError("native_infernal_artifact_path_escape")
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("native_infernal_artifact_not_regular_file")
    return path


def _failure(bundle, stage, code, role=None, **detail):
    bundle["failures"].append({"stage": stage, "code": code, "role": role, "detail": detail})


class _ScratchLimit(Exception):
    def __init__(self, observed, limit):
        self.observed, self.limit = observed, limit
        super().__init__("native_infernal_scratch_limit")


def _scratch(root, policy, additional=0):
    observed = allocated_bytes(root) + additional
    if observed > policy["scratch_bytes"]:
        raise _ScratchLimit(observed, policy["scratch_bytes"])


def _staged_relative(operand):
    role = operand["role"]
    if role in {"models_" + suffix for suffix in PRESSED_SUFFIXES}:
        return "inputs/models.cm." + role.rsplit("_", 1)[1]
    extension = {"infernal_ascii": "cm", "fasta": "fa", "stockholm": "sto", "text": "txt"}
    return "inputs/" + role + "." + extension[operand["format"]]


def _environment(job, root):
    return {**job["environment"], "TMPDIR": str(root / "tmp"), "TMP": str(root / "tmp"),
        "TEMP": str(root / "tmp"), "XDG_CACHE_HOME": str(root / "cache")}


def _stage_input(root, operand, policy, row):
    destination = _confined_file(root, row["relative_path"])
    try:
        with _regular_reader(Path(operand["path"])) as reader:
            size = os.fstat(reader.fileno()).st_size
            if size != operand["size_bytes"]:
                raise ValueError("native_infernal_input_size_mismatch")
            _scratch(root, policy, size)
            with destination.open("xb") as writer:
                for block in iter(lambda: reader.read(1024 * 1024), b""):
                    writer.write(block)
                    writer.flush()
                    _scratch(root, policy)
                os.fsync(writer.fileno())
    finally:
        # A failed copy can leave useful partial bytes. Their recorded size and
        # digest describe those bytes, never the original source's full size.
        if destination.exists():
            row["size_bytes"], row["actual_sha256"] = _digest_file(destination)
    if row["size_bytes"] != operand["size_bytes"]:
        raise ValueError("native_infernal_input_changed_size_during_capture")
    if row["actual_sha256"] != operand["sha256"]:
        raise ValueError("native_infernal_input_digest_mismatch")


def _validate_input_format(path, fmt, *, single_model=False):
    """Check framing only. Native code and separate readers own interpretation."""
    if fmt in {"infernal_" + suffix for suffix in PRESSED_SUFFIXES}:
        if not path.stat().st_size:
            raise ValueError("native_infernal_empty_pressed_index")
        return
    if fmt == "text":
        return
    if fmt == "infernal_ascii":
        # Native 1.1 ASCII consists of CM // HMM-filter // pairs. Each filter
        # belongs to the preceding CM; it is not another covariance model.
        state, count = "cm_header", 0
        with path.open("rb") as stream:
            for raw in stream:
                try:
                    line = raw.decode("ascii").strip()
                except UnicodeDecodeError as error:
                    raise ValueError("native_infernal_invalid_model_framing") from error
                if not line or line.startswith("#"):
                    continue
                token = line.split()[0]
                if state == "cm_header":
                    if token != "INFERNAL1/a":
                        raise ValueError("native_infernal_invalid_model_framing")
                    state, count = "cm_body", count + 1
                elif state == "filter_header":
                    if re.fullmatch(r"HMMER3/[a-f]", token) is None:
                        raise ValueError("native_infernal_filter_hmm_required")
                    state = "filter_body"
                elif line == "//":
                    state = "filter_header" if state == "cm_body" else "cm_header"
                elif token.startswith(("INFERNAL", "HMMER")) or "\0" in line:
                    raise ValueError("native_infernal_unterminated_model_block")
        if not count or state != "cm_header":
            raise ValueError("native_infernal_incomplete_model_input")
        if single_model and count != 1:
            raise ValueError("native_infernal_cmalign_exactly_one_model_required")
        return
    with path.open("rb") as stream:
        first = next((line.strip() for line in stream if line.strip()), b"")
        if fmt == "fasta":
            if not first.startswith(b">") or not first[1:].strip():
                raise ValueError("native_infernal_fasta_input_required")
        elif fmt == "stockholm":
            if first != b"# STOCKHOLM 1.0":
                raise ValueError("native_infernal_stockholm_input_required")
            ended = False
            for line in stream:
                if not line.strip():
                    continue
                if ended:
                    raise ValueError("native_infernal_stockholm_trailing_content")
                ended = line.strip() == b"//"
            if not ended:
                raise ValueError("native_infernal_incomplete_stockholm_input")


def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_native_infernal_bundle_files(bundle, directory) -> dict:
    """Check selected associations and all retained bytes without recapture.

    ``directory`` can be a complete retained copy. Realized paths continue to
    describe the original attempt, while this check reads only retained files.
    """
    bundle = finite_json_copy(bundle)
    if (type(bundle) is not dict or set(bundle) != _BUNDLE_FIELDS
            or bundle["version"] != "native_infernal_bundle_v1"):
        raise ValueError("native_infernal_bundle_required")
    request = validate_native_infernal_requested_job(bundle["requested_job"])
    _validate_identity(bundle["identity"], request)
    job = request["native_infernal"]
    if any(bundle[key] != job[key] for key in ("program", "table_format", "operand_bindings")):
        raise ValueError("native_infernal_bundle_request_conflict")
    root = _absolute_directory(str(directory))
    software = bundle["software"]
    if (type(software) is not dict or set(software) != {"executable", "expected_sha256",
            "actual_sha256", "declared_engine_version"}
            or software["executable"] != job["software"]["executable"]
            or software["expected_sha256"] != job["software"]["sha256"]
            or software["declared_engine_version"] != job["software"]["engine_version"]
            or software["actual_sha256"] is not None and not _sha(software["actual_sha256"])):
        raise ValueError("native_infernal_bundle_software_conflict")
    if type(bundle["environment"]) is not dict or type(bundle["environment"].get("TMPDIR")) is not str:
        raise ValueError("native_infernal_bundle_environment_conflict")
    original = Path(bundle["environment"]["TMPDIR"]).parent
    if not original.is_absolute() or bundle["environment"] != _environment(job, original):
        raise ValueError("native_infernal_bundle_environment_conflict")
    staged = {row["role"]: str(original / _staged_relative(row)) for row in job["operands"]}
    if bundle["realized_argv"] != compile_native_infernal_job(job, input_paths=staged,
            output_directory=str(original))["argv"]:
        raise ValueError("native_infernal_bundle_realized_command_conflict")
    rc = bundle["returncode"]
    if rc is not None and type(rc) is not int:
        raise ValueError("native_infernal_bundle_returncode_required")
    try:
        started, finished = (datetime.fromisoformat(bundle[k]) for k in ("started_at", "finished_at"))
        if started.utcoffset() is None or finished.utcoffset() is None or finished < started:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise ValueError("native_infernal_bundle_timestamp_conflict") from error
    failures = bundle["failures"]
    if type(failures) is not list:
        raise ValueError("native_infernal_bundle_failures_required")
    for failure in failures:
        if (type(failure) is not dict or set(failure) != {"stage", "code", "role", "detail"}
                or failure["stage"] not in {"software", "inputs", "staging", "execution", "outputs"}
                or type(failure["code"]) is not str or not failure["code"]
                or failure["role"] is not None and type(failure["role"]) is not str
                or type(failure["detail"]) is not dict):
            raise ValueError("native_infernal_bundle_failure_shape")
    if rc is None and not failures or rc not in (None, 0) and not any(
            f["code"] == "native_infernal_nonzero_returncode" and f["detail"] == {"returncode": rc}
            for f in failures):
        raise ValueError("native_infernal_bundle_execution_failure_missing")
    if rc is not None and software["actual_sha256"] != software["expected_sha256"]:
        raise ValueError("native_infernal_executed_software_identity_conflict")
    inputs = bundle["inputs"]
    if type(inputs) is not list or len(inputs) != len(job["operands"]):
        raise ValueError("native_infernal_bundle_inputs_required")
    for row, operand in zip(inputs, job["operands"]):
        expected = {"role": operand["role"], "format": operand["format"],
            "original_path": operand["path"], "relative_path": _staged_relative(operand),
            "artifact_ref": operand["artifact_ref"], "expected_sha256": operand["sha256"],
            "expected_size_bytes": operand["size_bytes"]}
        if type(row) is not dict or set(row) != _INPUT_FIELDS or any(row[k] != v for k, v in expected.items()):
            raise ValueError("native_infernal_bundle_input_identity_conflict")
        path = _confined_file(root, row["relative_path"])
        failed = any(f["role"] == row["role"] and f["stage"] in {"inputs", "staging"} for f in failures)
        if row["actual_sha256"] is None:
            if row["size_bytes"] is not None or path.exists() or not failed or rc is not None:
                raise ValueError("native_infernal_bundle_missing_input_conflict")
        else:
            if not _sha(row["actual_sha256"]) or type(row["size_bytes"]) is not int or row["size_bytes"] < 0:
                raise ValueError("native_infernal_bundle_input_measurement_invalid")
            if _digest_file(path) != (row["size_bytes"], row["actual_sha256"]):
                raise ValueError("native_infernal_sealed_input_digest_mismatch:" + row["relative_path"])
            if ((row["actual_sha256"], row["size_bytes"]) != (operand["sha256"], operand["size_bytes"])
                    and (not failed or rc is not None)):
                raise ValueError("native_infernal_bundle_input_capture_conflict")
    artifacts, selected, seen = bundle["artifacts"], {r["role"]: r for r in job["outputs"]}, set()
    if type(artifacts) is not list:
        raise ValueError("native_infernal_bundle_artifacts_required")
    for row in artifacts:
        if (type(row) is not dict or set(row) != _ARTIFACT_FIELDS
                or row["role"] not in selected or row["role"] in seen
                or any(row[k] != selected[row["role"]][k] for k in ("format", "relative_path"))
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0 or not _sha(row["sha256"])):
            raise ValueError("native_infernal_bundle_output_identity_conflict")
        seen.add(row["role"])
        path = _confined_file(root, row["relative_path"])
        if _digest_file(path) != (row["size_bytes"], row["sha256"]):
            raise ValueError("native_infernal_sealed_artifact_digest_mismatch:" + row["relative_path"])
    for role in selected.keys() - seen:
        path = _confined_file(root, selected[role]["relative_path"])
        if path.exists() or not any(f["stage"] == "outputs" and f["role"] == role for f in failures):
            raise ValueError("native_infernal_bundle_missing_output_conflict")
    return bundle


def _collect_outputs(root, job, bundle):
    for output in job["outputs"]:
        role, relative = output["role"], output["relative_path"]
        try:
            size, digest = _digest_file(_confined_file(root, relative))
        except FileNotFoundError:
            _failure(bundle, "outputs", "native_infernal_missing_output", role, relative_path=relative)
        except (OSError, ValueError) as error:
            _failure(bundle, "outputs", "native_infernal_invalid_output", role,
                relative_path=relative, reason=str(error))
        else:
            bundle["artifacts"].append({**output, "size_bytes": size, "sha256": digest})


def run_native_infernal(plan) -> dict:
    plan = _validate_plan(plan)
    root, request = Path(plan["attempt_directory"]), plan["requested_job"]
    job = request["native_infernal"]
    owner, manifest = root / ".native-infernal-owner.json", root / "bundle.json"
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if not _confined_file(root, owner.name).is_file():
            raise ValueError("native_infernal_attempt_not_exclusively_owned")
        if _read_json(owner, sealed=True) != plan:
            raise ValueError("native_infernal_attempt_identity_conflict")
        if not _confined_file(root, manifest.name).is_file():
            raise ValueError("native_infernal_unsealed_attempt_execution_uncertain")
        saved = _read_json(manifest, sealed=True)
        if (saved.get("identity") != plan["identity"] or saved.get("requested_job") != request):
            raise ValueError("native_infernal_sealed_manifest_identity_conflict")
        return validate_native_infernal_bundle_files(saved, root)
    _atomic_new(owner, plan)
    bundle = {"version": "native_infernal_bundle_v1", "identity": plan["identity"],
        "requested_job": request, "program": job["program"], "table_format": job["table_format"],
        "software": {"executable": job["software"]["executable"], "expected_sha256": job["software"]["sha256"],
            "actual_sha256": None, "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": [], "environment": _environment(job, root), "inputs": [],
        "operand_bindings": job["operand_bindings"], "returncode": None, "artifacts": [],
        "failures": [], "started_at": _now(), "finished_at": None}
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    paths = {row["role"]: str(root / _staged_relative(row)) for row in job["operands"]}
    compiled = compile_native_infernal_job(job, input_paths=paths, output_directory=str(root))
    bundle["realized_argv"] = compiled["argv"]
    try:
        _, actual_sha = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual_sha
        if actual_sha != job["software"]["sha256"]:
            _failure(bundle, "software", "native_infernal_software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software", "native_infernal_software_not_executable")
    except (OSError, ValueError) as error:
        _failure(bundle, "software", "native_infernal_software_unavailable", reason=str(error))
    for operand in job["operands"]:
        row = {"role": operand["role"], "format": operand["format"], "original_path": operand["path"],
            "relative_path": _staged_relative(operand), "artifact_ref": operand["artifact_ref"],
            "expected_sha256": operand["sha256"], "actual_sha256": None,
            "expected_size_bytes": operand["size_bytes"], "size_bytes": None}
        bundle["inputs"].append(row)
        try:
            _stage_input(root, operand, plan["policy"], row)
            _validate_input_format(root / row["relative_path"], operand["format"],
                single_model=job["program"] == "cmalign" and operand["role"] == "models")
        except _ScratchLimit as error:
            _failure(bundle, "staging", "native_infernal_scratch_limit", operand["role"],
                observed_bytes=error.observed, limit_bytes=error.limit)
        except FileNotFoundError:
            _failure(bundle, "inputs", "native_infernal_input_missing", operand["role"])
        except (OSError, ValueError) as error:
            _failure(bundle, "inputs", str(error) if isinstance(error, ValueError) else "native_infernal_input_io_error",
                operand["role"], **({"errno": error.errno} if isinstance(error, OSError) else {}))
    outputs = {row["role"]: _confined_file(root, row["relative_path"]) for row in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                # Exactly one selected native invocation. The enclosing existing
                # lifecycle enforces the caller's process-tree allocation.
                outcome = subprocess.run(compiled["argv"], cwd=root, env=bundle["environment"],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
            bundle["returncode"] = outcome.returncode
            if outcome.returncode:
                _failure(bundle, "execution", "native_infernal_nonzero_returncode", returncode=outcome.returncode)
            _scratch(root, plan["policy"])
        except _ScratchLimit as error:
            _failure(bundle, "execution", "native_infernal_scratch_limit",
                observed_bytes=error.observed, limit_bytes=error.limit)
        except OSError as error:
            _failure(bundle, "execution", "native_infernal_command_unavailable", errno=error.errno)
    _collect_outputs(root, job, bundle)
    bundle["finished_at"] = _now()
    _atomic_new(manifest, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise ValueError("native_infernal_exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_infernal(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / "bundle.json")}))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
