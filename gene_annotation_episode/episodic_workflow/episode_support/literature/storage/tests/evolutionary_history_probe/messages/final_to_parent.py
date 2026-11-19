"""What the plan did: the credit the system hands in and how many library calls returned."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({
    'calls': Field('integer', 'Library calls that returned'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How many library calls returned', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': {'calls': len(summary['outcomes'])}}
