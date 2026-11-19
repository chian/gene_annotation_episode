"""What the commission returns: the credit and how many functions were run."""
from method_loop import Field, RecordForm

FINDING_FORM = RecordForm({'functions_run': Field('integer', 'Functions run')})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'How many functions were run', form=FINDING_FORM),
})


def final_to_parent(summary, completion, selection):
    return {'credit': completion['credit'], 'finding': {'functions_run': completion['units_consumed']}}
