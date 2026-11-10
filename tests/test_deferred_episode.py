"""Actual shared-loop dispatch/collection semantics with synthetic local work."""
import asyncio

import pytest

from method_loop import (ClosedChildUnit, Context, DeferredUnit, Episode,
                         EpisodeRequest)
from gene_annotation_episode.runtime import Record
from test_independent_episode import Source, child_unit, leaf, world


def test_deferred_child_and_parent_work_have_only_completed_action_observations():
    async def exercise():
        context, goal, grain, controllers = world(2)
        class ExternalJob(asyncio.Event):
            async def wait(self):
                from method_loop.suspension import external_wait
                return await external_wait(super().wait(),
                    {'kind': 'scheduled_external_job', 'job_id': 'fixture-job'})
        entered, release = asyncio.Event(), ExternalJob()
        invocations, phases, credit = [], iter(range(3)), [0]

        def receive(result, *_):
            credit[0] += result.as_record()['value']
            return Record({'credit': credit[0]})

        def dispatch(ctx):
            unit, _ = child_unit(goal, grain, 'child', entered, release, receive=receive)
            invocations.append(unit.start_async(ctx, handle='selected-child'))
            return invocations[-1].handle

        async def own_work():
            await entered.wait()
            assert controllers[context.path].scores == []
            assert invocations[0].status()['state'] == 'running'
            credit[0] = 1
            release.set()
            return Record({'credit': 1})

        def choose(view):
            phase = next(phases)
            if phase == 0:
                return DeferredUnit('original-commission', dispatch)
            if phase == 1:
                assert view.units_consumed == 0
                return leaf('parent-work', own_work)
            assert view.units_consumed == 1
            return invocations[0]

        parent = Episode(grain, 'root', Source(choose), EpisodeRequest(goal, Record({})),
                         lambda _: Record({}))
        record = await parent.run_async(context)
        assert record.units_consumed == 2
        assert record.controller_state.scores == [1, 2]
        assert [unit.unit_label for unit in record.unit_records] == ['parent-work', 'child']
        assert record.unit_records[-1].episode_update.report.as_record() == {'value': 2}
    asyncio.run(exercise())


def test_restored_child_boundary_runs_without_parent_and_rejects_changed_goal():
    async def exercise():
        context, goal, grain, _ = world(2)
        entered, release = asyncio.Event(), asyncio.Event()
        release.set()
        unit, _ = child_unit(goal, grain, 'restored', entered, release)
        branch = Context.from_commission(tree=context.tree, run_id=context.require_run_id(),
            parent_path=((grain.name, 'root'),), parent_goal_id=goal.goal_id,
            child_goal_id=unit.child.goal.goal_id, grain=grain.name, key='restored')
        record = await unit.child.run_async(branch)
        assert record.path == ((grain.name, 'root'), (grain.name, 'restored'))
        assert record.units_consumed == 2
        assert len(branch.runtime._controllers) == 1
        bad = Context.from_commission(tree=context.tree, run_id=context.require_run_id(),
            parent_path=((grain.name, 'root'),), parent_goal_id=goal.goal_id,
            child_goal_id='different-child-goal', grain=grain.name, key='restored')
        with pytest.raises(ValueError, match='parent-owned commission'):
            await unit.child.run_async(bad)
        assert not bad.runtime._controllers
    asyncio.run(exercise())


def test_closed_child_collection_uses_original_form_once_without_child_execution():
    async def exercise():
        context, goal, grain, controllers = world(2)
        entered, release = asyncio.Event(), asyncio.Event()
        release.set()
        unit, _ = child_unit(goal, grain, 'closed', entered, release)
        branch = Context.from_commission(tree=context.tree, run_id=context.require_run_id(),
            parent_path=((grain.name, 'root'),), parent_goal_id=goal.goal_id,
            child_goal_id=unit.child.goal.goal_id, grain=grain.name, key='closed')
        child_record = await unit.child.run_async(branch)
        child_result = unit.child.build_result(child_record)
        collection = ClosedChildUnit('original-commission', child_record, child_result,
            unit.child.request, unit.receive_result, unit.synthesize_report)
        parent = Episode(grain, 'root', Source(lambda _: collection),
                         EpisodeRequest(goal, Record({})), lambda _: Record({}))
        with pytest.raises(ValueError, match='already received'):
            await parent.run_async(context)
        assert controllers[((grain.name, 'root'),)].scores == [2]
        assert child_record.controller_state.scores == [1, 1]
        assert context.path == ()
    asyncio.run(exercise())
