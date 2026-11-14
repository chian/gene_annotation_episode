"""Pure information about selected protein execution and result functions.

The caller authenticates the original target and called operation. This module
describes those implementations; it neither observes work nor reads its results.
"""
from copy import deepcopy

from .native_protein_structure_acquisition import is_native_protein_structure_target
from .native_protein_structure_contracts import (
    NATIVE_FORMATS, validate_protein_structure_request,
)
from .protein_structure_result_views import protein_structure_fact_sources
from .protein_structure_selection import (
    protein_structure_result_selector_schema,
    validate_protein_structure_result_selector,
)


_HOST = "gene_annotation_episode.native_protein_structure_results.NativeProteinStructureResults.execute"
_COMPONENT_VALIDATOR = (
    "gene_annotation_episode.protein_structure_calculations.validate_recorded_protein_structure_components"
)


def describe_protein_structure_result(target, *, called_operation, selector=None):
    """Describe an authenticated target without acquiring scientific data."""
    if not is_native_protein_structure_target(target) or target["resource_kind"] != "local":
        raise ValueError("original_commission_mismatch")
    if type(called_operation) is not str or not called_operation or "\0" in called_operation:
        raise ValueError("execution_called_operation_unavailable")
    job = target["assignment"]["requested_job"]["native_protein_structure"]
    request = validate_protein_structure_request(job["request"])
    selected = None if selector is None else validate_protein_structure_result_selector(
        selector, request=request)
    saved = selected is not None and selected["acquisition"] == "retained_sheet_only"
    comparison = request["operation"] == "compare"
    original_parameters = deepcopy(request["parameters"]) if comparison else None
    parameters = deepcopy(selected["parameters"]) if saved else original_parameters
    observation_basis = ("received_saved_input_pair_and_original_receipt" if saved
        else "original_selected_local_attempt")
    status = {"operation": "execution.results.status", "implementation": _HOST,
        "observation_basis": observation_basis, "fresh_native_observation": not saved,
        "scientific_result_acquisition": False, "return_fact_sources": [],
        "completes_assignment": False}
    collect = {"operation": "execution.results.collect", "implementation": _HOST,
        "result_worker": "gene_annotation_episode.protein_structure_result_worker.run_protein_structure_result_worker",
        "preparation": "gene_annotation_episode.native_protein_structure_preparation.prepare_protein_structure_worker",
        "projection_implementation": "gene_annotation_episode.protein_structure_result_views.project_protein_structure_results",
        "projection_publication": "gene_annotation_episode.protein_structure_projection_publication.publish_protein_structure_projection",
        "return_fact_sources": list(protein_structure_fact_sources()),
        "result_paths": ["result.body.native_success", "result.body.capture_complete",
            "result.body.issues", "result.publication.facts", "result.publication.delivery_complete"],
        "calculators": [], "scientific_annotation_score": False}
    if saved:
        collect.update(
            saved_input_validation="gene_annotation_episode.protein_structure_operands.validate_protein_structure_selected_inputs",
            calculation_basis="authenticated_saved_sheet_and_original_baseline",
            calculators=["gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components"],
            calculator_parameters=parameters,
            component_validation=_COMPONENT_VALIDATOR,
            original_sheet_and_baseline_preserved=True,
            new_producer_observation=False,
        )
    else:
        collect.update(
            native_format=NATIVE_FORMATS[request["operation"]],
            capture="gene_annotation_episode.native_protein_structure_acquisition.capture_local_protein_structure_bundle",
            native_validation="gene_annotation_episode.native_protein_structure_contracts.validate_native_protein_structure_result",
            calculation_basis=("original_recorded_native_baseline" if comparison else
                "original_native_inventory" if request["operation"] == "inspect" else "original_native_sequence_map"),
        )
        if comparison:
            collect.update(
                sheet_population="gene_annotation_episode.protein_structure_sheet.parse_native_protein_comparison",
                component_validation=_COMPONENT_VALIDATOR,
                original_calculation_parameters=original_parameters,
                original_sheet_and_baseline_preserved=True,
            )
    value = {"resource_kind": "local", "service_or_program": job["program"],
        "operation": request["operation"],
        "mode": parameters["mode"] if comparison else None,
        "output_format": "native_protein_structure_bundle_v1",
        "called_operation": called_operation, "selected_outputs": deepcopy(job["outputs"]),
        "result_selector_schema": protein_structure_result_selector_schema(),
        "status_operations": ["execution.results.status"],
        "acquisition_operations": ["execution.results.collect"],
        "extractors": [status, collect],
        "status_meanings": {"observation_basis": observation_basis,
            "fresh_native_observation": not saved,
            "result_available": "observed_sealed_bundle_availability_does_not_establish_valid_scientific_result",
            "native_success_capture_complete_delivery_complete_are_separate": True,
            "status_completes_assignment": False,
            "process_liveness_establishes_productive_work": False}}
    if saved:
        value["output_format"] = "protein_structure_components_v1"
        value["status_meanings"]["result_available"] = "validated_received_sheet_and_original_baseline_required"
    else:
        value["status_operations"].insert(0, "progress.observe")
        value["status_meanings"]["logs"] = "selected_original_stdout_stderr_windows"
        value["extractors"].insert(0, {"operation": "progress.observe",
            "implementation": "gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.observe_execution",
            "return_fields": ["state", "returncode", "failure_code", "result_available", "measurements", "outputs", "logs"],
            "return_fact_sources": ["monitoring_progress_refs", "monitoring_execution_state", "monitoring_result_available"]})
    if selected is not None:
        value["result_selection"] = selected
    return value
