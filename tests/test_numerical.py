import json
import math
from pathlib import Path
from unittest.mock import patch

import pytest
from real_time_credit_fixture import contexts_at, progress_time

from yield_control import (
    NumericBand, STATUS_INSUFFICIENT, STATUS_NORMAL,
    STATUS_UNIDENTIFIABLE, AccumulationYieldEstimator, SignedNumericBand, YieldEstimate,
    BoundedQualityYieldController, CompletionYieldController, AccumulationYieldController, YieldParameters,
    estimate_nonnegative_yield, estimate_score_yield, estimate_bounded_credit_yield, predicted_gain_upper_bound,
)


def test_bounded_native_yield_preserves_unknown_and_reopens_after_correction():
    missing = estimate_bounded_credit_yield((.2,), contexts=(None,),
        initial_credit=.5, maximum_credit=1.)
    assert missing.expected_next_gain.status_code == STATUS_INSUFFICIENT
    assert missing.diagnostics['remaining_positive_credit'] == pytest.approx(.3)
    observed = estimate_bounded_credit_yield((.2,), contexts=contexts_at((10,)),
        initial_credit=.5, maximum_credit=1.)
    assert observed.expected_next_gain.status_code == STATUS_NORMAL
    assert observed.expected_next_gain.upper <= .3 + 1e-12
    full = BoundedQualityYieldController('native', 1., .075, 1.)
    assert full.state().estimate.expected_next_gain == NumericBand.exact(0)
    assert full.state().decision.stop
    corrected = full.observe('revised native sheet', {'credit': .8})
    assert corrected.marginal_credit == pytest.approx(-.2)
    assert corrected.estimate.diagnostics['remaining_positive_credit'] == pytest.approx(.2)
    assert corrected.estimate.expected_next_gain.status_code == STATUS_INSUFFICIENT
    assert not corrected.stop
    replay = full.transitioned('revised')
    assert replay.state().initial_credit == .8
    assert replay.state().estimate.diagnostics['remaining_positive_credit'] == pytest.approx(.2)


def test_completion_yield_uses_observed_attempts_until_artifact_arrives():
    controller = CompletionYieldController('panel', 0, .075, 1)
    assert not controller.state().decision.stop
    attempted = controller.observe('attempt', {'credit': 0,
        'estimation_context': contexts_at((10,))[0]})
    assert attempted.estimate.expected_next_gain.status_code == STATUS_NORMAL
    assert attempted.estimate.expected_next_gain.upper <= 1
    assert attempted.estimate.estimator_binding['before_target'] == 'observed_action_yield_limited_by_remaining_distance'
    delivered = controller.observe('imported artifact', {'credit': 1,
        'estimation_context': contexts_at((10, 20))[1]})
    assert delivered.estimate.expected_next_gain == NumericBand.exact(0)
    assert delivered.stop
    reopened = controller.observe('artifact withdrawn', {'credit': 0,
        'estimation_context': contexts_at((10, 20, 30))[2]})
    assert reopened.estimate.expected_next_gain.status_code == STATUS_NORMAL
    assert reopened.estimate.diagnostics['remaining_deliverable_credit'] == 1
    assert controller.transitioned('new panel').state().initial_credit == 0


def test_time_scale_is_measured_and_does_not_convert_credit_to_a_rate():
    history = [.125, 0, .375, 0, .5, 0, .25, 0]
    contexts = contexts_at(range(10, 90, 10))
    band = estimate_score_yield(history, contexts=contexts).expected_next_gain
    assert band.status_code == STATUS_NORMAL
    assert band.as_record() == estimate_nonnegative_yield(history, contexts=contexts).expected_next_gain.as_record()
    stretched = estimate_score_yield(history,
        contexts=contexts_at(range(100, 900, 100), first_seconds=100.)).expected_next_gain
    assert stretched.as_record() == band.as_record()
    uneven = estimate_score_yield(history,
        contexts=contexts_at((10, 20, 30, 40, 50, 60, 70, 800))).expected_next_gain
    assert uneven.value != band.value


def test_signed_correction_has_one_history_entry_and_two_time_aligned_marks():
    estimator = AccumulationYieldEstimator(YieldParameters())
    history = [.8, .1, -.4, .2]
    for value, context in zip(history, contexts_at((10, 15, 80, 120))):
        result = estimator.observe(value, context=context)
    assert estimator.scores == tuple(history)
    assert result.turns == 4
    assert result.diagnostics["negative_action_count"] == 1
    assert result.diagnostics["gain_component"]["turns"] == 4
    assert result.diagnostics["loss_component"]["turns"] == 4
    assert result.expected_next_gain.lower < result.expected_next_gain.upper
    assert result.as_record()["diagnostics"]["coverage_calibrated"] is False
    json.loads(json.dumps(result.as_record()))


