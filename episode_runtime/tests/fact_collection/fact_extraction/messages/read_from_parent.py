"""What the parent gives: the records to read, passed in custody, and the field."""
from method_loop import Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'source_refs': Field('record_refs', 'The records to read, passed in custody'),
    'field': Field('text', 'The field to extract'),
})


def read_from_parent(assignment, message):
    return {'source_refs': assignment['source_refs'], 'field': assignment['field']}
