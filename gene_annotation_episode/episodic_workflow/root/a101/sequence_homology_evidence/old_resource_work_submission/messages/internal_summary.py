"""Where the episode stands, as a pure function of the loop's view (carried from the old ``internal_summary.py``
(``OperationalSummary.decision_context``: ``role``, ``assignment``), the facts of ``to_parent.py``
(``OperationalReport.facts``) and the general fields of ``decision_state.py`` and ``task_state.py`` that a resource
launch episode used).

The old facts merged what every adapter recorded: the handoffs de-duplicated by (``capability_binding_ref``,
``execution_handle``) and in identity order, ``execution_handoff`` the single one when exactly one identity is known,
and the adapters' other facts. Here the handoffs are the ones the resource children returned (``view.outcomes`` child
reports) and the ones this episode's own ``resource_check_handoff`` unit returned (an assumption about the adapter
reply, as in the sibling resource episodes: a handoff is ``result['execution_handoff']`` of the reply). A handoff
whose state is not ``usable`` is counted as an unavailable check and is not a fact; for each identity the usable check
with the latest ``checked_at`` is kept. The capabilities and the duration estimates shown to the model come from the
resource adapter service and are added in ``decide``; the capabilities the model last read are kept here. The typed
reasoning schema is the Store's (``records.reasoning_schema()`` reads no record)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

COMPLETED = ('completed', 'partial')


def identity(handoff):
    return (handoff['resource_selection']['capability_binding_ref'], handoff['execution_handle'])


def internal_summary(view):
    parent = view.parent_input
    capabilities, calls, commissions, reasonings = None, [], [], []
    latest, unavailable, handoff_refs, adapter_facts, last = {}, 0, [], {}, None

    def note(handoff):
        nonlocal unavailable
        if handoff['state'] != 'usable':
            unavailable += 1
            return
        current = latest.get(identity(handoff))
        if current is None or handoff['checked_at'] >= current['checked_at']:
            latest[identity(handoff)] = handoff

    for index, unit in enumerate(view.outcomes):
        if unit['kind'] == 'child':
            report = last = unit['report']
            commissions.append({'index': index, 'slot': unit['slot'],
                                'resource_id': unit['arguments']['resource_selection']['resource_id'],
                                'credit': report['credit'], 'finding': report['finding'],
                                'handoff_count': len(report['execution_handoffs'])})
            for handoff in report['execution_handoffs']:
                note(handoff)
            handoff_refs.extend(report['handoff_refs'])
            adapter_facts.update({name: value for name, value in report['adapter_facts'].items() if value is not None})
            continue
        outcome = last = unit['outcome']
        status = outcome.get('status')
        if unit['tool'] == 'resource_capabilities':
            capabilities = outcome['result']['capabilities']
        elif unit['tool'] == 'reason':
            reasonings.append({'index': index, 'outcome': outcome})
        elif unit['tool'] == 'resource_check_handoff':
            handoff = (outcome.get('result') or {}).get('execution_handoff')
            if handoff is not None:
                note(handoff)
        calls.append({'index': index, 'tool': unit['tool'], 'arguments': unit['arguments'], 'status': status,
                      'feedback': outcome.get('feedback')})
    ordered = [latest[key] for key in sorted(latest)]
    return {
        'role': 'launch',
        'assignment': parent['assignment'],
        'scope': parent['scope'],
        'scope_refs': parent['scope_refs'],
        'input_refs': parent['input_refs'],
        'completion_target': parent['completion_target'],
        'message': parent['message'],
        'capabilities': capabilities,
        'calls': calls,
        'commissions': commissions,
        'reasonings': reasonings,
        'last_outcome': last,
        'execution_handoffs': ordered,
        'execution_handoff': ordered[0] if len(ordered) == 1 else None,
        'handoff_refs': list(dict.fromkeys(handoff_refs)),
        'adapter_facts': adapter_facts,
        'unavailable_checks': unavailable,
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
