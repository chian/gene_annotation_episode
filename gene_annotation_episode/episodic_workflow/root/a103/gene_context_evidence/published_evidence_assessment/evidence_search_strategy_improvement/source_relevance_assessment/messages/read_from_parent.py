"""What the parent gives: the search assignment ``search_assignment_v1`` (the records that frame the question and the
returned sources to consider), the Store scope of the commission and the records passed in custody. This is the
only place the assignment is read.

``version``, ``question_context_refs`` and ``search_result_refs`` are the properties of the old assignment schema
(old ``from_parent.py``), under their names. ``scope`` and ``received_record_refs`` are new fields: the old episode
took the scope from its request and the records it had received from its binding context; the new commission names
both in its assignment. ``gene_context_evidence`` is the parent's constraints, context, evidence operands and
guidance, which the old request carried in its message. The old checks of this file (each reference in scope, each
search result a ``source`` record, an operation key) are not carried: they were the episode's checks of its own
commission, and a wrong commission fails."""
from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The search assignment version', 'search_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'search_result_refs': Field('record_refs', 'The returned sources to consider'),
    'scope': Field('record', "The Store scope of the commission: the parent's fixed subject and optional segments "
                             '(new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The search-result sources and their artifacts, passed in custody '
                                  '(new field: the old binding-context received records)'),
    'gene_context_evidence': Field('record', "The parent's constraints, context, evidence operands and guidance",
                                   required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the search assignment, the scope, the passed records, the parent's context when given and
    the commissioner's message."""
    parent_input = {name: assignment[name] for name in ASSIGNMENT_FORM.fields if name in assignment}
    parent_input['message'] = message
    return parent_input
