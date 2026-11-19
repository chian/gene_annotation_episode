"""What the parent gives: the literature assignment ``literature_assignment_v1`` (the records giving the question
its context and the sources to examine), the Store scope of the commission and the records passed in custody.

``version``, ``question_context_refs`` and ``source_refs`` are the properties of the old assignment schema (old
``from_parent.py``, role ``literature``), under their names. ``scope`` and ``received_record_refs`` are new
fields: the old episode took the scope from its request and the records it had received from its binding context;
the new commission names both in its assignment. The old checks of this file that needed the Store (every
reference in scope, ``source_refs`` being source records, the operation key, the unreachable ``literature_page``
branch) are not carried: they were this episode's checks of its own commission, and a wrong commission fails (see
the carried-over table)."""
from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FIELDS = ('version', 'question_context_refs', 'source_refs')

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The literature assignment version', 'literature_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'source_refs': Field('record_refs', 'The source records the investigation starts from'),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'received_record_refs': Field('record_refs', 'The records passed in custody: the question context and the '
                                  'sources (new field: the old binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the literature assignment (flat), the scope and the passed records."""
    return {'assignment': {name: assignment[name] for name in ASSIGNMENT_FIELDS}, 'scope': assignment['scope'],
            'received_record_refs': assignment['received_record_refs'], 'message': message}
