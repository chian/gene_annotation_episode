"""The records passed in custody (the problem subjects) and the plan of scenarios."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'subject_refs': Field('record_refs', 'The problem subjects of the Store, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'subject_refs': assignment['subject_refs'], 'plan': message['plan']}
