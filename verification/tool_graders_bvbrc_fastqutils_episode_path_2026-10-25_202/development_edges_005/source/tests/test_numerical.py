import hashlib
import json
import math
from pathlib import Path
from unittest.mock import patch

import pytest

from gene_annotation_episode.numerical import (
    NumericBand, SOURCE_SHA256, STATUS_INSUFFICIENT, STATUS_NORMAL,
    STATUS_UNIDENTIFIABLE, ScalarScoreYieldEstimator, SignedNumericBand,
    YieldController, YieldParameters, estimate_nonnegative_yield,
    estimate_score_yield, predicted_gain_upper_bound,
)


def test_nonnegative_path_matches_supplied_adapter_golden():
    # Fixed golden values from the supplied template, independent of our public
    # signed wrapper. This verifies numerical preservation, not biological fit.
    history = [.125, 0, .375, 0, .5, 0, .25, 0]
    band = estimate_score_yield(history).expected_next_gain
    assert band.status_code == STATUS_NORMAL
    assert band.as_record() == estimate_nonnegative_yield(history).expected_next_gain.as_record()
    assert band.value == pytest.approx(0.1401910417085443, rel=1e-8)
    assert band.upper == pytest.approx(0.4334196679749991, rel=1e-8)


def test_signed_correction_has_one_history_entry_and_two_rank_aligned_marks():
    estimator = ScalarScoreYieldEstimator(YieldParameters(4, 2))
    history = [.8, .1, -.4, .2]
    for value in history:
        result = estimator.observe(value)
    assert estimator.scores == tuple(history)
    assert result.turns == 4
    assert result.diagnostics["negative_action_count"] == 1
    assert result.diagnostics["gain_component"]["turns"] == 4
    assert result.diagnostics["loss_component"]["turns"] == 4
    assert result.expected_next_gain.lower < result.expected_next_gain.upper
    assert result.as_record()["diagnostics"]["coverage_calibrated"] is False
    json.loads(json.dumps(result.as_record()))


def test_cumulative_baseline_and_signed_delta_are_passed_unchanged():
    controller = YieldController("epoch-a", initial_credit=10, cost=.04,
                                 settings=YieldParameters(4, 2))
    for n, credit in enumerate((10.5, 10.5, 10.1, 10.3)):
        step = controller.observe(str(n), {"credit": credit}, is_root=True)
    assert controller.estimator.scores == pytest.approx((.5, 0, -.4, .2))
    assert step.credit == 10.3
    assert step.marginal_credit == pytest.approx(.2)
    assert step.requests_transition is False
    assert controller.state().as_record()["initial_credit"] == 10


def test_availability_and_failed_input_never_become_zero_observations():
    estimator = ScalarScoreYieldEstimator()
    for value in (True, math.inf, math.nan, "0.2", None):
        with pytest.raises(ValueError):
            estimator.observe(value)
    assert estimator.scores == ()
    for value in (.2, -.1, 0):
        result = estimator.observe(value)
        assert result.expected_next_gain.status_code == STATUS_INSUFFICIENT
        assert not predicted_gain_upper_bound(result.expected_next_gain, 1000).stop
    with patch("gene_annotation_episode.numerical._RealScoreFit._fit_full_history",
               side_effect=ArithmeticError("unknown")):
        unavailable = estimate_score_yield([.1]*7+[-.1])
    assert unavailable.expected_next_gain.status_code == STATUS_UNIDENTIFIABLE
    assert not predicted_gain_upper_bound(unavailable.expected_next_gain, 1000).stop


def test_full_history_is_not_window_truncated_or_smoothed():
    left = estimate_score_yield([.125]*4+[0]*8)
    right = estimate_score_yield([.75]*4+[0]*8)
    assert left.diagnostics["history_used"] == 12
    assert right.diagnostics["history_used"] == 12
    assert left.expected_next_gain.value != right.expected_next_gain.value
    estimate = estimate_score_yield([.2]*6+[0,0])
    assert estimate.expected_next_gain.upper > .04
    assert not predicted_gain_upper_bound(estimate.expected_next_gain,.04).stop


def test_controller_rule_is_exact_for_root_and_child_and_signed_band():
    band = SignedNumericBand(-.2, -.5, .03)
    assert not predicted_gain_upper_bound(band,.02).stop
    assert predicted_gain_upper_bound(band,.03).stop
    assert predicted_gain_upper_bound(band,.03).projected_gain is band
    zero = NumericBand.exact(0)
    assert predicted_gain_upper_bound(zero,0).stop
    for is_root in (False,True):
        c = YieldController("epoch",0,.03,YieldParameters(2,1))
        with patch.object(c.estimator, "observe") as observe:
            from gene_annotation_episode.numerical import YieldEstimate
            observe.return_value=YieldEstimate(2,band,c.settings,{})
            assert c.observe("action",-.2,is_root).stop


def test_vendored_source_digest_and_license_are_preserved():
    vendor = Path(__file__).resolve().parents[1]/"gene_annotation_episode/vendor"
    assert hashlib.sha256((vendor/"nano_rarefaction.py").read_bytes()).hexdigest() == SOURCE_SHA256
    assert json.loads((vendor/"SOURCE.nano-graphrag.json").read_text())["source_sha256"] == SOURCE_SHA256
    assert "Copyright (c) 2024 Gustavo Ye" in (vendor/"LICENSE.nano-graphrag").read_text()


def test_default_context_is_not_an_implicit_new_time_formula():
    plain = YieldController("plain", 0, .04, YieldParameters(2, 1))
    supplied = YieldController("supplied", 0, .04, YieldParameters(2, 1))
    for score in (1, 1.5):
        left = plain.observe("work", {"credit": score})
        right = supplied.observe("work", {"credit": score, "estimation_context": {"fixture_seconds": 100000}})
        assert left.estimate.as_record() == right.estimate.as_record()
        assert left.decision == right.decision
    assert supplied.estimator.scores == (1, .5)


def test_custom_estimator_has_its_own_provenance_and_aligned_raw_contexts():
    from gene_annotation_episode.numerical import YieldEstimate
    received = []
    def fixture(history, parameters, contexts):
        received.append((history, contexts))
        return YieldEstimate(len(history), NumericBand.exact(1), parameters, {})
    controller = YieldController("fixture", 4, 0, estimate_with_context=fixture)
    controller.observe("first", {"credit": 5, "estimation_context": {"fixture_seconds": 2}})
    step = controller.observe("second", {"credit": 4.5, "estimation_context": {"fixture_seconds": 3}})
    assert received == [((), ()), ((1,), ({"fixture_seconds": 2},)),
        ((1, -.5), ({"fixture_seconds": 2}, {"fixture_seconds": 3}))]
    binding = step.estimate.as_record()["provenance"]
    assert binding["kind"] == "caller_injected" and binding["function"].endswith("fixture")
    assert "source_repository" not in binding  # no false nano-template attribution
    assert controller.estimator.contexts == ({"fixture_seconds": 2}, {"fixture_seconds": 3})
