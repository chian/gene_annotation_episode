"""The records passed in custody and the plan."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'held_refs': Field('record_refs', 'The records the plan reads, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'held_refs': assignment['held_refs'], 'plan': message['plan']}
