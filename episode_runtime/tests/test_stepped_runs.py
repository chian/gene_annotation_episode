"""A run's caller steps the entry Episode: ``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit``.

The probe episode is linked with the real runner, journal, Store, services and model provider. ``next_decision``
returns what the episode's own ``decide`` returns first (here a ``ModelRequest``) and the model is never asked;
``run_unit`` runs a ``ToolCall`` the test names as the Episode's next unit. Everything a unit of a whole run
leaves is left by a stepped unit too (its attempt, its receipts, its controller input and step, the closure and
the result when the controller stops), and ``resume`` replays it. Nothing here is faked."""
import asyncio
from pathlib import Path

import pytest

from episode_runtime import ChildCall, JournalError, ModelRequest, ToolCall, link, resume

from .probe.episode import Probe
from .probe.task import INSTRUCTIONS, SCHEMA
from .probe_world import (EXTRACTION, again, collaborators, entry, journal_rows, probe_path, registry, run, tool,
                          world)  # noqa: F401 - ``world`` is the fixture

COUNT = {'service': 'counter', 'member': 'count', 'arguments': []}


def linked(world, run_id, plan):
    return link(registry(), 'probe', entry(world, plan), run_id=run_id, journal=world['journal'],
                collaborators=collaborators(world))


def relinked(world, run_id):
    return resume(registry(), run_id=run_id, journal=world['journal'], collaborators=collaborators(world))


def asks_the_model(world):
    """A plan step whose decision is a model request (which of the two records is named GeneX)."""
    return {'model': {'records': [{'ref': world['unrelated'], 'name': 'GeneY'},
                                  {'ref': world['subject'], 'name': 'GeneX'}], 'wanted': 'GeneX'},
            'count_in_context': True}


def produced(world, run_id):
    return [(row['ref'], row['unit'], row['producer_unit'])
            for row in world['journal'].receipts(run_id, probe_path(run_id)) if row['how'] == 'produced']


def decision_points(world, run_id):
    return [row[0] for row in world['journal'].db.execute(
        "SELECT name FROM progress_points WHERE run_id=? AND name LIKE 'episode_runtime.decision_point.%' "
        'ORDER BY name', (run_id,))]


def test_the_next_decision_is_the_episodes_own_model_request_and_the_model_is_not_asked(world):
    journal, path = world['journal'], probe_path('first')
    step = asks_the_model(world)
    stepped = linked(world, 'first', [step, tool('bump')])
    decision = asyncio.run(stepped.next_decision())
    assert decision == ModelRequest('FAST', INSTRUCTIONS, {**step['model'], 'step': 0, 'feedback': None, 'count': 0},
                                    SCHEMA)
    # Nothing was asked and nothing was consumed: no model call, no call file, no unit, no attempt.
    assert journal.model_calls('first', path) == [] and list(world['calls'].glob('call-*')) == []
    assert journal.units('first', path) == [] and journal.attempts('first', path) == []
    assert journal.run_state('first')[0] == 'active' and journal.run_failure('first') is None
    # The Episode was entered as a run enters it: its controller is built from the credit of the initial summary,
    # and the decision context is the recorded one of unit 0 (its clock point, what it read from a service).
    view = stepped.view
    assert view.units_consumed == 0 and view.outcomes == () and view.path == path
    assert view.controller_state.stop is False and view.controller_state.current_credit == 0.0
    assert view.records.holds(world['subject']) and not view.records.holds(world['unrelated'])
    summary = Probe.internal_summary(view)
    assert summary['subject_names'] == ['GeneX'] and Probe.credit(summary, view.records) == 0.0
    assert journal.service_reads('first', path) == [{'position': 0, 'request': COUNT, 'value': 0}]
    assert decision_points(world, 'first') == ['episode_runtime.decision_point.0']
    assert world['built'] == ['counter']
    # Asked again after the service's value changed, the decision is made on the recorded read and clock.
    world['counter'].count = 4
    assert asyncio.run(stepped.next_decision()) == decision
    assert len(journal.service_reads('first', path)) == 1 and len(decision_points(world, 'first')) == 1


