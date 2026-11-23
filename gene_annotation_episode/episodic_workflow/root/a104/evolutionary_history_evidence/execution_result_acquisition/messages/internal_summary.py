"""Where the acquisition stands, as a pure function of the view.

Everything is read from the records the Episode holds: the handoff row the commissioner passed, the check rows and
the closure row of the job (those the parent passed and those this Episode's units wrote through the job service),
the files the closure row lists for the requested paths, and every retained result acquisition (the initial results
the parent passed and those of this Episode's collect and read units), each read from its held record. From them
come the job as it was last observed, the acquisitions so far, whether the requested acquisition is complete and
the record references the return may name.

The credit view is what a decision needs of the Episode's credit: the unit, the credit so far and what each unit so
far earned."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    JOB_LEDGER, checks, closure, job_rows)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information'


def _credit_view(view, parent):
    state = view.controller_state
    if state is None:
        return None
    record = state.as_record()
    return {'credit_unit': parent['acquired_record_unit'], 'current_credit': record['current_credit'],
            'credit_of_each_unit': list(record['scores'])}


def _job_record_refs(records):
    """The job ledger rows chosen for the parent, of each job this Episode holds rows of: the latest check (the
    state last observed) and the closure (with it the parent no longer counts the job as outstanding)."""
    refs = []
    for job in dict.fromkeys(row['job'] for row in job_rows(records)):
        closed = closure(records, job)
        refs.extend(row['id'] for row in (*checks(records, job)[-1:], *([] if closed is None else [closed])))
    return refs


def _observed(records):
    """The latest observation of the job among the rows this Episode holds: a check or the closure; ``None`` when
    it holds neither."""
    rows = [row for row in job_rows(records) if row['event'] in ('check', 'closure')]
    return max(rows, key=lambda row: row['at']) if rows else None


def _result(records, ref, assignment, initial):
    """One retained result acquisition, read from its held record: its windows over the fetched files. A result of
    another assignment, or of another form (the bundle of a typed family), is not a plain file result of this
    assignment."""
    source = records.get(ref)
    if source['provider'] != RESULT_PROVIDER:
        raise ValueError('execution_initial_result_not_an_execution_result')
    if source['version'] != RESULT_VERSION:
        return None
    body = json.loads(records.get_artifact(source['artifact_ref']))
    if body['assignment'] != assignment:
        return None
    return {'ref': ref, 'artifact_ref': source['artifact_ref'], 'initial': initial, 'windows': body['windows']}


def _complete(requested, closed, results):
    """Whether the requested acquisition is complete: the job finished (its command returned 0) and the retained
    windows cover every requested byte interval."""
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
    """The plain file results of the handed-off job, from the held records and the outcomes of the units so far."""
    parent, records = view.parent_input, view.records
    assignment = parent['assignment']
    handoff = records.table(JOB_LEDGER).get(assignment['handoff_ref'])
    closed, observed = closure(records, handoff['job']), _observed(records)
    listed = {} if closed is None else {item['name']: item for item in closed['detail']['results']}
    fetched = {path: {'ref': listed[name]['ref'], 'bytes': listed[name]['bytes']}
               for path, name in parent['result_names'].items() if name in listed}
    job = {'job': handoff['job'], 'resource_id': handoff['detail']['resource_id'], 'kind': handoff['detail']['kind'],
           'submitted_at': handoff['at'],
           'last_observed_state': None if observed is None else observed['detail']['state'],
           'last_observed_at': None if observed is None else observed['at'],
           'closed': closed is not None, 'closure_ref': None if closed is None else closed['id'],
           'closed_at': None if closed is None else closed['at']}
    results = [result for result in (_result(records, ref, assignment, True)
                                     for ref in parent['initial_result_refs']) if result is not None]
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
    complete = _complete(parent['requested'], closed, results)
    own = [result for result in results if not result['initial'] and result['windows']]
    result_refs = list(dict.fromkeys(ref for result in own for ref in (
        result['ref'], result['artifact_ref'], *(window['artifact_ref'] for window in result['windows']))))
    return {'assignment': assignment, 'family': parent['family'], 'requested': parent['requested'],
            'result_names': parent['result_names'], 'acquired_record_unit': parent['acquired_record_unit'],
            'job': job, 'fetched_files': fetched, 'results': results, 'acquisitions': acquisitions,
            'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']],
                                   'execution_job_record_refs': _job_record_refs(records),
                                   'execution_result_refs': result_refs, 'execution_completed': complete},
            'execution_completed': complete, 'credit_view': _credit_view(view, parent)}
