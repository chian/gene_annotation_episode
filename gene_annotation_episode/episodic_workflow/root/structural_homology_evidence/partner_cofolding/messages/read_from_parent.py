"""What the parent gives: the commission of one co-folding job, controlled values and record references only. This is the only place
the assignment is read. A wrong commission raises and the run fails; nothing repairs it.

``query_refs``: exactly one protein subject record of the parent's scope (the target), and ``input_refs``: the records its sequence is
read from, both passed in custody. ``ligands``: two to four distinct ligand candidate names ``ligand:<chemical component id>`` the
parent holds and has not had co-folded for this target; ``resource_id`` (a bound resource of kind ``pbs``): both chosen by the parent.
The allocation of the job is the run's setting, not a field. ``handoff_unit``, ``information_unit`` and ``graded_unit`` are the credits
of the handoff, of an estimate held or a status request that shows a fact the earlier ones did not, and of the graded result. ``until``
says where this commission ends: ``launched`` (estimate and launch, then the child parks: it returns at once with a wait notice) or
``extracted`` (follow the job to its graded result; also how a parked job is resumed). On a resuming commission the parent passes back,
in custody, the records the earlier commission returned: ``handoff_refs``, ``check_refs`` and ``closure_refs`` (what the child's code
reads to rebuild its state), with ``known_ended`` (a passed-back status already shows the job ended). The commission's finite target is
the credit still obtainable under ``until`` (``structure_search_child.read_common``, without a model)."""
import re

from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.partner_cofolding import (
    LIGAND_COUNT, LIGAND_PATTERN)
from gene_annotation_episode.episodic_workflow.episode_support.tools.structure_search.structural_homology_evidence.structure_search_child import (
    COMMON_ASSIGNMENT, read_common)

ASSIGNMENT_FORM = RecordForm({
    'query_refs': Field('record_refs', 'The target: exactly one protein subject record of the parent\'s scope, passed in custody'),
    'input_refs': Field('record_refs', 'The records the target\'s sequence is read from (its sequence artifact), passed in custody'),
    'ligands': Field('list', 'The ligand candidates to co-fold with the target, one at a time: two to four distinct names '
                             'ligand:<chemical component id>, held by the parent'),
    'resource_id': Field('text', 'The bound PBS resource the co-folding job is launched on'),
    **{name: spec for name, spec in COMMON_ASSIGNMENT.items() if name not in ('model_unit', 'model_refs')},
})


def read_from_parent(assignment, message):
    (query,) = assignment['query_refs']
    ligands = list(assignment['ligands'])
    if (not LIGAND_COUNT[0] <= len(ligands) <= LIGAND_COUNT[1] or len(set(ligands)) != len(ligands)
            or any(type(ligand) is not str or re.fullmatch(LIGAND_PATTERN, ligand) is None for ligand in ligands)):
        raise ValueError('partner_cofolding_two_to_four_distinct_ligand_names_required')
    common = read_common(assignment, 'partner_cofolding', with_model=False)
    return {'fields': {'ligands': ligands, 'resource_id': assignment['resource_id']}, 'query_ref': query, **common}
