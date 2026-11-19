"""The runner's behaviours that need an episode driven by a plan: services, the decision context and the service
reads it records, side effects and their resumption, abandoned attempts, child slots, a slot that commissions its
own kind, selected return fields, a closing value written by a tool unit, the three yield controllers (nothing
else ends an Episode), credit that reads records and is returned as the system's credit, a closed run and a cut
run whose credit counts held records resumed from the recorded initial credit, and settings."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, CustodyError, JournalError, link, resume
from method_loop import FormError

from .fact_collection.fact_extraction.episode import FactExtraction
from .probe.episode import Probe
from .probe_world import (CONTINUATION, EXTRACTION, SETTINGS, again, child, collaborators, journal_rows, outcomes,
                          probe_path, registry, run, tool, world)  # noqa: F401 - ``world`` is the fixture

# Credit that is an inventory of the Episode's custody: the number of cells of sheet ``s`` it holds.
HELD_CELLS = {'rule': 'cells', 'sheet': 's'}


def writes(world, *cells):
    """A plan step: one unit that writes ``cells`` (``[cell, value]`` each) of the sheet whose held cells are the
    credit."""
    return tool('sheet', sheet='s', cells=[list(cell) for cell in cells], source_ref=world['subject'])


def credit_before_any_unit(linked):
    """What ``credit`` of the entry Episode's summary before any unit says of the records the Episode holds now."""
    return Probe.credit({'credit': HELD_CELLS, 'steps': 0, 'outcomes': []}, linked.episode.records)


def test_a_tool_reaches_only_the_services_its_episode_declared_and_each_is_built_once(world):
    result = run(world, 'services', [tool('bump'), tool('bump')])
    assert [outcome['outcome'] for outcome in outcomes(world, 'services')] == [
        {'count': 1, 'secret_hidden': True, 'service_names': ['counter', 'switch', 'work_cache']},
        {'count': 2, 'secret_hidden': True, 'service_names': ['counter', 'switch', 'work_cache']}]
    # Built once, on first use; 'switch' and 'work_cache' were not used and 'secret' is not declared.
    assert world['built'] == ['counter']
    assert result['result'].as_record()['n'] == 2
    journal = world['journal']
    assert journal.services('services') == {'probe': ['counter', 'switch', 'work_cache'],
                                            'fact_collection/fact_extraction': []}
    assert journal.service_builds('services') == [{'name': 'counter', 'path': probe_path('services'), 'unit': 0}]
    again(world, 'services')                  # a closed run replays its units: no service is built or recorded again
    assert len(journal.service_builds('services')) == 1


def test_decide_sees_its_settings_services_clock_and_identity_and_a_resume_sees_the_same(world):
    log = world['tmp'] / 'side_effects.log'
    settings = {**SETTINGS, 'threshold': {'worth': 3}}
    continuation = {**CONTINUATION, 'probe': settings}
    plan = [tool('bump'), {'show_context': True}, tool('effect', log=str(log)), {'show_context': True}]
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'context', plan, continuation=continuation)
    world['switch'].fail = False
    first = outcomes(world, 'context')[1]['outcome']
    seen = first['decide']
    assert seen['settings'] == settings and seen['services'] == ['counter', 'switch', 'work_cache']
    assert seen['run_id'] == 'context' and seen['binding_path'] == 'probe' and seen['key'] == 'context'
    assert seen['episode_id'] == first['tool']['episode_id'] and first['tool']['settings'] == settings
    clock = seen['clock']
    assert clock['status'] == 'available' and clock['elapsed_seconds'] > 0 and clock['began_at'] < clock['now']
    assert clock['progress_time_position'] == 0          # the receipt of the unit completed before this decision
    again(world, 'context', continuation=continuation)
    units = outcomes(world, 'context')
    assert units[1]['outcome'] == first                   # the completed unit was replayed, not decided again
    later = units[3]['outcome']['decide']['clock']
    assert later['progress_time_position'] == 2 and later['elapsed_seconds'] > clock['elapsed_seconds']
    # The clock of a decision is recorded once: a second resume of the closed run rebuilds nothing.
    points = world['journal'].db.execute("SELECT name FROM progress_points WHERE run_id='context' AND name LIKE "
                                         "'episode_runtime.decision_point.%' ORDER BY name").fetchall()
    assert [row[0][-1] for row in points] == ['0', '1', '2', '3']
    again(world, 'context', continuation=continuation)
    assert len(world['journal'].db.execute("SELECT name FROM progress_points WHERE run_id='context' AND name LIKE "
                                           "'episode_runtime.decision_point.%'").fetchall()) == 4


