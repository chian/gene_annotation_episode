"""The records passed in custody and the number of functions to run."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'held_refs': Field('record_refs', 'Records passed in custody'),
})


def read_from_parent(assignment, message):
    return {'held_refs': assignment['held_refs'], 'steps_planned': message['steps']}
