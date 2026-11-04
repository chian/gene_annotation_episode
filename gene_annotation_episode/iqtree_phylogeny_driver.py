"""Store-free IQ-TREE LG/UFBoot invocation over an exact aligned FASTA File.

The ordinary owner selects and authenticates the supplied-alignment or explicit
MUSCLE-to-IQ-TREE route. This leaf receives the actual aligned File for either
route. It neither aligns sequences nor substitutes an inference algorithm.
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


OPERATION = "protein_phylogeny_iqtree_native"
REQUEST_VERSION = "iqtree_phylogeny_native_request_v1"
MANIFEST_VERSION = "iqtree_phylogeny_native_manifest_v1"
NATIVE_DIRECTORY_NAME = "iqtree-phylogeny-native"
INT_MAX = 2147483647
_FILES = (
    ("input", "input.fasta", "fasta", True),
    ("maximum_likelihood_tree", "result.treefile", "newick", True),
    ("bootstrap_consensus_tree", "result.contree", "newick", True),
    ("report", "result.iqtree", "iqtree_report", True),
    ("log", "result.log", "iqtree_log", True),
    ("bootstrap_splits", "result.splits.nex", "nexus", False),
    ("initial_tree", "result.bionj", "newick", False),
    ("distance_matrix", "result.mldist", "phylogenetic_distances", False),
    ("checkpoint", "result.ckp.gz", "iqtree_checkpoint", False),
    ("stdout", "stdout", "iqtree_log", True),
    ("stderr", "stderr", "iqtree_log", True),
)
ISSUE_CODES = tuple("iqtree_phylogeny_" + code for code in (
    "native_nonzero_exit", "staged_input_changed", "software_changed_after_execution",
    *(role + "_file_unavailable" for role, _, _, required in _FILES if required),
    "maximum_likelihood_tree_empty", "bootstrap_consensus_tree_empty"))


def _require(condition, code):
    if not condition:
        raise ValueError("iqtree_phylogeny_" + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields.split()), code)


def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _absolute_path(value):
    _require(type(value) is str and bool(value) and not any(char in value for char in "\0\r\n\\"), "path_invalid")
    path = PurePosixPath(value)
    _require(path.is_absolute() and str(path) == value and ".." not in path.parts
        and value != "/" and not value.startswith("//"), "path_invalid")
    return value


def validate_iqtree_parameters(value):
    """The selected model and bootstrap method have no inferred alternatives."""
    _closed(value, "model bootstrap_replicates threads seed", "parameters_invalid")
    _require(type(value["model"]) is str and value["model"] == "LG", "model_invalid")
    _require(type(value["bootstrap_replicates"]) is int and value["bootstrap_replicates"] == 1000,
        "bootstrap_replicates_invalid")
    for name in ("threads", "seed"):
        _require(type(value[name]) is int and 1 <= value[name] <= INT_MAX, "parameter_invalid_" + name)
    return deepcopy(value)


def validate_iqtree_software(value):
    """Validate an explicit physical pin without opening or running software."""
    _closed(value, "path sha256 size_bytes", "software_invalid")
    _absolute_path(value["path"])
    _require(_sha(value["sha256"]) and type(value["size_bytes"]) is int and value["size_bytes"] >= 0,
        "software_invalid")
    return deepcopy(value)


def validate_iqtree_native_request(value):
    _closed(value, "version input software parameters", "native_request_invalid")
    _require(value["version"] == REQUEST_VERSION, "native_request_version_invalid")
    operand = value["input"]
    _closed(operand, "path file source_ref", "input_invalid")
    _absolute_path(operand["path"])
    file = operand["file"]
    _closed(file, "artifact_ref sha256 size_bytes format", "input_file_invalid")
    _require(_sha(file["sha256"]) and file["artifact_ref"] == "artifact_" + file["sha256"]
        and type(file["size_bytes"]) is int and file["size_bytes"] >= 0 and file["format"] in ("fasta", "aligned_fasta"),
        "input_file_invalid")
    _require(operand["source_ref"] is None or type(operand["source_ref"]) is str
        and re.fullmatch(r"source_[0-9a-f]{24,64}", operand["source_ref"]) is not None, "input_source_invalid")
    return dict(version=REQUEST_VERSION, input=deepcopy(operand),
        software=validate_iqtree_software(value["software"]),
        parameters=validate_iqtree_parameters(value["parameters"]))


def iqtree_native_argv(request):
    """Preserve LG/-bb1000; select AA, CPU count and seed explicitly.

    The official command reference defines -nt, -seed and -st AA:
    https://iqtree.github.io/doc/Command-Reference
    """
    request = validate_iqtree_native_request(request)
    parameters = request["parameters"]
    return [request["software"]["path"], "-s", "input.fasta", "-st", "AA", "-m", "LG",
        "-bb", "1000", "-nt", str(parameters["threads"]), "-seed", str(parameters["seed"]), "-pre", "result"]


def validate_iqtree_native_manifest(value):
    """Validate declared byte relationships, never an execution receipt."""
    _closed(value, "version request argv returncode files issues", "native_manifest_invalid")
    _require(value["version"] == MANIFEST_VERSION, "native_manifest_version_invalid")
    request = validate_iqtree_native_request(value["request"])
    _require(type(value["argv"]) is list and value["argv"] == iqtree_native_argv(request), "native_manifest_argv_invalid")
    _require(type(value["returncode"]) is int, "native_manifest_returncode_invalid")
    _require(type(value["issues"]) is list and all(type(code) is str and code in ISSUE_CODES for code in value["issues"])
        and len(set(value["issues"])) == len(value["issues"]), "native_manifest_issues_invalid")
    specs = {role: (name, format, required) for role, name, format, required in _FILES}
    _require(type(value["files"]) is list, "native_manifest_files_invalid")
    found, order = {}, []
    for row in value["files"]:
        _closed(row, "role relative_path format sha256 size_bytes", "native_manifest_file_invalid")
        role = row["role"]
        _require(type(role) is str and role in specs and role not in found, "native_manifest_file_invalid")
        name, format, _ = specs[role]
        _require(row["relative_path"] == NATIVE_DIRECTORY_NAME + "/" + name and row["format"] == format
            and _sha(row["sha256"]) and type(row["size_bytes"]) is int and row["size_bytes"] >= 0,
            "native_manifest_file_invalid")
        found[role] = row
        order.append(role)
    _require(order == [role for role, _, _, _ in _FILES if role in found], "native_manifest_file_order_invalid")
    issues = set(value["issues"])
    _require((value["returncode"] != 0) == ("iqtree_phylogeny_native_nonzero_exit" in issues), "native_manifest_exit_issue_conflict")
    for role, _, _, required in _FILES:
        if required:
            _require((role not in found) == ("iqtree_phylogeny_" + role + "_file_unavailable" in issues), "native_manifest_file_issue_conflict")
    for role in ("maximum_likelihood_tree", "bootstrap_consensus_tree"):
        _require((role in found and found[role]["size_bytes"] == 0)
            == ("iqtree_phylogeny_" + role + "_empty" in issues), "native_manifest_empty_issue_conflict")
    changed = "input" in found and any(found["input"][key] != request["input"]["file"][key] for key in ("sha256", "size_bytes"))
    _require(changed == ("iqtree_phylogeny_staged_input_changed" in issues), "native_manifest_input_issue_conflict")
    return deepcopy(value)


@contextmanager
def _log(path):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        try:
            yield stream
        finally:
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o444)


def _software(value):
    try:
        _require(storage.file_pin(value["path"]) == value and os.access(value["path"], os.X_OK), "software_identity_conflict")
    except (OSError, ValueError) as error:
        raise ValueError("iqtree_phylogeny_software_identity_conflict") from error


def run_iqtree_native(request, *, output_directory):
    """Start one selected attempt; preserve failed native files without fallback."""
    request = validate_iqtree_native_request(request)
    _software(request["software"])
    parent = storage.directory(_absolute_path(str(output_directory)))
    with storage._directory_fd(parent) as descriptor:
        try:
            os.mkdir(NATIVE_DIRECTORY_NAME, mode=0o700, dir_fd=descriptor)
        except FileExistsError as error:
            raise ValueError("iqtree_phylogeny_native_attempt_exists") from error
        os.fsync(descriptor)
    directory = storage.directory(parent / NATIVE_DIRECTORY_NAME)
    observed = storage.retain_input(request["input"]["path"], storage.confined_file(directory, "input.fasta"),
        max_bytes=request["input"]["file"]["size_bytes"])
    _require(observed == {key: request["input"]["file"][key] for key in ("sha256", "size_bytes")}, "input_identity_conflict")
    for name in ("tmp", "cache"):
        storage.directory(directory / name, create=True)
    environment = dict(TMPDIR=str(directory / "tmp"), TMP=str(directory / "tmp"), TEMP=str(directory / "tmp"),
        XDG_CACHE_HOME=str(directory / "cache"), OMP_NUM_THREADS=str(request["parameters"]["threads"]), LC_ALL="C", LANG="C")
    argv = iqtree_native_argv(request)
    with _log(directory / "stdout") as stdout, _log(directory / "stderr") as stderr:
        try:
            process = subprocess.Popen(argv, cwd=directory, env=environment, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, shell=False)
        except OSError as error:
            raise ValueError("iqtree_phylogeny_native_spawn_failed") from error
        returncode = process.wait()
    issues = ["iqtree_phylogeny_native_nonzero_exit"] if returncode != 0 else []
    try:
        _software(request["software"])
    except ValueError:
        issues.append("iqtree_phylogeny_software_changed_after_execution")
    files = []
    for role, name, format, required in _FILES:
        try:
            path = storage.confined_file(directory, name)
            with storage.regular(path) as stream:
                os.fchmod(stream.fileno(), 0o444)
            pin = storage.file_pin(path)
        except (OSError, ValueError):
            if required:
                issues.append("iqtree_phylogeny_" + role + "_file_unavailable")
            continue
        files.append(dict(role=role, relative_path=NATIVE_DIRECTORY_NAME + "/" + name, format=format,
            **{key: pin[key] for key in ("sha256", "size_bytes")}))
        if role == "input" and any(pin[key] != request["input"]["file"][key] for key in ("sha256", "size_bytes")):
            issues.append("iqtree_phylogeny_staged_input_changed")
        if role in ("maximum_likelihood_tree", "bootstrap_consensus_tree") and pin["size_bytes"] == 0:
            issues.append("iqtree_phylogeny_" + role + "_empty")
    return validate_iqtree_native_manifest(dict(version=MANIFEST_VERSION, request=request, argv=argv,
        returncode=returncode, files=files, issues=issues))


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
    _require(result_path.parent == request_path.parent and result_path.name != NATIVE_DIRECTORY_NAME and not result_path.exists()
        and not result_path.is_symlink(), "worker_result_path_invalid")
    manifest = run_iqtree_native(envelope["arguments"]["request"], output_directory=result_path.parent)
    storage.immutable_bytes(result_path, json.dumps(manifest, sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False).encode() + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
