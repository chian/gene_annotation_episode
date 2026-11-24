"""The return. Always returned: the Episode's credit (the system hands it in ``completion``), the finding (the
selected prediction model, its quality against the entry model on the fixed validation cases and the cases it was
trained on), ``hpc_model_ref`` (the immutable selected prediction model), ``hpc_result_refs`` (the held result
sources, returned in custody) and ``hpc_ledger_refs`` (the ledger rows this Episode wrote: models, model choices,
candidates, queue observations, comparisons, discoveries, shared history and the credit slot, returned in custody).
Selectable: ``hpc_credit`` (the same number as ``credit``) and ``hpc_accepted_obligations``."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'model_ref': Field('text', 'The selected prediction model identity (immutable)'),
    'entry_model_ref': Field('text', 'The model current when this episode was commissioned'),
    'entry_quality': Field('number', 'Quality of the entry model on the fixed validation cases', required=False),
    'validation_quality': Field('number', 'Quality of the selected model on the fixed validation cases; absent for '
                                          'a model trained on later allocations or without validation cases',
                                required=False),
    'model_quality_improvement': Field('number', 'Selected model quality minus entry quality; zero when either is '
                                                 'unknown'),
    'prospective_validation_credit': Field('number', 'Credit of scored forecasts made with this episode\'s models'),
    'training_ids': Field('list', 'The measured cases the selected model was trained on'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the prediction established about the resource model', form=FINDING_FORM),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity (namespace hpc_model).'),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody that '
                                            'this episode holds.'),
    'hpc_ledger_refs': Field('record_refs', 'The rows of the HPC ledger this episode wrote (new field).'),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.', required=False),
})

_QUALIFICATION = ('Quality is measured on the fixed historical validation cases only; a model trained on later '
                  'allocations earns prospective credit when real outcomes arrive. Unknown inputs stay unknown.')


def facts(summary, completion):
    """The facts a parent may select; ``hpc_credit`` is the credit the controller last saw."""
    return {'hpc_credit': completion['credit'], 'hpc_model_ref': summary['model_ref'],
            'hpc_accepted_obligations': summary['accepted_obligations'],
            'hpc_result_refs': summary['result_source_refs']}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary, completion)
    finding = {'model_ref': summary['model_ref'], 'entry_model_ref': summary['entry_model_ref'],
               'model_quality_improvement': summary['model_quality_improvement'],
               'prospective_validation_credit': summary['prospective_validation_credit'],
               'training_ids': list(summary['training_ids']), 'qualification': _QUALIFICATION}
    if summary['entry_quality'] is not None:
        finding['entry_quality'] = summary['entry_quality']
    if summary['model_quality'] is not None:
        finding['validation_quality'] = summary['model_quality']
    result = {'credit': completion['credit'], 'finding': finding, 'hpc_model_ref': recorded['hpc_model_ref'],
              'hpc_result_refs': recorded['hpc_result_refs'], 'hpc_ledger_refs': list(summary['produced_refs'])}
    if 'hpc_credit' in selection:
        result['hpc_credit'] = recorded['hpc_credit']
    if 'hpc_accepted_obligations' in selection:
        result['hpc_accepted_obligations'] = recorded['hpc_accepted_obligations']
    return result
