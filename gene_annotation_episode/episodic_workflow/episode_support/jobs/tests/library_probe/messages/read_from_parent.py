"""The records passed in custody and the plan."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'record_refs': Field('record_refs', 'The records the plan reads, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'record_refs': assignment['record_refs'], 'plan': message['plan']}
