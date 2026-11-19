"""What the commissioner gives: the subject records in custody, optionally the field to extract, and
references named only for context."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'subject_refs': Field('record_refs', 'The subject records, passed in custody'),
    'field': Field('text', 'The subject field to extract, when the commissioner has chosen it', required=False),
    'context_refs': Field('list', 'Records named for context only; this episode does not hold them',
                          required=False),
})


def read_from_parent(assignment, message):
    return {'subject_refs': assignment['subject_refs'], 'field': assignment.get('field'),
            'context_refs': assignment.get('context_refs', []), 'fields': message['fields']}
