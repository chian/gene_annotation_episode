"""Where the acquisition stands, as a pure function of the view: the assignment and its target, every result
acquisition known (the initial results the parent passed, read through the held records, and the acquisitions of the
units so far, each tool outcome carrying its body and the references of its retained copy), the progress facts
for a native byte target, whether the requested acquisition is complete, the selected execution task
(when the parent supplied the scientific task) and the controller's yield table.

Old ``ResultsInternalSummary.decision_context`` (execution_assignment, execution_progress = ``facts``,
execution_target, selected_execution_task), ``ResultsReceiptSelection._received``,
``ResultsResultPublication._read_result`` and ``ResultsCompletion._native_results_complete``. The target description of
the old progress provider (``describe_target``), the resource information of the configuration and the received
BV-BRC / BLAST job values of the initial context are in no place now and are not shown."""
import json
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

RESULT_PROVIDER = 'episode.execution_result'
RESULT_TOOLS = ('execution_results_status', 'execution_results_collect', 'execution_results_read')
# Results of the typed native families are bundles, read by their own (unplaced) classes: not generic windows.
BUNDLE_VERSIONS = ('native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1',
                   'native_blast_bundle_v1', 'native_blast_database_bundle_v1',
                   'native_blast_standard_database_bundle_v1', 'native_hmmer_preparation_bundle_v1')
SUPPORTED_NATIVE_JOBS = ('native_blast', 'native_blast_masking', 'native_blast_utility', 'native_blast_database',
                         'native_blast_standard_database', 'native_hmmer', 'native_hmmer_preparation')


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
    """The old ``selected_execution_task_v1`` of the decision context (``_with_selected_execution_task``): present only
    when the parent supplied the scientific task; an API request only for the HMMER service; a native request only when
    it names exactly one supported native job. The resource information of the old configuration is not in the
    summary."""
    task = parent.get('scientific_task')
    if task is None:
        return None
    target = parent['target']
    request = target['assignment']
    if target['resource_kind'] == 'api':
        if request.get('service') != 'ebi_hmmer':
            return None
        job = deepcopy(request)
    else:
        jobs = request.get('requested_job', {})
        chosen = [name for name in SUPPORTED_NATIVE_JOBS if isinstance(jobs.get(name), dict)]
        if len(chosen) != 1:
            return None
        if chosen[0] in ('native_hmmer', 'native_hmmer_preparation'):
            raise NotImplementedError('unplaced:native_profile_scientific_job_view')
        job = deepcopy(jobs[chosen[0]])
    return deepcopy({'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
                     'selected_tool_info': task['selected_tool_info'],
                     'requests': [{'resource_id': target['resource_id'], 'resource_kind': target['resource_kind'],
                                   'endpoint': request.get('endpoint'), 'constraints': request.get('constraints', {}),
                                   'job': job}],
                     'constraints': parent['assignment'].get('constraints', {}), 'selector': parent['selector']})


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
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
                'execution_completed': complete}
    controller = view.controller_state
    return {'assignment': assignment, 'target': parent['target'], 'family': parent['family'],
            'requested': parent['requested'], 'acquired_record_unit': parent['acquired_record_unit'],
            'initial_result_refs': parent['initial_result_refs'], 'results': results, 'acquisitions': acquisitions,
            'execution_progress': progress, 'execution_completed': complete,
            'selected_execution_task': _selected_execution_task(parent),
            'controller': None if controller is None else yield_table(controller, forecast_unit='acquired record credit'),
            'units_consumed': view.units_consumed}
