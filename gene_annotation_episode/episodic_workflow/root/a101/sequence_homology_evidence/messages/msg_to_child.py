"""The commission of each child. A commission is controlled data only: the model chooses among values this episode holds
(``task.commission_fields``: a subject of the scope, a program and a hosted database of fixed sets, a number in a range,
a bound API resource), and this file builds the child's assignment, in the child's own form, from those choices and this
episode's summary. The model writes no assignment, objective or message: the objective is this episode's own fixed text
for the slot and the message is empty. A commission the child does not admit fails (no check here).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the query subject record and,
in ``input_refs``, every held record it names, and those name in turn (a subject and its sequence artifact: ``_custody``
over the summary's ``named_refs``). When this episode holds an outstanding search of the query that the commission
names (``summary['database_searches']``), the commission continues it and code passes back, in custody, the records the
child returned for it: its handoff, status and closure records (the rows and what they name, as held). The credit units
are this episode's ``child_credit_units``: ``handoff_unit`` for the handoff, ``information_unit`` for a status request
that shows something new and ``acquired_record_unit`` for the graded result.

Required return fields: every kind of record the child returns for its search (handoff, status, closure and graded
records), so that this episode holds the whole record of the search and can pass it back on a later visit."""
from episode_runtime import ChildMessage

ANALYSIS_KIND = 'database_search'

# The objective of each commission: this episode's own text, never the model's.
OBJECTIVES = {
    'database_blast': 'Search the query sequence against the hosted database through the public BLAST service, follow '
                      'the search without waiting for it and return what it established: the handoff, the status '
                      'records and, when the service has finished it, the graded result.',
    'bvbrc_blast': 'Search the query sequence against the precomputed BV-BRC database through the BV-BRC application '
                   'service, in this one commission: estimate the duration, launch the search, monitor it until the '
                   'service has ended it and extract the graded result, and return what it established.',
}
# The return fields every commission of a slot selects.
REQUIRED_RETURN = {
    'database_blast': ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs'),
    'bvbrc_blast': ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs'),
}


def _selection(slot, arguments):
    return tuple(dict.fromkeys([*REQUIRED_RETURN[slot], *arguments.get('selection', [])]))


def _custody(references, summary):
    """The held records ``references`` with every held record they name, and those name in turn (the summary's
    ``named_refs``): a pass carries only the records named, and the child's code follows the names (a subject to its
    sequence)."""
    found, pending = [], list(references)
    while pending:
        reference = pending.pop(0)
        if reference not in found:
            found.append(reference)
            pending.extend(summary['named_refs'].get(reference, []))
    return found


def _database_blast(arguments, summary):
    """The assignment of one database search: the declared kind, the query and its sequence in custody, the program,
    the database, the hit-list size, the resource, the three credit units and, when the commission continues an
    outstanding search of the query, the records of that search passed back."""
    query = arguments['query_ref']
    units = summary['child_credit_units']
    assignment = {'analysis_kind': ANALYSIS_KIND, 'query_refs': [query],
                  'input_refs': [ref for ref in _custody([query], summary) if ref != query],
                  'program': arguments['program'], 'database': arguments['database'],
                  'hitlist_size': arguments['hitlist_size'], 'resource_id': arguments['resource_id'],
                  'handoff_unit': units['handoff_unit'], 'information_unit': units['information_unit'],
                  'graded_unit': units['acquired_record_unit']}
    held = [search for search in summary['database_searches'] if search['query_ref'] == query and search['outstanding']]
    if held:
        (search,) = held
        assignment.update(handoff_refs=[search['handoff_ref']], check_refs=search['check_refs'],
                          closure_refs=search['closure_refs'])
    return assignment


def _bvbrc_blast(arguments, summary):
    """The assignment of one BV-BRC database search: the query and its sequence in custody, the program, the database,
    the resource, ``until`` and the three credit units. When the commission continues an outstanding search of the query
    (``summary['bvbrc_searches']``) code passes back, in custody, the records the child returned for it: its handoff and
    status records and the closure record, with whether a status already shows it ended: nothing is submitted again."""
    query = arguments['query_ref']
    units = summary['child_credit_units']
    assignment = {'query_refs': [query], 'input_refs': [ref for ref in _custody([query], summary) if ref != query],
            'program': arguments['program'], 'database': arguments['database'], 'resource_id': arguments['resource_id'],
            'until': arguments['until'], 'handoff_unit': units['handoff_unit'],
            'information_unit': units['information_unit'], 'graded_unit': units['acquired_record_unit']}
    held = [search for search in summary['bvbrc_searches'] if search['query_ref'] == query and search['outstanding']]
    if held:
        (search,) = held
        assignment.update(handoff_refs=[search['handoff_ref']], check_refs=search['check_refs'],
                          closure_refs=search['closure_refs'], known_ended=search['known_ended'])
    return assignment


ASSIGNMENTS = {'database_blast': _database_blast, 'bvbrc_blast': _bvbrc_blast}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot], message={}, assignment=ASSIGNMENTS[slot](arguments, summary),
                        selection=_selection(slot, arguments))
