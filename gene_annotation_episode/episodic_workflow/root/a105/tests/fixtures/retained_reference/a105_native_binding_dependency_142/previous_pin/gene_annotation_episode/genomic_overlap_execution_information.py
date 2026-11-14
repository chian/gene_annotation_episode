"""Pure library information for selected genomic-overlap result operations.

The caller authenticates the original execution target and handoff receipt.
Descriptions validate supplied records; they do not observe work, acquire bytes,
grant source authority, calculate measurements or construct episode prompts.
"""
from __future__ import annotations

from copy import deepcopy

from .execution_contracts import digest, validate_target
from .genomic_overlap_contracts import genomic_overlap_schema, validate_genomic_overlap_record
from .genomic_overlap_result_worker import _selector
from .genomic_overlap_return_views import (
    SAVED_SOURCE, genomic_overlap_fact_sources, validate_genomic_overlap_fact_values,
)
from .native_genomic_overlap_contracts import POLICY, validate_genomic_overlap_requested_job


_HOST = "gene_annotation_episode.native_genomic_overlap_results.NativeGenomicOverlapResults.execute"
_CALCULATOR = "gene_annotation_episode.genomic_overlap_calculations.calculate_genomic_overlap_components"
_CALLED_OPERATIONS = ("practical.job.start", "practical.job.status", "practical.job.collect")


def genomic_overlap_result_selector_schema() -> dict:
    """Return the unchanged G1 selector with its own embedded reference scope."""
    schema = genomic_overlap_schema("Selector")
    definitions = schema.pop("$defs")
    wanted = set()

    def visit(value):
        if isinstance(value, dict):
            reference = value.get("$ref")
            if reference is not None:
                if not reference.startswith("#/$defs/"):
                    raise ValueError("genomic_overlap_selector_external_schema_reference")
                name = reference.removeprefix("#/$defs/")
                if name not in wanted:
                    wanted.add(name)
                    visit(definitions[name])
            for key, child in value.items():
                if key != "$ref":
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(schema)
    schema["$defs"] = {name: definitions[name] for name in sorted(wanted)}
    schema["$id"] = "urn:gene-annotation:genomic-overlap:result-selector:" + digest(schema)
    return schema


