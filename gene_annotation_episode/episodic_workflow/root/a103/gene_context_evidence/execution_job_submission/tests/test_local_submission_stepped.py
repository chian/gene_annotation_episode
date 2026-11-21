"""The job submission episode over its local launch child, offline: no model is asked for the submission's own
decision (each test names the answer the model would give) and the launch child, which asks its model, is not run
here. What is run by the real runner on a real Store, RunJournal, the real job services and the axis's two frozen
instruction libraries: the lookup of the configured resources, the decision request as the model would see it, and
the library lookups (with the pin code writes at the end of a read of a launch-instruction section, and its way into
the commission)."""
import asyncio
import json

import pytest

from episode_runtime import ChildCall, ModelRequest, Rejected, RunJournal, ToolCall, link

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

from ..episode import ExecutionJobSubmission
from ..local_job_execution.episode import LocalJobExecution
from .submission_world import HANDOFF_UNIT, PATH, POLICY, RESOURCE_ID, collaborators, entry, registry, world

RUN = 'a103-submission-offline'
KNOWLEDGE = ['knowledge.search', 'knowledge.entry', 'knowledge.read']
LAUNCH = ['launch.instructions.search', 'launch.instructions.entry', 'launch.instructions.read']


def looked_up(held, tmp_path, cutoff=None):
    """The run linked and its first unit, the lookup of the configured resources, completed. ``cutoff`` is the
    cost of a unit in the submission's yield profile, for a test that runs several units that earn nothing."""
    if cutoff is not None:
        held['settings'][PATH]['task_yield_profiles']['launch:practical_local_handoff'] = {
            'cutoff': cutoff, 'parameters': {}}
    linked = link(registry(), PATH, entry(held), run_id=RUN, journal=RunJournal(tmp_path / 'journal.sqlite3'),
                  collaborators=collaborators(held, 'model_calls'))
    first = asyncio.run(linked.next_decision())
    assert first == ToolCall('execution_capabilities', {})          # decided by code: no model
    return linked, asyncio.run(linked.run_unit(first))['outcome']


def unit_of(linked, answer):
    """The unit the episode's own ``action`` makes of a model answer."""
    summary = ExecutionJobSubmission.internal_summary(linked.view)
    return ExecutionJobSubmission.action({'action': answer}, summary, linked.view.records, None)


def test_the_resources_are_looked_up_first_and_the_request_shows_the_assignment_once_and_the_actions(tmp_path):
    held = world(tmp_path)
    linked, looked = looked_up(held, tmp_path)
    resource, = looked['execution_resource_capabilities']
    assert (resource['resource_id'], resource['resource_kind'], resource['policy']) == (RESOURCE_ID, 'local', POLICY)
    assert 'tool_names' not in resource                              # a local resource offers no tool to a model
    request = asyncio.run(linked.next_decision())
    print('REQUEST', json.dumps({'instructions': request.instructions, 'context': request.context,
                                 'output_schema': request.output_schema}, indent=1))
    assert isinstance(request, ModelRequest)
    summary = ExecutionJobSubmission.internal_summary(linked.view)
    assert request.context == {
        'assignment': {name: held['assignment'][name] for name in ('version', 'requests', 'immutable_input_versions',
                                                                   'constraints')},
        'permitted_resources': {RESOURCE_ID: 'local'}, 'resources': [resource], 'received_bvbrc_values': [],
        'launches_so_far': [], 'lookups_so_far': [], 'pinned_launch_instructions': None,
        'credit': {'handoff_earns_per_resource': HANDOFF_UNIT, 'resources_with_a_handoff': [],
                   'earned_by_each_action_so_far': [0.0]}}
    assert json.dumps(request.context).count('a103-local-1') == 1     # the assignment is shown once
    # The answer is one defined action: the commission, or one operation of a library.
    assert violations(request.output_schema) == []
    actions = request.output_schema['properties']['action']['anyOf']
    names = [(one['properties']['name']['enum'][0], one['properties'].get('operation', {}).get('enum', [None])[0])
             for one in actions]
    assert names == [('commission_launch', None), *(('knowledge_lookup', operation) for operation in KNOWLEDGE),
                     *(('launch_instruction_lookup', operation) for operation in LAUNCH)]
    assert actions[0]['properties']['resource_id'] == {'type': 'string', 'enum': [RESOURCE_ID]}
    for stated in ('commission_launch', 'only thing that earns credit', 'You do not write or run a command',
                   'knowledge_lookup', 'launch_instruction_lookup', 'No lookup is mandatory'):
        assert stated in request.instructions
    assert 'exec_command' not in json.dumps([request.instructions, request.context, request.output_schema])
    # The answer the model would give becomes the commission of the local launch child with the request alone.
    call = unit_of(linked, {'name': 'commission_launch', 'resource_id': RESOURCE_ID})
    assert call == ChildCall('launch_local', {'resource_id': RESOURCE_ID})
    message = ExecutionJobSubmission.msg_to_child(call.slot, call.arguments, summary)
    assert message.assignment == held['assignment']['requests'][RESOURCE_ID]
    assert message.selection == ('execution_handoff_refs', 'execution_completed')
    # An answer that is rejected creates no unit, and the next request shows why.
    with pytest.raises(Rejected) as rejected:
        unit_of(linked, {'name': 'commission_launch', 'resource_id': 'nowhere'})
    again = ExecutionJobSubmission.decide(summary, rejected.value.feedback, None)
    assert again.context == {**request.context, 'feedback': rejected.value.feedback}
    assert rejected.value.feedback['status'] == 'invalid'
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    held['store'].close()


