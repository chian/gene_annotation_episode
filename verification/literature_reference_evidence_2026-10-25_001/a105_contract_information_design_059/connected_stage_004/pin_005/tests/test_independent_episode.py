"""Shared-runtime independent children: synthetic work, no model or native job.

These are execution/admission tests. They do not claim durable process recovery,
application integration, a scientific result or production estimator tuning.
"""
import asyncio
import gc
import weakref

import pytest

from method_loop import (ChildEpisodeUnit, Context, Episode, EpisodeGoal,
                         EpisodeRequest, EpisodeTree, Grain, Leaf)
from method_loop.archive import JsonArchive
from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.runtime import Record, TypedReportContract
from test_runtime import FixtureController, obj


def leaf(label, work):
    return Leaf(None, lambda _: work(), lambda _, result: result, label=label)


class Source:
    def __init__(self, choose):
        self.choose = choose

    def next(self, view):
        return self.choose(view)


def world(root_steps):
    controllers = {}
    def factory(path):
        controller = FixtureController(str(path), 0, root_steps if len(path) == 1 else 2)
        controllers[path] = controller
        return controller
    root_grain = Grain('science', 'One selected action', 'Synthetic values', factory)
    tree = EpisodeTree.recursive(root_grain)
    context = Context(tree=tree, run_id='independent-fixture')
    goal = EpisodeGoal.root(objective='Investigate the fixed synthetic question', result_contract={})
    return context, goal, root_grain, controllers


def child_unit(parent_goal, grain, name, entered, release, *, archive=None, receive=None, value=2):
    contract = TypedReportContract('Return only the requested measured fixture value',
                                  obj({'value': {'type': 'integer'}}), None)
    goal = EpisodeGoal.child(parent_goal, objective='Iteratively resolve '+name,
                             result_contract=contract.schema)
    async def first():
        entered.set()
        await release.wait()
        return Record({'credit': 1})
    source = Source(lambda view: leaf('first', first) if view.units_consumed == 0 else
                    leaf('second', lambda: Record({'credit': 2})))
    source_ref = weakref.ref(source)
    child = Episode(grain, name, source, EpisodeRequest(goal, Record({}), contract),
                    lambda _: Record({'value': value}), archive_record=archive)
    unit = ChildEpisodeUnit(child, receive or (lambda *args: Record({'credit': 2})),
                            lambda result, *_: result.as_record())
    return unit, source_ref


def test_parent_and_two_children_iterate_with_separate_stacks_and_exact_reports():
    async def exercise():
        context, goal, grain, controllers = world(4)
        entered = [asyncio.Event(), asyncio.Event()]
        release = [asyncio.Event(), asyncio.Event()]
        handles, seen = [], []
        current = [0]
        def receive(result, *_):
            current[0] += result.as_record()['value']
            return Record({'credit': current[0]})
        def dispatch():
            for index in range(2):
                unit, _ = child_unit(goal, grain, 'child_'+str(index), entered[index],
                                     release[index], receive=receive)
                handles.append(unit.start_async(context, handle='execution_'+str(index)))
            assert context.child_reports == ()
            return Record({'credit': 0})
        async def own_work():
            await asyncio.gather(*(event.wait() for event in entered))
            assert context.path == (('science', 'root'),)
            assert context.child_reports == ()
            assert all(handle.status()['state'] == 'running' for handle in handles)
            assert [controller.scores for path, controller in controllers.items() if len(path) == 2] == [[], []]
            seen.append('parent worked while both children remained open')
            current[0] = 1
            for event in release:
                event.set()
            return Record({'credit': 1})
        def choose(view):
            if view.units_consumed == 0:
                return leaf('launch-selected-children', dispatch)
            if view.units_consumed == 1:
                return leaf('parent-own-work', own_work)
            return handles[view.units_consumed-2]
        root = Episode(grain, 'root', Source(choose), EpisodeRequest(goal, Record({})), lambda _: Record({}))
        result = await root.run_async(context)
        assert seen and result.ended_by == 'yield_stop'
        assert result.controller_state.scores == [0, 1, 2, 2]
        assert [record.child.units_consumed for record in result.unit_records if record.child] == [2, 2]
        assert [record.episode_update.report.as_record() for record in result.unit_records
                if record.episode_update] == [{'value': 2}, {'value': 2}]
        assert context.path == ()
        assert all(handle.status()['delivered'] for handle in handles)
        for path, controller in controllers.items():
            if len(path) == 2:
                assert controller.scores == [1, 1]
    asyncio.run(exercise())


