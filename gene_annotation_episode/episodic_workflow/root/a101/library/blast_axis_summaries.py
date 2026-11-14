"""Original A101 annotation/axis summary calculation."""

def _blast_axis_summaries(jobs):
    """Keep root scheduling input at annotation/axis level."""
    grouped = {}
    for job in jobs:
        key = (job['proposed_annotation_ref'], job['evidence_axis'], job['subject_ref'])
        grouped.setdefault(key, []).append(job)
    summaries = []
    for annotation, axis, subject in sorted(grouped,
            key=lambda key: tuple('' if value is None else value for value in key)):
        rows = grouped[(annotation, axis, subject)]
        active = [row for row in rows if not row['result_received']
            and row['native_state'] not in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}]
        actionable = min(active, key=lambda row: (
            row['native_state'] != 'READY', row['observed_at'], row['handoff_ref'])) if active else None
        summaries.append({'proposed_annotation_ref': annotation, 'evidence_axis': axis,
            'subject_ref': subject, 'original_job_count': len(rows),
            'waiting_count': sum(row['native_state'] in {'accepted', 'WAITING'} for row in active),
            'ready_count': sum(row['native_state'] == 'READY' for row in active),
            'result_received_count': sum(row['result_received'] for row in rows),
            'failed_or_unknown_count': sum(row['native_state'] in
                {'FAILED', 'UNKNOWN', 'failed', 'unknown'} for row in rows),
            'actionable_handoff_ref': None if actionable is None else actionable['handoff_ref'],
            'status_observed_at': None if actionable is None else actionable['observed_at'],
            'forecast_as_of': None if actionable is None else actionable['forecast_as_of'],
            'latest_progress_failure_code': (None if actionable is None else
                actionable['latest_progress_failure_code']),
            'estimated_remaining_seconds': (None if actionable is None else
                (actionable['wait_forecast'] or {}).get('estimated_remaining_seconds'))})
    return summaries
