"""Where the acquisition stands, as a pure function of the loop's view: the original assignment and requested
windows, the retained results (those of this Episode's units and the earlier ones passed in custody), the actions
tried and whether the requested acquisition is complete (old ``decision_context`` and the result reading of
``receipt_selection._received``)."""
import json

RESULT_PROVIDER = 'episode.execution_result'


def compact_result(reference, body):
    """What credit, completion and the model need of a retained result: the observation and the windows without
    their bytes."""
    return {'ref': reference, 'tool_name': body['tool_name'],
            'observation': {'state': body['observation']['state'], 'returncode': body['observation']['returncode']},
            'windows': [{key: window[key] for key in ('path', 'offset', 'returned_bytes', 'size_bytes')}
                        for window in body['windows']],
            'failures': body['failures']}


def native_results_complete(bodies, requested):
    """Library candidate (the old ``_native_results_complete`` of a generic native target): every requested path is
    covered from its start to its end by windows of completed, return code 0 observations."""
    closed = [body for body in bodies
              if body['observation']['state'] == 'completed' and body['observation']['returncode'] == 0]
    if not closed:
        return False
    for path, (start, length) in requested.items():
        windows = [window for body in closed for window in body['windows'] if window['path'] == path]
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


def _initial_bodies(parent_input, records):
    """The earlier retained results passed in custody (each source and its artifact were named by the parent). Only
    the results of the same requested job count (the old ``body['assignment'] != assignment`` skip)."""
    bodies = []
    for reference in parent_input['initial_result_refs']:
        source = records.get(reference)
        if source.get('provider') != RESULT_PROVIDER:
            continue
        body = json.loads(records.get_artifact(source['artifact_ref']))
        if body['handoff_refs'] != parent_input['handoff_refs'] or body['requested'] != parent_input['requested']:
            continue
        bodies.append(compact_result(reference, body))
    return bodies


def internal_summary(view):
    parent_input = view.parent_input
    requested = parent_input['requested']
    initial = _initial_bodies(parent_input, view.records)
    own, actions = [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        actions.append({'tool': unit['tool'], 'arguments': unit['arguments']['operation'],
                        'status': outcome['status'], 'feedback': outcome['feedback']})
        if outcome['status'] == 'completed':
            own.append(compact_result(outcome['record_refs'][0], outcome['result']))
    bodies = initial + own
    summary = {
        'assignment': parent_input['assignment'], 'scientific_task': parent_input['scientific_task'],
        'requested': requested,
        'requested_paths': [{'path': path, 'offset': start, 'limit': length}
                            for path, (start, length) in requested.items()],
        'handoff_refs': parent_input['handoff_refs'], 'acquired_record_unit': parent_input['acquired_record_unit'],
        'initial': initial, 'own': own, 'actions': actions,
        'result_refs': sorted(body['ref'] for body in bodies if body['windows']),
        'has_windows': any(body['windows'] for body in bodies),
        'window_count': sum(len(body['windows']) for body in bodies),
        'failure_count': sum(len(body['failures']) for body in bodies),
        'observation_states': [body['observation'] for body in bodies],
        'completed': native_results_complete(bodies, requested)}
    if view.controller_state is not None:
        summary['controller'] = view.controller_state.as_record()
    return summary
