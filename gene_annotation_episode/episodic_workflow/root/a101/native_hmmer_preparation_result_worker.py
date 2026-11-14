"""Bounded readers for retained preparation grading and saved-data selection.

The host supplies authenticated occurrences and explicit retained paths. This
worker never acquires a native result, runs an analysis, or publishes a Store
record. Grading and projection are separate tasks; projection imports no grader.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .domain import ContractError, canonical
from .library.native_record_identity import finite_json_copy, native_record_digest
from gene_annotation_episode.episodic_workflow.root.a101.native_hmmer_preparation_acquisition import _confined_reader, _decode, _read_record
from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_preparation_capture_contracts import _shape
from gene_annotation_episode.episodic_workflow.root.a101.native_hmmer_preparation_acquisition import validate_original_bundle
from .practical_execution_records import canonical as practical_canonical
from .practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_preparation_worker_context import PREFIX, effective_metadata, eligible_occurrences, failure, qualified_occurrences, unique_failures, validate_failures


PLAN_VERSION = PREFIX + "result_worker_plan_v1"
MANIFEST_VERSION = PREFIX + "result_worker_manifest_v1"
NUMERICAL_FILES = {"grading": "grading.json", "sheet": "sheet.json",
                   "calculations": "calculations.json"}




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


def _immutable_numerical(path, value):
    """Keep practical canonical bytes, escaping unencodable surrogates only.

    Native byte text survives JSON reading followed by surrogateescape encoding.
    The ordinary practical receipt/digest policy is intentionally unchanged.
    """
    payload = (practical_canonical(value) + "\n").encode("utf-8", errors="backslashreplace")
    descriptor, temporary = tempfile.mkstemp(prefix=".hmmer-numerical-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError("practical_immutable_record_conflict")
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def _write(directory, name, value):
    _immutable_numerical(directory / name, value)
    raw = (directory / name).read_bytes()
    return {"filename": name, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _grade(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_preparation_worker import grade_hmmer_preparation
    bundle = validate_original_bundle(plan["bundle"], plan["original_plan"])
    occurrences, problems = qualified_occurrences(bundle, plan["bundle_artifact_ref"], plan["capture"])
    metadata, metadata_failures = effective_metadata(bundle, occurrences, include_map_context=True)
    if (native_record_digest(plan["occurrences"]) != native_record_digest(occurrences)
            or native_record_digest(plan["effective_metadata"]) != native_record_digest(metadata)
            or native_record_digest(plan["failures"]) != native_record_digest(unique_failures([*problems, *metadata_failures]))):
        raise ContractError(PREFIX + "worker_authenticated_input_conflict")
    expected, files = eligible_occurrences(occurrences), plan["files"]
    if type(files) is not list or len(files) != len(expected):
        raise ContractError(PREFIX + "worker_retained_file_population_conflict")
    inputs, outputs, formats = {}, {}, {}
    for row, entry in zip(expected, files):
        if type(entry) is not dict or set(entry) != {"occurrence_id", "path"} or entry["occurrence_id"] != row["occurrence_id"]:
            raise ContractError(PREFIX + "worker_retained_file_association_conflict")
        try:
            raw = _read_bytes({"path": entry["path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]})
        except (ValueError, OSError) as error:
            _diagnostic(error, "reading", row["occurrence_id"])
            manifest["failures"].append(failure("reading", exception_code(error, PREFIX + "worker_retained_file_invalid")
                if isinstance(error, ValueError) else PREFIX + "worker_retained_file_unreadable", row["occurrence_id"]))
            continue
        occurrence = {k: row[k] for k in ("occurrence_id", "direction", "role", "ordinal", "artifact_ref",
                                               "sha256", "size_bytes", "completeness")}
        (inputs if row["direction"] == "input" else outputs).setdefault(row["role"], []).append({"occurrence": occurrence, "content": raw})
        formats[row["occurrence_id"]] = row["format"]
    grading = grade_hmmer_preparation(operation=bundle["operation"], inputs=inputs, outputs=outputs,
        formats=formats, metadata=metadata, parameters=bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"],
        native_abi=bundle["native_abi"])
    for field, name in NUMERICAL_FILES.items():
        manifest["outputs"][field] = _write(directory, name, grading if field == "grading" else grading[field])
    # Family-specific issues remain in the full sheets and calculators. An
    # expected duplicate label or missing optional measurement is not a universal
    # failed result, nor does completed=True erase those qualifications.


def _project(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_preparation_result_views import project_preparation_result
    context = plan["grading_context"]
    if type(context) is not dict or set(context) != {
            "version", "operation", "formats", "metadata", "native_abi", "requested_parameters"}:
        raise ContractError(PREFIX + "projection_grading_context_invalid")
    if plan["grading"] is None:
        if plan["selector"]["projection"] is not None:
            raise ContractError(PREFIX + "saved_numerical_grading_unavailable")
        grading = {**deepcopy(context), "sheet": None, "calculations": None}
    else:
        grading = _decode(_read_bytes(plan["grading"]))
        if any(native_record_digest(grading.get(k)) != native_record_digest(v)
               for k, v in context.items() if k != "formats"):
            raise ContractError(PREFIX + "projection_original_grading_conflict")
        actual, expected = grading.get("formats"), context["formats"]
        if type(actual) is not dict or type(expected) is not dict or any(expected.get(k) != v for k, v in actual.items()):
            raise ContractError(PREFIX + "projection_grading_formats_conflict")
        failed_reads = {r["record_key"] for r in plan["failures"] if r["stage"] == "reading"}
        if set(expected) - actual.keys() - failed_reads:
            raise ContractError(PREFIX + "projection_unexplained_missing_input")
    selected = project_preparation_result(grading, selector=plan["selector"],
        source_ref=plan["source_ref"], occurrences=plan["occurrences"])
    manifest["outputs"]["projection"] = _write(directory, "projection.json", selected)


def run(value):
    """Run exactly one saved-data task; return a small receipt, never a sheet."""
    plan = finite_json_copy(value)
    common = {"version", "task", "directory", "failures"}
    fields = {"grade": {"bundle", "original_plan", "bundle_artifact_ref", "capture", "occurrences",
                        "effective_metadata", "files"},
              "project": {"grading", "grading_context", "occurrences", "source_ref", "selector"}}
    if (type(plan) is not dict or plan.get("version") != PLAN_VERSION or plan.get("task") not in fields
            or set(plan) != common | fields[plan["task"]]):
        raise ContractError(PREFIX + "result_worker_plan_invalid")
    validate_failures(plan["failures"])
    directory = Path(plan["directory"])
    if not directory.is_absolute() or directory.resolve() != directory or not directory.is_dir():
        raise ContractError(PREFIX + "result_worker_directory_invalid")
    identity = {"plan_sha256": native_record_digest(plan)}
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
        "plan_sha256": native_record_digest(plan), "completed": False,
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
