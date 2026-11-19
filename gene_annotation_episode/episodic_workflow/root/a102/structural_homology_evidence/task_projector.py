"""The A102 head's credit projector for one commissioned structural evidence task."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import (A102StructuralCredit, A102FeatureGeometryCredit,
    A102FunctionalContrastCredit, A102ReferenceAttributionCredit,
    A102LocalTraitCredit, A102InterfaceContactCredit)
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import credit_projector, task_context

_TASK_CREDIT = {
    'functional_feature_geometry': A102FeatureGeometryCredit,
    'functional_contrast': A102FunctionalContrastCredit,
    'reference_attribution': A102ReferenceAttributionCredit,
    'local_trait_attribution': A102LocalTraitCredit,
    'interface_constraints': A102InterfaceContactCredit,
}


def original_task_projector(task, *, merged_a102):
    """The structural credit for a structural-only library entry, else the task's own projector."""
    context = task_context(task)
    if not merged_a102:
        return A102StructuralCredit()
    if task in _TASK_CREDIT:
        return _TASK_CREDIT[task]()
    return credit_projector({'context': {'a102_task': context}})
