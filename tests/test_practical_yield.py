from copy import deepcopy
import json

import pytest
from real_time_credit_fixture import progress_time

from method_loop import Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree, Grain, Leaf
from method_loop.identities import EpisodeRef, UnitRef

from gene_annotation_episode.numerical import (NumericBand, STATUS_INSUFFICIENT, STATUS_NORMAL,
    YieldController, YieldEstimate, YieldParameters, estimate_score_yield)
from gene_annotation_episode.practical_yield import ESTIMATOR_VERSION, PracticalYieldEstimator
from gene_annotation_episode.runtime import Record


def completion_context(*, run_id="run-practical", episode_id="episode-practical",
                       unit_index=0, action_index=7):
    unit = UnitRef(episode_id, unit_index).as_record()
    proof = {"version": "practical_completion_v1", "run_id": run_id,
        "episode_id": episode_id, "assignment_sha256": "a" * 64,
        "endpoint": "completed_job_outputs", "operation_key": "recorded-operation",
        "receipt_sha256": "b" * 64, "validation_keys": ["requested_outputs"]}
    return {"version": "completed_action_estimation_context_v5",
        "progress_time": progress_time(10. * (unit_index + 1), run_id=run_id,
            episode_id=episode_id, decision_index=action_index),
        "current_completion_evidence": {"version": "completed_action_evidence_v1",
            "run_id": run_id, "episode_id": episode_id, "unit_ref": unit,
            "original_decision_index": action_index, "action_kind": "tool",
            "received_record_refs": [], "received_progress_refs": [],
            "progress_records": [], "child_return": None, "unavailable_reasons": []},
        "practical_completion": {**proof, "unit_ref": unit, "action_index": action_index}}


def without_runtime(context):
    return {key: value for key, value in context["practical_completion"].items()
            if key not in {"unit_ref", "action_index"}}


@pytest.mark.parametrize("history", [(), (1., 0., -.25),
    (.125, 0., .375, 0., .5, 0., .25, 0.),
    (.8, .1, -.4, .2, 0., .1, 0., .05)])
def test_unfinished_default_estimates_are_unchanged(history):
    def unexpected_verification(_):
        raise AssertionError("No completion proof was supplied")
    parameters = YieldParameters()
    callback = PracticalYieldEstimator(unexpected_verification)
    contexts = ({"practical_completion": None},) * len(history)
    assert callback(history, parameters, contexts).as_record() == estimate_score_yield(
        history, parameters).as_record()


@pytest.mark.parametrize("final_credit,final_delta", [(14, 2.5), (11.25, -.25), (11.5, 0)])
def test_terminal_proof_changes_only_future_forecast_with_short_history(final_credit, final_delta):
    contexts = [None, None, completion_context(unit_index=2)]
    original_contexts = deepcopy(contexts)
    seen = []
    def verify(proof):
        seen.append(proof)
        return proof == without_runtime(contexts[-1])
    callback = PracticalYieldEstimator(verify)
    controller = YieldController("practical", 10, 0, estimate_with_context=callback)
    for label, credit, context in zip(("prepare", "repair", "validate"),
                                    (12, 11.5, final_credit), contexts):
        step = controller.observe(label, {"credit": credit, "estimation_context": context})
    assert controller.estimator.scores == (2, -.5, final_delta)
    assert step.marginal_credit == final_delta and step.credit == final_credit
    assert step.stop and not step.requests_transition
    assert step.estimate.turns == 3
    assert step.estimate.expected_next_gain == NumericBand.exact(0)
    assert controller.state().decision.projected_gain == NumericBand.exact(0)
    assert seen == [without_runtime(contexts[-1])]
    assert contexts == original_contexts
    assert step.estimate.estimator_binding["version"] == ESTIMATOR_VERSION
    assert json.loads(json.dumps(step.as_record()))["estimate"]["turns"] == 3


def test_default_scientific_controller_does_not_consume_practical_terminal_proof():
    controller = YieldController("ordinary-scientific", 0, 0)
    step = controller.observe("work", {"credit": 3,
        "estimation_context": completion_context()})
    assert controller.estimator.scores == (3,)
    assert step.estimate.expected_next_gain.status_code == STATUS_NORMAL
    assert not step.stop


def test_unverified_proof_does_not_force_completion_or_replace_custom_base():
    expected = YieldEstimate(1, NumericBand.exact(9), YieldParameters(), {"custom": True})
    captured = []
    def base(history, parameters):
        captured.append((history, parameters))
        return expected
    callback = PracticalYieldEstimator(lambda _: False, base)
    assert callback((-.5,), expected.parameters, (completion_context(),)) is expected
    assert captured == [((-.5,), expected.parameters)]


