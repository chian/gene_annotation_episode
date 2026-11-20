"""Where the visit stands, as a pure function of the view: the commission, the job's resource read from the handoff row
the episode holds, what each unit did (a check that completed, with its state and time, or a failure with its code and how
long the service asks to be left alone) and the latest observation among the check rows the episode holds, those the
parent handed over and those its own units wrote."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_progress import FIELDS, check_view, held_checks
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import JOB_LEDGER


def internal_summary(view):
    parent, records = view.parent_input, view.records
    handoff = records.table(JOB_LEDGER).get(parent['handoff_ref'])
    units, own = [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        if outcome['status'] == 'completed':
            own.append(outcome['check_ref'])
            units.append({'status': 'completed', 'state': outcome['state'], 'observed_at': outcome['observed_at'],
                          'retry_after_seconds': None})
        else:
            failure = outcome['failure']
            units.append({'status': 'failed', 'state': None, 'observed_at': None, 'failure_code': failure['code'],
                          'retry_after_seconds': failure['detail'].get('retry_after_seconds')})
    rows = [row for row in held_checks(records, handoff['job']) if row['detail']['handoff_ref'] == parent['handoff_ref']]
    latest = max(rows, key=lambda row: row['at']) if rows else None
    return {**parent, 'resource_id': handoff['detail']['resource_id'], 'job': handoff['job'], 'units': units,
            'own_check_refs': own, 'latest': None if latest is None else check_view(latest, FIELDS),
            'units_consumed': view.units_consumed}