def test_an_interruption_after_a_side_effect_reruns_the_unit_with_its_key_and_resumed_set(world):
    log = world['tmp'] / 'side_effects.log'
    plan = [tool('effect', log=str(log))]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        run(world, 'effect', plan)
    journal = world['journal']
    began = journal.attempts('effect', probe_path('effect'))
    assert [(index, label, state) for index, label, _, state in began] == [(0, 'tool:effect:0', 'began')]
    assert journal.units('effect', probe_path('effect')) == []
    orphan = [row['ref'] for row in journal.receipts('effect', probe_path('effect')) if row['how'] == 'produced']
    assert len(orphan) == 1
    world['switch'].fail = False
    resumed = again(world, 'effect')
    outcome = outcomes(world, 'effect')[0]
    key = began[0][2]
    assert outcome['outcome'] == {'ref': outcome['produced'][0], 'resumed': True, 'operation_key': key,
                                  'already_logged': True}
    assert log.read_text().splitlines() == [key]                 # the tool was idempotent on the key
    assert outcome['produced'] != orphan and len(outcome['produced']) == 1
    held = [row['ref'] for row in journal.receipts('effect', probe_path('effect')) if row['how'] == 'produced']
    assert held == outcome['produced']                            # the abandoned attempt's record is not held
    assert journal.abandoned('effect', probe_path('effect'), 0) == orphan     # and its receipt is kept as trace
    assert journal.times_begun('effect', probe_path('effect'), 0) == 2
    assert [state for *_, state in journal.attempts('effect', probe_path('effect'))] == ['finished']
    assert resumed['result'].as_record()['produced'] == [outcome['produced']]


@pytest.mark.parametrize('reclaim', [False, True])
def test_a_rerun_is_told_what_its_abandoned_attempt_produced_and_may_read_or_take_it_over(world, reclaim):
    run_id = 'intent_' + str(reclaim)
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='cut after the intent was written'):
        run(world, run_id, [tool('intent', reclaim=reclaim)])
    journal, path = world['journal'], probe_path(run_id)
    first, = [row['ref'] for row in journal.receipts(run_id, path) if row['how'] == 'produced']
    world['switch'].fail = False
    again(world, run_id)
    outcome = outcomes(world, run_id)[0]
    key = journal.attempts(run_id, path)[0][2]
    assert outcome['outcome']['resumed'] is True
    assert outcome['outcome']['abandoned'] == [{'ref': first, 'producer_unit': 0, 'held': False,
                                                'content': 'intent ' + key + ' resumed False'}]
    held = [row['ref'] for row in journal.receipts(run_id, path) if row['how'] == 'produced']
    if reclaim:
        assert outcome['produced'] == [first] == held and outcome['outcome']['marker'] == first
    else:
        assert first not in outcome['produced'] and first not in held and len(outcome['produced']) == 1
    assert journal.abandoned(run_id, path, 0) == [first]          # kept in the journal either way


def test_what_a_decision_reads_from_a_service_is_recorded_and_a_resume_decides_on_the_recorded_value(world):
    """Both plan steps take an argument ``decide`` reads from a service (``ctx.services['counter'].read('count')``).
    The first unit is interrupted and the service's value changes before the resume: the unit is decided again on
    the recorded value, so it is the same unit and the run goes on. The second unit is decided for the first time
    after the change and reads the new value. A resume of the closed run after another change replays the same."""
    log = world['tmp'] / 'side_effects.log'
    plan = [{'tool_with_count': 'effect', 'arguments': {'log': str(log)}},
            {'tool_with_count': 'echo', 'arguments': {}}]
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'reads', plan)
    journal, path = world['journal'], probe_path('reads')
    request = {'service': 'counter', 'member': 'count', 'arguments': []}
    assert journal.service_reads('reads', path) == [{'position': 0, 'request': request, 'value': 0}]
    world['switch'].fail = False
    world['counter'].count = 7
    first = again(world, 'reads')['result'].as_record()
    rerun, fresh = outcomes(world, 'reads')
    assert rerun['arguments']['count'] == 0 and rerun['outcome']['resumed'] is True     # decided on the record
    assert fresh['arguments']['count'] == 7                                               # read after the change
    assert journal.service_reads('reads', path) == [{'position': 0, 'request': request, 'value': 0},
                                                     {'position': 1, 'request': request, 'value': 7}]
    assert journal.times_begun('reads', path, 0) == 2 and first['n'] == 2
    # The resumed process did not ask the counter service for unit 0: it built it only for the read of unit 1,
    # after the switch service the rerun tool used.
    assert world['built'] == ['counter', 'switch', 'switch', 'counter']
    world['counter'].count = 9
    assert again(world, 'reads')['result'].as_record() == first
    assert len(journal.service_reads('reads', path)) == 2 and len(world['built']) == 4     # nothing read or built


