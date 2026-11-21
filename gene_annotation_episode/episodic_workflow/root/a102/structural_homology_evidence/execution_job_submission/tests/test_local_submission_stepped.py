"""The job submission episode over its local launch child, offline: no model is asked for the submission's own
decision (the test names the commission the model would choose) and the launch child, which asks its model, is not
run here. What is run by the real runner on a real Store, RunJournal and the real job services: the lookup of the
configured resources, and the decision request as the model would see it."""
import asyncio
import json

from episode_runtime import ChildCall, ModelRequest, RunJournal, ToolCall, link

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.tests.provider_schema_rules import (
    violations)

from ..episode import ExecutionJobSubmission
from .submission_world import HANDOFF_UNIT, PATH, POLICY, RESOURCE_ID, collaborators, entry, registry, world

RUN = 'a102-submission-offline'


def test_the_resources_are_looked_up_first_and_the_request_shows_the_assignment_once_and_one_action(tmp_path):
    held = world(tmp_path)
    linked = link(registry(), PATH, entry(held), run_id=RUN, journal=RunJournal(tmp_path / 'journal.sqlite3'),
                  collaborators=collaborators(held, 'model_calls'))
    first = asyncio.run(linked.next_decision())
    assert first == ToolCall('execution_capabilities', {})          # decided by code: no model
    looked = asyncio.run(linked.run_unit(first))['outcome']
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
        'permitted_resources': {RESOURCE_ID: 'local'}, 'resources': [resource],
        'launches_so_far': [],
        'credit': {'handoff_earns_per_resource': HANDOFF_UNIT, 'resources_with_a_handoff': [],
                   'earned_by_each_action_so_far': [0.0]}}
    assert json.dumps(request.context).count('a102-local-1') == 1     # the assignment is shown once
    assert violations(request.output_schema) == []
    commission = request.output_schema['properties']['action']
    assert commission['properties'] == {
        'name': {'type': 'string', 'enum': ['commission_launch']},
        'resource_id': {'type': 'string', 'enum': [RESOURCE_ID]}}
    for stated in ('commission_launch', 'only thing that earns credit',
                   'You do not write or run a command'):
        assert stated in request.instructions
    # The answer the model would give becomes the commission of the local launch child with the request alone.
    call = ExecutionJobSubmission.action({'action': {'name': 'commission_launch', 'resource_id': RESOURCE_ID}},
                                         summary, linked.view.records, None)
    assert call == ChildCall('launch_local', {'resource_id': RESOURCE_ID})
    message = ExecutionJobSubmission.msg_to_child(call.slot, call.arguments, summary)
    assert message.assignment == held['assignment']['requests'][RESOURCE_ID]
    assert message.selection == ('execution_handoff_refs', 'execution_completed')
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    held['store'].close()
