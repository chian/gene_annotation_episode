"""What this episode returns to its parent. ``credit`` is the Episode's credit as its controller last saw it
(``completion['credit']``) and ``finding`` is the HPC work against the commission; both are always returned. The
selectable facts are ``hpc_credit`` (signed measured credit, the same number as ``credit``; repeated polling adds
none), ``hpc_model_ref`` (the immutable selected prediction model), ``hpc_accepted_obligations`` (original obligations
with accepted actual results), ``hpc_result_refs`` (the sources holding the original result bytes, restricted to those
this episode holds) and ``hpc_result_artifact_refs`` (the artifact of each result source: a returned source does not
bring the artifact it names)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'accepted_obligations': Field('list', 'The original obligations with accepted actual results'),
    'remaining_obligations': Field('list', 'The original obligations without an accepted actual result'),
    'plans_frozen': Field('integer', 'How many portfolios were frozen into plans'),
    'plans_closed': Field('integer', 'How many frozen plans are closed (their allocation finished)'),
    'results_published': Field('integer', 'How many original result sources this episode published'),
    'credit_components': Field('record', 'The owner ledger credit by component: actual, model and validation'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the allocation work accomplished against the commission', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody',
                             required=False),
    'hpc_result_artifact_refs': Field('record_refs', 'The artifact of each source named in hpc_result_refs (a '
                                      'returned record does not bring the records it names; new field)',
                                      required=False),
})

_QUALIFICATION = ('Credit is the owner ledger\'s: accepted accomplishment, model improvement and validated '
                  'forecasts only. A plan whose allocation is not closed has no accepted result yet, and '
                  'completion of a unit is not acceptance.')


def facts(summary, completion):
    """The recorded facts, from the summary (what the ledger showed after the last tool)."""
    view = summary['ledger_view']
    return {'hpc_credit': completion['credit'], 'hpc_model_ref': view['model_ref'],
            'hpc_accepted_obligations': [row['slot'].removeprefix('actual:')
                                         for row in view['credit']['contributions'] if row['kind'] == 'actual'],
            'hpc_result_refs': list(summary['result_refs']),
            'hpc_result_artifact_refs': list(summary['result_artifact_refs'])}


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
