"""The records passed in custody and the plan of library calls."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'input_refs': Field('record_refs', 'Problem subjects of the Store, passed in custody'),
    'held_refs': Field('record_refs', 'Other records passed in custody', required=False),
})


def read_from_parent(assignment, message):
    return {'input_refs': assignment['input_refs'], 'held_refs': assignment.get('held_refs', []),
            'plan': message['plan']}
