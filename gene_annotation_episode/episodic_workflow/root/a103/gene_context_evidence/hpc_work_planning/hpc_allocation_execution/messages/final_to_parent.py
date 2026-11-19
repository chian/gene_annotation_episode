"""The return. Always returned: the Episode's credit (the system hands it in ``completion``) and the finding. A parent
selects the facts it wants: ``hpc_credit``, ``hpc_model_ref``, ``hpc_accepted_obligations``, ``hpc_result_refs``,
``hpc_result_artifact_refs`` (the artifact of each result source, because a returned record does not bring the
records it names) and ``hpc_handoff_refs`` (the handoff records the Launch children returned and this Episode holds,
so the planner can pass them on).

``hpc_credit`` is the credit the controller last saw (``completion['credit']``), never a second computation.
``hpc_result_refs`` are the result sources this Episode's own ``hpc_results`` units produced."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'accepted_obligations': Field('list', 'The original obligations whose actual results were accepted'),
    'open_obligations': Field('list', 'The original obligations not accepted'),
    'plans': Field('list', 'The frozen plans this Episode saw'),
    'launched_plans': Field('list', 'The plans a Launch child was commissioned for'),
    'closed_plans': Field('list', 'The plans whose allocation is closed'),
    'credit_components': Field('record', 'The measured credit by component: actual, model and validation'),
    'model_ref': Field('text', 'The immutable selected prediction model identity'),
    'qualification': Field('text', 'What the credit does and does not establish'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What the execution of the HPC portfolio established', form=FINDING_FORM),
    'hpc_credit': Field('number', 'Signed measured credit; repeated polling adds none.', required=False),
    'hpc_model_ref': Field('text', 'Immutable selected prediction model identity.', required=False),
    'hpc_accepted_obligations': Field('list', 'Original obligations with accepted actual results.',
                                      required=False),
    'hpc_result_refs': Field('record_refs', 'Sources containing original result bytes and attempt custody.',
                             required=False),
    'hpc_result_artifact_refs': Field('record_refs', 'The artifact of each source in hpc_result_refs (new field).',
                                      required=False),
    'hpc_handoff_refs': Field('record_refs', 'The handoff records the Launch children returned (new field).',
                              required=False),
})

QUALIFICATION = ('Credit is the signed measured credit of the original ledger: obligations whose actual results '
                 'passed the frozen acceptance predicates, model improvement and fixed prospective forecast '
                 'validation. A launched handoff, a monitoring observation or elapsed time alone is not '
                 'accomplishment.')


def facts(summary, completion):
    """The facts this Episode recorded."""
    hpc = summary['hpc']
    handoffs = [ref for row in summary['launches'] for ref in row['handoff_refs']]
    return {'hpc_credit': completion['credit'], 'hpc_model_ref': hpc['model_ref'],
            'hpc_accepted_obligations': list(hpc['accepted_obligations']),
            'hpc_result_refs': list(summary['result_refs']),
            'hpc_result_artifact_refs': list(summary['result_artifact_refs']),
            'hpc_handoff_refs': list(dict.fromkeys(handoffs))}


def final_to_parent(summary, completion, selection):
    hpc = summary['hpc']
    recorded = facts(summary, completion)
    accepted = list(hpc['accepted_obligations'])
    finding = {'accepted_obligations': accepted,
               'open_obligations': [name for name in summary['commission']['obligations'] if name not in accepted],
               'plans': [plan['plan_id'] for plan in hpc['plans'].values()],
               'launched_plans': [hpc['plans'][row['plan_ref']]['plan_id'] for row in summary['launches']],
               'closed_plans': list(hpc['closed']),
               'credit_components': dict(hpc['credit_view']['components'] or {}),
               'model_ref': hpc['model_ref'], 'qualification': QUALIFICATION}
    result = {'credit': completion['credit'], 'finding': finding}
    for name in selection:
        result[name] = recorded[name]
    return result
