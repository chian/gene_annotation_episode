"""Where the launch stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py`` and ``received_record_selection.py``: what the old code showed of the received handoffs).

The parent input (the assignment's requests, constraints, pinned inputs and the derived permitted requests), the
progress so far (the resources that newly received a usable handoff, resources already handed off when the
commission began left out; the handoff references the children returned; whether a handoff is complete) and the
controller's yield table. ``credit.py`` prices exactly these facts."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    start = set(view.parent_input['already_handed_off'])
    handed_off, handoff_refs, commissions, capabilities, capability_reads, completed = [], [], [], None, 0, False
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            capability_reads += 1
            capabilities = unit['outcome']
            continue
        report = unit['report']
        resource_id = unit['arguments']['resource_id']
        commissions.append({'resource_id': resource_id, 'slot': unit['slot'],
                            'usable_handoff': report['usable_handoff'], 'completed': report['completed'],
                            'qualification': report['qualification']})
        if report['usable_handoff'] and resource_id not in start and resource_id not in handed_off:
            handed_off.append(resource_id)
        handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
        completed = completed or report['completed']
    state = view.controller_state
    return {**view.parent_input, 'units_consumed': view.units_consumed, 'capability_reads': capability_reads,
            'capabilities': capabilities, 'commissions': commissions, 'handed_off': handed_off,
            'handoff_refs': handoff_refs, 'completed': completed,
            'progress': {'handed_off': handed_off, 'already_handed_off': sorted(start),
                         'handoff_refs': handoff_refs, 'completed': completed},
            'action_yields': None if state is None else yield_table(state, forecast_unit='handoff')}
