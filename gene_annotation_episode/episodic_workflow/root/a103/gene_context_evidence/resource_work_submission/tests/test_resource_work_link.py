"""The A103 resource-work bindings linked through the generic runner over real collaborators.

Real pieces only: the five resource-work bindings built by their own constructors with their own route tools
(A103 ``TerminalExecution`` over a local resource, ``HpcJobTools`` and API services over the run's one
``Store``), the repository's launch instruction library frozen for the run, a real ``RunJournal`` and the
standard ``ModelProvider`` built from a Codex app-server configuration. No unit runs, so the model is never
called and no command, PBS transport or API request is issued.
"""
from importlib import import_module
import json

import pytest
from jsonschema import ValidationError

from episode_runtime import BindingRegistry, RunJournal, link
from yield_control import CompletionYieldController

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store

AXIS = 'a103'
ROOT = 'gene_annotation_episode.episodic_workflow.root.' + AXIS + '.'
PACKAGE = ROOT + 'gene_context_evidence.'
HEAD = 'gene_context_evidence'
SUBMISSION = HEAD + '/resource_work_submission'
LOCAL = SUBMISSION + '/local_resource_work_execution'
HPC = SUBMISSION + '/hpc_resource_work_execution'
API = SUBMISSION + '/api_resource_work_execution'
RESULTS = HEAD + '/resource_result_acquisition'
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
HPC_JOB = {'version': 'practical_assignment_v1', 'assignment_id': 'work1', 'resource_kind': 'hpc',
           'resource_id': 'aurora', 'workspace': REMOTE + '/work1', 'endpoint': 'usable_handoff',
           'requested_job': {'argv': ['echo', 'hi'], 'environment': {}},
           'progress_requirements': [{'key': 'handoff', 'credit': 2.5,
                                      'predicate': {'kind': 'requested_job_handoff'}}],
           'completion_keys': ['handoff'],
           'initial_context': {'revision': 0, 'cwd': REMOTE + '/work1', 'environment': {}},
           'inventory_snapshot': {}, 'constraints': {}}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
LOCAL_CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}
CONTINUATION = {SUBMISSION: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}},
                HPC: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}}


def _module(path):
    return import_module(PACKAGE + path.split('/', 1)[1].replace('/', '.') + '.episode')


def _class(path):
    """The one binding class its module declares for ``path``."""
    module = _module(path)
    found = [value for name, value in vars(module).items() if name.endswith('Episode') and isinstance(value, type)
             and getattr(value, 'binding_path', None) == path and value.__module__ == module.__name__]
    assert len(found) == 1, path
    return found[0]


def _tool_registry(tmp_path, store):
    return import_module('gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations').A103ToolRegistry(store, a103_work_directory=tmp_path / 'a103',
                                                               target_genomic_sources={})


def bindings(tmp_path, store):
    launch_module = import_module('gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions')
    launch_instructions = launch_module.LaunchInstructions
    launch = launch_instructions.freeze(tmp_path / 'launch', source=launch_module.LIBRARY_ROOT / 'gene_context_evidence')
    (tmp_path / 'resource').mkdir()
    (tmp_path / 'coordinator').mkdir()

    def local(state):
        return {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                'coordinator_workspace': tmp_path / 'coordinator', 'state_directory': tmp_path / state,
                'launch_instruction_directory': tmp_path / 'launch', 'continuation': LOCAL_CONTINUATION}
    construct = import_module(PACKAGE + 'execution_job_submission.hpc_job_execution.runtime').construct
    return [_class(SUBMISSION)(),
            _class(LOCAL)(**local('local_practical')),
            construct(_class(HPC), store, {'resource': HPC_RESOURCE, 'directory': tmp_path / 'hpc',
                                           'launch_instructions': launch}),
            _class(API)(tool_registry=_tool_registry(tmp_path, store),
                        configuration={'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}},
                                       'continuation': LOCAL_CONTINUATION}),
            _class(RESULTS)(**local('result_practical'))]


