"""The records passed in custody, and the plan, controller and credit rule (from the message). A commission that
names no controller has a finite target: one credit per plan step."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'subject_refs': Field('record_refs', 'The subject records, passed in custody'),
    'input_refs': Field('record_refs', 'Problem subjects of the Store, passed in custody', required=False),
    'held_refs': Field('record_refs', 'Other records passed in custody', required=False),
})


def read_from_parent(assignment, message):
    plan = message['plan']
    return {'subject_refs': assignment['subject_refs'], 'input_refs': assignment.get('input_refs', []),
            'held_refs': assignment.get('held_refs', []), 'plan': plan,
            'controller': message.get('controller', {'kind': 'completion', 'target': len(plan)}),
            'credit': message.get('credit', {'rule': 'units'})}
