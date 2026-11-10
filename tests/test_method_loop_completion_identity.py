"""Shared completion identity with fixture work and fixture controllers only.

No application projection, model call or native job is used in these tests.
"""

import asyncio
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from method_loop import (
    ClosedRecord,
    Context,
    ControllerRuntime,
    DeferredUnit,
    Episode,
    EpisodeGoal,
    EpisodeRequest,
    EpisodeTree,
    Grain,
    Leaf,
    ResumeUnit,
    leaves,
)
from method_loop.identities import EpisodeRef, UnitRef


@dataclass(frozen=True)
class FixtureValue(ClosedRecord):
    credit: float
    detail: str = "fixture contribution"

    def as_record(self):
        return {"credit": self.credit, "detail": self.detail}


class LegacyController:
    """Only the original observe signature is accepted."""

    epoch = "fixture-epoch"

    def __init__(self, *, stop_after=None):
        self.observations = []
        self.stop_after = stop_after

    def _observe(self, port, label, value, unit_ref, is_root):
        self.observations.append((port, label, value, unit_ref, is_root))
        return SimpleNamespace(stop=self.state().stop, requests_transition=False)

    def observe(self, unit_label, value, *, is_root):
        return self._observe("legacy", unit_label, value, None, is_root)

    def state(self):
        return SimpleNamespace(stop=(self.stop_after is not None
            and len(self.observations) >= self.stop_after))

    def transitioned(self, epoch):
        raise AssertionError("this fixture selects no epoch transition")


class IdentityController(LegacyController):
    def observe_unit(self, unit_label, value, *, unit_ref, is_root):
        return self._observe("identity", unit_label, value, unit_ref, is_root)


class Source:
    def __init__(self, choose):
        self.choose = choose

    def next(self, view):
        return self.choose(view)


def fixture_episode(controller, source, *, resume_units=(), on_unit=None):
    grain = Grain("fixture", "One selected fixture action", "Fixture values",
                  lambda _: controller)
    context = Context(tree=EpisodeTree(grain), run_id="actual-fixture-run")
    goal = EpisodeGoal.root(objective="Exercise the completion boundary", result_contract={})
    episode = Episode(grain, "readable-episode-key", source,
        EpisodeRequest(goal, FixtureValue(0)), lambda _: FixtureValue(0),
        resume_units=resume_units, on_unit=on_unit)
    return episode, context


def run_episode(episode, context, asynchronous):
    return (asyncio.run(episode.run_async(context)) if asynchronous
            else episode.run(context))


@pytest.mark.parametrize("asynchronous", [False, True])
def test_completed_acquisitions_supply_the_actual_reference_and_exact_value(asynchronous):
    values = [FixtureValue(3.5), FixtureValue(-2.0), FixtureValue(-2.0)]
    controller = IdentityController()
    hooks = []

    async def extract_async(value):
        return value

    async def result_async(_, value):
        return value

    source = leaves(values,
        extract=extract_async if asynchronous else lambda value: value,
        result=result_async if asynchronous else lambda _, value: value,
        label=lambda _: "repeated readable label")

    def on_unit(item, contribution, view):
        assert len(controller.observations) == len(hooks) + 1
        hooks.append((contribution, view))

    episode, context = fixture_episode(controller, source, on_unit=on_unit)
    record = run_episode(episode, context, asynchronous)
    expected_episode = EpisodeRef("actual-fixture-run", record.path)

    assert record.episode_ref == expected_episode
    assert record.units_consumed == len(controller.observations) == len(hooks) == 3
    assert [unit.controller_input.as_record()["credit"] for unit in record.unit_records] == [3.5, -2.0, -2.0]
    for index, (unit, observed, hook) in enumerate(zip(record.unit_records, controller.observations, hooks)):
        port, label, value, unit_ref, is_root = observed
        contribution, view = hook
        assert (port, label, is_root) == ("identity", "repeated readable label", True)
        assert value is unit.controller_input is contribution.controller_input is view.controller_input is values[index]
        assert unit_ref is unit.unit_ref is view.unit_ref
        assert unit_ref == UnitRef(expected_episode.episode_id, index)
    assert len({unit.unit_id for unit in record.unit_records}) == 3


@pytest.mark.parametrize("asynchronous", [False, True])
def test_resume_replays_actual_positions_before_the_next_completed_action(asynchronous):
    values = [FixtureValue(4), FixtureValue(-1), FixtureValue(-1)]
    controller = IdentityController()
    source_views, hooks = [], []

    def choose(view):
        source_views.append(view.units_consumed)
        if view.units_consumed == 2:
            return Leaf(None, lambda _: values[2], lambda _, value: value, "same label")

    episode, context = fixture_episode(controller, Source(choose),
        resume_units=tuple(ResumeUnit("same label", value) for value in values[:2]),
        on_unit=lambda item, contribution, view: hooks.append(view))
    record = run_episode(episode, context, asynchronous)

    assert source_views == [2, 3]
    assert record.units_consumed == len(controller.observations) == 3
    assert len(hooks) == 1
    assert [row[3].unit_index for row in controller.observations] == [0, 1, 2]
    for index, (observed, unit) in enumerate(zip(controller.observations, record.unit_records)):
        assert observed[2] is values[index] is unit.controller_input
        assert observed[3] is unit.unit_ref
        assert observed[3] == UnitRef(record.episode_id, index)
    assert hooks[0].unit_ref is record.unit_records[2].unit_ref


