"""One caller-selected bwrap invocation at original absolute VDB paths.

The wrapper supplies an isolated filesystem/PID/network namespace. Its status
records qualify the attempted command; they are not syscall-trace evidence or a
scientific result. All runtime files are selected beforehand, never discovered.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from jsonschema import Draft202012Validator

from .domain import ContractError
from .native_blast_contracts import finite_json_copy
from .native_blast_database_contracts import _absolute

VERSION = "native_blast_vdb_offline_execution_v1"
RECEIPT_VERSION = "native_blast_vdb_offline_receipt_v1"
OFFLINE_FAILURE_CODES = frozenset({"offline_launcher_unavailable", "offline_runtime_identity_mismatch",
    "offline_setup_failed", "offline_status_unavailable", "offline_configuration_conflict", "offline_child_exec_failed"})
_FILE = {"type": "object", "properties": {"path": {"type": "string", "minLength": 1},
    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "size_bytes": {"type": "integer", "minimum": 0}},
    "required": ["path", "sha256", "size_bytes"], "additionalProperties": False}
OFFLINE_EXECUTION_SCHEMA = {"type": "object", "properties": {
    "version": {"const": VERSION}, "launcher": _FILE, "runtime_files": {"type": "array", "items": _FILE},
    "runtime_aliases": {"type": "array", "items": {"type": "object", "properties": {
        "path": {"type": "string", "minLength": 1}, "target_path": {"type": "string", "minLength": 1}},
        "required": ["path", "target_path"], "additionalProperties": False}},
    "system_interface_profile": {"const": "blast_vdb_bwrap_local_v1"}},
    "required": ["version", "launcher", "runtime_files", "runtime_aliases", "system_interface_profile"],
    "additionalProperties": False}
OFFLINE_ENVIRONMENT_SCHEMA = {"type": "object", "properties": {
    "NCBI_VDB_CONFIG": {"type": "string", "minLength": 1}, "BLAST_USAGE_REPORT": {"const": "false"},
    "NCBI_USAGE_REPORT_ENABLED": {"const": "false"}, "DO_NOT_TRACK": {"const": "1"}, "LC_ALL": {"const": "C"}},
    "required": ["NCBI_VDB_CONFIG", "BLAST_USAGE_REPORT", "NCBI_USAGE_REPORT_ENABLED", "DO_NOT_TRACK", "LC_ALL"],
    "additionalProperties": False}


def _error(code):
    raise ContractError("native_blast_utility_" + code)


def _require(value, code="offline_configuration_conflict"):
    if not value:
        _error(code)


def _overlap(a, b):
    a, b = PurePosixPath(a), PurePosixPath(b)
    return a == b or a in b.parents or b in a.parents


def _runtime_files(job):
    rows, known = [], {}
    selected = job["offline_execution"]
    for row in [selected["launcher"], *selected["runtime_files"]]:
        previous = known.get(row["path"])
        _require(previous is None or previous == row)
        if previous is None:
            rows.append(row); known[row["path"]] = row
    return rows


def validate_vdb_offline_execution(value: dict, *, job: dict) -> dict:
    value = finite_json_copy(value)
    _require(next(Draft202012Validator(OFFLINE_EXECUTION_SCHEMA).iter_errors(value), None) is None)
    job = {**job, "offline_execution": value}
    from .native_blast_utility_contracts import database_file_selections
    _require(next(Draft202012Validator(OFFLINE_ENVIRONMENT_SCHEMA).iter_errors(job["environment"]), None) is None)
    config = job["databases"][0]["manifest"]["access"]["offline_configuration"]
    _require(config is not None and job["environment"]["NCBI_VDB_CONFIG"] == config["path"])
    selected = value["runtime_files"]
    _require(len({r["path"] for r in selected}) == len(selected))
    helper = [r for r in selected if r["path"] == job["software"]["executable"]]
    _require(len(helper) == 1 and helper[0]["sha256"] == job["software"]["sha256"])
    runtime = _runtime_files(job)
    paths = {r["path"] for r in runtime}
    data = database_file_selections(job)
    identities = {}
    for row in data:
        identity = row["expected_sha256"], row["expected_size_bytes"]
        _require(row["original_path"] not in identities or identities[row["original_path"]] == identity)
        identities[row["original_path"]] = identity
    aliases = value["runtime_aliases"]
    _require(len({r["path"] for r in aliases}) == len(aliases))
    for row in aliases:
        _require(row["target_path"] in paths and row["path"] not in paths)
    mounts = [*paths, *[r["path"] for r in aliases], *identities]
    for path in mounts:
        _absolute(path)
        _require(path != "/" and not any(_overlap(path, forbidden) for forbidden in
            ("/proc", "/dev", "/sys")))
    for i, path in enumerate(mounts):
        _require(not any(_overlap(path, other) for other in mounts[i + 1:]))
    return value


def compile_vdb_offline_argv(job: dict, *, attempt_directory: str,
                             native_argv: list[str], status_fd: int) -> list[str]:
    validate_vdb_offline_execution(job["offline_execution"], job=job)
    from .native_blast_utility_contracts import (compile_native_blast_utility_job,
        database_file_selections, native_environment, realized_path_maps)
    _absolute(attempt_directory)
    _require(type(status_fd) is int and status_fd >= 0)
    _require(native_argv == compile_native_blast_utility_job(job,
        **realized_path_maps(job, attempt_directory), output_directory=attempt_directory))
    root = PurePosixPath(attempt_directory)
    writable = [str(root / name) for name in ("tmp", "cache", "work")]
    data = [r["original_path"] for r in database_file_selections(job)]
    staged = list(realized_path_maps(job, attempt_directory)["input_paths"].values())
    runtime = [r["path"] for r in job["offline_execution"]["runtime_files"]]
    files = list(dict.fromkeys([*runtime, *data, *staged]))
    aliases = job["offline_execution"]["runtime_aliases"]
    destinations = [*files, *[r["path"] for r in aliases]]
    _require(not any(_overlap(path, target) for path in destinations for target in writable))
    _require(not any(_overlap(path, str(root)) for path in [*runtime, *data, *[r["path"] for r in aliases]]))
    directories = {str(root)}
    for path in [*destinations, *writable]:
        directories.update(str(p) for p in PurePosixPath(path).parents if str(p) != "/")
    # Only complete selected regular files are bound; directory databases are
    # represented by their empty parents plus these exact file mounts.
    args = [job["offline_execution"]["launcher"]["path"], "--unshare-user", "--unshare-pid",
        "--unshare-net", "--new-session", "--clearenv", "--json-status-fd", str(status_fd), "--tmpfs", "/"]
    for path in sorted(directories, key=lambda p: (len(PurePosixPath(p).parts), p)):
        args += ["--dir", path]
    for path in files:
        args += ["--ro-bind", path, path]
    for alias in aliases:
        args += ["--symlink", alias["target_path"], alias["path"]]
    for path in writable:
        args += ["--bind", path, path]
    args += ["--proc", "/proc", "--dev", "/dev", "--chdir", str(root)]
    # JSON object insertion order is not an execution selection. Canonical
    # saved jobs must compile to the original wrapper argv byte for byte.
    for key, value in sorted(native_environment(job, str(root)).items()):
        args += ["--setenv", key, value]
    # Device nodes remain usable for their native interfaces, while arbitrary
    # regular files cannot be placed in a writable dev/proc child mount.
    args += ["--remount-ro", "/proc", "--remount-ro", "/dev", "--remount-ro", "/", "--", *native_argv]
    return args


def _measure(path):
    from .native_infernal_driver import _absolute_directory, _confined_file, _digest_file
    path = Path(path)
    try:
        return _digest_file(_confined_file(_absolute_directory(str(path.parent)), path.name))
    except (OSError, ValueError):
        return None, None


def _failure(receipt, code):
    from .native_blast_utility_contracts import producer_failure
    row = producer_failure(code)
    if row not in receipt["failures"]:
        receipt["failures"].append(row)


def vdb_offline_native_outcome(receipt):
    """Return confirmed helper outcome only; raw wrapper facts remain separate."""
    unavailable = {"offline_launcher_unavailable", "offline_setup_failed", "offline_status_unavailable",
                   "offline_child_exec_failed", "offline_configuration_conflict"}
    before_matches = all((r["before_sha256"], r["before_size_bytes"]) ==
                         (r["expected_sha256"], r["expected_size_bytes"])
                         for r in receipt["runtime_files"])
    if (not before_matches or receipt["child_pid"] is None or receipt["child_exit_code"] is None or
            receipt["launcher_returncode"] != receipt["child_exit_code"] or
            any(r["code"] in unavailable for r in receipt["failures"])):
        return False, None
    return True, receipt["child_exit_code"]


def validate_vdb_offline_receipt(value, *, job, attempt_directory):
    receipt = finite_json_copy(value)
    fields = {"version", "launcher_argv", "status_fd", "status_records", "launcher_returncode",
              "child_pid", "child_exit_code", "runtime_files", "failures"}
    _require(type(receipt) is dict and set(receipt) == fields and receipt["version"] == RECEIPT_VERSION)
    _require(type(receipt["status_fd"]) is int and receipt["status_fd"] >= 0)
    _require(type(receipt["status_records"]) is list and all(type(r) is dict for r in receipt["status_records"]))
    for key in ("launcher_returncode", "child_pid", "child_exit_code"):
        _require(receipt[key] is None or type(receipt[key]) is int)
    _require(receipt["child_pid"] is None or receipt["child_pid"] > 0)
    from .native_blast_utility_contracts import compile_native_blast_utility_job, measurement_pair, realized_path_maps, producer_failure
    if receipt["launcher_argv"]:
        native = compile_native_blast_utility_job(job, **realized_path_maps(job, attempt_directory), output_directory=attempt_directory)
        _require(receipt["launcher_argv"] == compile_vdb_offline_argv(job, attempt_directory=attempt_directory,
            native_argv=native, status_fd=receipt["status_fd"]))
    else:
        _require(receipt["launcher_returncode"] is None and not receipt["status_records"])
    expected = _runtime_files(job)
    _require(type(receipt["runtime_files"]) is list and len(receipt["runtime_files"]) == len(expected))
    for row, original in zip(receipt["runtime_files"], expected):
        _require(type(row) is dict and set(row) == {"path", "expected_sha256", "expected_size_bytes",
            "before_sha256", "before_size_bytes", "final_sha256", "final_size_bytes"})
        _require(row["path"] == original["path"] and measurement_pair(row, "expected_") ==
                 (original["size_bytes"], original["sha256"]))
        for prefix in ("before_", "final_"):
            pair = measurement_pair(row, prefix)
            if pair != measurement_pair(row, "expected_"):
                _require(producer_failure("offline_runtime_identity_mismatch") in receipt["failures"] or
                    row["path"] == job["offline_execution"]["launcher"]["path"] and
                    producer_failure("offline_launcher_unavailable") in receipt["failures"])
        # A failed pre-execution identity check cannot coexist with a selected
        # wrapper attempt. A changed final identity still retains the observed
        # helper outcome, qualified by its separate custody failure.
        if measurement_pair(row, "before_") != measurement_pair(row, "expected_"):
            _require(not receipt["launcher_argv"])
    _require(type(receipt["failures"]) is list and len({json.dumps(r, sort_keys=True) for r in receipt["failures"]}) == len(receipt["failures"]))
    for row in receipt["failures"]:
        _require(row.get("code") in OFFLINE_FAILURE_CODES and row == producer_failure(row["code"]))
    pids = [r["child-pid"] for r in receipt["status_records"] if "child-pid" in r]
    exits = [r["exit-code"] for r in receipt["status_records"] if "exit-code" in r]
    expected_pid = pids[0] if len(pids) == 1 and type(pids[0]) is int and pids[0] > 0 else None
    expected_exit = exits[0] if len(exits) == 1 and type(exits[0]) is int else None
    _require(receipt["child_pid"] == expected_pid and receipt["child_exit_code"] == expected_exit)
    if receipt["launcher_argv"] and (expected_pid is None or expected_exit is None or receipt["launcher_returncode"] != expected_exit):
        _require(any(r["code"] in {"offline_launcher_unavailable", "offline_setup_failed", "offline_child_exec_failed", "offline_status_unavailable"} for r in receipt["failures"]))
    return receipt


def _run(job, *, attempt_directory, native_argv, stdout, stderr, blocked):
    from .native_infernal_driver import _absolute_directory, _confined_file, _regular_reader
    root = _absolute_directory(attempt_directory)
    validate_vdb_offline_execution(job["offline_execution"], job=job)
    for name in ("tmp", "cache", "work"):
        path = root / name
        path.mkdir(exist_ok=True)
        _require(path.resolve() == path and path.is_dir())
    receipt = {"version": RECEIPT_VERSION, "launcher_argv": [], "status_fd": 0,
        "status_records": [], "launcher_returncode": None, "child_pid": None, "child_exit_code": None,
        "runtime_files": [], "failures": []}
    for selected in _runtime_files(job):
        size, digest = _measure(selected["path"])
        receipt["runtime_files"].append({"path": selected["path"], "expected_sha256": selected["sha256"],
            "expected_size_bytes": selected["size_bytes"], "before_sha256": digest, "before_size_bytes": size,
            "final_sha256": None, "final_size_bytes": None})
        if (size, digest) != (selected["size_bytes"], selected["sha256"]):
            _failure(receipt, "offline_launcher_unavailable" if selected["path"] == job["offline_execution"]["launcher"]["path"]
                     else "offline_runtime_identity_mismatch")
    status_path = _confined_file(root, ".vdb-wrapper-status.jsonl")
    with status_path.open("xb") as status:
        receipt["status_fd"] = status.fileno()
        if not blocked and not receipt["failures"]:
            argv = compile_vdb_offline_argv(job, attempt_directory=attempt_directory, native_argv=native_argv, status_fd=status.fileno())
            receipt["launcher_argv"] = argv
            try:
                result = subprocess.run(argv, cwd=root, env={}, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, pass_fds=(status.fileno(),), check=False)
                receipt["launcher_returncode"] = result.returncode
            except OSError:
                _failure(receipt, "offline_launcher_unavailable")
        status.flush(); os.fsync(status.fileno())
    with _regular_reader(status_path) as source:
        raw = source.read()
    try:
        def reject_constant(value):
            raise ValueError(value)
        records = [json.loads(line, parse_constant=reject_constant) for line in raw.splitlines() if line.strip()]
        _require(all(type(r) is dict for r in records))
        receipt["status_records"] = finite_json_copy(records)
    except (ValueError, UnicodeError):
        _failure(receipt, "offline_status_unavailable")
    pids = [r["child-pid"] for r in receipt["status_records"] if "child-pid" in r]
    exits = [r["exit-code"] for r in receipt["status_records"] if "exit-code" in r]
    if len(pids) == 1 and type(pids[0]) is int and pids[0] > 0:
        receipt["child_pid"] = pids[0]
    if len(exits) == 1 and type(exits[0]) is int:
        receipt["child_exit_code"] = exits[0]
    if receipt["launcher_argv"]:
        stderr.flush()
        with _regular_reader(Path(stderr.name)) as source:
            diagnostics = source.read()
        if re.search(rb"(?m)^bwrap: (?:execvp|execv|exec |Failed to exec|Can't exec)", diagnostics):
            _failure(receipt, "offline_child_exec_failed")
        elif re.search(rb"(?m)^bwrap:", diagnostics):
            _failure(receipt, "offline_setup_failed")
        if (receipt["child_pid"] is None or receipt["child_exit_code"] is None or
                receipt["launcher_returncode"] != receipt["child_exit_code"]):
            _failure(receipt, "offline_status_unavailable")
    for row in receipt["runtime_files"]:
        row["final_size_bytes"], row["final_sha256"] = _measure(row["path"])
        if (row["final_size_bytes"], row["final_sha256"]) != (row["expected_size_bytes"], row["expected_sha256"]):
            _failure(receipt, "offline_runtime_identity_mismatch")
    return validate_vdb_offline_receipt(receipt, job=job, attempt_directory=attempt_directory)


def run_vdb_offline_once(job: dict, *, attempt_directory: str,
                        native_argv: list[str], stdout, stderr) -> dict:
    return _run(job, attempt_directory=attempt_directory, native_argv=native_argv,
                stdout=stdout, stderr=stderr, blocked=False)


def observe_vdb_offline_unstarted(job: dict, *, attempt_directory: str, native_argv: list[str]) -> dict:
    """Record controls for a producer-preflight failure without executing bwrap."""
    return _run(job, attempt_directory=attempt_directory, native_argv=native_argv,
                stdout=None, stderr=None, blocked=True)
