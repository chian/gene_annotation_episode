"""The A101 ``api_job_execution`` episode, without a model: its class and forms, and a run through the real runner
(``link``, ``next_decision``, ``run_unit``, ``resume``) with a real Store, RunJournal and the job services, whose API
route is bound to a service of this test process that speaks the NCBI BLAST Common URL API. The model's place is
taken only where a decision is needed: the test names the unit the episode's own ``action`` admitted."""
import ast
import asyncio
import importlib
import json
from pathlib import Path

import pytest

from episode_runtime import DecisionContext, EpisodeBinding, ModelRequest, Rejected, ToolCall
from episode_runtime.job_access import JOB_LEDGER
from episode_runtime.services import DecisionServices
from method_loop import FormError
from yield_control import CompletionYieldController

from gene_annotation_episode.episodic_workflow.episode_support.jobs.tests.blast_url_api_server import (
    blast_url_api_service, route_configuration)

from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services

from . import api_world

PACKAGE = ('gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.'
           'execution_job_submission.api_job_execution')
FOLDER = Path(__file__).resolve().parent.parent
TEN_FILES = {'__init__.py', 'goal.py', 'task.py', 'credit.py', 'yield_estimator.py', 'episode.py',
             'messages/__init__.py', 'messages/read_from_parent.py', 'messages/internal_summary.py',
             'messages/final_to_parent.py'}
ROOT_PACKAGE = 'gene_annotation_episode.episodic_workflow.root'
ASSIGNMENT = {'resource_id': 'ncbi_blast', 'service': 'ncbi_blast', 'query_subject_refs': ['subject_a'],
              'input_refs': ['artifact_a'], 'fixed_request': {'program': 'blastp', 'database': 'swissprot'},
              'completion_target': 2.0}
REQUEST = {'program': 'blastp', 'database': 'swissprot', 'hitlist_size': 10}


@pytest.fixture(scope='module')
def episode_module():
    return importlib.import_module(PACKAGE + '.episode')


@pytest.fixture
def service():
    with blast_url_api_service() as running:
        yield running


@pytest.fixture
def world(service, tmp_path):
    made = api_world.world(tmp_path, route_configuration(service, tmp_path / 'api_jobs'))
    made['service'] = service
    yield made
    made['store'].close()


# -- the class and its forms -------------------------------------------------------------------------------------
def test_the_class_inherits_only_the_episode_base(episode_module):
    cls = episode_module.ApiJobExecution
    assert cls.__bases__ == (EpisodeBinding,)
    assert cls.binding_path == 'sequence_homology_evidence/execution_job_submission/api_job_execution'
    assert dict(cls.child_slots) == {} and tuple(cls.services) == ('job_access',)
    assert sorted(cls.tools) == ['launch_instructions', 'submit', 'tool_knowledge']


def test_the_folder_holds_exactly_the_ten_files():
    found = {str(path.relative_to(FOLDER)) for path in FOLDER.rglob('*.py')
             if '__pycache__' not in path.parts and 'tests' not in path.relative_to(FOLDER).parts}
    assert found == TEN_FILES
    assert not any(path.is_dir() and path.name not in ('messages', 'tests', '__pycache__')
                   for path in FOLDER.iterdir())


