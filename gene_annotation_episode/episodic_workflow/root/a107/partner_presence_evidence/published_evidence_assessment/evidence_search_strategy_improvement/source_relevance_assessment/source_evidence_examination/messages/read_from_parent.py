"""What the parent gives: the page assignment ``page_assignment_v1`` (the exact source to examine), the Store scope of
the commission, the finding unit of its credit and the records passed in custody. This is the only place the
assignment is read.

``version``, ``source_ref``, ``representation``, ``artifact_ref``, ``question_context_refs`` and
``prior_delivery_refs`` are the properties of the old assignment schema (old ``from_parent.py``, ``_PAGE``), under
their names; the whole assignment is the page. The old schema also took the partner fields of
``library.partner_source_contracts.assignment_schema_fields()``; that module has no placement, so their names are
unknown here. The one the carried code reads (the components whose cells the report returns, old
``context.assignment.get(requested_field, defaults)``) is declared as ``literature_partner_components`` (new field,
optional). ``scope``, ``finding_unit`` and ``received_record_refs`` are new fields: the old episode took the scope
from its request, its credit unit from the old runner's credit service and the records it had received from its
binding context; the new commission names them in its assignment.

The old checks of this file that needed the Store (the page's artifact against the source's artifact for the
representation, every reference in scope) were this episode's checks of its own commission and are not carried: a
wrong commission fails."""
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
    'literature_partner_components': Field('list', 'The requested partner components: when given, the reading opens with the partner-grading lead (new '
                                           'field: the old partner assignment field of partner_source_contracts, '
                                           'not placed); the library default when absent', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding (new field: the old runner '
                          'supplied it to its credit service)'),
    'received_record_refs': Field('record_refs', 'The source, its artifact, the sources it derives from and the '
                                  'subjects of the scope, passed in custody (new field: the old binding-context '
                                  'received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the page (the old assignment, flat), the scope, the finding unit, the passed records and the
    requested partner components."""
    return {'page': {name: assignment[name] for name in PAGE_FIELDS}, 'scope': assignment['scope'],
            'finding_unit': assignment['finding_unit'], 'received_record_refs': assignment['received_record_refs'],
            'partner_components': (assignment['literature_partner_components']
                                   if 'literature_partner_components' in assignment else None)}