def test_a_decision_is_handed_read_handles_and_never_the_service(world):
    """``ctx.services`` of ``decide`` and ``action`` maps the declared names to read handles: a handle reads a
    public member as JSON and cannot act; a tool is handed the service itself."""
    from episode_runtime import DecisionServices, ServiceReader
    from episode_runtime.recording import ServiceReads
    asked = []

    class Table:
        factor = 3

        def estimate(self, job, scale):
            asked.append(job)
            return {'job': job, 'seconds': scale * self.factor}

        def handle(self):
            return object()
    table = Table()
    reads = ServiceReads(world['journal'], 'handles', probe_path('handles'))
    services = DecisionServices({'table': table}, reads.at(0))
    assert list(services) == ['table'] and isinstance(services['table'], ServiceReader)
    assert not hasattr(services['table'], 'estimate') and not hasattr(services['table'], 'factor')
    assert services['table'].read('factor') == 3
    assert services['table'].read('estimate', 'j1', 2) == {'job': 'j1', 'seconds': 6}
    table.factor = 10
    assert services['table'].read('estimate', 'j1', 2) == {'job': 'j1', 'seconds': 6}    # the recorded value
    assert services['table'].read('estimate', 'j1', 4) == {'job': 'j1', 'seconds': 40}   # another request
    assert asked == ['j1', 'j1']
    # The next unit position reads again; a resumed process (a new object over the journal) replays position 0.
    assert DecisionServices({'table': table}, reads.at(1))['table'].read('factor') == 10
    replay = DecisionServices({'table': table}, ServiceReads(world['journal'], 'handles', probe_path('handles')).at(0))
    assert replay['table'].read('factor') == 3 and asked == ['j1', 'j1']
    with pytest.raises(KeyError, match='service_not_declared_by_this_episode:other'):
        services['other']
    with pytest.raises(ValueError, match='service_read_member_must_be_a_public_name'):
        services['table'].read('_private')
    with pytest.raises(TypeError, match='service_read_member_takes_no_arguments:table.factor'):
        services['table'].read('factor', 1)
    with pytest.raises(TypeError, match='service_read_value:table.handle_must_be_closed_json'):
        services['table'].read('handle')


def test_a_controller_stop_ends_the_episode_and_a_resume_of_the_stopped_run_replays_it(world):
    stop = {'probe': {'cost': 1e9, 'parameters': SETTINGS['parameters']}, 'fact_collection/fact_extraction': SETTINGS}
    first = run(world, 'stopped', [tool('bump'), tool('bump'), tool('bump')], continuation=stop,
                controller={'kind': 'accumulation'})
    assert first['record'].ended_by == 'yield_stop' and first['record'].units_consumed < 3
    journal = world['journal']
    assert journal.run_state('stopped')[1]['ended_by'] == 'yield_stop'
    assert journal.episodes('stopped')[0]['completion']['ended_by'] == 'yield_stop'
    steps = journal.controller_steps('stopped', probe_path('stopped'))
    assert [step['stop'] for step in steps] == [False] * (len(steps) - 1) + [True]
    assert steps[-1]['decision']['continuation_cost'] == 1e9
    resumed = again(world, 'stopped', continuation=stop)
    assert resumed['record'].ended_by == 'yield_stop'
    assert resumed['result'].as_record() == first['result'].as_record()


@pytest.mark.parametrize('controller, cost', [({'kind': 'accumulation'}, 0.5), ({'kind': 'bounded', 'maximum': 3}, 0.0),
                                              ({'kind': 'completion', 'target': 3}, 0.0)])
