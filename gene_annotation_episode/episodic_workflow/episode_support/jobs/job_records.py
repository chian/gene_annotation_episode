"""The job records an Episode holds: readers over the job ledger rows in its custody.

The ``job_access`` service writes one row of the work table ``JOB_LEDGER`` for each handoff, check and closure of
a job (``episode_runtime/job_access.py``). These functions read them for ``internal_summary``, ``credit``,
``msg_to_child`` and ``final_to_parent``. They take the read-only ``records`` (or ``ctx.store``) and find only the
rows the Episode holds: there is no reading of jobs it was not handed.

An **outstanding job** is one whose handoff row the Episode holds and whose closure row it does not hold.
"""
from __future__ import annotations

from episode_runtime.job_access import JOB_LEDGER
from episode_runtime.work_tables import is_row_ref


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


def named_records(reader, ref):
    """The held records the held record ``ref`` names, in the order it names them. A Store record names what the Store's
    own rule says (``reader.named_references``); an artifact names none; a job ledger row names its reply artifact
    (``source_ref``), its ``result_refs``, the artifacts a handoff staged as the job's inputs (``detail['input_refs']``,
    a mapping of file name to artifact) and the handoff a check, window or closure row belongs to
    (``detail['handoff_ref']``). Only records the reader holds are named."""
    if ref.startswith('artifact_'):
        return []
    if is_row_ref(ref):
        row = reader.get(ref)
        detail = row['detail']
        names = [row['source_ref'], *row['result_refs'], *detail.get('input_refs', {}).values()]
        if 'handoff_ref' in detail:
            names.append(detail['handoff_ref'])
    else:
        names = reader.named_references(ref)
    return [name for name in dict.fromkeys(names) if name != ref and reader.holds(name)]


def returned_with_names(reader, refs):
    """THE CLOSING RULE of what a child returns: the records ``refs`` the child chose to return, together with everything
    they name, and everything those name in turn, among the records the child holds (the walk the head's ``msg_to_child``
    does when it passes records on). A returned list is closed under naming by construction: what a child returns it
    returns for the parent to use, and nothing a returned record names stays private to the child. A record that must stay
    private must not be named by anything returned."""
    found, pending = [], list(refs)
    while pending:
        ref = pending.pop(0)
        if ref not in found:
            found.append(ref)
            pending.extend(named_records(reader, ref))
    return found


__all__ = ['JOB_LEDGER', 'checks', 'closure', 'handoff', 'job_rows', 'named_records', 'outstanding_jobs',
           'returned_with_names']