def test_cumulative_baseline_and_signed_delta_are_passed_unchanged():
    controller = AccumulationYieldController("epoch-a", initial_credit=10, cost=.04,
                                 settings=YieldParameters())
    for n, credit in enumerate((10.5, 10.5, 10.1, 10.3)):
        step = controller.observe(str(n), {"credit": credit}, is_root=True)
    assert controller.estimator.scores == pytest.approx((.5, 0, -.4, .2))
    assert step.credit == 10.3
    assert step.marginal_credit == pytest.approx(.2)
    assert step.requests_transition is False
    assert controller.state().as_record()["initial_credit"] == 10


def test_availability_and_failed_input_never_become_zero_observations():
    estimator = AccumulationYieldEstimator()
    for value in (True, math.inf, math.nan, "0.2", None):
        with pytest.raises(ValueError):
            estimator.observe(value)
    assert estimator.scores == ()
    for value in (.2, -.1, 0):
        result = estimator.observe(value)
        assert result.expected_next_gain.status_code == STATUS_INSUFFICIENT
        assert not predicted_gain_upper_bound(result.expected_next_gain, 1000).stop
    with patch("yield_control._RealTimeCreditFit.fit",
               side_effect=ArithmeticError("unknown")):
        unavailable = estimate_score_yield([.1]*7+[-.1], contexts=contexts_at(range(10, 90, 10)))
    assert unavailable.expected_next_gain.status_code == STATUS_UNIDENTIFIABLE
    assert not predicted_gain_upper_bound(unavailable.expected_next_gain, 1000).stop


def test_full_history_is_not_window_truncated_or_smoothed():
    contexts = contexts_at(range(10, 130, 10))
    left = estimate_score_yield([.125]*4+[0]*8, contexts=contexts)
    right = estimate_score_yield([.75]*4+[0]*8, contexts=contexts)
    assert left.diagnostics["history_used"] == 12
    assert right.diagnostics["history_used"] == 12
    assert left.expected_next_gain.value != right.expected_next_gain.value
    same = estimate_score_yield([.125]*4+[0]*8, YieldParameters(), contexts=contexts)
    assert same.expected_next_gain == left.expected_next_gain


def test_no_minimum_window_and_prior_only_is_distinct_from_missing_time():
    prior = estimate_score_yield(())
    assert prior.ready and prior.diagnostics["fitting_scope"] == "prior_only"
    assert prior.expected_next_gain.upper > prior.expected_next_gain.value > 0
    one = estimate_score_yield((1.,), YieldParameters(), contexts=contexts_at((10,)))
    assert one.ready and one.turns == 1
    missing = estimate_score_yield((1.,))
    assert not missing.ready and missing.diagnostics["unavailable_reason"] == "progress_time_unavailable"
    assert not predicted_gain_upper_bound(missing.expected_next_gain, 1000).stop


def test_query_clock_can_advance_without_adding_progress_and_replay_is_fixed():
    contexts = contexts_at((10, 20, 30))
    original = estimate_score_yield((1., 0., 0.), contexts=contexts)
    query = progress_time(100., query=True)
    later = estimate_score_yield((1., 0., 0.), contexts=contexts, evaluation_time=query)
    assert later.turns == original.turns == 3
    assert later.expected_next_gain.value != original.expected_next_gain.value
    assert later.as_record() == estimate_score_yield((1., 0., 0.),
        contexts=contexts, evaluation_time=query).as_record()
    assert contexts[-1]["progress_time"]["elapsed_seconds"] == 30


def test_controller_rule_is_exact_for_root_and_child_and_signed_band():
    band = SignedNumericBand(-.2, -.5, .03)
    assert not predicted_gain_upper_bound(band,.02).stop
    assert predicted_gain_upper_bound(band,.03).stop
    assert predicted_gain_upper_bound(band,.03).projected_gain is band
    zero = NumericBand.exact(0)
    assert predicted_gain_upper_bound(zero,0).stop
    for is_root in (False,True):
        c = AccumulationYieldController("epoch",0,.03,YieldParameters())
        with patch.object(c.estimator, "observe") as observe:
            observe.return_value=YieldEstimate(2,band,c.settings,{})
            assert c.observe("action",-.2,is_root).stop




def test_default_context_is_not_an_implicit_new_time_formula():
    plain = AccumulationYieldController("plain", 0, .04, YieldParameters())
    supplied = AccumulationYieldController("supplied", 0, .04, YieldParameters())
    for score in (1, 1.5):
        left = plain.observe("work", {"credit": score})
        right = supplied.observe("work", {"credit": score, "estimation_context": {"fixture_seconds": 100000}})
        assert left.estimate.as_record() == right.estimate.as_record()
        assert left.decision == right.decision
    assert supplied.estimator.scores == (1, .5)