def test_a_unit_the_caller_names_is_recorded_as_the_unit_the_loop_runs_for_that_action(world):
    """The stepped run names, unit by unit, the actions the whole run's plan names. Both leave the same units,
    credits, controller steps, attempts, receipts, closure and result."""
    journal, subject = world['journal'], world['subject']
    log = world['tmp'] / 'side_effects.log'
    plan = [tool('read_ref', ref=subject), tool('effect', log=str(log)), tool('bump')]
    whole = run(world, 'whole', plan)['result'].as_record()
    log.unlink()
    world['counter'].count = 0

    stepped = linked(world, 'stepped', [asks_the_model(world), *plan[1:]])
    assert isinstance(asyncio.run(stepped.next_decision()), ModelRequest)
    read = asyncio.run(stepped.run_unit(ToolCall('read_ref', {'ref': subject})))      # in the model's place
    assert read == {'kind': 'tool', 'tool': 'read_ref', 'arguments': {'ref': subject}, 'outcome': {'name': 'GeneX'},
                    'produced': []}
    assert stepped.view.units_consumed == 1 and stepped.view.controller_state.current_credit == 1.0
    # The decision for the next unit is the episode's own, from the summary with that outcome.
    second = asyncio.run(stepped.next_decision())
    assert second == ToolCall('effect', {'log': str(log)})
    effect = asyncio.run(stepped.run_unit(second))
    key = journal.attempts('stepped', probe_path('stepped'))[1][2]
    assert effect['outcome'] == {'ref': effect['produced'][0], 'resumed': False, 'operation_key': key,
                                 'already_logged': False}
    assert log.read_text().splitlines() == [key]
    # What the unit wrote is held as produced by it, and the Episode's reader reads it.
    records = stepped.view.records
    assert records.receipt(effect['produced'][0])['how'] == 'produced'
    assert records.get_artifact(effect['produced'][0]) == b'{"resumed": false}'
    assert journal.run_state('stepped')[0] == 'active'
    # The last unit reaches the finite target: the controller stops the Episode and the run is closed.
    bumped = asyncio.run(stepped.run_unit(ToolCall('bump', {})))
    assert bumped['outcome']['count'] == 1 and world['built'].count('counter') == 2      # one per run
    assert stepped.view.controller_state.stop is True and stepped.view.units_consumed == 3
    result = asyncio.run(stepped.run())
    assert result['record'].ended_by == 'yield_stop' and result['result'].as_record() == whole
    for name in ('whole', 'stepped'):
        path = probe_path(name)
        assert [(label, value['credit'], value['estimation_context']['progress_time']['position'])
                for label, value, _, _ in journal.units(name, path)] == [
            ('tool:read_ref:0', 1.0, 0), ('tool:effect:1', 2.0, 1), ('tool:bump:2', 3.0, 2)]
        assert [step['stop'] for step in journal.controller_steps(name, path)] == [False, False, True]
        assert [(index, label, state) for index, label, _, state in journal.attempts(name, path)] == [
            (0, 'tool:read_ref:0', 'finished'), (1, 'tool:effect:1', 'finished'), (2, 'tool:bump:2', 'finished')]
        assert produced(world, name) == [(effect['produced'][0], 1, 1)]
        assert journal.run_state(name) == ('closed', {'ended_by': 'yield_stop', 'units': 3, 'result': whole})
        assert journal.episodes(name)[0]['completion'] == {'ended_by': 'yield_stop', 'units': 3, 'credit': 3.0}
        assert journal.run_failure(name) is None
    assert journal.model_calls('stepped', probe_path('stepped')) == [] and list(world['calls'].glob('call-*')) == []
    # The yield controller stopped the Episode: it has no further unit and no further decision.
    for step in (stepped.run_unit(ToolCall('bump', {})), stepped.next_decision()):
        with pytest.raises(RuntimeError, match='episode_stopped_by_its_yield_controller:probe'):
            asyncio.run(step)
    assert world['counter'].count == 1 and journal.run_failure('stepped') is None
    # A resume of the closed run replays the stepped units: the same result, and nothing left to step.
    assert again(world, 'stepped')['result'].as_record() == whole
    closed = relinked(world, 'stepped')
    with pytest.raises(RuntimeError, match='episode_stopped_by_its_yield_controller:probe'):
        asyncio.run(closed.next_decision())
    assert asyncio.run(closed.run())['result'].as_record() == whole and world['counter'].count == 1


def test_a_cut_stepped_unit_runs_again_on_resume_with_its_key_and_another_action_in_its_place_is_refused(world):
    journal, path = world['journal'], probe_path('cut')
    log = world['tmp'] / 'side_effects.log'
    call = ToolCall('effect', {'log': str(log)})
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        asyncio.run(linked(world, 'cut', [tool('bump'), tool('bump')]).run_unit(call))
    assert 'interrupted after the side effect' in journal.run_failure('cut')
    (index, label, key, state), = journal.attempts('cut', path)
    assert (index, label, state) == (0, 'tool:effect:0', 'began') and journal.units('cut', path) == []
    orphan = [ref for ref, _, _ in produced(world, 'cut')]
    assert len(orphan) == 1
    world['switch'].fail = False
    # The unit that began is the unit that runs again: another action at its position is refused by the journal.
    with pytest.raises(JournalError, match='abandoned_unit_differs'):
        asyncio.run(relinked(world, 'cut').run_unit(ToolCall('bump', {})))
    assert world['counter'].count == 0 and journal.times_begun('cut', path, 0) == 1
    resumed = relinked(world, 'cut')
    outcome = asyncio.run(resumed.run_unit(call))
    assert outcome['outcome'] == {'ref': outcome['produced'][0], 'resumed': True, 'operation_key': key,
                                  'already_logged': True}
    assert log.read_text().splitlines() == [key] and journal.times_begun('cut', path, 0) == 2
    assert [ref for ref, _, _ in produced(world, 'cut')] == outcome['produced'] != orphan
    assert journal.abandoned('cut', path, 0) == orphan
    assert not resumed.view.records.holds(orphan[0]) and resumed.view.records.holds(outcome['produced'][0])
    assert [state for *_, state in journal.attempts('cut', path)] == ['finished']


