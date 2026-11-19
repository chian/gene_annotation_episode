"""Where the episode stands, as a pure function of the view (old ``internal_summary.py`` ``decision_context``, the
general fields of ``decision_state.py`` that a resource episode used, and the state ``task_state.py`` kept).

The old own fields: ``role`` (``launch``), ``assignment`` (the admitted launch assignment, in full),
``resource_capabilities`` (every declared capability; read from the resource adapter service in ``decide``, as the
old context read them) and ``resource_tool_estimates`` (every adapter's duration information; a service read made
in ``decide``). The old general fields kept here: the current credit, the controller state, the last outcome, the
feedback of a failed unit and the completed-action reports (the old ``request_context`` lookups of the episode's
own earlier attempts are this list). The adapters' recorded state (their facts, their credit) comes from what the
operating tools returned in their outcomes; the execution handoffs of the resource children come from the child
reports."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

CHECK = 'resource_check_handoff'
RESOURCE_TOOLS = ('resource_capabilities', 'resource_inspect', CHECK)


def internal_summary(view):
    parent = view.parent_input
    summary = {'role': 'launch', 'assignment': parent['assignment'],
               'adapter_assignment': parent['adapter_assignment'], 'scope': parent['scope'],
               'scope_refs': parent['scope_refs'], 'input_refs': parent['input_refs'],
               'completion_target': parent['completion_target'], 'message': parent['message'],
               'adapter_facts': {}, 'child_handoffs': [], 'handoff_refs': [], 'commissions': [],
               'adapter_credit': None, 'feedback': None, 'last_local_outcome': None,
               'completed_action_reports': [],
               'action_yields': (None if view.controller_state is None
                                 else yield_table(view.controller_state, forecast_unit='credit'))}
    for index, unit in enumerate(view.outcomes):
        if unit['kind'] == 'child':
            result, report = unit['result'], unit['report']
            summary['commissions'].append({'slot': unit['slot'], 'finding': result['finding'],
                                           'usable_handoffs': [item for item in report['execution_handoffs']
                                                               if item['state'] == 'usable']})
            summary['child_handoffs'].extend(report['execution_handoffs'])
            summary['handoff_refs'] = list(dict.fromkeys([*summary['handoff_refs'], *report['handoff_refs']]))
            summary['adapter_facts'] = {**summary['adapter_facts'], **report['adapter_facts']}
            status, shown_result, feedback = 'completed', {'finding': result['finding']}, None
            name, shown = unit['slot'], unit['arguments']
        else:
            name, outcome = unit['tool'], unit['outcome']
            status, shown_result, feedback = outcome['status'], outcome.get('result'), outcome.get('feedback')
            if name in RESOURCE_TOOLS:
                summary['adapter_credit'] = outcome['adapter_credit']
            if name == CHECK:
                summary['adapter_facts'] = outcome['facts']
                summary['handoff_refs'] = list(dict.fromkeys([*summary['handoff_refs'], *outcome['handoff_refs']]))
            shown = {key: value for key, value in unit['arguments'].items()
                     if key not in ('assignment', 'held_refs')}
        summary['feedback'] = (None if status in ('completed', 'partial') else
                               feedback or {'status': status, 'category': 'work_failed'})
        summary['last_local_outcome'] = {'index': index, 'tool': name, 'selected': shown, 'status': status,
                                         'result': shown_result, 'feedback': feedback}
        summary['completed_action_reports'].append(summary['last_local_outcome'])
    return summary
