"""Where the episode stands, as a pure function of the loop's view: the parent input, the outcomes of its own
units, and (once ``hpc_initialize`` completed) the state of the parent-owned HPC ledger and the facts the old
report derived from it.

Carried from the old ``internal_summary.py`` (``PredictionSummary.decision_context``: the ``hpc_*`` fields),
``decision_state.py`` (the working state: the last local outcome, the controller state), ``to_parent.py``
(``facts``) and ``decision_inputs.py`` (``completed_action_reports``, ``requested_action_history``). The ledger
reads go through ``task.py``'s ledger primitives (BLOCKED-ON-JOB-SERVICE: they raise where reached). Not carried:
``hpc_report_form`` (the form with ``x-source`` fields the parent used to write: the child's ``RETURN_FORM``
replaces it), ``hpc_resource`` and ``hpc_shared_memory`` (they come from the settings and the service, which a
summary does not read: ``decide`` adds them). ``hpc_shared_history_refs`` is always present (empty when no shared
snapshot was taken): the old summary showed it only when shared memory was configured, which a summary cannot
read. ``model_ids`` (every model identity of the ledger) is new: ``final_to_parent`` resolves the ``hpc_model``
namespace of the report check against it, as the old ``resolve`` did against the ledger."""
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.evolutionary_history_evidence import (
    hpc_prediction as prediction)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import credit_view
from ..task import (accepted_obligations, candidates, current_model, history_cases, ledger_commission, ledger_read,
                    ledger_records)


def facts(reader, owner, credit):
    """The old ``facts``: the credit, the selected model, the accepted obligations and the result sources this
    episode holds (the old ``known`` references are custody: ``holds``)."""
    return {'hpc_credit': credit, 'hpc_model_ref': current_model(reader, owner),
            'hpc_accepted_obligations': accepted_obligations(reader, owner),
            'hpc_result_refs': [row['body']['source_ref'] for row in ledger_records(reader, owner, 'result')
                                if reader.holds(row['body']['source_ref'])]}


def ledger_state(reader, owner, episode_id):
    """The old ``decision_context`` over the ledger."""
    commission = ledger_commission(reader, owner)
    model_ref = current_model(reader, owner)
    view = credit_view(reader, owner, episode_id, True)
    return {
        'hpc_commission': commission, 'hpc_owner_episode_id': ledger_read(reader, owner, 'owner')['episode_id'],
        'hpc_candidates': candidates(reader, owner, commission),
        'hpc_tool_request': [row['body'] for row in ledger_records(reader, owner, 'tool_request')],
        'hpc_model_ref': model_ref, 'hpc_credit': view,
        'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                   if key not in ('episode_id', 'operation_key')}}
                                  for row in ledger_records(reader, owner, 'comparison')[-1:]],
        'hpc_model_support': prediction.predict(ledger_read(reader, owner, model_ref), {})['support'],
        'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                      for row in ledger_records(reader, owner, 'plan')],
        'hpc_latest_monitor': ledger_records(reader, owner, 'monitor')[-1:],
        'hpc_monitor_controllers': ledger_records(reader, owner, 'monitor_controller'),
        'hpc_queue_refs': [row['id'] for row in ledger_records(reader, owner, 'queue')],
        'hpc_shared_history_refs': [row['id'] for row in ledger_records(reader, owner, 'shared_history')],
        'hpc_available_training_ids': sorted(set(history_cases(reader, owner, commission))
                                             - set(commission['validation_ids']))}


def without_owner(arguments):
    return {key: value for key, value in arguments.items() if key != 'owner_episode_id'}


def internal_summary(view):
    parent = view.parent_input
    owner, episode_id = parent['owner_episode_id'], view.episode_ref.episode_id
    initialized = any(item['tool'] == 'hpc_initialize' for item in view.outcomes)
    ledger = facts_of = model_ids = None
    if initialized:
        ledger = ledger_state(view.records, owner, episode_id)
        facts_of = facts(view.records, owner, ledger['hpc_credit']['credit'])
        model_ids = [row['id'] for row in ledger_records(view.records, owner, 'model')]
    last = view.outcomes[-1] if view.outcomes else None
    return {
        'owner_episode_id': owner,
        'commission_identity': parent['commission_identity'],
        'yield_binding': parent['yield_binding'],
        'message': parent['message'],
        'episode_id': episode_id,
        'initialized': initialized,
        'ledger': ledger,
        'facts': facts_of,
        'model_ids': model_ids,
        'last_outcome': None if last is None else {
            'tool': last['tool'], 'arguments': without_owner(last['arguments']), 'outcome': last['outcome']},
        'history': [{'tool': item['tool'], 'status': item['outcome']['status'],
                     'arguments': without_owner(item['arguments'])} for item in view.outcomes],
        'completed_action_reports': [
            {'tool': item['tool'], 'status': item['outcome']['status'],
             'record_refs': item['outcome']['record_refs'],
             'changed_record_refs': item['outcome']['changed_record_refs'],
             'feedback': item['outcome']['feedback']} for item in view.outcomes],
        'units_consumed': view.units_consumed,
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
    }
