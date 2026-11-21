"""What the parent gives: the commission of one structure search, controlled values and record references only. This is the
only place the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one protein subject record of the parent's scope (the target), and ``input_refs``: the records its
sequence is read from, both passed in custody. ``database`` (one of the databases of the Foldseek route) and ``resource_id``
(the bound Foldseek resource) are chosen by the parent; the mode is not a field (fixed ``tmalign`` in the route).
``model_refs``: zero or one held data-product row of kind ``protein_structure_model``, passed in custody with the artifact it
names (and the records it names): when present the child uses it and ``get_model`` is never offered; when absent the child
obtains one. ``handoff_unit``, ``information_unit``, ``graded_unit`` and ``model_unit`` are the credits of the handoff, of an
estimate held or a status request that shows a fact the earlier ones did not, of the graded result and of a model obtained.
``until`` says where this commission ends: ``launched`` (estimate and launch, then the child parks: it returns at once with a
wait notice) or ``extracted`` (follow the job to its graded result; also how a parked job is resumed). On a resuming commission
the parent passes back, in custody, the records the earlier commission returned: ``handoff_refs``, ``check_refs`` and
``closure_refs`` (what the child's code reads to rebuild its state; the handoff row names the model file the job was given and
its identity), with ``known_ended`` (a passed-back status already shows the job ended); a resuming commission passes no model.
The commission's finite target is the credit still obtainable under ``until`` (``structure_search_child.read_common``)."""
from method_loop import ChoiceField, Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.jobs.foldseek_job_route import DATABASES
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    COMMON_ASSIGNMENT, read_common)

ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The target: exactly one protein subject record of the parent\'s scope, passed in '
                                       'custody'),
    'input_refs': Field('record_refs', 'The records the target\'s sequence is read from (its sequence artifact), passed in '
                                       'custody'),
    'database': ChoiceField('text', 'The structure database searched, as the Foldseek server spells it', tuple(DATABASES)),
    'resource_id': Field('text', 'The bound Foldseek resource of the job service the search is launched on'),
    **COMMON_ASSIGNMENT,
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    models = list(assignment.get('model_refs', []))
    if len(models) > 1:
        raise ValueError('structure_search_zero_or_one_model_required')
    common = read_common(assignment, 'structure_search')
    fields = {'database': assignment['database'], 'resource_id': assignment['resource_id']}
    return {'fields': fields, 'query_ref': query, 'model_ref': models[0] if models else None, **common}