@pytest.mark.parametrize("mutation", [
    lambda c: c["practical_completion"].update(completed=True),
    lambda c: c["practical_completion"].update(version="invented"),
    lambda c: c["practical_completion"].update(assignment_sha256="unknown"),
    lambda c: c["practical_completion"].update(receipt_sha256="unknown"),
    lambda c: c["practical_completion"].update(endpoint="software_installed"),
    lambda c: c["practical_completion"].update(validation_keys=["x", "x"]),
    lambda c: c["practical_completion"].update(action_index=True),
    lambda c: c["practical_completion"].update(action_index=8),
    lambda c: c["practical_completion"].update(run_id="another-run"),
    lambda c: c["practical_completion"].update(episode_id="another-episode"),
    lambda c: c["practical_completion"].update(unit_ref=UnitRef("episode-practical", 1).as_record()),
    lambda c: c["practical_completion"]["unit_ref"].update(unit_id="invented"),
    lambda c: c.pop("current_completion_evidence"),
])
def test_invalid_or_wrong_action_proofs_never_reach_authoritative_verifier(mutation):
    context = completion_context()
    mutation(context)
    def unexpected_verification(_):
        raise AssertionError("Invalid proof reached authoritative verification")
    with pytest.raises(ValueError):
        PracticalYieldEstimator(unexpected_verification)((1,), YieldParameters(), (context,))


def test_history_position_must_match_actual_completion_position():
    callback = PracticalYieldEstimator(lambda _: True)
    context = completion_context(unit_index=1)
    with pytest.raises(ValueError, match="identity_conflict"):
        callback((1,), YieldParameters(), (context,))


def test_invalid_terminal_input_does_not_mutate_controller_history():
    callback = PracticalYieldEstimator(lambda _: "true")
    controller = YieldController("practical", 4, 0, estimate_with_context=callback)
    with pytest.raises(TypeError, match="requires_boolean"):
        controller.observe("invalid", {"credit": 5,
            "estimation_context": completion_context()})
    assert controller.estimator.scores == ()
    assert controller.state().current_credit == 4
    assert controller.state().estimate.expected_next_gain.status_code == STATUS_NORMAL


@pytest.mark.parametrize("history,contexts", [
    ((1,), ()), ((float("nan"),), (completion_context(),)),
    ((float("inf"),), (completion_context(),)), ((True,), (completion_context(),))])
def test_terminal_claim_does_not_bypass_history_validation(history, contexts):
    with pytest.raises(ValueError):
        PracticalYieldEstimator(lambda _: True)(history, YieldParameters(), contexts)


def test_only_current_action_proof_can_make_latest_forecast_terminal():
    prior = completion_context()
    seen = []
    callback = PracticalYieldEstimator(lambda proof: seen.append(proof) or True)
    estimate = callback((1., 0.), YieldParameters(), (prior, None))
    assert estimate.expected_next_gain.status_code == STATUS_INSUFFICIENT
    assert seen == []


def test_shared_episode_closes_on_same_action_and_replay_matches():
    run_id, key = "run-practical", "requested-execution"
    callbacks = []
    def factory(path):
        callback = PracticalYieldEstimator(lambda proof: True)
        callbacks.append(callback)
        return YieldController("practical-epoch", 0, 0, estimate_with_context=callback)
    grain = Grain("practical", "One selected operation", "Validated work", factory)
    identity = EpisodeRef(run_id, ((grain.name, key),))
    context = completion_context(run_id=run_id, episode_id=identity.episode_id, action_index=0)
    value = Record({"credit": 3, "estimation_context": context})
    executed = []
    class Source:
        def next(self, view):
            executed.append("selected")
            if len(executed) > 1:
                raise AssertionError("A second turn was requested after validated completion")
            return Leaf(None, lambda _: executed.append("executed") or value,
                lambda _, result: result, "validate")
    request = EpisodeRequest(EpisodeGoal.root(objective="Produce requested outputs",
        result_contract={"type": "object"}), Record({}))
    episode = Episode(grain, key, Source(), request, lambda _: Record({}))
    record = episode.run(Context(tree=EpisodeTree(grain), run_id=run_id))
    assert executed == ["selected", "executed"]
    assert record.ended_by == "yield_stop" and record.units_consumed == 1
    assert record.unit_records[0].controller_step.marginal_credit == 3
    restored_calls = []
    class SavedCompletion:
        def next(self, view):
            restored_calls.append("read-original-completion")
            if len(restored_calls) > 1:
                raise AssertionError("Replay must close before requesting new work")
            return Leaf(value, lambda saved: saved, lambda _, result: result, "validate")
    replay = Episode(grain, key, SavedCompletion(), request, lambda _: Record({}))
    restored = replay.run(Context(tree=EpisodeTree(grain), run_id=run_id))
    assert restored.as_record() == record.as_record()
    assert restored_calls == ["read-original-completion"]
    assert executed == ["selected", "executed"]
    assert len(callbacks) == 2