def test_resume_replays_the_stepped_units_and_run_finishes_the_run_by_the_episodes_own_decisions(world):
    journal, path = world['journal'], probe_path('replayed')
    first = linked(world, 'replayed', [asks_the_model(world), tool('bump'), tool('bump')])
    asyncio.run(first.run_unit(ToolCall('read_ref', {'ref': world['subject']})))
    del first                                               # the process that stepped the run is gone
    resumed = relinked(world, 'replayed')
    assert asyncio.run(resumed.next_decision()) == ToolCall('bump', {})
    view = resumed.view
    assert view.units_consumed == 1 and [outcome['tool'] for outcome in view.outcomes] == ['read_ref']
    assert view.controller_state.current_credit == 1.0
    assert journal.times_begun('replayed', path, 0) == 1    # replayed from the journal, not run again
    result = asyncio.run(resumed.run())
    assert result['record'].units_consumed == 3 and result['result'].as_record()['n'] == 3
    assert [label for label, *_ in journal.units('replayed', path)] == ['tool:read_ref:0', 'tool:bump:1',
                                                                        'tool:bump:2']
    assert world['counter'].count == 2 and journal.run_state('replayed')[0] == 'closed'
    assert journal.model_calls('replayed', path) == [] and list(world['calls'].glob('call-*')) == []
    assert again(world, 'replayed')['result'].as_record() == result['result'].as_record()


@pytest.mark.parametrize('action, error, message', [
    (ToolCall('undeclared', {}), LookupError, 'task_tool_not_declared:probe:undeclared'),
    (ChildCall('nobody', {}), LookupError, 'task_child_slot_not_declared:probe:nobody'),
    ({'tool': 'bump'}, TypeError, 'task_action_must_be_a_ToolCall_or_a_ChildCall:probe')])
def test_an_action_the_episode_cannot_run_ends_the_stepped_run_as_it_ends_any_run(world, action, error, message):
    journal, path = world['journal'], probe_path('unrunnable')
    stepped = linked(world, 'unrunnable', [tool('bump')])
    with pytest.raises(error, match=message):
        asyncio.run(stepped.run_unit(action))
    assert message in journal.run_failure('unrunnable') and journal.run_state('unrunnable')[0] == 'active'
    assert journal.attempts('unrunnable', path) == [] and journal.units('unrunnable', path) == []
    # The run is resumed like any run that an error ended, and stepped on.
    assert asyncio.run(relinked(world, 'unrunnable').run_unit(ToolCall('bump', {})))['outcome']['count'] == 1
    assert journal.run_state('unrunnable')[0] == 'closed'


def test_a_cancellation_of_the_caller_reaches_the_stepped_unit_where_it_waits(world):
    """The tool waits for a worker thread that ends only when it is cancelled. The caller's task is cancelled: the
    cancellation is raised in the tool, which waits for its thread before its scratch directory is removed, and
    the run records it as its failure. The unit began and did not finish."""
    journal, path, switch = world['journal'], probe_path('cancelled'), world['switch']
    stepped = linked(world, 'cancelled', [tool('bump')])

    async def cancel_when_the_thread_runs():
        task = asyncio.create_task(stepped.run_unit(ToolCall('scratch_cancel', {})))
        await asyncio.to_thread(switch.started.wait)
        assert switch.seen == {}                          # the thread is working; it has not finished
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(cancel_when_the_thread_runs())
    assert switch.seen['directory_existed'] is True and switch.seen['finished'] == 'finished after the cancellation'
    assert not Path(switch.seen['path']).exists()
    assert journal.run_failure('cancelled').startswith('CancelledError')
    assert [(label, state) for _, label, _, state in journal.attempts('cancelled', path)] == [
        ('tool:scratch_cancel:0', 'began')]
    assert journal.units('cancelled', path) == []


