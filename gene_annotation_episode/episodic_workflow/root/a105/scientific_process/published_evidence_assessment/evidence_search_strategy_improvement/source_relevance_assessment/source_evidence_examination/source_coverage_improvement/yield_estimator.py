"""Private yield for the original literature_ordered commission."""
from __future__ import annotations
from dataclasses import dataclass, replace
import json
import math
import heapq
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.numerical import NumericBand, STATUS_NORMAL, YieldController, YieldEstimate, YieldParameters, estimate_score_yield
import json
from gene_annotation_episode.domain import ContractError
VERSION = 'literature_local_task_v1'
SCREENING = 'literature_screening_answers'
LEADS = 'literature_source_lead_dispositions'
YIELD_TASKS = frozenset((f'A105:{task}' for task in ('verified_source_leads', 'source_answer:assessment', 'source_answer:screening'))) | frozenset(('A105:source_answer:measurement', 'A105:experiments', 'A105:assembly'))
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import YIELD_TASKS, _task_key, _yield_kind, commissioned_task, continuation_task

def validate_yield_bindings(bindings):
    """Validate this episode's exact task declarations before work."""
    if not isinstance(bindings, dict):
        raise ContractError('literature_yield_bindings_object_required')
    result = {}
    for key, declaration in bindings.items():
        if key not in YIELD_TASKS or not isinstance(declaration, dict) or set(declaration) != {'credit_unit', 'kind', 'cutoff', 'uncertainty_alpha'}:
            raise ContractError('literature_yield_task_binding_invalid:' + str(key))
        expected_kind = 'accumulation' if key.endswith(':verified_source_leads') else 'remaining_commissioned_credit'
        if declaration['kind'] != expected_kind:
            raise ContractError('literature_yield_task_kind_mismatch:' + key)
        unit = declaration['credit_unit']
        if type(unit) not in (int, float) or not math.isfinite(unit) or unit <= 0:
            raise ContractError('literature_yield_credit_unit_invalid:' + key)
        try:
            YieldController('configuration', 0, declaration['cutoff'], YieldParameters(uncertainty_alpha=declaration['uncertainty_alpha']))
        except (TypeError, ValueError) as error:
            raise ContractError('literature_yield_settings_invalid:' + key) from error
        result[key] = dict(declaration)
    return result

@dataclass(frozen=True)
class _RemainingCommissionedCredit:
    """Forecast another action against this episode's finite requested answer."""
    maximum_credit: float
    initial_credit: float

    def __call__(self, raw_signed_history, parameters, aligned_original_contexts):
        history = tuple(raw_signed_history)
        contexts = tuple(aligned_original_contexts)
        if len(history) != len(contexts):
            raise ValueError('literature_yield_requires_aligned_actions')
        current_credit = math.fsum((self.initial_credit, *history))
        remaining = max(0.0, self.maximum_credit - current_credit)
        if remaining == 0.0:
            return YieldEstimate(len(history), NumericBand.exact(0.0), parameters, {'completed_acquisition_turns': len(history), 'history_used': len(history), 'remaining_commissioned_credit': 0.0, 'commissioned_credit_capacity': self.maximum_credit, 'completion': 'all_requested_answers_earned'}, self.as_record())
        estimate = estimate_score_yield(history, parameters, contexts=contexts)
        band = estimate.expected_next_gain
        if band.status_code == STATUS_NORMAL:
            band = type(band)(min(band.value, remaining), min(band.lower, remaining), min(band.upper, remaining), band.status_code, band.uncertainty_code, band.alpha)
        return replace(estimate, expected_next_gain=band, diagnostics={**estimate.diagnostics, 'remaining_commissioned_credit': remaining, 'commissioned_credit_capacity': self.maximum_credit}, estimator_binding=self.as_record())

    def as_record(self):
        return {'version': 'literature_remaining_commissioned_credit_v1', 'base_estimator': 'gene_annotation_episode.episodic_workflow.root.a105.numerical.estimate_score_yield', 'maximum_credit': self.maximum_credit, 'initial_credit': self.initial_credit, 'forecast': 'observed_next_action_yield_bounded_by_remaining_commissioned_credit', 'terminal_forecast': 'exact_zero_when_all_requested_answers_earned'}

def _private_yield_controller(context, initial_credit, epoch, declaration):
    task, _ = commissioned_task(context)
    settings = task.get('yield_settings')
    if settings is None:
        raise ContractError('literature_original_task_yield_settings_required')
    if task['credit_unit'] != declaration['credit_unit'] or settings != {key: declaration[key] for key in ('kind', 'cutoff', 'uncertainty_alpha')} or settings['kind'] != _yield_kind(task):
        raise ContractError('literature_original_task_yield_binding_mismatch:' + _task_key(task))
    cutoff = settings['cutoff']
    parameters = YieldParameters(uncertainty_alpha=settings['uncertainty_alpha'])
    if task['kind'] == 'verified_source_leads':
        return YieldController(epoch, initial_credit, cutoff, parameters)
    maximum_credit = task['credit_unit'] * (len(task['experiments']) if task['kind'] == 'a105_experiments' else 1)
    if not math.isfinite(maximum_credit) or initial_credit > maximum_credit:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return _FiniteLiteratureYieldController(epoch, initial_credit, cutoff, parameters, maximum_credit=maximum_credit)

class _FiniteLiteratureYieldController(YieldController):
    """An original finite commission with its own remaining-credit forecast."""

    def __init__(self, epoch, initial_credit, cutoff, parameters, *, maximum_credit):
        self.maximum_credit = maximum_credit
        super().__init__(epoch, initial_credit, cutoff, parameters, estimate_with_context=_RemainingCommissionedCredit(maximum_credit, initial_credit))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('explicit_new_epoch_required')
        return type(self)(epoch, self._current_credit, self.cost, self.settings, maximum_credit=self.maximum_credit)
'Private literature_ordered yield behavior for A105.'
from gene_annotation_episode.domain import ContractError

class LiteratureYield:

    def continuation_task(self, context):
        from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import continuation_task
        self._role(context.role)
        return continuation_task(context)

    def yield_controller(self, context, initial_credit, epoch):
        """Bind this commissioned literature episode's estimator and cutoff."""
        self._role(context.role)
        if not self.private_yield_binding:
            return None
        from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement.goal import continuation_task
        key = continuation_task(context)
        declaration = self._yield_bindings.get(key)
        if declaration is None:
            raise ContractError('literature_yield_binding_missing_for_task:' + key)
        return _private_yield_controller(context, initial_credit, epoch, declaration)
