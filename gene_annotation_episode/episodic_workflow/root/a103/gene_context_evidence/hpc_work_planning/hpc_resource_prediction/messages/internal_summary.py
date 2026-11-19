"""Where the prediction stands: the commission, the ledger state and credit inputs the last tool unit returned,
the Episode's own earlier actions, and the result sources it holds. A pure function of the view."""
from ..credit import credit as credit_file_credit, model_quality_improvement


def internal_summary(view):
    parent_input = view.parent_input
    tool_outcomes = [item for item in view.outcomes if item['kind'] == 'tool']
    initialize = next((item['outcome'] for item in tool_outcomes if item['tool'] == 'hpc_initialize'), None)
    latest = tool_outcomes[-1]['outcome'] if tool_outcomes else None
    summary = {'owner_episode_id': parent_input['owner_episode_id'],
               'commission_identity': parent_input['commission_identity'],
               'launch_instructions': parent_input['launch_instructions'],
               'initialized': initialize is not None,
               'commission': None if initialize is None else initialize['commission'],
               'ledger': None if latest is None else latest['ledger_view'],
               'credit_inputs': None if latest is None else latest['credit_inputs'],
               'controller_state': None if view.controller_state is None else view.controller_state.as_record(),
               'requested_action_history': [
                   {'tool': item['tool'], 'arguments': item['arguments'], 'status': item['outcome']['status']}
                   for item in tool_outcomes],
               'last_outcome': None if latest is None else {
                   'tool': tool_outcomes[-1]['tool'], 'status': latest['status'], 'result': latest['result']},
               'feedback': None if latest is None else latest.get('feedback'),
               'hpc_credit': None, 'credit': 0.0, 'hpc_result_refs': []}
    if latest is not None:
        inputs = latest['credit_inputs']
        summary['hpc_credit'] = {'model_quality_improvement': model_quality_improvement(inputs),
                                 'prospective_validation_credit': inputs['prospective_validation_credit'],
                                 'actual_job_credit_counted_here': False}
        summary['credit'] = credit_file_credit(summary, view.records)
        summary['hpc_result_refs'] = [ref for ref in latest['ledger_view']['hpc_result_source_refs']
                                      if view.records.holds(ref)]
    return summary
