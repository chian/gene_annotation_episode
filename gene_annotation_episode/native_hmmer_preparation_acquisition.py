"""Acquire one original HMMER preparation attempt, without work or grading.

The saved plan anchors the original request and paths. Replay reads only that
plan and retained Store bytes. Repeated operands and working-copy/output roles
remain separate associations even when their content-addressed bytes coincide.
The recorded producer ABI belongs to that original execution; replay never
substitutes the current host's ABI or reopens a producer to recover it.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .domain import ContractError
from .execution_contracts import validate_target
from .local_jobs import LocalJobPolicy
from .materials import artifact_file
from .native_infernal_contracts import finite_json_copy, native_infernal_digest
from .native_hmmer_preparation_contracts import (
    compile_native_hmmer_preparation_job,
    recorded_operation_matches_compiled,
    validate_native_hmmer_preparation_requested_job, native_options, parse_ranges,
)
from .native_hmmer_preparation_driver import (
    _FAILURES, NATIVE_ABI_FIELDS, PREFLIGHT_REASONS, PREFLIGHT_FAILURE_CONTEXT,
)
from .native_hmmer_preparation_local import local_hmmer_preparation_plan
from .practical_execution_state import _immutable, canonical


VERSION = "native_hmmer_preparation_capture_v1"
PROVIDER = "episode.execution_result"
_PREFIX = "native_hmmer_preparation_"
_BUNDLE_VERSION = _PREFIX + "bundle_v1"
_BUNDLE_FIELDS = {"version", "identity", "requested_job", "program", "mode", "operation",
    "software", "realized_argv", "environment", "inputs", "working_copies", "returncode",
    "artifacts", "failures", "started_at", "finished_at", "native_abi"}
_INPUT_FIELDS = {"role", "ordinal", "format", "original_path", "relative_path", "artifact_ref",
    "expected_sha256", "expected_size_bytes", "staged_sha256", "staged_size_bytes",
    "final_sha256", "final_size_bytes"}
_COPY_FIELDS = {"operand_role", "operand_ordinal", "relative_path", "mutable", "source_sha256",
    "initial_sha256", "initial_size_bytes", "final_sha256", "final_size_bytes"}
_ARTIFACT_FIELDS = {"role", "format", "relative_path", "size_bytes", "sha256"}
_CAPTURE_FIELDS = {"version", "bundle_artifact_ref", "bundle_validated", "artifacts",
    "invalid_artifacts", "failures", "complete"}
_ROW_FIELDS = {"direction", "role", "ordinal", "format", "relative_path", "artifact_ref"}


def _error(code):
    raise ContractError(_PREFIX + code)


def is_native_hmmer_preparation_target(target):
    """Recognize the explicit branch; this does not establish an HPC binding."""
    return (isinstance(target, dict) and target.get("resource_kind") in ("local", "hpc")
        and isinstance(target.get("assignment"), dict)
        and isinstance(target["assignment"].get("requested_job"), dict)
        and "native_hmmer_preparation" in target["assignment"]["requested_job"])


def _same(left, right):
    return native_infernal_digest(left) == native_infernal_digest(right)


def _path(value, *, absolute=False):
    if (type(value) is not str or not value or any(c in value for c in "\0\r\n\\")
            or value.startswith("//") or ".." in value.split("/") or value in {".", "/"}):
        _error("capture_path_invalid")
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        _error("capture_path_invalid")
    return path


def _sha(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _error("bundle_digest_invalid")


def _pair(row, prefix):
    size, digest = row[prefix + "_size_bytes"], row[prefix + "_sha256"]
    if size is None and digest is None:
        return None, None
    if type(size) is not int or size < 0:
        _error("bundle_measurement_pair_invalid")
    _sha(digest)
    return size, digest


def _staged_relative(operand):
    if operand["role"] == "models":
        return "inputs/models.hmm"
    if operand["role"] == "ssi":
        return "inputs/models.hmm.ssi"
    return "inputs/" + operand["role"] + "/" + str(operand["ordinal"])


def _plan(value):
    """Pure plan qualification; the producer plan validator also reads paths."""
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job",
            "attempt_directory", "policy"} or plan["version"] != _PREFIX + "run_plan_v1"):
        _error("run_plan_required")
    request = validate_native_hmmer_preparation_requested_job(plan["requested_job"])
    identity = plan["identity"]
    if (type(identity) is not dict or set(identity) != {"run_id", "episode_id", "resource_id",
            "execution_id", "attempt_id", "operation_key", "requested_job_sha256"}
            or any(type(v) is not str or not v or "\0" in v for v in identity.values())
            or identity["requested_job_sha256"] != native_infernal_digest(request)
            or identity["attempt_id"] != native_infernal_digest(identity["operation_key"])):
        _error("original_plan_identity_conflict")
    root = _path(plan["attempt_directory"], absolute=True)
    execution = _path(identity["execution_id"], absolute=True)
    if execution.name != "native.json" or root != execution.parent / "hmmer-preparation-attempt":
        _error("original_plan_directory_conflict")
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        _error("explicit_policy_required")
    LocalJobPolicy(**policy)
    if any(_path(row["path"], absolute=True).is_relative_to(root)
            for row in request["native_hmmer_preparation"]["operands"]):
        _error("supplied_operand_inside_attempt")
    if _path(request["native_hmmer_preparation"]["software"]["executable"], absolute=True).is_relative_to(root):
        _error("supplied_software_inside_attempt")
    return plan


def _target_plan(target, plan):
    plan = _plan(plan)
    identity, assignment = plan["identity"], target["assignment"]
    if (target["resource_kind"] != "local" or assignment.get("resource_kind") != "local"
            or assignment.get("resource_id") != target["resource_id"]
            or not _same(assignment.get("requested_job"), plan["requested_job"])
            or target["request_sha256"] != identity["requested_job_sha256"]
            or any(target[key] != identity[other] for key, other in (
                ("run_id", "run_id"), ("origin_episode_id", "episode_id"),
                ("resource_id", "resource_id"), ("execution_id", "execution_id")))):
        _error("original_target_conflict")
    workspace = _path(assignment.get("workspace"), absolute=True)
    expected = workspace / ".episode-operations" / native_infernal_digest({
        "run": identity["run_id"], "episode": identity["episode_id"]}) / identity["attempt_id"]
    if PurePosixPath(plan["attempt_directory"]) != expected / "hmmer-preparation-attempt":
        _error("original_plan_directory_conflict")
    return plan


def _has(bundle, code=None, *, role=None, **detail):
    return any((code is None or f["code"] == _PREFIX + code) and f["role"] == role
        and all(_same(f["detail"].get(k), v) for k, v in detail.items()) for f in bundle["failures"])


def _validate_failures(bundle, job, copies):
    failures = bundle["failures"]
    if type(failures) is not list:
        _error("bundle_failures_invalid")
    inputs = {(r["role"], r["ordinal"]): r for r in job["operands"]}
    outputs = {r["role"]: r for r in job["outputs"]}
    copy_keys = {(r["operand_role"], r["operand_ordinal"], r["relative_path"]) for r in copies}
    for failure in failures:
        if (type(failure) is not dict or set(failure) != {"stage", "code", "role", "detail"}
                or type(failure["code"]) is not str or not failure["code"].startswith(_PREFIX)
                or failure["code"][len(_PREFIX):] not in _FAILURES):
            _error("bundle_failure_shape")
        code = failure["code"][len(_PREFIX):]
        stages, fields = _FAILURES[code]
        stage, role, detail = failure["stage"], failure["role"], failure["detail"]
        if (type(stage) is not str or stage not in stages or type(detail) is not dict
                or set(detail) != set(fields) or role is not None and type(role) is not str):
            _error("bundle_failure_context")
        for key, kind in fields.items():
            value = detail[key]
            if kind in {"uint", "int", "errno"}:
                valid = (value is None and kind == "errno" or type(value) is int
                    and (kind != "uint" or value >= 0))
            elif kind == "reason":
                valid = type(value) is str and value in {"missing", "unsafe_file", "io_error"}
            elif kind == "preflight_reason":
                valid = type(value) is str and value in PREFLIGHT_REASONS
            elif kind == "fm_issue_codes":
                from .hmmer_fm_data import ISSUE_CODES
                valid = type(value) is list and all(type(v) is str and v in ISSUE_CODES for v in value)
                valid = valid and value == sorted(set(value))
            else:
                valid = value is None and kind == "nullable_path" or type(value) is str
                if valid and value is not None:
                    _path(value)
            if not valid:
                _error("bundle_failure_context_type")
        if "ordinal" in detail and code != "invalid_exactmatch_queries" and (role, detail["ordinal"]) not in inputs:
            _error("bundle_failure_operand_conflict")
        if "operand_ordinal" in detail and (role, detail["operand_ordinal"], detail["relative_path"]) not in copy_keys:
            _error("bundle_failure_working_copy_conflict")
        if stage == "outputs" and (role not in outputs or detail["relative_path"] != outputs[role]["relative_path"]):
            _error("bundle_failure_output_conflict")
        if stage == "software" and role is not None:
            _error("bundle_failure_role")
        if stage == "preflight":
            _validate_preflight_failure(failure, job, bundle["native_abi"])
        if code == "nonzero_returncode" and (role is not None or detail["returncode"] in (0, None)
                or detail["returncode"] != bundle["returncode"]):
            _error("bundle_failure_returncode_conflict")
        if code == "command_unavailable" and (role is not None or bundle["returncode"] is not None):
            _error("bundle_failure_execution_conflict")
        if code == "scratch_limit":
            selected_paths = {(r["role"], _staged_relative(r)) for r in job["operands"]}
            selected_paths.update((r["operand_role"], r["relative_path"]) for r in copies)
            if (detail["observed_bytes"] <= detail["limit_bytes"]
                    or stage == "execution" and (role is not None or detail["relative_path"] is not None)
                    or stage == "staging" and (role, detail["relative_path"]) not in selected_paths):
                _error("bundle_failure_scratch_conflict")


def _validate_preflight_failure(failure, job, abi):
    """Relate recorded preflight facts without re-reading the native inputs."""
    code, role, detail = failure["code"][len(_PREFIX):], failure["role"], failure["detail"]
    context = PREFLIGHT_FAILURE_CONTEXT.get(code)
    if (context is None or job["program"] not in context["programs"] or role != context["role"]
            or context["reasons"] is not None and detail["reason"] not in context["reasons"]):
        _error("bundle_preflight_context_conflict")
    if code == "unsafe_alimask_range" and (job["mode"] != "alignment_to_model"
            or (detail["start"], detail["end"]) not in parse_ranges(native_options(job)["--ali2model"])
            or detail["start"] <= detail["last_match"]):
        _error("bundle_preflight_range_conflict")
    if code == "source_binding_digest_mismatch":
        binding = job["input_metadata"].get("source_binding")
        expected = [r["sha256"] for r in job["operands"] if r["role"] == "source_sequences"]
        if binding is None or binding["source_sha256s"] == expected:
            _error("bundle_preflight_binding_conflict")
    if code == "incompatible_fm_abi":
        contract = job["input_metadata"]["producer_contract"]
        mismatch = (contract["byte_order"] != abi["byte_order"] if detail["reason"] == "producer_byte_order_mismatch"
            else any(contract[k] != abi[k] for k in ("uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")))
        if not mismatch:
            _error("bundle_preflight_abi_conflict")


def validate_original_bundle(bundle, plan):
    """Qualify finite original facts and relationships with no filesystem I/O."""
    plan, bundle = _plan(plan), finite_json_copy(bundle)
    if (type(bundle) is not dict or set(bundle) != _BUNDLE_FIELDS or bundle["version"] != _BUNDLE_VERSION
            or not _same(bundle["identity"], plan["identity"])
            or not _same(bundle["requested_job"], plan["requested_job"])):
        _error("original_bundle_identity_conflict")
    job, root = plan["requested_job"]["native_hmmer_preparation"], PurePosixPath(plan["attempt_directory"])
    if any(not _same(bundle[k], job[k]) for k in ("program", "mode")):
        _error("original_bundle_request_conflict")
    abi = bundle["native_abi"]
    if (type(abi) is not dict or set(abi) != NATIVE_ABI_FIELDS
            or type(abi["byte_order"]) is not str or abi["byte_order"] not in {"little", "big"}
            or type(abi["float_format"]) is not str or abi["float_format"] not in {"ieee754_binary64", "unsupported"}
            or any(type(abi[k]) is not int or abi[k] <= 0 for k in NATIVE_ABI_FIELDS - {"byte_order", "float_format"})
            or abi["float_format"] == "ieee754_binary64" and abi["bytes_per_float"] != 8):
        _error("bundle_native_abi_invalid")
    paths = {}
    for row in job["operands"]:
        paths.setdefault(row["role"], []).append(str(root / _staged_relative(row)))
    compiled = compile_native_hmmer_preparation_job(job, input_paths=paths, output_directory=str(root))
    environment = {**compiled["environment"], **{key: str(root / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
        "XDG_CACHE_HOME": str(root / "cache")}
    if (not _same(bundle["realized_argv"], compiled["argv"])
            or not recorded_operation_matches_compiled(bundle["operation"], compiled["operation"])
            or not _same(bundle["environment"], environment)):
        _error("original_realized_command_conflict")
    software = bundle["software"]
    if (type(software) is not dict or set(software) != {"executable", "expected_sha256", "actual_sha256",
            "declared_engine_version"} or software["executable"] != job["software"]["executable"]
            or software["expected_sha256"] != job["software"]["sha256"]
            or software["declared_engine_version"] != job["software"]["engine_version"]):
        _error("original_bundle_software_conflict")
    _sha(software["actual_sha256"], nullable=True)
    rc = bundle["returncode"]
    if rc is not None and type(rc) is not int:
        _error("bundle_returncode_invalid")
    try:
        times = [datetime.fromisoformat(bundle[key]) for key in ("started_at", "finished_at")]
        if any(t.utcoffset() is None for t in times) or times[1] < times[0]:
            raise ValueError
    except (ValueError, TypeError, OverflowError) as error:
        raise ContractError(_PREFIX + "bundle_timestamp_conflict") from error
    inputs, copies = bundle["inputs"], bundle["working_copies"]
    if type(inputs) is not list or len(inputs) != len(job["operands"]):
        _error("original_bundle_inputs_conflict")
    sources = {}
    for row, operand in zip(inputs, job["operands"]):
        expected = {"role": operand["role"], "ordinal": operand["ordinal"], "format": operand["format"],
            "original_path": operand["path"], "relative_path": _staged_relative(operand),
            "artifact_ref": operand["artifact_ref"], "expected_sha256": operand["sha256"],
            "expected_size_bytes": operand["size_bytes"]}
        if (type(row) is not dict or set(row) != _INPUT_FIELDS
                or any(not _same(row[k], v) for k, v in expected.items())):
            _error("original_bundle_input_conflict")
        _pair(row, "staged")
        _pair(row, "final")
        sources[row["role"], row["ordinal"]] = row
    if type(copies) is not list or len(copies) != len(compiled["working_copies"]):
        _error("original_bundle_working_copies_conflict")
    for row, copy in zip(copies, compiled["working_copies"]):
        source = sources[copy["operand_role"], copy["operand_ordinal"]]
        expected = {"operand_role": copy["operand_role"], "operand_ordinal": copy["operand_ordinal"],
            "relative_path": str(PurePosixPath(copy["destination"]).relative_to(root)),
            "mutable": copy["mutable"], "source_sha256": source["staged_sha256"]}
        if (type(row) is not dict or set(row) != _COPY_FIELDS
                or any(not _same(row[k], v) for k, v in expected.items())):
            _error("original_bundle_working_copy_conflict")
        _pair(row, "initial")
        _pair(row, "final")
    _validate_failures(bundle, job, copies)
    failures = bundle["failures"]
    prevented = any(f["stage"] in {"software", "inputs", "staging", "preflight"}
        or f["code"] in {_PREFIX + "command_unavailable", _PREFIX + "scratch_limit"} for f in failures)
    if ((rc is None and not prevented)
            or rc not in (0, None) and not _has(bundle, "nonzero_returncode", returncode=rc)):
        _error("bundle_execution_failure_missing")
    if rc is not None and any(f["stage"] in {"software", "inputs", "staging", "preflight"} for f in failures):
        _error("execution_after_preexecution_failure")
    if rc is not None and software["actual_sha256"] != software["expected_sha256"]:
        _error("executed_software_identity_conflict")
    if (software["actual_sha256"] is None and not _has(bundle, "software_unavailable")
            or software["actual_sha256"] not in {None, software["expected_sha256"]}
            and not _has(bundle, "software_digest_mismatch")):
        _error("bundle_software_failure_missing")
    for row in inputs:
        staged, final = _pair(row, "staged"), _pair(row, "final")
        failed = _has(bundle, role=row["role"], ordinal=row["ordinal"]) or _has(
            bundle, "scratch_limit", role=row["role"], relative_path=row["relative_path"])
        if staged != (row["expected_size_bytes"], row["expected_sha256"]) and (rc is not None or not failed):
            _error("bundle_input_capture_conflict")
        if staged != final and not _has(bundle, "immutable_input_changed", role=row["role"], ordinal=row["ordinal"]):
            _error("bundle_changed_input_failure_missing")
        if staged[0] is not None and final[0] is None and not _has(
                bundle, "input_final_unavailable", role=row["role"], ordinal=row["ordinal"]):
            _error("bundle_missing_input_failure_missing")
    for row in copies:
        source = sources[row["operand_role"], row["operand_ordinal"]]
        initial, final = _pair(row, "initial"), _pair(row, "final")
        detail = {"operand_ordinal": row["operand_ordinal"], "relative_path": row["relative_path"]}
        failed = _has(bundle, role=row["operand_role"], **detail) or _has(
            bundle, "scratch_limit", role=row["operand_role"], relative_path=row["relative_path"])
        if (initial[0] is None or initial != _pair(source, "staged")) and (rc is not None or not failed):
            _error("bundle_working_copy_capture_conflict")
        if not row["mutable"] and initial != final and not _has(
                bundle, "immutable_working_copy_changed", role=row["operand_role"], **detail):
            _error("bundle_changed_working_copy_failure_missing")
        if initial[0] is not None and final[0] is None and not _has(
                bundle, "working_copy_final_unavailable", role=row["operand_role"], **detail):
            _error("bundle_missing_working_copy_failure_missing")
    outputs, seen = {r["role"]: r for r in job["outputs"]}, set()
    if type(bundle["artifacts"]) is not list:
        _error("bundle_artifacts_invalid")
    for row in bundle["artifacts"]:
        if (type(row) is not dict or set(row) != _ARTIFACT_FIELDS or type(row["role"]) is not str
                or row["role"] not in outputs or row["role"] in seen
                or any(not _same(row[k], outputs[row["role"]][k]) for k in ("format", "relative_path"))
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0):
            _error("original_bundle_output_conflict")
        _sha(row["sha256"])
        seen.add(row["role"])
    for role in outputs.keys() - seen:
        if not any(f["stage"] == "outputs" and f["role"] == role for f in failures):
            _error("bundle_missing_output_failure_required")
    # A shared working-copy/output path describes one final physical file.
    measurements = {}
    for row in _selected_files(bundle):
        pair = row["size_bytes"], row["sha256"]
        if row["relative_path"] in measurements and measurements[row["relative_path"]] != pair:
            _error("bundle_shared_file_measurement_conflict")
        measurements[row["relative_path"]] = pair
    return bundle


def _selected_files(bundle):
    """Ordered associations, including declared missing files for stray checks."""
    result = []
    sources = {(r["role"], r["ordinal"]): r for r in bundle["inputs"]}
    for row in bundle["inputs"]:
        result.append({"direction": "input", **{k: row[k] for k in ("role", "ordinal", "format", "relative_path")},
            "sha256": row["final_sha256"], "size_bytes": row["final_size_bytes"]})
    for row in bundle["working_copies"]:
        source = sources[row["operand_role"], row["operand_ordinal"]]
        result.append({"direction": "working_copy", "role": row["operand_role"],
            "ordinal": row["operand_ordinal"], "format": source["format"], "relative_path": row["relative_path"],
            "sha256": row["final_sha256"], "size_bytes": row["final_size_bytes"]})
    produced = {r["role"]: r for r in bundle["artifacts"]}
    for row in bundle["requested_job"]["native_hmmer_preparation"]["outputs"]:
        actual = produced.get(row["role"], {"sha256": None, "size_bytes": None})
        result.append({"direction": "output", "ordinal": 0, **row,
            "sha256": actual["sha256"], "size_bytes": actual["size_bytes"]})
    return result


def _directory(value):
    directory = Path(value).absolute()
    _path(str(directory), absolute=True)
    if directory.resolve() != directory:
        _error("capture_directory_escape")
    return directory


@contextmanager
def _confined_reader(root, relative):
    relative, root = _path(relative), _directory(root)
    descriptors = []
    try:
        descriptors.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        for part in relative.parts[:-1]:
            descriptors.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptors[-1]))
        descriptor = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
            dir_fd=descriptors[-1])
        descriptors.append(descriptor)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _error("capture_regular_file_required")
        yield Path("/proc/self/fd") / str(descriptor)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _capture_file(store, root, relative, media_type="application/octet-stream"):
    with _confined_reader(root, relative) as path:
        return artifact_file(store, path, media_type)


def _retained(store, reference):
    if type(reference) is not str:
        _error("capture_artifact_reference_invalid")
    metadata = store._require(reference, {"artifact"})
    _sha(metadata["sha256"])
    if (reference != "artifact_" + metadata["sha256"] or type(metadata["size"]) is not int
            or metadata["size"] < 0):
        _error("capture_artifact_identity_conflict")
    with _confined_reader(store.path / "artifacts", metadata["sha256"][:2] + "/" + metadata["sha256"]) as path:
        digest, size = hashlib.sha256(), 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        if size != metadata["size"] or digest.hexdigest() != metadata["sha256"]:
            _error("capture_artifact_measurement_conflict")
    return metadata


def _decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _error("manifest_duplicate_key")
            result[key] = value
        return result
    try:
        return finite_json_copy(json.loads(raw, object_pairs_hook=unique))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(_PREFIX + "manifest_json_invalid") from error


def _read_record(directory, name):
    with _confined_reader(directory, name) as path:
        raw = path.read_bytes()
    value = _decode(raw)
    if raw != (canonical(value) + "\n").encode("utf-8"):
        _error("capture_record_bytes_changed")
    return value


def _shape(capture):
    capture = finite_json_copy(capture)
    if (type(capture) is not dict or set(capture) != _CAPTURE_FIELDS or capture["version"] != VERSION
            or type(capture["bundle_validated"]) is not bool or type(capture["complete"]) is not bool
            or capture["bundle_artifact_ref"] is not None and type(capture["bundle_artifact_ref"]) is not str
            or any(type(capture[k]) is not list for k in ("artifacts", "invalid_artifacts", "failures"))):
        _error("capture_receipt_invalid")
    for row in capture["artifacts"] + capture["invalid_artifacts"]:
        if (type(row) is not dict or set(row) != _ROW_FIELDS or type(row["direction"]) is not str
                or row["direction"] not in {"input", "working_copy", "output"}
                or type(row["ordinal"]) is not int or row["ordinal"] < 0
                or row["direction"] == "output" and row["ordinal"] != 0
                or any(type(row[k]) is not str or not row[k] for k in ("role", "format", "relative_path", "artifact_ref"))):
            _error("capture_artifact_row_invalid")
        _path(row["relative_path"])
    for row in capture["failures"]:
        if (type(row) is not dict or set(row) != {"stage", "code", "record_key"}
                or row["stage"] != "capture" or type(row["code"]) is not str or not row["code"]
                or row["record_key"] is not None):
            _error("capture_failure_invalid")
    return capture


def _key(row):
    return row["direction"], row["role"], row["ordinal"], row["relative_path"]


def _file_code(code, row):
    return _PREFIX + code + ":" + ":".join(str(v) for v in _key(row))


def _failure(code):
    return {"stage": "capture", "code": code, "record_key": None}


def _validate_rows(store, capture, bundle):
    selected = {_key(row): row for row in _selected_files(bundle)}
    seen, failures, paths, metadata_by_ref = set(), [], {}, {}
    recorded = [r["code"] for r in capture["failures"]]
    for category in ("artifacts", "invalid_artifacts"):
        previous = -1
        order = {key: index for index, key in enumerate(selected)}
        for row in capture[category]:
            key, path = _key(row), row["relative_path"]
            expected = selected.get(key)
            if expected is None or key in seen or row["format"] != expected["format"] or order[key] <= previous:
                _error("capture_artifact_association_conflict")
            previous = order[key]
            seen.add(key)
            if path in paths and paths[path] != row["artifact_ref"]:
                _error("capture_shared_file_association_conflict")
            paths[path] = row["artifact_ref"]
            reference = row["artifact_ref"]
            if reference not in metadata_by_ref:
                metadata_by_ref[reference] = _retained(store, reference)
            metadata = metadata_by_ref[reference]
            matches = (metadata["sha256"], metadata["size"]) == (expected["sha256"], expected["size_bytes"])
            if (category == "artifacts") != matches:
                _error("capture_artifact_measurement_conflict")
            if not matches:
                failures.append(_file_code("sealed_artifact_digest_mismatch" if expected["sha256"] is not None
                    else "unlisted_file_present", row))
    for key, row in selected.items():
        if key not in seen:
            code = _file_code("bundle_file_unavailable_or_escaped", row)
            if row["sha256"] is not None or code in recorded:
                failures.append(code)
    if sorted(recorded) != sorted(failures):
        _error("capture_failure_association_conflict")
    if capture["complete"] != (not failures):
        _error("capture_completion_conflict")


def _saved_capture(store, *, target, directory):
    plan = _target_plan(target, _read_record(directory, "capture-plan.json"))
    saved = _shape(_read_record(directory, "capture.json"))
    reference, bundle = saved["bundle_artifact_ref"], None
    if reference is not None:
        _retained(store, reference)
        try:
            bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
        except ValueError as error:
            if saved["bundle_validated"] or saved["failures"] != [_failure(str(error))]:
                raise ContractError(_PREFIX + "capture_manifest_validation_conflict") from error
    if bundle is None:
        if (saved["bundle_validated"] or saved["complete"] or saved["artifacts"] or saved["invalid_artifacts"]
                or not saved["failures"] or reference is None and saved["failures"] != [
                    _failure(_PREFIX + "sealed_bundle_unavailable")]):
            _error("capture_unvalidated_manifest_conflict")
    else:
        if not saved["bundle_validated"]:
            _error("capture_manifest_validation_conflict")
        _validate_rows(store, saved, bundle)
    return saved


def capture_local_bundle(store, *, target, directory):
    """Retain declared final bytes once; complete means custody, not success."""
    if not is_native_hmmer_preparation_target(target) or target["resource_kind"] != "local":
        _error("local_capture_binding_required")
    target = validate_target(finite_json_copy(target))
    directory = _directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("capture-intent.json", "capture-plan.json", "capture.json"):
        path = directory / name
        if path.is_symlink() or path.exists() and not path.is_file():
            _error("capture_record_path_invalid")
    # Bind every original target field before any reservation read.
    _immutable(directory / "capture-intent.json", {"target": target})
    if (directory / "capture.json").exists():
        return _saved_capture(store, target=target, directory=directory)
    plan = _target_plan(target, local_hmmer_preparation_plan(target["assignment"], target["execution_id"]))
    _immutable(directory / "capture-plan.json", plan)
    root = Path(plan["attempt_directory"])
    result = {"version": VERSION, "bundle_artifact_ref": None, "bundle_validated": False,
        "artifacts": [], "invalid_artifacts": [], "failures": [], "complete": False}
    try:
        reference = _capture_file(store, root, "bundle.json", "application/json")
    except (ValueError, OSError):
        result["failures"].append(_failure(_PREFIX + "sealed_bundle_unavailable"))
    else:
        result["bundle_artifact_ref"] = reference
        # Store corruption is not a native manifest validation outcome.
        _retained(store, reference)
        try:
            bundle = validate_original_bundle(_decode(store.get_artifact(reference)), plan)
            result["bundle_validated"] = True
        except ValueError as error:
            result["failures"].append(_failure(str(error)))
    if not result["bundle_validated"]:
        _immutable(directory / "capture.json", result)
        return result
    physical = {}
    for row in _selected_files(bundle):
        relative = row["relative_path"]
        if relative not in physical:
            try:
                reference = _capture_file(store, root, relative)
            except FileNotFoundError:
                physical[relative] = (None, "missing")
            except (ValueError, OSError):
                physical[relative] = (None, "unsafe")
            else:
                physical[relative] = (reference, _retained(store, reference))
        reference, observed = physical[relative]
        if reference is None:
            if row["sha256"] is not None or observed != "missing":
                result["failures"].append(_failure(_file_code("bundle_file_unavailable_or_escaped", row)))
            continue
        item = {key: row[key] for key in _ROW_FIELDS - {"artifact_ref"}}
        matches = (observed["sha256"], observed["size"]) == (row["sha256"], row["size_bytes"])
        result["artifacts" if matches else "invalid_artifacts"].append({**item, "artifact_ref": reference})
        if not matches:
            result["failures"].append(_failure(_file_code("sealed_artifact_digest_mismatch"
                if row["sha256"] is not None else "unlisted_file_present", row)))
    result["complete"] = not result["failures"]
    _validate_rows(store, result, bundle)
    _immutable(directory / "capture.json", result)
    return result


def original_source_payload(*, bundle, capture, prepared=None):
    """Construct execution provenance whose identity is the original attempt."""
    bundle, capture = finite_json_copy(bundle), _shape(capture)
    if (not capture["bundle_validated"] or capture["bundle_artifact_ref"] is None
            or type(bundle) is not dict or bundle.get("version") != _BUNDLE_VERSION):
        _error("source_validated_manifest_required")
    auxiliary = [r["artifact_ref"] for r in capture["artifacts"] + capture["invalid_artifacts"]]
    if prepared is not None:
        if type(prepared) is not dict:
            _error("source_prepared_object_required")
        if prepared.get("source_grading_artifact_ref") is not None:
            auxiliary.append(prepared["source_grading_artifact_ref"])
    if any(type(ref) is not str or not ref for ref in auxiliary):
        _error("source_artifact_reference_invalid")
    return {"provider": PROVIDER, "accession": _PREFIX + native_infernal_digest(bundle["identity"]),
        "uri": None, "artifact_ref": capture["bundle_artifact_ref"], "text_ref": None, "request_ref": None,
        "version": _BUNDLE_VERSION, "retrieved_at": bundle["finished_at"],
        "auxiliary_artifact_refs": sorted(set(auxiliary))}


def publish_original_source(store, *, bundle, capture, prepared=None):
    payload = original_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    _retained(store, payload["artifact_ref"])
    if not _same(_decode(store.get_artifact(payload["artifact_ref"])), bundle):
        _error("source_bundle_association_conflict")
    _validate_rows(store, _shape(capture), bundle)
    for reference in payload["auxiliary_artifact_refs"]:
        _retained(store, reference)
    return store.put("source", payload, origin="tool")["id"]


__all__ = ["is_native_hmmer_preparation_target", "validate_original_bundle", "capture_local_bundle",
    "original_source_payload", "publish_original_source", "VERSION", "PROVIDER"]
