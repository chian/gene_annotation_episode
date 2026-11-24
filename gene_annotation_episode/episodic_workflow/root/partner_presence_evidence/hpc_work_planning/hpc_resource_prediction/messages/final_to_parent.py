"""What this episode returns to the planner that commissioned it: controlled data only.

The planner's next decision is whether the prediction was productive (its ``credit``, and the trend of it over
commissions) and what it may now plan from. ``finding`` says, in counts and one boolean, what the ledger holds
after this episode: whether it ends on a model it fitted, how many measured cases that model was trained on, and
how many candidate portfolios, portfolio comparisons and queue observations the ledger has. ``hpc_ledger_refs`` are
the rows of the HPC ledger this Episode holds (the commission row, which names the ledger, among them) with the
records they name: the fitted model, the model choice, the comparisons and every other record of this episode
reach the planner in custody, never as text. ``hpc_result_refs`` (selectable) are the result sources of the ledger
this Episode holds.

Not returned, because a reference or the credit already says it: the old ``hpc_credit`` (it restated the credit),
``hpc_model_ref`` (the model is a row of the returned ledger), ``hpc_accepted_obligations`` (rows of the ledger) and
the explanatory ``qualification`` text."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'model_fitted': Field('boolean', 'Whether this episode ends on a model it fitted (not the one it started from)'),
    'training_cases_used': Field('integer', 'How many measured cases the current model was trained on'),
    'candidates': Field('integer', 'How many candidate portfolios the ledger holds'),
    'comparisons': Field('integer', 'How many portfolio comparisons the ledger holds'),
    'queue_observations': Field('integer', 'How many queue observations the ledger holds'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the ledger holds after this episode, in counts', form=FINDING_FORM),
    'hpc_ledger_refs': Field('record_refs', 'The rows of the HPC ledger this Episode holds and the records they '
                                            'name; the commission row names the ledger'),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody, that '
                                            'this episode holds.', required=False),
})


def final_to_parent(summary, completion, selection):
    state, ledger = summary['ledger_state'], summary['ledger']
    finding = {'model_fitted': state['current_model_ref'] != ledger['model_entry']['model_ref'],
               'training_cases_used': state['current_model_support']['observations'],
               'candidates': len(state['candidates']), 'comparisons': len(state['comparison_refs']),
               'queue_observations': len(state['queue_refs'])}
    selectable = {'hpc_result_refs': list(summary['result_refs'])}
    return {'credit': completion['credit'], 'finding': finding, 'hpc_ledger_refs': list(summary['ledger_refs']),
            **{name: selectable[name] for name in selection}}
