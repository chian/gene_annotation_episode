"""The A101 HPC job binding linked through the generic runner over the run's shared Store.

Real pieces only: the binding constructed by ``runtime.construct`` with its own ``HpcJobTools`` over a
``Store``, the repository's frozen launch instruction library, a real ``RunJournal`` and the standard
``ModelProvider`` built from a Codex app-server configuration. No unit runs, so neither the model nor the
configured PBS transport is ever invoked.
"""
import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from yield_control import CompletionYieldController

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.execution_job_submission.\
    hpc_job_execution.episode import HpcJobExecutionEpisode
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.execution_job_submission.\
    hpc_job_execution.runtime import HpcJobSource, construct

PATH = 'sequence_homology_evidence/execution_job_submission/hpc_job_execution'
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
            'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test', 'scheduler': {'kind': 'pbs'}}
JOB = {'version': 'practical_assignment_v1', 'assignment_id': 'job1', 'resource_kind': 'hpc',
       'resource_id': 'aurora', 'workspace': REMOTE + '/job1', 'endpoint': 'usable_handoff',
       'requested_job': {'argv': ['echo', 'hi'], 'environment': {}},
       'progress_requirements': [{'key': 'handoff', 'credit': 2.5, 'predicate': {'kind': 'requested_job_handoff'}}],
       'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': REMOTE + '/job1', 'environment': {}},
       'inventory_snapshot': {}, 'constraints': {}}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
CONTINUATION = {PATH: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}}


def _binding(tmp_path, store):
    return construct(HpcJobExecutionEpisode, store, {
        'resource': RESOURCE, 'directory': tmp_path / 'coordinator',
        'launch_instructions': LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT / 'sequence_homology_evidence')})


def _target(store):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    return target


def _link(tmp_path, target, binding, collaborators, job=JOB, run_id='a101_hpc_job_link'):
    return link(BindingRegistry([binding]), PATH, {'scope': {'subject_refs': [target]}, 'job': job},
                run_id=run_id, journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators=collaborators)


def test_linked_hpc_job_presents_its_job_and_refuses_commands_outside_the_workspace(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding = _binding(tmp_path, store)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        collaborators = {'store': store, 'model_provider': provider, 'continuation': CONTINUATION}
        source = _link(tmp_path, _target(store), binding, collaborators).episode.source
        assert type(source) is HpcJobSource
        controller = binding.build_controller(source._bound, collaborators)
        assert type(controller) is CompletionYieldController
        assert controller.target == 2.5 and controller.state().current_credit == 0 and not controller.state().stop

        class View:
            units_consumed = 0
            controller_state = controller.state()
        context = source.decision_context(View())
        assert context['execution_assignment']['assignment_id'] == 'job1'
        assert context['execution_resource']['account'] == 'BioReason-Aurora-Test'
        assert context['execution_completion'] is None and context['receipts'] == []
        with pytest.raises(ValueError, match='execution_workdir_outside_workspace'):
            source._tools.admit_arguments(source._job, {'cmd': ['ls'], 'workdir': '/tmp', 'target': 'resource',
                                                        'env': []})
        with pytest.raises(ValueError, match='exec_command_environment_name_repeats:A'):
            source._tools.admit_arguments(source._job, {'cmd': ['ls'], 'workdir': REMOTE + '/job1',
                                                        'target': 'resource',
                                                        'env': [{'name': 'A', 'value': '1'}, {'name': 'A', 'value': '2'}]})
        assert source._tools.admit_arguments(source._job, {
            'cmd': ['qstat'], 'workdir': REMOTE + '/job1', 'target': 'resource',
            'env': [{'name': 'A', 'value': '1'}]}) == {'cmd': ['qstat'], 'workdir': REMOTE + '/job1',
                                                        'env': {'A': '1'}, 'target': 'resource'}
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_hpc_job_requires_an_hpc_job_and_its_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        binding = _binding(tmp_path, store)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        target = _target(store)
        with pytest.raises(LinkError, match='collaborator_required:' + PATH + ':continuation'):
            _link(tmp_path, target, binding, {'store': store, 'model_provider': provider})
        with pytest.raises(ContractError, match='a101_hpc_job_execution_requires_an_hpc_job'):
            _link(tmp_path, target, binding, {'store': store, 'model_provider': provider,
                                              'continuation': CONTINUATION}, job={**JOB, 'resource_kind': 'local'},
                  run_id='a101_hpc_job_local_job')
