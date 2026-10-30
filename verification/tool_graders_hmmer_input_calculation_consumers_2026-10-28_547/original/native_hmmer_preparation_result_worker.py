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
from .native_infernal_contracts import finite_json_copy, native_infernal_digest
from .native_hmmer_preparation_acquisition import (
    _confined_reader, _decode, _read_record, _shape, validate_original_bundle,
)
from .practical_execution_state import _immutable


PREFIX = "native_hmmer_preparation_"
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
            declared[key] = {"occurrence_id": bundle_ref + "#/" + collection + "/" + str(index),
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
            problems.append(failure("custody", PREFIX + "input_not_original_selected_bytes", actual["occurrence_id"]))
    for index, row in enumerate(bundle["failures"]):
        matches = [r for r in result if r["role"] == row["role"] and (
            r["direction"] == "input" and row["detail"].get("ordinal") == r["ordinal"]
            or r["direction"] == "working_copy" and row["detail"].get("operand_ordinal") == r["ordinal"]
            or r["direction"] == "output" and row["stage"] == "outputs")]
        problems.append(failure(row["stage"], row["code"],
            matches[0]["occurrence_id"] if len(matches) == 1 else bundle_ref + "#/failures/" + str(index)))
    if bundle["returncode"] != 0:
        problems.append(failure("native", PREFIX + "native_execution_unsuccessful", bundle_ref + "#/returncode"))
    return result, unique_failures(problems)


def effective_metadata(bundle, occurrences, *, include_map_context=True):
    """Project original producer facts; imported declarations stay explicit.

    This function authenticates no external producer history. A current build
    has its own recorded ABI, attempt and input/output association. A caller's
    imported declaration remains a declaration, including any mismatch.
    """
    if type(include_map_context) is not bool:
        raise ContractError(PREFIX + "map_context_selection_invalid")
    job = bundle["requested_job"]["native_hmmer_preparation"]
    original = deepcopy(job["input_metadata"])
    metadata, problems = deepcopy(original), []
    lookup = {(r["direction"], r["role"], r["ordinal"]): r for r in occurrences}
    if bundle["program"] == "alimask" and include_map_context:
        from .hmmer_alignment_preparation_calculations import resolve_alimask_map_context
        alignment = lookup.get(("input", "alignment", 0))
        if alignment is not None and alignment["completeness"] == "complete":
            occurrence = {key: alignment[key] for key in ("occurrence_id", "direction", "role", "ordinal",
                "artifact_ref", "sha256", "size_bytes", "completeness")}
            metadata["map_reconstruction_context"] = resolve_alimask_map_context(operation=bundle["operation"],
                software=bundle["software"], source_occurrence=occurrence, requested_options=job["options"])
    source = lookup.get(("input", "models", 0))
    copy = lookup.get(("working_copy", "models", 0))
    valid_copy = (source is not None and copy is not None
        and source["completeness"] == copy["completeness"] == "complete"
        and source["sha256"] == copy["sha256"] and bundle["returncode"] is not None)
    if bundle["program"] in {"hmmconvert", "hmmfetch", "hmmpress"}:
        bindings = []
        for row in occurrences:
            if row["direction"] != "output" or row["role"] not in {
                    "ssi", "binary_models", "ssi_index", "msv_profiles", "remaining_profiles"}:
                continue
            selected = (bundle["program"] == "hmmpress" or
                        (bundle["program"], bundle["mode"]) == ("hmmfetch", "index"))
            if valid_copy and selected:
                bindings.append({"artifact_occurrence_id": row["occurrence_id"],
                    "source_occurrence_id": source["occurrence_id"], "source_sha256": source["sha256"],
                    "producer_attempt_id": bundle["identity"]["attempt_id"],
                    "staged_source_stem": copy["relative_path"], "actual_relative_path": row["relative_path"]})
            else:
                problems.append(failure("metadata", PREFIX + "artifact_binding_unavailable", row["occurrence_id"]))
        if bindings:
            metadata["artifact_bindings"] = bindings
    if bundle["program"] == "makehmmerdb":
        abi = bundle["native_abi"]
        contract = {"format": "hmmer_fm_3_4", "engine_version": bundle["operation"]["engine_version"],
            **{key: abi[key] for key in ("byte_order", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")}}
        if "producer_contract" in original and original["producer_contract"] != contract:
            problems.append(failure("metadata", PREFIX + "supplied_fm_producer_contract_conflict"))
        metadata["producer_contract"] = contract
        database = lookup.get(("output", "fm_database", 0))
        sources = [r for r in occurrences if r["direction"] == "input" and r["role"] == "sequences"]
        if database is not None and sources and all(r["completeness"] == "complete" for r in sources):
            binding = {"database_occurrence_id": database["occurrence_id"],
                "source_occurrence_ids": [r["occurrence_id"] for r in sources],
                "source_sha256s": [r["sha256"] for r in sources],
                "producer_attempt_id": bundle["identity"]["attempt_id"]}
            if "source_binding" in original and original["source_binding"] != binding:
                problems.append(failure("metadata", PREFIX + "supplied_fm_source_binding_conflict"))
            metadata["source_binding"] = binding
    return metadata, problems


def grading_context(bundle, occurrences, metadata):
    return {"version": PREFIX + "grading_v1", "operation": deepcopy(bundle["operation"]),
        "formats": {r["occurrence_id"]: r["format"] for r in eligible_occurrences(occurrences)},
        "metadata": deepcopy(metadata), "native_abi": deepcopy(bundle["native_abi"]),
        "requested_parameters": deepcopy(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"])}


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
    from .native_hmmer_preparation_worker import grade_hmmer_preparation
    bundle = validate_original_bundle(plan["bundle"], plan["original_plan"])
    occurrences, problems = qualified_occurrences(bundle, plan["bundle_artifact_ref"], plan["capture"])
    metadata, metadata_failures = effective_metadata(bundle, occurrences, include_map_context=True)
    if (native_infernal_digest(plan["occurrences"]) != native_infernal_digest(occurrences)
            or native_infernal_digest(plan["effective_metadata"]) != native_infernal_digest(metadata)
            or native_infernal_digest(plan["failures"]) != native_infernal_digest(unique_failures([*problems, *metadata_failures]))):
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
    from .hmmer_preparation_result_views import project_preparation_result
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
        if any(native_infernal_digest(grading.get(k)) != native_infernal_digest(v)
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
