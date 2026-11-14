"""Validate the original literature owner's declared scientific yield settings."""
import math
from gene_annotation_episode.domain import ContractError
from ..numerical import YieldController, YieldParameters

YIELD_TASKS = frozenset(
    f'{axis}:{task}' for axis in ('A105', 'A106', 'A108')
    for task in ('verified_source_leads', 'source_answer:assessment',
        'source_answer:screening')) | frozenset((
    'A105:source_answer:measurement', 'A105:experiments', 'A105:assembly'))


def validate_yield_bindings(bindings):
    """Validate the literature owner's exact task declarations before work."""
    if not isinstance(bindings, dict):
        raise ContractError('literature_yield_bindings_object_required')
    result = {}
    for key, declaration in bindings.items():
        if key not in YIELD_TASKS or not isinstance(declaration, dict) or set(declaration) != {
                'credit_unit', 'kind', 'cutoff', 'uncertainty_alpha'}:
            raise ContractError('literature_yield_task_binding_invalid:' + str(key))
        expected_kind = ('accumulation' if key.endswith(':verified_source_leads')
            else 'remaining_commissioned_credit')
        if declaration['kind'] != expected_kind:
            raise ContractError('literature_yield_task_kind_mismatch:' + key)
        unit = declaration['credit_unit']
        if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
            raise ContractError('literature_yield_credit_unit_invalid:' + key)
        try:
            YieldController('configuration', 0, declaration['cutoff'],
                YieldParameters(uncertainty_alpha=declaration['uncertainty_alpha']))
        except (TypeError, ValueError) as error:
            raise ContractError('literature_yield_settings_invalid:' + key) from error
        result[key] = dict(declaration)
    return result


