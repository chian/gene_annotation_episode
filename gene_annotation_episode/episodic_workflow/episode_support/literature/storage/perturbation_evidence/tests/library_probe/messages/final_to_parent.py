"""The return: the Episode's credit and how many scenarios ran."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'scenarios': Field('integer', 'Scenarios commissioned'),
    'done': Field('integer', 'Scenarios that ran'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How many of the commissioned scenarios ran', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'],
            'finding': {'scenarios': len(summary['plan']), 'done': summary['steps']}}
