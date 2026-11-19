"""What the parent gives: the literature assignment ``literature_assignment_v1`` (the records that give the question
its context and the sources to examine), the Store scope of the commission and the records passed in custody. This is
the only place the assignment is read.

``version``, ``question_context_refs`` and ``source_refs`` are the properties of the old assignment schema (old
``from_parent.py``), under their names. ``scope`` and ``received_record_refs`` are new fields: the old episode took
the scope from its request and the records it had received from its binding context; the new commission names both
in its assignment. ``gene_context_evidence`` is the parent's constraints, context, evidence operands and guidance,
which the old request carried in its message. The old checks of this file (each reference in scope, ``source_refs``
being source records, a non-empty operation key) are not carried: they were the episode's checks of its own
commission, and a wrong commission fails."""
from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The literature assignment version', 'literature_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'source_refs': Field('record_refs', 'The source records assigned for examination'),
    'scope': Field('record', "The Store scope of the commission: the parent's fixed subject and optional segments "
                             '(new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The sources, their artifacts and the context records, passed in '
                                  'custody (new field: the old binding-context received records)'),
    'gene_context_evidence': Field('record', "The parent's constraints, context, evidence operands and guidance",
                                   required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the literature assignment, the scope, the passed records, the parent's context when given
    and the commissioner's message."""
    parent_input = {name: assignment[name] for name in ASSIGNMENT_FORM.fields if name in assignment}
    parent_input['message'] = message
    return parent_input
