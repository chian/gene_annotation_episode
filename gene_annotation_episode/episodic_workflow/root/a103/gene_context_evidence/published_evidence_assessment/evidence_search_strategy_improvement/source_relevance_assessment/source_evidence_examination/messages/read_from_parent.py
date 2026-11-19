"""What the parent gives: the page assignment ``page_assignment_v1`` (one source in one representation), the Store
scope of the commission and the records passed in custody. This is the only place the assignment is read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and
``prior_delivery_refs`` are the properties of the old assignment schema (old ``from_parent.py``, ``_PAGE``), under
their names. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its request
and the records it had received from its binding context; the new commission names both in its assignment.
``gene_context_evidence`` is the parent's constraints, context, evidence operands and guidance, which the old
request carried in its message. The old checks of this file that needed the Store (the page's artifact against the
source's artifact for the representation, the references in scope) are not carried: they were the episode's checks
of its own commission, and a wrong commission fails (see the carried-over table)."""
from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The source to examine'),
    'representation': ChoiceField('text', 'The representation of the source that is read', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this source'),
    'scope': Field('record', "The Store scope of the commission: the parent's fixed subject and optional segments "
                             '(new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact and the sources it derives from, passed '
                                  'in custody (new field: the old binding-context received records)'),
    'gene_context_evidence': Field('record', "The parent's constraints, context, evidence operands and guidance",
                                   required=False),
})


def read_from_parent(assignment, message):
    """The parent input: the page, the scope, the passed records, the parent's context when given and the
    commissioner's message."""
    parent_input = {name: assignment[name] for name in ASSIGNMENT_FORM.fields if name in assignment}
    parent_input['message'] = message
    return parent_input
