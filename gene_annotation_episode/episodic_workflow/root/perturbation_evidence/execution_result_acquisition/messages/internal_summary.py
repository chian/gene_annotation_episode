"""Where the acquisition stands: the assignment, the original target and result catalog, what each unit's tool
returned (operations done, recorded facts, the handoff, support and result records, the identities and credit
units), and the latest outcome, as a pure function of the loop's view.

Carried from the old ``internal_summary.py`` (``decision_context``: ``execution_assignment``,
``execution_progress`` (the facts), ``execution_target``, ``execution_target_description``;
``initial_decision_context``: the resource capabilities and the initial inventory, now the first unit's outcome)
and from the old ``decision_state.py`` (last local outcome, feedback, controller table). The old ``facts`` of
``to_parent.py`` (handoff refs, support refs, ``execution_result_refs``, ``execution_completed``, the application
facts) are collected here from the outcomes."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    summary = {**view.parent_input, 'catalog': None, 'target': None, 'target_description': None,
               'capabilities': None, 'inventory_snapshot': None, 'operations_done': 0, 'facts': {},
               'handoff_refs': [], 'support_refs': [], 'result_refs': [], 'execution_completed': False,
               'credit_units': None, 'handoff_identities': [], 'initial_handoff_identities': [],
               'result_identities': [], 'last_local_outcome': None, 'feedback': None, 'lookups': []}
    for outcome in view.outcomes:
        tool, returned = outcome['tool'], outcome['outcome']
        if tool == 'result_catalog':
            for name in ('catalog', 'target', 'target_description', 'capabilities', 'inventory_snapshot',
                         'credit_units'):
                summary[name] = returned[name]
            summary['initial_handoff_identities'] = returned['initial_handoff_identities']
            continue
        if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
            summary['lookups'].append(returned)
            continue
        summary['operations_done'] += 1
        summary['last_local_outcome'] = returned
        summary['feedback'] = returned['feedback']
        summary['credit_units'] = returned['credit_units']
        if returned['facts']:
            summary['facts'] = returned['facts']
        for key, name in (('handoff_refs', 'handoff_refs'), ('support_refs', 'support_refs'),
                          ('result_refs', 'result_refs'), ('handoff_identities', 'handoff_identities'),
                          ('result_identities', 'result_identities')):
            summary[key] = summary[key] + [item for item in returned[name] if item not in summary[key]]
        summary['execution_completed'] = summary['execution_completed'] or returned['execution_completed']
    summary['facts_by_source'] = {
        'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
        'bvbrc_appservice_support_refs': summary['support_refs'],
        'execution_completed': summary['execution_completed'],
        'bvbrc_application_outcomes': summary['facts']['bvbrc_application_outcomes']}
    if view.controller_state is not None:
        summary['action_yields'] = yield_table(view.controller_state, forecast_unit='credit')
    return summary