def test_parent_yield_does_not_cancel_child_or_rewrite_history_and_closed_source_is_released(tmp_path):
    async def exercise():
        context, goal, grain, controllers = world(1)
        entered, release = asyncio.Event(), asyncio.Event()
        archive = JsonArchive(tmp_path/'archive')
        handles, references = [], []
        def dispatch():
            unit, reference = child_unit(goal, grain, 'survivor', entered, release,
                                          archive=archive.store)
            references.append(reference)
            handles.append(unit.start_async(context, handle='execution_survivor'))
            return Record({'credit': 0})
        root = Episode(grain, 'root', Source(lambda _: leaf('launch', dispatch)),
                       EpisodeRequest(goal, Record({})), lambda _: Record({}))
        parent_result = await root.run_async(context)
        before = list(parent_result.controller_state.scores)
        await entered.wait()
        assert handles[0].status() == {'handle': 'execution_survivor', 'state': 'running', 'delivered': False}
        release.set()
        await handles[0].wait_ready()
        assert handles[0].status()['state'] == 'returned'
        assert parent_result.controller_state.scores == before == [0]
        assert controllers[(('science', 'root'),)].scores == [0]
        assert len(list((tmp_path/'archive').glob('*.json'))) == 4  # two payloads and their indexes
        gc.collect()
        assert references[0]() is None
        with pytest.raises(ValueError, match='assigning active parent'):
            await handles[0].acquire_async(context)
    asyncio.run(exercise())


def test_cancelling_readiness_wait_does_not_cancel_selected_child():
    async def exercise():
        context, goal, grain, _ = world(3)
        entered, release = asyncio.Event(), asyncio.Event()
        handles = []
        def dispatch():
            unit, _ = child_unit(goal, grain, 'survivor', entered, release)
            handles.append(unit.start_async(context, handle='execution_survivor'))
            return Record({'credit': 0})
        async def observe_without_delivery():
            await entered.wait()
            waiter = asyncio.create_task(handles[0].wait_ready())
            await asyncio.sleep(0)  # fixture scheduling, not a production polling interval
            waiter.cancel()
            with pytest.raises(asyncio.CancelledError):
                await waiter
            assert handles[0].status()['state'] == 'running'
            assert context.child_reports == ()
            release.set()
            return Record({'credit': 0})
        def choose(view):
            return (leaf('launch', dispatch) if view.units_consumed == 0 else
                    leaf('observe', observe_without_delivery) if view.units_consumed == 1 else handles[0])
        root = Episode(grain, 'root', Source(choose), EpisodeRequest(goal, Record({})), lambda _: Record({}))
        result = await root.run_async(context)
        assert result.controller_state.scores == [0, 0, 2]
        assert result.unit_records[-1].episode_update.report.as_record() == {'value': 2}
    asyncio.run(exercise())


def test_independent_dispatch_checks_parent_goal_before_starting_child():
    async def exercise():
        context, goal, grain, controllers = world(1)
        other = EpisodeGoal.root(objective='Unrelated parent', result_contract={})
        entered, release = asyncio.Event(), asyncio.Event()
        def invalid_dispatch():
            unit, _ = child_unit(other, grain, 'wrong-owner', entered, release)
            with pytest.raises(ValueError, match='parent-owned child invocation'):
                unit.start_async(context, handle='wrong_owner')
            assert not entered.is_set()
            return Record({'credit': 0})
        root = Episode(grain, 'root', Source(lambda _: leaf('invalid-dispatch', invalid_dispatch)),
                       EpisodeRequest(goal, Record({})), lambda _: Record({}))
        await root.run_async(context)
        assert len(controllers) == 1
    asyncio.run(exercise())


