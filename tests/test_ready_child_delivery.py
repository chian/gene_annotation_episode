"""Ready child reports must not wait behind a running sibling.

This checks execution and typed receipt ordering with synthetic values only.
It makes no scientific, autonomous-workflow or durable-recovery claim.
"""
import asyncio
from types import SimpleNamespace

from method_loop import (ChildEpisodeUnit, Context, Episode, EpisodeGoal,
                         EpisodeRequest, EpisodeTree, Grain, Leaf)
from method_loop.suspension import external_wait
from gene_annotation_episode.domain import obj
from gene_annotation_episode.runtime import Record, TypedReportContract


class RecordingController:
    epoch = "fixture"

    def __init__(self):
        self.observations = []

    def observe(self, label, value, *, is_root):
        return self.observe_unit(label, value, unit_ref=None, is_root=is_root)

    def observe_unit(self, label, value, *, unit_ref, is_root):
        self.observations.append((label, value, unit_ref, is_root))
        return SimpleNamespace(stop=False, requests_transition=False)

    def state(self):
        return SimpleNamespace(stop=False)

    def transitioned(self, epoch):
        raise AssertionError("this fixture requests no epoch transition")


class FiniteSource:
    def __init__(self, items):
        self.items = iter(items)

    def next(self, view):
        return next(self.items, None)


def test_ready_zero_credit_reports_are_admitted_before_running_sibling_finishes():
    async def exercise():
        controllers = {}

        def controller(path):
            value = RecordingController()
            controllers[path] = value
            return value

        grain = Grain("science", "Selected fixture work", "Typed fixture values", controller)
        context = Context(tree=EpisodeTree.recursive(grain), run_id="ready-return-fixture")
        root_goal = EpisodeGoal.root(objective="Receive each original fixture result", result_contract={})
        release_first, release_middle, release_last = (asyncio.Event() for _ in range(3))
        entered, cancelled, receipts = [], [], []

        def child(name, value, release, *, external, starts_first=False):
            contract = TypedReportContract("Return the original selected value",
                obj({"value": {"type": "integer"}}), None)
            goal = EpisodeGoal.child(root_goal, objective="Resolve "+name,
                                     result_contract=contract.schema)

            async def work():
                entered.append(name)
                if starts_first:
                    release_first.set()
                try:
                    if external:
                        await external_wait(release.wait(), {"kind": "fixture_event", "name": name})
                    else:
                        await release.wait()
                except asyncio.CancelledError:
                    cancelled.append(name)
                    raise
                return Record({"credit": 0})

            leaf = Leaf(None, lambda _: work(), lambda _, result: result, label="fixture-work")
            episode = Episode(grain, name, FiniteSource([leaf]),
                EpisodeRequest(goal, Record({}), contract), lambda _: Record({"value": value}))

            def receive(result, *_):
                receipts.append((name, result.as_record()["value"]))
                if name == "first":
                    release_middle.set()
                elif name == "middle":
                    release_last.set()
                return Record({"credit": 0})

            return ChildEpisodeUnit(episode, receive, lambda result, *_: result.as_record(),
                                    allow_suspension=True)

        # The first two children suspend. The last child then makes the first
        # ready, but cannot finish until the parent receives both earlier
        # reports. These are causal events, without a deadline or step budget.
        units = [child("first", 7, release_first, external=True),
                 child("middle", 13, release_middle, external=True),
                 child("last", 19, release_last, external=False, starts_first=True)]
        root = Episode(grain, "root", FiniteSource(units),
                       EpisodeRequest(root_goal, Record({})), lambda _: Record({}))
        result = await root.run_async(context)

        assert entered == ["first", "middle", "last"]
        assert cancelled == []
        assert receipts == [("first", 7), ("middle", 13), ("last", 19)]
        assert [unit.episode_update.report.as_record() for unit in result.unit_records] == [
            {"value": 7}, {"value": 13}, {"value": 19}]
        assert [unit.unit_ref.unit_index for unit in result.unit_records] == [0, 1, 2]
        assert all(unit.child.goal.parent_goal_id == root_goal.goal_id for unit in result.unit_records)
        observed = controllers[(("science", "root"),)].observations
        assert [value.as_record() for _, value, _, _ in observed] == [{"credit": 0}] * 3
        assert [reference for _, _, reference, _ in observed] == [
            unit.unit_ref for unit in result.unit_records]

    asyncio.run(exercise())
