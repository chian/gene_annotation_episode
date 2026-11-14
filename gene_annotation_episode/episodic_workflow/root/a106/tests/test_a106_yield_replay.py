"""Decision replay checks; these engineered traces make no scientific claim."""
from copy import deepcopy

import pytest

from gene_annotation_episode import numerical
from tools.replay_a106_yield import band_at_alpha, discovery_tradeoff, replay, validate_trace


def episode(marks, means, variances=None):
    variances = variances or [0.] * len(marks)
    result = dict(initial_credit=0., observations=[], actions=[], first_decision_started_at=None)
    credit = 0.
    for index, (mark, mean, variance) in enumerate(zip(marks, means, variances)):
        credit += mark
        band = numerical.NumericBand.laplace(mean, variance, .05)
        result["observations"].append(dict(unit_index=index, decision_index=index, credit=credit,
            marginal_credit=mark, estimate=dict(turns=index+1,
                expected_next_gain=band.as_record(), diagnostics=dict(next_gain_variance=variance),
                parameters=dict(uncertainty_alpha=.05), provenance=dict(estimator=numerical.ESTIMATOR_VERSION)),
            decision=numerical.predicted_gain_upper_bound(band, .001).as_record()))
        result["actions"].append(dict(decision_index=index, ended_at=None, kind="tool", tool="source.read"))
    return result


def test_replay_uses_first_crossing_and_not_the_convenient_later_one():
    trace = episode([0, 0, 1, 0], [.1, .005, .5, .001])
    before = deepcopy(trace)
    result = replay(trace, cost=.01, alpha=.05, numerical=numerical)
    assert result["stop"]["decision_index"] == 1
    assert result["stop"]["cumulative_credit"] == 0
    assert result["stop"]["later_recorded_credit"] == 1
    assert trace == before
    trace["observations"][-1]["estimate"]["expected_next_gain"]["value"] = 999
    assert replay(trace, cost=.01, alpha=.05, numerical=numerical)["stop"]["decision_index"] == 1


def test_unavailable_prediction_does_not_stop_at_any_finite_cost():
    trace = episode([0], [0])
    trace["observations"][0]["estimate"]["expected_next_gain"] = numerical.NumericBand.coded(numerical.STATUS_INSUFFICIENT).as_record()
    assert replay(trace, cost=1e6, alpha=.05, numerical=numerical)["stop"] is None


def test_equality_is_the_original_upper_bound_stop_rule():
    trace = episode([0], [.1])
    assert replay(trace, cost=.1, alpha=.05, numerical=numerical)["stop"]["decision_index"] == 0
    assert replay(trace, cost=.099, alpha=.05, numerical=numerical)["stop"] is None


def test_rejected_grading_and_finalization_are_not_counted_as_completed():
    trace = episode([0, 0], [.1, .001])
    trace["actions"][0].update(tool="literature.intervention_grading.populate", status="completed")
    trace["actions"][1].update(tool="literature.a106.finalize", status="invalid")
    result = replay(trace, cost=.01, alpha=.05, numerical=numerical)["stop"]
    assert result["completed_grading_actions"] == 1
    assert result["completed_finalization_actions"] == 0


def test_changed_alpha_reuses_fit_not_observations_or_new_credit():
    trace = episode([1], [.2], [.03])
    value = trace["observations"][0]["estimate"]
    original = band_at_alpha(value, .05, numerical)
    changed = band_at_alpha(value, .2, numerical)
    assert original.value == changed.value
    assert changed.upper < original.upper
    assert changed.as_record() == numerical.NumericBand.laplace(.2, .03, .2).as_record()


def test_signed_replay_preserves_same_gain_loss_band_subtraction():
    gain = episode([1], [.2], [.01])["observations"][0]["estimate"]
    loss = episode([1], [.4], [.02])["observations"][0]["estimate"]
    value = dict(expected_next_gain=numerical.SignedNumericBand(-.2, -.5, .1).as_record(),
        diagnostics=dict(gain_component=gain, loss_component=loss))
    actual = band_at_alpha(value, .2, numerical)
    g = band_at_alpha(gain, .1, numerical)
    l = band_at_alpha(loss, .1, numerical)
    assert actual.value == pytest.approx(-.2)
    assert actual.lower == g.lower-l.upper and actual.upper == g.upper-l.lower


def test_no_fixed_cost_can_keep_discovery_and_yield_on_higher_later_bands():
    trace = episode([0, 0, 1, 0], [.1, .005, .5, .02])
    result = discovery_tradeoff(trace, .05, numerical)
    assert result["cost_must_be_strictly_below_to_reach_first_positive"] == .005
    assert result["minimum_cost_that_can_stop_from_first_positive_onward"] == .02
    assert result["fixed_cost_can_reach_first_positive_and_stop_later"] is False


def test_trace_validation_detects_changed_credit_and_changed_saved_decision():
    trace = episode([0, 1], [.1, .2])
    validate_trace(trace, numerical)
    bad = deepcopy(trace)
    bad["observations"][1]["credit"] = 2
    with pytest.raises(ValueError, match="raw_credit_delta_mismatch"):
        validate_trace(bad, numerical)
    bad = deepcopy(trace)
    bad["observations"][0]["decision"]["stop"] = True
    with pytest.raises(ValueError, match="original_decision_replay_mismatch"):
        validate_trace(bad, numerical)
