"""Where the launch stands, as a pure function of the loop's view (carried from ``internal_summary.py``
``decision_context`` (``execution_assignment`` and ``execution_progress``), ``decision_state.py`` and
``received_record_selection.py``).

The old ``execution_progress`` was this episode's live report facts: the usable handoffs it had received. Here the
received handoffs are the reports of the episode's own child units (``view.outcomes``): a resource has a usable
handoff when its child returned handoff references (``read_from_child``). The resource information, capabilities
and the other context the old summary showed come from the run's settings and services and are added in
``decide``. ``credit.py`` prices exactly these facts."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    parent = view.parent_input
    capabilities, commissions = None, []
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            capabilities = outcome['outcome']
            continue
        report = outcome['report']
        commissions.append({'resource_id': outcome['arguments']['resource_id'], 'slot': report['slot'],
                            'usable_handoff': report['usable_handoff'], 'handoff_refs': report['handoff_refs'],
                            'completed': report['completed'], 'child_credit': report['child_credit']})
    handed_off = {}
    for commission in commissions:
        if commission['usable_handoff']:
            handed_off.setdefault(commission['resource_id'], []).extend(commission['handoff_refs'])
    already = set(parent['already_handed_off_resource_ids'])
    return {
        **parent,
        'capabilities': capabilities,
        'commissions': commissions,
        'handed_off': {resource_id: sorted(set(refs)) for resource_id, refs in sorted(handed_off.items())},
        'new_handoff_resource_ids': sorted(set(handed_off) - already),
        'handoff_refs': sorted({ref for refs in handed_off.values() for ref in refs}),
        'completed': any(commission['completed'] for commission in commissions if commission['usable_handoff']),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