def practical_assignment(tmp_path, **changes):
    work = str(tmp_path / 'resource' / 'work')
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'local-work-1', 'resource_kind': 'local',
             'resource_id': 'local', 'workspace': work, 'endpoint': 'completed_job_outputs',
             'requested_job': {'argv': ['sh', '-c', 'echo done > out.txt'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'outputs', 'credit': 2.0,
                  'predicate': {'kind': 'requested_job_outputs', 'output_paths': [work + '/out.txt']}},
                 {'key': 'directory', 'credit': 1.0,
                  'predicate': {'kind': 'path_exists', 'path': work, 'object_type': 'directory'}}],
             'completion_keys': ['outputs', 'directory'],
             'initial_context': {'revision': 0, 'cwd': work, 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    return {**value, **changes}


def _scope(store):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    return store.validate_scope({'subject_refs': [target]})


def _link(tmp_path, store, registry, path, entry, run_id):
    collaborators = {'store': store, 'continuation': CONTINUATION,
                     'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / ('model_calls_' + run_id), tmp_path)}
    run = link(registry, path, entry, run_id=run_id, journal=RunJournal(tmp_path / (run_id + '.sqlite')),
               collaborators=collaborators)
    return run, collaborators


class _View:
    units_consumed = 0

    def __init__(self, controller):
        self.controller_state = controller.state()


def test_resource_work_bindings_are_built_with_their_own_route_tools(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry(bindings(tmp_path, store))
        assert set(registry.paths) == {SUBMISSION, LOCAL, HPC, API, RESULTS}
        forms = {path: set(registry.binding(path).assignment_form.fields) for path in registry.paths}
        assert forms == {SUBMISSION: {'scope', 'role_assignment'}, LOCAL: {'scope', 'role_assignment'},
                         RESULTS: {'scope', 'role_assignment'}, HPC: {'scope', 'role_assignment'},
                         API: {'scope', 'resource_id', 'request'}}
        assert registry.binding(API).assignment_form.fields['resource_id'].options == ('blast',)
        assert registry.binding(LOCAL).terminal.configuration['kind'] == 'local'
        assert registry.binding(RESULTS).terminal is not registry.binding(LOCAL).terminal
        assert registry.binding(HPC).tool_registry.store is store
        assert dict(registry.binding(SUBMISSION).child_slots) == {
            'api_resource_work_execution': API, 'local_resource_work_execution': LOCAL,
            'hpc_resource_work_execution': HPC}


def test_linked_submission_hands_each_request_to_a_resource_route(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry(bindings(tmp_path, store))
        requests = [{'request_id': 'r1', 'job': {'tool': 'phmmer', 'inputs': {}}},
                    {'request_id': 'r2', 'job': {'tool': 'phmmer', 'inputs': {'max': True}}}]
        run, collaborators = _link(tmp_path, store, registry, SUBMISSION,
                                   {'scope': _scope(store), 'role_assignment': {'requests': requests}}, 'submission')
        source = run.episode.source
        assert type(source).__name__ == 'JobSubmissionSource' and source.credit == 0
        controller = registry.binding(SUBMISSION).build_controller(source._bound, collaborators)
        assert type(controller) is CompletionYieldController
        assert controller.target == 2 and controller.state().stop is False
        schema = source.action_schema()
        assert sorted(option['properties']['slot']['enum'][0]
                      for option in schema['properties']['selection']['anyOf']) == sorted(
            ['api_resource_work_execution', 'hpc_resource_work_execution', 'local_resource_work_execution'])
        assert source.decision_context(_View(controller))['completion_target'] == 2
        selection = {'kind': 'episode_child', 'slot': 'local_resource_work_execution', 'request_id': 'r1',
                     'objective': 'Run the requested work locally',
                     'assignment': json.dumps({'role_assignment': practical_assignment(tmp_path)})}
        chosen, commission = source.admit({'selection': selection}, schema)
        assert chosen['request_id'] == 'r1'
        assert commission.assignment['role_assignment']['assignment_id'] == 'local-work-1'
        assert commission.request.message.as_record()['request'] == requests[0]
        with pytest.raises(ValidationError):
            source.admit({'selection': {**selection, 'request_id': 'r3'}}, schema)
        with pytest.raises(ValidationError):
            source.admit({'selection': {**selection, 'assignment': json.dumps({'unknown': HPC_JOB})}}, schema)
        assert not (tmp_path / 'model_calls_submission' / 'call-00001').exists()


@pytest.mark.parametrize('path', [LOCAL, RESULTS])
def test_linked_local_route_and_result_acquisition_open_their_practical_state(tmp_path, path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry(bindings(tmp_path, store))
        run, collaborators = _link(tmp_path, store, registry, path,
                                   {'scope': _scope(store), 'role_assignment': practical_assignment(tmp_path)},
                                   'local')
        source = run.episode.source
        assert type(source).__name__ == 'LocalJobSource'
        assert source.credit() == 0 and source.target == 3.0 and source.state.receipts() == []
        controller = registry.binding(path).build_controller(source._bound, collaborators)
        assert controller.target == 3.0 and controller.state().stop is False
        with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
            source.admit({'selection': {'tool': 'exec_command', 'cmd': 'true', 'workdir': str(tmp_path),
                                        'target': 'resource', 'env': []}})
        assert not (tmp_path / 'model_calls_local' / 'call-00001').exists()


def test_linked_hpc_route_executes_only_an_hpc_assignment(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry(bindings(tmp_path, store))
        scope = _scope(store)
        run, collaborators = _link(tmp_path, store, registry, HPC, {'scope': scope, 'role_assignment': HPC_JOB},
                                   'hpc')
        source = run.episode.source
        assert type(source).__name__ == 'HpcJobSource'
        controller = registry.binding(HPC).build_controller(source._bound, collaborators)
        assert controller.target == 2.5 and controller.state().current_credit == 0
        assert source.decision_context(_View(controller))['execution_resource']['account'] == 'BioReason-Aurora-Test'
        with pytest.raises(ContractError, match=AXIS + '_hpc_job_execution_requires_an_hpc_job'):
            _link(tmp_path, store, registry, HPC,
                  {'scope': scope, 'role_assignment': {**HPC_JOB, 'resource_kind': 'local'}}, 'hpc_local')


def test_linked_api_route_refuses_a_request_its_service_does_not_admit(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry(bindings(tmp_path, store))
        with pytest.raises(ContractError, match=AXIS + '_api_job_request_not_admitted'):
            _link(tmp_path, store, registry, API, {'scope': _scope(store), 'resource_id': 'blast', 'request': {}},
                  'api')
        assert not (tmp_path / 'model_calls_api' / 'call-00001').exists()
