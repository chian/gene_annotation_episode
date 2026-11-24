"""Where the episode stands, as a pure function of the loop's view (carried from the old ``internal_summary.py``
(``initial_decision_context``, ``decision_context``), ``decision_state.py``, ``execution_state.py`` (``_selection``,
``_context_target``) and ``received_evidence.py`` (``_received``)).

The old ``decision_context`` was ``execution_assignment`` (the commission) and ``execution_progress`` (the live
report facts: the usable handoffs the episode received). Here the received handoffs are the reports of the
episode's own child units (``view.outcomes``): a resource has a usable handoff when its child returned handoff
references. The resource information and capabilities the old summary showed (``initial_decision_context``) are
the outcome of the capabilities tool, and the settings-derived part is added in ``decide``. The typed reasoning
schema is the Store's (``records.reasoning_schema()`` reads no record).

The old receiver selection (which references this episode knew, from the receipts, the old ``runtime_actions``
rows or a services callback) is custody now: the received handoffs are the references the child units returned and
``credit`` asks ``records.holds``. The old ``received_evidence`` read each received handoff record to learn its
target (resource id) and its usability from the old progress provider. There is no handoff-record library yet, so
the resource id is the one this episode commissioned and the usability is the child's own return (see the
carry-over record)."""
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
                            'handoff_refs': report['handoff_refs'], 'support_refs': report['support_refs'],
                            'completed': report['completed'], 'finding': report['finding']})
    handed_off = {}
    for commission in commissions:
        if commission['handoff_refs']:
            handed_off.setdefault(commission['resource_id'], []).extend(commission['handoff_refs'])
    already = set(parent['already_handed_off_resource_ids'])
    # The input list (nano-graphrag's input-list paradigm): the permitted resources whose request is still to be
    # carried out. A resource already handed off, or commissioned once, is consumed and no longer offered.
    consumed = sorted(already | {commission['resource_id'] for commission in commissions})
    input_list = [resource_id for resource_id in parent['eligible_resource_ids'] if resource_id not in consumed]
    return {
        **parent,
        'input_list': input_list,
        'consumed_resource_ids': consumed,
        'capabilities': capabilities,
        'reasonings': reasonings,
        'commissions': commissions,
        'handed_off': {resource_id: sorted(set(refs)) for resource_id, refs in sorted(handed_off.items())},
        'new_handoff_resource_ids': sorted(set(handed_off) - already),
        'handoff_refs': sorted({ref for refs in handed_off.values() for ref in refs}),
        'support_refs': sorted({ref for commission in commissions for ref in commission['support_refs']}),
        'completed': any(commission['completed'] for commission in commissions),
        'reasoning_schema': view.records.reasoning_schema(),
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
