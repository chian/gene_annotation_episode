"""The commission of the child. A commission is controlled data only: the model chooses among values this episode holds
(``task.commission_fields``: a protein sequence of the scope, a database and a bound Foldseek resource of fixed sets, a held model
of the target or the fixed value that tells the child to obtain one, and where the commission ends), and this file builds the
child's assignment, in the child's own form, from those choices and this episode's summary. The model writes no assignment,
objective or message: the objective is this episode's own fixed text and the message is empty. A commission the child does not admit
fails (the check is the head's ``task.check_structure_search``, before the child exists).

Every record the child's code reads is named in a ``record_refs`` field of the assignment: the query subject record and, in
``input_refs``, every held record it names (a subject and its sequence artifact: ``_custody`` over the summary's ``named_refs``).
WHEN A HELD MODEL IS PASSED the row of the data product ``protein_structure_model`` goes in ``model_refs`` and, in ``input_refs``,
the artifact it names (the model file the child stages for the job): a data-product row passed alone does not hold the artifact it
names (``docs/plan/designs/a102_structure_search_episode.md``). When this episode holds an outstanding job of the search that the
commission names (``summary['structure_search_jobs']``), the commission continues it: code passes back, in custody, the records the
child returned for it, its handoff, status and closure rows with everything they name (the model file the job was given and its
identity: a continuation reads its model from the handoff row, so no model is passed), and nothing is submitted again. The credit
units are this episode's ``child_credit_units``: ``handoff_unit`` for the handoff, ``information_unit`` for an estimate held and a
status request that shows something new, ``acquired_record_unit`` for the graded result and ``model_unit`` for a model the child
obtained.

Required return fields: every kind of record the child returns for its job (handoff, status, closure and graded records), so that
this episode holds the job's rows, reads its state from them and can pass them back on a later visit."""
from episode_runtime import ChildMessage

from ..credit import OBTAIN

OBJECTIVES = {
    'structure_search': 'Search the target sequence against the structure database through a model of the target on the Foldseek '
                        'structure search server, in this one commission: obtain the model unless one is passed, estimate the '
                        'duration, launch the search and, when the commission goes to its result, monitor it until the service '
                        'has ended it and extract the graded result, and return what it established.',
}
REQUIRED_RETURN = {
    'structure_search': ('execution_handoff_refs', 'execution_check_refs', 'execution_closure_refs', 'graded_refs'),
}


def _custody(references, summary):
    """The held records ``references`` with every held record they name, and those name in turn (the summary's
    ``named_refs``): a pass carries only the records named, and the child's code follows the names (a subject to its sequence, a
    model row to its file)."""
    found, pending = [], list(references)
    while pending:
        reference = pending.pop(0)
        if reference not in found:
            found.append(reference)
            pending.extend(summary['named_refs'].get(reference, []))
    return found


def _structure_search(arguments, summary):
    """The assignment of one structure search: the query and its sequence in custody, the database, the resource, ``until``, the
    four credit units, the held model (its row in ``model_refs``, the row and the artifact it names in custody) when one is
    passed, and, when the commission continues an outstanding job of the same search, the records of that job passed back."""
    query, units = arguments['query_ref'], summary['child_credit_units']
    named = [ref for ref in _custody([query], summary) if ref != query]
    assignment = {'query_refs': [query], 'database': arguments['database'], 'resource_id': arguments['resource_id'],
                  'until': arguments['until'], 'handoff_unit': units['handoff_unit'],
                  'information_unit': units['information_unit'], 'graded_unit': units['acquired_record_unit'],
                  'model_unit': units['model_unit']}
    held = [job for job in summary['structure_search_jobs'] if job['outstanding'] and job['resource_id'] == arguments['resource_id']
            and job['identity']['query_ref'] == query and job['identity']['database'] == arguments['database']]
    if held:
        (job,) = held
        rows = [job['handoff_ref'], *job['check_refs'], *job['closure_refs']]
        assignment.update(handoff_refs=[job['handoff_ref']], check_refs=job['check_refs'], closure_refs=job['closure_refs'],
                          known_ended=job['known_ended'],
                          input_refs=list(dict.fromkeys([*named, *(ref for ref in _custody(rows, summary) if ref not in rows)])))
    elif arguments['model_ref'] != OBTAIN:
        model = arguments['model_ref']
        assignment.update(model_refs=[model], input_refs=list(dict.fromkeys(
            [*named, *(ref for ref in _custody([model], summary) if ref != model)])))
    else:
        assignment['input_refs'] = named
    return assignment


ASSIGNMENTS = {'structure_search': _structure_search}


def msg_to_child(slot, arguments, summary):
    return ChildMessage(objective=OBJECTIVES[slot], message={}, assignment=ASSIGNMENTS[slot](arguments, summary),
                        selection=REQUIRED_RETURN[slot])
