"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
obligations accepted and remaining, the plans frozen and closed, the result sources held and the owner ledger credit
by component). Selectable: ``hpc_credit`` (signed measured credit; repeated polling adds none, the same number as
``credit``), ``hpc_model_ref`` (the immutable selected prediction model), ``hpc_accepted_obligations`` (original
obligations with accepted actual results) and ``hpc_result_refs`` (the sources holding the original result bytes)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'accepted_obligations': Field('list', 'The original obligations with accepted actual results'),
    'remaining_obligations': Field('list', 'The original obligations without an accepted actual result'),
    'plans_frozen': Field('integer', 'How many portfolios were frozen into plans'),
    'plans_closed': Field('integer', 'How many frozen plans are closed (their allocation finished)'),
    'results_published': Field('integer', 'How many original result sources this episode holds'),
    'credit_components': Field('record', 'The owner ledger credit by component: actual, model and validation'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the HPC work accomplished against the commission', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody',
                             required=False),
})

_QUALIFICATION = ('Credit is the owner ledger\'s: accepted accomplishment, model improvement and validated '
                  'forecasts only. A plan whose allocation is not closed has no accepted result yet, and '
                  'completion of a unit is not acceptance.')


def facts(summary, completion):
    """The facts a parent may select, from the summary (what the ledger showed after the last tool)."""
    view = summary['ledger_view']
    return {'hpc_credit': completion['credit'], 'hpc_model_ref': view['model_ref'],
            'hpc_accepted_obligations': [row['slot'].removeprefix('actual:')
                                         for row in view['credit']['contributions'] if row['kind'] == 'actual'],
            'hpc_result_refs': list(summary['result_refs'])}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary, completion)
    view = summary['ledger_view']
    accepted = recorded['hpc_accepted_obligations']
    closed = [plan for plan in view['plans'] if plan['closed']]
    finding = {'accepted_obligations': accepted,
               'remaining_obligations': sorted(set(view['commission']['obligations']) - set(accepted)),
               'plans_frozen': len(view['plans']), 'plans_closed': len(closed),
               'results_published': len(summary['result_refs']),
               'credit_components': dict(view['credit']['components']), 'qualification': _QUALIFICATION}
    result = {'credit': completion['credit'], 'finding': finding, **{name: recorded[name] for name in selection}}
    return result
