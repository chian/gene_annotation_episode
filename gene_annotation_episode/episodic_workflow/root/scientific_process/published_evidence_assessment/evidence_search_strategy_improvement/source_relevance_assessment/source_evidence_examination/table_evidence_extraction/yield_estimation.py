"""Original commissioned-literature continuation estimators and controllers."""
from dataclasses import dataclass, replace
import math
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.numerical import (NumericBand, STATUS_NORMAL, YieldController, YieldEstimate,
    YieldParameters, estimate_score_yield)
from .commission_contract import commissioned_task, _task_key

def _yield_kind(task):
    return 'accumulation' if task['kind'] == 'verified_source_leads' else 'remaining_commissioned_credit'


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
        remaining = max(0., self.maximum_credit - current_credit)
        if remaining == 0.:
            return YieldEstimate(len(history), NumericBand.exact(0.), parameters,
                {'completed_acquisition_turns': len(history),
                    'history_used': len(history),
                    'remaining_commissioned_credit': 0.,
                    'commissioned_credit_capacity': self.maximum_credit,
                    'completion': 'all_requested_answers_earned'},
                self.as_record())
        estimate = estimate_score_yield(history, parameters, contexts=contexts)
        band = estimate.expected_next_gain
        if band.status_code == STATUS_NORMAL:
            band = type(band)(min(band.value, remaining), min(band.lower, remaining),
                min(band.upper, remaining), band.status_code,
                band.uncertainty_code, band.alpha)
        return replace(estimate, expected_next_gain=band,
            diagnostics={**estimate.diagnostics,
                'remaining_commissioned_credit': remaining,
                'commissioned_credit_capacity': self.maximum_credit},
            estimator_binding=self.as_record())

    def as_record(self):
        return {'version': 'literature_remaining_commissioned_credit_v1',
            'base_estimator': 'gene_annotation_episode.episodic_workflow.root.numerical.estimate_score_yield',
            'maximum_credit': self.maximum_credit,
            'initial_credit': self.initial_credit,
            'forecast': 'observed_next_action_yield_bounded_by_remaining_commissioned_credit',
            'terminal_forecast': 'exact_zero_when_all_requested_answers_earned'}


def _private_yield_controller(context, initial_credit, epoch, declaration):
    task, _ = commissioned_task(context)
    settings = task.get('yield_settings')
    if settings is None:
        raise ContractError('literature_original_task_yield_settings_required')
    if (task['credit_unit'] != declaration['credit_unit']
            or settings != {key: declaration[key]
                for key in ('kind', 'cutoff', 'uncertainty_alpha')}
            or settings['kind'] != _yield_kind(task)):
        raise ContractError('literature_original_task_yield_binding_mismatch:' + _task_key(task))
    cutoff = settings['cutoff']
    parameters = YieldParameters(uncertainty_alpha=settings['uncertainty_alpha'])
    if task['kind'] == 'verified_source_leads':
        # Open source discovery has no finite number of useful original leads.
        return YieldController(epoch, initial_credit, cutoff, parameters)
    maximum_credit = task['credit_unit'] * (len(task['experiments'])
        if task['kind'] == 'a105_experiments' else 1)
    if not math.isfinite(maximum_credit) or initial_credit > maximum_credit:
        raise ContractError('literature_commissioned_credit_capacity_invalid')
    return _FiniteLiteratureYieldController(epoch, initial_credit, cutoff, parameters,
        maximum_credit=maximum_credit)


class _FiniteLiteratureYieldController(YieldController):
    """An original finite commission with its own remaining-credit forecast."""

    def __init__(self, epoch, initial_credit, cutoff, parameters, *, maximum_credit):
        self.maximum_credit = maximum_credit
        super().__init__(epoch, initial_credit, cutoff, parameters,
            estimate_with_context=_RemainingCommissionedCredit(maximum_credit, initial_credit))

    def transitioned(self, epoch):
        if epoch == self.epoch:
            raise ValueError('explicit_new_epoch_required')
        return type(self)(epoch, self._current_credit, self.cost, self.settings,
            maximum_credit=self.maximum_credit)


