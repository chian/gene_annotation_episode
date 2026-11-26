"""What the commissioner gives: the Store scope of the DNA to place and the records the scope names, in custody, and,
optionally, records that already exist and bear on the question (``evidence_refs``, in custody): the taxon claims another
episode kept (the source of a claim sheet, its retained grading and what they name), which the scoring sheet reads among
the sources this episode holds. Controlled data only. This is the only place the assignment is read; the commissioner's
message is not used."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope this episode investigates: its subject_refs are the sequences to place'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'evidence_refs': Field('record_refs', 'Records that already exist and bear on which organism the sequences are from, '
                                          'passed in custody: the source of each taxon claim sheet and what it names',
                           required=False),
})


def read_from_parent(assignment, message):
    return {'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
            'evidence_refs': list(assignment.get('evidence_refs', []))}