def test_the_library_lookups_run_and_a_section_that_was_read_is_pinned_and_travels_to_the_launch_child(tmp_path):
    held = world(tmp_path)
    linked, _ = looked_up(held, tmp_path, cutoff=0.001)
    # The tool-instruction library: the answer names the operation and its arguments; the tool reads the library.
    call = unit_of(linked, {'name': 'knowledge_lookup', 'operation': 'knowledge.search',
                            'arguments': {'query': '', 'offset': 0, 'limit': 3}})
    assert call == ToolCall('knowledge_lookup', {'operation': 'knowledge.search',
                                                 'arguments': {'query': '', 'offset': 0, 'limit': 3}})
    found = asyncio.run(linked.run_unit(call))['outcome']
    assert found['status'] == 'completed' and len(found['result']['entries']) == 3
    known = found['result']['entries'][0]['entry_id']
    indexed = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'knowledge_lookup', 'operation': 'knowledge.entry', 'arguments': {'entry_id': known}})))['outcome']
    manual = indexed['result']['entry']['sections'][0]
    lines = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'knowledge_lookup', 'operation': 'knowledge.read',
        'arguments': {'entry_id': known, 'section_id': manual['section_id'], 'offset': 0, 'limit': 2}})))['outcome']
    assert lines['status'] == 'completed' and 'pinned' not in lines   # only launch instructions are pinned
    # The launch-instruction library: search, the entry's sections, then the lines of one section.
    searched = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'launch_instruction_lookup', 'operation': 'launch.instructions.search',
        'arguments': {'query': '', 'offset': 0, 'limit': 5, 'resource_kind': None}})))['outcome']
    assert searched['status'] == 'completed' and 'pinned' not in searched
    entry_id = searched['result']['entries'][0]['entry_id']
    listed = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'launch_instruction_lookup', 'operation': 'launch.instructions.entry',
        'arguments': {'entry_id': entry_id}})))['outcome']
    section = listed['result']['entry']['sections'][0]
    read = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'launch_instruction_lookup', 'operation': 'launch.instructions.read',
        'arguments': {'entry_id': entry_id, 'section_id': section['section_id'], 'offset': 0, 'limit': 5}})))
    # The read is pinned by code at the end of its unit: the section's identity and digest in the frozen library.
    pin = {'entry_id': entry_id, 'section_id': section['section_id'], 'sha256': section['sha256']}
    assert read['outcome']['status'] == 'completed' and read['outcome']['pinned']['sections'] == [pin]
    assert read['produced'] == []                                     # a library is outside the Store
    # A read of a section the library does not have is a failed unit: nothing is pinned.
    missing = asyncio.run(linked.run_unit(unit_of(linked, {
        'name': 'launch_instruction_lookup', 'operation': 'launch.instructions.read',
        'arguments': {'entry_id': entry_id, 'section_id': 'no-such-section', 'offset': 0, 'limit': 5}})))['outcome']
    assert missing['status'] == 'failed' and 'pinned' not in missing
    summary = ExecutionJobSubmission.internal_summary(linked.view)
    assert summary['pinned_launch_instructions'] == read['outcome']['pinned']
    assert summary['pinned_launch_instructions'] == held['launch_library'].select([
        {'entry_id': entry_id, 'section_id': section['section_id']}])
    # The lookups earned nothing; the next decision shows what they returned and the pins.
    assert ExecutionJobSubmission.credit(summary, linked.view.records) == 0.0
    request = asyncio.run(linked.next_decision())
    assert [item['arguments']['operation'] for item in request.context['lookups_so_far']] == [
        'knowledge.search', 'knowledge.entry', 'knowledge.read', 'launch.instructions.search',
        'launch.instructions.entry', 'launch.instructions.read', 'launch.instructions.read']
    assert request.context['pinned_launch_instructions']['sections'] == [pin]
    assert request.context['credit']['earned_by_each_action_so_far'] == [0.0] * 8
    # The pins travel to the launch child with the request, and the child's form takes them.
    message = ExecutionJobSubmission.msg_to_child('launch_local', {'resource_id': RESOURCE_ID}, summary)
    assert message.assignment == {**held['assignment']['requests'][RESOURCE_ID],
                                  'launch_instructions': read['outcome']['pinned']}
    admitted = LocalJobExecution.assignment_form.admit(message.assignment, 'assignment')
    assert LocalJobExecution.read_from_parent(admitted, {})['assignment']['launch_instructions']['sections'] == [pin]
    # A section the commissioner pinned is kept and the read section is added to it.
    other = listed['result']['entry']['sections'][1]
    given = held['launch_library'].select([{'entry_id': entry_id, 'section_id': other['section_id']}])
    pinned_by_parent = {**summary, 'assignment': {**summary['assignment'], 'launch_instructions': given}}
    both = ExecutionJobSubmission.msg_to_child('launch_local', {'resource_id': RESOURCE_ID}, pinned_by_parent)
    assert both.assignment['launch_instructions']['sections'] == [*given['sections'], pin]
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    held['store'].close()
