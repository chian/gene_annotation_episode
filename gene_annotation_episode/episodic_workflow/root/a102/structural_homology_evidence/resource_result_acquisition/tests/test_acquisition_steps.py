"""The result acquisition episode stepped through the real runner on a real job, without a model call.

``next_decision`` returns the request the episode's own ``decide`` builds (the prompt the model would see);
``selected_action`` (what the episode's ``action`` does with an answer, given the wait range of its settings) turns
an answer into the action; ``run_unit`` runs it as a real, journaled, receipted unit through the run's real job
services. The job is a real detached local job the run's caller launched (``acquisition_world``)."""
import asyncio
import json
import time

import pytest

from episode_runtime import BindingRegistry, Rejected, RunJournal, link, resume

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, violations)

from .. import task
from .acquisition_world import (ANSWER, EPISODE, PATH, PROGRAM, SETTINGS, SLOW, collaborators, entry, launched_job,
                                world)

# A wait is long beside the units before it, and the completion controller's forecast falls with the measured
# progress time; the tests that step through a wait give the controller a lower cost.
PATIENT = {**SETTINGS, 'cost': 0.05}
OLD_RUNNER_TEXT = ('exec_', 'shell', 'bash', 'ssh', 'receipt ledger', 'iterator', 'alpha', 'status_code',
                   'uncertainty_code', 'typed form', 'resource.capabilities', 'job.fetch')


def commissioned(tmp_path, names, selection=(), *, program=PROGRAM, settings=SETTINGS):
    store, services = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    handoff_ref = launched_job(store, tmp_path, services, journal, program)
    registry = BindingRegistry([EPISODE()])
    linked = link(registry, PATH, entry(handoff_ref, names, selection), run_id='acquisition',
                  journal=journal, collaborators=collaborators(store, tmp_path, services, {PATH: settings}))
    return store, services, journal, registry, handoff_ref, linked


def routed(linked, selection):
    """The action the episode makes of an answer, on the Episode as it stands."""
    return task.selected_action({'selection': selection}, EPISODE.internal_summary(linked.view),
                                SETTINGS['wait_seconds'])


def test_the_request_says_what_the_episode_is_for_shows_the_assignment_once_and_offers_its_actions(tmp_path):
    store, _, _, _, handoff_ref, linked = commissioned(tmp_path, ['answer.txt'])
    request = asyncio.run(linked.next_decision())
    text = json.dumps({'instructions': request.instructions, 'context': request.context}, sort_keys=True)
    whole = json.dumps({'role': request.role, 'instructions': request.instructions, 'context': request.context,
                        'output_schema': request.output_schema}, indent=1)
    print('REQUEST', whole)
    print('REQUEST_CHARACTERS', len(whole))
    branches = request.output_schema['properties']['selection']['anyOf']
    assert [branch['properties']['action']['enum'][0] for branch in branches] == [
        'check_job', 'fetch_results', 'wait']
    assert branches[2]['properties']['seconds'] == {'type': 'number', 'minimum': 1, 'maximum': 60}
    assert violations(request.output_schema) == []
    admitted_by_provider(request, tmp_path / 'provider')
    for word in ('PURPOSE', 'ASSIGNED WORK', 'ACTIONS', 'CREDIT', 'check_job', 'fetch_results', 'wait'):
        assert word in request.instructions
    assert [word for word in (*OLD_RUNNER_TEXT, 'reason', 'commit') if word in text] == []
    assert text.count(handoff_ref) == 1 and text.count('answer.txt') == 1 and len(text) < 3500
    assert request.context['job']['state'] == 'not_checked' and request.context['credit'] == {
        'earned': 0, 'target': 1}
    store.close()


