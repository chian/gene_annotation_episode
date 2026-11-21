"""The sequence records passed in custody and the plan of pairs."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'input_refs': Field('record_refs', 'The sequence records the pairs name, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'input_refs': assignment['input_refs'], 'plan': message['plan']}
