"""What the commissioner gives: the Store scope of the bare sequence, the records the scope names and, when there is any,
information that already exists about the sequence, all in custody. Controlled data only. Nothing about the sequence is
required: not what kind of sequence it is, not a feature, not a name. This is the only place the assignment is read; the
commissioner's message is not used."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope this episode investigates: its subject_refs are the sequences whose '
                             'features are to be found'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'evidence_refs': Field('record_refs', 'Information that already exists about the sequences (records the commissioner '
                                          'holds: features, graded sources and what they name), passed in custody',
                           required=False),
})


def read_from_parent(assignment, message):
    return {'scope': assignment['scope'], 'scope_refs': list(assignment['scope_refs']),
            'evidence_refs': list(assignment.get('evidence_refs', []))}
