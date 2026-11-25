"""What the commissioner gives: the Store scope of the DNA to place and the records the scope names, in custody.
Controlled data only. This is the only place the assignment is read; the commissioner's message is not used."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope this episode investigates: its subject_refs are the sequences to place'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
})


def read_from_parent(assignment, message):
    return {'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs'])}
