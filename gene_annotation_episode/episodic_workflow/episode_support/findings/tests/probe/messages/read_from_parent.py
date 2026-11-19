"""The records passed in custody and the plan."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'subject_refs': Field('record_refs', 'The subject records, passed in custody'),
    'input_refs': Field('record_refs', 'Problem subjects of the Store, passed in custody', required=False),
    'held_refs': Field('record_refs', 'Other records passed in custody', required=False),
})


def read_from_parent(assignment, message):
    return {'subject_refs': assignment['subject_refs'], 'input_refs': assignment.get('input_refs', []),
            'held_refs': assignment.get('held_refs', []), 'plan': message['plan']}
