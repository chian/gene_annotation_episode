"""What the commissioner of an annotation gives: the subject, the proposed annotation and the records already
known for them. Controlled data only: a Store scope and record references. This is the only place the assignment
is read; the commissioner's message is not used."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'scope': Field('record', 'The Store scope of the subject to annotate: its subject_refs and, when it has them, '
                             'its segments or read selections'),
    'scope_refs': Field('record_refs', 'The records the scope names, passed in custody'),
    'proposed_annotation_ref': Field('record_refs', 'The proposed annotation the nine axes evaluate: one '
                                                    'hypothesis record, passed in custody'),
    'evidence_refs': Field('record_refs', 'The evidence records already known for the subject, passed in custody'),
    'received_record_refs': Field('record_refs', 'Every further record an axis head reads that the proposed '
                                                 'annotation and the evidence name, passed in custody'),
    'source_dna_refs': Field('record_refs', 'The DNA the subject is from, when the commissioner holds it: the one '
                                            'sequence record of that DNA and the records it names, passed in custody. '
                                            'Nothing about the organism is given with it: the organism identification '
                                            'head works it out', required=False),
})


def read_from_parent(assignment, message):
    (proposed,) = assignment['proposed_annotation_ref']
    return {'scope': assignment['scope'], 'scope_refs': assignment['scope_refs'],
            'proposed_annotation_ref': proposed, 'evidence_refs': assignment['evidence_refs'],
            'received_record_refs': assignment['received_record_refs'],
            'source_dna_refs': list(assignment.get('source_dna_refs', []))}
