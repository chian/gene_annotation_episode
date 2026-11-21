"""The resource work submission episode stepped through the real runner, without a model call.

``next_decision`` returns the request the episode's own ``decide`` builds (the prompt the model would see);
``selected_action`` (what the episode's ``action`` does with an answer once it has read the resources) turns an
answer into the action; ``run_unit`` runs a tool action as a real, journaled, receipted unit through the run's real
resource adapters and frozen instruction libraries. The commission of the local child is built by the
episode's own ``msg_to_child`` and admitted by the child's own forms; the child itself is run by its model in the
model-run test. A handoff the commissioner passes back is a real job the caller launched."""
import asyncio
import json

import pytest

from episode_runtime import ChildCall, Rejected, RunJournal, ToolCall, link, resume

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    admitted_by_provider, violations)

from .. import task
from .submission_world import (ANSWER, EPISODE, LOCAL, PATH, PROGRAM, SETTINGS, caller_launch, collaborators, entry,
                               later_fetch, registry, world)

OLD_RUNNER_TEXT = ('exec_', 'shell', 'bash', 'ssh', 'receipt ledger', 'iterator', 'alpha', 'status_code',
                   'uncertainty_code', 'typed form', 'resource.capabilities', 'adapter_credit')
LOOKUP_OPERATIONS = {
    'knowledge_lookup': ['knowledge.search', 'knowledge.entry', 'knowledge.read'],
    'launch_instruction_lookup': ['launch.instructions.search', 'launch.instructions.entry',
                                  'launch.instructions.read', 'launch.instructions.select']}
ALWAYS = {name: {'operation': operations} for name, operations in LOOKUP_OPERATIONS.items()}


def commissioned(tmp_path, passed_back=False, **changes):
    store, services, records = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    if passed_back:
        changes['job_refs'] = [caller_launch(store, tmp_path, services, journal, records['limit_ref'])]
    linked = link(registry(), PATH, entry(records, **changes), run_id='submission', journal=journal,
                  collaborators=collaborators(store, tmp_path, services, SETTINGS))
    return store, services, journal, records, linked


def routed(linked, services, selection):
    """The action of an answer on the Episode as it stands, over the run's real resource adapters."""
    adapters = services['resource_adapter']()
    capabilities = task.capabilities_of(adapters.declared_capabilities(), adapters.adapter_capabilities())
    return task.selected_action({'selection': selection}, EPISODE.internal_summary(linked.view), capabilities,
                                adapters.bound_resource_ids())


def offered(request):
    return {branch['properties']['action']['enum'][0]: {
        name: schema['enum'] for name, schema in branch['properties'].items() if 'enum' in schema and name != 'action'}
        for branch in request.output_schema['properties']['selection']['anyOf']}


def shown(request):
    """The request as text, without the operations of the frozen libraries (their names and input schemas, which
    the lookups need)."""
    context = {name: value for name, value in request.context.items() if name != 'library_operations'}
    return json.dumps({'instructions': request.instructions, 'context': context}, sort_keys=True)


def test_the_request_says_what_the_episode_is_for_shows_the_work_once_and_offers_its_actions(tmp_path):
    store, _, _, records, linked = commissioned(tmp_path)
    request = asyncio.run(linked.next_decision())
    text = shown(request)
    whole = json.dumps({'role': request.role, 'instructions': request.instructions, 'context': request.context,
                        'output_schema': request.output_schema}, indent=1)
    print('REQUEST', whole)
    print('REQUEST_CHARACTERS', len(whole))
    assert offered(request) == {'inspect_resource': {'resource_id': ['local', 'cluster']},
                                'launch_work': {'resource_id': ['local']}, **ALWAYS}
    assert violations(request.output_schema) == []
    admitted_by_provider(request, tmp_path / 'provider')
    for word in ('PURPOSE', 'ASSIGNED WORK', 'ACTIONS', 'CREDIT', 'inspect_resource', 'launch_work',
                 'check_handoff', 'knowledge_lookup', 'launch_instruction_lookup'):
        assert word in request.instructions
    assert [word for word in (*OLD_RUNNER_TEXT, 'reason', 'commit') if word in text] == []
    assert text.count(records['work_ref']) == 1 and PROGRAM.splitlines()[0] not in text and len(text) < 6500
    assert request.context['resources'] == [
        {'resource_id': 'local', 'kind': 'local', 'availability': 'available', 'bound': True, 'launchable': True},
        {'resource_id': 'cluster', 'kind': 'hpc', 'availability': 'authentication_required', 'bound': False,
         'launchable': False}]
    assert [item['name'] for item in request.context['library_operations']] == [
        *LOOKUP_OPERATIONS['knowledge_lookup'], *LOOKUP_OPERATIONS['launch_instruction_lookup']]
    store.close()


