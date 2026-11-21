"""What this episode returns to the planner that commissioned it: controlled data only.

The planner's next decision is whether the allocation work was productive (its ``credit``, and the trend of it over
commissions) and what the ledger now holds. ``finding`` says it in counts: the obligations with and without an
accepted actual result, the plans frozen, handed off and closed, and the result sources published.
``hpc_ledger_refs`` are the rows of the HPC ledger this Episode holds (the rows it was passed and its own) with the
records they name (a plan's launch input, an attached handoff): the plans, forecasts, measurements, scores and
acceptances reach the planner in custody, never as text. Selectable: ``hpc_result_refs`` (the sources holding the
original result bytes) and ``hpc_result_artifact_refs`` (the artifact of each: a returned source does not bring the
artifact it names).

Not returned, because a reference or the credit already says it: the old ``hpc_credit`` (it restated the credit),
``hpc_model_ref`` and ``hpc_accepted_obligations`` (rows of the returned ledger), the credit by component (the
planner derives it from the rows it holds) and the explanatory ``qualification`` text."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'accepted_obligations': Field('integer', 'How many original obligations have an accepted actual result'),
    'remaining_obligations': Field('integer', 'How many original obligations have no accepted actual result'),
    'plans_frozen': Field('integer', 'How many portfolios are frozen into plans'),
    'plans_handed_off': Field('integer', 'How many frozen plans have their launch handoff attached'),
    'plans_closed': Field('integer', 'How many frozen plans are closed (their allocation finished)'),
    'results_published': Field('integer', 'How many original result sources this episode published'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the allocation work accomplished against the commission, in counts',
                     form=FINDING_FORM),
    'hpc_ledger_refs': Field('record_refs', 'The rows of the HPC ledger this Episode holds and the records they '
                                            'name; the commission row names the ledger'),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody',
                             required=False),
    'hpc_result_artifact_refs': Field('record_refs', 'The artifact of each source named in hpc_result_refs (a '
                                      'returned record does not bring the records it names)', required=False),
})


def final_to_parent(summary, completion, selection):
    view, state = summary['ledger_view'], summary['ledger_state']
    accepted = len(state['accepted_obligations'])
    finding = {'accepted_obligations': accepted,
               'remaining_obligations': len(view['commission']['obligations']) - accepted,
               'plans_frozen': len(view['plans']),
               'plans_handed_off': sum(plan['handed_off'] for plan in view['plans']),
               'plans_closed': sum(plan['closed'] for plan in view['plans']),
               'results_published': len(summary['result_refs'])}
    selectable = {'hpc_result_refs': list(summary['result_refs']),
                  'hpc_result_artifact_refs': list(summary['result_artifact_refs'])}
    return {'credit': completion['credit'], 'finding': finding, 'hpc_ledger_refs': list(view['ledger_refs']),
            **{name: selectable[name] for name in selection}}
