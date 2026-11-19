"""Where the acquisition stands, as a pure function of the loop's view: the original assignment and requested windows,
the retained results (those of this Episode's units and the earlier ones passed in custody), the actions tried and
whether the requested acquisition is complete.

Carried from the old ``internal_summary.py`` (``ResultsInternalSummary.decision_context``: ``execution_assignment``,
``execution_progress``, ``selected_execution_task``), ``receipt_selection.py`` (``_received``: the retained results
among the known records), ``to_parent.py`` (``_live_facts`` for a generic native target) and ``completion.py``
(``_native_results_complete``). The old generic snapshot builder ``results_decision_snapshot`` read the old journal,
the old working state and the old report update (machinery); what it showed the model of the controller is
``action_yields`` (``yield_table``). ``execution_target`` and its description need the job-access service and are
read in ``decide``.

Not carried (machinery): the pinned closed credit view (``closed_credit.py``) and the receipt selection by the old
ledger; the known results are the records the commission named."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

RESULT_PROVIDER = 'episode.execution_result'


def _compact(reference, artifact, body):
    """What credit, completion and the model need of a retained result: the observation and the windows without
    their bytes (``artifact`` is the artifact of the result source, returned with it in custody)."""
    return {'ref': reference, 'artifact_ref': artifact, 'tool_name': body['tool_name'],
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
    """The earlier retained results passed in custody (each source and its artifact were named by the parent)."""
    bodies = []
    for reference in parent_input['initial_result_refs']:
        source = records.get(reference)
        if source.get('provider') != RESULT_PROVIDER:
            continue
        body = json.loads(records.get_artifact(source['artifact_ref']))
        if body['assignment'] != parent_input['assignment']:
            continue
        bodies.append(_compact(reference, source['artifact_ref'], body))
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
            own.append(_compact(outcome['record_refs'][0], outcome['record_refs'][1], outcome['result']))
    bodies = initial + own
    return {
        'assignment': parent_input['assignment'], 'scientific_task': parent_input['scientific_task'],
        'requested': requested,
        'requested_paths': [{'path': path, 'offset': start, 'limit': length}
                            for path, (start, length) in requested.items()],
        'handoff_refs': parent_input['handoff_refs'], 'acquired_record_unit': parent_input['acquired_record_unit'],
        'initial': initial, 'own': own, 'actions': actions,
        'result_refs': sorted(body['ref'] for body in bodies if body['windows']),
        'result_artifact_refs': sorted(body['artifact_ref'] for body in bodies if body['windows']),
        'has_windows': any(body['windows'] for body in bodies),
        'window_count': sum(len(body['windows']) for body in bodies),
        'failure_count': sum(len(body['failures']) for body in bodies),
        'observation_states': [body['observation'] for body in bodies],
        'completed': native_results_complete(bodies, requested),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit'))}
