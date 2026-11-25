"""What the commissioner of an annotation gives: the subject (a Store scope) and the records already known for it.
Controlled data only: a Store scope and record references. The root starts with no proposed annotation: the candidate
annotations are what its heads find (the owner, 2026-11-25: "that is literally how this pipeline is supposed to always
start. with no proposed annotations period"). This is the only place the assignment is read; the commissioner's message
is not used."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope of the subject to annotate: its subject_refs and, when it has them, '
                             'its segments or read selections'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'evidence_refs': Field('record_refs', 'The evidence records already known for the subject, passed in custody'),
    'received_record_refs': Field('record_refs', 'Every further record an axis head reads that the evidence names, '
                                                 'passed in custody'),
})


def read_from_parent(assignment, message):
    return {'scope': assignment['scope'], 'scope_refs': assignment['scope_refs'],
            'evidence_refs': assignment['evidence_refs'],
            'received_record_refs': assignment['received_record_refs']}
