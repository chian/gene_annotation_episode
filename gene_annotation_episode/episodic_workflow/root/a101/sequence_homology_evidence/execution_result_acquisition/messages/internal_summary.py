"""Where the acquisition stands, as a pure function of the view: the assignment and its target, every result
acquisition known (the initial results the parent passed, read through the held records, and the acquisitions of the
units so far, each tool outcome carrying its body and the references of its retained copy), the facts of the old
``_live_facts`` for a native byte target, whether the requested acquisition is complete, the selected execution task
(when the parent supplied the scientific task) and the controller's yield table.

Old ``OperationalSummary.decision_context`` (execution_assignment, execution_progress = ``facts``, execution_target,
selected_execution_task), ``ReceivedOperationalEvidence._received`` and ``OperationalResultAcquisition._read_result``
and ``_native_results_complete``. The target description of the old progress provider (``describe_target``) is in no
place now and is not shown."""
import json
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.blast_database_features import (
    saved_grading_features)
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.hmmer_search_features import (
    saved_hit_features)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

RESULT_PROVIDER = 'episode.execution_result'
RESULT_TOOLS = ('execution_results_status', 'execution_results_collect', 'execution_results_read')
# Results of the typed native families are bundles, read by their own (unplaced) classes: not generic windows.
BUNDLE_VERSIONS = ('native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1',
                   'native_blast_bundle_v1', 'native_blast_database_bundle_v1',
                   'native_blast_standard_database_bundle_v1', 'native_hmmer_preparation_bundle_v1')
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation')
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}


def _compact(ref, body, initial):
    """What credit, completion and the facts need of one acquisition: its windows without their bytes."""
    return {'ref': ref, 'initial': initial, 'state': body['observation']['state'],
            'returncode': body['observation']['returncode'],
            'windows': [{key: window[key] for key in ('path', 'offset', 'returned_bytes', 'size_bytes')}
                        for window in body['windows']],
            'failures': deepcopy(body['failures'])}


def _initial_result(records, ref, assignment):
    """One earlier result acquisition of this handoff the parent passed (old ``_read_result``); a bundle of a typed
    family, or a result of another assignment, is not a generic window (old ``_received``)."""
    source = records.get(ref)
    if source.get('provider') != RESULT_PROVIDER:
        raise ValueError('execution_initial_result_not_an_execution_result')
    if source.get('version') in BUNDLE_VERSIONS:
        return None
    body = json.loads(records.get_artifact(source['artifact_ref']))
    return body if body['assignment'] == assignment else None


def _native_results_complete(parent, results):
    """The old ``_native_results_complete`` of a native byte target: a completed attempt with return code 0 and every
    requested window covered by the windows of the closed observations."""
    if not results:
        return False
    closed = [result for result in results if result['state'] == 'completed' and result['returncode'] == 0]
    if not closed:
        return False
    for path, (start, length) in parent['requested'].items():
        windows = [window for result in closed for window in result['windows'] if window['path'] == path]
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


