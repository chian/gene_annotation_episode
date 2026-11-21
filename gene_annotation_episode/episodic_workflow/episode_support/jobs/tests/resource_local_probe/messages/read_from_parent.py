"""The inputs passed in custody (what an execution may stage) and the plan."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'input_refs': Field('record_refs', 'The inputs an execution may stage, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'input_refs': assignment['input_refs'], 'plan': message['plan']}
