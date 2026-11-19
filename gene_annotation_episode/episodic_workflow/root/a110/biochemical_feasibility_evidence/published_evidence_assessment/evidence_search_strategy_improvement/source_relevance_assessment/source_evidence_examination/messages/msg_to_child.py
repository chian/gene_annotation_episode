"""The three commissions. Carried from the old ``to_child_table_evidence_extraction.py``,
``to_child_source_coverage_improvement.py`` and ``to_child_passage_evidence_extraction.py`` (each assembled the
common request message and the child's assignment; the request, goal, receipt-binding and contract-declaration
machinery is the system's now) and from ``contracts.py`` (``_WINDOW``, ``_TABLE``).

Each child's assignment is ``reading_assignment_v1``: this episode's page, the selection the model chose, the
reaction cells this episode was asked for (their presence selects the child's reaction lead, R10), the scope,
the unit of finding credit and the records passed in custody. The records passed are the ones this episode was
given (the source, its artifact, the sources it derives from and the question's context records): a pass carries
exactly the records named. The selection is the model's ``ChildCall`` arguments in the shape each child declares:

- ``table_evidence_extraction``: ``kind`` ``table`` (``source_ref``, ``sheet_key``, ``offset``, ``limit``,
  optional ``header_row`` and ``where``) or ``window`` (``source_ref``, ``representation``, ``offset``,
  ``limit``); a null ``header_row`` or ``where`` of the old table schema is omitted;
- ``source_coverage_improvement``: ``window``, the one window the ordered reading starts from;
- ``passage_evidence_extraction``: ``spans``, one or more windows.

Nothing here checks the commission: a selection the child does not admit fails when the child is built."""
from episode_runtime import ChildMessage

VERSION = 'reading_assignment_v1'
OBJECTIVES = {
    'table_evidence_extraction': 'Investigate the selected table/sheet of this source and its scientific meaning',
    'source_coverage_improvement': 'Investigate this source in document order from the selected window',
    'passage_evidence_extraction': 'Investigate the supplied source-bound passages of this source',
}
# selectable return fields wanted (each is declared by the child's own return form)
SELECTIONS = {'table_evidence_extraction': (), 'source_coverage_improvement': (), 'passage_evidence_extraction': ()}


def table_selection(arguments):
    selection = {key: arguments[key] for key in ('kind', 'source_ref', 'offset', 'limit')}
    if arguments['kind'] == 'window':
        selection['representation'] = arguments['representation']
        return selection
    selection['sheet_key'] = arguments['sheet_key']
    if arguments['header_row'] is not None:
        selection['header_row'] = arguments['header_row']
    where = arguments['where']
    if where is not None:
        selection['where'] = {key: value for key, value in where.items() if value is not None}
    return selection


def window(value):
    return {key: value[key] for key in ('source_ref', 'representation', 'offset', 'limit')}


def msg_to_child(slot, arguments, summary):
    if slot == 'table_evidence_extraction':
        selection = table_selection(arguments)
    elif slot == 'source_coverage_improvement':
        selection = window(arguments)
    elif slot == 'passage_evidence_extraction':
        selection = {'spans': [window(span) for span in arguments['spans']]}
    else:
        raise KeyError(slot)
    assignment = {'version': VERSION, 'page': summary['page'], 'selection': selection, 'scope': summary['scope'],
                  'finding_unit': summary['finding_unit'], 'received_record_refs': summary['received_record_refs']}
    if summary['requested_reaction_components']:
        assignment['requested_reaction_components'] = summary['requested_reaction_components']
    return ChildMessage(objective=OBJECTIVES[slot], message={'page_source_ref': summary['page']['source_ref']},
                        assignment=assignment,
                        selection=SELECTIONS[slot])