def _selected_execution_task(parent):
    """The old ``selected_execution_task_v1`` of the decision context: present only when the parent supplied the
    scientific task and the request names exactly one supported native job (the resource information of the old
    configuration is not in the summary)."""
    task = parent.get('scientific_task')
    if task is None:
        return None
    target = parent['target']
    if target['resource_kind'] == 'api':
        raise NotImplementedError('unplaced:api_execution.selected_execution_task')
    request = target['assignment']
    jobs = request.get('requested_job', {})
    chosen = [name for name in SUPPORTED_NATIVE_JOBS if isinstance(jobs.get(name), dict)]
    if len(chosen) != 1:
        return None
    if chosen[0] in ('native_hmmer', 'native_hmmer_preparation'):
        raise NotImplementedError('unplaced:native_profile_scientific_job_view')
    return deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
                     'selected_tool_info': task['selected_tool_info'],
                     'requests': [{'resource_id': target['resource_id'], 'resource_kind': target['resource_kind'],
                                   'endpoint': request.get('endpoint'), 'constraints': request.get('constraints', {}),
                                   'job': jobs[chosen[0]]}],
                     'constraints': parent['assignment'].get('constraints', {}), 'selector': parent['selector']})


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


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    if parent['family'] == 'phmmer_graded':
        fetched, closed, gradings, sheets, refs = _phmmer_graded(view, parent)
        held = view.records.holds(assignment['handoff_ref'])
        graded = any(row['status'] in ('completed', 'partial') for row in gradings)
        controller = view.controller_state
        return {'assignment': assignment, 'target': parent['target'], 'family': parent['family'],
                'selector': parent['selector'], 'query_ref': parent['query_ref'],
                'acquired_record_unit': parent['acquired_record_unit'],
                'initial_result_refs': parent['initial_result_refs'], 'fetched_results': fetched,
                'fetch_offered': held and not closed, 'gradings': gradings, 'graded_sheets': [],
                'profile_sheets': sheets,
                'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']] if held else [],
                                       'execution_result_refs': [], 'execution_file_source_refs': [],
                                       'execution_file_capture_outcomes': [], 'execution_result_origin': None,
                                       'execution_completed': graded, 'execution_blast_graded_refs': [],
                                       'execution_phmmer_graded_refs': refs},
                'execution_completed': graded, 'results': [], 'acquisitions': [],
                'selected_execution_task': None,
                'controller': None if controller is None else yield_table(controller,
                                                                          forecast_unit='graded result credit'),
                'units_consumed': view.units_consumed}
    if parent['family'] == 'blast_graded':
        fetched, closed, graded, gradings = _blast_graded(view, parent)
        held = view.records.holds(assignment['handoff_ref'])
        refs = [ref for row in graded for ref in (row['source_ref'], row['sheet_refs'][0], row['search_ref'])]
        controller = view.controller_state
        return {'assignment': assignment, 'target': parent['target'], 'family': parent['family'],
                'selector': parent['selector'], 'acquired_record_unit': parent['acquired_record_unit'],
                'initial_result_refs': parent['initial_result_refs'], 'fetched_results': fetched,
                'fetch_offered': held and not closed, 'gradings': gradings,
                'profile_sheets': [],
                'graded_sheets': [{key: value for key, value in row.items() if key not in ('source_ref', 'search_ref')}
                                  for row in graded],
                'execution_progress': {'execution_handoff_refs': [assignment['handoff_ref']] if held else [],
                                       'execution_result_refs': [], 'execution_file_source_refs': [],
                                       'execution_file_capture_outcomes': [], 'execution_result_origin': None,
                                       'execution_completed': bool(graded), 'execution_blast_graded_refs': refs,
                                       'execution_phmmer_graded_refs': []},
                'execution_completed': bool(graded), 'results': [], 'acquisitions': [],
                'selected_execution_task': None,
                'controller': None if controller is None else yield_table(controller,
                                                                          forecast_unit='graded result credit'),
                'units_consumed': view.units_consumed}
    results, acquisitions = [], []
    if parent['family'] == 'native_bytes':
        for ref in parent['initial_result_refs']:
            body = _initial_result(view.records, ref, assignment)
            if body is not None:
                results.append(_compact(ref, body, True))
        for unit in view.outcomes:
            if unit['tool'] not in RESULT_TOOLS:
                continue
            outcome = unit['outcome']
            row = {'tool': unit['tool'], 'arguments': unit['arguments']['arguments'], 'status': outcome['status']}
            if outcome['status'] == 'completed':
                ref = outcome['record_refs'][0]
                result = _compact(ref, outcome['result'], False)
                results.append(result)
                row.update({'source_ref': ref, 'artifact_ref': outcome['artifact_ref'], 'windows': result['windows'],
                            'failures': result['failures'], 'attempt_state': result['state']})
            else:
                row['feedback'] = outcome['feedback']
            acquisitions.append(row)
    complete = parent['family'] == 'native_bytes' and _native_results_complete(parent, results)
    held = view.records.holds(assignment['handoff_ref'])
    with_windows = sorted(result['ref'] for result in results if result['windows'])
    progress = {'execution_handoff_refs': [assignment['handoff_ref']] if held else [],
                'execution_result_refs': with_windows, 'execution_file_source_refs': [],
                'execution_file_capture_outcomes': [],
                'execution_result_origin': deepcopy(NATIVE_RESULT_ORIGIN) if with_windows else None,
                'execution_completed': complete, 'execution_blast_graded_refs': [],
                     'execution_phmmer_graded_refs': []}
    controller = view.controller_state
    return {'assignment': assignment, 'target': parent['target'], 'family': parent['family'],
            'requested': parent['requested'], 'acquired_record_unit': parent['acquired_record_unit'],
            'initial_result_refs': parent['initial_result_refs'], 'results': results, 'acquisitions': acquisitions,
            'execution_progress': progress, 'execution_completed': complete,
            'selected_execution_task': _selected_execution_task(parent), 'graded_sheets': [], 'profile_sheets': [],
            'controller': None if controller is None else yield_table(controller, forecast_unit='acquired record credit'),
            'units_consumed': view.units_consumed}
