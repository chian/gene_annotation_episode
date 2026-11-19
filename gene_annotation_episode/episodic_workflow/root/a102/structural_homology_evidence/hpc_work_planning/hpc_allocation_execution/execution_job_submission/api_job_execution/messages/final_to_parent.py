"""What this episode returns. Selectable: ``execution_handoff_refs``, ``execution_result_refs``,
``execution_completed`` and ``execution_result_origin`` (the empty record: this episode retains no result window).
``credit`` is the system's ``completion['credit']``; ``finding`` says what was established about the request or
job."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'resource_id': Field('text', 'The configured API resource that ran the work'),
    'service': Field('text', 'The API service that carried out the work'),
    'handoff_established': Field('boolean', 'Whether a usable monitoring/results handoff was recorded'),
    'completed': Field('boolean', 'Whether the original handoff completion was verified'),
    'last_status': Field('text', 'The status of the last unit that ran, as the service reported it'),
    'interpretation': Field('text', "The model's latest interpretation of the job for the parent"),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'What was established about the assigned request or job', form=FINDING_FORM),
    'execution_handoff_refs': Field('record_refs', 'The records that hold the usable handoff', required=False),
    'execution_result_refs': Field('record_refs', 'The records that hold acquired results', required=False),
    'execution_completed': Field('boolean', 'Whether the original handoff completion is verified', required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (the empty record: no '
                                     'result window exists for this episode)', required=False),
})


def final_to_parent(summary, completion, selection):
    facts = {'execution_handoff_refs': summary['handoff_refs'], 'execution_result_refs': summary['result_refs'],
             'execution_completed': summary['completed'], 'execution_result_origin': {}}
    return {'credit': completion['credit'],
            'finding': {'resource_id': summary['resource_id'], 'service': summary['service'],
                        'handoff_established': bool(summary['handoff_refs']), 'completed': summary['completed'],
                        'last_status': 'none' if summary['last_status'] is None else summary['last_status'],
                        'interpretation': summary['report_update']},
            **{name: facts[name] for name in selection}}
