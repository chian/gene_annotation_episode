"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
selected model and the parts of its credit). The report facts are declared too; the commissioner
selects the ones it wants: the signed measured credit, the selected model identity, the original obligations with
accepted actual results, and the ledger result Sources this Episode holds (returned in custody)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'model_ref': Field('text', 'The selected prediction model identity'),
    'model_quality_improvement': Field('number', 'Held-out quality gain of the model over the quality at entry'),
    'prospective_validation_credit': Field('number', 'Validation credit of the predictions this Episode made'),
    'actual_job_credit_counted_here': Field('boolean', 'Whether actual job credit is counted in this credit'),
    'entry_quality': Field('number', 'Held-out quality of the model at entry, when known', required=False),
    'current_quality': Field('number', 'Held-out quality of the selected model, when known', required=False),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The selected model and the parts of the credit', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity.', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody.',
                             required=False),
})


def final_to_parent(summary, completion, selection):
    ledger, inputs = summary['ledger'], summary['credit_inputs']
    finding = {'model_ref': ledger['hpc_model_ref'],
               'model_quality_improvement': summary['hpc_credit']['model_quality_improvement'],
               'prospective_validation_credit': inputs['prospective_validation_credit'],
               'actual_job_credit_counted_here': False}
    if inputs['entry_quality'] is not None:
        finding['entry_quality'] = inputs['entry_quality']
    if inputs['current_quality'] is not None:
        finding['current_quality'] = inputs['current_quality']
    facts = {'hpc_credit': completion['credit'], 'hpc_model_ref': ledger['hpc_model_ref'],
             'hpc_accepted_obligations': ledger['hpc_accepted_obligations'],
             'hpc_result_refs': summary['hpc_result_refs']}
    result = {'credit': completion['credit'], 'finding': finding}
    result.update({name: facts[name] for name in selection})
    return result