def test_a_closed_run_whose_credit_counts_held_records_is_resumed_from_its_recorded_initial_credit(world, controller,
                                                                                                    cost):
    """Credit is the number of cells of a sheet the Episode holds: an inventory of its custody. Three units write
    one cell each. Under the accumulating controller the units after them earn nothing until the estimator stops
    the Episode; under the other two the third cell reaches the declared limit. A resume of the closed run builds
    the Episode with every cell already held, so ``credit`` of its summary before any unit now says 3. The
    controller is built from the credit recorded when the Episode was first entered (0): it observes the recorded
    units again and stops where it stopped. No unit runs, no model is asked and nothing is recorded."""
    run_id = 'held_' + controller['kind']
    settings = {**CONTINUATION, 'probe': {'cost': cost, 'parameters': SETTINGS['parameters']}}
    plan = [writes(world, ['a1', 1]), writes(world, ['a2', 2]), writes(world, ['a3', 3])]
    first = run(world, run_id, plan, continuation=settings, credit=HELD_CELLS, controller=controller)
    journal, path, record = world['journal'], probe_path(run_id), first['record']
    units = record.units_consumed
    assert record.ended_by == 'yield_stop' and (units > 3 if controller['kind'] == 'accumulation' else units == 3)
    assert [value['credit'] for _, value, _, _ in journal.units(run_id, path)] == [1.0, 2.0, 3.0] + [3.0] * (units - 3)
    assert journal.episodes(run_id)[0]['initial_credit'] == 0.0
    recorded = journal_rows(world)
    relinked = resume(registry(), run_id=run_id, journal=journal, collaborators=collaborators(world, settings))
    assert credit_before_any_unit(relinked) == 3.0              # the Episode holds the three cells before the replay
    resumed = asyncio.run(relinked.run())
    assert resumed['result'].as_record() == first['result'].as_record()
    assert resumed['record'].units_consumed == units
    state = resumed['record'].controller_state
    assert (state.initial_credit, state.current_credit, state.stop) == (0.0, 3.0, True)
    assert state.history == record.controller_state.history == (1.0, 1.0, 1.0) + (0.0,) * (units - 3)
    assert [(unit.controller_step.credit, unit.controller_step.marginal_credit, unit.controller_step.stop)
            for unit in resumed['record'].unit_records] == [
        (step['credit'], step['marginal_credit'], step['stop']) for step in journal.controller_steps(run_id, path)]
    assert journal_rows(world) == recorded                      # no unit, no attempt, no model call, no receipt
    assert journal.model_calls(run_id, path) == [] and list(world['calls'].glob('call-*')) == []
    assert again(world, run_id, continuation=settings)['result'].as_record() == first['result'].as_record()


def test_a_cut_run_whose_credit_counts_held_records_goes_on_mid_way_from_its_recorded_initial_credit(world):
    """The same credit, toward a target of four cells. The run is cut in its third unit, after two units wrote
    three cells, so the resumed Episode holds three cells when its controller is built. Built from the recorded
    initial credit (0), the controller has after the replay the history of the run that was cut, the run goes on
    from there, and it ends as the same plan ends when nothing cuts it."""
    log = world['tmp'] / 'side_effects.log'
    plan = [writes(world, ['a1', 1]), writes(world, ['a2', 2], ['a3', 3]), tool('effect', log=str(log)),
            writes(world, ['a4', 4])]
    message = {'credit': HELD_CELLS, 'controller': {'kind': 'completion', 'target': 4}}
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        run(world, 'held_cut', plan, **message)
    world['switch'].fail = False
    journal, path = world['journal'], probe_path('held_cut')
    assert [value['credit'] for _, value, _, _ in journal.units('held_cut', path)] == [1.0, 3.0]
    assert journal.episodes('held_cut')[0]['initial_credit'] == 0.0
    relinked = resume(registry(), run_id='held_cut', journal=journal, collaborators=collaborators(world))
    assert credit_before_any_unit(relinked) == 3.0              # the Episode holds three cells before the replay
    resumed = asyncio.run(relinked.run())
    state = resumed['record'].controller_state
    assert (state.initial_credit, state.history, state.current_credit) == (0.0, (1.0, 2.0, 0.0, 1.0), 4.0)
    assert [(step['credit'], step['marginal_credit'], step['stop'])
            for step in journal.controller_steps('held_cut', path)] == [
        (1.0, 1.0, False), (3.0, 2.0, False), (3.0, 0.0, False), (4.0, 1.0, True)]
    assert [journal.times_begun('held_cut', path, unit) for unit in range(4)] == [1, 1, 2, 1]
    done = resumed['result'].as_record()
    assert (done['credit'], done['n']) == (4.0, 4)
    assert journal.episodes('held_cut')[0]['completion'] == {'ended_by': 'yield_stop', 'units': 4, 'credit': 4.0}
    # The same plan, not cut: the same controller history, credits and end.
    whole = run(world, 'held_whole', plan, **message)
    uncut = whole['record'].controller_state
    assert (uncut.initial_credit, uncut.history, uncut.current_credit) == (
        state.initial_credit, state.history, state.current_credit)
    assert (whole['result'].as_record()['credit'], whole['record'].units_consumed) == (4.0, 4)
    # The run that was cut and finished is closed: resumed again, it replays to the same end and records nothing.
    recorded = journal_rows(world)
    assert again(world, 'held_cut')['result'].as_record() == done
    assert journal_rows(world) == recorded and journal.model_calls('held_cut', path) == []


