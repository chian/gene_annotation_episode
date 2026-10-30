"""Run one selected utility and seal its original, possibly partial, files.

The existing native lifecycle supplies process-tree limits. No checking utility,
database acquisition, retry, or result parser is invoked here.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys

from .native_infernal_driver import (
    _ScratchLimit, _absolute_directory, _atomic_new, _confined_file,
    _digest_file, _now, _read_json, _regular_reader, _scratch,
)
from .native_hmmer_preparation_acquisition import _decode
from .native_blast_utility_contracts import (
    BUNDLE_NAME, BUNDLE_VERSION, OWNER_NAME, _error,
    compile_native_blast_utility_job, database_file_selections, measurement_pair,
    native_environment, native_blast_utility_output_completeness, producer_failure, staged_relative,
    validate_native_blast_utility_bundle, validate_native_blast_utility_plan,
)


def _failure(bundle, code, **association):
    row = producer_failure(code, **association)
    if row not in bundle["failures"]:
        bundle["failures"].append(row)


def _measure(root, relative):
    try:
        return _digest_file(_confined_file(root, relative))
    except (OSError, ValueError):
        return None, None


def _original_file(path):
    path = Path(path)
    return _confined_file(_absolute_directory(str(path.parent)), path.name)


def _measure_original(path):
    try:
        return _digest_file(_original_file(path))
    except (OSError, ValueError):
        return None, None


def _set_pair(row, prefix, pair):
    row[prefix + "size_bytes"], row[prefix + "sha256"] = pair


def _family_paths(root, relative):
    """Enumerate only the explicitly selected prefix's own original directory."""
    prefix = root / relative
    parent = _absolute_directory(str(prefix.parent))
    with os.scandir(parent) as entries:
        return sorted(str((parent / entry.name).relative_to(root)) for entry in entries
                      if entry.name.startswith(prefix.name + "."))


def _database_inventory_matches(db):
    selected = {row["path"] for row in db["manifest"]["files"]}
    for value in db["native_paths"]:
        prefix = Path(value)
        actual = {str(prefix.parent / relative) for relative in _family_paths(prefix.parent, prefix.name)}
        if (actual != {path for path in selected if path.startswith(value + ".")}
                or prefix.exists() or prefix.is_symlink()):
            return False
    return True


def _observe_databases(job, bundle, *, final):
    if not final:
        bundle["database_files"] = [{**row, "before_sha256": None, "before_size_bytes": None,
            "final_sha256": None, "final_size_bytes": None} for row in database_file_selections(job)]
    for row in bundle["database_files"]:
        pair = _measure_original(row["original_path"])
        _set_pair(row, "final_" if final else "before_", pair)
        key = row["database_key"]
        if pair[0] is None:
            _failure(bundle, "database_unavailable", database_key=key)
        if final:
            if pair != measurement_pair(row, "before_"):
                _failure(bundle, "database_changed", database_key=key)
        elif pair[0] is not None and pair != measurement_pair(row, "expected_"):
            _failure(bundle, "database_identity_mismatch", database_key=key)
    for db in job["databases"]:
        key = db["database_key"]
        try:
            with _regular_reader(_original_file(db["manifest_file"]["path"])) as stream:
                actual = _decode(stream.read())
            matches = actual == db["manifest"] and _database_inventory_matches(db)
        except (OSError, ValueError):
            _failure(bundle, "database_unavailable", database_key=key)
            matches = False
        if not matches:
            _failure(bundle, "database_changed" if final else "database_identity_mismatch", database_key=key)


def _stage_inputs(root, job, policy, bundle):
    for selected in job["inputs"]:
        row = {"input_key": selected["input_key"], "role": selected["role"], "format": selected["format"],
            "original_path": selected["path"], "relative_path": staged_relative(selected),
            "artifact_ref": selected["artifact_ref"], "expected_sha256": selected["sha256"],
            "expected_size_bytes": selected["size_bytes"], "staged_sha256": None,
            "staged_size_bytes": None, "final_sha256": None, "final_size_bytes": None}
        bundle["inputs"].append(row)
        association = {"input_key": row["input_key"], "relative_path": row["relative_path"]}
        destination = _confined_file(root, row["relative_path"])
        try:
            with _regular_reader(Path(selected["path"])) as reader:
                _scratch(root, policy, os.fstat(reader.fileno()).st_size)
                with destination.open("xb") as writer:
                    for block in iter(lambda: reader.read(1024 * 1024), b""):
                        writer.write(block)
                        writer.flush()
                        _scratch(root, policy)
                    os.fsync(writer.fileno())
        except _ScratchLimit:
            _failure(bundle, "staging_scratch_limit", **association)
        except (OSError, ValueError):
            _failure(bundle, "input_unavailable", **association)
        pair = _measure(root, row["relative_path"])
        _set_pair(row, "staged_", pair)
        if pair[0] is not None:
            destination.chmod(0o444)
            if pair != measurement_pair(row, "expected_"):
                _failure(bundle, "input_identity_mismatch", **association)


def _final_inputs(root, bundle):
    for row in bundle["inputs"]:
        pair, before = _measure(root, row["relative_path"]), measurement_pair(row, "staged_")
        _set_pair(row, "final_", pair)
        association = {"input_key": row["input_key"], "relative_path": row["relative_path"]}
        if pair != before:
            _failure(bundle, "immutable_input_changed", **association)
        if before[0] is not None and pair[0] is None:
            _failure(bundle, "input_final_unavailable", **association)


