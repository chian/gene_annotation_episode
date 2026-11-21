"""The local resource work execution episode stepped through the real runner on a real local resource, without a
model call.

``next_decision`` returns the request the episode's own ``decide`` builds (the prompt the model would see);
``selected_action`` (what the episode's ``action`` does with an answer, given the wait range of its settings) turns
an answer into the action; ``run_unit`` runs it as a real, journaled, receipted unit. The launch starts a real
detached job through the library's execution point for local resources; the wait runs the library's wait runner."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, Rejected, RunJournal, link, resume

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, violations)

from .. import task
from .local_world import ANSWER, EPISODE, PATH, PROGRAM, SETTINGS, collaborators, entry, later_fetch, world

# A wait is long beside the units before it, and the completion controller's forecast falls with the measured
# progress time: at cost 0.5 it stops the Episode right after a one-second wait (seen in runs/fixres_9). The test
# that steps through a wait gives the controller a lower cost.
PATIENT = {**SETTINGS, 'cost': 0.05}
OLD_RUNNER_TEXT = ('exec_', 'shell', 'bash', 'ssh', 'receipt ledger', 'iterator', 'alpha', 'status_code',
                   'uncertainty_code', 'typed form', 'workdir', 'coordinator')


def commissioned(tmp_path, settings=SETTINGS):
    store, services, records = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry([EPISODE()])
    linked = link(registry, PATH, entry(records), run_id='launch', journal=journal,
                  collaborators=collaborators(store, tmp_path, services, {PATH: settings}))
    return store, services, journal, registry, records, linked


def routed(linked, selection):
    """The action the episode makes of an answer, on the Episode as it stands."""
    return task.selected_action({'selection': selection}, EPISODE.internal_summary(linked.view),
                                SETTINGS['wait_seconds'])


def offered(request):
    return [branch['properties']['action']['enum'][0]
            for branch in request.output_schema['properties']['selection']['anyOf']]


def test_the_request_says_what_the_episode_is_for_shows_the_work_once_and_offers_its_actions(tmp_path):
    store, _, _, _, records, linked = commissioned(tmp_path)
    request = asyncio.run(linked.next_decision())
    text = json.dumps({'instructions': request.instructions, 'context': request.context}, sort_keys=True)
    whole = json.dumps({'role': request.role, 'instructions': request.instructions, 'context': request.context,
                        'output_schema': request.output_schema}, indent=1)
    print('REQUEST', whole)
    print('REQUEST_CHARACTERS', len(whole))
    assert offered(request) == ['inspect_resource', 'launch_work']
    assert violations(request.output_schema) == []
    admitted_by_provider(request, tmp_path / 'provider')
    for word in ('PURPOSE', 'ASSIGNED WORK', 'ACTIONS', 'CREDIT', 'inspect_resource', 'launch_work',
                 'check_handoff', 'wait'):
        assert word in request.instructions
    assert [word for word in (*OLD_RUNNER_TEXT, 'reason', 'commit') if word in text] == []
    assert text.count(records['work_ref']) == 1 and PROGRAM.splitlines()[0] not in text and len(text) < 4000
    assert [item['earned'] for item in request.context['credit']] == [False, False]
    store.close()


def test_inspect_launch_wait_and_check_earn_the_handoff_and_the_controller_stops_at_the_target(tmp_path):
    store, services, journal, registry, records, linked = commissioned(tmp_path, PATIENT)
    asyncio.run(linked.next_decision())
    inspected = asyncio.run(linked.run_unit(routed(linked, {'action': 'inspect_resource'})))
    assert inspected['outcome']['resource']['kind'] == 'local' and inspected['produced'] == []
    assert linked.view.controller_state.current_credit == 0.0 and linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert request.context['resource']['description'] == inspected['outcome']['resource']
    launched = asyncio.run(linked.run_unit(routed(linked, {'action': 'launch_work'})))
    outcome = launched['outcome']
    assert launched['arguments'] == {'resource_id': 'local', 'work_ref': records['work_ref']}
    assert outcome['status'] == 'completed' and outcome['kind'] == 'local' and outcome['adopted'] is False
    assert linked.view.records.receipt(outcome['handoff_ref'])['how'] == 'produced'
    assert linked.view.controller_state.current_credit == 4.0 and linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert offered(request) == ['inspect_resource', 'check_handoff', 'wait']
    branches = request.output_schema['properties']['selection']['anyOf']
    assert branches[1]['properties']['handoff_ref']['enum'] == [outcome['handoff_ref']]
    assert branches[2]['properties']['seconds'] == {'type': 'number', 'minimum': 1, 'maximum': 60}
    assert violations(request.output_schema) == []
    assert [item['earned'] for item in request.context['credit']] == [True, False]
    with pytest.raises(Rejected):
        routed(linked, {'action': 'launch_work'})
    for seconds in (0.5, 61, '5'):
        with pytest.raises(Rejected):
            routed(linked, {'action': 'wait', 'seconds': seconds})
    waited = asyncio.run(linked.run_unit(routed(linked, {'action': 'wait', 'seconds': 1})))
    assert waited['arguments'] == {'handoff_ref': outcome['handoff_ref'], 'seconds': 1}
    assert waited['outcome']['status'] == 'completed' and waited['outcome']['waited_seconds'] == 1
    assert waited['outcome']['state'] in ('queued', 'running', 'finished')
    assert linked.view.records.receipt(waited['outcome']['check_ref'])['how'] == 'produced'
    assert linked.view.controller_state.current_credit == 4.0 and linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert request.context['launched_jobs'][0]['state'] == waited['outcome']['state']
    assert [item['earned'] for item in request.context['credit']] == [True, False]
    checked = asyncio.run(linked.run_unit(routed(linked, {'action': 'check_handoff',
                                                          'handoff_ref': outcome['handoff_ref']})))
    assert checked['outcome']['status'] == 'completed'
    assert checked['outcome']['state'] in ('queued', 'running', 'finished')
    assert linked.view.controller_state.current_credit == 7.0 and linked.view.controller_state.stop is True
    result = asyncio.run(linked.run())['result'].as_record()
    assert EPISODE.return_form.admit(result, 'return') == result
    assert result == {'credit': 7.0, 'finding': {'job_state': checked['outcome']['state'],
                                                 'result_available': checked['outcome']['result_available']},
                      'handoff_refs': [outcome['handoff_ref']], 'check_refs': [checked['outcome']['check_ref']]}
    assert journal.run_state('launch')[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes('launch')
    units = journal.units('launch', episode['path'])
    assert later_fetch(store, tmp_path, services, journal, outcome['handoff_ref'], 'result.txt') == ANSWER
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id='launch', journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, {PATH: PATIENT})).run())
    assert resumed['result'].as_record() == result and journal.units('launch', episode['path']) == units
    assert journal.model_calls('launch', episode['path']) == []
    assert len(list((tmp_path / 'jobs').iterdir())) == 1
    store.close()


def test_readings_alone_earn_nothing_and_the_controller_stops_an_episode_that_never_launches(tmp_path):
    store, _, journal, _, _, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    units = 0
    while not linked.view.controller_state.stop:
        asyncio.run(linked.run_unit(routed(linked, {'action': 'inspect_resource'})))
        units += 1
        assert linked.view.controller_state.current_credit == 0.0
    print('UNITS_UNTIL_THE_CONTROLLER_STOPPED', units)
    result = asyncio.run(linked.run())['result'].as_record()
    assert result == {'credit': 0.0, 'finding': {'job_state': 'not_launched', 'result_available': False},
                      'handoff_refs': [], 'check_refs': []}
    assert not (tmp_path / 'jobs').exists() or not list((tmp_path / 'jobs').iterdir())
    store.close()


def test_an_answer_outside_the_offered_actions_is_rejected(tmp_path):
    store, _, _, _, _, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    for selection in ({'action': 'run_command', 'cmd': 'true'}, {'action': 'launch_work', 'command': ['true']},
                      {'action': 'check_handoff', 'handoff_ref': 'row_not_held'}, {'action': 'wait', 'seconds': 5},
                      {}):
        with pytest.raises(Rejected):
            routed(linked, selection)
    store.close()
