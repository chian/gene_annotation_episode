"""The progress of a job, as a monitor reads it from the check rows it holds.

A monitor learns about a job by ``job_access.check`` (``episode_runtime/job_access.py``): one status request,
written as a ``check`` row of the job ledger in the monitor's custody. These functions are the monitor's own
reading of those rows. They take the read-only ``records`` (or ``ctx.store``) and find only held rows.

- ``status_reading(status, handoff)`` is the ``assess`` a monitor passes to ``job_access.check``: the measurements
  of the route's reply as controlled features (numbers, booleans, file names of a fixed set, a status word of the
  provider's fixed set), kept in the row. There is one reading for each kind of route (``READINGS``):

  | Kind | Route | What its status reply measures |
  |---|---|---|
  | ``local`` | ``local_job_route.py`` | the return code and duration of the ended command, the elapsed seconds of a running one, the two logs and their sizes |
  | ``pbs`` | ``pbs_job_route.py`` | the return code of the ended job |
  | ``api`` | ``api_job_route.py`` | the service's own word for the job's status (``provider_status``) and, once the job has finished, whether it found anything (``has_hits``); a web service reports no return code, duration or elapsed time and keeps no log |

  Every reading holds ``MEASUREMENTS``; the ``api`` reading also holds ``PROVIDER_MEASUREMENTS``. The job's state
  (``job_access.STATES``; a web service's unfinished job is ``queued``) and whether its results are available are
  the route's own and stand in the check row beside the reading. A status request the route did not send or the
  resource did not answer is no check: ``job_access.check`` returns it as ``{'status': 'failed', 'failure':
  {'code', 'detail'}}`` and writes no row. For an API job that includes a request that comes before the
  provider's spacing permits it (``provider_spacing_required``; the detail says ``sent: False``,
  ``retry_after_seconds`` and ``earliest_at``).
- ``check_view(row, fields)`` is what a check row shows of the fields a monitor was asked for.
- ``progress_information(reader, baseline_refs, fields, information_unit)`` is the information credit: one unit
  for each held check row, outside the baseline the commissioner passed, that shows a fact of its job the rows
  before it (in receipt order, the baseline first) do not show. Timestamps, the elapsed time of an unfinished job
  and the size of its logs are not facts: they change without anything being learned.
- ``check_expectation`` and ``check_resolution`` are the rows a check adds to the estimate table
  (``episode_runtime/estimate_table.py``): what was expected of the check before it ran, in the monitor's credit
  units, and what it gave.

The fields a commissioner may ask for (``FIELDS``): ``execution_status`` (the job's state), ``result_available``,
``measurements`` (what the reading of the job's route kind holds). The logs a route keeps in a job's directory,
which ``job_access.window`` reads while the job runs, are ``LOGS`` by route kind: ``LOG_NAMES`` for a local and a
PBS job, none for an API job.
"""
from __future__ import annotations

from datetime import datetime

from episode_runtime.job_access import STATES as JOB_STATES

from .job_records import job_rows

FIELDS = ('execution_status', 'result_available', 'measurements')
LOG_NAMES = ('stdout.log', 'stderr.log')
LOGS = {'local': LOG_NAMES, 'pbs': LOG_NAMES, 'api': ()}
MEASUREMENTS = ('returncode', 'duration_seconds', 'elapsed_seconds', 'outputs')
PROVIDER_MEASUREMENTS = ('provider_status', 'has_hits')
# The measurements that are facts of a job once they are known: they do not change without something being learned.
FACTS = ('returncode', 'duration_seconds', *PROVIDER_MEASUREMENTS)


def _local(reply):
    receipt = reply['receipt']
    duration = None if receipt is None else (datetime.fromisoformat(receipt['ended_at'])
                                             - datetime.fromisoformat(receipt['started_at'])).total_seconds()
    return {'returncode': None if receipt is None else receipt['returncode'], 'duration_seconds': duration,
            'elapsed_seconds': reply['elapsed_seconds'] if receipt is None else None,
            'outputs': [{'name': name + '.log', 'available': reply['files'][name]['available'],
                         'bytes': reply['files'][name]['bytes']} for name in ('stdout', 'stderr')]}


def _pbs(reply):
    # A login-mode job reports ``returncode``; a batch job's scheduler fields report ``Exit_status`` once it ended.
    native = reply['native']
    return {'returncode': native.get('returncode', native.get('Exit_status')), 'duration_seconds': None,
            'elapsed_seconds': None, 'outputs': []}