def test_independent_return_uses_same_closed_typed_form_guard():
    async def exercise():
        context, goal, grain, controllers = world(2)
        entered, release = asyncio.Event(), asyncio.Event()
        release.set()
        handles = []
        def dispatch():
            unit, _ = child_unit(goal, grain, 'invalid-form', entered, release,
                                 value='An unrestricted findings paragraph')
            handles.append(unit.start_async(context, handle='execution_invalid_form'))
            return Record({'credit': 0})
        root = Episode(grain, 'root', Source(lambda view: leaf('launch', dispatch)
            if view.units_consumed == 0 else handles[0]), EpisodeRequest(goal, Record({})), lambda _: Record({}))
        with pytest.raises(ReportBoundaryError):
            await root.run_async(context)
        assert handles[0].status()['state'] == 'returned'
        assert not handles[0].status()['delivered']
        assert controllers[(('science', 'root'),)].scores == [0]
        assert controllers[(('science', 'root'), ('science', 'invalid-form'))].scores == [1, 1]
    asyncio.run(exercise())


def test_nested_independent_child_keeps_its_immediate_owner_and_parent_observation_boundary():
    async def exercise():
        context, goal, grain, controllers = world(3)
        entered, release = asyncio.Event(), asyncio.Event()
        descendants, handles = [], []
        contract = TypedReportContract('Return the requested scoped fixture result',
                                      obj({'value': {'type': 'integer'}}), None)
        scoped_goal = EpisodeGoal.child(goal, objective='Resolve the narrower fixture question',
                                        result_contract=contract.schema)

        class DispatchDescendant:
            label = 'dispatch-descendant'
            async def acquire_async(self, branch):
                unit, _ = child_unit(scoped_goal, grain, 'grandchild', entered, release)
                descendants.append(unit.start_async(branch, handle='execution_grandchild'))
                return await leaf('dispatch', lambda: Record({'credit': 0})).acquire_async(branch)

        def dispatch():
            scoped = Episode(grain, 'scoped', Source(lambda view: DispatchDescendant()
                if view.units_consumed == 0 else descendants[0]),
                EpisodeRequest(scoped_goal, Record({}), contract), lambda _: Record({'value': 2}))
            unit = ChildEpisodeUnit(scoped, lambda *args: Record({'credit': 2}),
                                    lambda result, *_: result.as_record())
            handles.append(unit.start_async(context, handle='execution_scoped'))
            return Record({'credit': 0})

        async def parent_work():
            await entered.wait()
            assert context.path == (('science', 'root'),)
            with pytest.raises(ValueError, match='assigning active parent'):
                await descendants[0].acquire_async(context)
            release.set()
            return Record({'credit': 0})

        def choose(view):
            return (leaf('dispatch', dispatch) if view.units_consumed == 0 else
                    leaf('parent-work', parent_work) if view.units_consumed == 1 else handles[0])
        root = Episode(grain, 'root', Source(choose), EpisodeRequest(goal, Record({})), lambda _: Record({}))
        result = await root.run_async(context)
        assert result.controller_state.scores == [0, 0, 2]
        scoped_result = result.unit_records[-1].child
        assert scoped_result.controller_state.scores == [0, 2]
        assert scoped_result.unit_records[-1].child.controller_state.scores == [1, 1]
        assert result.unit_records[-1].episode_update.report.as_record() == {'value': 2}
        assert len(controllers) == 3
    asyncio.run(exercise())


def test_pending_child_does_not_retain_closed_parent_through_delivery_callbacks():
    async def exercise():
        context, goal, grain, _ = world(1)
        entered, release = asyncio.Event(), asyncio.Event()
        handles = []
        class ParentSource:
            def receive(self, result, *_):
                return Record({'credit': result.as_record()['value']})
            def dispatch(self):
                unit, _ = child_unit(goal, grain, 'pending', entered, release, receive=self.receive)
                handles.append(unit.start_async(context, handle='execution_pending'))
                return Record({'credit': 0})
            def next(self, view):
                return leaf('launch', self.dispatch)
        source = ParentSource()
        reference = weakref.ref(source)
        root = Episode(grain, 'root', source, EpisodeRequest(goal, Record({})), lambda _: Record({}))
        await root.run_async(context)
        del root, source
        gc.collect()
        assert reference() is None
        await entered.wait()
        assert handles[0].status()['state'] == 'running'
        release.set()
        await handles[0].wait_ready()
        assert handles[0].status()['state'] == 'returned'
    asyncio.run(exercise())
