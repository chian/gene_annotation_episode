"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding (the
selected model, its measured improvement and the validation credit attributed to this episode). Selectable:
``hpc_credit``, ``hpc_model_ref``, ``hpc_accepted_obligations`` and ``hpc_result_refs`` (returned in custody)."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'model_ref': Field('text', 'The identity of the selected prediction model'),
    'model_quality_improvement': Field('number', 'Held-out quality of the current model minus its quality at this '
                                       'episode\'s entry (zero when the model has no measured quality)'),
    'prospective_validation_credit': Field('number', 'The validation credit the parent ledger attributes to '
                                           'predictions made in this episode'),
    'actual_job_credit_counted_here': Field('boolean', 'Whether actual job credit is counted in this episode\'s '
                                            'credit (never)'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The selected prediction model and the credit it earned', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity.', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody.',
                             required=False),
})


def final_to_parent(summary, completion, selection):
    view = summary['ledger']['hpc_credit']
    finding = {'model_ref': summary['facts']['hpc_model_ref'],
               'model_quality_improvement': view['model_quality_improvement'],
               'prospective_validation_credit': view['prospective_validation_credit'],
               'actual_job_credit_counted_here': view['actual_job_credit_counted_here']}
    result = {'credit': completion['credit'], 'finding': finding}
    for name in selection:
        result[name] = completion['credit'] if name == 'hpc_credit' else summary['facts'][name]
    return result
