"""Bounded deterministic stages over retained masking bytes and saved sheets.

The host owns capture and publication. These stages neither submit native work
nor use a Store or model. Replaying a completed stage reads its original receipt.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

from .domain import ContractError, canonical
from .native_blast_masking_acquisition import validate_native_blast_masking_capture
from .native_blast_masking_contracts import (
    finite_json_copy, native_blast_digest, masking_occurrence_id, validate_original_bundle,
)
from .native_hmmer_preparation_acquisition import _decode, _directory, _read_record
from .native_hmmer_preparation_result_worker import _read_bytes, _write
from .practical_execution_state import _immutable
from .sequence_masking_contracts import validate_sequence_masking_record as core
from .sequence_masking_result_views import failure, unique_failures


PREFIX = "native_blast_masking_"
PLAN_VERSION = PREFIX + "result_worker_plan_v1"
MANIFEST_VERSION = PREFIX + "result_worker_manifest_v1"
OUTPUT_FILES = {"sheet": "sheet.json", "calculations": "calculations.json",
                "statistics": "statistics.json", "projection": "projection.json",
                "recalculations": "recalculations.json"}


def _error(code):
    raise ContractError(PREFIX + code)


def exception_code(error, fallback):
    value = getattr(error, "code", str(error))
    return value if type(value) is str and re.fullmatch(r"[a-z][a-z0-9_]*", value) else fallback


def diagnostic(error):
    return {"exception_type": type(error).__name__, "detail": str(error)}


def _occurrence_id(bundle, direction, role):
    if direction == "input" and role == "statistics":
        return bundle["statistics_binding"]["statistics_occurrence_id"]
    return masking_occurrence_id(bundle["identity"], direction, role)


def qualified_masking_context(bundle, capture):
    """Reconstruct typed custody facts from a previously authenticated Bundle."""
    capture = validate_native_blast_masking_capture(capture)
    if not capture["bundle_validated"] or capture["bundle_artifact_ref"] is None:
        _error("validated_capture_required")
    originals = {}
    for direction, collection in (("input", "inputs"), ("output", "artifacts")):
        for row in bundle[collection]:
            originals[direction, row["role"], row["ordinal"]] = row
    rc = bundle["returncode"]
    succeeded = rc == 0 and not bundle["failures"]
    state = "succeeded" if succeeded else "incomplete" if rc == 0 else "failed"
    rows = []
    for item in capture["artifacts"]:
        slot = tuple(item[k] for k in ("direction", "role", "ordinal"))
        row = originals.get(slot)
        if row is None or any(item[k] != row[k] for k in ("role", "ordinal", "format", "relative_path")):
            _error("captured_occurrence_association_conflict")
        direction, role, ordinal = slot
        if direction == "input":
            identities = [(row[p + "sha256"], row[p + "size_bytes"]) for p in ("expected_", "staged_", "final_")]
            valid = all(pair == (item["sha256"], item["size_bytes"]) for pair in identities)
        else:
            valid = (row["sha256"], row["size_bytes"]) == (item["sha256"], item["size_bytes"])
        if not valid or item["artifact_ref"] != "artifact_" + item["sha256"]:
            _error("captured_occurrence_identity_conflict")
        complete = direction == "input" or succeeded or role in {"stdout", "stderr"} and rc is not None
        rows.append(core("Occurrence", {"occurrence_id": _occurrence_id(bundle, direction, role),
            "direction": direction, "role": role, "ordinal": ordinal, "artifact_ref": item["artifact_ref"],
            "sha256": item["sha256"], "size_bytes": item["size_bytes"],
            "completeness": "complete" if complete else "partial"}))
    if len({r["occurrence_id"] for r in rows}) != len(rows):
        _error("captured_occurrence_identity_duplicate")
    primary = "statistics" if bundle["operation"]["mode"] == "create_counts" else "mask"
    output_complete = succeeded and any(r["direction"] == "output" and r["role"] == primary for r in rows)
    outcome = core("NativeOutcome", {"returncode": rc, "state": state, "output_complete": output_complete})
    failures = []
    for original in bundle["failures"]:
        role = original["role"]
        direction = "input" if role in {r["role"] for r in bundle["inputs"]} else "output"
        oid = _occurrence_id(bundle, direction, role) if role else None
        stage = "input" if original["stage"] in {"inputs", "preflight"} else "native"
        failures.append(failure(stage, original["code"], oid))
        for row in original["input_failures"]:
            key = oid + "#/records/" + str(row["record_ordinal"]) if oid and row["record_ordinal"] is not None else None
            failures.append(failure("input", row["code"], oid, key, row["line_number"]))
    for original in capture["failures"]:
        oid = _occurrence_id(bundle, original["direction"], original["role"]) if original["direction"] else None
        failures.append(failure("custody", original["code"], oid))
    if state != "succeeded":
        failures.append(failure("native", "native_" + state))
    return rows, outcome, unique_failures(failures)


def expected_outputs(plan):
    if plan["task"] == "project_saved":
        return {"projection", *({"recalculations"} if plan["selector"]["mode"] == "saved_recalculation" else set())}
    roles = set()
    slots = {(r["direction"], r["role"]) for r in plan["occurrences"]}
    if ("output", "mask") in slots:
        roles.update({"sheet", "calculations"})
    if any(role == "statistics" for _, role in slots):
        roles.add("statistics")
    return roles


def _parse_calculate(plan, directory, manifest):
    from .sequence_masking_inputs import parse_masking_input_fasta, parse_sequence_masking_output, populate_sequence_masking_sheet
    from .sequence_masking_calculations import calculate_sequence_masking_components
    from .windowmasker_statistics import parse_windowmasker_statistics

    bundle = validate_original_bundle(plan["bundle"], plan["original_plan"])
    occurrences, outcome, failures = qualified_masking_context(bundle, plan["capture"])
    if (plan["capture"]["bundle_artifact_ref"] != plan["bundle_artifact_ref"]
            or (plan["occurrences"], plan["native_outcome"], plan["failures"]) != (occurrences, outcome, failures)):
        _error("worker_original_context_conflict")
    expected = [r for r in occurrences if r["role"] not in {"stdout", "stderr"}]
    if type(plan["files"]) is not list or len(plan["files"]) != len(expected):
        _error("worker_file_population_conflict")
    contents = {}
    for occurrence, descriptor in zip(expected, plan["files"]):
        if (type(descriptor) is not dict or set(descriptor) != {"occurrence_id", "path", "sha256", "size_bytes"}
                or any(descriptor[k] != occurrence[k] for k in ("occurrence_id", "sha256", "size_bytes"))):
            _error("worker_file_association_conflict")
        contents[occurrence["occurrence_id"]] = _read_bytes({k: descriptor[k] for k in ("path", "sha256", "size_bytes")})
    inputs, input_checks = [], []
    for occurrence in occurrences:
        if occurrence["direction"] == "input" and occurrence["role"] in {"sequences", "reference_sequences"}:
            parsed = parse_masking_input_fasta(contents[occurrence["occurrence_id"]], occurrence=occurrence,
                molecule="protein" if bundle["operation"]["program"] == "segmasker" else "dna")
            inputs.extend(parsed["records"])
            input_checks.extend(parsed["checks"])
            manifest["failures"].extend(parsed["failures"])
    statistics = None
    stats_occurrence = next((r for r in occurrences if r["role"] == "statistics"), None)
    if stats_occurrence is not None:
        statistics = parse_windowmasker_statistics(contents[stats_occurrence["occurrence_id"]], occurrence=stats_occurrence,
            format="ascii_statistics", reference_binding=bundle["statistics_binding"])
        manifest["failures"].extend(statistics["failures"])
        manifest["outputs"]["statistics"] = _write(directory, OUTPUT_FILES["statistics"], statistics)
    output = next((r for r in occurrences if r["role"] == "mask"), None)
    if output is not None:
        # A sealed failure retains bytes, but supplies no proof of a partial
        # output-to-input mapping. The core retains those blocks as unassigned.
        custody = {"producer_kind": "authenticated_native", "sequence_order": [r["record_key"] for r in inputs],
            "order_basis": "native_fasta_iteration", "output_complete": outcome["output_complete"],
            "native_returncode": outcome["returncode"], "record_bindings": []}
        parsed = parse_sequence_masking_output(contents[output["occurrence_id"]], format=bundle["operation"]["output_format"],
            occurrence=output, input_records=inputs, operation=bundle["operation"], custody=custody)
        sheet = populate_sequence_masking_sheet(operation=bundle["operation"], inputs=inputs,
            parsed_output=parsed, statistics=statistics, native_outcome=outcome)
        sheet["checks"] += [r for r in input_checks if r not in sheet["checks"]]
        sheet["failures"] = unique_failures([*sheet["failures"], *manifest["failures"]])
        sheet = core("SequenceMaskingSheet", sheet)
        manifest["outputs"]["sheet"] = _write(directory, OUTPUT_FILES["sheet"], sheet)
        manifest["failures"].extend(sheet["failures"])
        calculated = calculate_sequence_masking_components(sheet)
        manifest["outputs"]["calculations"] = _write(directory, OUTPUT_FILES["calculations"], calculated)
    elif bundle["operation"]["mode"] == "mask":
        manifest["failures"].append(failure("parse", "mask_output_unavailable"))
    elif statistics is None:
        manifest["failures"].append(failure("statistics", "statistics_output_unavailable"))


def _project_saved(plan, directory, manifest):
    from .sequence_masking_result_views import project_masking_result, validate_masking_result_selector
    operation, outcome = core("Operation", plan["operation"]), core("NativeOutcome", plan["native_outcome"])
    selector = validate_masking_result_selector(plan["selector"], operation=operation)
    if type(plan["files"]) is not dict or set(plan["files"]) != {"sheet", "calculations", "statistics"}:
        _error("worker_saved_files_invalid")
    saved = {role: _decode(_read_bytes(row)) if row is not None else None for role, row in plan["files"].items()}
    if selector["mode"] == "saved_recalculation":
        from .sequence_masking_calculations import calculate_sequence_masking_components
        if saved["sheet"] is None:
            _error("saved_masking_sheet_unavailable")
        saved["calculations"] = calculate_sequence_masking_components(saved["sheet"])
        manifest["outputs"]["recalculations"] = _write(directory, OUTPUT_FILES["recalculations"], saved["calculations"])
    selected = project_masking_result(source_ref=plan["source_ref"], operation=operation,
        native_outcome=outcome, occurrences=plan["occurrences"], selector=selector,
        failures=plan["failures"], saved_data=plan["saved_data"], **saved)
    manifest["outputs"]["projection"] = _write(directory, OUTPUT_FILES["projection"], selected)


def validate_worker_manifest(manifest, plan):
    manifest = finite_json_copy(manifest)
    if (type(manifest) is not dict or set(manifest) != {"version", "task", "plan_sha256", "completed", "outputs", "failures"}
            or manifest["version"] != MANIFEST_VERSION or manifest["task"] != plan["task"]
            or manifest["plan_sha256"] != native_blast_digest(plan) or type(manifest["completed"]) is not bool
            or type(manifest["outputs"]) is not dict):
        _error("worker_manifest_invalid")
    unique_failures(manifest["failures"])
    if not set(manifest["outputs"]) <= expected_outputs(plan) or manifest["completed"] and set(manifest["outputs"]) != expected_outputs(plan):
        _error("worker_manifest_output_population_conflict")
    for role, row in manifest["outputs"].items():
        if (type(row) is not dict or set(row) != {"filename", "sha256", "size_bytes"}
                or row["filename"] != OUTPUT_FILES[role] or type(row["sha256"]) is not str
                or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0):
            _error("worker_manifest_descriptor_invalid")
    return manifest


def run(value):
    """Execute exactly one bounded saved-data stage, with immutable replay."""
    plan = finite_json_copy(value)
    common = {"version", "task", "directory", "occurrences", "native_outcome", "files", "failures"}
    fields = {"parse_calculate": {"bundle", "bundle_artifact_ref", "original_plan", "capture"},
        "project_saved": {"source_ref", "operation", "selector", "saved_data"}}
    if (type(plan) is not dict or plan.get("version") != PLAN_VERSION or plan.get("task") not in fields
            or set(plan) != common | fields[plan["task"]]):
        _error("worker_plan_invalid")
    unique_failures(plan["failures"])
    directory = _directory(plan["directory"])
    if not directory.is_dir():
        _error("worker_directory_required")
    intent = {"plan_sha256": native_blast_digest(plan)}
    if (directory / "worker-intent.json").exists():
        if _read_record(directory, "worker-intent.json") != intent:
            _error("worker_identity_conflict")
        if not (directory / "worker-result.json").is_file():
            _error("worker_original_work_incomplete")
        saved = validate_worker_manifest(_read_record(directory, "worker-result.json"), plan)
        for row in saved["outputs"].values():
            _read_bytes({"path": str(directory / row["filename"]), **{k: row[k] for k in ("sha256", "size_bytes")}})
        return saved
    _immutable(directory / "worker-intent.json", intent)
    manifest = {"version": MANIFEST_VERSION, "task": plan["task"], "plan_sha256": native_blast_digest(plan),
        "completed": False, "outputs": {}, "failures": deepcopy(plan["failures"])}
    try:
        (_parse_calculate if plan["task"] == "parse_calculate" else _project_saved)(plan, directory, manifest)
        manifest["completed"] = set(manifest["outputs"]) == expected_outputs(plan)
    except (ValueError, OSError, KeyError, TypeError, IndexError) as error:
        print(canonical(diagnostic(error)), file=sys.stderr)
        manifest["failures"].append(failure("calculation", exception_code(error, PREFIX + "worker_failed")))
    manifest["failures"] = unique_failures(manifest["failures"])
    validate_worker_manifest(manifest, plan)
    _immutable(directory / "worker-result.json", manifest)
    return manifest


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        _error("one_worker_plan_required")
    result = run(_decode(Path(args[0]).read_bytes()))
    print(canonical(result))
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
