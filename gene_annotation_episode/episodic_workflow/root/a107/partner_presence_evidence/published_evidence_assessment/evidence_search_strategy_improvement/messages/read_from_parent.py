"""What the parent gives: the strategy assignment ``strategy_assignment_v1`` (the records that give the question its
context and the earlier searches), the Store scope of the commission, the finding unit of its credit and the records
passed in custody. This is the only place the assignment is read.

``version``, ``question_context_refs`` and ``prior_search_refs`` are the properties of the old assignment schema
(old ``from_parent.py``), under their names. The old schema also took the partner fields of
``library.partner_source_contracts.assignment_schema_fields()``; that module has no placement, so their names are
unknown here. The one the carried code reads (the components whose cells the report returns, old
``context.assignment.get(requested_field, defaults)``) is declared as ``literature_partner_components`` (new field,
optional, the name the child declares). ``scope``, ``finding_unit`` and ``received_record_refs`` are new fields: the
old episode took the scope from its request, its credit unit from the old runner's credit service and the records
it had received from its binding context; the new commission names them in its assignment.

The old checks of this file that needed the Store (every ``*_refs`` entry in scope, ``prior_search_refs`` of kind
``source``) were this episode's checks of its own commission and are not carried: a wrong commission fails."""
from method_loop import DeclaredField, Field, RecordForm

ASSIGNMENT_FORM = RecordForm({
    'version': DeclaredField('text', 'The strategy assignment version', 'strategy_assignment_v1'),
    'question_context_refs': Field('record_refs', 'Records giving the assigned question its context'),
    'prior_search_refs': Field('record_refs', 'The source records of the earlier searches'),
    'literature_partner_components': Field('list', 'The partner components whose cells the report may return (new '
                                           'field: the old partner assignment field of partner_source_contracts, '
                                           'not placed); the library default when absent', required=False),
    'scope': Field('record', 'The Store scope of the commission (new field: the old request scope)'),
    'finding_unit': Field('number', 'The credit of one distinct retained finding (new field: the old runner '
                          'supplied it to its credit service)'),
    'received_record_refs': Field('record_refs', 'The earlier searches, their artifacts, the sources they derive '
                                  'from and the subjects of the scope, passed in custody (new field: the old '
                                  'binding-context received records)'),
})


def read_from_parent(assignment, message):
    """The parent input: the question context, the earlier searches, the scope, the finding unit, the passed records
    and the requested partner components."""
    return {'question_context_refs': assignment['question_context_refs'],
            'prior_search_refs': assignment['prior_search_refs'], 'scope': assignment['scope'],
            'finding_unit': assignment['finding_unit'], 'received_record_refs': assignment['received_record_refs'],
            'partner_components': (assignment['literature_partner_components']
                                   if 'literature_partner_components' in assignment else None)}