def test_no_episode_module_imports_another_episode_folder_or_names_a_retired_service_member():
    for relative in TEN_FILES:
        source = (FOLDER / relative).read_text()
        for node in ast.walk(ast.parse(source)):
            names = [node.module or ''] if isinstance(node, ast.ImportFrom) else \
                [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
            for name in names:
                assert not name.startswith(ROOT_PACKAGE), (relative, name)
                assert not (isinstance(node, ast.ImportFrom) and node.level > 1), (relative, name)
        for retired in ('bvbrc', 'NotImplementedError', 'BLOCKED', 'api_execute', 'wait_for_job'):
            assert retired not in source, (relative, retired)


def test_the_assignment_form_admits_one_assignment_and_refuses_a_missing_field(episode_module):
    cls = episode_module.ApiJobExecution
    cls.assignment_form.admit(ASSIGNMENT, 'assignment')
    with pytest.raises(FormError):
        cls.assignment_form.admit({name: value for name, value in ASSIGNMENT.items() if name != 'completion_target'},
                                  'assignment')
    with pytest.raises(FormError):
        cls.assignment_form.admit({**ASSIGNMENT, 'version': 'api_service_assignment_v1'}, 'assignment')
    assert cls.read_from_parent(ASSIGNMENT, {}) == {
        'resource_id': 'ncbi_blast', 'service': 'ncbi_blast', 'query_subject_ref': 'subject_a',
        'fixed_request': {'program': 'blastp', 'database': 'swissprot'}, 'launch_instructions': None,
        'completion_target': 2.0}


def test_the_return_form_is_controlled_data_and_nothing_a_model_wrote(episode_module):
    cls = episode_module.ApiJobExecution
    assert set(cls.return_form.fields) == {'credit', 'finding', 'execution_handoff_refs', 'execution_completed'}
    assert {name: spec.type for name, spec in cls.return_form.fields.items()} == {
        'credit': 'number', 'finding': 'record', 'execution_handoff_refs': 'record_refs',
        'execution_completed': 'boolean'}
    finding = cls.return_form.fields['finding'].form.fields
    assert {name: spec.type for name, spec in finding.items()} == {
        'submissions': 'integer', 'failed_submissions': 'integer', 'lookups': 'integer'}
    with pytest.raises(FormError):
        cls.return_form.select(('credit',))
    with pytest.raises(FormError):
        cls.return_form.select(('execution_result_refs',))
    summary = {'handoff_refs': ['row_a'], 'lookups': [{}],
               'submissions': [{'status': 'failed'}, {'status': 'completed'}]}
    completion = {'ended_by': 'yield_stop', 'units_consumed': 3, 'credit': 2.0}
    selection = ('execution_handoff_refs', 'execution_completed')
    result = cls.final_to_parent(summary, completion, selection)
    assert cls.return_form.select(selection).admit(result, 'result') == {
        'credit': 2.0, 'finding': {'submissions': 2, 'failed_submissions': 1, 'lookups': 1},
        'execution_handoff_refs': ['row_a'], 'execution_completed': True}
    assert cls.final_to_parent({**summary, 'handoff_refs': []}, completion, ()) == {
        'credit': 2.0, 'finding': {'submissions': 2, 'failed_submissions': 1, 'lookups': 1}}


def test_the_controller_is_completion_toward_the_commissioned_target(episode_module):
    cls = episode_module.ApiJobExecution
    parent_input = cls.read_from_parent(ASSIGNMENT, {})
    settings = {'task_yield_profiles': {'launch_api:api_ncbi_blast_blastp_swissprot_handoff':
                                        {'cutoff': 0.1, 'parameters': {}}}}
    controller = cls.yield_controller(0.0, settings, parent_input)
    assert isinstance(controller, CompletionYieldController) and controller.target == 2.0
    with pytest.raises(ValueError, match='execution_original_task_yield_profile_required:'
                                         'launch_api:api_ncbi_blast_blastp_swissprot_handoff'):
        cls.yield_controller(0.0, {'task_yield_profiles': {}}, parent_input)


# -- the decision: what the model is asked ---------------------------------------------------------------------
def test_the_request_says_what_the_episode_is_for_where_the_job_is_and_what_each_tool_does(world):
    run = api_world.linked(world, 'asked')
    request = asyncio.run(run.next_decision())
    api_world.show(request)
    assert isinstance(request, ModelRequest) and request.role == 'REASONING'
    text = request.instructions
    assert text.startswith('You are the launch step of one job on the public web service ncbi_blast. Build the '
                           'request of the assigned job, submit it once through the job service, and end at handoff.')
    for decision in ('Keep the original inputs, request, resource and parent constraints fixed',
                     'a missing reply does not establish that no job was created',
                     'The established handoff earns 1.0 and completes the commission',
                     'Do not wait for the job, ask its status or fetch anything here'):
        assert decision in text
    for retired in ('bvbrc', 'BV-BRC', 'ssh', 'ledger', 'iterator', 'report_update', 'wait is offered'):
        assert retired not in text
    context = request.context
    assert list(context) == ['assigned_job', 'service', 'tools', 'progress', 'credit', 'feedback']
    assert context['assigned_job'] == {
        'service': 'ncbi_blast', 'resource_id': 'ncbi_blast',
        'query': {'record': world['subject'], 'molecule': 'protein', 'length': len(api_world.QUERY),
                  'programs_that_take_it': ['blastp', 'tblastn']},
        'fixed': {'database': {'value': 'swissprot',
                               'parameter': "The name of one of the service's databases, as the service spells it"}},
        'open': ['hitlist_size', 'program']}
    assert context['service']['request_form']['required'] == ['database', 'hitlist_size', 'program']
    assert context['service']['seconds_between_contacts'] == 0.05
    assert [tool['name'] for tool in context['tools']] == ['submit', 'launch_instructions', 'tool_knowledge']
    assert list(context['tools'][1]['operations']) == [
        'launch.instructions.search', 'launch.instructions.entry', 'launch.instructions.read']
    assert context['progress'] == {'handoff_established': False, 'submissions': [], 'lookups': []}
    assert context['credit'] == {'now': 0.0, 'the_handoff_earns': 1.0} and context['feedback'] is None
    # The job is stated once, the sequence itself is not in the request, and no controller internals are shown.
    serialized = json.dumps(context)
    assert api_world.QUERY not in serialized and serialized.count('swissprot') == 1
    for internal in ('alpha', 'status_code', 'uncertainty', 'controller', 'time_accounting'):
        assert internal not in serialized
    schema = request.output_schema
    assert schema['required'] == ['action', 'request', 'lookup']
    assert schema['properties']['action']['enum'] == ['submit', 'launch_instructions', 'tool_knowledge']
    assert asyncio.run(run.next_decision()).context == context          # asked again: the same decision
    assert world['service'].requests == []                              # a decision sends nothing


def test_without_the_library_settings_only_the_submission_is_offered(service, tmp_path):
    made = api_world.world(tmp_path, route_configuration(service, tmp_path / 'api_jobs'), libraries=False)
    request = asyncio.run(api_world.linked(made, 'bare').next_decision())
    assert [tool['name'] for tool in request.context['tools']] == ['submit']
    assert request.output_schema['required'] == ['action', 'request'] and 'lookup null' not in request.instructions
    made['store'].close()


def decision(world, run, episode_module):
    """The summary, the held records and the decision context the episode's ``action`` is handed, with the run's
    real job service behind its read handle (a read is asked of the service each time: no journal position)."""
    cls = episode_module.ApiJobExecution
    services = DecisionServices({'job_access': world['collaborators']['services']['job_access']()},
                                lambda request, ask: ask())
    ctx = DecisionContext(settings=dict(world['collaborators']['continuation'][api_world.PATH]), services=services,
                          clock=None, run_id='r', episode_id='e', binding_path=api_world.PATH, key='k')
    return cls, cls.internal_summary(run.view), run.view.records, ctx


def test_action_admits_the_request_of_the_assigned_job_and_rejects_any_other(world, episode_module):
    run = api_world.linked(world, 'admitted')
    asyncio.run(run.next_decision())
    cls, summary, records, ctx = decision(world, run, episode_module)
    sequence_ref = world['entry']['assignment']['input_refs'][0]
    assert summary['query'] == {'subject_ref': world['subject'], 'sequence_ref': sequence_ref,
                                'molecule': 'protein', 'length': len(api_world.QUERY)}
    admitted = cls.action({'action': 'submit', 'request': REQUEST, 'lookup': None}, summary, records, ctx)
    assert admitted == ToolCall('submit', {'resource_id': 'ncbi_blast', 'request': REQUEST,
                                           'query_sequence_ref': sequence_ref})
    looked = cls.action({'action': 'tool_knowledge', 'request': None, 'lookup': {
        'operation': 'knowledge.search', 'arguments_json': '{"query": "blast", "offset": 0, "limit": 2}'}},
        summary, records, ctx)
    assert looked == ToolCall('tool_knowledge', {'operation': 'knowledge.search',
                                                 'arguments': {'query': 'blast', 'offset': 0, 'limit': 2}})
    rejected = {
        'request_changes_a_parameter_the_parent_fixed:database:assigned:"swissprot":given:"nr"':
            {'action': 'submit', 'request': {**REQUEST, 'database': 'nr'}, 'lookup': None},
        'program_does_not_take_the_assigned_query:blastn:query_is:protein':
            {'action': 'submit', 'request': {**REQUEST, 'program': 'blastn'}, 'lookup': None},
        'a_lookup_requires_the_lookup_member:tool_knowledge':
            {'action': 'tool_knowledge', 'request': None, 'lookup': None},
        'operation_is_not_of_the_selected_library:knowledge.search':
            {'action': 'launch_instructions', 'request': None,
             'lookup': {'operation': 'knowledge.search', 'arguments_json': '{}'}}}
    for detail, response in rejected.items():
        with pytest.raises(Rejected) as refusal:
            cls.action(response, summary, records, ctx)
        assert refusal.value.feedback == {'status': 'invalid', 'category': 'selection', 'detail': detail}
    for malformed in ({'action': 'submit', 'request': None, 'lookup': None},
                      {'action': 'submit', 'request': {**REQUEST, 'hitlist_size': 0}, 'lookup': None},
                      {'action': 'submit', 'request': {**REQUEST, 'query': 'MKT'}, 'lookup': None},
                      {'action': 'wait', 'request': None, 'lookup': None},
                      {'action': 'submit', 'request': REQUEST}):
        with pytest.raises(Rejected):
            cls.action(malformed, summary, records, ctx)
    assert world['service'].requests == []


# -- the units: a lookup, the submission, the handoff, the return, resume ---------------------------------------
def test_the_submission_goes_to_the_service_once_and_the_episode_ends_at_handoff(world, episode_module):
    cls = episode_module.ApiJobExecution
    run = api_world.linked(world, 'launched')
    asyncio.run(run.next_decision())
    looked = asyncio.run(run.run_unit(ToolCall('tool_knowledge', {
        'operation': 'knowledge.search', 'arguments': {'query': 'blast', 'offset': 0, 'limit': 2}})))
    assert looked['outcome']['status'] == 'completed' and looked['outcome']['result'] is not None
    summary = cls.internal_summary(run.view)
    assert cls.credit(summary, run.view.records) == 0.0 and run.view.controller_state.stop is False
    after_lookup = asyncio.run(run.next_decision())
    assert after_lookup.context['progress']['lookups'][0]['operation'] == 'knowledge.search'
    _cls, summary, records, ctx = decision(world, run, episode_module)
    call = cls.action({'action': 'submit', 'request': REQUEST, 'lookup': None}, summary, records, ctx)
    unit = asyncio.run(run.run_unit(call))
    outcome = unit['outcome']
    # The built request and the assigned query reached the service as one submission, with no credential.
    put, = world['service'].requests
    assert put['fields'] == {'CMD': 'Put', 'PROGRAM': 'blastp', 'DATABASE': 'swissprot', 'HITLIST_SIZE': '10',
                             'QUERY': '>query\n' + api_world.QUERY + '\n', 'FORMAT_TYPE': 'Text',
                             'tool': 'api-job-route-test'}
    assert put['authorization'] is None and put['cookie'] is None
    assert outcome['status'] == 'completed' and outcome['sent'] is True and outcome['failure'] is None
    handoff_ref, = outcome['handoff_refs']
    assert {handoff_ref, outcome['reply_ref']} <= set(unit['produced'])
    # The handoff row says where the job is; the Episode holds it as produced by the unit.
    summary = cls.internal_summary(run.view)
    row = run.view.records.table(JOB_LEDGER).get(handoff_ref)
    assert row['event'] == 'handoff' and row['detail']['kind'] == 'api' and row['detail']['resource_id'] == 'ncbi_blast'
    assert row['detail']['native']['remote_id'] == 'TESTRID0001'
    assert row['detail']['native']['request']['query_length'] == len(api_world.QUERY)
    assert run.view.records.receipt(handoff_ref)['how'] == 'produced'
    assert summary['submissions'] == [{'request': REQUEST, 'status': 'completed', 'failure_code': None,
                                       'sent': True, 'retry_after_seconds': None}]
    # The handoff is the commission: the credit is the target and the controller stopped the Episode.
    assert cls.credit(summary, run.view.records) == 1.0 and run.view.controller_state.stop is True
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    assert result == {'credit': 1.0, 'finding': {'submissions': 1, 'failed_submissions': 0, 'lookups': 1},
                      'execution_handoff_refs': [handoff_ref], 'execution_completed': True}
    assert world['journal'].run_state('launched')[1]['ended_by'] == 'yield_stop'
    # Resume replays the recorded units: the result is the same and nothing is sent to the service.
    again = asyncio.run(api_world.resumed(world, 'launched').run())
    assert again['result'].as_record() == result and len(world['service'].requests) == 1


def test_a_failed_submission_is_a_returned_outcome_that_earns_nothing(world, episode_module):
    cls = episode_module.ApiJobExecution
    sequence_ref = world['entry']['assignment']['input_refs'][0]
    call = ToolCall('submit', {'resource_id': 'ncbi_blast', 'request': REQUEST, 'query_sequence_ref': sequence_ref})
    # A refusing service: the failed submission is the unit's outcome, earns nothing, and the Episode goes on.
    world['service'].submit_status = 503
    run = api_world.linked(world, 'refused')
    refused = asyncio.run(run.run_unit(call))['outcome']
    assert (refused['status'], refused['failure_code'], refused['sent']) == ('failed', 'provider_http_503', True)
    assert refused['handoff_refs'] == [] and cls.credit(cls.internal_summary(run.view), run.view.records) == 0.0
    shown = asyncio.run(run.next_decision()).context['progress']
    assert shown == {'handoff_established': False, 'lookups': [], 'submissions': [{
        'request': REQUEST, 'status': 'failed', 'failure_code': 'provider_http_503', 'sent': True,
        'retry_after_seconds': None}]}
    # Too early for the service's spacing (here thirty seconds after the contact above): the request is not sent,
    # and the outcome says how long the service asks to be left alone.
    world['service'].submit_status = 200
    route = world['configuration']['api']['ncbi_blast']
    slow = {**world['configuration'], 'api': {'ncbi_blast': {**route, 'request_spacing_seconds': 30}}}
    spaced = {**world, 'collaborators': {**world['collaborators'], 'services': job_services(slow)}}
    early = asyncio.run(api_world.linked(spaced, 'early').run_unit(call))['outcome']
    assert (early['failure_code'], early['sent']) == ('provider_spacing_required', False)
    assert 0 < early['retry_after_seconds'] <= 30 and len(world['service'].requests) == 1
