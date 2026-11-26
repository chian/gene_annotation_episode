"""The commission of the search child. A commission is controlled data only: the model chooses among values this episode
holds (``task.search_fields``: a held sequence, a program and a database of fixed sets, a bound BV-BRC service, where to
stop), and this file builds the child's assignment, in the child's own form, from those choices and this episode's
summary. The model writes no assignment, objective or message: the objective is this episode's own fixed text and the
message is empty. A commission the child does not admit fails (no check here).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the searched sequence's record
and, in ``input_refs``, every held record it names, and those name in turn (its sequence artifact and, for a sequence
derived from another, the sequence it was derived from: ``_custody`` over the summary's ``named_refs``). When this episode
holds that same search (the sequence, the program and the database) still running (``summary['searches']``), the
commission continues it and code
passes back, in custody, the records the child returned for it: its handoff, status and closure records.

Required return fields: every kind of record the child returns for its search (handoff, status, closure and graded
records, the kept claims among the graded ones), so that this episode holds the search's rows, reads its state from them
and can pass them back on a later visit."""
from episode_runtime import ChildMessage

OBJECTIVE = ('Search the assigned sequence against the precomputed BV-BRC database through the BV-BRC application '
             'service, in this one commission: estimate the duration, launch the search, monitor it until the service '
             'has ended it and extract the graded result with the claims its hits make, and return what it established.')
REQUIRED_RETURN = ('execution_handoff_refs', 'check_refs', 'closure_refs', 'graded_refs')
# The credit of the child's own steps (its completion controller counts them): the search launched, a status that shows
# something new, the graded result.
SEARCH_UNITS = {'handoff_unit': 1.0, 'information_unit': 1.0, 'graded_unit': 1.0}


def _custody(references, summary):
    """The held records ``references`` with every held record they name, and those name in turn (the summary's
    ``named_refs``): a pass carries only the records named, and the child's code follows the names."""
    found, pending = [], list(references)
    while pending:
        reference = pending.pop(0)
        if reference not in found:
            found.append(reference)
            pending.extend(summary['named_refs'].get(reference, []))
    return found


def _continued(assignment, search, summary):
    """The assignment of a commission that continues the held ``search``: its handoff, status and closure rows, passed
    back, and in ``input_refs`` every held record the rows name (and those name in turn)."""
    rows = [search['handoff_ref'], *search['check_refs'], *search['closure_refs']]
    assignment.update(handoff_refs=[search['handoff_ref']], check_refs=search['check_refs'],
                      closure_refs=search['closure_refs'], known_ended=search['known_ended'],
                      input_refs=list(dict.fromkeys([*assignment['input_refs'],
                                                     *(ref for ref in _custody(rows, summary) if ref not in rows)])))


def msg_to_child(slot, arguments, summary):
    searched = arguments['searched_ref']
    # the child settles the feature records after it keeps its claims, from every graded source held: it is passed
    # every source and feature record this episode holds, with the records they name
    statements = [ref for ref in summary['held_record_refs'] if ref.split('_')[0] in ('source', 'feature')]
    assignment = {'searched_refs': [searched],
                  'input_refs': [ref for ref in _custody([searched, *statements], summary)
                                 if ref != searched and not ref.startswith('row_')],
                  'program': arguments['program'], 'database': arguments['database'],
                  'resource_id': arguments['resource_id'], 'until': arguments['until'], **SEARCH_UNITS}
    running = [search for search in summary['searches'] if search['outstanding']
               and (search['query_ref'], search['program'], search['database'])
               == (searched, arguments['program'], arguments['database'])]
    if running:
        (search,) = running
        _continued(assignment, search, summary)
    return ChildMessage(objective=OBJECTIVE, message={}, assignment=assignment, selection=REQUIRED_RETURN)