def test_a_stepped_unit_awaits_its_tools_worker_thread_and_a_child_call_runs_the_child_episode(world):
    journal, store, subject = world['journal'], world['store'], world['subject']
    stepped = linked(world, 'awaited', [tool('bump'), tool('bump'), tool('bump')])
    counted = asyncio.run(stepped.run_unit(ToolCall('scratch_work', {'ref': subject, 'unheld': world['unrelated'],
                                                                     'damaged': subject})))
    done, text = counted['outcome'], store.get_artifact(subject).decode()
    assert done['residues'] == len(text) and done['scratch_removed'] is True
    assert counted['produced'] == [done['counts_ref']] == [ref for ref, _, _ in produced(world, 'awaited')]
    commissioned = asyncio.run(stepped.run_unit(ChildCall('left', {'field': 'name', 'prediction': 'GeneX'})))
    assert commissioned['kind'] == 'child' and commissioned['slot'] == 'left'
    assert commissioned['report']['fact_content'] == 'GeneX'
    child = (*probe_path('awaited'), (EXTRACTION, 'left_1'))
    assert [(row['binding_path'], row['state']) for row in journal.episodes('awaited')] == [
        ('probe', 'active'), ('fact_collection/fact_extraction', 'closed')]
    assert journal.units('awaited', child) and len(stepped.view.child_reports) == 1
    assert stepped.view.records.receipt(commissioned['result']['fact_refs'][0])['how'] == 'returned'
    assert [label for label, *_ in journal.units('awaited', probe_path('awaited'))] == ['tool:scratch_work:0',
                                                                                        'left_1']


def test_a_resumed_stepped_run_whose_credit_counts_held_records_is_built_from_its_recorded_initial_credit(world):
    """Credit is the number of cells of a sheet the Episode holds, toward a target of four. Two stepped units write
    three cells and the process that stepped them is gone. The resumed Episode holds the three cells when its
    controller is built; the controller is built from the credit recorded when the Episode was first entered (0),
    so the view shows the controller of the run that was stepped, and the next stepped unit reaches the target."""
    journal, subject = world['journal'], world['subject']
    rule = {'rule': 'cells', 'sheet': 's'}

    def writes(*cells):
        return ToolCall('sheet', {'sheet': 's', 'cells': [list(cell) for cell in cells], 'source_ref': subject})
    first = link(registry(), 'probe', entry(world, [tool('bump')] * 3, credit=rule,
                                            controller={'kind': 'completion', 'target': 4}),
                 run_id='held', journal=journal, collaborators=collaborators(world))
    assert asyncio.run(first.next_decision()) == ToolCall('bump', {})
    assert first.view.controller_state.current_credit == 0.0
    assert journal.episodes('held')[0]['initial_credit'] == 0.0      # recorded when the Episode was entered
    asyncio.run(first.run_unit(writes(['a1', 1])))
    asyncio.run(first.run_unit(writes(['a2', 2], ['a3', 3])))
    state = first.view.controller_state
    assert (state.initial_credit, state.history, state.current_credit) == (0.0, (1.0, 2.0), 3.0)
    del first                                               # the process that stepped the run is gone
    resumed = relinked(world, 'held')
    assert asyncio.run(resumed.next_decision()) == ToolCall('bump', {})
    view = resumed.view
    # With the cells the Episode holds now, the credit of its summary before any unit is 3, not the recorded 0.
    assert Probe.credit({'credit': rule, 'steps': 0, 'outcomes': []}, view.records) == 3.0
    state = view.controller_state
    assert (view.units_consumed, state.initial_credit, state.history, state.current_credit) == (
        2, 0.0, (1.0, 2.0), 3.0)
    asyncio.run(resumed.run_unit(writes(['a4', 4])))
    state = resumed.view.controller_state
    assert (state.stop, state.initial_credit, state.history, state.current_credit) == (
        True, 0.0, (1.0, 2.0, 1.0), 4.0)
    result = asyncio.run(resumed.run())['result'].as_record()
    assert result['credit'] == 4.0
    assert journal.episodes('held')[0]['completion'] == {'ended_by': 'yield_stop', 'units': 3, 'credit': 4.0}
    # The closed run, resumed with all four cells held: replayed to the same stop, nothing to step, nothing recorded.
    recorded = journal_rows(world)
    closed = relinked(world, 'held')
    with pytest.raises(RuntimeError, match='episode_stopped_by_its_yield_controller:probe'):
        asyncio.run(closed.next_decision())
    state = closed.view.controller_state
    assert (closed.view.units_consumed, state.initial_credit, state.history) == (3, 0.0, (1.0, 2.0, 1.0))
    assert asyncio.run(closed.run())['result'].as_record() == result
    assert journal_rows(world) == recorded and world['counter'].count == 0
    assert journal.model_calls('held', probe_path('held')) == [] and list(world['calls'].glob('call-*')) == []
