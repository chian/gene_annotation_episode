"""The return: the credit, the finding (how many plan steps were carried out) and the current sheets, in custody."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({'steps_done': Field('integer', 'Plan steps carried out')})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How much of the plan was carried out', form=FINDING_FORM),
    'current': Field('record_refs', 'The current partner sheets'),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': {'steps_done': summary['steps']},
            'current': summary['current']}
