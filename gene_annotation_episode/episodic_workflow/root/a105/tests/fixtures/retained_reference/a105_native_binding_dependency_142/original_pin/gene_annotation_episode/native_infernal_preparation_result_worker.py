"""Bounded readers for retained preparation grading and saved-data selection.

The host supplies authenticated occurrences and explicit retained paths. This
worker never acquires a native result, runs an analysis, or publishes a Store
record. Grading and projection are separate tasks; projection imports no grader.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from .domain import ContractError, canonical
from .infernal_preparation_schema import new_calculations, new_sheet
from .native_infernal_contracts import finite_json_copy, native_infernal_digest
from .native_infernal_preparation_acquisition import (
    _confined_reader, _decode, _read_record, _shape, validate_original_bundle,
)
from .practical_execution_state import _immutable


PREFIX = "native_infernal_preparation_"
PLAN_VERSION = PREFIX + "result_worker_plan_v1"
MANIFEST_VERSION = PREFIX + "result_worker_manifest_v1"
NUMERICAL_FILES = {"grading": "grading.json", "sheet": "sheet.json",
                   "calculations": "calculations.json"}


def failure(stage, code, record_key=None):
    return {"stage": stage, "code": code, "record_key": record_key}


def exception_code(error, fallback):
    """Keep literal machine codes; arbitrary exception text stays diagnostic.

    Already-recorded capture codes, including their file locators, are passed
    through separately and never normalized by this exception boundary.
    """
    candidate = getattr(error, "code", str(error))
    return candidate if type(candidate) is str and re.fullmatch(r"[a-z][A-Za-z0-9_]{0,191}", candidate) else fallback


def exception_diagnostic(error):
    return {"exception_type": type(error).__name__, "detail": str(error)}


def _diagnostic(error, stage, record_key=None):
    # The bounded host retains worker.stderr as a diagnostic artifact. Neither
    # this text nor its interpretation is a typed result failure or measurement.
    print(canonical({"stage": stage, "record_key": record_key, **exception_diagnostic(error)}), file=sys.stderr)


def validate_failures(rows):
    if type(rows) is not list or any(type(row) is not dict or set(row) != {
            "stage", "code", "record_key"} or any(type(row[k]) is not str or not row[k]
            for k in ("stage", "code")) or row["record_key"] is not None and
            (type(row["record_key"]) is not str or not row["record_key"]) for row in rows):
        raise ContractError(PREFIX + "result_failures_invalid")
    return rows


def unique_failures(rows):
    validate_failures(rows)
    return list({(r["stage"], r["code"], r["record_key"]): r for r in rows}.values())


def qualified_occurrences(bundle, bundle_ref, capture):
    """Pure association reconstruction from the original, validated capture.

    Input descriptors describe FINAL bytes. Only bytes equal to both the staged
    and expected identity qualify as original operands for the pure grader.
    """
    capture = _shape(capture)
    if (not capture["bundle_validated"] or capture["bundle_artifact_ref"] != bundle_ref
            or type(bundle_ref) is not str or not bundle_ref.startswith("artifact_")):
        raise ContractError(PREFIX + "grading_validated_capture_required")
    declared = {}
    sources = {(r["role"], r["ordinal"]): r for r in bundle["inputs"]}
    for collection, direction in (("inputs", "input"), ("working_copies", "working_copy"),
                                   ("artifacts", "output")):
        for index, row in enumerate(bundle[collection]):
            role = row["operand_role"] if direction == "working_copy" else row["role"]
            ordinal = row["operand_ordinal"] if direction == "working_copy" else row.get("ordinal", 0)
            fmt = sources[role, ordinal]["format"] if direction == "working_copy" else row["format"]
            sha = row["sha256"] if direction == "output" else row["final_sha256"]
            size = row["size_bytes"] if direction == "output" else row["final_size_bytes"]
            complete = bundle["returncode"] == 0 and not bundle["failures"]
            if direction == "input":
                complete = (sha is not None and sha == row["staged_sha256"] == row["expected_sha256"]
                    and size == row["staged_size_bytes"] == row["expected_size_bytes"])
            elif direction == "working_copy" and not row["mutable"]:
                original = sources[role, ordinal]
                complete = (sha is not None and sha == row["initial_sha256"] == row["source_sha256"]
                    == original["expected_sha256"] and size == row["initial_size_bytes"]
                    == original["expected_size_bytes"])
            key = direction, role, ordinal, row["relative_path"]
            declared[key] = {"occurrence_ref": bundle_ref + "#/" + collection + "/" + str(index),
                "direction": direction, "role": role, "ordinal": ordinal, "format": fmt,
                "relative_path": row["relative_path"], "sha256": sha, "size_bytes": size,
                "completeness": "complete" if complete else "partial"}
    result, seen, problems = [], set(), deepcopy(capture["failures"])
    for row in capture["artifacts"]:
        key = tuple(row[k] for k in ("direction", "role", "ordinal", "relative_path"))
        actual = declared.get(key)
        if (actual is None or key in seen or row["format"] != actual["format"]
                or actual["sha256"] is None or row["artifact_ref"] != "artifact_" + actual["sha256"]):
            raise ContractError(PREFIX + "grading_occurrence_association_conflict")
        seen.add(key)
        result.append({**actual, "artifact_ref": row["artifact_ref"]})
        if row["direction"] == "input" and actual["completeness"] != "complete":
            problems.append(failure("custody", PREFIX + "input_not_original_selected_bytes", actual["occurrence_ref"]))
    if (bundle["program"], bundle["mode"]) == ("cmfetch", "single_key"):
        raw = canonical(bundle["requested_job"]).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        result.append({"occurrence_ref": bundle_ref + "#/requested_job", "direction": "input",
            "role": "request", "ordinal": 0, "format": "infernal_request_json",
            "relative_path": "request.json", "artifact_ref": "artifact_" + digest,
            "sha256": digest, "size_bytes": len(raw), "completeness": "complete"})
    for index, row in enumerate(bundle["failures"]):
        matches = [r for r in result if r["role"] == row["role"] and (
            r["direction"] == "input" and row["detail"].get("ordinal") == r["ordinal"]
            or r["direction"] == "working_copy" and row["detail"].get("operand_ordinal") == r["ordinal"]
            or r["direction"] == "output" and row["stage"] == "outputs")]
        problems.append(failure(row["stage"], row["code"],
            matches[0]["occurrence_ref"] if len(matches) == 1 else bundle_ref + "#/failures/" + str(index)))
    if bundle["returncode"] != 0:
        problems.append(failure("native", PREFIX + "native_execution_unsuccessful", bundle_ref + "#/returncode"))
    return result, unique_failures(problems)


def effective_parameters(bundle, occurrences):
    """Use only provenance already proved by this selected producer/capture.

    A previous SSI or merge partition operand has no producer request in this
    contract. Its bytes remain retained, while producer-dependent checks stay
    unknown. Self-reported binding metadata is never accepted as that proof.
    """
    original = deepcopy(bundle["requested_job"]["native_infernal_preparation"]["grading_parameters"])
    result, problems = deepcopy(original), []
    lookup = {(r["direction"], r["role"], r["ordinal"]): r for r in occurrences}
    source = lookup.get(("input", "models", 0))
    source_ok = source is not None and source["completeness"] == "complete"
    if bundle["program"] in {"cmconvert", "cmfetch", "cmpress"}:
        authenticated = []
        copy = lookup.get(("working_copy", "models", 0))
        copies = [r for r in bundle["working_copies"] if r["operand_role"] == "models" and r["operand_ordinal"] == 0]
        valid_copy = (source_ok and copy is not None and len(copies) == 1 and not copies[0]["mutable"]
            and copy["completeness"] == "complete" and copy["sha256"] == source["sha256"]
            and bundle["returncode"] is not None)
        for row in occurrences:
            if row["role"] not in {"ssi", "i1m", "i1i", "i1f", "i1p"}:
                continue
            selected_output = (row["direction"] == "output" and valid_copy and (
                bundle["program"] == "cmpress" or (bundle["program"], bundle["mode"]) == ("cmfetch", "index")))
            if selected_output:
                authenticated.append({"artifact_ref": row["occurrence_ref"], "artifact_sha256": row["sha256"],
                    "source_artifact_ref": source["occurrence_ref"], "source_sha256": source["sha256"],
                    "expected_attempt_id": bundle["identity"]["attempt_id"],
                    "actual_attempt_id": bundle["identity"]["attempt_id"],
                    "staged_source_stem": copy["relative_path"], "actual_relative_path": row["relative_path"],
                    "regular_file": True})
            elif row["direction"] != "working_copy":
                problems.append(failure("metadata", PREFIX + "artifact_binding_unavailable", row["occurrence_ref"]))
        supplied = original.get("artifact_bindings")
        if supplied and native_infernal_digest(supplied) != native_infernal_digest(authenticated):
            problems.append(failure("metadata", PREFIX + "supplied_artifact_bindings_conflict"))
        if authenticated or "artifact_bindings" in original:
            result["artifact_bindings"] = authenticated
    if bundle["program"] in {"cmbuild", "cmcalibrate", "cmstat"}:
        authenticated = []
        output = lookup.get(("output", "partition_scores", 0))
        settings = bundle["operation"]["settings"]
        # The original request for the CURRENT partition is retained. Previous
        # partitions and GC-file identity need a separate explicit producer port.
        has_gc = any(r["role"] == "gc" for r in bundle["requested_job"]["native_infernal_preparation"]["operands"])
        if (bundle["program"], bundle["mode"]) == ("cmcalibrate", "partition_scores") and source_ok and output is not None and not has_gc:
            authenticated.append({"artifact_ref": output["occurrence_ref"],
                "source_model_artifact_ref": source["occurrence_ref"], "source_model_sha256": source["sha256"],
                "partition_index": settings["--part"], "partition_count": settings["--ptot"],
                "requested_megabases": settings["-L"], "settings": deepcopy(settings)})
        bound = {r["artifact_ref"] for r in authenticated}
        for row in occurrences:
            if row["role"] == "partition_scores" and row["direction"] != "working_copy" and row["occurrence_ref"] not in bound:
                problems.append(failure("metadata", PREFIX + "partition_request_binding_unavailable", row["occurrence_ref"]))
        if original.get("partition_requests") and native_infernal_digest(original["partition_requests"]) != native_infernal_digest(authenticated):
            problems.append(failure("metadata", PREFIX + "supplied_partition_requests_unverified"))
        result.pop("partition_requests", None)
        if authenticated:
            result["partition_requests"] = authenticated
    return result, problems


def eligible_occurrences(occurrences):
    return [r for r in occurrences if r["direction"] == "output" or
            r["direction"] == "input" and r["completeness"] == "complete"]


def _read_bytes(descriptor):
    if type(descriptor) is not dict or set(descriptor) != {"path", "sha256", "size_bytes"}:
        raise ContractError(PREFIX + "worker_file_descriptor_invalid")
    if (type(descriptor["path"]) is not str or type(descriptor["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", descriptor["sha256"]) is None
            or type(descriptor["size_bytes"]) is not int or descriptor["size_bytes"] < 0):
        raise ContractError(PREFIX + "worker_file_descriptor_invalid")
    path = Path(descriptor["path"])
    if not path.is_absolute():
        raise ContractError(PREFIX + "worker_absolute_retained_path_required")
    with _confined_reader(path.parent, path.name) as retained:
        raw = retained.read_bytes()
    if len(raw) != descriptor["size_bytes"] or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
        raise ContractError(PREFIX + "worker_retained_bytes_mismatch")
    return raw


def _write(directory, name, value):
    _immutable(directory / name, value)
    raw = (directory / name).read_bytes()
    return {"filename": name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _grade(plan, directory, manifest):
    from .native_infernal_preparation_worker import grade_infernal_preparation
    bundle = validate_original_bundle(plan["bundle"], plan["original_plan"])
    occurrences, problems = qualified_occurrences(bundle, plan["bundle_artifact_ref"], plan["capture"])
    parameters, metadata_failures = effective_parameters(bundle, occurrences)
    if (native_infernal_digest(plan["occurrences"]) != native_infernal_digest(occurrences)
            or native_infernal_digest(plan["effective_parameters"]) != native_infernal_digest(parameters)
            or native_infernal_digest(plan["failures"]) != native_infernal_digest(unique_failures([*problems, *metadata_failures]))):
        raise ContractError(PREFIX + "worker_authenticated_input_conflict")
    expected = eligible_occurrences(occurrences)
    files = plan["files"]
    if type(files) is not list or len(files) != len(expected):
        raise ContractError(PREFIX + "worker_retained_file_population_conflict")
    inputs, outputs = {}, {}
    for row, entry in zip(expected, files):
        if type(entry) is not dict or set(entry) != {"occurrence_ref", "path"} or entry["occurrence_ref"] != row["occurrence_ref"]:
            raise ContractError(PREFIX + "worker_retained_file_association_conflict")
        try:
            raw = _read_bytes({"path": entry["path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
        except (ValueError, OSError) as error:
            _diagnostic(error, "reading", row["occurrence_ref"])
            manifest["failures"].append(failure("reading", exception_code(error, PREFIX + "worker_retained_file_invalid")
                if isinstance(error, ValueError) else PREFIX + "worker_retained_file_unreadable", row["occurrence_ref"]))
            continue
        if row["role"] == "request" and raw != canonical(bundle["requested_job"]).encode("utf-8"):
            raise ContractError(PREFIX + "worker_original_request_bytes_conflict")
        artifact = {k: row[k] for k in ("role", "format", "sha256", "size_bytes", "completeness")}
        artifact["artifact_ref"] = row["occurrence_ref"]
        (inputs if row["direction"] == "input" else outputs).setdefault(row["role"], []).append({"artifact": artifact, "content": raw})
    grading = grade_infernal_preparation(operation=bundle["operation"], inputs=inputs,
        outputs=outputs, parameters=parameters)
    for field, name in NUMERICAL_FILES.items():
        manifest["outputs"][field] = _write(directory, name, grading if field == "grading" else grading[field])
    for value in (grading["sheet"], grading["calculations"]):
        for problem in value["issues"]:
            if problem["severity"] == "error":
                manifest["failures"].append(failure(problem["stage"], problem["code"], problem["record_key"]))


def _project(plan, directory, manifest):
    from .infernal_preparation_result_views import project_preparation_result
    if plan["grading"] is None:
        if plan["selector"]["projection"] is not None:
            raise ContractError(PREFIX + "saved_numerical_grading_unavailable")
        grading = {"version": PREFIX + "grading_v1", "operation": plan["operation"],
            "sheet": new_sheet(plan["operation"], []),
            "calculations": new_calculations(plan["operation"], {})}
    else:
        grading = _decode(_read_bytes(plan["grading"]))
        if grading.get("operation") != plan["operation"]:
            raise ContractError(PREFIX + "projection_original_operation_conflict")
    selected = project_preparation_result(grading, selector=plan["selector"],
        source_ref=plan["source_ref"], occurrences=plan["occurrences"])
    manifest["outputs"]["projection"] = _write(directory, "projection.json", selected)


def run(value):
    """Run exactly one saved-data task; return a small receipt, never a sheet."""
    plan = finite_json_copy(value)
    common = {"version", "task", "directory", "failures"}
    fields = {"grade": {"bundle", "original_plan", "bundle_artifact_ref", "capture", "occurrences",
                        "effective_parameters", "files"},
              "project": {"grading", "operation", "occurrences", "source_ref", "selector"}}
    if (type(plan) is not dict or plan.get("version") != PLAN_VERSION or plan.get("task") not in fields
            or set(plan) != common | fields[plan["task"]]):
        raise ContractError(PREFIX + "result_worker_plan_invalid")
    validate_failures(plan["failures"])
    directory = Path(plan["directory"])
    if not directory.is_absolute() or directory.resolve() != directory or not directory.is_dir():
        raise ContractError(PREFIX + "result_worker_directory_invalid")
    identity = {"plan_sha256": native_infernal_digest(plan)}
    if (directory / "worker-intent.json").exists():
        if _read_record(directory, "worker-intent.json") != identity:
            raise ContractError(PREFIX + "result_worker_identity_conflict")
        if not (directory / "worker-result.json").is_file():
            raise ContractError(PREFIX + "result_worker_original_work_incomplete")
        saved = _read_record(directory, "worker-result.json")
        if (type(saved) is not dict or set(saved) != {"version", "task", "plan_sha256", "completed", "outputs", "failures"}
                or saved["version"] != MANIFEST_VERSION or saved["task"] != plan["task"]
                or saved["plan_sha256"] != identity["plan_sha256"] or type(saved["completed"]) is not bool
                or type(saved["outputs"]) is not dict):
            raise ContractError(PREFIX + "result_worker_saved_manifest_invalid")
        validate_failures(saved["failures"])
        expected = NUMERICAL_FILES if plan["task"] == "grade" else {"projection": "projection.json"}
        if set(saved["outputs"]) - expected.keys() or saved["completed"] and set(saved["outputs"]) != set(expected):
            raise ContractError(PREFIX + "result_worker_saved_outputs_invalid")
        for role, descriptor in saved["outputs"].items():
            if (type(descriptor) is not dict or set(descriptor) != {"filename", "sha256", "size_bytes"}
                    or descriptor["filename"] != expected[role]):
                raise ContractError(PREFIX + "result_worker_saved_output_descriptor_invalid")
            _read_bytes({"path": str(directory / descriptor["filename"]),
                **{k: descriptor[k] for k in ("sha256", "size_bytes")}})
        return saved
    _immutable(directory / "worker-intent.json", identity)
    manifest = {"version": MANIFEST_VERSION, "task": plan["task"],
        "plan_sha256": native_infernal_digest(plan), "completed": False,
        "outputs": {}, "failures": deepcopy(plan["failures"])}
    try:
        (_grade if plan["task"] == "grade" else _project)(plan, directory, manifest)
        manifest["completed"] = True
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        _diagnostic(error, "worker")
        fallback = next(PREFIX + "result_worker_" + cls.__name__ for cls in
            (ValueError, OSError, KeyError, TypeError, IndexError) if isinstance(error, cls))
        manifest["failures"].append(failure("worker", exception_code(error, fallback)))
    manifest["failures"] = unique_failures(manifest["failures"])
    _immutable(directory / "worker-result.json", manifest)
    return manifest


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise ContractError(PREFIX + "exact_result_worker_plan_required")
    result = run(_decode(Path(arguments[0]).read_bytes()))
    print(canonical(result))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
