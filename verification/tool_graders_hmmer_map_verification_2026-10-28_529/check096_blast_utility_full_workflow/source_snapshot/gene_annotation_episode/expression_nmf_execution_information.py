"""Recorded NMF operation and deterministic result capabilities, without I/O.

This supplies tool-library information under the existing resource task. It is
not an episode prompt, an observation, a numerical calculation or a grant of
access to a saved sheet.
"""
from copy import deepcopy

from .execution_contracts import digest, validate_target
from .expression_nmf_result_contracts import (
    EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA, validate_expression_nmf_result_selector,
)
from .expression_nmf_return_views import FACT_SOURCES
from .native_expression_nmf_contracts import (
    POLICY, expression_nmf_output_files, validate_expression_nmf_requested_job,
)


def describe_expression_nmf_result(target, *, called_operation=None, selector=None):
    target = validate_target(target)
    assignment = target['assignment']
    if (target['resource_kind'] != 'local' or assignment.get('resource_kind') != 'local'
            or assignment.get('resource_id') != target['resource_id']):
        raise ValueError('expression_nmf_result_target_conflict')
    requested = validate_expression_nmf_requested_job(assignment.get('requested_job'))
    if target['request_sha256'] != digest(requested):
        raise ValueError('expression_nmf_result_target_conflict')
    if called_operation is not None and called_operation not in (
            'practical.job.start', 'practical.job.status', 'practical.job.collect'):
        raise ValueError('execution_called_operation_invalid')
    job = requested['native_expression_nmf']
    selected = (None if selector is None else
        validate_expression_nmf_result_selector(selector, job=job))
    saved = selected is not None and selected['mode'] == 'saved_sheet_recalculation'
    basis = 'explicitly_received_saved_sheet' if saved else 'original_selected_local_attempt'
    implementation = 'gene_annotation_episode.native_expression_nmf_results.NativeExpressionNMFResults.execute'
    collect = {
        'operation': 'execution.results.collect', 'implementation': implementation,
        'preparation': 'gene_annotation_episode.native_expression_nmf_preparation.prepare_expression_nmf_result_worker',
        'result_worker': 'gene_annotation_episode.expression_nmf_result_worker.execute_expression_nmf_worker',
        'calculators': ['gene_annotation_episode.expression_nmf_calculations.calculate_nmf_sheet'],
        'projection_implementation': 'gene_annotation_episode.expression_nmf_result_views.project_nmf_result',
        'return_source_selection': 'gene_annotation_episode.expression_nmf_return_views.requested_expression_nmf_sources',
        'return_fact_sources': list(FACT_SOURCES), 'complete_data_retained': True,
        'projection_scope': 'requested_view_occurrence_positions_fields_filter_and_row_window',
        'local_job_policy': deepcopy(POLICY), 'swap_bytes': 0,
        'new_native_analysis': False, 'scientific_annotation_score': False,
        'calculation_basis': basis,
    }
    status = {'operation': 'execution.results.status', 'implementation': implementation,
        'observation_basis': basis, 'fresh_native_observation': not saved,
        'scientific_result_acquisition': False, 'completes_assignment': False}
    if saved:
        collect.update(
            saved_input_validation='gene_annotation_episode.expression_nmf_returns.ExpressionNMFReturns.authenticate_received_saved_sheet',
            worker_plan='gene_annotation_episode.native_expression_nmf_preparation.build_saved_expression_nmf_worker_plan',
            original_sheet_and_completed_observations_preserved=True, native_input_acquisition=False)
    else:
        collect.update(
            capture='gene_annotation_episode.native_expression_nmf_capture.capture_expression_nmf_native_files',
            worker_plan='gene_annotation_episode.native_expression_nmf_preparation.build_native_expression_nmf_worker_plan',
            native_format='expression_nmf_native_manifest_v1',
            parser='gene_annotation_episode.expression_nmf_sheet.load_expression_nmf_artifacts',
            sheet_population='gene_annotation_episode.expression_nmf_sheet.populate_nmf_sheet')
    extractors = [status, collect]
    if not saved:
        extractors.insert(0, {'operation': 'progress.observe',
            'implementation': 'gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.observe_execution',
            'return_fields': ['state', 'returncode', 'failure_code', 'result_available', 'measurements', 'outputs', 'logs']})
    return {
        'resource_kind': 'local', 'service_or_program': job['operation'],
        'operation': job['operation'], 'mode': job['mode'], 'called_operation': called_operation,
        'output_format': 'expression_nmf_sheet_v1' if saved else 'expression_nmf_native_manifest_v1',
        'fit_parameters': deepcopy(job['parameters']),
        'selected_outputs': [] if saved else expression_nmf_output_files(job),
        'result_selector_schema': deepcopy(EXPRESSION_NMF_RESULT_SELECTOR_SCHEMA),
        'result_selection': selected,
        'status_operations': ['execution.results.status'] if saved else ['progress.observe', 'execution.results.status'],
        'acquisition_operations': ['execution.results.collect'], 'extractors': extractors,
        'return_fact_sources': list(FACT_SOURCES), 'status_meanings': {
            'observation_basis': basis, 'fresh_native_observation': not saved,
            'native_success_capture_complete_delivery_complete_are_separate': True,
            'process_liveness_establishes_productive_work': False,
            'result_available': ('received_sheet_authority_and_current_bytes_are_separate' if saved else
                'observed_manifest_presence_does_not_establish_qualified_scientific_results'),
            'native_warnings': 'recorded_fit_qualifications_with_available_factors_preserved',
            'logs': 'selected_original_stdout_stderr_windows' if not saved else 'not_required',
        },
    }
