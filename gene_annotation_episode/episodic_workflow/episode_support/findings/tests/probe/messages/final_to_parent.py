"""The Episode's credit and how much of the plan was carried out."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'plan_steps': Field('integer', 'Steps of the commissioned plan'),
    'steps_done': Field('integer', 'Plan steps carried out'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How much of the plan was carried out', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {'plan_steps': len(summary['plan']), 'steps_done': summary['steps']}}
