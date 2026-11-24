"""Where the acquisition stands: a pure function of the view, carried from the old ``internal_summary.py``
(``ResultsInternalSummary.decision_context``: ``execution_assignment``, ``execution_progress`` (= the facts)),
``completion.py`` (``_native_results_complete``) and ``to_parent.py`` (``_live_facts``).

The results are the bodies of this episode's own completed tool outcomes, in order (the old ``_received`` read
them back from the Store by reference). The target and its description (``execution_target``,
``execution_target_description``) are a recorded read of the job service in ``decide`` (``task.py``). Not carried:
the selected execution task of flux balance work (``_with_selected_execution_task``, ``scientific_parent_task``),
the compact flux balance assignment views, the local file source view, and the shared state fields of
``results_decision_snapshot`` that came from the old runner (working state, pending work, report lifecycle,
journal views, ``local_outcome_preview`` and the recorded visual evidence)."""
from yield_control import YieldState

from ..credit import credit_binding, selector_progress

NATIVE_RESULT_ORIGIN = {'content_location': 'current_resource_filesystem', 'attempt_output_version': 'unverified',
                        'window_consistency': 'separate_reads_no_atomic_file_snapshot',
                        'completion_basis': 'requested_acquisition_and_observed_successful_attempt'}


def native_results_complete(requested, bodies):
    """Every requested window of every path is covered by windows of completed, return-code-0 observations
    (the old ``_native_results_complete``)."""
    closed = [body for body in bodies
              if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
    if not closed:
        return False
    for row in requested:
        windows = [window for body in closed for window in body['windows'] if window['path'] == row['path']]
        if not windows:
            return False
        start, length = row['start'], row['length']
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


def facts(summary):
    """The recorded facts of the old ``_live_facts`` (native, no local file source, no flux balance)."""
    bodies = summary['results']
    return {'execution_handoff_refs': sorted(summary['handoff_refs']),
            'execution_result_refs': sorted(ref for ref, body in zip(summary['result_refs'], bodies)
                                            if body['windows']),
            'execution_file_source_refs': sorted({row['source_ref'] for body in bodies
                                                  for row in body.get('captured_files', [])
                                                  if row['source_ref'] is not None}),
            'execution_file_capture_outcomes': [],
            'execution_result_origin': dict(NATIVE_RESULT_ORIGIN) if any(body['windows'] for body in bodies)
            else None,
            'execution_completed': native_results_complete(summary['windows'], bodies)}


def _preview(outcome):
    """The last outcome as the model sees it: its status, feedback, references and the shape of each window."""
    if outcome is None:
        return None
    result = outcome['outcome']
    body = result['result']
    shown = None if body is None else {
        'observation': body['observation'], 'failures': body['failures'],
        'windows': [{key: window[key] for key in ('path', 'offset', 'returned_bytes', 'size_bytes')}
                    for window in body['windows']]}
    return {'tool': outcome['tool'], 'status': result['status'], 'record_refs': result['record_refs'],
            'feedback': result['feedback'], 'result': shown}


def internal_summary(view):
    parent = view.parent_input
    results, result_refs, artifact_refs = [], [], []
    last = None
    for outcome in view.outcomes:
        last = outcome
        result = outcome['outcome']
        if result['status'] == 'completed':
            results.append(result['result'])
            result_refs.extend(result['record_refs'])
            artifact_refs.extend(result['artifact_refs'])
    controller = view.controller_state.as_record() if isinstance(view.controller_state, YieldState) else None
    summary = {**parent, 'results': results, 'result_refs': result_refs,
               'result_artifact_refs': list(dict.fromkeys(artifact_refs)),
               'acquired_selector_fraction': selector_progress(parent['windows'], results),
               'controller': controller,
               'current_credit': None if controller is None else controller['current_credit']}
    summary['credit_binding'] = credit_binding(summary)
    summary['execution_progress'] = facts(summary)
    summary['execution_assignment'] = {key: parent[key] for key in ('handoff_refs', 'selector', 'constraints')}
    summary['last_local_outcome'] = _preview(last)
    summary['goal'] = {'objective': view.goal.objective, 'selector': parent['selector']}
    return summary