@pytest.mark.parametrize("starting_unit_index", [0, 7])
def test_async_single_unit_uses_restored_offset_without_controller_history(starting_unit_index):
    controller = IdentityController()
    value = FixtureValue(-7)
    views = []

    def choose(view):
        views.append(view)
        return Leaf(None, lambda _: value, lambda _, result: result, "same label")

    episode, context = fixture_episode(controller, Source(choose))
    unit = asyncio.run(episode.run_unit_async(context,
        expected_label="same label", starting_unit_index=starting_unit_index))

    assert len(controller.observations) == 1
    assert views[0].units_consumed == starting_unit_index
    assert controller.observations[0][2] is value is unit.controller_input
    assert controller.observations[0][3] is unit.unit_ref
    assert unit.unit_ref == UnitRef(views[0].episode_ref.episode_id, starting_unit_index)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("optional_port", [None, "not callable"])
def test_legacy_episode_observer_keeps_its_original_signature(asynchronous, optional_port):
    controller = LegacyController()
    controller.observe_unit = optional_port
    value = FixtureValue(-3)
    episode, context = fixture_episode(controller,
        leaves([value], extract=lambda item: item, result=lambda _, item: item))

    record = run_episode(episode, context, asynchronous)

    assert controller.observations == [("legacy", "unit-0", value, None, True)]
    assert record.units_consumed == 1
    assert record.unit_records[0].controller_input is value


@pytest.mark.parametrize("identity_aware", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_direct_advance_without_identity_uses_only_legacy_observe(identity_aware, nested):
    controller = IdentityController() if identity_aware else LegacyController()
    runtime = ControllerRuntime()
    path = (("fixture", "root"), ("fixture", "child")) if nested else (("fixture", "root"),)
    scope = runtime.open_scope(path, lambda _: controller)
    opaque_value = object()

    runtime.advance(scope, 17, opaque_value)

    assert controller.observations == [("legacy", "17", opaque_value, None, not nested)]


def test_direct_advance_with_actual_identity_uses_optional_port_once():
    controller = IdentityController()
    runtime = ControllerRuntime()
    scope = runtime.open_scope((("fixture", "root"), ("fixture", "child")), lambda _: controller)
    unit_ref = UnitRef(EpisodeRef("actual-run", scope).episode_id, 8)
    opaque_value = object()

    runtime.advance(scope, "readable label", opaque_value, unit_ref=unit_ref)

    assert controller.observations == [("identity", "readable label", opaque_value, unit_ref, False)]
    assert controller.observations[0][2] is opaque_value
    assert controller.observations[0][3] is unit_ref


def test_direct_advance_with_identity_keeps_a_legacy_observer_unchanged():
    controller = LegacyController()
    runtime = ControllerRuntime()
    scope = runtime.open_scope((("fixture", "root"),), lambda _: controller)
    unit_ref = UnitRef(EpisodeRef("actual-run", scope).episode_id, 8)
    opaque_value = object()

    runtime.advance(scope, "readable label", opaque_value, unit_ref=unit_ref)

    assert controller.observations == [("legacy", "readable label", opaque_value, None, True)]


@pytest.mark.parametrize("unit_ref", ["unit-0", {"episode_id": "missing", "unit_index": 0}, object()])
def test_direct_advance_rejects_untyped_identity_before_any_observation(unit_ref):
    controller = IdentityController()
    runtime = ControllerRuntime()
    scope = runtime.open_scope((("fixture", "root"),), lambda _: controller)

    with pytest.raises(TypeError, match="actual UnitRef"):
        runtime.advance(scope, "unit-0", object(), unit_ref=unit_ref)

    assert controller.observations == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unowned_dispatch_is_rejected_without_completion_identity(asynchronous):
    controller = IdentityController()
    value = FixtureValue(5)
    phases, dispatches = iter(range(3)), []

    def dispatch(context):
        assert not controller.observations
        dispatches.append(context.path)
        return "selected-pending-handle"

    async def dispatch_async(context):
        return dispatch(context)

    def choose(view):
        phase = next(phases)
        if phase == 0:
            return DeferredUnit("original-commission", dispatch_async if asynchronous else dispatch)
        if phase == 1:
            assert view.units_consumed == 0
            assert not controller.observations
            return Leaf(None, lambda _: value, lambda _, result: result, "completed-own-action")

    episode, context = fixture_episode(controller, Source(choose))
    expected = ValueError if asynchronous else TypeError
    with pytest.raises(expected, match='registered original receiver|async method loop'):
        run_episode(episode, context, asynchronous)
    assert len(dispatches) == int(asynchronous)
    assert controller.observations == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_failed_acquisition_supplies_no_identity_or_observation(asynchronous):
    controller = IdentityController()

    def fail(_):
        raise RuntimeError("fixture acquisition failed")

    episode, context = fixture_episode(controller,
        Source(lambda _: Leaf(None, fail, lambda _, value: value, "failed-action")))

    with pytest.raises(RuntimeError, match="fixture acquisition failed"):
        run_episode(episode, context, asynchronous)

    assert controller.observations == []


def test_episode_rejects_a_foreign_scope_before_constructing_completion_identity():
    controller = IdentityController()
    value = FixtureValue(1)
    leaf = Leaf(None, lambda _: value, lambda _, result: result, "same label")
    episode, context = fixture_episode(controller, Source(lambda _: leaf))
    active_scope = context.enter(episode.grain, episode.key)
    foreign_scope = context.runtime.open_scope((("fixture", "foreign"),), lambda _: controller)
    records = []
    try:
        with pytest.raises(ValueError, match="active Episode scope"):
            episode._append_record(context, foreign_scope, records, leaf.label, leaf.acquire(context))
    finally:
        context.leave(active_scope)

    assert records == []
    assert controller.observations == []