def test_a_check_then_a_fetch_acquire_the_file_and_the_controller_stops_at_the_target(tmp_path):
    store, services, journal, registry, handoff_ref, linked = commissioned(tmp_path, ['answer.txt'],
                                                                           ('check_refs',))
    asyncio.run(linked.next_decision())
    checked = asyncio.run(linked.run_unit(routed(linked, {'action': 'check_job'})))
    assert checked['tool'] == 'check_job' and checked['outcome']['status'] == 'completed'
    assert checked['outcome']['state'] == 'finished' and checked['outcome']['result_available'] is True
    assert linked.view.records.receipt(checked['outcome']['check_ref'])['how'] == 'produced'
    summary = EPISODE.internal_summary(linked.view)
    assert EPISODE.credit(summary, linked.view.records) == 0.0 and linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert request.context['job']['state'] == 'finished' and request.context['job']['result_available'] is True
    assert request.context['actions_so_far'] == [{'action': 'check_job', 'status': 'completed', 'failure': None}]
    fetched = asyncio.run(linked.run_unit(routed(linked, {'action': 'fetch_results'})))
    assert fetched['outcome']['status'] == 'completed' and fetched['outcome']['outcome'] == 'results_acquired'
    assert [item['name'] for item in fetched['outcome']['results']] == ['answer.txt']
    assert store.get_artifact(fetched['outcome']['result_refs'][0]) == ANSWER
    assert linked.view.controller_state.stop is True and linked.view.controller_state.current_credit == 1.0
    result = asyncio.run(linked.run())['result'].as_record()
    assert EPISODE.return_form.select(('check_refs',)).admit(result, 'return') == result
    assert result == {'credit': 1.0, 'finding': {'job_state': 'finished', 'fetch_outcome': 'results_acquired'},
                      'result_refs': fetched['outcome']['result_refs'],
                      'closure_refs': [fetched['outcome']['closure_ref']],
                      'check_refs': [checked['outcome']['check_ref']]}
    assert journal.run_state('acquisition')[1]['ended_by'] == 'yield_stop'
    (episode,) = journal.episodes('acquisition')
    units = journal.units('acquisition', episode['path'])
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry, run_id='acquisition', journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, {PATH: SETTINGS})).run())
    assert resumed['result'].as_record() == result and journal.units('acquisition', episode['path']) == units
    assert journal.model_calls('acquisition', episode['path']) == []
    store.close()


def test_a_fetch_of_a_job_that_has_not_ended_fails_and_a_wait_after_it_is_where_the_controller_stops(tmp_path):
    """The completion controller forecasts over the measured progress time: after a short unit that earned
    nothing, a wait that earns nothing is long enough for its forecast to fall to its cost, also at cost 0.05."""
    store, _, journal, _, _, linked = commissioned(tmp_path, ['answer.txt'], program=SLOW, settings=PATIENT)
    asyncio.run(linked.next_decision())
    early = asyncio.run(linked.run_unit(routed(linked, {'action': 'fetch_results'})))
    assert early['outcome']['status'] == 'failed' and early['produced'] == []
    assert early['outcome']['failure']['code'] == 'results_not_available'
    assert linked.view.controller_state.stop is False
    waited = asyncio.run(linked.run_unit(routed(linked, {'action': 'wait', 'seconds': 8})))
    assert waited['outcome']['state'] == 'finished' and linked.view.controller_state.stop is True
    result = asyncio.run(linked.run())['result'].as_record()
    assert result == {'credit': 0.0, 'finding': {'job_state': 'finished',
                                                 'fetch_outcome': 'results_not_available'},
                      'result_refs': [], 'closure_refs': []}
    assert journal.run_state('acquisition')[1]['ended_by'] == 'yield_stop'
    store.close()


