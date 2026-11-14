"""A101 BLAST monitor's original one-observation completion rule."""

from collections.abc import Mapping


def blast_monitor_yield(scores, parameters, contexts, target_handle):
    """Complete this monitor visit after one original BLAST status observation."""
    from .numerical import NumericBand, YieldEstimate, STATUS_UNIDENTIFIABLE
    observed = any(
        isinstance(item, Mapping)
        and isinstance(item.get('current_completion_evidence'), Mapping)
        and any(isinstance(row, Mapping) and row.get('target_handle') == target_handle
            and row.get('execution_status', {}).get('native', {}).get('native', {}).get('service') == 'ncbi_blast'
            for row in item['current_completion_evidence'].get('progress_records', ()))
        for item in contexts or ())
    return YieldEstimate(len(scores), NumericBand.exact(0) if observed else
        NumericBand.coded(STATUS_UNIDENTIFIABLE), parameters,
        {'original_blast_status_observed': observed}, estimator_binding={
            'kind': 'blast_monitor_one_observation_completion_v1',
            'forecast': 'zero_remaining_local_monitor_work_after_original_status_observation'})


def is_blast_job(services, context):
    describe = getattr(services, 'describe_progress_target', None)
    if not callable(describe):
        return False
    target = describe(context.assignment['target_handle'], context.scope)
    return (isinstance(target, Mapping) and target.get('resource_kind') == 'api'
        and target.get('service_or_program') == 'ncbi_blast')
