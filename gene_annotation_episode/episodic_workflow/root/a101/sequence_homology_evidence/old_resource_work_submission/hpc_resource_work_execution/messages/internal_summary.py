"""Where the episode stands, as a pure function of the loop's view.

Carried from the old ``OperationalSummary.decision_context`` (``role``, ``assignment``) and from the facts of the
old ``OperationalReport.facts`` (``execution_handoff``, ``execution_handoffs``): the capabilities and the handoff
checks are read from the unit outcomes of this Episode's own tools, where the old report asked the adapter for
them. A handoff is an ``execution_handoff_v1`` record the resource adapter returned under
``result['execution_handoff']`` of one tool reply (an assumption about the adapter's reply: see the blocked file).
Handoffs are de-duplicated by (``capability_binding_ref``, ``execution_handle``), the usable check with the latest
``checked_at`` is kept for each, and they are ordered by that identity (the old ``facts``). The capabilities shown
to the model, the estimates and the tool catalogue come from the adapter service and are added in ``decide``."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

COMPLETED = ('completed', 'partial')


def identity(handoff):
    return (handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle'])


def internal_summary(view):
    parent = view.parent_input
    capabilities, calls, latest, unavailable, last = None, [], {}, 0, None
    for index, unit in enumerate(view.outcomes):
        if unit['kind'] != 'tool' or unit['tool'] == 'reason':
            continue
        outcome = last = unit['outcome']
        if unit['tool'] == 'resource_capabilities':
            capabilities = outcome['result']['capabilities']
        calls.append({'index': index, 'tool': unit['arguments'].get('tool_name', 'resource.capabilities'),
                      'arguments': unit['arguments'].get('tool_arguments', {}), 'status': outcome['status'],
                      'feedback': outcome['feedback'], 'reply_ref': outcome.get('reply_ref')})
        handoff = (outcome['result'] or {}).get('execution_handoff') if unit['tool'] == 'adapter_tool' else None
        if handoff is None:
            continue
        if handoff['state'] != 'usable':
            unavailable += 1
            continue
        current = latest.get(identity(handoff))
        if current is None or handoff['checked_at'] >= current[0]['checked_at']:
            latest[identity(handoff)] = (handoff, outcome['reply_ref'])
    ordered = [latest[key] for key in sorted(latest)]
    selection = parent['assignment']['resource_selection']
    availability = next((item['availability'] for item in capabilities or ()
                         if item['resource_id'] == selection['resource_id']), 'not_read')
    return {
        'role': 'launch_hpc',
        'assignment': parent['assignment'],
        'input_refs': parent['input_refs'],
        'reasoning_schema': view.records.reasoning_schema(),
        'message': parent['message'],
        'capabilities': capabilities,
        'availability': availability,
        'calls': calls,
        'last_outcome': last,
        'execution_handoffs': [handoff for handoff, _ in ordered],
        'execution_handoff': ordered[0][0] if len(ordered) == 1 else None,
        'handoff_refs': sorted({ref for _, ref in ordered}),
        'unavailable_checks': unavailable,
        'failed_calls': sum(call['status'] not in COMPLETED for call in calls),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
