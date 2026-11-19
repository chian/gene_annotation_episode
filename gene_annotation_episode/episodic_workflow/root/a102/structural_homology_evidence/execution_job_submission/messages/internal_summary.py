"""Where the episode stands, as a pure function of the loop's view (carried from the old ``internal_summary.py``
(``decision_context``), ``decision_state.py``, ``execution_state.py`` and ``received_record_selection.py``
(``_received``)).

The old ``decision_context`` was ``execution_assignment`` (the commission) and ``execution_progress`` (the live
report facts: the usable handoffs the episode received). Here the received handoffs are the reports of the
episode's own child units (``view.outcomes``): a resource has a usable handoff when its resource child returned
handoff references. The capabilities the old ``initial_decision_context`` showed are the outcome of the
capabilities tool, and the settings-derived part (with the old ``_with_selected_execution_task``, which needs the
resource information) is added in ``decide``. The typed reasoning schema is the Store's
(``records.reasoning_schema()`` reads no record).

The old receiver selection (which references this episode knew, from the receipts, the old ``runtime_actions``
rows or a services callback) is custody now: the received handoffs are the references the child units returned and
``credit`` asks ``records.holds``. The old selection read each received handoff record to learn its target (the
resource id) and its usability from the old progress provider; there is no handoff-record library yet, so the
resource id is the one this episode commissioned and the usability is the child's own return."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    parent = view.parent_input
    capabilities, reasonings, commissions = None, [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'tool':
            if outcome['tool'] == 'execution_capabilities':
                capabilities = outcome['outcome']
            else:
                reasonings.append(outcome['outcome'])
            continue
        report = outcome['report']
        commissions.append({'resource_id': outcome['arguments']['resource_id'], 'slot': report['slot'],
                            'handoff_refs': report['handoff_refs'], 'completed': report['completed'],
                            'child_credit': report['child_credit'], 'finding': report['finding']})
    handed_off = {}
    for commission in commissions:
        if commission['handoff_refs']:
            handed_off.setdefault(commission['resource_id'], []).extend(commission['handoff_refs'])
    already = set(parent['already_handed_off_resource_ids'])
    return {
        **parent,
        'capabilities': capabilities,
        'reasonings': reasonings,
        'commissions': commissions,
        'handed_off': {resource_id: sorted(set(refs)) for resource_id, refs in sorted(handed_off.items())},
        'new_handoff_resource_ids': sorted(set(handed_off) - already),
        'handoff_refs': sorted({ref for refs in handed_off.values() for ref in refs}),
        'completed': any(commission['completed'] for commission in commissions),
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
