"""What the parent gives: the page assignment ``page_assignment_v1`` (the exact source to examine), the Store scope
of the commission and the records passed in custody.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and
``prior_delivery_refs`` are the properties of the old assignment schema (old ``from_parent.py``, ``_PAGE``), under
their names. ``scope`` and ``received_record_refs`` are new fields: the old episode took the scope from its request
and the records it had received from its binding context; the new commission names both in its assignment.
The old checks of this file that needed the Store (the page's artifact against the source's artifact for the
representation, every reference in scope) are not carried: they were this episode's checks of its own commission,
and a wrong commission fails (see the carried-over table)."""
from method_loop import ChoiceField, DeclaredField, Field, RecordForm

REPRESENTATIONS = ('text', 'original', 'stdout', 'stderr')
PAGE_FIELDS = ('version', 'source_ref', 'representation', 'artifact_ref', 'question_context_refs',
               'prior_delivery_refs')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The page assignment version', 'page_assignment_v1'),
    'source_ref': Field('text', 'The exact source to examine'),
    'representation': ChoiceField('text', 'The representation of the source that is examined', REPRESENTATIONS),
    'artifact_ref': Field('text', "The source's artifact for that representation"),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_delivery_refs': Field('record_refs', 'Records delivered by earlier examinations of this source'),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact and the sources it derives from, passed '
                                  'in custody (new field: the old binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page (the old assignment, flat), the scope and the passed records."""
    return {'page': {name: assignment[name] for name in PAGE_FIELDS}, 'scope': assignment['scope'],
            'received_record_refs': assignment['received_record_refs'], 'message': message}