def test_different_settings_or_services_on_resume_raise_instead_of_changing_the_run(world):
    log = world['tmp'] / 'side_effects.log'
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'settings', [tool('effect', log=str(log))])
    world['switch'].fail = False
    other = {'probe': {'cost': 1e9, 'parameters': SETTINGS['parameters']},
             'fact_collection/fact_extraction': SETTINGS}
    with pytest.raises(JournalError, match='recorded_continuation_settings_differ:probe'):
        resume(registry(), run_id='settings', journal=world['journal'], collaborators=collaborators(world, other))
    assert world['journal'].settings('settings') == CONTINUATION
    world['journal'].db.execute("UPDATE services SET names='[\"counter\"]' WHERE run_id='settings' AND "
                                "binding_path='probe'")
    with pytest.raises(JournalError, match='recorded_services_differ:probe'):
        resume(registry(), run_id='settings', journal=world['journal'], collaborators=collaborators(world))


def test_child_slots_are_attributed_and_the_commission_arguments_are_kept(world):
    plan = [child('left', field='name', prediction='GeneX'), child('right', field='function', prediction='kinase')]
    result = run(world, 'slots', plan)['result'].as_record()
    left, right = outcomes(world, 'slots')
    assert (left['slot'], right['slot']) == ('left', 'right')
    assert left['arguments']['prediction'] == 'GeneX' and right['arguments']['prediction'] == 'kinase'
    assert left['message']['objective'] == 'Extract name for the left slot'
    assert left['report']['fact_content'] == 'GeneX' and right['report']['fact_content'] == 'kinase'
    assert result['slots'] == ['left', 'right']


def test_the_view_and_its_reports_are_restored_exactly_on_resume(world):
    log = world['tmp'] / 'side_effects.log'
    plan = [child('left', field='name'), tool('effect', log=str(log)), child('right', field='function')]
    uninterrupted = run(world, 'whole', plan[:1] + [tool('bump')] + plan[2:])['result'].as_record()
    assert (uninterrupted['n_updates'], uninterrupted['n_reports']) == (2, 2)
    world['switch'].fail = True
    with pytest.raises(RuntimeError):
        run(world, 'cut', plan)
    world['switch'].fail = False
    resumed = again(world, 'cut')['result'].as_record()
    assert (resumed['n_updates'], resumed['n_reports']) == (2, 2)
    assert resumed['slots'] == uninterrupted['slots'] and resumed['subject_names'] == ['GeneX']
    journal = world['journal']
    credits = [value['credit'] for _, value, _, _ in journal.units('cut', probe_path('cut'))]
    assert credits == [1.0, 2.0, 3.0]
    assert again(world, 'cut')['result'].as_record() == resumed


