"""Stage, run and seal one selected masking command within native_lifecycle."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from .native_infernal_driver import (
    _ScratchLimit, _absolute_directory, _atomic_new, _confined_file,
    _digest_file, _now, _read_json, _regular_reader, _scratch,
)
from .native_blast_masking_contracts import (
    BUNDLE_VERSION, OWNER_NAME, PLAN_VERSION, FAILURE_CODES, _error,
    compile_native_blast_masking_job, generated_statistics_binding,
    native_environment, producer_failure, staged_relative,
    validate_native_blast_masking_plan, validate_original_bundle,
)
from .sequence_masking_inputs import preflight_masking_input_fasta

BUNDLE_NAME = "bundle.json"


def _failure(bundle, code, role=None, input_failures=None):
    item = producer_failure(code, role, input_failures)
    if item not in bundle["failures"]:
        bundle["failures"].append(item)


def _measure(root, relative):
    try:
        return _digest_file(_confined_file(root, relative))
    except (OSError, ValueError):
        return None, None


def _set_pair(row, prefix, pair):
    row[prefix + "size_bytes"], row[prefix + "sha256"] = pair


def _stage(root, job, policy, bundle):
    for operand in job["operands"]:
        role = operand["role"]
        row = {"role": role, "ordinal": 0, "format": operand["format"],
            "original_path": operand["path"], "relative_path": staged_relative(operand),
            "artifact_ref": operand["artifact_ref"], "expected_sha256": operand["sha256"],
            "expected_size_bytes": operand["size_bytes"], "staged_sha256": None,
            "staged_size_bytes": None, "final_sha256": None, "final_size_bytes": None}
        bundle["inputs"].append(row)
        destination = _confined_file(root, row["relative_path"])
        try:
            with _regular_reader(Path(operand["path"])) as reader:
                observed_size = os.fstat(reader.fileno()).st_size
                _scratch(root, policy, observed_size)
                # Retain actual supplied bytes even when their declared identity is wrong.
                with destination.open("xb") as writer:
                    for block in iter(lambda: reader.read(1024 * 1024), b""):
                        writer.write(block)
                        writer.flush()
                        _scratch(root, policy)
                    os.fsync(writer.fileno())
        except _ScratchLimit:
            _failure(bundle, "staging_scratch_limit", role)
        except (OSError, ValueError):
            _failure(bundle, "input_unavailable", role)
        pair = _measure(root, row["relative_path"])
        _set_pair(row, "staged_", pair)
        if pair[0] is not None:
            destination.chmod(0o444)
            if pair != (operand["size_bytes"], operand["sha256"]):
                _failure(bundle, "input_identity_mismatch", role)


def _preflight(root, job, bundle):
    if bundle["failures"]:
        return
    for row in bundle["inputs"]:
        content = _confined_file(root, row["relative_path"]).read_bytes()
        if row["role"] == "statistics":
            # This is framing only. Native refusal and retained full parsing
            # own statistics validity; no occurrence is fabricated pre-capture.
            if not content or any(c == 0 or c > 127 for c in content):
                _failure(bundle, "invalid_statistics", row["role"])
            continue
        parsed = preflight_masking_input_fasta(content,
            molecule="protein" if job["operation"]["program"] == "segmasker" else "dna")
        if not parsed["valid"]:
            _failure(bundle, "invalid_fasta", row["role"], parsed["failures"])
        if any(r["operand_role"] == row["role"] and r["record_ordinal"] >= parsed["record_count"]
               for r in job["operand_bindings"]):
            _failure(bundle, "record_binding_outside_input", row["role"])


def _final_inputs(root, bundle):
    for row in bundle["inputs"]:
        pair = _measure(root, row["relative_path"])
        _set_pair(row, "final_", pair)
        staged = row["staged_size_bytes"], row["staged_sha256"]
        if staged != pair:
            _failure(bundle, "immutable_input_changed", row["role"])
        if staged[0] is not None and pair[0] is None:
            _failure(bundle, "input_final_unavailable", row["role"])


def validate_native_blast_masking_bundle_files(bundle, directory):
    """Validate a sealed original attempt against its owner and actual bytes."""
    root = _absolute_directory(str(directory))
    plan = validate_native_blast_masking_plan(_read_json(_confined_file(root, OWNER_NAME), sealed=True))
    if plan["attempt_directory"] != str(root):
        _error("attempt_directory_conflict")
    bundle = validate_original_bundle(bundle, plan)
    for row in bundle["inputs"]:
        expected = row["final_size_bytes"], row["final_sha256"]
        if _measure(root, row["relative_path"]) != expected:
            _error("sealed_input_digest_mismatch")
    for row in bundle["artifacts"]:
        if _measure(root, row["relative_path"]) != (row["size_bytes"], row["sha256"]):
            _error("sealed_output_digest_mismatch")
    return bundle


def run_native_blast_masking(plan):
    plan = validate_native_blast_masking_plan(plan)
    root = _absolute_directory(plan["attempt_directory"])
    request, job = plan["requested_job"], plan["requested_job"]["native_blast_masking"]
    owner, manifest = root / OWNER_NAME, root / BUNDLE_NAME
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if not _confined_file(root, OWNER_NAME).is_file():
            _error("attempt_not_exclusively_owned")
        if _read_json(owner, sealed=True) != plan:
            _error("attempt_identity_conflict")
        if not _confined_file(root, BUNDLE_NAME).is_file():
            _error("unsealed_attempt_execution_uncertain")
        return validate_native_blast_masking_bundle_files(_read_json(manifest, sealed=True), root)
    _atomic_new(owner, plan)
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    argv = compile_native_blast_masking_job(job,
        input_paths={r["role"]: str(root / staged_relative(r)) for r in job["operands"]}, output_directory=str(root))
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": request,
        "operation": job["operation"], "software": {"executable": job["software"]["executable"],
            "expected_sha256": job["software"]["sha256"], "actual_sha256": None,
            "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": argv, "environment": native_environment(job, root), "inputs": [],
        "operand_bindings": job["operand_bindings"], "statistics_binding": job["statistics_binding"],
        "returncode": None, "artifacts": [], "failures": [], "started_at": _now(), "finished_at": None}
    try:
        _, actual = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual
        if actual != job["software"]["sha256"]:
            _failure(bundle, "software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software_not_executable")
    except (OSError, ValueError):
        _failure(bundle, "software_unavailable")
    _stage(root, job, plan["policy"], bundle)
    _preflight(root, job, bundle)
    outputs = {r["role"]: _confined_file(root, r["relative_path"]) for r in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                result = subprocess.run(argv, cwd=root, env=bundle["environment"], stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, check=False)
            bundle["returncode"] = result.returncode
            if result.returncode:
                _failure(bundle, "nonzero_returncode")
            _scratch(root, plan["policy"])
        except _ScratchLimit:
            _failure(bundle, "execution_scratch_limit")
        except OSError:
            _failure(bundle, "command_unavailable")
    _final_inputs(root, bundle)
    for selected in job["outputs"]:
        pair = _measure(root, selected["relative_path"])
        bundle["artifacts"].append({**selected, "ordinal": 0, "size_bytes": pair[0], "sha256": pair[1]})
        if pair[0] is None:
            _failure(bundle, "invalid_output" if outputs[selected["role"]].exists() else "missing_output", selected["role"])
    if job["operation"]["mode"] == "create_counts" and bundle["returncode"] == 0 and not bundle["failures"]:
        bundle["statistics_binding"] = generated_statistics_binding(bundle)
    bundle["finished_at"] = _now()
    validate_native_blast_masking_bundle_files(bundle, root)
    _atomic_new(manifest, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        _error("exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_blast_masking(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / BUNDLE_NAME)}))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
