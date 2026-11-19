"""The three A104 local job executions linked through the generic runner over real collaborators.

Real pieces only: the bindings' own ``TerminalExecution`` over a local resource configuration, the
repository's launch instruction library frozen for the run, the run's one ``Store``, a real
``RunJournal`` and the standard ``ModelProvider`` built from a Codex app-server configuration. No unit
is run, so the model is never called and no command executes: the test reads the linked Episode's
practical state, its admission of an exec_command selection and its completion controller.
"""
import pytest

from episode_runtime import BindingRegistry, RunJournal, grain_name_for, link

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.evolutionary_history_evidence.local_job_runtime import (LocalJobExecutionError,
                                                                                         LocalJobSource)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_bindings import EPISODES
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.execution_job_submission.\
    local_job_execution.runtime import construct

# The A104 table's three launch_local episodes and their commissioning parents.
LOCAL = tuple((path, parent) for path, role, parent in EPISODES if role == 'launch_local')
PATHS = tuple(path for path, _ in LOCAL)
ROLES_BY_GRAIN = {grain_name_for(path): role for path, role, _ in EPISODES}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}


def bindings(tmp_path):
    workspace = tmp_path / 'resource'
    workspace.mkdir(exist_ok=True)
    launch = tmp_path / 'launch'
    if not launch.exists():
        LaunchInstructions.freeze(launch, source=LIBRARY_ROOT / 'evolutionary_history_evidence')
    operands = {'resource': {'kind': 'local', 'workspace': str(workspace),
                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                'coordinator_workspace': tmp_path / 'coordinator', 'state_directory': tmp_path / 'practical',
                'launch_instruction_directory': launch, 'continuation': CONTINUATION}
    (tmp_path / 'coordinator').mkdir(exist_ok=True)
    return [construct(operands, path, 'launch_local', parent, {}, ROLES_BY_GRAIN) for path, parent in LOCAL]


def practical_assignment(tmp_path, **changes):
    job = str(tmp_path / 'resource' / 'job')
    value = {'version': 'practical_assignment_v1', 'assignment_id': 'local-job-1', 'resource_kind': 'local',
             'resource_id': 'local', 'workspace': job, 'endpoint': 'completed_job_outputs',
             'requested_job': {'argv': ['sh', '-c', 'echo done > out.txt'], 'environment': {}},
             'progress_requirements': [
                 {'key': 'outputs', 'credit': 2.0,
                  'predicate': {'kind': 'requested_job_outputs', 'output_paths': [job + '/out.txt']}},
                 {'key': 'directory', 'credit': 1.0,
                  'predicate': {'kind': 'path_exists', 'path': job, 'object_type': 'directory'}}],
             'completion_keys': ['outputs', 'directory'],
             'initial_context': {'revision': 0, 'cwd': job, 'environment': {}},
             'inventory_snapshot': {}, 'constraints': {}}
    return {**value, **changes}


def subject_scope(store):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    return store.validate_scope({'subject_refs': [target]})


def linked(tmp_path, store, path, assignment, run_id, scope=None):
    registry = BindingRegistry(bindings(tmp_path))
    provider = ModelProvider(MODEL_CONFIG, tmp_path / ('model_calls_' + run_id), tmp_path)
    scope = subject_scope(store) if scope is None else scope
    collaborators = {'store': store, 'model_provider': provider}
    run = link(registry, path, {'objective': 'Run the frozen local job',
                                'assignment': {'scope': scope, 'assignment': assignment}}, run_id=run_id,
               journal=RunJournal(tmp_path / (run_id + '.sqlite')), collaborators=collaborators)
    return registry.binding(path), run, collaborators


def test_local_job_bindings_register_with_their_own_runtime(tmp_path):
    registry = BindingRegistry(bindings(tmp_path))
    assert set(registry.paths) == set(PATHS)
    for path in PATHS:
        binding = registry.binding(path)
        assert binding.required_collaborators == ('model_provider', 'store')
        assert set(binding.assignment_form.fields) == {'scope', 'assignment'}
        assert binding.terminal.configuration['kind'] == 'local'


@pytest.mark.parametrize('path', PATHS)
def test_linked_local_job_opens_its_practical_state_and_completion_controller(tmp_path, path):
    with Store(tmp_path / 'state') as store:
        binding, run, collaborators = linked(tmp_path, store, path, practical_assignment(tmp_path), 'local_job')
        source = run.episode.source
        assert type(source) is LocalJobSource
        assert source.credit() == 0 and source.target == 3.0
        assert source.state.completion_proof() is None and source.state.receipts() == []
        controller = binding.build_controller(source._bound, collaborators)
        assert controller.target == 3.0 and controller.state().stop is False
        job = str(tmp_path / 'resource' / 'job')
        arguments = source.admit({'selection': {'tool': 'exec_command', 'cmd': 'sh run.sh', 'workdir': job,
                                                'target': 'resource', 'env': [{'name': 'LC_ALL', 'value': 'C'}]}})
        assert arguments == {'cmd': 'sh run.sh', 'workdir': job, 'target': 'resource', 'env': {'LC_ALL': 'C'}}
        with pytest.raises(LocalJobExecutionError, match='exec_command_environment_name_repeated'):
            source.admit({'selection': {'tool': 'exec_command', 'cmd': 'true', 'workdir': job, 'target': 'resource',
                                        'env': [{'name': 'A', 'value': '1'}, {'name': 'A', 'value': '2'}]}})
        with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
            source.admit({'selection': {'tool': 'exec_command', 'cmd': 'true', 'workdir': str(tmp_path),
                                        'target': 'resource', 'env': []}})
        assert not (tmp_path / 'model_calls_local_job' / 'call-00001').exists()


def test_local_job_refuses_an_assignment_it_cannot_complete(tmp_path):
    with Store(tmp_path / 'state') as store:
        scope = subject_scope(store)
        with pytest.raises(LocalJobExecutionError, match='local_job_execution_requires_local_resource_kind'):
            linked(tmp_path, store, PATHS[0], practical_assignment(tmp_path, resource_kind='hpc'), 'hpc_job', scope)
        unnamed = practical_assignment(tmp_path)
        del unnamed['resource_id']
        with pytest.raises(ValueError, match='practical_assignment_resource_id_required'):
            linked(tmp_path, store, PATHS[0], unnamed, 'unnamed_resource', scope)
        with pytest.raises(LocalJobExecutionError, match='local_job_credited_requirement_outside_completion_keys:'
                                                         'directory'):
            linked(tmp_path, store, PATHS[0], practical_assignment(tmp_path, completion_keys=['outputs']),
                   'partial_completion', scope)
