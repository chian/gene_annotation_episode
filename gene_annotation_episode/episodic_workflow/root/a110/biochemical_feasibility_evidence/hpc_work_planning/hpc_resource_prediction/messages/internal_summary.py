"""Where the episode stands, carried from the old ``internal_summary.py`` (``PredictionSummary.decision_context``),
``decision_state.py`` (the fields that come from the view), ``prediction_state.py`` (``initialize``) and the
credit view of ``credit.py``: a pure function of the view.

The ledger is the held rows of the work table ``hpc_evidence`` (``task.read_ledger`` over ``view.records``). The
old ``initialize`` (the reference model, an initial model fitted from shared history when the shared memory is
configured, and the entry quality recorded once per episode) is computed here: the reference model is the prior
model of the commission, the entry model is the last model choice among the rows the parent named in
``ledger_refs``, and the entry quality is its quality. The initial model fitted from shared history is not
carried (it needs a read of the ``estimate_table`` service at entry; the model may fit the refreshed history with
``hpc_model_fit``). The old ``hpc_report_form`` (the ``x-source`` report form) is report-form machinery and is not
carried: the return form is declared in ``final_to_parent.py``.

``decision_context`` holds the old keys; ``hpc_resource`` and ``hpc_shared_memory`` come from settings and the
``estimate_table`` service and are added by ``decide``."""
from yield_control import YieldState

from ..credit import prospective_validation_credit, quality, quality_improvement
from ..task import (HPC_EVIDENCE, candidates, check_owner, credit_view, current_model, history, read, read_ledger,
                    records_of)
from .. import goal as goal_file

import gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.biochemical_feasibility_evidence.hpc_prediction as prediction


def _entry_model_ref(view):
    choices = []
    table = view.records.table(HPC_EVIDENCE)
    for ref in view.parent_input['ledger_refs']:
        row = table.get(ref)
        if row['kind'] == 'model_choice':
            choices.append(row['body']['model_ref'])
    return choices[-1] if choices else 'reference_model'


def _unique(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    ledger = check_owner(read_ledger(view.records), parent)
    commission = ledger['commission']
    episode_id = view.episode_ref.episode_id
    entry_ref = _entry_model_ref(view)
    entry_quality = quality(ledger, read(ledger, entry_ref))
    model_ref = current_model(ledger)
    model = read(ledger, model_ref)
    current_quality = quality(ledger, model)
    improvement = quality_improvement(entry_quality, current_quality)
    validation = prospective_validation_credit(ledger, episode_id)
    available = sorted(set(history(ledger)) - set(commission['validation_ids']))
    produced = _unique(ref for outcome in view.outcomes if outcome['kind'] == 'tool' for ref in outcome['produced'])
    controller = view.controller_state.as_record() if isinstance(view.controller_state, YieldState) else None
    credit_now = credit_view(ledger)
    decision_context = {
        'hpc_commission': commission,
        'hpc_owner_episode_id': ledger['owner']['episode_id'],
        'hpc_candidates': candidates(ledger),
        'hpc_tool_request': [row['body'] for row in records_of(ledger, 'tool_request')],
        'hpc_model_ref': model_ref,
        'hpc_credit': {'credit': commission['credit']['model_scale'] * improvement + validation,
                       'model_quality_improvement': improvement, 'prospective_validation_credit': validation,
                       'actual_job_credit_counted_here': False},
        'hpc_latest_comparison': [{**row, 'body': {key: value for key, value in row['body'].items()
                                                   if key not in ('episode_id', 'operation_key')}}
                                  for row in records_of(ledger, 'comparison')[-1:]],
        'hpc_model_support': prediction.predict(model, {})['support'],
        'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                      for row in records_of(ledger, 'plan')],
        'hpc_latest_monitor': records_of(ledger, 'monitor')[-1:],
        'hpc_monitor_controllers': records_of(ledger, 'monitor_controller'),
        'hpc_queue_refs': [row['id'] for row in records_of(ledger, 'queue')],
        'hpc_shared_history_refs': [row['id'] for row in records_of(ledger, 'shared_history')],
        'hpc_available_training_ids': available,
    }
    return {
        **parent,
        'episode_id': episode_id,
        'hpc_goal': {'objective': view.goal.objective, 'goal': goal_file.GOAL},
        'decision_context': decision_context,
        'model_ref': model_ref,
        'training_ids': list(model['training_ids']),
        'entry_model_ref': entry_ref,
        'entry_quality': entry_quality,
        'model_quality': current_quality,
        'model_scale': commission['credit']['model_scale'],
        'model_quality_improvement': improvement,
        'prospective_validation_credit': validation,
        'credit_components': credit_now,
        'accepted_obligations': [row['slot'].removeprefix('actual:') for row in ledger['credits']
                                 if row['kind'] == 'actual'],
        'result_source_refs': [row['body']['source_ref'] for row in records_of(ledger, 'result')
                               if view.records.holds(row['body']['source_ref'])],
        'ledger_model_ids': [row['id'] for row in records_of(ledger, 'model')],
        'produced_refs': produced,
        'outcomes': list(view.outcomes),
        'controller': controller,
        'current_credit': None if controller is None else controller['current_credit'],
    }