def test_a_wait_on_a_running_job_then_a_fetch_acquire_the_file_and_resume_does_not_wait_again(tmp_path):
    store, services, journal, registry, handoff_ref, linked = commissioned(
        tmp_path, ['answer.txt'], program=SLOW, settings=PATIENT)
    asyncio.run(linked.next_decision())
    for seconds in (0, 61, '8'):
        with pytest.raises(Rejected):
            routed(linked, {'action': 'wait', 'seconds': seconds})
    call = routed(linked, {'action': 'wait', 'seconds': 8})
    assert (call.name, call.arguments) == ('wait', {'handoff_ref': handoff_ref, 'seconds': 8})
    waited = asyncio.run(linked.run_unit(call))
    assert waited['outcome']['status'] == 'completed' and waited['outcome']['waited_seconds'] == 8
    assert waited['outcome']['state'] == 'finished' and waited['outcome']['result_available'] is True
    assert linked.view.records.receipt(waited['outcome']['check_ref'])['how'] == 'produced'
    assert linked.view.controller_state.current_credit == 0.0
    print('STOPPED_AFTER_THE_WAIT', linked.view.controller_state.stop)
    assert linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert request.context['job']['state'] == 'finished'
    assert request.context['actions_so_far'] == [{'action': 'wait', 'status': 'completed', 'failure': None}]
    fetched = asyncio.run(linked.run_unit(routed(linked, {'action': 'fetch_results'})))
    assert store.get_artifact(fetched['outcome']['result_refs'][0]) == ANSWER
    assert linked.view.controller_state.stop is True and linked.view.controller_state.current_credit == 1.0
    result = asyncio.run(linked.run())['result'].as_record()
    assert result == {'credit': 1.0, 'finding': {'job_state': 'finished', 'fetch_outcome': 'results_acquired'},
                      'result_refs': fetched['outcome']['result_refs'],
                      'closure_refs': [fetched['outcome']['closure_ref']]}
    (episode,) = journal.episodes('acquisition')
    units = journal.units('acquisition', episode['path'])
    (tmp_path / 'resume').mkdir()
    started = time.monotonic()
    resumed = asyncio.run(resume(registry, run_id='acquisition', journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, {PATH: PATIENT})).run())
    assert time.monotonic() - started < 8                # the wait is replayed, not waited again
    assert resumed['result'].as_record() == result and journal.units('acquisition', episode['path']) == units
    store.close()


def test_a_fetch_of_a_file_the_job_did_not_write_is_a_failed_unit_that_earns_nothing(tmp_path):
    store, _, journal, _, _, linked = commissioned(tmp_path, ['absent.txt'])
    asyncio.run(linked.next_decision())
    units = 0
    while not linked.view.controller_state.stop:
        failed = asyncio.run(linked.run_unit(routed(linked, {'action': 'fetch_results'})))
        units += 1
        assert failed['outcome']['status'] == 'failed' and failed['produced'] == []
        assert failed['outcome']['failure']['code'] == 'result_not_in_catalog'
        assert linked.view.controller_state.current_credit == 0.0
    print('UNITS_UNTIL_THE_CONTROLLER_STOPPED', units)
    result = asyncio.run(linked.run())['result'].as_record()
    assert result == {'credit': 0.0, 'finding': {'job_state': 'not_checked',
                                                 'fetch_outcome': 'result_not_in_catalog'},
                      'result_refs': [], 'closure_refs': []}
    assert journal.run_state('acquisition')[1]['ended_by'] == 'yield_stop'
    store.close()


def test_an_answer_outside_the_actions_is_rejected(tmp_path):
    store, _, _, _, handoff_ref, linked = commissioned(tmp_path, ['answer.txt'])
    asyncio.run(linked.next_decision())
    for selection in ({'action': 'run_command'}, {'action': 'fetch_results', 'names': ['other.txt']},
                      {'action': 'wait'}, {'action': 'wait', 'seconds': 5, 'handoff_ref': handoff_ref}, {}):
        with pytest.raises(Rejected):
            routed(linked, selection)
    call = routed(linked, {'action': 'fetch_results'})
    assert (call.name, call.arguments) == ('fetch_results', {
        'resource_selection': {'resource_id': 'local'}, 'handoff_ref': handoff_ref, 'names': ['answer.txt']})
    store.close()
