"""The A101 head linked through the generic runner: its own decision source over the shared Store.

Real pieces only: the A101 home factory composed by ``BindingRegistry.compose`` over the run's one
``Store`` and the repository's slotted process library, a real ``RunJournal``, and the standard
``ModelProvider`` constructed from a Codex app-server configuration. No unit is run, so the model
is never called: the test reads what the linked head would present and admit for its first decision.
"""
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from method_loop import Episode

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.home_factory import (
    a101_home_factory, a101_progress_provider)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import (
    A101SequenceCredit)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.runtime_source import (
    SequenceHomologyEvidenceSource)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.yield_estimator import HEAD_TASK
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary)

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
HEAD = 'sequence_homology_evidence'
RUN_ID = 'a101_head_link'
YIELD_BINDINGS = {HEAD_TASK: {'kind': 'bounded_quality', 'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05},
                              'credit_definition': A101SequenceCredit().as_record()}}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
MONITOR = {'information_unit': 1.0, 'yield_settings': {'kind': 'information_accumulation', 'cutoff': 0.25,
                                                       'uncertainty_alpha': 0.1}}
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
LOCAL_CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}
# The runtime continuation collaborator: the settings of each binding that reads its own by binding path.
CONTINUATION = {HEAD + '/' + home: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}} for home in (
    'execution_job_submission', 'execution_job_submission/hpc_job_execution', 'resource_work_submission',
    'resource_work_submission/hpc_resource_work_execution', 'execution_result_acquisition')}


def _registry(tmp_path, store):
    library = SequenceHomologyEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT / 'sequence_homology_evidence')
    (tmp_path / 'resource').mkdir()
    (tmp_path / 'coordinator').mkdir()

    def local(state):
        return {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                'coordinator_workspace': tmp_path / 'coordinator', 'state_directory': tmp_path / state,
                'launch_instruction_directory': tmp_path / 'launch', 'continuation': LOCAL_CONTINUATION}

    def hpc(directory):
        return {'resource': HPC_RESOURCE, 'directory': tmp_path / directory, 'launch_instructions': launch}
    api = {'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}}, 'continuation': LOCAL_CONTINUATION}
    return BindingRegistry.compose([a101_home_factory], {'store': store, 'a101': {
        'library': library, 'tools': {}, 'yield_bindings': YIELD_BINDINGS, 'monitor': MONITOR,
        'local_job_execution': local('local_job_practical'), 'hpc_job_execution': hpc('hpc_job'),
        'api_job_execution': api, 'local_resource_work_execution': local('local_resource_practical'),
        'hpc_resource_work_execution': hpc('hpc_resource'), 'api_resource_work_execution': api,
        'resource_result_acquisition': local('result_practical')}})


def _link(tmp_path, store, registry, collaborators):
    head = registry.binding(HEAD)
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    entry = {'scope': {'subject_refs': [target]}, 'thought_pattern': sorted(head.thought_patterns)[0],
             'tools': list(head.selectable_tools[:2])}
    return head, target, link(registry, HEAD, entry, run_id=RUN_ID, journal=RunJournal(
        tmp_path / 'journal.sqlite'), collaborators=collaborators)


def test_linked_head_builds_its_own_decision_source_over_the_run_store(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        head, target, run = _link(tmp_path, store, registry, {
            'store': store, 'model_provider': provider, 'continuation': CONTINUATION,
            'a101_progress_provider': a101_progress_provider(store, run_id=RUN_ID)})
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is SequenceHomologyEvidenceSource
        assert set(source.tool_catalog()) == set(head.selectable_tools[:2])
        options = source.action_schema()['properties']['selection']['anyOf']
        kinds = [option['properties']['kind']['const'] for option in options]
        assert kinds.count('reason') == 1 and kinds.count('tool') == 2
        assert sorted(option['properties']['slot']['const'] for option in options
                      if option['properties']['kind']['const'] == 'episode_child') == sorted(head.child_slots)
        assert source.credit_view()['credit'] == 0
        schema = source.action_schema()
        with pytest.raises(ValueError, match='a101_decision_response_must_be_exactly_selection'):
            source.admit({'choice': {}}, schema)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_head_cannot_link_without_the_model_provider(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        with pytest.raises(LinkError, match='collaborator_required:sequence_homology_evidence'):
            _link(tmp_path, store, registry, {'store': store})
