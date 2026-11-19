"""The report. ``RETURN_FORM`` declares required ``credit`` and ``finding`` and four selectable fields: ``hpc_credit``
(signed measured credit; polling adds none), ``hpc_model_ref`` (immutable selected model identity),
``hpc_accepted_obligations`` (obligations with accepted actual results) and ``hpc_result_refs`` (received owned result
sources; ``record_refs``, so only sources this Episode holds). The facts come from the summary, which keeps the ledger's
view from the last tool outcome. ``hpc_credit`` is the credit the controller stopped on (``completion['credit']``);
no second credit is computed.

``finding`` is the episode's own typed finding: the model it ends on, with its held-out quality, its credit parts
and what the finding does and does not establish."""
from method_loop import Field, RecordForm

_QUALIFICATION = ('Model credit is the measured improvement of the held-out quality since this episode began plus '
                  'the prospective validation credit of forecasts attributed to it; actual job credit is not counted '
                  'here and the HPC parent later scores frozen predictions against real outcomes. Unknown inputs '
                  'stay unknown.')

FINDING_FORM = RecordForm({
    'model_ref': Field('text', 'The immutable identity of the model this episode ends on'),
    'model_quality_improvement': Field('number', 'Held-out quality of that model minus the quality at entry; zero '
                                                 'when either is unmeasured'),
    'prospective_validation_credit': Field('number', 'The validation credit attributed to this prediction episode'),
    'available_training_count': Field('integer', 'How many measured cases are available for training'),
    'candidate_count': Field('integer', 'How many executable portfolios the ledger holds'),
    'comparison_made': Field('boolean', 'Whether any portfolio comparison exists in the ledger'),
    'qualification': Field('text', 'What the finding does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The model this episode ends on, with its measured credit', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity (namespace hpc_model).',
                           required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.', required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody, that '
                                            'this episode holds.', required=False),
})


def hpc_facts(summary, completion):
    """The recorded facts."""
    return {'hpc_credit': completion['credit'], 'hpc_model_ref': summary['hpc_model_ref'],
            'hpc_accepted_obligations': list(summary['hpc_accepted_obligations']),
            'hpc_result_refs': list(summary['hpc_result_refs'])}


def final_to_parent(summary, completion, selection):
    facts = hpc_facts(summary, completion)
    credit = summary['hpc_credit']
    finding = {'model_ref': facts['hpc_model_ref'],
               'model_quality_improvement': credit['model_quality_improvement'],
               'prospective_validation_credit': credit['prospective_validation_credit'],
               'available_training_count': len(summary['hpc_available_training_ids']),
               'candidate_count': len(summary['hpc_candidates']),
               'comparison_made': bool(summary['hpc_latest_comparison']),
               'qualification': _QUALIFICATION}
    result = {'credit': completion['credit'], 'finding': finding, **{name: facts[name] for name in selection}}
    return result
