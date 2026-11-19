"""The job records an Episode holds: readers over the job ledger rows in its custody.

The ``job_access`` service writes one row of the work table ``JOB_LEDGER`` for each handoff, check and closure of
a job (``episode_runtime/job_access.py``). These functions read them for ``internal_summary``, ``credit``,
``msg_to_child`` and ``final_to_parent``. They take the read-only ``records`` (or ``ctx.store``) and find only the
rows the Episode holds: there is no reading of jobs it was not handed.

An **outstanding job** is one whose handoff row the Episode holds and whose closure row it does not hold.
"""
from __future__ import annotations

from episode_runtime.job_access import JOB_LEDGER


def job_rows(reader, job=None):
    """The held job ledger rows, in receipt order: all of them, or those of ``job``."""
    return reader.table(JOB_LEDGER).select(None if job is None else {'job': job})


def handoff(reader, job):
    """The held handoff row of ``job``; ``LookupError`` when the Episode holds none."""
    rows = reader.table(JOB_LEDGER).select({'job': job, 'event': 'handoff'})
    if not rows:
        raise LookupError('job_handoff_not_held:' + str(job))
    return rows[0]


def checks(reader, job):
    """The held check rows of ``job``, the earliest observation first."""
    return sorted(reader.table(JOB_LEDGER).select({'job': job, 'event': 'check'}), key=lambda row: row['at'])


def closure(reader, job):
    """The held closure row of ``job``, or ``None``."""
    rows = reader.table(JOB_LEDGER).select({'job': job, 'event': 'closure'})
    return rows[0] if rows else None


def outstanding_jobs(reader):
    """Each job the Episode holds a handoff of and no closure of: ``{'job', 'resource_id', 'kind',
    'submitted_at', 'estimates', 'handoff_ref', 'latest_check' (the latest held check: its reference, time, state,
    whether results are available and the assessment made at it; ``None`` before the first), 'record_refs' (the
    held rows of the job, to pass on in custody)}``, in the order the handoffs were received."""
    rows = reader.table(JOB_LEDGER).select()
    closed = {row['job'] for row in rows if row['event'] == 'closure'}
    found = []
    for row in rows:
        if row['event'] != 'handoff' or row['job'] in closed:
            continue
        seen = sorted((item for item in rows if item['job'] == row['job'] and item['event'] == 'check'),
                      key=lambda item: item['at'])
        latest = None if not seen else {
            'check_ref': seen[-1]['id'], 'observed_at': seen[-1]['at'], 'state': seen[-1]['detail']['state'],
            'result_available': seen[-1]['detail']['result_available'],
            'assessment': seen[-1]['detail']['assessment']}
        found.append({'job': row['job'], 'resource_id': row['detail']['resource_id'], 'kind': row['detail']['kind'],
                      'submitted_at': row['at'], 'estimates': row['detail']['estimates'], 'handoff_ref': row['id'],
                      'latest_check': latest, 'record_refs': [row['id'], *(item['id'] for item in seen)]})
    return found


__all__ = ['JOB_LEDGER', 'checks', 'closure', 'handoff', 'job_rows', 'outstanding_jobs']
