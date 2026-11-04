"""Closed numerical facts through the real guard/runtime, with fixture policies.

No proposed production score, time conversion, scheduling policy or live model.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.episode_reports import closing_yield, report_sources
from gene_annotation_episode.numerical import (NumericBand, SignedNumericBand, STATUS_INSUFFICIENT,
    STATUS_UNIDENTIFIABLE, YieldController, YieldEstimate, YieldState)
from gene_annotation_episode.runtime import run_workflow
from test_runtime import (FixtureController, ScriptedProvider, commission, fixture_credit,
                          obj, reason, setup)


PRIVATE = "PRIVATE_CHILD_DIAGNOSTICS_NOT_A_PARENT_FORM"


def form():
    return obj({"yield": report_sources()["episode_yield"]["report_schema"]})


def factory(final_band, *, parent_actions=2, fits=None):
    def fixture_estimate(history, parameters, contexts):
        if fits is not None:
            fits.append(tuple(history))
        band = NumericBand.exact(.5) if len(history) < 2 else final_band
        return YieldEstimate(len(history), band, parameters,
            {"private_diagnostic": PRIVATE, "private_history": list(history)})
    def controller(path, initial):
        return (FixtureController(str(path), initial, parent_actions) if len(path) == 1 else
                YieldController(str(path), initial, 0, estimate_with_context=fixture_estimate))
    return controller


def run(store, tools, provider, directory, controller, **kwargs):
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=directory,
        controller_factory=controller, project_credit=fixture_credit, **kwargs))


@pytest.mark.parametrize("band", [NumericBand.exact(0),
    SignedNumericBand(-1, -1, -1, uncertainty_code=0, alpha=0)])
def test_parent_receives_actual_final_band_only_when_requested_not_the_prior_model_view(tmp_path, band):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([commission(form(), {}), reason(1), reason(0), reason(0)])
    result = run(store, tools, provider, tmp_path/"run", factory(band))
    assert result["completed_actions"] == 2 and result["credit"] == 1
    # The child sees .5 before its last selected action. Its closing estimate
    # actually differs, and must not come from a model's stale report_update.
    assert provider.contexts[2]["controller"]["estimate"]["expected_next_gain"]["value"] == .5
    projection = {"completed_actions": 2, "expected_next_gain": band.as_record(),
                  "continuation_cost": 0, "stop_requested": True}
    assert provider.contexts[-1]["child_reports"] == [{"yield": projection}]
    assert PRIVATE not in json.dumps(provider.contexts[-1])
    assert "scores" not in projection and "diagnostics" not in projection
    assert "episode_yield" in provider.contexts[0]["available_report_facts"]
    assert set(provider.contexts[0]["available_report_facts"]["episode_yield"]["report_schema"]["properties"]) == set(projection)
    raw = [json.loads(row[0])["step"]["delta"] for row in store.db.execute(
        "SELECT observation FROM runtime_observations WHERE episode_id IN "
        "(SELECT episode_id FROM runtime_episodes WHERE json_array_length(path)=1) ORDER BY unit_index")]
    assert raw == [1, 0]  # Closing/reporting does not create another observation.
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
    assert len(provider.contexts) == 4  # No report composer or new model call.
    facts = json.loads(store.db.execute("SELECT facts FROM runtime_forms").fetchone()[0])
    assert facts["episode_yield"] == projection
    validate_form({"yield": projection}, form())


def test_parent_does_not_receive_an_unrequested_child_estimate(tmp_path):
    store, tools = setup(tmp_path)
    requested = obj({"credit": {"type": "number", "x-source": "credit"}})
    provider = ScriptedProvider([commission(requested, {}), reason(1), reason(0), reason(0)])
    run(store, tools, provider, tmp_path/"run", factory(NumericBand.exact(0)))
    assert provider.contexts[-1]["child_reports"] == [{"credit": 1}]
    assert "expected_next_gain" not in json.dumps(provider.contexts[-1]["child_reports"])


def test_child_cannot_replace_recorded_closing_estimate_in_report_update(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([commission(form(), {}), reason(1, {"yield": {"invented_gain": 999}}),
        reason(0), reason(0)])
    result = run(store, tools, provider, tmp_path/"run", factory(NumericBand.exact(0)))
    assert result["credit"] == 1  # Valid work survives the separate formatting failure.
    assert provider.contexts[2]["feedback"]["category"] == "report_format"
    report, = provider.contexts[-1]["child_reports"]
    assert report["yield"]["expected_next_gain"] == NumericBand.exact(0).as_record()
    assert "invented_gain" not in json.dumps(report)
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4


def test_controller_without_a_typed_estimate_returns_null_not_zero_or_a_new_forecast(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([commission(form(), {}), reason(1), reason(0)])
    controller = lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
    run(store, tools, provider, tmp_path/"run", controller)
    assert provider.contexts[-1]["child_reports"] == [{"yield": None}]


@pytest.mark.parametrize("status", [STATUS_INSUFFICIENT, STATUS_UNIDENTIFIABLE])
def test_projection_preserves_coded_unavailable_band_without_turning_it_into_loss_or_zero(status):
    controller = YieldController("fixture", 0, 0, estimate_with_context=lambda history, parameters, contexts:
        YieldEstimate(len(history), NumericBand.coded(status), parameters, {"private": PRIVATE}))
    record = SimpleNamespace(controller_state=controller.state(), units_consumed=0)
    value = closing_yield(record)
    assert value == {"completed_actions": 0, "expected_next_gain": NumericBand.coded(status).as_record(),
                     "continuation_cost": 0, "stop_requested": False}
    validate_form({"yield": value}, form())


def test_final_projection_is_frozen_across_report_repair_and_interruption_without_refitting(tmp_path):
    store, tools = setup(tmp_path)
    too_narrow = form()
    too_narrow["properties"]["yield"]["properties"]["completed_actions"]["maximum"] = 1
    fits = []
    controller = factory(NumericBand.exact(0), fits=fits)
    provider = ScriptedProvider([commission(too_narrow, {}), reason(1), reason(0), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, provider, tmp_path/"run", controller)
    frozen = store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()
    observations = store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
    assert observations == 3
    # Child refits while reconstructing its own controller history are distinct
    # from the parent-form repair, which must use the original closed facts.
    repair_fits = []
    def repair(context):
        repair_fits.append(len(fits))
        return {"selection": {"kind": "redeliver_report", "delivery_ref": context["feedback"]["delivery_ref"],
            "purpose": "Read the recorded closing local numerical projection", "schema_json": json.dumps(form())},
            "report_update": {}}
    def after_repair(context):
        assert len(fits) == repair_fits[0]
        return reason(0)
    resumed = ScriptedProvider([repair, after_repair])
    summary = run(store, tools, resumed, tmp_path/"run", controller, resume=True)
    assert summary["pending_report_deliveries"] == 0
    assert summary["completed_actions"] == 2
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
    assert tuple(store.db.execute("SELECT facts,form FROM runtime_forms").fetchone()) == tuple(frozen)
    expected = json.loads(frozen[0])["episode_yield"]
    assert resumed.contexts[-1]["child_reports"] == [{"yield": expected}]
    assert PRIVATE not in json.dumps(resumed.contexts[-1])
    before = len(fits)
    assert run(store, tools, ScriptedProvider([]), tmp_path/"run", controller, resume=True) == summary
    assert len(fits) == before  # Inspecting a closed run does not refit.


def test_report_schema_has_no_unrestricted_fields_and_is_not_caller_mutable():
    schema = form()
    validate_closed_schema(schema)
    schema["properties"]["yield"]["properties"].clear()
    assert report_sources()["episode_yield"]["report_schema"]["properties"]
    unsafe = form()
    unsafe["properties"]["yield"]["properties"]["findings"] = {"type": "string"}
    unsafe["properties"]["yield"]["required"].append("findings")
    with pytest.raises(ReportBoundaryError, match="declared semantic type"):
        validate_closed_schema(unsafe)


def test_projection_does_not_serialize_the_child_state_history_or_custom_band_payload():
    class RestrictedState(YieldState):
        def as_record(self):
            raise AssertionError("Do not serialize full child controller state")
    class RestrictedBand(NumericBand):
        def as_record(self):
            raise AssertionError("Only copy the explicitly declared numeric coordinates")
    band = RestrictedBand(1, 1, 1, 0, 0, 0)
    controller = YieldController("fixture", 0, 0, estimate_with_context=lambda history, parameters, contexts:
        YieldEstimate(len(history), band, parameters, {"private": PRIVATE}))
    state = controller.state()
    protected = RestrictedState(state.epoch, state.initial_credit, state.current_credit,
                                state.history, state.estimate, state.decision)
    report = closing_yield(SimpleNamespace(controller_state=protected, units_consumed=0))
    assert report["expected_next_gain"] == {"value": 1, "lower": 1, "upper": 1,
                                           "status_code": 0, "uncertainty_code": 0, "alpha": 0}
    assert PRIVATE not in json.dumps(report)
