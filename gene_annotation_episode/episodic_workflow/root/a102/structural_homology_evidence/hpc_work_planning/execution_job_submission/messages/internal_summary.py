"""Where the episode stands, as a pure function of the loop's view (carried from the old ``internal_summary.py``,
``decision_state.py``, ``received_record_selection.py`` and ``received_records.py``).

The old ``decision_context`` was ``execution_assignment`` (the commission) and ``execution_progress`` (the live
report facts: the usable handoffs the episode received). Here the received handoffs are the reports of the
episode's own child units (``view.outcomes``): a resource has a usable handoff when its child returned handoff
references. The resource information and capabilities the old summary showed come from the run's settings and are
added in ``decide``; the old ``selected_execution_task`` (an all-local native protein-structure commission with a
scientific parent task) is built there too, from ``scientific_task``.

The old ``received_record_selection`` read each received handoff record to learn its target (resource id) and its
usability from the old progress provider. There is no handoff-record library yet, so the resource id is the one
this episode commissioned and the usability is the child's own return (see the carry-over record)."""
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
                            'handoff_refs': report['handoff_refs'], 'completed': report['completed'],
                            'finding': report['finding']})
    handed_off = {}
    for commission in commissions:
        if commission['handoff_refs']:
            handed_off.setdefault(commission['resource_id'], []).extend(commission['handoff_refs'])
    already = set(parent['already_handed_off_resource_ids'])
    return {
        **parent,
        'capabilities': capabilities,
        'commissions': commissions,
        'handed_off': {resource_id: sorted(set(refs)) for resource_id, refs in sorted(handed_off.items())},
        'new_handoff_resource_ids': sorted(set(handed_off) - already),
        'handoff_refs': sorted({ref for refs in handed_off.values() for ref in refs}),
        'completed': any(commission['completed'] for commission in commissions),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
