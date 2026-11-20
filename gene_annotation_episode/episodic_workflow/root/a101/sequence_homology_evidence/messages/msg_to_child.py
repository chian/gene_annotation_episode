"""The commission of each child. A commission is controlled data only: the model chooses among values this episode holds
(``task.commission_fields``: a program of the fixed set, a subject of the scope, a held subject record, a bound local
resource, the optional return fields), and this file builds the child's assignment, in the child's own form, from those
choices and this episode's summary. The model writes no assignment, objective or message: the objective is this
episode's own fixed text for the slot and the message is empty. A commission the child does not admit fails (no check
here).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the two subject records of a
pairwise comparison with every held record they name, and those name in turn (a subject and its sequence artifact:
``_custody`` over the summary's ``named_refs``). The credit unit (``information_unit``) is this episode's
``child_credit_units``.

Required return fields: a pairwise comparison returns the graded records its credit reads
(``execution_blast_graded_refs``: the saved sheet, the source it is retained on and the search row) and
``execution_completed``; the model may also select the handoff row and the job records of the job."""
from episode_runtime import ChildMessage

PAIRWISE_VERSION = 'pairwise_blast_assignment_v1'
PAIRWISE_KIND = 'pairwise'

# The objective of each commission: this episode's own text, never the model's.
OBJECTIVES = {
    'pairwise_blast': 'Compare the query sequence with the subject sequence by a pairwise BLAST and return the graded '
                      'correspondence of the two.',
}
# The return fields every commission of a slot selects.
REQUIRED_RETURN = {
    'pairwise_blast': ('execution_blast_graded_refs', 'execution_completed'),
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
            pending.extend(summary['named_refs'][reference])
    return found


def _pairwise(arguments, summary):
    """The assignment of one pairwise BLAST: the program, the one query and the one subject record, the local resource,
    the information unit and, in custody, the two subject records with the sequence artifacts they name."""
    query, subject = arguments['query_ref'], arguments['subject_ref']
    return {'version': PAIRWISE_VERSION, 'analysis_kind': PAIRWISE_KIND, 'program': arguments['program'],
            'query_refs': [query], 'subject_refs': [subject], 'resource_id': arguments['resource_id'],
            'information_unit': summary['child_credit_units']['information_unit'],
            'record_refs': list(dict.fromkeys([*_custody([query], summary), *_custody([subject], summary)]))}


ASSIGNMENTS = {'pairwise_blast': _pairwise}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot], message={}, assignment=ASSIGNMENTS[slot](arguments, summary),
                        selection=_selection(slot, arguments))
