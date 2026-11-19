"""Where the API job stands: the assignment, what each unit's tool returned (operations done, recorded facts,
the handoff, support and result records, acquired records, the credit units), the latest outcome and the latest
recorded progress event of each API operation, as a pure function of the loop's view.

Carried from the old ``internal_summary.py`` (``_api_decision_summary``: ``api_service``, ``api_request``,
``api_received_progress`` by operation name, ``api_execution_completed``; ``decision_context``:
``execution_assignment``, ``execution_progress``; ``initial_decision_context``: the resource capabilities and
the initial inventory) and from the old ``decision_state.py`` (last local outcome, feedback, controller table)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    summary = {**view.parent_input, 'operations_done': 0, 'capabilities': None, 'inventory_snapshot': None,
               'facts': {}, 'handoff_refs': [], 'support_refs': [], 'result_refs': [],
               'handoff_established': False, 'execution_completed': False, 'acquired_record_count': 0,
               'credit_units': None, 'api_received_progress': {}, 'last_local_outcome': None, 'feedback': None,
               'lookups': [], 'job_identity': None, 'request_identity': None, 'submission_outcome': None}
    for outcome in view.outcomes:
        tool, returned = outcome['tool'], outcome['outcome']
        if tool == 'api_capabilities':
            summary['capabilities'] = returned['capabilities']
            summary['inventory_snapshot'] = returned['inventory_snapshot']
            continue
        if tool in ('knowledge_lookup', 'launch_instruction_lookup'):
            summary['lookups'].append(returned)
            continue
        summary['operations_done'] += 1
        summary['last_local_outcome'] = returned
        summary['feedback'] = returned['feedback']
        summary['credit_units'] = returned['credit_units']
        summary['facts'] = returned['facts']
        for key, name in (('handoff_refs', 'handoff_refs'), ('support_refs', 'support_refs'),
                          ('result_refs', 'result_refs')):
            summary[key] = summary[key] + [ref for ref in returned[name] if ref not in summary[key]]
        summary['handoff_established'] = summary['handoff_established'] or returned['handoff_established']
        summary['execution_completed'] = returned['execution_completed']
        for name in ('job_identity', 'request_identity', 'submission_outcome'):
            if returned[name] is not None:
                summary[name] = returned[name]
        for event in returned['events']:
            summary['api_received_progress'][event['name']] = {
                'state': event['event']['state'], 'kind': event['event']['kind'],
                'facts': event['event']['facts'], 'failure_code': event['event']['failure_code']}
    summary['acquired_record_count'] = len(summary['result_refs'])
    summary['facts_by_source'] = {
        'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
        'bvbrc_appservice_support_refs': summary['support_refs'],
        'execution_completed': summary['execution_completed'],
        'bvbrc_application_outcomes': summary['facts']['bvbrc_application_outcomes']}
    if view.controller_state is not None:
        summary['action_yields'] = yield_table(view.controller_state, forecast_unit='credit')
    return summary