def test_an_episode_commissions_its_own_kind_three_deep_and_resumes_from_an_interruption_at_the_bottom(world):
    log = world['tmp'] / 'side_effects.log'
    bottom = [tool('bump'), tool('effect', log=str(log))]
    plan = [child('nested', plan=[child('nested', plan=bottom)]), child('right', field='name')]
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        run(world, 'own_kind', plan)
    journal = world['journal']
    top, middle = probe_path('own_kind'), (*probe_path('own_kind'), ('probe', 'nested_0'))
    deepest = (*middle, ('probe', 'nested_0'))
    assert [(len(row['path']), row['binding_path'], row['state']) for row in journal.episodes('own_kind')] == [
        (1, 'probe', 'active'), (2, 'probe', 'active'), (3, 'probe', 'active')]
    assert [state for *_, state in journal.attempts('own_kind', top)] == ['began']
    assert [state for *_, state in journal.attempts('own_kind', middle)] == ['began']
    assert [state for *_, state in journal.attempts('own_kind', deepest)] == ['finished', 'began']
    world['switch'].fail = False
    result = again(world, 'own_kind')
    assert result['result'].as_record()['slots'] == ['nested', 'right']
    assert [(len(row['path']), row['state']) for row in journal.episodes('own_kind')] == [
        (1, 'closed'), (2, 'closed'), (3, 'closed'), (2, 'closed')]
    assert [label for label, *_ in journal.units('own_kind', deepest)] == ['tool:bump:0', 'tool:effect:1']
    bottom_effect = journal.units('own_kind', deepest)[1][2]['outcome']
    assert bottom_effect['resumed'] is True and bottom_effect['already_logged'] is True
    assert world['counter'].count == 1                              # the completed unit below was not run again
    assert [unit[2]['report'] for unit in journal.units('own_kind', top)][0] == {
        'slot': 'nested', 'n': 1, 'returned_cells': []}
    assert journal.times_begun('own_kind', top, 0) == 2 and journal.times_begun('own_kind', deepest, 0) == 1
    assert again(world, 'own_kind')['result'].as_record() == result['result'].as_record()


@pytest.mark.parametrize('controller', [{'kind': 'completion', 'target': 2}, {'kind': 'bounded', 'maximum': 2}])
def test_a_controller_built_from_the_parent_input_stops_the_episode_at_what_the_commissioner_asked(world, controller):
    """``yield_controller`` reads ``parent_input`` (what ``read_from_parent`` made of the commission): the
    commissioner's target ends a five-step plan after two units, and the closed run resumes to the same end."""
    run_id = 'asked_' + controller['kind']
    result = run(world, run_id, [tool('bump')] * 5, controller=controller)
    assert (result['record'].ended_by, result['record'].units_consumed) == ('yield_stop', 2)
    journal = world['journal']
    assert [value['credit'] for _, value, _, _ in journal.units(run_id, probe_path(run_id))] == [1.0, 2.0]
    assert [step['stop'] for step in journal.controller_steps(run_id, probe_path(run_id))] == [False, True]
    resumed = again(world, run_id)
    assert (resumed['record'].ended_by, resumed['record'].units_consumed) == ('yield_stop', 2)
    nested = run(world, run_id + '_nested', [child('nested', plan=[tool('bump')] * 5, controller=controller)])
    child_path = (*probe_path(run_id + '_nested'), ('probe', 'nested_0'))
    assert nested['record'].units_consumed == 1 and len(journal.units(run_id + '_nested', child_path)) == 2
    assert outcomes(world, run_id + '_nested')[0]['completion'] == {
        'ended_by': 'yield_stop', 'units_consumed': 2}


def test_credit_reads_the_records_its_units_produced_and_its_children_returned(world):
    log = world['tmp'] / 'side_effects.log'
    expected = [len(json.dumps({'resumed': False})),
                len(json.dumps({'field': 'name', 'value': 'GeneX', 'source_ref': world['subject']}, sort_keys=True))]
    result = run(world, 'bytes', [tool('effect', log=str(log)), child('left', field='name')],
                 credit={'rule': 'bytes'}, controller={'kind': 'completion', 'target': sum(expected)})
    produced, returned = outcomes(world, 'bytes')
    sizes = [len(world['store'].get_artifact(produced['produced'][0])),
             len(world['store'].get_artifact(returned['result']['fact_refs'][0]))]
    credits = [value['credit'] for _, value, _, _ in world['journal'].units('bytes', probe_path('bytes'))]
    assert credits == [float(sizes[0]), float(sizes[0] + sizes[1])] and sizes == expected
    # The returned credit is the one the controller stopped on. ``final_to_parent`` has no records and could
    # not compute this credit itself: the system hands it over in ``completion``.
    assert result['result'].as_record()['credit'] == credits[-1] == float(sum(sizes))
    assert world['journal'].episodes('bytes')[0]['completion'] == {'ended_by': 'yield_stop', 'units': 2,
                                                                  'credit': credits[-1]}


