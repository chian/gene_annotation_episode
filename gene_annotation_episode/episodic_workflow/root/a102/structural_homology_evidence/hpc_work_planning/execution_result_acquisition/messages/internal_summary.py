"""Where the acquisition stands, as a pure function of the view.

Everything is read from the records the Episode holds: the handoff row the commissioner passed (its ``detail``
gives the job, its resource and the job's directory), the check rows and the closure row of the job that this
Episode's units wrote through the job service, the files the closure row lists for the requested paths, and every
retained result acquisition (the known results the parent passed and those of this Episode's collect and read
units), each read from its held record. From them come the job as it was last observed, the acquisitions so far,
whether the requested acquisition is complete and the record references the return may name.

The requested paths are confined to the job's directory here, where the handoff row is read, and the job service's
name of each path (its path inside that directory, which is how a route lists the result files of a job) is
computed here: a path outside the directory raises and the run fails with that error.

The credit view is what a decision needs of the Episode's credit: the unit, the credit so far and what each unit so
far earned."""
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    JOB_LEDGER, checks, closure, job_rows)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.structural_homology_evidence.practical_execution_operations import (
    confined)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v3'


def result_names(handoff, requested):
    """The job service's name of each requested path: its path inside the job's directory."""
    directory = Path(handoff['detail']['native']['directory']).resolve()
    return {path: confined(path, directory).relative_to(directory).as_posix() for path in requested}


def _credit_view(view, parent):
    state = view.controller_state
    if state is None:
        return None
    record = state.as_record()
    return {'credit_unit': parent['acquired_record_unit'], 'current_credit': record['current_credit'],
            'credit_of_each_unit': list(record['scores'])}


def _job_record_refs(records, job):
    """The job ledger rows chosen for the parent: the latest check (the state last observed) and the closure (with
    it the parent no longer counts the job as outstanding)."""
    closed = closure(records, job)
    return [row['id'] for row in (*checks(records, job)[-1:], *([] if closed is None else [closed]))]


def _observed(records, job):
    """The latest observation of the job among the rows this Episode holds: a check or the closure; ``None`` when
    it holds neither."""
    rows = [row for row in job_rows(records, job) if row['event'] in ('check', 'closure')]
    return max(rows, key=lambda row: row['at']) if rows else None


def _result(records, ref, assignment, initial):
    """One retained result acquisition, read from its held record: its windows over the fetched files. A result
    of another assignment is not a result of this one."""
    source = records.get(ref)
    if source['provider'] != RESULT_PROVIDER or source['version'] != RESULT_VERSION:
        raise ValueError('invalid_execution_result_information')
    body = json.loads(records.get_artifact(source['artifact_ref']))
    if body['assignment'] != assignment:
        return None
    return {'ref': ref, 'artifact_ref': source['artifact_ref'], 'initial': initial, 'windows': body['windows']}


def _known(records, refs, assignment):
    """The known results of this assignment among what the parent passed back: the result records (the
    information artifacts and fetched files passed with them are read through their record)."""
    found = (_result(records, ref, assignment, True) for ref in refs
             if records.get(ref)['record_type'] == 'source')
    return [result for result in found if result is not None]


def _complete(requested, closed, results):
    """Whether the requested acquisition is complete: the job finished (its command returned 0) and the retained
    windows cover every requested byte interval without a gap."""
    if closed is None or closed['detail']['state'] != 'finished':
        return False
    for path, (start, length) in requested.items():
        windows = [window for result in results for window in result['windows'] if window['path'] == path]
        if not windows:
            return False
        end = max(window['size_bytes'] for window in windows)
        if length is not None:
            end = min(end, start + length)
        cursor = start
        for window in sorted(windows, key=lambda item: item['offset']):
            if window['offset'] > cursor:
                return False
            cursor = max(cursor, window['offset'] + window['returned_bytes'])
        if cursor < end:
            return False
    return True


def internal_summary(view):
    parent = view.parent_input
    records, assignment, requested = view.records, parent['assignment'], parent['requested']
    handoff = records.table(JOB_LEDGER).get(assignment['handoff_ref'])
    names = result_names(handoff, requested)
    closed, observed = closure(records, handoff['job']), _observed(records, handoff['job'])
    listed = {} if closed is None else {item['name']: item for item in closed['detail']['results']}
    fetched = {path: {'ref': listed[name]['ref'], 'bytes': listed[name]['bytes']}
               for path, name in names.items() if name in listed}
    job = {'job': handoff['job'], 'resource_id': handoff['detail']['resource_id'], 'kind': handoff['detail']['kind'],
           'submitted_at': handoff['at'],
           'last_observed_state': None if observed is None else observed['detail']['state'],
           'last_observed_at': None if observed is None else observed['at'],
           'closed': closed is not None, 'closure_ref': None if closed is None else closed['id'],
           'closed_at': None if closed is None else closed['at']}
    results = _known(records, parent['known_result_refs'], assignment)
    acquisitions = []
    for unit in view.outcomes:
        outcome = unit['outcome']
        row = {'tool': unit['tool'], 'status': outcome['status']}
        if unit['tool'] == 'execution_results_read':
            row['window'] = unit['arguments']['window']
        if outcome['status'] == 'failed':
            row['failure_code'] = outcome['failure']['code']
        elif outcome['status'] == 'invalid':
            row['failure_code'] = outcome['feedback']['code']
        elif unit['tool'] == 'execution_results_status':
            row.update({'state': outcome['state'], 'result_available': outcome['result_available']})
        else:
            result = _result(records, outcome['result_ref'], assignment, False)
            results.append(result)
            row.update({'result_ref': result['ref'],
                        'windows': [{key: window[key] for key in ('path', 'offset', 'returned_bytes', 'size_bytes')}
                                    for window in result['windows']]})
        acquisitions.append(row)
    complete = _complete(requested, closed, results)
    own = [result for result in results if not result['initial'] and result['windows']]
    result_refs = list(dict.fromkeys(ref for result in own for ref in (
        result['ref'], result['artifact_ref'], *(window['artifact_ref'] for window in result['windows']))))
    return {'assignment': assignment, 'requested': requested, 'result_names': names,
            'acquired_record_unit': parent['acquired_record_unit'], 'job': job, 'fetched_files': fetched,
            'results': results, 'acquisitions': acquisitions,
            'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']],
                                   'execution_job_record_refs': _job_record_refs(records, handoff['job']),
                                   'execution_result_refs': result_refs, 'execution_completed': complete},
            'execution_completed': complete, 'credit_view': _credit_view(view, parent),
            'units_consumed': view.units_consumed}
