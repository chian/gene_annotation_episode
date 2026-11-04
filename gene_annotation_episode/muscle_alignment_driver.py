"""Store-free, one-attempt MUSCLE invocation over an exact supplied FASTA File.

The ordinary owner authenticates action/admission/runtime selection. This leaf
copies bytes and declares actual files; it does not parse an alignment, calculate
conservation, publish a Source or establish complete intended row membership.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

from . import native_flux_balance_storage as storage


OPERATION = "protein_conservation_native"
REQUEST_VERSION = "muscle_alignment_native_request_v1"
MANIFEST_VERSION = "muscle_alignment_native_manifest_v1"
NATIVE_DIRECTORY_NAME = "muscle-alignment-native"
PERMUTATIONS = ("none", "abc", "acb", "bca")
NATIVE_UNSIGNED_MAX = 4294967295
ISSUE_CODES = tuple("muscle_alignment_" + code for code in (
    "native_nonzero_exit", "alignment_missing", "alignment_empty",
    "input_file_unavailable", "alignment_file_unavailable",
    "stdout_file_unavailable", "stderr_file_unavailable",
    "staged_input_changed", "software_changed_after_execution"))
_FILE_SPECS = (
    ("input", "input.fasta", "fasta"),
    ("alignment", "aligned.fasta", "fasta"),
    ("stdout", "stdout", "muscle_log"),
    ("stderr", "stderr", "muscle_log"),
)


def _require(condition, code):
    if not condition:
        raise ValueError("muscle_alignment_" + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields.split()), code)


def _sha(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def _absolute_path(value):
    _require(type(value) is str and bool(value) and not any(c in value for c in "\0\r\n\\"),
        "path_invalid")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
        and value != "/" and not value.startswith("//"), "path_invalid")
    return value


def validate_muscle_alignment_parameters(value):
    """Validate explicit native unsigned parameters; infer no defaults."""
    _closed(value, "threads randseed perturb perm consiters refineiters", "parameters_invalid")
    for key in ("threads", "randseed", "perturb", "consiters", "refineiters"):
        _require(type(value[key]) is int and (1 if key in ("threads", "randseed") else 0)
            <= value[key] <= NATIVE_UNSIGNED_MAX,
            "parameter_invalid_" + key)
    _require(type(value["perm"]) is str and value["perm"] in PERMUTATIONS, "parameter_invalid_perm")
    return deepcopy(value)


def validate_muscle_alignment_software(value):
    """Validate a caller-selected physical pin, without inspecting a path."""
    _closed(value, "path sha256 size_bytes", "software_invalid")
    _absolute_path(value["path"])
    _require(_sha(value["sha256"]) and type(value["size_bytes"]) is int
        and value["size_bytes"] >= 0, "software_invalid")
    return deepcopy(value)


def validate_muscle_alignment_native_request(value):
    _closed(value, "version input software parameters", "native_request_invalid")
    _require(value["version"] == REQUEST_VERSION, "native_request_version_invalid")
    operand = value["input"]
    _closed(operand, "path file source_ref", "input_invalid")
    _absolute_path(operand["path"])
    file = operand["file"]
    _closed(file, "artifact_ref sha256 size_bytes format", "input_file_invalid")
    _require(_sha(file["sha256"]) and file["artifact_ref"] == "artifact_" + file["sha256"]
        and type(file["size_bytes"]) is int and file["size_bytes"] >= 0 and file["format"] == "fasta",
        "input_file_invalid")
    _require(operand["source_ref"] is None or type(operand["source_ref"]) is str
        and re.fullmatch("source_[0-9a-f]{24,64}", operand["source_ref"]) is not None,
        "input_source_invalid")
    software = validate_muscle_alignment_software(value["software"])
    parameters = validate_muscle_alignment_parameters(value["parameters"])
    return dict(version=REQUEST_VERSION, input=deepcopy(operand), software=software, parameters=parameters)


def muscle_alignment_native_argv(request):
    request = validate_muscle_alignment_native_request(request)
    parameters = request["parameters"]
    return [request["software"]["path"], "-align", "input.fasta", "-output", "aligned.fasta",
        "-threads", str(parameters["threads"]), "-randseed", str(parameters["randseed"]),
        "-perturb", str(parameters["perturb"]), "-perm", parameters["perm"],
        "-consiters", str(parameters["consiters"]), "-refineiters", str(parameters["refineiters"])]


def validate_muscle_alignment_native_manifest(value):
    """Validate byte relationships only; a shape is not a native receipt."""
    _closed(value, "version request argv returncode files issues", "native_manifest_invalid")
    _require(value["version"] == MANIFEST_VERSION, "native_manifest_version_invalid")
    request = validate_muscle_alignment_native_request(value["request"])
    _require(type(value["argv"]) is list and value["argv"] == muscle_alignment_native_argv(request),
        "native_manifest_argv_invalid")
    _require(type(value["returncode"]) is int, "native_manifest_returncode_invalid")
    _require(type(value["issues"]) is list and all(type(code) is str and code in ISSUE_CODES
        for code in value["issues"]) and len(value["issues"]) == len(set(value["issues"])),
        "native_manifest_issues_invalid")
    _require(type(value["files"]) is list, "native_manifest_files_invalid")
    specs = {role: (name, format) for role, name, format in _FILE_SPECS}
    files, order = {}, []
    for row in value["files"]:
        _closed(row, "role relative_path format sha256 size_bytes", "native_manifest_file_invalid")
        role = row["role"]
        _require(type(role) is str and role in specs and role not in files, "native_manifest_file_invalid")
        name, format = specs[role]
        _require(row["relative_path"] == NATIVE_DIRECTORY_NAME + "/" + name and row["format"] == format
            and _sha(row["sha256"]) and type(row["size_bytes"]) is int and row["size_bytes"] >= 0,
            "native_manifest_file_invalid")
        files[role] = row
        order.append(role)
    _require(order == [role for role, _, _ in _FILE_SPECS if role in files], "native_manifest_file_order_invalid")
    issues = set(value["issues"])
    _require((value["returncode"] != 0) == ("muscle_alignment_native_nonzero_exit" in issues),
        "native_manifest_exit_issue_conflict")
    for role in ("input", "stdout", "stderr"):
        _require((role not in files) == ("muscle_alignment_" + role + "_file_unavailable" in issues),
            "native_manifest_file_issue_conflict")
    alignment_missing = "muscle_alignment_alignment_missing" in issues
    alignment_unavailable = "muscle_alignment_alignment_file_unavailable" in issues
    _require((not alignment_missing and not alignment_unavailable) if "alignment" in files
        else alignment_missing != alignment_unavailable, "native_manifest_alignment_issue_conflict")
    _require(("alignment" in files and files["alignment"]["size_bytes"] == 0)
        == ("muscle_alignment_alignment_empty" in issues), "native_manifest_empty_issue_conflict")
    changed = "input" in files and any(files["input"][key] != request["input"]["file"][key]
        for key in ("sha256", "size_bytes"))
    _require(changed == ("muscle_alignment_staged_input_changed" in issues),
        "native_manifest_input_issue_conflict")
    return deepcopy(value)


def _reserve_native_directory(output_directory):
    parent = storage.directory(_absolute_path(str(output_directory)))
    with storage._directory_fd(parent) as descriptor:
        try:
            os.mkdir(NATIVE_DIRECTORY_NAME, mode=0o700, dir_fd=descriptor)
        except FileExistsError as error:
            raise ValueError("muscle_alignment_native_attempt_exists") from error
        os.fsync(descriptor)
    return storage.directory(parent / NATIVE_DIRECTORY_NAME)


def _check_software(software):
    try:
        actual = storage.file_pin(software["path"])
        _require(actual == software and os.access(software["path"], os.X_OK), "software_identity_conflict")
    except (OSError, ValueError) as error:
        raise ValueError("muscle_alignment_software_identity_conflict") from error


def _stage_input(operand, directory):
    target = storage.confined_file(directory, "input.fasta")
    try:
        observed = storage.retain_input(operand["path"], target, max_bytes=operand["file"]["size_bytes"])
        _require(observed == {key: operand["file"][key] for key in ("sha256", "size_bytes")},
            "input_identity_conflict")
    except (OSError, ValueError) as error:
        raise ValueError("muscle_alignment_input_identity_conflict") from error
    return target


@contextmanager
def _native_log(path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        try:
            yield stream
        finally:
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)


def _observed_files(directory, request):
    files, issues = [], []
    for role, name, format in _FILE_SPECS:
        try:
            path = storage.confined_file(directory, name)
            with storage.regular(path) as stream:
                os.fchmod(stream.fileno(), 0o444)
            pin = storage.file_pin(path)
        except FileNotFoundError:
            issues.append("muscle_alignment_alignment_missing" if role == "alignment"
                else "muscle_alignment_" + role + "_file_unavailable")
            continue
        except (OSError, ValueError):
            issues.append("muscle_alignment_" + role + "_file_unavailable")
            continue
        files.append(dict(role=role, relative_path=NATIVE_DIRECTORY_NAME + "/" + name,
            format=format, **{key: pin[key] for key in ("sha256", "size_bytes")}))
        if role == "input" and any(pin[key] != request["input"]["file"][key]
                for key in ("sha256", "size_bytes")):
            issues.append("muscle_alignment_staged_input_changed")
        if role == "alignment" and pin["size_bytes"] == 0:
            issues.append("muscle_alignment_alignment_empty")
    return files, issues


def run_muscle_alignment_native(request, *, output_directory):
    """Run once beneath the existing owned worker parent; never repeat an attempt.

    Unstarted/spawn failures have no invented native returncode. Created files
    remain at their real paths for the ordinary host's terminal capture.
    """
    request = validate_muscle_alignment_native_request(request)
    _check_software(request["software"])
    directory = _reserve_native_directory(output_directory)
    _stage_input(request["input"], directory)
    for name in ("tmp", "cache"):
        storage.directory(directory / name, create=True)
    environment = dict(TMPDIR=str(directory / "tmp"), TMP=str(directory / "tmp"), TEMP=str(directory / "tmp"),
        XDG_CACHE_HOME=str(directory / "cache"), OMP_NUM_THREADS=str(request["parameters"]["threads"]),
        LC_ALL="C", LANG="C")
    argv = muscle_alignment_native_argv(request)
    with _native_log(directory / "stdout") as stdout, _native_log(directory / "stderr") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=directory, env=environment,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
        except OSError as error:
            raise ValueError("muscle_alignment_native_spawn_failed") from error
        returncode = process.wait()
    issues = ["muscle_alignment_native_nonzero_exit"] if returncode != 0 else []
    try:
        _check_software(request["software"])
    except ValueError:
        issues.append("muscle_alignment_software_changed_after_execution")
    files, observed_issues = _observed_files(directory, request)
    issues.extend(observed_issues)
    return validate_muscle_alignment_native_manifest(dict(version=MANIFEST_VERSION,
        request=request, argv=argv, returncode=returncode, files=files, issues=issues))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("result")
    args = parser.parse_args(argv)
    request_path = Path(_absolute_path(args.request))
    envelope = storage.read_json(request_path)
    _closed(envelope, "operation arguments", "worker_request_invalid")
    _require(envelope["operation"] == OPERATION, "worker_operation_invalid")
    _closed(envelope["arguments"], "request", "worker_arguments_invalid")
    result_path = Path(_absolute_path(args.result))
    _require(result_path.parent == request_path.parent and result_path.name != NATIVE_DIRECTORY_NAME,
        "worker_result_path_invalid")
    _require(not result_path.is_symlink() and not result_path.exists(), "worker_result_exists")
    manifest = run_muscle_alignment_native(envelope["arguments"]["request"], output_directory=result_path.parent)
    storage.immutable_bytes(result_path, json.dumps(manifest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