def test_a_reading_of_an_unbound_resource_fails_with_its_code_and_the_launch_commission_fits_the_child(tmp_path):
    store, services, _, records, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    call = routed(linked, services, {'action': 'inspect_resource', 'resource_id': 'cluster'})
    read = asyncio.run(linked.run_unit(call))
    assert read['outcome'] == {'status': 'failed', 'resource_id': 'cluster', 'kind': 'hpc',
                               'availability': 'authentication_required', 'bound': False, 'facts': None,
                               'failure': {'code': 'resource_authentication_required', 'detail': None}}
    assert linked.view.controller_state.current_credit == 0.0 and linked.view.controller_state.stop is False
    request = asyncio.run(linked.next_decision())
    assert request.context['inspected'] == {'cluster': {'availability': 'authentication_required', 'bound': False,
                                                        'facts': None}}
    assert request.context['actions_so_far'] == [{'action': 'inspect_resource', 'status': 'failed',
                                                  'failure': 'resource_authentication_required'}]
    launch = routed(linked, services, {'action': 'launch_work', 'resource_id': 'local'})
    assert launch == ChildCall('launch_local', {'resource_id': 'local', 'kind': 'local'})
    message = EPISODE.msg_to_child(launch.slot, launch.arguments, EPISODE.internal_summary(linked.view))
    assert message.objective == 'launch_the_assigned_work_and_return_at_handoff' and message.message == {}
    assert LOCAL.assignment_form.admit(message.assignment, 'assignment') == {
        'version': 'resource_launch_assignment_v1', 'resource_id': 'local', 'work_refs': [records['work_ref']],
        'input_refs': [records['limit_ref']], 'handoff_unit': 3.5, 'check_unit': 3.5}
    assert {'credit', 'finding', 'handoff_refs', 'check_refs'} == set(
        LOCAL.return_form.select(message.selection).fields)
    for selection in ({'action': 'launch_work', 'resource_id': 'cluster'},
                      {'action': 'launch_work', 'resource_id': 'local', 'command': ['true']},
                      {'action': 'check_handoff', 'handoff_ref': 'row_not_held'}, {'action': 'run_command'},
                      {'action': 'wait', 'seconds': 5}):
        with pytest.raises(Rejected):
            routed(linked, services, selection)
    store.close()


def test_a_reading_of_the_bound_resource_returns_what_its_adapter_says(tmp_path):
    store, services, _, _, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    read = asyncio.run(linked.run_unit(routed(linked, services, {'action': 'inspect_resource',
                                                                 'resource_id': 'local'})))
    assert read['outcome']['status'] == 'completed' and read['outcome']['bound'] is True
    assert read['outcome']['facts']['resource']['kind'] == 'local' and read['produced'] == []
    store.close()


def test_a_lookup_reads_the_frozen_library_with_the_models_own_arguments_and_earns_nothing(tmp_path):
    store, services, _, _, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    arguments = {'query': '', 'offset': 0, 'limit': 3}
    call = routed(linked, services, {'action': 'knowledge_lookup', 'operation': 'knowledge.search',
                                     'arguments': json.dumps(arguments)})
    assert call == ToolCall('knowledge_lookup', {'operation': 'knowledge.search', 'arguments': arguments})
    found = asyncio.run(linked.run_unit(call))
    assert found['outcome']['status'] == 'completed' and found['outcome']['result'], found['outcome']
    assert found['produced'] == [] and linked.view.controller_state.current_credit == 0.0
    request = asyncio.run(linked.next_decision())
    assert request.context['lookup_results'] == [{
        'action': 'knowledge_lookup', 'operation': 'knowledge.search', 'arguments': arguments,
        'status': 'completed', 'result': found['outcome']['result'], 'feedback': None}]
    for wrong in ({'action': 'knowledge_lookup', 'operation': 'launch.instructions.search', 'arguments': '{}'},
                  {'action': 'launch_instruction_lookup', 'operation': 'launch.instructions.search',
                   'arguments': 'not json'},
                  {'action': 'launch_instruction_lookup', 'operation': 'launch.instructions.search',
                   'arguments': '[]'}):
        with pytest.raises(Rejected):
            routed(linked, services, wrong)
    store.close()


