"""The A104 head linked through the generic runner: every declared child slot is offered and commissioned.

Real pieces only: the A104 home factory composed by ``BindingRegistry.compose`` over the run's one
``Store`` and the repository's slotted process library, a real ``RunJournal``, and the standard
``ModelProvider`` constructed from a Codex app-server configuration. No unit is run, so the model is
never called: the test reads what the linked head would offer and admit for its first decision.
"""
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, FormError, RunJournal, link
from method_loop import Episode

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_runtime import (
    HPCServices)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_bindings import (
    EPISODES, a104_home, a104_progress_provider)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_source import (
    EVIDENCE_REFS, EvolutionaryHistoryEvidenceSource, ROLE, head_credit_projector)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import (
    EvolutionaryHistoryEvidenceLibrary)

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
RUN_ID = 'a104_head_link'
LOCAL_CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}
# The runtime continuation collaborator: the settings of each binding that reads its own by binding path
# (the submissions, HPC job executions and result acquisitions).
CONTINUATION = {path: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}
                for path, role, _ in EPISODES if role in ('launch', 'launch_hpc', 'results')}


def _linked(tmp_path, store):
    projector = head_credit_projector()
    library = EvolutionaryHistoryEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT / 'evolutionary_history_evidence')
    (tmp_path / 'resource').mkdir()
    (tmp_path / 'coordinator').mkdir()
    registry = BindingRegistry.compose([a104_home], {'store': store, 'a104': {
        'head': {'library': library, 'continuation': {
            'kind': projector.yield_method, 'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05},
            'credit_definition': projector.as_record()}},
        'tools': {}, 'monitor': {'information_unit': 1.0, 'yield_settings': {
            'kind': 'information_accumulation', 'cutoff': 0.25, 'uncertainty_alpha': 0.1}},
        'local_job_execution': {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                                'coordinator_workspace': tmp_path / 'coordinator',
                                'state_directory': tmp_path / 'practical', 'launch_instruction_directory': tmp_path / 'launch',
                                'continuation': LOCAL_CONTINUATION},
        'hpc_job_execution': {'resource': HPC_RESOURCE, 'directory': tmp_path / 'hpc', 'launch_instructions': launch},
        'api_job_execution': {'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}},
                              'continuation': LOCAL_CONTINUATION}}})
    head = registry.binding(ROLE)
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    entry = {'scope': {'subject_refs': [target]}, 'thought_pattern': sorted(head.thought_patterns)[0],
             'tools': list(head.selectable_tools[:1])}
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    run = link(registry, ROLE, entry, run_id=RUN_ID, journal=RunJournal(tmp_path / 'journal.sqlite'),
               collaborators={'store': store, 'model_provider': provider, 'a104_hpc': HPCServices(
                   resources={'aurora': HPC_RESOURCE}, directory=tmp_path / 'hpc_services',
                   shared_execution_memory=None), 'continuation': CONTINUATION,
                   'a104_progress_provider': a104_progress_provider(store, run_id=RUN_ID)})
    return head, target, run


def test_linked_head_offers_every_declared_child_with_its_own_form(tmp_path):
    with Store(tmp_path / 'state') as store:
        head, target, run = _linked(tmp_path, store)
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is EvolutionaryHistoryEvidenceSource
        schema = source.action_schema()
        offered = {option['properties']['role']['const']: option
                   for option in schema['properties']['selection']['anyOf']
                   if option['properties']['kind']['const'] == 'episode_child'}
        assert set(offered) == set(head.child_slots)
        for slot in set(head.child_slots) - {ROLE}:
            # A descendant's own declared assignment form: the model fills its ``assignment`` record.
            assert set(offered[slot]['properties']) == {'kind', 'role', 'objective', 'scope', 'assignment'}
            contract, form = source._descendant_reports[slot]
            assert EVIDENCE_REFS in form.fields and 'credit' in contract['measurements']
            assert set(source.child_options()[slot]) == {'binding_path', 'improves', 'unit', 'returns',
                                                         'report_information'}
        launch = {'kind': 'episode_child', 'role': 'launch', 'objective': 'Launch the selected search',
                  'scope': {'subject_refs': [target]}, 'assignment': {'assignment': {'work': 'selected search'}}}
        assert source.admit({'selection': launch}, schema) == launch
        with pytest.raises(FormError):
            source._descendant_assignment({**launch, 'assignment': {'assignment': 'not a record'}})
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()
