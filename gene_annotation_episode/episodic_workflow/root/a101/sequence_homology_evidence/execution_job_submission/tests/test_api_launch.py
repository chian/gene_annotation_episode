"""The A101 launch episode on an API resource, without a model: through the real runner (``link``,
``next_decision``, ``run_unit``) with a real Store, RunJournal and the job services, whose API route is bound to a
service of this test process that speaks the NCBI BLAST Common URL API. The capabilities lookup reads the route;
the commission the episode builds for its API child is the one that child's own form admits."""
import asyncio

import pytest

from episode_runtime import ModelRequest, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.blast_url_api_server import (
    blast_url_api_service, route_configuration)

from ..api_job_execution.episode import ApiJobExecution
from ..api_job_execution.tests import api_world
from ..episode import ExecutionJobSubmission
from . import launch_world


@pytest.fixture
def world(tmp_path):
    with blast_url_api_service() as service:
        made = launch_world.world(tmp_path, route_configuration(service, tmp_path / 'api_jobs'))
        made['service'] = service
        yield made
        made['store'].close()


def test_the_capabilities_lookup_describes_the_api_resource_from_its_route_and_the_child_is_commissioned(world):
    run = launch_world.linked(world, 'launch')
    first = asyncio.run(run.next_decision())
    assert first == ToolCall('execution_capabilities', {})
    looked = asyncio.run(run.run_unit(first))['outcome']
    assert looked == {'execution_initial_information': {}, 'execution_resource_capabilities': [{
        'resource_id': 'ncbi_blast', 'resource_kind': 'api', 'availability': 'unknown',
        'observed_at': 'caller_configuration', 'provenance_refs': [],
        'inventory_snapshot': None, 'service': 'ncbi_blast', 'tool_names': ['submit'],
        'request_parameters': ['database', 'hitlist_size', 'program'],
        'api_configuration_facts': {'contact_configured': False, 'authentication': 'none',
                                    'request_spacing_seconds': 0.05, 'poll_spacing_seconds': 0.2}}]}
    request = asyncio.run(run.next_decision())
    api_world.show(request)
    assert isinstance(request, ModelRequest)
    assert 'bvbrc' not in str(request.context).lower()
    # The commission of the API child, built from the real summary: the child's own form admits it, and it is the
    # assignment the child's own world runs on.
    summary = ExecutionJobSubmission.internal_summary(run.view)
    message = ExecutionJobSubmission.msg_to_child('launch_api', {'resource_id': 'ncbi_blast'}, summary)
    assert ApiJobExecution.assignment_form.admit(message.assignment, 'assignment') == world['child_entry']['assignment']
    assert message.selection == ('execution_handoff_refs', 'execution_completed')
    ApiJobExecution.return_form.select(message.selection)
    assert world['service'].requests == []                    # nothing was sent: a lookup and two decisions