@pytest.mark.parametrize('gaining', [0, 3])
def test_an_episode_with_nothing_left_to_do_goes_on_until_its_yield_estimator_stops_it(world, gaining):
    """A plan of ``gaining`` steps under an accumulating controller: after the plan the task has only units that
    do nothing and earn nothing (``idle``), as a head with only an outstanding job has only waits and checks. The
    task cannot end the Episode; the estimator does, once its forecast of the next unit's credit is at or below
    the cost, and sooner for a higher cost. Whether such a unit earns anything is the episode's own credit."""
    ends = {}
    for cost in (0.01, 0.5):
        run_id = 'gain_' + str(gaining) + '_' + str(cost).replace('.', '_')
        settings = {**CONTINUATION, 'probe': {'cost': cost, 'parameters': SETTINGS['parameters']}}
        result = run(world, run_id, [tool('bump')] * gaining, continuation=settings,
                     controller={'kind': 'accumulation'})
        assert result['record'].ended_by == 'yield_stop'
        ends[cost] = result['record'].units_consumed
        steps = world['journal'].controller_steps(run_id, probe_path(run_id))
        assert [step['stop'] for step in steps] == [False] * (len(steps) - 1) + [True]
        assert [step['credit'] for step in steps] == [float(min(index + 1, gaining)) for index in range(len(steps))]
        assert [unit[2]['tool'] for unit in world['journal'].units(run_id, probe_path(run_id))] == (
            ['bump'] * gaining + ['idle'] * (len(steps) - gaining))
        done = result['result'].as_record()
        assert (done['n'], done['credit'], done['finding']) == (
            gaining, float(gaining), {'plan_steps': gaining, 'steps_done': gaining})
    assert gaining < ends[0.5] < ends[0.01]


def test_at_no_cost_an_accumulating_episode_is_not_stopped_however_little_its_units_gain(world):
    """Twenty units of which only the first two add credit, at cost zero: no step of the estimator says stop. (The
    run ends here because its twenty-first unit is interrupted; nothing but the estimator would have ended it.)"""
    log = world['tmp'] / 'side_effects.log'
    settings = {**CONTINUATION, 'probe': {'cost': 0.0, 'parameters': SETTINGS['parameters']}}
    world['switch'].fail = True
    with pytest.raises(RuntimeError, match='interrupted after the side effect'):
        run(world, 'free', [tool('bump')] * 20 + [tool('effect', log=str(log))], continuation=settings,
            credit={'rule': 'capped', 'cap': 2}, controller={'kind': 'accumulation'})
    steps = world['journal'].controller_steps('free', probe_path('free'))
    assert [step['stop'] for step in steps] == [False] * 20
    assert [step['marginal_credit'] for step in steps] == [1.0, 1.0] + [0.0] * 18


def test_a_closing_value_is_the_outcome_of_a_tool_unit_and_reaches_the_result_through_the_summary(world):
    """Nothing but the controller closes an Episode, so a closing value (in a real episode: what the model wrote
    to close its work) is produced by a tool unit the episode declares for it. Its outcome is recorded like any
    unit's, the summary holds it and ``final_to_parent`` returns it. ``completion`` says how the system ended the
    Episode and with which credit."""
    closing = {'report': 'closing text', 'confidence': 0.5}
    plan = [tool('bump'), tool('close', **closing)]
    result = run(world, 'closing', plan, selection=['completion', 'closing'])['result'].as_record()
    assert result['closing'] == [closing] and result['n'] == 2
    assert result['completion'] == {'ended_by': 'yield_stop', 'units_consumed': 2, 'credit': 2.0}
    assert result['credit'] == 2.0 and result['finding'] == {'plan_steps': 2, 'steps_done': 2}
    assert outcomes(world, 'closing')[1]['outcome'] == {'closing': closing}
    assert world['journal'].episodes('closing')[0]['completion'] == {'ended_by': 'yield_stop', 'units': 2,
                                                                     'credit': 2.0}
    assert again(world, 'closing')['result'].as_record() == result
    plain = run(world, 'no_closing', [tool('bump')], selection=['completion', 'closing'])['result'].as_record()
    assert plain['closing'] == [] and plain['completion']['credit'] == 1.0


