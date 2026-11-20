"""Where the acquisition stands, as a pure function of the view.

For the plain file results of a job (``native_bytes``) everything is read from the records the Episode holds: the
handoff row the commissioner passed, the check rows and the closure row of the job (those the parent passed and
those this Episode's units wrote through the job service), the files the closure row lists for the requested paths,
and every retained result acquisition (the initial results the parent passed and those of this Episode's collect and
read units), each read from its held record. From them come the job as it was last observed, the acquisitions so
far, whether the requested acquisition is complete and the record references the return may name.

For the graded returns (``blast_graded``, ``phmmer_graded``) it is the fetched result files and the gradings of the
units so far with the controlled features of the saved sheets.

The credit view is what a decision needs of the Episode's credit: the unit, the credit so far and what each unit so
far earned."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_search_features import (
    saved_hit_features)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_records import (
    JOB_LEDGER, checks, closure, job_rows)

RESULT_PROVIDER = 'episode.execution_result'
RESULT_VERSION = 'execution_result_information_v3'
PLAIN_TOOLS = ('execution_results_status', 'execution_results_collect', 'execution_results_read')


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


def _plain(view, parent):
    """The plain file results of the handed-off job, from the held records and the outcomes of the units so far."""
    records, assignment = view.records, parent['assignment']
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
        if unit['tool'] not in PLAIN_TOOLS:
            continue
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
    return {'assignment': assignment, 'target': parent['target'], 'family': parent['family'],
            'requested': parent['requested'], 'result_names': parent['result_names'],
            'acquired_record_unit': parent['acquired_record_unit'],
            'initial_result_refs': parent['initial_result_refs'], 'job': job, 'fetched_files': fetched,
            'results': results, 'acquisitions': acquisitions,
            'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']],
                                   'execution_job_record_refs': _job_record_refs(records),
                                   'execution_result_refs': result_refs, 'execution_file_source_refs': [],
                                   'execution_completed': complete, 'execution_blast_graded_refs': [],
                                   'execution_phmmer_graded_refs': []},
            'execution_completed': complete, 'graded_sheets': [], 'profile_sheets': [],
            'credit_view': _credit_view(view, parent), 'units_consumed': view.units_consumed}


def _blast_graded(view, parent):
    """The graded BLAST return: the result files fetched so far (those the parent passed and those this Episode's
    fetch units acquired through the job service's closure row) and, for each grading unit that completed, the
    controlled features code reads from the saved grading artifact (``blast_database_features``)."""
    fetched = [{'result_ref': ref, 'name': None, 'initial': True} for ref in parent['initial_result_refs']]
    closed, graded, gradings = False, [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        if unit['tool'] == 'execution_results_fetch' and outcome['status'] == 'completed':
            closed = True
            fetched.extend({'result_ref': item['ref'], 'name': item['name'], 'initial': False}
                           for item in outcome['results'])
        if unit['tool'] == 'blast_grade':
            gradings.append({'result_ref': unit['arguments']['result_ref'], 'status': outcome['status'],
                             **({'code': outcome['feedback']['code']} if outcome['status'] != 'completed' else {})})
            if outcome['status'] == 'completed' and outcome['result']['grading_artifact_ref'] not in {
                    row['sheet_refs'][0] for row in graded}:
                graded.append({'source_ref': outcome['result']['result_ref'],
                               'search_ref': outcome['result']['search_ref'],
                               **saved_grading_features(view.records, outcome['result']['grading_artifact_ref'])})
    return fetched, closed, graded, gradings


def _first_line(records, ref):
    """The first line of a fetched result file (at most 120 bytes), so the model can tell the files apart."""
    with records.open_artifact(ref) as stream:
        return stream.readline(120).decode('utf-8', 'replace').rstrip('\n')


def _phmmer_graded(view, parent):
    """The local phmmer return: the result files fetched so far (those the parent passed and those this Episode's
    fetch units acquired), each with its first line, and the gradings of its ``phmmer_grade`` units with the
    controlled features of every retained hit sheet (``hmmer_search_features``)."""
    fetched = [{'result_ref': ref, 'name': None, 'initial': True} for ref in parent['initial_result_refs']]
    closed, gradings, grading_refs, refs = False, [], [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        if unit['tool'] == 'execution_results_fetch' and outcome['status'] == 'completed':
            closed = True
            fetched.extend({'result_ref': item['ref'], 'name': item['name'], 'initial': False}
                           for item in outcome['results'])
        if unit['tool'] == 'phmmer_grade':
            gradings.append({'status': outcome['status'],
                             **({'code': outcome['feedback']['code']} if outcome['feedback'] else {})})
            if outcome['status'] in ('completed', 'partial'):
                grading_refs.extend(ref for ref in outcome['result']['grading_artifact_refs']
                                    if ref not in grading_refs)
                refs.extend(ref for ref in outcome['record_refs'] if ref not in refs)
    for row in fetched:
        row['first_line'] = _first_line(view.records, row['result_ref'])
    return fetched, closed, gradings, saved_hit_features(view.records, grading_refs), refs


def _graded(view, parent, *, fetched, closed, gradings, complete, graded_sheets, profile_sheets, blast_refs,
            phmmer_refs):
    """The summary of a graded return."""
    assignment, target = parent['assignment'], parent['target']
    held, observed = view.records.holds(assignment['handoff_ref']), _observed(view.records)
    return {'assignment': assignment, 'target': target, 'family': parent['family'],
            'selector': parent['selector'], 'acquired_record_unit': parent['acquired_record_unit'],
            'initial_result_refs': parent['initial_result_refs'],
            'job': {'resource_id': target['resource_id'], 'kind': target['resource_kind'], 'handoff_held': held,
                    'last_observed_state': None if observed is None else observed['detail']['state'],
                    'closed': closed},
            'fetched_results': fetched, 'fetch_offered': held and not closed, 'gradings': gradings,
            'graded_sheets': graded_sheets, 'profile_sheets': profile_sheets,
            'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']] if held else [],
                                   'execution_job_record_refs': _job_record_refs(view.records),
                                   'execution_result_refs': [], 'execution_file_source_refs': [],
                                   'execution_completed': complete, 'execution_blast_graded_refs': blast_refs,
                                   'execution_phmmer_graded_refs': phmmer_refs},
            'execution_completed': complete, 'results': [], 'acquisitions': [],
            'credit_view': _credit_view(view, parent), 'units_consumed': view.units_consumed}


def internal_summary(view):
    parent = view.parent_input
    if parent['family'] == 'phmmer_graded':
        fetched, closed, gradings, sheets, refs = _phmmer_graded(view, parent)
        graded = any(row['status'] in ('completed', 'partial') for row in gradings)
        return {**_graded(view, parent, fetched=fetched, closed=closed, gradings=gradings, complete=graded,
                          graded_sheets=[], profile_sheets=sheets, blast_refs=[], phmmer_refs=refs),
                'query_ref': parent['query_ref']}
    if parent['family'] == 'blast_graded':
        fetched, closed, graded, gradings = _blast_graded(view, parent)
        refs = [ref for row in graded for ref in (row['source_ref'], row['sheet_refs'][0], row['search_ref'])]
        return _graded(view, parent, fetched=fetched, closed=closed, gradings=gradings, complete=bool(graded),
                       graded_sheets=[{key: value for key, value in row.items()
                                       if key not in ('source_ref', 'search_ref')} for row in graded],
                       profile_sheets=[], blast_refs=refs, phmmer_refs=[])
    return _plain(view, parent)
