"""Actual barcode artifact and deterministic result information, without I/O.

The existing resource task consumes this library information. It is neither an
episode prompt nor a scientific judgment, observation, calculation or data grant.
"""
from copy import deepcopy

from .execution_contracts import digest, validate_target
from .barcode_result_contracts import (
    BARCODE_RESULT_SELECTOR_SCHEMA, validate_barcode_result_selector,
)
from .barcode_return_views import FACT_SOURCES
from .native_barcode_contracts import (
    POLICY, barcode_output_files, validate_barcode_requested_job,
)


RESULT_INSTRUCTIONS = (
    'Acquire the selected original closed barcode bundle through its retained handoff, or calculate '
    'the exact explicitly received barcode_sheet_v1 selected by the parent. Native collection '
    'authenticates the original request, attempt, writer closure and complete role-specific bytes. '
    'The barcode_bundle_v1 manifest identifies the original reads, original request JSON, optional '
    'target-map JSON, read-extraction TSV, all prefilter count TSV, population JSON, condensed '
    'distance TSV, average-linkage TSV and categorical cluster TSV. Formats and fields are explicit; '
    'a filename or live process does not establish a valid measurement. The deterministic parser '
    'and metadata join preserve sample identity, repeated read occurrences, exact literal strings, '
    'supplied target identities and each stage outcome. Counts measure read occurrences. Separate '
    'calculators retain counts, fractions with their exact populations and denominators, direct '
    'sequence discrepancy counts, saved-tree cuts and supplied target aggregates. Cluster labels '
    'are categories, not ancestry or annotation confidence. Available zero, zero denominator, '
    'not applicable, missing, invalid and partial populations remain distinct. A later clustering '
    'or mapping failure does not erase independently validated counts. Return only the requested '
    'summary, barcode, distance, cluster, target or failure view and explicit numerical fields. '
    'Complete native data and the full numerical sheet remain retained separately. Saved-sheet '
    'calculation uses only that received sheet, changed explicit parameters and projection; it '
    'does not repeat extraction, generate new distances, rerun linkage or reacquire references. '
    'A threshold selecting a population without saved distances reports missing components '
    'while preserving available counts. A measurement-only return grants no sheet or native-file '
    'access. Selected status observes the original attempt once, or reports saved-sheet authority; '
    'it neither acquires scientific data nor completes the result assignment. Collection uses '
    'the existing bounded finite worker at 20 GiB RAM, 4 GiB scratch, zero swap and no wall limit. '
    'The responsible episode chooses any later action from actual outcomes.'
)


def describe_barcode_result(target, *, called_operation=None, selector=None):
    target = validate_target(target)
    assignment = target['assignment']
    if (target['resource_kind'] != 'local' or assignment.get('resource_kind') != 'local'
            or assignment.get('resource_id') != target['resource_id']):
        raise ValueError('barcode_result_target_conflict')
    requested = validate_barcode_requested_job(assignment.get('requested_job'))
    if target['request_sha256'] != digest(requested):
        raise ValueError('barcode_result_target_conflict')
    if called_operation is not None and called_operation not in (
            'practical.job.start', 'practical.job.status', 'practical.job.collect'):
        raise ValueError('execution_called_operation_invalid')
    job = requested['native_barcode']
    selected = None if selector is None else validate_barcode_result_selector(selector, job=job)
    saved = selected is not None and selected['mode'] == 'saved_sheet_recalculation'
    basis = 'explicitly_received_saved_sheet' if saved else 'original_selected_local_attempt'
    implementation = 'gene_annotation_episode.native_barcode_results.NativeBarcodeResults.execute'
    collect = {
        'operation': 'execution.results.collect', 'implementation': implementation,
        'preparation': 'gene_annotation_episode.native_barcode_preparation.prepare_barcode_result_worker',
        'result_worker': 'gene_annotation_episode.barcode_result_worker.execute_barcode_worker',
        'calculators': ['gene_annotation_episode.barcode_calculators.calculate_barcode_components'],
        'projection_implementation': 'gene_annotation_episode.barcode_result_views.project_barcode_result',
        'return_source_selection': 'gene_annotation_episode.barcode_return_views.requested_barcode_sources',
        'return_fact_sources': list(FACT_SOURCES), 'complete_data_retained': True,
        'projection_scope': 'requested_view_fields_exact_keys_or_declared_top_k',
        'local_job_policy': deepcopy(POLICY), 'swap_bytes': 0,
        'new_native_analysis': False, 'scientific_annotation_score': False,
        'calculation_basis': basis,
    }
    status = {'operation': 'execution.results.status', 'implementation': implementation,
        'observation_basis': basis, 'fresh_native_observation': not saved,
        'scientific_result_acquisition': False, 'completes_assignment': False}
    if saved:
        collect.update(
            saved_input_validation='gene_annotation_episode.barcode_returns.BarcodeReturns.authenticate_received_saved_sheet',
            worker_plan='gene_annotation_episode.native_barcode_preparation.build_saved_barcode_worker_plan',
            original_sheet_and_completed_observations_preserved=True, native_input_acquisition=False)
    else:
        collect.update(
            capture='gene_annotation_episode.native_barcode_capture.capture_barcode_native_files',
            worker_plan='gene_annotation_episode.native_barcode_preparation.build_native_barcode_worker_plan',
            native_format='barcode_bundle_v1',
            parser='gene_annotation_episode.barcode_formats.parse_barcode_native_bundle',
            sheet_population='gene_annotation_episode.barcode_metadata.join_barcode_metadata')
    extractors = [status, collect]
    if not saved:
        extractors.insert(0, {'operation': 'progress.observe',
            'implementation': 'gene_annotation_episode.practical_execution_operations.LocalPracticalOperations.observe_execution',
            'return_fields': ['state', 'returncode', 'failure_code', 'result_available', 'measurements', 'outputs', 'logs']})
    return {
        'resource_kind': 'local', 'service_or_program': job['operation'],
        'operation': job['operation'], 'called_operation': called_operation,
        'instructions': RESULT_INSTRUCTIONS,
        'output_format': 'barcode_sheet_v1' if saved else 'barcode_bundle_v1',
        'input_format': job['request']['format'],
        'input_compression': job['request']['compression'],
        'selected_outputs': [] if saved else barcode_output_files(job),
        'result_selector_schema': deepcopy(BARCODE_RESULT_SELECTOR_SCHEMA),
        'result_selection': selected,
        'status_operations': ['execution.results.status'] if saved else ['progress.observe', 'execution.results.status'],
        'acquisition_operations': ['execution.results.collect'], 'extractors': extractors,
        'return_fact_sources': list(FACT_SOURCES), 'status_meanings': {
            'observation_basis': basis, 'fresh_native_observation': not saved,
            'native_success_capture_complete_delivery_complete_are_separate': True,
            'process_liveness_establishes_productive_work': False,
            'result_available': ('received_sheet_authority_and_current_bytes_are_separate' if saved else
                'observed_manifest_presence_does_not_establish_qualified_scientific_results'),
            'partial_results': 'validated_count_population_survives_later_distance_cluster_or_mapping_failure',
            'logs': 'selected_original_stdout_stderr_windows' if not saved else 'not_required',
        },
    }