def _capture_output(root, bundle, role, ordinal, relative, fmt):
    pair = _measure(root, relative)
    if pair[0] is None:
        path = root / relative
        _failure(bundle, "invalid_output" if path.exists() or path.is_symlink() else "missing_output",
                 relative_path=relative)
    bundle["artifacts"].append({"role": role, "ordinal": ordinal, "relative_path": relative,
        "format": fmt, "size_bytes": pair[0], "sha256": pair[1],
        "completeness": native_blast_utility_output_completeness(bundle, measured=pair[0] is not None)})
    return pair[0] is not None


def _collect_outputs(root, job, bundle):
    bundle["inventory_complete"] = True
    for row in job["outputs"]:
        if row["role"] != "database_family":
            _capture_output(root, bundle, row["role"], 0, row["relative_path"], row["format"])
    family = next((row["relative_path"] for row in job["outputs"] if row["role"] == "database_family"), None)
    if family is None:
        return
    try:
        candidates = _family_paths(root, family)
        if (root / family).exists() or (root / family).is_symlink():
            _failure(bundle, "invalid_output", relative_path=family)
            bundle["inventory_complete"] = False
    except (OSError, ValueError):
        candidates = []
        bundle["inventory_complete"] = False
    for ordinal, relative in enumerate(candidates):
        metadata = PurePosixPath(relative).suffix in {".njs", ".pjs"}
        if not _capture_output(root, bundle, "database_metadata" if metadata else "database_file", ordinal,
                relative, "blastdb_metadata_json" if metadata else "blastdb_binary"):
            bundle["inventory_complete"] = False
    if not candidates and bundle["inventory_complete"]:
        _failure(bundle, "missing_output", relative_path=family)
    if not bundle["inventory_complete"]:
        _failure(bundle, "output_inventory_incomplete", relative_path=family)


def validate_native_blast_utility_bundle_files(bundle: dict, directory) -> dict:
    """Qualify the sealed owner and original current files; never execute work."""
    root = _absolute_directory(str(directory))
    plan = validate_native_blast_utility_plan(_read_json(_confined_file(root, OWNER_NAME), sealed=True))
    if plan["attempt_directory"] != str(root):
        _error("attempt_directory_conflict")
    bundle = validate_native_blast_utility_bundle(bundle, plan)
    for row in bundle["inputs"]:
        if _measure(root, row["relative_path"]) != measurement_pair(row, "final_"):
            _error("sealed_input_digest_mismatch")
    for row in bundle["database_files"]:
        if _measure_original(row["original_path"]) != measurement_pair(row, "final_"):
            _error("sealed_database_digest_mismatch")
    for row in bundle["artifacts"]:
        if _measure(root, row["relative_path"]) != measurement_pair(row):
            _error("sealed_output_digest_mismatch")
    family = next((row["relative_path"] for row in plan["requested_job"]["native_blast_utility"]["outputs"]
                   if row["role"] == "database_family"), None)
    if family:
        expected = [row["relative_path"] for row in bundle["artifacts"]
                    if row["role"] in {"database_file", "database_metadata"}]
        try:
            actual = _family_paths(root, family)
        except (OSError, ValueError):
            if bundle["inventory_complete"]:
                _error("sealed_output_inventory_unavailable")
        else:
            if actual != expected:
                _error("sealed_output_inventory_changed")
    return bundle


def run_native_blast_utility(plan: dict) -> dict:
    plan = validate_native_blast_utility_plan(plan)
    root, request = _absolute_directory(plan["attempt_directory"]), plan["requested_job"]
    job = request["native_blast_utility"]
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        owner = _confined_file(root, OWNER_NAME)
        if not owner.is_file():
            _error("attempt_not_exclusively_owned")
        if _read_json(owner, sealed=True) != plan:
            _error("attempt_identity_conflict")
        manifest = _confined_file(root, BUNDLE_NAME)
        if not manifest.is_file():
            _error("unsealed_attempt_execution_uncertain")
        return validate_native_blast_utility_bundle_files(_read_json(manifest, sealed=True), root)
    _atomic_new(root / OWNER_NAME, plan)
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    argv = compile_native_blast_utility_job(job,
        input_paths={row["input_key"]: str(root / staged_relative(row)) for row in job["inputs"]},
        database_paths={db["database_key"]: db["native_paths"] for db in job["databases"]}, output_directory=str(root))
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": request,
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": None,
            "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": argv, "environment": native_environment(job, root), "started": False,
        "returncode": None, "writer_closed": False, "inventory_complete": False,
        "output_completeness_basis": "captured_bytes",
        "started_at": _now(), "finished_at": None, "inputs": [], "database_files": [], "artifacts": [], "failures": []}
    try:
        _, actual = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual
        if actual != job["software"]["sha256"]:
            _failure(bundle, "software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software_not_executable")
    except (OSError, ValueError):
        _failure(bundle, "software_unavailable")
    _stage_inputs(root, job, plan["policy"], bundle)
    _observe_databases(job, bundle, final=False)
    outputs = {row["role"]: _confined_file(root, row["relative_path"]) for row in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                result = subprocess.run(argv, cwd=root, env=bundle["environment"], stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, check=False)
            bundle["started"], bundle["returncode"] = True, result.returncode
            if result.returncode:
                _failure(bundle, "nonzero_returncode")
            _scratch(root, plan["policy"])
        except _ScratchLimit:
            _failure(bundle, "execution_scratch_limit")
        except OSError:
            _failure(bundle, "command_unavailable")
    bundle["writer_closed"] = True
    _final_inputs(root, bundle)
    _observe_databases(job, bundle, final=True)
    _collect_outputs(root, job, bundle)
    bundle["finished_at"] = _now()
    validate_native_blast_utility_bundle_files(bundle, root)
    _atomic_new(root / BUNDLE_NAME, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        _error("exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_blast_utility(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / BUNDLE_NAME)}))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
