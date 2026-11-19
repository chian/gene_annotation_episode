"""Bounded deterministic stages over retained masking bytes and saved sheets.

The host owns capture and publication. These stages neither submit native work
nor use a Store or model. Replaying a completed stage reads its original receipt.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import sys

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.native_blast_masking_capture_contracts import validate_native_blast_masking_capture
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.native_blast_masking_contracts import finite_json_copy, native_blast_digest, masking_occurrence_id, validate_original_bundle
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_acquisition import _decode, _directory, _read_record
from gene_annotation_episode.episodic_workflow.episode_support.jobs.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_result_worker import _read_bytes, _write
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_homology_evidence.practical_execution_state import _immutable
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_masking.sequence_homology_evidence.sequence_masking_contracts import sequence_masking_molecule, validate_sequence_masking_record as core
from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import failure, unique_failures
from gene_annotation_episode.episodic_workflow.episode_support.jobs.sequence_masking.native_blast_masking_worker_context import MANIFEST_VERSION, OUTPUT_FILES, PREFIX, _error, diagnostic, exception_code, expected_outputs, qualified_masking_context, validate_worker_manifest


PLAN_VERSION = PREFIX + "result_worker_plan_v1"














def _parse_calculate(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_inputs import parse_masking_input_fasta, parse_sequence_masking_output, populate_sequence_masking_sheet
    from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_masking.sequence_homology_evidence.sequence_masking_calculations import calculate_sequence_masking_components
    from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_masking.sequence_homology_evidence.windowmasker_statistics import parse_windowmasker_statistics

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
                molecule=sequence_masking_molecule(bundle["operation"]))
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
        if bundle["operation"]["mode"] == "convert_mask":
            from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.blast_maskinfo_inputs import parse_blast_maskinfo, populate_mask_conversion
            parsed = parse_blast_maskinfo(contents[output["occurrence_id"]], occurrence=output,
                native_format=bundle["operation"]["output_format"])
            custody["order_basis"] = "native_masked_input_iteration"
            if bundle["operation"]["output_format"] == "interval":
                # Bare intervals have no native record separators. Only the
                # original single-input invocation proves their association.
                custody["order_basis"] = "native_single_input" if len(inputs) == 1 else "unknown"
                if len(inputs) == 1:
                    custody["record_bindings"] = [{"output_record_ordinal": row["native_record_ordinal"],
                        "input_record_key": inputs[0]["record_key"], "basis": "native_single_input"}
                        for row in parsed["records"]]
            sheet = populate_mask_conversion(operation=bundle["operation"], input_records=inputs,
                parsed_maskinfo=parsed, custody=custody, native_outcome=outcome)
        else:
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
    elif bundle["operation"]["mode"] in {"mask", "convert_mask"}:
        manifest["failures"].append(failure("parse", "mask_output_unavailable"))
    elif statistics is None:
        manifest["failures"].append(failure("statistics", "statistics_output_unavailable"))


def _project_saved(plan, directory, manifest):
    from gene_annotation_episode.episodic_workflow.episode_support.readers.sequence_masking.sequence_homology_evidence.sequence_masking_result_views import project_masking_result, validate_masking_result_selector
    operation, outcome = core("Operation", plan["operation"]), core("NativeOutcome", plan["native_outcome"])
    selector = validate_masking_result_selector(plan["selector"], operation=operation)
    if type(plan["files"]) is not dict or set(plan["files"]) != {"sheet", "calculations", "statistics"}:
        _error("worker_saved_files_invalid")
    saved = {role: _decode(_read_bytes(row)) if row is not None else None for role, row in plan["files"].items()}
    if selector["mode"] == "saved_recalculation":
        from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_masking.sequence_homology_evidence.sequence_masking_calculations import calculate_sequence_masking_components
        if saved["sheet"] is None:
            _error("saved_masking_sheet_unavailable")
        saved["calculations"] = calculate_sequence_masking_components(saved["sheet"])
        manifest["outputs"]["recalculations"] = _write(directory, OUTPUT_FILES["recalculations"], saved["calculations"])
    selected = project_masking_result(source_ref=plan["source_ref"], operation=operation,
        native_outcome=outcome, occurrences=plan["occurrences"], selector=selector,
        failures=plan["failures"], saved_data=plan["saved_data"], **saved)
    manifest["outputs"]["projection"] = _write(directory, OUTPUT_FILES["projection"], selected)




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
