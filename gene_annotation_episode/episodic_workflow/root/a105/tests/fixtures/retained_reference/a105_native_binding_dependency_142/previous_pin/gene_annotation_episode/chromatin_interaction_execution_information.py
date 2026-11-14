"""Pure information for chromatin result selection and its actual operations.

These functions validate supplied records. Receipt authority, byte acquisition,
scientific calculation and the episode's TASK/STEERING construction are separate.
"""
from __future__ import annotations

from copy import deepcopy

from .chromatin_interaction_contracts import chromatin_record_schema, validate_chromatin_record
from .chromatin_interaction_return_views import (
    FACT_SOURCES, SAVED_SOURCE, validate_chromatin_fact_values,
)
from .execution_contracts import digest, validate_target
from .native_chromatin_interaction_contracts import POLICY, validate_chromatin_requested_job


def chromatin_result_selector_schema():
    return chromatin_record_schema("ResultSelector")


def validate_chromatin_result_selector(selector, *, request):
    request = validate_chromatin_record("ChromatinRequest", request)
    selector = validate_chromatin_record("ResultSelector", selector)
    if not set(selector["population_keys"]) <= {row["population_key"] for row in request["populations"]}:
        raise ValueError("chromatin_result_population_conflict")
    parameters = selector["parameters"]
    for field, mode in (("contact", "cis_anchor_contact_enrichment"),
            ("insulation", "cross_window_insulation_heuristic")):
        if (parameters[field] is not None) != (mode in request["analysis_modes"]):
            raise ValueError("chromatin_result_analysis_mode_conflict")
    kind = selector["projection"]["kind"]
    if (kind in {"contact_pairs", "distance_expectations"} and parameters["contact"] is None
            or kind in {"insulation_windows", "domains"} and parameters["insulation"] is None):
        raise ValueError("chromatin_result_projection_mode_conflict")
    if selector["mode"] == "saved_sheet_recalculation":
        validate_chromatin_fact_values(SAVED_SOURCE, [selector["saved_sheet_bundle"]])
    return selector


def describe_chromatin_result(target, *, selector):
    target = validate_target(target)
    assignment = target["assignment"]
    if (target["resource_kind"] != "local" or assignment.get("resource_kind") != "local"
            or assignment.get("resource_id") != target["resource_id"]):
        raise ValueError("chromatin_result_target_conflict")
    job = validate_chromatin_requested_job(assignment.get("requested_job"))
    if target["request_sha256"] != digest(job):
        raise ValueError("chromatin_result_target_conflict")
    request = job["native_chromatin_interactions"]["request"]
    selected = validate_chromatin_result_selector(selector, request=request)
    saved = selected["mode"] == "saved_sheet_recalculation"
    host = "gene_annotation_episode.native_chromatin_interaction_results.NativeChromatinInteractionResults.execute"
    collect = {
        "operation": "execution.results.collect", "implementation": host,
        "preparation": "gene_annotation_episode.native_chromatin_interaction_preparation.prepare_chromatin_result_worker",
        "result_worker": "gene_annotation_episode.chromatin_interaction_result_worker.run_chromatin_result_worker",
        "calculator": "gene_annotation_episode.chromatin_interaction_calculations.calculate_chromatin_components",
        "projection": "gene_annotation_episode.chromatin_interaction_result_views.project_chromatin_result",
        "parameters": deepcopy(selected["parameters"]),
        "return_fact_sources": list(FACT_SOURCES),
        "return_source_scope": "receiving_form_requested_sources",
        "new_native_analysis": False,
        "local_job_policy": deepcopy(POLICY), "swap_bytes": 0,
    }
    if saved:
        collect.update(
            saved_input_validation="gene_annotation_episode.chromatin_interaction_returns.ChromatinInteractionReturns.authenticate_received_saved_bundle",
            worker_plan="gene_annotation_episode.native_chromatin_interaction_preparation.build_saved_chromatin_worker_plan",
            table_parser="gene_annotation_episode.chromatin_interaction_tables.read_chromatin_sheet_tables",
            native_input_acquisition=False,
        )
    else:
        collect.update(
            capture="gene_annotation_episode.native_chromatin_interaction_capture.capture_chromatin_native_files",
            worker_plan="gene_annotation_episode.native_chromatin_interaction_preparation.build_native_chromatin_worker_plan",
            table_parser="gene_annotation_episode.chromatin_interaction_tables.open_chromatin_contact_tables",
            sheet_population="gene_annotation_episode.chromatin_interaction_inputs.build_chromatin_sheet",
            native_input_acquisition=False,
        )
    return {
        "resource_kind": "local", "service_or_program": request["operation"],
        "operation": request["operation"], "analysis_modes": deepcopy(request["analysis_modes"]),
        "input_format": request["contact"]["format"],
        "output_format": "chromatin_interaction_components_v1" if saved else "chromatin_interaction_native_bundle_v1",
        "result_selection": selected,
        "observation_basis": "received_saved_sheet_and_original_receipts" if saved else "original_selected_local_attempt",
        "status_operations": ["execution.results.status"] if saved else ["progress.observe", "execution.results.status"],
        "acquisition_operations": ["execution.results.collect"],
        "extractors": [
            {"operation": "execution.results.status", "implementation": host,
             "fresh_native_observation": not saved, "scientific_result_acquisition": False,
             "return_fact_sources": [], "completes_assignment": False},
            collect,
        ],
        "return_fact_sources": list(FACT_SOURCES),
    }


__all__ = ["chromatin_result_selector_schema", "validate_chromatin_result_selector",
           "describe_chromatin_result"]
