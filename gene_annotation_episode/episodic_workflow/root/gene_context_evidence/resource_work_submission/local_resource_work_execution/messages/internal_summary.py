"""Where the episode stands, as a pure function of the view (old ``internal_summary.py`` ``decision_context``, the
general fields of ``decision_state.py`` that a resource episode used, and the state ``task_state.py`` kept).

The old own fields: ``role``, ``assignment`` (the admitted launch assignment, in full), ``resource_capabilities``
(every declared capability) and ``resource_tool_estimates`` (the selected adapter's duration information; that
one is a service read, made in ``decide``). The old general fields kept here: the current credit, the controller
state, the last outcome, the feedback of a failed unit and the completed-action reports (the old
``request_context`` lookups of the episode's own earlier attempts are this list). The adapter's recorded state
(its facts, its credit) comes from what the operating tool returned in its outcome."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

OPERATION = 'resource_operation'
PREPARE = 'prepare_resource_assignment'
CAPABILITIES = 'resource_capabilities'


def internal_summary(view):
    parent = view.parent_input
    summary = {'role': 'launch_local', 'assignment': parent['assignment'], 'prepared': False,
               'scope': parent['scope'], 'scope_refs': parent['scope_refs'], 'input_refs': parent['input_refs'],
               'completion_target': parent['completion_target'], 'message': parent['message'],
               'capabilities': None, 'facts': {}, 'handoff_refs': [], 'adapter_credit': None, 'feedback': None,
               'last_local_outcome': None, 'completed_action_reports': [],
               'action_yields': (None if view.controller_state is None
                                 else yield_table(view.controller_state, forecast_unit='credit'))}
    for index, unit in enumerate(view.outcomes):
        tool, outcome = unit['tool'], unit['outcome']
        if tool == PREPARE:
            summary.update(assignment=outcome['assignment'], prepared=True, capabilities=outcome['capabilities'])
        elif tool == CAPABILITIES:
            summary['capabilities'] = outcome['result']['capabilities']
        elif tool == OPERATION:
            summary.update(facts=outcome['facts'], adapter_credit=outcome['adapter_credit'])
            summary['handoff_refs'] = list(dict.fromkeys([*summary['handoff_refs'], *outcome['handoff_refs']]))
        status = outcome['status']
        summary['feedback'] = (None if status in ('completed', 'partial') else
                               outcome.get('feedback') or {'status': status,
                                                           'category': outcome.get('error_code', 'work_failed')})
        shown = {name: value for name, value in unit['arguments'].items() if name not in ('assignment', 'held_refs')}
        summary['last_local_outcome'] = {'index': index, 'tool': tool, 'selected': shown, 'status': status,
                                         'result': outcome.get('result'), 'feedback': outcome.get('feedback')}
        summary['completed_action_reports'].append(summary['last_local_outcome'])
    return summary