def test_a_launch_instruction_lookup_reads_its_own_frozen_library(tmp_path):
    store, services, _, _, linked = commissioned(tmp_path)
    asyncio.run(linked.next_decision())
    found = asyncio.run(linked.run_unit(routed(linked, services, {
        'action': 'launch_instruction_lookup', 'operation': 'launch.instructions.search',
        'arguments': json.dumps({'query': '', 'offset': 0, 'limit': 3})})))
    assert found['tool'] == 'launch_instruction_lookup' and found['outcome']['status'] == 'completed'
    refused = asyncio.run(linked.run_unit(routed(linked, services, {
        'action': 'launch_instruction_lookup', 'operation': 'launch.instructions.entry',
        'arguments': json.dumps({'unknown_argument': 1})})))
    assert refused['outcome']['status'] == 'failed' and refused['outcome']['feedback'] is not None
    store.close()


def test_a_handoff_passed_back_is_checked_through_its_adapter_and_nothing_is_launched_again(tmp_path):
    store, services, journal, _, linked = commissioned(tmp_path, passed_back=True)
    request = asyncio.run(linked.next_decision())
    (handoff_ref,) = offered(request)['check_handoff']['handoff_ref']
    assert set(offered(request)) == {'inspect_resource', 'check_handoff', *ALWAYS}
    assert linked.view.controller_state.current_credit == 3.5
    assert [item['earned'] for item in request.context['credit']] == [True, False]
    with pytest.raises(Rejected):
        routed(linked, services, {'action': 'launch_work', 'resource_id': 'local'})
    call = routed(linked, services, {'action': 'check_handoff', 'handoff_ref': handoff_ref})
    assert call == ToolCall('check_handoff', {'resource_selection': {'resource_id': 'local'},
                                              'handoff_ref': handoff_ref})
    checked = asyncio.run(linked.run_unit(call))
    assert checked['outcome']['status'] == 'completed'
    assert checked['outcome']['state'] in ('queued', 'running', 'finished')
    assert linked.view.records.receipt(checked['outcome']['check_ref'])['how'] == 'produced'
    assert linked.view.controller_state.current_credit == 7.0 and linked.view.controller_state.stop is True
    result = asyncio.run(linked.run())['result'].as_record()
    assert EPISODE.return_form.select(('check_refs',)).admit(result, 'return') == result
    assert result == {'credit': 7.0, 'finding': {'job_state': checked['outcome']['state'], 'route_kind': 'local'},
                      'handoff_refs': [handoff_ref], 'check_refs': [checked['outcome']['check_ref']]}
    (episode,) = journal.episodes('submission')
    units = journal.units('submission', episode['path'])
    assert later_fetch(store, tmp_path, services, journal, handoff_ref, 'result.txt') == ANSWER
    (tmp_path / 'resume').mkdir()
    resumed = asyncio.run(resume(registry(), run_id='submission', journal=journal, collaborators=collaborators(
        store, tmp_path / 'resume', services, SETTINGS)).run())
    assert resumed['result'].as_record() == result and journal.units('submission', episode['path']) == units
    assert journal.model_calls('submission', episode['path']) == []
    assert len(list((tmp_path / 'jobs').iterdir())) == 1
    store.close()


def test_with_no_launchable_resource_no_launch_is_offered_and_the_controller_stops_the_episode(tmp_path):
    store, services, journal, _, linked = commissioned(tmp_path, kinds=('api',))
    request = asyncio.run(linked.next_decision())
    assert offered(request) == {'inspect_resource': {'resource_id': ['local', 'cluster']}, **ALWAYS}
    assert [item['launchable'] for item in request.context['resources']] == [False, False]
    units = 0
    while not linked.view.controller_state.stop:
        asyncio.run(linked.run_unit(routed(linked, services, {'action': 'inspect_resource',
                                                              'resource_id': 'local'})))
        units += 1
    print('UNITS_UNTIL_THE_CONTROLLER_STOPPED', units)
    result = asyncio.run(linked.run())['result'].as_record()
    assert result == {'credit': 0.0, 'finding': {'job_state': 'not_launched', 'route_kind': 'none'},
                      'handoff_refs': [], 'check_refs': []}
    assert journal.run_state('submission')[1]['ended_by'] == 'yield_stop'
    store.close()
