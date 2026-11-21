"""Where the acquisition stands, as a pure function of the view.

Everything is read from the records the Episode holds: the handoff row the commissioner passed, the check rows and
the closure row of the job that this Episode's units wrote through the job service, the files the closure row lists
for the requested paths, and every retained result acquisition (the earlier ones the parent passed and those of this
Episode's collect and read units), each read from its held record. From them come the job as it was last observed,
the acquisitions so far, whether the requested acquisition is complete and the record references the return may
name.

The credit view is what a decision needs of the Episode's credit: the unit, the credit so far and what each unit so
far earned."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    JOB_LEDGER, checks, closure, job_rows)


def _credit_view(view, parent):
    state = view.controller_state
    if state is None:
        return None
    record = state.as_record()
    return {'credit_unit': parent['acquired_record_unit'], 'current_credit': record['current_credit'],
            'credit_of_each_unit': list(record['scores'])}


def _observed(records, job):
    """The latest observation of the job among the rows this Episode holds: a check or the closure; ``None`` when
    it holds neither."""
    rows = [row for row in job_rows(records, job) if row['event'] in ('check', 'closure')]
    return max(rows, key=lambda row: row['at']) if rows else None


def _result(records, ref):
    """One retained result acquisition, read from its held record: the assignment it served and its windows over
    the fetched files."""
    source = records.get(ref)
    body = json.loads(records.get_artifact(source['artifact_ref']))
    return body['assignment'], {'ref': ref, 'artifact_ref': source['artifact_ref'], 'windows': body['windows']}


def native_results_complete(closed, results, requested):
    """Whether the requested acquisition is complete: the job finished (its closure row says so) and the retained
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
    records, parent = view.records, view.parent_input
    assignment = parent['assignment']
    handoff = records.table(JOB_LEDGER).get(assignment['handoff_ref'])
    closed, observed = closure(records, handoff['job']), _observed(records, handoff['job'])
    listed = {} if closed is None else {item['name']: item for item in closed['detail']['results']}
    fetched = {path: {'ref': listed[name]['ref'], 'bytes': listed[name]['bytes']}
               for path, name in parent['result_names'].items() if name in listed}
    job = {'job': handoff['job'], 'resource_id': handoff['detail']['resource_id'], 'kind': handoff['detail']['kind'],
           'submitted_at': handoff['at'],
           'last_observed_state': None if observed is None else observed['detail']['state'],
           'last_observed_at': None if observed is None else observed['at'],
           'closed': closed is not None, 'closure_ref': None if closed is None else closed['id'],
           'closed_at': None if closed is None else closed['at']}
    # The earlier results of this same assignment (a result of another selector of the job is not one of them).
    initial = [result for served, result in (_result(records, ref) for ref in parent['initial_result_refs'])
               if served == assignment]
    own, acquisitions = [], []
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
            _, result = _result(records, outcome['result_ref'])
            own.append(result)
            row.update({'result_ref': result['ref'],
                        'windows': [{key: window[key] for key in ('path', 'offset', 'returned_bytes', 'size_bytes')}
                                    for window in result['windows']]})
        acquisitions.append(row)
    complete = native_results_complete(closed, initial + own, parent['requested'])
    # The job ledger rows chosen for the parent: the latest check (the state last observed) and the closure (with
    # it the parent no longer counts the job as outstanding).
    job_refs = [row['id'] for row in (*checks(records, handoff['job'])[-1:], *([] if closed is None else [closed]))]
    return {'assignment': assignment, 'requested': parent['requested'], 'result_names': parent['result_names'],
            'acquired_record_unit': parent['acquired_record_unit'], 'job': job, 'fetched_files': fetched,
            'initial': initial, 'own': own, 'acquisitions': acquisitions, 'completed': complete,
            'execution_progress': {
                'execution_handoff_refs': [assignment['handoff_ref']],
                'execution_job_record_refs': job_refs,
                'execution_result_refs': [result['ref'] for result in own],
                'execution_result_artifact_refs': list(dict.fromkeys(
                    ref for result in own
                    for ref in (result['artifact_ref'], *(window['artifact_ref'] for window in result['windows'])))),
                'execution_completed': complete},
            'credit_view': _credit_view(view, parent), 'units_consumed': view.units_consumed}