def _api(reply):
    # The service's own word for the job's status, and whether a finished job found anything (``None`` before).
    return {'returncode': None, 'duration_seconds': None, 'elapsed_seconds': None, 'outputs': [],
            'provider_status': reply['provider_status'], 'has_hits': reply['has_hits']}


READINGS = {'local': _local, 'pbs': _pbs, 'api': _api}


def status_reading(status, handoff):
    """The measurements of one status reply of the handoff's route kind: ``{'returncode', 'duration_seconds' (of
    the ended command), 'elapsed_seconds' (of a command still running), 'outputs' ([{'name', 'available',
    'bytes'}])}`` and, for an API job, ``'provider_status'`` and ``'has_hits'``; what the route does not report is
    ``None``. A kind without a reading raises ``KeyError``."""
    return READINGS[handoff['detail']['kind']](status['reply'])


def check_view(row, fields):
    """What the check row shows of ``fields``: its reference and observation time, and the asked facts."""
    view = {'check_ref': row['id'], 'observed_at': row['at']}
    if 'execution_status' in fields:
        view['state'] = row['detail']['state']
    if 'result_available' in fields:
        view['result_available'] = row['detail']['result_available']
    if 'measurements' in fields:
        view.update(row['detail']['assessment'])
    return view


def check_facts(row, fields):
    """The facts of a check row that count as information, among ``fields``: a set of tuples."""
    detail, facts = row['detail'], set()
    if 'execution_status' in fields:
        facts.add(('state', detail['state']))
    if 'result_available' in fields:
        facts.add(('result_available', detail['result_available']))
    if 'measurements' in fields:
        reading = detail['assessment']
        facts.update((name, reading[name]) for name in FACTS if name in reading and reading[name] is not None)
        facts.update(('output_available', output['name'], output['available']) for output in reading['outputs'])
    return facts


def held_checks(reader, job=None):
    """The held check rows (of ``job``, or of every job), in receipt order."""
    return [row for row in job_rows(reader, job) if row['event'] == 'check']


def progress_information(reader, baseline_refs, fields, information_unit):
    """The information credit of the held check rows over the baseline: ``{'credit', 'information_unit',
    'contributions' ([{'check_ref', 'job', 'new_fact_count'}], one per newly informative row)}``. The facts of
    the baseline rows are known beforehand; each other row, in receipt order, contributes one unit when it shows
    at least one fact of its job not seen before it. Several new facts in one row still earn one unit."""
    rows, seen, contributions = held_checks(reader), {}, []
    for row in rows:
        if row['id'] in baseline_refs:
            seen.setdefault(row['job'], set()).update(check_facts(row, fields))
    for row in rows:
        if row['id'] in baseline_refs:
            continue
        known = seen.setdefault(row['job'], set())
        novel = check_facts(row, fields) - known
        if novel:
            contributions.append({'check_ref': row['id'], 'job': row['job'], 'new_fact_count': len(novel)})
        known.update(novel)
    return {'credit': information_unit * len(contributions), 'information_unit': information_unit,
            'contributions': contributions}


def check_expectation(informative_probability, information_unit, cost):
    """What is expected of one check before it runs, for ``EstimateTable.expect``: the gain band in the monitor's
    credit units (nothing, the probability-weighted unit, one unit), the cost of the unit and the two outcomes."""
    return {'gain': {'value': information_unit * informative_probability, 'lower': 0.0, 'upper': information_unit},
            'cost': cost,
            'outcomes': [{'label': 'informative', 'probability': informative_probability},
                         {'label': 'nothing_new', 'probability': 1 - informative_probability}]}


def check_resolution(informative, expectation, state):
    """What the check gave, for ``EstimateTable.resolve``: the credit it earned, its cost and its outcome."""
    return {'gain': expectation['gain']['upper'] if informative else 0.0, 'cost': expectation['cost'],
            'outcome': 'informative' if informative else 'nothing_new', 'state': state}


__all__ = ['FACTS', 'FIELDS', 'JOB_STATES', 'LOGS', 'LOG_NAMES', 'MEASUREMENTS', 'PROVIDER_MEASUREMENTS',
           'check_expectation', 'check_facts', 'check_resolution', 'check_view', 'held_checks',
           'progress_information', 'status_reading']
