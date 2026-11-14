"""Execute the selected finite overlap batch and retain its original native facts.

The existing lifecycle owns dispatch and resource enforcement. This primitive
normalizes supplied rows with G1, invokes the bound program once per eligible
selected pair, and seals files. It has no scientific calculator or retry loop.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import sys

from .acquisition import AcquisitionError
from .execution_contracts import canonical, digest
from .genomic_overlap_inputs import parse_region_set
from .local_jobs import LocalJobPolicy, check_scratch_budget
from .native_genomic_overlap_contracts import (
    BATCH_FILENAME, OWNER_FILENAME, RUN_PLAN_FILENAME, STARTED_FILENAME,
    genomic_overlap_driver_argv, genomic_overlap_environment,
    validate_genomic_overlap_batch, validate_genomic_overlap_pair_manifest,
    validate_genomic_overlap_run_plan,
)


def _require(condition, code="original_attempt_mismatch"):
    if not condition:
        raise ValueError(code)


def _path(value, *, absolute):
    _require(type(value) is str and value and not any(c in value for c in "\0\n\r\\"),
        "invalid_output_path")
    path = PurePosixPath(value)
    _require(str(path) == value and ".." not in path.parts and
        path.is_absolute() == absolute and value not in {".", "/"}, "invalid_output_path")
    return Path(value)


def _directory(value):
    path = _path(str(value), absolute=True)
    current = Path("/")
    for part in path.parts[1:]:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        _require(stat.S_ISDIR(mode), "invalid_output_path")
    return path


def confined_file(directory, relative_path):
    directory = _directory(directory)
    path = directory / _path(relative_path, absolute=False)
    _directory(path.parent)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return path
    _require(stat.S_ISREG(mode), "invalid_output_path")
    return path


@contextmanager
def _regular(value):
    """Pin every directory and the regular endpoint without following symlinks."""
    path = _path(str(value), absolute=True)
    with ExitStack() as stack:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        fd = os.open("/", flags)
        stack.callback(os.close, fd)
        for part in path.parts[1:-1]:
            fd = os.open(part, flags, dir_fd=fd)
            stack.callback(os.close, fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=fd)
        stack.callback(os.close, fd)
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid_output_path")
        with os.fdopen(os.dup(fd), "rb") as stream:
            yield stream


def file_identity(path):
    with _regular(path) as stream:
        hasher, size = hashlib.sha256(), 0
        while block := stream.read(1024 * 1024):
            hasher.update(block)
            size += len(block)
    return {"sha256": hasher.hexdigest(), "size_bytes": size}


def _decode(raw):
    def pairs(rows):
        value = {}
        for key, item in rows:
            _require(key not in value, "invalid_native_control_json")
            value[key] = item
        return value
    def constant(_):
        raise ValueError("invalid_native_control_json")
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid_native_control_json") from error


def _strict_json(path):
    with _regular(path) as stream:
        return _decode(stream.read())


def _read_control(path):
    with _regular(path) as stream:
        raw = stream.read()
    value = _decode(raw)
    _require(raw == (canonical(value) + "\n").encode("utf-8"), "original_attempt_mismatch")
    return value


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish(temporary, destination):
    os.chmod(temporary, 0o444)
    os.link(temporary, destination)
    _sync_directory(destination.parent)
    temporary.unlink()
    _sync_directory(destination.parent)


@contextmanager
def _writing(path):
    """Leave any failed partial temporary intact; publish only closed bytes."""
    path = confined_file(path.parent, path.name)
    temporary = confined_file(path.parent, "." + path.name + ".writing")
    with temporary.open("xb") as stream:
        yield stream
        stream.flush()
        os.fsync(stream.fileno())
    _publish(temporary, path)


def _immutable(path, value):
    payload = (canonical(value) + "\n").encode("utf-8")
    path = confined_file(path.parent, path.name)
    if path.exists():
        with _regular(path) as stream:
            _require(stream.read() == payload, "original_attempt_mismatch")
        return
    with _writing(path) as stream:
        stream.write(payload)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _identity(plan):
    identity = plan["identity"]
    return {"run_id": identity["run_id"], "origin_episode_id": identity["episode_id"],
        **{key: identity[key] for key in ("resource_id", "execution_id", "attempt_id", "operation_key")}}


def _failure(failures, code, stage, *, set_key=None, comparison_key=None,
    file_key=None, field_path=None, expected_value=None, observed_value=None):
    failures.append({"code": code, "stage": stage, "set_key": set_key,
        "comparison_key": comparison_key, "file_key": file_key, "field_path": field_path,
        "expected_value": deepcopy(expected_value), "observed_value": deepcopy(observed_value)})
    return len(failures) - 1


def _error_value(error):
    error = getattr(error, "original", error)
    return {"exception_type": type(error).__name__, "errno": getattr(error, "errno", None)}


def _event(stream, event, **values):
    stream.write((canonical({"event": event, "at": _now(), **values}) + "\n").encode("utf-8"))
    stream.flush()


def _stage(binding, spec, *, position, paths, directory, policy, failures):
    row = {"set_key": spec["set_key"], "set_position": position, "input_state": "unavailable",
        "measured_fingerprint": None, "parse_extent": None, "original_file_key": f"s{position}:original",
        "rejected_file_key": f"s{position}:rejected", "parsed_file_key": f"s{position}:parsed",
        "canonical_file_key": f"s{position}:canonical", "failure_indices": []}
    expected = {key: spec["source"]["file"][key] for key in ("sha256", "size_bytes")}
    temporary = confined_file(paths[row["original_file_key"]].parent, ".original.data.staging")
    try:
        hasher, size = hashlib.sha256(), 0
        with _regular(binding["path"]) as source:
            check_scratch_budget(directory, policy, additional_bytes=os.fstat(source.fileno()).st_size)
            with temporary.open("xb") as target:
                while block := source.read(1024 * 1024):
                    target.write(block)
                    hasher.update(block)
                    size += len(block)
                    check_scratch_budget(directory, policy)
                target.flush()
                os.fsync(target.fileno())
    except (OSError, ValueError, AcquisitionError) as error:
        row["failure_indices"].append(_failure(failures,
            "resource_limit" if isinstance(error, AcquisitionError) else "input_unavailable", "input",
            set_key=spec["set_key"], file_key=row["original_file_key"],
            field_path=f"/inputs/{position}/path", expected_value=binding["path"], observed_value=_error_value(error)))
        return row
    actual = {"sha256": hasher.hexdigest(), "size_bytes": size}
    # Failed publication leaves the attempt unsealed and the copied bytes in
    # place. It cannot turn a measured candidate into a missing fingerprint or
    # claim that the original/rejected endpoint was successfully published.
    _publish(temporary, paths[row["original_file_key"] if actual == expected else row["rejected_file_key"]])
    row["measured_fingerprint"] = {"set_key": spec["set_key"], "format": spec["format"], **actual}
    row["input_state"] = "verified" if actual == expected else "digest_mismatch"
    if actual != expected:
        row["failure_indices"].append(_failure(failures, "input_digest_mismatch", "input",
            set_key=spec["set_key"], file_key=row["rejected_file_key"],
            field_path=f"/request/region_sets/{position}/source/file", expected_value=expected, observed_value=actual))
    return row


def _normalize(row, spec, *, paths, directory, policy, failures):
    writing_key = row["parsed_file_key"]
    try:
        if row["input_state"] == "verified":
            with _regular(paths[row["original_file_key"]]) as stream:
                parsed = parse_region_set(stream, specification=spec, set_position=row["set_position"])
        else:
            parsed = parse_region_set(None, specification=spec, set_position=row["set_position"])
        check_scratch_budget(directory, policy, additional_bytes=len(canonical(parsed).encode("utf-8")) + 1)
        _immutable(paths[row["parsed_file_key"]], parsed)
        row["parse_extent"] = parsed["result_extent"]
        if parsed["result_extent"] == "complete":
            writing_key = row["canonical_file_key"]
            index = {region["occurrence_key"]: region for region in parsed["regions"]}
            _require(len(index) == len(parsed["regions"]) == len(parsed["canonical_order"]) and
                set(index) == set(parsed["canonical_order"]), "invalid_input")
            with _writing(paths[row["canonical_file_key"]]) as stream:
                for key in parsed["canonical_order"]:
                    region = index[key]
                    _require(region["native_token"] == f"s{row['set_position']}_r{region['data_ordinal']}", "invalid_input")
                    stream.write((f"{region['chromosome']}\t{region['start']}\t{region['end']}\t{region['native_token']}\n").encode("utf-8"))
                check_scratch_budget(directory, policy)
        elif row["input_state"] == "verified":
            row["failure_indices"].append(_failure(failures, "invalid_input", "input",
                set_key=spec["set_key"], file_key=row["parsed_file_key"], field_path="/result_extent",
                expected_value="complete", observed_value=parsed["result_extent"]))
        return parsed
    except (OSError, ValueError, AcquisitionError) as error:
        row["failure_indices"].append(_failure(failures,
            "resource_limit" if isinstance(error, AcquisitionError) else "seal_failed", "seal",
            set_key=spec["set_key"], file_key=writing_key, observed_value=_error_value(error)))
        return None


def _implementation(software, failures):
    result = {"state": "not_needed", "python_observed": None, "bedtools_observed": None,
        "version_probe": None, "failure_indices": []}
    checks = []
    try:
        selected = Path(software["python_executable"]).resolve(strict=True)
        actual = file_identity(selected)["sha256"]
        result["python_observed"] = {"sha256": actual, "version": platform.python_version()}
        checks.extend((
            ("/software/python_sha256", software["python_sha256"], actual),
            ("/software/python_version", software["python_version"], platform.python_version()),
            ("/software/python_executable", str(selected), str(Path(sys.executable).resolve(strict=True))),
        ))
        _require(os.path.samefile(selected, "/proc/self/exe"), "software_identity_mismatch")
        root = _directory(software["module_root"])
        checks.append(("/software/driver_module", str(root / (software["driver_module"].replace(".", "/") + ".py")), __file__))
        for row in software["implementation_files"]:
            path = confined_file(root, row["module"].replace(".", "/") + ".py")
            checks.append(("/software/implementation_files/" + row["module"], row["sha256"], file_identity(path)["sha256"]))
            loaded = sys.modules.get(row["module"])
            if loaded is not None:
                checks.append(("/software/module_root/" + row["module"], str(path), getattr(loaded, "__file__", None)))
    except (OSError, ValueError) as error:
        result["failure_indices"].append(_failure(failures, "software_identity_mismatch", "software",
            field_path="/software", observed_value=_error_value(error)))
    for field, expected, observed in checks:
        if expected != observed:
            result["failure_indices"].append(_failure(failures, "software_identity_mismatch", "software",
                field_path=field, expected_value=expected, observed_value=observed))
    if result["failure_indices"]:
        result["state"] = "failed"
    return result


class _NativeSpawnError(Exception):
    """The selected process did not start; output I/O errors are distinct."""
    def __init__(self, original):
        self.original = original
        super().__init__("native_spawn_failed")


def _native_call(argv, *, directory, environment, stdout, stderr, on_start=None):
    """One selected subprocess; no retry, timeout or alternative executable."""
    started_at = _now()
    with stdout.open("xb") as out, stderr.open("xb") as err:
        try:
            try:
                process = subprocess.Popen(argv, cwd=directory, env={**os.environ, **environment},
                    stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            except OSError as error:
                raise _NativeSpawnError(error) from error
            try:
                if on_start is not None:
                    on_start(started_at)
            finally:
                # A failed progress-log write cannot abandon or relabel an
                # already started process as a spawn failure.
                returncode = process.wait()
            finished_at = _now()
        finally:
            for stream in (out, err):
                stream.flush()
                os.fsync(stream.fileno())
                os.fchmod(stream.fileno(), 0o444)
    for path in (stdout, stderr):
        path.chmod(0o444)
    return returncode, started_at, finished_at


def _bedtools(verification, software, *, directory, environment, paths, failures):
    try:
        actual = file_identity(software["bedtools_executable"])["sha256"]
        _require(os.access(software["bedtools_executable"], os.X_OK), "native_dependency_unavailable")
    except (OSError, ValueError) as error:
        verification["failure_indices"].append(_failure(failures, "native_dependency_unavailable", "software",
            field_path="/software/bedtools_executable", expected_value=software["bedtools_executable"], observed_value=_error_value(error)))
        verification["state"] = "failed"
        return
    verification["bedtools_observed"] = {"executable": software["bedtools_executable"],
        "declared_version": software["bedtools_version"], "observed_version": None, "executable_sha256": actual}
    if actual != software["bedtools_sha256"]:
        verification["failure_indices"].append(_failure(failures, "software_identity_mismatch", "software",
            field_path="/software/bedtools_sha256", expected_value=software["bedtools_sha256"], observed_value=actual))
        verification["state"] = "failed"
        return
    argv = [software["bedtools_executable"], "--version"]
    try:
        rc, started, finished = _native_call(argv, directory=directory, environment=environment,
            stdout=paths["version_stdout"], stderr=paths["version_stderr"])
    except _NativeSpawnError as error:
        verification["failure_indices"].append(_failure(failures, "native_spawn_failed", "software",
            field_path="/software/bedtools_executable", observed_value=_error_value(error)))
        verification["state"] = "failed"
        return
    verification["version_probe"] = {"realized_argv": argv, "environment": environment,
        "returncode": rc, "started_at": started, "finished_at": finished, "writer_closed": True,
        "stdout_file_key": "version_stdout", "stderr_file_key": "version_stderr"}
    with _regular(paths["version_stdout"]) as stream:
        raw = stream.read()
    try:
        version = raw.decode("utf-8").rstrip("\r\n")
    except UnicodeError:
        version = None
    if version and "\n" not in version and "\r" not in version:
        verification["bedtools_observed"]["observed_version"] = version
    if rc != 0 or version != software["bedtools_version"]:
        verification["failure_indices"].append(_failure(failures, "native_version_unverified", "software",
            field_path="/software/bedtools_version", expected_value=software["bedtools_version"],
            observed_value={"returncode": rc, "version": verification["bedtools_observed"]["observed_version"]}))
        verification["state"] = "failed"
    else:
        verification["state"] = "verified"


def _declaration(spec, paths):
    path = confined_file(paths[spec["file_key"]].parent, paths[spec["file_key"]].name)
    value = {"relative_path": spec["relative_path"], "format": spec["format"],
        "state": "absent", "sha256": None, "size_bytes": None}
    if path.exists():
        value.update(state="present", **file_identity(path))
    return value


def _manifest(plan, comparison, sets):
    index = {row["set_key"]: row for row in sets}
    return {"version": "genomic_overlap_native_manifest_v1", "comparison_key": comparison["comparison_key"],
        "identity": _identity(plan), "a_set_key": comparison["a_set_key"], "b_set_key": comparison["b_set_key"],
        "input_fingerprints": [index[comparison[side + "_set_key"]]["measured_fingerprint"] for side in ("a", "b")],
        "derivation": "not_executed_invalid_input", "outcome": "not_executed", "software": None,
        "realized_argv": [], "environment": {}, "returncode": None, "started_at": None,
        "finished_at": None, "writer_closed": True, "files": []}


def _replay(directory, plan):
    bundle = validate_genomic_overlap_batch(_read_control(confined_file(directory, BATCH_FILENAME)), plan=plan)
    started = _read_control(confined_file(directory, STARTED_FILENAME))
    _require(started == {"plan": plan, "started_at": bundle["started_at"]}, "original_attempt_mismatch")
    for row in bundle["files"]:
        declaration = row["declaration"]
        path = confined_file(directory, declaration["relative_path"])
        if declaration["state"] == "present":
            _require(file_identity(path) == {key: declaration[key] for key in ("sha256", "size_bytes")},
                "original_attempt_mismatch")
        else:
            _require(not path.exists(), "original_attempt_mismatch")
    return bundle


def run_genomic_overlap_driver(plan: dict) -> dict:
    """Execute or return an already sealed original attempt, never a suffix retry."""
    plan = validate_genomic_overlap_run_plan(plan)
    directory = _directory(plan["attempt_directory"])
    existed = directory.exists()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner = confined_file(directory, OWNER_FILENAME)
    if existed and any(directory.iterdir()):
        _require(owner.exists() and _read_control(owner) == plan, "original_attempt_mismatch")
        if confined_file(directory, BATCH_FILENAME).exists():
            return _replay(directory, plan)
        raise ValueError("unsealed_native_attempt")
    _immutable(owner, plan)
    started_at = _now()
    _immutable(confined_file(directory, STARTED_FILENAME), {"plan": plan, "started_at": started_at})
    job = plan["requested_job"]["native_genomic_overlap"]
    policy = LocalJobPolicy(**plan["policy"])
    environment = genomic_overlap_environment(job, attempt_directory=str(directory))
    # The shared worker supplies its own temporary overrides; explicitly apply
    # this selected driver's attempt-local overrides before any staging/calls.
    os.environ.update(environment)
    for name in ("tmp", "cache", "cache/pip"):
        path = _directory(directory / name)
        path.mkdir(parents=True, exist_ok=True)
    paths = {row["file_key"]: confined_file(directory, row["relative_path"]) for row in job["outputs"]}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    specs = {row["file_key"]: row for row in job["outputs"]}
    failures, sets, parsed, pairs = [], [], {}, []
    verification = _implementation(job["software"], failures)
    implementation_ok = verification["state"] != "failed"
    with paths["stdout"].open("xb") as stdout, paths["stderr"].open("xb") as stderr:
        for i, (spec, binding) in enumerate(zip(job["request"]["region_sets"], job["inputs"])):
            row = _stage(binding, spec, position=i, paths=paths, directory=directory, policy=policy, failures=failures)
            sets.append(row)
            if implementation_ok:
                value = _normalize(row, spec, paths=paths, directory=directory, policy=policy, failures=failures)
                if value is not None:
                    parsed[spec["set_key"]] = value
            else:
                row["failure_indices"].extend(verification["failure_indices"])
            _event(stdout, "set_normalized", set_position=i, set_key=spec["set_key"],
                input_state=row["input_state"], parse_extent=row["parse_extent"],
                region_count=len(parsed[spec["set_key"]]["regions"]) if spec["set_key"] in parsed else None)
        needs_native = any(all(key in parsed and parsed[key]["result_extent"] == "complete" and
            bool(parsed[key]["regions"]) for key in (p["a_set_key"], p["b_set_key"]))
            for p in job["request"]["comparisons"])
        if implementation_ok and needs_native:
            _bedtools(verification, job["software"], directory=directory, environment=environment,
                paths=paths, failures=failures)
        by_key = {row["set_key"]: row for row in sets}
        for comparison in job["request"]["comparisons"]:
            ordinal, key = comparison["ordinal"], comparison["comparison_key"]
            operands = [by_key[comparison[side + "_set_key"]] for side in ("a", "b")]
            row = {"comparison": deepcopy(comparison), "disposition": "input_unavailable",
                "manifest_file_key": None, "manifest": None, "failure_indices": []}
            row["failure_indices"] = list(dict.fromkeys(i for operand in operands for i in operand["failure_indices"]))
            if all(operand["input_state"] == "verified" for operand in operands):
                normalized = [parsed.get(operand["set_key"]) for operand in operands]
                if not implementation_ok or any(value is None for value in normalized):
                    row["disposition"] = "native_unavailable"
                elif any(value["result_extent"] != "complete" for value in normalized):
                    row.update(disposition="invalid_input", manifest=_manifest(plan, comparison, sets))
                elif any(not value["regions"] for value in normalized):
                    manifest = _manifest(plan, comparison, sets)
                    manifest["derivation"] = "validated_empty_input"
                    row.update(disposition="analytic_empty", manifest=manifest)
                elif verification["state"] != "verified":
                    row["disposition"] = "native_unavailable"
                    row["failure_indices"].extend(verification["failure_indices"])
                else:
                    manifest = _manifest(plan, comparison, sets)
                    argv = [job["software"]["bedtools_executable"], "intersect", "-a",
                        str(paths[operands[0]["canonical_file_key"]]), "-b",
                        str(paths[operands[1]["canonical_file_key"]]), "-wo", "-sorted"]
                    try:
                        check_scratch_budget(directory, policy)
                        rc, began, ended = _native_call(argv, directory=directory, environment=environment,
                            stdout=paths[f"p{ordinal}:stdout"], stderr=paths[f"p{ordinal}:stderr"],
                            on_start=lambda at: _event(stdout, "pair_started", at=at,
                                ordinal=ordinal, comparison_key=key))
                    except (_NativeSpawnError, AcquisitionError) as error:
                        row["disposition"] = "native_unavailable"
                        row["failure_indices"].append(_failure(failures,
                            "resource_limit" if isinstance(error, AcquisitionError) else "native_spawn_failed", "native",
                            comparison_key=key, file_key=f"p{ordinal}:stdout", observed_value=_error_value(error)))
                    else:
                        manifest.update(derivation="bedtools_intersect", outcome="succeeded" if rc == 0 else "failed",
                            software=deepcopy(verification["bedtools_observed"]), realized_argv=argv,
                            environment=environment, returncode=rc, started_at=began, finished_at=ended)
                        file_keys = [operands[0]["canonical_file_key"], operands[1]["canonical_file_key"],
                            f"p{ordinal}:stdout", f"p{ordinal}:stderr"]
                        manifest["files"] = [{"file_key": key + ":file:" + str(i), "role": role,
                            "declaration": _declaration(specs[file_key], paths)} for i, (role, file_key) in
                            enumerate(zip(("canonical_a", "canonical_b", "overlap_stdout", "overlap_stderr"), file_keys))]
                        row.update(disposition="native_succeeded" if rc == 0 else "native_failed", manifest=manifest)
                        if rc != 0:
                            row["failure_indices"].append(_failure(failures, "native_nonzero_exit", "native",
                                comparison_key=key, field_path="/returncode", expected_value=0, observed_value=rc))
            if row["manifest"] is not None:
                row["manifest"] = validate_genomic_overlap_pair_manifest(row["manifest"], plan=plan,
                    comparison=comparison, set_outputs=sets)
                row["manifest_file_key"] = f"p{ordinal}:manifest"
                _immutable(paths[row["manifest_file_key"]], row["manifest"])
            pairs.append(row)
            _event(stdout, "pair_closed", ordinal=ordinal, comparison_key=key, disposition=row["disposition"],
                returncode=row["manifest"]["returncode"] if row["manifest"] else None)
        for failure in failures:
            stderr.write((canonical(failure) + "\n").encode("utf-8"))
        for stream in (stdout, stderr):
            stream.flush()
            os.fsync(stream.fileno())
    paths["stdout"].chmod(0o444)
    paths["stderr"].chmod(0o444)
    successes = sum(row["disposition"] in {"native_succeeded", "analytic_empty"} for row in pairs)
    complete = successes == len(pairs) and all(row["parse_extent"] == "complete" for row in sets)
    bundle = {"version": "genomic_overlap_native_batch_v1", "identity": _identity(plan),
        "plan_sha256": digest(plan), "requested_job_sha256": plan["identity"]["requested_job_sha256"],
        "policy": plan["policy"], "driver_argv": genomic_overlap_driver_argv(plan),
        "realized_environment": environment, "requested_set_keys": [row["set_key"] for row in sets],
        "requested_comparisons": job["request"]["comparisons"], "software_verification": verification,
        "sets": sets, "pairs": pairs, "files": [{"specification": spec, "declaration": _declaration(spec, paths)}
            for spec in job["outputs"] if spec["role"] != "batch_manifest"], "failures": failures,
        "batch_status": "complete" if complete else "partial" if successes else "failed",
        "started_at": started_at, "finished_at": _now(), "sealed": True}
    bundle = validate_genomic_overlap_batch(bundle, plan=plan)
    _immutable(paths["batch_manifest"], bundle)
    return bundle


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _require(type(args) is list and len(args) == 1, "original_attempt_mismatch")
    plan = validate_genomic_overlap_run_plan(_read_control(Path(args[0])))
    _require(args[0] == genomic_overlap_driver_argv(plan)[-1] and
        Path.cwd() == Path(plan["identity"]["execution_id"]).parent, "original_attempt_mismatch")
    bundle = run_genomic_overlap_driver(plan)
    return 0 if bundle["batch_status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_genomic_overlap_driver", "main"]
