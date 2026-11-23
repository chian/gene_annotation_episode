import json
import math
from pathlib import Path
from unittest.mock import patch

import pytest
from real_time_credit_fixture import contexts_at, progress_time

from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from yield_control import (
    NumericBand, STATUS_INSUFFICIENT, STATUS_NORMAL,
    STATUS_UNIDENTIFIABLE, SignedNumericBand, YieldState,
    BoundedQualityYieldController, CompletionYieldController, AccumulationYieldController, YieldParameters,
    ADAPTIVE_CONTROL, FIXED_CONTROL, AccumulationControl,
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
    history = [.8, .1, -.4, .2]
    result = estimate_score_yield(history, YieldParameters(), contexts=contexts_at((10, 15, 80, 120)))
    assert result.turns == 4
    assert result.diagnostics["negative_action_count"] == 1
    assert result.diagnostics["gain_component"]["turns"] == 4
    assert result.diagnostics["loss_component"]["turns"] == 4
    assert result.expected_next_gain.lower < result.expected_next_gain.upper
    assert result.as_record()["diagnostics"]["coverage_calibrated"] is False
    json.loads(json.dumps(result.as_record()))


def _accumulate(controller, discoveries, *, start=0.0, is_root=False):
    credit, steps = start, []
    for index, discovery in enumerate(discoveries):
        credit += discovery
        steps.append(controller.observe(str(index), {"credit": credit}, is_root=is_root))
    return steps


def test_accumulation_contract_takes_a_control_and_items_and_no_cost():
    controller = AccumulationYieldController("epoch-a", 10, FIXED_CONTROL)
    state = controller.state()
    assert isinstance(state, YieldState) and not state.stop
    assert state.estimate.expected_next_gain.status_code == STATUS_INSUFFICIENT
    assert not hasattr(controller, "cost") and not hasattr(controller, "settings")
    with pytest.raises(TypeError):
        AccumulationYieldController("epoch-a", 0, .04, YieldParameters())
    for control in (.04, YieldParameters(), AccumulationControl("adaptive_marginal_credit_threshold",
                                                                0.0, 0.0, 8, 8, 4, .05)):
        with pytest.raises(ValueError, match="ADAPTIVE_CONTROL_or_FIXED_CONTROL"):
            AccumulationYieldController("epoch-a", 0, control)
    for items in (0, -1, True, 2.0, "3"):
        with pytest.raises(ValueError, match="positive_integer"):
            AccumulationYieldController("epoch-a", 0, ADAPTIVE_CONTROL, items=items)
    assert (ADAPTIVE_CONTROL.gamma, ADAPTIVE_CONTROL.rho, ADAPTIVE_CONTROL.streak_length) == (0.0, 0.0, 4)
    assert (FIXED_CONTROL.gamma, FIXED_CONTROL.rho, FIXED_CONTROL.streak_length) == (.06, 0.0, 4)
    for control in (ADAPTIVE_CONTROL, FIXED_CONTROL):
        assert (control.window_size, control.subsample_size, control.alpha) == (8, 4, .05)


def test_accumulation_observation_is_the_marginal_credit_over_the_initial_credit():
    controller = AccumulationYieldController("epoch-a", 10, ADAPTIVE_CONTROL)
    steps = _accumulate(controller, (.5, 0, 2.25, 1), start=10)
    assert [step.marginal_credit for step in steps] == [.5, 0, 2.25, 1]
    assert steps[-1].credit == 13.75 and steps[-1].requests_transition is False
    state = controller.state()
    assert state.history == (.5, 0, 2.25, 1) and state.initial_credit == 10
    assert state.estimate.incidence.observed_results == NumericBand.exact(3.75)
    with pytest.raises(ValueError, match="accumulation_credit_cannot_fall"):
        controller.observe("fell", {"credit": 13.5})
    for value in (True, math.inf, math.nan, "0.2", None):
        with pytest.raises(ValueError):
            controller.observe("bad", value)
    assert controller.state().history == (.5, 0, 2.25, 1)


def test_accumulation_has_no_verdict_before_eight_units_and_stops_after_four_flat_units():
    for control in (FIXED_CONTROL, ADAPTIVE_CONTROL):
        steps = _accumulate(AccumulationYieldController("e", 0, control), [0] * 14)
        assert all(step.estimate.expected_next_gain.status_code == STATUS_INSUFFICIENT for step in steps[:7])
        assert [step.stop for step in steps[:10]] == [False] * 10
        assert steps[7].decision.flat_streak == 1 and steps[10].stop
        assert steps[10].decision.as_record()["stopped_by"] == ["estimator"]
        assert steps[10].decision.outcome == "local_saturation"
    fixed = _accumulate(AccumulationYieldController("e", 0, FIXED_CONTROL), [3, 2, 2, 1, 1, 1] + [0] * 10)
    adaptive = _accumulate(AccumulationYieldController("e", 0, ADAPTIVE_CONTROL), [3, 2, 2, 1, 1, 1] + [0] * 10)
    # The first stops of nano-graphrag's EstimatorController on the same identities (parity run, 2026-11-21).
    assert [step.stop for step in fixed].index(True) == 12
    assert [step.stop for step in adaptive].index(True) == 10
    assert all(step.decision.as_record()["continuation_cost"] == .06 for step in fixed)
    assert adaptive[-1].decision.threshold_update.version == "adaptive_marginal_credit_threshold"
    assert adaptive[-1].decision.gamma == adaptive[-1].decision.threshold_update.gamma.value > 0


def test_accumulation_streak_resets_on_a_productive_unit():
    steps = _accumulate(AccumulationYieldController("e", 0, FIXED_CONTROL), [1] * 20)
    assert [step.stop for step in steps].index(True) == 18
    assert not any(step.stop for step in steps[:18])


def test_accumulation_stops_when_no_item_remains():
    controller = AccumulationYieldController("e", 0, ADAPTIVE_CONTROL, items=3)
    steps = _accumulate(controller, (4, 4, 4))
    assert [step.stop for step in steps] == [False, False, True]
    assert steps[-1].decision.as_record()["stopped_by"] == ["items"]
    assert steps[-1].decision.items_remaining == 0 and controller.state().stop
    with pytest.raises(RuntimeError, match="accumulation_no_item_left_for_unit"):
        controller.observe("extra", {"credit": 12})


def test_accumulation_stops_when_the_episode_reports_no_item_left_on_its_list():
    """An episode whose list is not known at its start reports the number left with each unit; nothing is counted down."""
    controller = AccumulationYieldController("e", 0, ADAPTIVE_CONTROL)

    def unit(label, credit, remaining):
        context = {"progress_time": {}} if remaining is None else {"progress_time": {}, "items_remaining": remaining}
        return controller.observe(label, {"credit": credit, "estimation_context": context})

    first = unit("list not built yet", 0, None)
    assert not first.stop and first.decision.items_remaining is None
    second = unit("list built", 0, 5)
    assert not second.stop and second.decision.items_remaining == 5
    third = unit("one leaf used three", 4, 2)
    assert not third.stop and third.decision.items_remaining == 2
    owed = unit("a unit the episode owes is pending: the list is not settled", 4, None)
    assert not owed.stop and owed.decision.items_remaining is None
    one = unit("one left", 4, 1)
    owed = unit("the last one is used and a unit is owed: not counted down to 0", 5, None)
    assert not one.stop and not owed.stop and owed.decision.items_remaining is None
    with pytest.raises(ValueError, match="accumulation_items_are_counted_from_the_start_or_reported_not_both"):
        AccumulationYieldController("e", 0, ADAPTIVE_CONTROL, items=3).observe(
            "u", {"credit": 0, "estimation_context": {"items_remaining": 2}})
    last = unit("the rest", 6, 0)
    assert last.stop and last.decision.as_record()["stopped_by"] == ["items"] and controller.state().stop
    for wrong in (-1, True, 1.0, "2"):
        with pytest.raises(ValueError, match="accumulation_items_remaining_must_be_an_integer_at_least_0"):
            AccumulationYieldController("e", 0, ADAPTIVE_CONTROL).observe(
                "u", {"credit": 0, "estimation_context": {"items_remaining": wrong}})


def test_accumulation_replays_exactly_and_state_reads_do_not_move_the_warm_start():
    sequence = [5, 4, 3, 3, 2, 2, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0]
    plain = _accumulate(AccumulationYieldController("e", 0, ADAPTIVE_CONTROL), sequence)
    read = AccumulationYieldController("e", 0, ADAPTIVE_CONTROL)
    credit, steps = 0, []
    for index, discovery in enumerate(sequence):
        read.state()
        credit += discovery
        steps.append(read.observe(str(index), {"credit": credit}))
        read.state()
    assert [step.as_record() for step in steps] == [step.as_record() for step in plain]
    json.loads(json.dumps(plain[-1].as_record()))


def test_accumulation_reads_the_rank_not_the_progress_time():
    plain = AccumulationYieldController("plain", 0, FIXED_CONTROL)
    timed = AccumulationYieldController("timed", 0, FIXED_CONTROL)
    for index, (score, context) in enumerate(zip((1, 1, 2, 2, 2, 3, 3, 3, 3), contexts_at(range(10, 100, 10)))):
        left = plain.observe(str(index), {"credit": score})
        right = timed.observe(str(index), {"credit": score, "estimation_context": context})
        assert left.estimate.as_record() == right.estimate.as_record()
        assert left.decision == right.decision


def test_accumulation_state_is_a_yield_table():
    controller = AccumulationYieldController("e", 0, ADAPTIVE_CONTROL)
    _accumulate(controller, [3, 2, 2, 1, 1, 1, 0, 0, 0])
    table = yield_table(controller.state(), forecast_unit="credit")
    assert table["completed_units"] == 9 and table["current_credit"] == 10
    assert table["expected_next_gain"]["status_code"] == STATUS_NORMAL
    assert table["continuation_cost"] == controller.state().decision.gamma
    assert table["parameters"]["threshold"] == "adaptive_marginal_credit_threshold"
    json.loads(json.dumps(table))


def test_availability_and_failed_input_never_become_zero_observations():
    for value in (True, math.inf, math.nan, "0.2", None):
        with pytest.raises(ValueError):
            estimate_score_yield((value,))
    history = []
    for value in (.2, -.1, 0):
        history.append(value)
        result = estimate_score_yield(history)
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
    for is_root in (False, True):
        steps = _accumulate(AccumulationYieldController("epoch", 0, FIXED_CONTROL), [0] * 11, is_root=is_root)
        assert steps[-1].stop
        assert steps[-1].decision.outcome == ("root_incomplete" if is_root else "local_saturation")
        assert steps[-1].requests_transition is is_root

