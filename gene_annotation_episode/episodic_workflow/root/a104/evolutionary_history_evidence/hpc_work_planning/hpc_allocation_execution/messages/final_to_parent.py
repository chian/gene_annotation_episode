"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding.
Selectable: ``hpc_credit`` (signed measured credit), ``hpc_model_ref`` (immutable selected prediction model identity),
``hpc_accepted_obligations`` (original obligations with accepted actual results) and ``hpc_result_refs`` (sources that
contain original result bytes and attempt custody, returned in custody). Facts come from the ledger state the last
tool unit returned."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'model_ref': Field('text', 'The immutable prediction model identity selected when the Episode closed'),
    'accepted_obligations': Field('list', 'The original obligations with accepted actual results'),
    'plans': Field('list', 'Each frozen plan: its reference, candidate, and whether its handoff is attached'),
    'credit_components': Field('record', 'The ledger credit by component (actual, model, validation)'),
    'launches_run': Field('integer', 'The launch children commissioned'),
    'monitors_run': Field('integer', 'The monitor children commissioned'),
    'acquisitions_run': Field('integer', 'The results children commissioned'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the allocation execution established', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity.', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody.',
                             required=False),
})


def _facts(summary):
    state = summary['state']
    return {'hpc_credit': state['hpc_credit']['credit'], 'hpc_model_ref': state['hpc_model_ref'],
            'hpc_accepted_obligations': list(state['hpc_accepted_obligations']),
            'hpc_result_refs': list(state['hpc_result_refs'])}


def final_to_parent(summary, completion, selection):
    facts = _facts(summary)
    state = summary['state']
    result = {'credit': completion['credit'],
              'finding': {'model_ref': facts['hpc_model_ref'],
                          'accepted_obligations': facts['hpc_accepted_obligations'],
                          'plans': [{'plan_ref': row['plan_ref'], 'candidate_id': row['candidate_id'],
                                     'handoff_attached': row['handoff_ref'] is not None}
                                    for row in state['hpc_plans']],
                          'credit_components': state['hpc_credit']['components'],
                          'launches_run': len(summary['launches']), 'monitors_run': len(summary['monitors']),
                          'acquisitions_run': len(summary['acquisitions'])}}
    for name in selection:
        result[name] = completion['credit'] if name == 'hpc_credit' else facts[name]
    return result
