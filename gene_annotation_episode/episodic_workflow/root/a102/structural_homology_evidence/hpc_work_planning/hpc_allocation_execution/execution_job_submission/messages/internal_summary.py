"""Where the launch stands, as a pure function of the loop's view (carried from ``internal_summary.py``,
``decision_state.py``, ``execution_state.py`` and ``task_state.py``).

The parent input (the assignment's requests, constraints, pinned inputs and the derived eligibility), the progress
facts so far (the resources that newly received a usable handoff, resources already handed off at the start
excluded; their references; whether a handoff is complete) and the controller's yield table. ``credit.py`` prices
those facts."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    start = set(view.parent_input['already_handed_off'])
    handed_off, handoff_refs, result_refs, artifact_refs, completed = [], [], [], [], False
    commissions, capability_reads = [], 0
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            capability_reads += 1
            continue
        report = unit['report']
        resource_id = unit['arguments']['resource_id']
        commissions.append({'resource_id': resource_id, 'slot': unit['slot'],
                            'usable_handoff': bool(report['handoff_refs']), 'completed': report['completed']})
        if report['handoff_refs'] and resource_id not in start and resource_id not in handed_off:
            handed_off.append(resource_id)
        for target, source in ((handoff_refs, 'handoff_refs'), (result_refs, 'result_refs'),
                               (artifact_refs, 'artifact_refs')):
            target.extend(ref for ref in report[source] if ref not in target)
        completed = completed or report['completed']
    state = view.controller_state
    return {**view.parent_input, 'units_consumed': view.units_consumed, 'capability_reads': capability_reads,
            'commissions': commissions, 'handed_off': handed_off, 'handoff_refs': handoff_refs,
            'result_refs': result_refs, 'artifact_refs': artifact_refs, 'completed': completed,
            'progress': {'handed_off': handed_off, 'already_handed_off': sorted(start),
                         'handoff_refs': handoff_refs, 'completed': completed},
            'action_yields': None if state is None else yield_table(state, forecast_unit='handoff')}