def test_two_parents_select_different_fields_of_one_child(world):
    from .fact_collection.episode import FactCollection
    plan = [child('left', field='name', select=['records_read']),
            child('right', field='function', select=['field', 'records_read'])]
    run(world, 'probe_selects', plan)
    left, right = outcomes(world, 'probe_selects')
    assert left['result']['records_read'] == [world['subject']] and 'field' not in left['result']
    assert right['result']['field'] == 'function' and right['result']['records_read'] == [world['subject']]
    assert left['message']['selection'] == ['records_read'] and right['message']['selection'] == ['field', 'records_read']
    # The other parent (fact_collection) always selects 'field' only.
    other = BindingRegistry([FactCollection(), FactExtraction()])
    linked = link(other, 'fact_collection', {'assignment': {'subject_refs': [world['subject']], 'field': 'name'},
                                             'message': {'fields': ['name']}, 'selection': []},
                  run_id='other_parent', journal=world['journal'], collaborators={
                      **collaborators(world), 'continuation': {'fact_collection': SETTINGS,
                                                               'fact_collection/fact_extraction': SETTINGS}})
    asyncio.run(linked.run())
    path = (('fact_collection', 'other_parent'),)
    result = world['journal'].units('other_parent', path)[0][2]['result']
    assert result['field'] == 'name' and 'records_read' not in result


@pytest.mark.parametrize('wrong, error, message', [
    ({'select': ['invented']}, FormError, 'selection_not_a_selectable_field:invented'),
    ({'select': ['credit']}, FormError, 'selection_not_a_selectable_field:credit'),
    ({'select': ['finding']}, FormError, 'selection_not_a_selectable_field:finding'),
    ({'source_refs': ['UNHELD']}, CustodyError, 'record_not_held_by_commissioner')])
def test_a_wrong_commission_fails_with_its_error(world, wrong, error, message):
    """A commission that selects a field the child does not declare as selectable, or passes a record the parent
    does not hold, raises. Nothing catches it: the run ends with the error as its recorded failure, no child
    Episode exists, the unit that began stays begun, and resuming the unchanged run raises the same error."""
    arguments = {'field': 'name', **wrong}
    if arguments.get('source_refs') == ['UNHELD']:
        arguments['source_refs'] = [world['unrelated']]
    with pytest.raises(error, match=message):
        run(world, 'wrong', [tool('bump'), child('left', **arguments)])
    journal, path = world['journal'], probe_path('wrong')
    assert message in journal.run_failure('wrong') and journal.run_state('wrong')[0] == 'active'
    assert [row['binding_path'] for row in journal.episodes('wrong')] == ['probe']
    assert [(label, state) for _, label, _, state in journal.attempts('wrong', path)] == [
        ('tool:bump:0', 'finished'), ('left_1', 'began')]
    assert len(journal.units('wrong', path)) == 1 and journal.model_calls('wrong', path) == []
    assert journal.receipts('wrong', (*path, (EXTRACTION, 'left_1'))) == []
    with pytest.raises(error, match=message):
        again(world, 'wrong')
    assert journal.times_begun('wrong', path, 1) == 2


def test_the_entry_selection_admits_only_declared_optional_fields(world):
    child_entry = {'assignment': {'source_refs': [world['subject']], 'field': 'name'}, 'message': {}}
    linked = link(BindingRegistry([FactExtraction()]), 'fact_collection/fact_extraction',
                  {**child_entry, 'selection': ['records_read']}, run_id='entry_selection',
                  journal=world['journal'], collaborators=collaborators(world))
    result = asyncio.run(linked.run())['result'].as_record()
    assert result['records_read'] == [world['subject']] and 'field' not in result
    with pytest.raises(FormError, match='selection_not_a_selectable_field:fact'):
        link(BindingRegistry([FactExtraction()]), 'fact_collection/fact_extraction',
             {**child_entry, 'selection': ['fact']}, run_id='entry_bad', journal=world['journal'],
             collaborators=collaborators(world))
