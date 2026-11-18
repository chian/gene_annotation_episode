"""Original own-A102 Scientific original_task_projector."""
from ..communication import plain
from ..domain import ContractError
from ..a102_credit import (A102StructuralCredit, A102FeatureGeometryCredit,
    A102FunctionalContrastCredit, A102ReferenceAttributionCredit,
    A102LocalTraitCredit, A102InterfaceContactCredit)
from ..a102_structural_evidence import credit_projector, task_context


def original_task_projector(assignment, *, merged_a102=False):
    assigned = plain(assignment)
    context = assigned.get('context', {})
    if not merged_a102:
        return A102StructuralCredit()
    task = context.get('a102_task')
    if task is not None and (not isinstance(task, dict)
            or task != task_context(task.get('name'))):
        raise ContractError('a102_original_task_definition_required')
    if task is None:
        return credit_projector(assigned)
    local = {
        'functional_feature_geometry': A102FeatureGeometryCredit,
        'functional_contrast': A102FunctionalContrastCredit,
        'reference_attribution': A102ReferenceAttributionCredit,
        'local_trait_attribution': A102LocalTraitCredit,
        'interface_constraints': A102InterfaceContactCredit,
    }.get(task['name'])
    return local() if local is not None else credit_projector(assigned)
