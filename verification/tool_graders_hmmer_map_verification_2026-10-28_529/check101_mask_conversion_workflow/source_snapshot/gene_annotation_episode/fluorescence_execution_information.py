"""Recorded fluorescence capabilities and selected operands, without I/O.

This information describes installed execution/result ports. It is neither a
model task template nor a scientific calculation, observation, or artifact grant.
"""
from copy import deepcopy

from .execution_contracts import digest, validate_target
from .fluorescence_result_contracts import (
    FLUORESCENCE_RESULT_SELECTOR_SCHEMA, validate_fluorescence_selector,
)
from .fluorescence_return_views import FACT_SOURCES
from .native_fluorescence_contracts import (
    POLICY, fluorescence_output_files, validate_fluorescence_requested_job,
)


_PARSERS = {
    'csv': 'gene_annotation_episode.fluorescence_event_readers.parse_fluorescence_csv',
    'table_snapshot': 'gene_annotation_episode.fluorescence_event_readers.parse_fluorescence_table_snapshot',
    'fcs_encoded': 'gene_annotation_episode.fluorescence_fcs_reader.parse_fluorescence_fcs',
}


def describe_fluorescence_result(target, *, called_operation=None, selector=None):
    """Describe the original operation and the explicitly selected calculation."""
    target = validate_target(target)
    assignment = target['assignment']
    if (target['resource_kind'] != 'local' or assignment.get('resource_kind') != 'local'
            or assignment.get('resource_id') != target['resource_id']):
        raise ValueError('fluorescence_result_target_conflict')
    requested = validate_fluorescence_requested_job(assignment.get('requested_job'))
    if target['request_sha256'] != digest(requested):
        raise ValueError('fluorescence_result_target_conflict')
    if called_operation is not None and called_operation not in (
            'practical.job.start', 'practical.job.status', 'practical.job.collect'):
        raise ValueError('execution_called_operation_invalid')
    job = requested['native_fluorescence']
    selected = None if selector is None else validate_fluorescence_selector(selector, job=job)
    saved = selected is not None and selected['mode'] == 'saved_sheet_recalculation'
    basis = 'explicitly_received_saved_sheet' if saved else 'original_selected_local_attempt'
    parameters = selected['parameters'] if saved else job['parameters']
    implementation = 'gene_annotation_episode.native_fluorescence_results.NativeFluorescenceResults.execute'
    collect = {
        'operation': 'execution.results.collect', 'implementation': implementation,
        'preparation': 'gene_annotation_episode.native_fluorescence_preparation.prepare_fluorescence_result_worker',
        'result_worker': 'gene_annotation_episode.fluorescence_result_worker.execute_fluorescence_worker',
        'calculators': ['gene_annotation_episode.fluorescence_event_calculations.calculate_fluorescence_sheet'],
        'calculator_parameters': deepcopy(parameters),
        'projection_implementation': 'gene_annotation_episode.fluorescence_result_views.project_fluorescence_result',
        'context_projection_implementation': 'gene_annotation_episode.fluorescence_context_views.project_fluorescence_context',
        'return_source_selection': 'gene_annotation_episode.fluorescence_return_views.requested_fluorescence_sources',
        'return_fact_sources': list(FACT_SOURCES),
        'retention_scope': 'verified_available_artifacts_with_explicit_partial_or_missing_roles',
        'projection_scope': 'requested_cells_and_row_window_with_selected_context_dependencies',
        'local_job_policy': deepcopy(POLICY), 'swap_bytes': 0,
        'new_native_analysis': False, 'laboratory_operation': False,
        'scientific_annotation_score': False, 'calculation_basis': basis,
    }
    status = {'operation': 'execution.results.status', 'implementation': implementation,
        'observation_basis': basis, 'fresh_native_observation': not saved,
        'scientific_result_acquisition': False, 'completes_assignment': False}
    if saved:
        collect.update(
            saved_input_validation='gene_annotation_episode.fluorescence_returns.FluorescenceReturns.authenticate_received_saved_sheet',
            worker_plan='gene_annotation_episode.native_fluorescence_preparation.build_saved_fluorescence_worker_plan',
            original_sheet_and_completed_observations_preserved=True,
            original_producer_completion_required=False, native_input_acquisition=False)
    else:
        collect.update(
            capture='gene_annotation_episode.native_fluorescence_capture.capture_fluorescence_native_files',
            worker_plan='gene_annotation_episode.native_fluorescence_preparation.build_native_fluorescence_worker_plan',
            native_format='fluorescence_native_manifest_v1',
            parsed_batch_format='fluorescence_parsed_batch_v1',
            sheet_population='gene_annotation_episode.fluorescence_event_sheet.populate_fluorescence_sheet',
            original_input_parsers=[{'parser': parser, 'implementation': _PARSERS[parser]}
                for parser in dict.fromkeys(row['parser'] for row in job['inputs'])],
            native_input_acquisition=True)
    extractors = [status, collect]
    if not saved:
        extractors.insert(0, {'operation': 'progress.observe',
            'implementation': 'gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.observe_execution',
            'file_observation': 'gene_annotation_episode.native_fluorescence_observations.fluorescence_observed_files',
            'output_reader': 'gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.read_output',
            'output_window_reader': 'gene_annotation_episode.native_fluorescence_observations.read_fluorescence_output',
            'return_fields': ['state', 'returncode', 'failure_code', 'result_available', 'measurements', 'outputs', 'logs']})
    return {
        'resource_kind': 'local', 'service_or_program': job['operation'],
        'operation': job['operation'], 'mode': job['mode'], 'called_operation': called_operation,
        'output_format': 'fluorescence_event_population_sheet_v1' if saved else 'fluorescence_native_manifest_v1',
        'input_selection': [] if saved else [{
            'parser': row['parser'], 'source_key': row['source']['key'],
            'dataset_position': row['source']['dataset_position'],
            'sample_key': row['sample']['key'], 'domain_key': row['domain']['key'],
            'channel_bindings': [{key: channel[key] for key in ('key', 'ordinal', 'measurement_origin')}
                for channel in row['channels']], 'format_spec': deepcopy(row['format_spec']),
        } for row in job['inputs']],
        'calculation_parameters': deepcopy(parameters),
        'selected_outputs': [] if saved else fluorescence_output_files(job),
        'result_selector_schema': deepcopy(FLUORESCENCE_RESULT_SELECTOR_SCHEMA),
        'result_selection': selected,
        'status_operations': ['execution.results.status'] if saved else ['progress.observe', 'execution.results.status'],
        'acquisition_operations': ['execution.results.collect'], 'extractors': extractors,
        'return_fact_sources': list(FACT_SOURCES), 'status_meanings': {
            'observation_basis': basis, 'fresh_native_observation': not saved,
            'native_success_capture_complete_delivery_complete_are_separate': True,
            'process_liveness_establishes_productive_work': False,
            'result_available': ('received_sheet_authority_and_current_bytes_are_separate' if saved else
                'observed_manifest_presence_does_not_establish_qualified_scientific_results'),
            'partial_data': 'available_cells_preserved_with_original_missing_input_and_population_qualifications',
            'context': 'requested_definition_fields_for_the_selected_numerical_page_only',
            'logs': 'not_required' if saved else 'selected_original_stdout_stderr_windows',
        },
    }


__all__ = ['describe_fluorescence_result']
