"""Original saved BLAST scientific identity and annotation summaries."""
import json

def blast_scientific_owner(self, origin_episode_id):
    """Recover the annotation and axis assigned above one original launch."""
    row = self.store.db.execute('SELECT path FROM runtime_episodes WHERE run_id=? AND episode_id=?', (self.run_id, origin_episode_id)).fetchone()
    if row is None:
        raise ValueError('blast_original_launch_episode_unavailable')
    path = json.loads(row['path'])
    for length in range(len(path), 0, -1):
        if path[length - 1][0] != 'partner_presence_evidence':
            continue
        owner = self.store.db.execute('SELECT request FROM runtime_episodes WHERE run_id=? AND json(path)=json(?)', (self.run_id, json.dumps(path[:length]))).fetchone()
        if owner is None:
            raise ValueError('blast_scientific_owner_unavailable')
        assignment = json.loads(owner['request'])['message']['episode_assignment']
        return {'proposed_annotation_ref': assignment.get('proposed_annotation_ref'), 'evidence_axis': assignment['selection']['evidence_axis']['option_id']}
    return {'proposed_annotation_ref': None, 'evidence_axis': None}
def blast_axis_summaries(jobs):
    """Keep root scheduling input at annotation/axis level."""
    grouped = {}
    for job in jobs:
        key = (job['proposed_annotation_ref'], job['evidence_axis'], job['subject_ref'])
        grouped.setdefault(key, []).append(job)
    summaries = []
    for annotation, axis, subject in sorted(grouped, key=lambda key: tuple(('' if value is None else value for value in key))):
        rows = grouped[annotation, axis, subject]
        active = [row for row in rows if not row['result_received'] and row['native_state'] not in {'FAILED', 'UNKNOWN', 'failed', 'unknown'}]
        actionable = min(active, key=lambda row: (row['native_state'] != 'READY', row['observed_at'], row['handoff_ref'])) if active else None
        summaries.append({'proposed_annotation_ref': annotation, 'evidence_axis': axis, 'subject_ref': subject, 'original_job_count': len(rows), 'waiting_count': sum((row['native_state'] in {'accepted', 'WAITING'} for row in active)), 'ready_count': sum((row['native_state'] == 'READY' for row in active)), 'result_received_count': sum((row['result_received'] for row in rows)), 'failed_or_unknown_count': sum((row['native_state'] in {'FAILED', 'UNKNOWN', 'failed', 'unknown'} for row in rows)), 'actionable_handoff_ref': None if actionable is None else actionable['handoff_ref'], 'status_observed_at': None if actionable is None else actionable['observed_at'], 'forecast_as_of': None if actionable is None else actionable['forecast_as_of'], 'latest_progress_failure_code': None if actionable is None else actionable['latest_progress_failure_code'], 'estimated_remaining_seconds': None if actionable is None else (actionable['wait_forecast'] or {}).get('estimated_remaining_seconds')})
    return summaries