def describe_genomic_overlap_result(target, *, called_operation=None, selector=None) -> dict:
    """Describe authenticated local work, including retained-only recalculation.

    A missing called operation or selector stays null. This port cannot prove
    configuration/receipt authority or current scientific-byte availability.
    """
    target = validate_target(target)
    assignment = target["assignment"]
    if (target["resource_kind"] != "local" or assignment.get("resource_kind") != "local"
            or assignment.get("resource_id") != target["resource_id"]):
        raise ValueError("genomic_overlap_result_target_conflict")
    requested_job = validate_genomic_overlap_requested_job(assignment.get("requested_job"))
    if target["request_sha256"] != digest(requested_job):
        raise ValueError("genomic_overlap_result_target_conflict")
    if called_operation is not None and (
            type(called_operation) is not str or called_operation not in _CALLED_OPERATIONS):
        raise ValueError("execution_called_operation_invalid")
    job = requested_job["native_genomic_overlap"]
    request = job["request"]
    selected = None
    if selector is not None:
        selected = validate_genomic_overlap_record("Selector", selector)
        selected = _selector(selected, mode=selected["mode"], request=request)
        if (selected["mode"] == "native_result") != (selected["saved_sheet_file"] is None):
            raise ValueError("genomic_overlap_result_saved_sheet_mode_conflict")
        if selected["saved_sheet_file"] is not None:
            validate_genomic_overlap_fact_values(SAVED_SOURCE, [selected["saved_sheet_file"]])
    saved = selected is not None and selected["mode"] == "saved_sheet_recalculation"
    parameters = None if selected is None else deepcopy(selected["parameters"])
    sources = list(genomic_overlap_fact_sources())
    basis = ("received_saved_sheet_and_original_receipts" if saved else "original_selected_local_attempt")
    status = {
        "operation": "execution.results.status", "implementation": _HOST,
        "observation_basis": basis, "fresh_native_observation": not saved,
        "scientific_result_acquisition": False, "return_fact_sources": [],
        "completes_assignment": False,
    }
    collect = {
        "operation": "execution.results.collect", "implementation": _HOST,
        "preparation": "gene_annotation_episode.native_genomic_overlap_preparation.prepare_genomic_overlap_worker",
        "result_worker": "gene_annotation_episode.genomic_overlap_result_worker.run_genomic_overlap_result_worker",
        "worker_output_capture": "gene_annotation_episode.native_genomic_overlap_preparation.capture_genomic_overlap_worker_outputs",
        "calculators": [_CALCULATOR], "calculator_parameters": parameters,
        "projection_implementation": "gene_annotation_episode.genomic_overlap_result_views.project_genomic_overlap_result",
        "return_source_selection": "gene_annotation_episode.genomic_overlap_return_views.requested_genomic_overlap_sources",
        "return_fact_sources": deepcopy(sources), "complete_data_retained": True,
        "projection_scope": "selected_comparisons_measurement_fields_occurrence_keys_and_page",
        "return_source_scope": "receiving_form_requested_sources",
        "local_job_policy": deepcopy(POLICY), "swap_bytes": 0,
        "new_native_analysis": False, "scientific_annotation_score": False,
    }
    meanings = {
        "resource_id": target["resource_id"], "observation_basis": basis,
        "fresh_native_observation": not saved,
        "original_receipt_authority_is_current_byte_availability": False,
        "result_available": "observed_fixed_output_availability_does_not_establish_qualified_scientific_result",
        "native_success_capture_complete_delivery_complete_are_separate": True,
        "scientific_extents": ["complete", "partial", "unavailable"],
        "missing_partial_unavailable_are_measured_zero": False,
        "status_completes_assignment": False,
        "process_liveness_establishes_productive_work": False,
    }
    extractors = [status, collect]
    status_operations = ["execution.results.status"]
    if saved:
        collect.update(
            saved_input_validation="gene_annotation_episode.genomic_overlap_returns.GenomicOverlapReturns.authenticate_received_saved_sheet",
            worker_plan="gene_annotation_episode.native_genomic_overlap_preparation.build_saved_genomic_overlap_worker_plan",
            calculation_basis="authenticated_saved_sheet_and_explicit_parameters",
            calculation_operands={"sheet": deepcopy(selected["saved_sheet_file"]),
                                  "parameters": deepcopy(parameters)},
            original_sheet_and_completed_observations_preserved=True,
            native_input_acquisition=False,
        )
        meanings["result_available"] = "received_sheet_authority_and_current_retained_byte_availability_are_separate"
    else:
        collect.update(
            native_format="bedtools_intersect_wo_bed4_v1",
            original_native_execution={
                "implementation": "gene_annotation_episode.native_genomic_overlap_driver.run_genomic_overlap_driver",
                "program": "bedtools", "executable": job["software"]["bedtools_executable"],
                "declared_version": job["software"]["bedtools_version"],
                "operation": "intersect", "options": ["-wo", "-sorted"],
            },
            capture="gene_annotation_episode.native_genomic_overlap_capture.capture_genomic_overlap_native_files",
            worker_plan="gene_annotation_episode.native_genomic_overlap_preparation.build_native_genomic_overlap_worker_plan",
            input_parser="gene_annotation_episode.genomic_overlap_inputs.parse_region_set",
            parser="gene_annotation_episode.genomic_overlap_inputs.parse_bedtools_intersect_wo",
            metadata_extractor="gene_annotation_episode.genomic_overlap_inputs.extract_overlap_reference_metadata",
            sheet_population="gene_annotation_episode.genomic_overlap_inputs.build_genomic_overlap_sheet",
            calculation_basis="qualified_original_native_results_and_explicit_parameters",
        )
        meanings.update(logs="selected_original_stdout_stderr_windows",
            native_batch_states=["complete", "partial", "failed"],
            native_pair_dispositions=["native_succeeded", "native_failed", "analytic_empty",
                                      "invalid_input", "input_unavailable", "native_unavailable"])
        status_operations.insert(0, "progress.observe")
        extractors.insert(0, {
            "operation": "progress.observe",
            "implementation": "gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.observe_execution",
            "return_fields": ["state", "returncode", "failure_code", "result_available", "measurements", "outputs", "logs"],
            "return_fact_sources": ["monitoring_progress_refs", "monitoring_execution_state", "monitoring_result_available"],
        })
    return {
        "resource_kind": target["resource_kind"], "service_or_program": job["program"],
        "operation": request["operation"], "mode": request["mode"],
        "output_format": "genomic_region_overlap_components_v1" if saved else "genomic_overlap_native_batch_v1",
        "called_operation": called_operation, "selected_outputs": deepcopy(job["outputs"]),
        "result_selector_schema": genomic_overlap_result_selector_schema(), "result_selection": selected,
        "status_operations": status_operations, "acquisition_operations": ["execution.results.collect"],
        "status_meanings": meanings, "extractors": extractors, "return_fact_sources": sources,
    }


__all__ = ["describe_genomic_overlap_result", "genomic_overlap_result_selector_schema"]
