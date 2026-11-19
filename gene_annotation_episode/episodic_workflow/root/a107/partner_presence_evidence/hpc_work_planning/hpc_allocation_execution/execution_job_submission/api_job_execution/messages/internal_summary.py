"""Where the API job stands: the assignment, what each unit's tool returned (operations done, recorded facts, the
handoff and result records, acquired records, the credit units), the latest outcome and the operational progress of
each API operation, as a pure function of the loop's view.

Carried from the old ``internal_summary.py`` (``decision_context``: ``execution_assignment`` and
``execution_progress``, the episode's own recorded facts) and the old ``state.py`` / ``initial_information.py`` (the
bound resource's capabilities, which the first unit looks up). A returned API error is kept complete."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    summary = {**view.parent_input, 'operations_done': 0, 'capabilities': None, 'facts': {},
               'handoff_refs': [], 'result_refs': [], 'handoff_established': False, 'execution_completed': False,
               'acquired_record_count': 0, 'credit_units': None, 'api_received_progress': {},
               'last_local_outcome': None, 'feedback': None, 'lookups': [], 'job_identity': None,
               'request_identity': None, 'submission_outcome': None}
    for outcome in view.outcomes:
        tool, arguments, returned = outcome['tool'], outcome['arguments'], outcome['outcome']
        if tool == 'api_capabilities':
            summary['capabilities'] = returned['capabilities']
            continue
        if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
            summary['lookups'].append(returned)
            continue
        summary['operations_done'] += 1
        summary['last_local_outcome'] = returned
        summary['feedback'] = returned.get('feedback')
        summary['credit_units'] = returned['credit_units']
        summary['facts'] = returned['facts']
        summary['handoff_refs'] = summary['handoff_refs'] + [ref for ref in returned['handoff_refs']
                                                             if ref not in summary['handoff_refs']]
        summary['result_refs'] = summary['result_refs'] + [ref for ref in returned['result_refs']
                                                           if ref not in summary['result_refs']]
        summary['handoff_established'] = summary['handoff_established'] or returned['handoff_established']
        summary['execution_completed'] = returned['execution_completed']
        for name in ('job_identity', 'request_identity', 'submission_outcome'):
            if returned[name] is not None:
                summary[name] = returned[name]
        if tool == 'api_operation':
            summary['api_received_progress'][arguments['operation']] = returned
    summary['acquired_record_count'] = len(summary['result_refs'])
    if view.controller_state is not None:
        summary['action_yields'] = yield_table(view.controller_state, forecast_unit='credit')
    return summary
