"""Where the acquisition stands, as a pure function of the loop's view: the assignment, the result records acquired
so far (the episode's own units and the known results the parent passed), the facts the old report derived from
them, the acquired target and whether the requested paths are completely acquired.

Carried from the old ``internal_summary.py`` (``decision_context``: ``execution_assignment``,
``execution_progress`` = the facts, ``execution_target``), ``received_record_selection.py`` (``_received``: the
results among the records the episode knew, those of another assignment skipped), ``to_parent.py``
(``_live_facts``) and ``completion.py`` (``_native_results_complete``). The old summary shows the target from the
first decision (read through the handoff and described by the job-progress provider, which has no home in the
library and whose read of the handoff is BLOCKED-ON-JOB-SERVICE); here the target is shown from the first result a
unit acquired (``None`` before). ``selected_execution_task`` (local protein-structure targets only) and
``execution_target_description`` are not carried: they come from the protein-structure library and the provider.

Not carried (machinery): the pinned closed credit view (``closed_credit.py``) and the old receipt selection
(``_selection``): the known results are the records the commission named, and the credit the controller last saw is
handed to ``final_to_parent``."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

RESULT_VERSION = 'execution_result_information_v3'
NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}
CREDIT_BINDING_VERSION = 'execution_received_selector_coverage_credit_v2'


def _entry(ref, body, initial):
    return {'ref': ref, 'initial': initial, 'failures': len(body['failures']),
            'observation': {'state': body['observation']['state'], 'returncode': body['observation']['returncode']},
            'windows': [{'path': window['path'], 'offset': window['offset'], 'returned_bytes': window['returned_bytes'],
                         'size_bytes': window['size_bytes']} for window in body['windows']]}


def uncovered_paths(requested, results):
    """The requested paths that are not completely acquired: the old ``_native_results_complete`` over the
    results of a successful (completed, return code 0) exact attempt observation; a path whose requested interval
    is read without a gap from its start to the end of the file (or of the interval) is covered."""
    closed = [item for item in results
              if item['observation']['state'] == 'completed' and item['observation']['returncode'] == 0]
    missing = []
    for path, (start, length) in requested.items():
        windows = [window for item in closed for window in item['windows'] if window['path'] == path]
        if not windows:
            missing.append(path)
            continue
        end = max(window['size_bytes'] for window in windows)
        if length is not None:
            end = min(end, start + length)
        cursor, covered = start, True
        for window in sorted(windows, key=lambda item: item['offset']):
            if window['offset'] > cursor:
                covered = False
                break
            cursor = max(cursor, window['offset'] + window['returned_bytes'])
        if not covered or cursor < end:
            missing.append(path)
    return missing


def facts(assignment, results, target):
    """The old ``_live_facts`` for a native target: the handoff and result references, the origin and the
    completion. The file-source, capture-outcome and protein-structure facts are empty (their selectors are not
    carried); ``execution_result_origin`` is the empty record where the old value was ``null``."""
    with_windows = sorted(item['ref'] for item in results if item['windows'])
    return {'execution_handoff_refs': [] if target is None else [assignment['handoff_ref']],
            'execution_result_refs': with_windows,
            'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
            'execution_protein_structure_projections': [], 'execution_protein_structure_saved_sheets': [],
            'execution_protein_structure_sequences': [], 'execution_protein_structure_failures': [],
            'execution_result_origin': dict(NATIVE_RESULT_ORIGIN) if with_windows else {}}


def internal_summary(view):
    parent = view.parent_input
    assignment, requested = parent['assignment'], parent['requested']
    results = []
    for ref in parent['known_result_refs']:
        body = json.loads(view.records.get_artifact(ref))
        if body['version'] != RESULT_VERSION:
            raise ValueError('invalid_execution_result_information')
        if body['assignment'] == assignment:
            results.append(_entry(ref, body, True))
    target = None
    last = None
    for outcome in view.outcomes:
        last = outcome
        returned = outcome['outcome']
        if returned['status'] == 'completed':
            body = returned['result']
            results.append(_entry(returned['record_refs'][0], body, False))
            target = body['target']
    missing = uncovered_paths(requested, results)
    completed = not missing
    return {
        'assignment': assignment,
        'requested': requested,
        'message': parent['message'],
        'acquired_record_unit': parent['acquired_record_unit'],
        'credit_binding': {'version': CREDIT_BINDING_VERSION, 'acquired_record_unit': parent['acquired_record_unit'],
                           'qualification': 'original_selector_byte_position_union_current_filesystem_version_unverified'},
        'results': results,
        'target': target,
        'uncovered_paths': missing,
        'completed': completed,
        'facts': {**facts(assignment, results, target), 'execution_completed': completed},
        'last_outcome': None if last is None else {'tool': last['tool'], 'arguments': last['arguments'].get('window'),
                                                    'outcome': last['outcome']},
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
