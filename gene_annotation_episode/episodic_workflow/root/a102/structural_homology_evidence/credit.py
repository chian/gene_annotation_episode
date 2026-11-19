"""How the A102 head's credit is counted (carried from ``credit.py``, ``task_projector.py`` and the proposed
annotation check of the old ``credit_projector`` at ``97308b94c``).

Credit kind ``scientific``: the head's own projector for the commissioned ``a102_task``, called as a library
function over the records the Episode holds. ``task_projector.original_task_projector`` chose it: a named task
among ``functional_feature_geometry``, ``functional_contrast``, ``reference_attribution``,
``local_trait_attribution`` and ``interface_constraints`` has its own credit class; any other named task, or none,
takes the library's ``credit_projector`` of the merged A102 axis (native structural correspondence for the
comparative tasks, received retained scientific findings for the rest). The old branch for a library whose A102
entry is not the merged one (always ``A102StructuralCredit``) is not carried: the library's A102 axis is the merged
entry (``forms/protein_structure/structural_evidence.py``).

The old credit view was a record, not a number: ``credit`` plus ``axis_components``, ``retained_finding_count``,
``inactive_dependencies``, ``detail_pages`` and the sheets. ``credit_view`` makes it from the held records, once,
for ``messages/internal_summary.py`` (which shows it to the model); ``credit`` is its number. The projector read a
provider's values nowhere: every input is a held record, so ``credit`` needs no service. Credit is never bounded,
clamped or rescaled here.

The projectors are the library's: ``A102StructuralCredit`` and the five task credits in
``grading/structural_homology_evidence/credit.py`` and ``ScientificFindingProgress`` in
``findings/structural_homology_evidence/investigation_progress.py``. They still read the raw Store (``store.db``,
private ``_require``, ``read_snapshot``): library not carried; the call stays as written.
"""
from __future__ import annotations

import json

from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import (
    credit_projector, task_context)
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import (
    A102FeatureGeometryCredit, A102FunctionalContrastCredit, A102InterfaceContactCredit, A102LocalTraitCredit,
    A102ReferenceAttributionCredit)

LOCAL = {
    'functional_feature_geometry': A102FeatureGeometryCredit,
    'functional_contrast': A102FunctionalContrastCredit,
    'reference_attribution': A102ReferenceAttributionCredit,
    'local_trait_attribution': A102LocalTraitCredit,
    'interface_constraints': A102InterfaceContactCredit,
}


def projector(task_name):
    """The old ``original_task_projector`` of the merged axis: the task's own credit class, else the library's
    projector of the task (none: the library's finding progress)."""
    if task_name is None:
        return credit_projector({})
    local = LOCAL.get(task_name)
    if local is not None:
        return local()
    return credit_projector({'context': {'a102_task': task_context(task_name)}})


def credit_view(parent_input, records):
    """The old ``services.scientific_credit(context, receiver_selection)`` over the held records."""
    if not parent_input['proposed_annotation_ref']:
        raise ValueError('scientific_task_proposed_annotation_required')
    chosen = projector(parent_input['a102_task'])
    scope = parent_input['scope']
    assignment = {'scope': scope, 'context': parent_input['context'],
                  'proposed_annotation_ref': parent_input['proposed_annotation_ref'][0]}
    if chosen.requires_known_record_refs:
        view = chosen(records, scope, known_record_refs=list(records.refs()), assignment=assignment)
    else:
        known = [row['id'] for row in records.list('assessment', scope)]
        view = chosen(records, scope, known_assessment_refs=known, assignment=assignment)
    return json.loads(json.dumps(view, allow_nan=False))


def credit(summary, records):
    return float(summary['credit_view']['credit'])
