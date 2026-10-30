"""Pure operation/selection information; no prompt construction or execution."""
from __future__ import annotations

from copy import deepcopy
from .atac_differential_result_contracts import atac_result_schema, validate_atac_result_record, require, digest
from .atac_differential_return_views import FACT_SOURCES


def atac_result_selector_schema():
    schema = atac_result_schema('ResultSelector')
    # This resource is embedded inside results-assignment conditionals. Its
    # local references must remain scoped to its own definitions there.
    schema['$id'] = 'urn:gene-annotation:atac:selector:' + digest(schema)
    return schema


def validate_atac_result_selector(selector, *, request):
    from .native_atac_differential_contracts import validate_atac_record
    request = validate_atac_record('Request', request)
    selector = validate_atac_result_record('ResultSelector', selector)
    require(selector['comparison_key'] == request['comparison_key'], 'atac_result_comparison_conflict')
    require(set(selector['projection']['run_keys']) <= {'callpeak1', 'callpeak2'}, 'atac_result_unknown_run')
    return selector


def describe_atac_result(target, *, selector):
    from .execution_contracts import validate_target, digest
    from .native_atac_differential_contracts import POLICY, validate_atac_requested_job
    target = validate_target(target)
    assignment = target['assignment']
    require(target['resource_kind'] == assignment['resource_kind'] == 'local'
        and target['resource_id'] == assignment['resource_id'], 'atac_result_target_conflict')
    job = validate_atac_requested_job(assignment['requested_job'])
    require(target['request_sha256'] == digest(job), 'atac_result_target_conflict')
    request = job['native_atac_differential']['request']
    selected = validate_atac_result_selector(selector, request=request)
    saved = selected['mode'] == 'saved_sheet_recalculation'
    host = 'gene_annotation_episode.native_atac_differential_results.NativeAtacDifferentialResults.execute'
    collect = dict(operation='execution.results.collect', implementation=host,
        preparation='gene_annotation_episode.native_atac_differential_preparation.prepare_atac_result_worker',
        worker_plan='gene_annotation_episode.native_atac_differential_preparation.' + ('build_saved_atac_worker_plan' if saved else 'build_native_atac_worker_plan'),
        result_worker='gene_annotation_episode.atac_differential_result_worker.run_atac_result_worker',
        calculation_inputs='gene_annotation_episode.atac_differential_calculation_inputs.prepare_atac_calculation_inputs',
        calculators=['gene_annotation_episode.atac_differential_calculations.' + name for name in
            ('iter_atac_track_segments', 'iter_atac_interval_components', 'iter_atac_differential_regions')],
        projection='gene_annotation_episode.atac_differential_result_views.project_atac_result',
        parameters=deepcopy(selected['parameters']), return_fact_sources=list(FACT_SOURCES),
        return_source_scope='receiving_form_requested_sources', new_native_analysis=False,
        native_input_acquisition=False, local_job_policy=deepcopy(POLICY), swap_bytes=0)
    if saved:
        collect.update(saved_input_validation='gene_annotation_episode.atac_differential_returns.AtacDifferentialReturns.authenticate_received_saved_bundle',
            table_parser='gene_annotation_episode.atac_differential_inputs.iter_atac_track_table_rows')
    else:
        collect.update(capture='gene_annotation_episode.native_atac_differential_capture.capture_atac_native_files',
            table_parser='gene_annotation_episode.atac_differential_inputs.iter_atac_bedgraph_records',
            header_parser='gene_annotation_episode.atac_reference_observations.parse_atac_bam_reference',
            sheet_population='gene_annotation_episode.atac_differential_sheet.build_atac_differential_sheet')
    return dict(resource_kind='local', service_or_program=request['operation'], operation=request['operation'],
        mode=request['mode'], input_format='bam', output_format='atac_differential_calculations_v1' if saved else 'atac_differential_native_bundle_v1',
        result_selection=selected, observation_basis='received_saved_sheet_and_original_receipts' if saved else 'original_selected_local_attempt',
        status_operations=['execution.results.status'] if saved else ['progress.observe', 'execution.results.status'],
        acquisition_operations=['execution.results.collect'], extractors=[dict(operation='execution.results.status', implementation=host,
            fresh_native_observation=not saved, scientific_result_acquisition=False, return_fact_sources=[], completes_assignment=False), collect],
        return_fact_sources=list(FACT_SOURCES))


__all__ = ['atac_result_selector_schema', 'validate_atac_result_selector', 'describe_atac_result']
