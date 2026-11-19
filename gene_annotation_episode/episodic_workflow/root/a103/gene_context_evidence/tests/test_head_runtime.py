"""The A103 head on the generic runner, over real collaborators and test-written input data.

The A103 home factory builds every binding over the run's shared Store with A103's
own tool registry and the frozen A103 scientific library fixture. The head's
commission form offers the library's thought patterns and the registry's tools;
its continuation opens at A103's own measured-context credit over the records the
commission hands it (a measured neighbourhood published from test-written GenBank
files). No model is called: the head's model decision is not exercised here.
"""
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, FormError, LinkError, RunJournal, link
from episode_runtime.journal import EpisodeRecorder
from episode_runtime.progress import ProgressClock
from episode_runtime.runner import BoundEpisode
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import A103ContextCredit
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.publication import publish
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence import home
from gene_annotation_episode.episodic_workflow.episode_support.configuration.gene_context_evidence.process_options import GeneContextEvidenceLibrary
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.tests.test_a103_context import context_case, grade  # noqa: F401
from gene_annotation_episode.state import Store
from method_loop import EpisodeRef

LIBRARY_SOURCE = Path(__file__).resolve().parent / 'fixtures' / 'publication' / '2026-10-24-001'
DECLARATION = {'kind': 'bounded_quality', 'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.1},
               'credit_definition': A103ContextCredit().as_record()}
MONITOR = {'information_unit': 1.0, 'yield_settings': {'kind': 'information_accumulation', 'cutoff': 0.25,
                                                       'uncertainty_alpha': 0.1}}
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
LOCAL_CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}
RUN = 'a103-head-run'


def services(store, tmp_path, *, child_roles=('gene_context_evidence',)):
    library = GeneContextEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT / 'gene_context_evidence')
    (tmp_path / 'resource').mkdir(parents=True)
    (tmp_path / 'coordinator').mkdir(parents=True)

    def local(state):
        return {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                'coordinator_workspace': tmp_path / 'coordinator', 'state_directory': tmp_path / state,
                'launch_instruction_directory': tmp_path / 'launch', 'continuation': LOCAL_CONTINUATION}

    def hpc(directory):
        return {'resource': HPC_RESOURCE, 'directory': tmp_path / directory, 'launch_instructions': launch}
    api = {'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}}, 'continuation': LOCAL_CONTINUATION}
    return {'store': store, 'a103_tools': {'a103_work_directory': tmp_path / 'runs' / 'a103',
                                           'target_genomic_sources': {}},
            'a103_head': {'library': library, 'child_roles': child_roles,
                          'yield_bindings': {'A103:a103_context_credit': DECLARATION}},
            'a103_monitor': MONITOR,
            'a103_local_job_execution': local('local_job_practical'),
            'a103_hpc_job_execution': hpc('hpc_job'),
            'a103_api_job_execution': api,
            'a103_local_resource_work_execution': local('local_resource_practical'),
            'a103_hpc_resource_work_execution': hpc('hpc_resource'),
            'a103_api_resource_work_execution': api,
            'a103_resource_result_acquisition': local('result_practical')}


def bound_head(binding, journal, entry):
    commission = binding.entry_request(entry, {}, parent_goal=None)
    path = ((binding.grain_name, 'head'),)
    journal.open_run(RUN, {'entry_path': binding.binding_path})
    journal.open_episode(RUN, path, binding.binding_path, commission.as_record())
    recorder = EpisodeRecorder(journal, RUN, path)
    episode_id = EpisodeRef(RUN, path).episode_id
    return BoundEpisode(run_id=RUN, binding_path=binding.binding_path, path=path, key='head', episode_id=episode_id,
                        request=commission.request,
                        assignment=binding.assignment_form.admit(commission.assignment, 'assignment'),
                        recorder=recorder, progress=ProgressClock(recorder, run_id=RUN, episode_id=episode_id),
                        report_form=binding.return_form)


def test_home_factory_builds_all_34_bindings_and_the_head_offers_its_own_choices(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([home.factory], services(store, tmp_path))
        assert len(registry.paths) == 34
        head = registry.binding('gene_context_evidence')
        assert head.required_collaborators == ('store', 'model_provider')
        assert dict(head.child_slots) == {'gene_context_evidence': 'gene_context_evidence'}
        assert head.tool_registry.store is store
        choices = head.assignment_form.choices
        assert set(choices['thought_pattern']) == set(head.thought_patterns) and choices['thought_pattern']
        assert set(choices['tools']) == set(head.tool_registry.catalog(None))
        assert 'context.compare_neighborhoods' in choices['tools']
        with pytest.raises(LinkError, match='collaborator_required:gene_context_evidence:'):
            link(registry, 'gene_context_evidence', {}, run_id='unlinked', journal=RunJournal(tmp_path / 'j.sqlite'))


def test_head_declares_each_configured_child_home_and_refuses_an_undeclared_role(tmp_path):
    with Store(tmp_path / 'state') as store:
        head = home.factory(services(store, tmp_path, child_roles=('gene_context_evidence',
                                                                   'execution_job_submission')))[0]
        assert dict(head.child_slots) == {'gene_context_evidence': 'gene_context_evidence',
                                          'execution_job_submission': 'gene_context_evidence/execution_job_submission'}
    with Store(tmp_path / 'state2') as store:
        with pytest.raises(ContractError, match='a103_head_child_role_not_declared:launch'):
            home.factory(services(store, tmp_path / 'other', child_roles=('gene_context_evidence', 'launch')))


def test_head_commission_admits_parent_choices_and_rejects_unoffered_ones(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MDEAKG', molecule='protein')['subject_refs']
        head = home.factory(services(store, tmp_path))[0]
        pattern = sorted(head.thought_patterns)[0]
        entry = {'scope': {'subject_refs': [target]}, 'thought_pattern': pattern,
                 'tools': ['context.compare_neighborhoods'], 'evidence_refs': []}
        commission = head.entry_request(entry, {}, parent_goal=None)
        admitted = head.assignment_form.admit(commission.assignment, 'assignment')
        assert admitted['evidence_task'] == head.evidence_task and admitted['tools'] == ['context.compare_neighborhoods']
        with pytest.raises(FormError, match='not_an_offered_option:thought_pattern'):
            head.assignment_form.admit({**commission.assignment, 'thought_pattern': 'P_not_offered'}, 'assignment')
        with pytest.raises(FormError, match='repeats_an_option'):
            head.assignment_form.admit({**commission.assignment, 'tools': ['context.fusion', 'context.fusion']},
                                       'assignment')


def test_head_continuation_opens_at_its_own_measured_context_credit(context_case, tmp_path):
    store, target, known, a, ab, b, bb, na, sa, nb, sb, raw, definition = context_case
    measured = publish(store, raw, [target])
    known.add(measured)
    graded, _ = grade(store, target, known)
    head = home.factory(services(store, tmp_path))[0]
    entry = {'scope': {'subject_refs': [target]}, 'thought_pattern': sorted(head.thought_patterns)[0],
             'tools': ['context.compare_neighborhoods'], 'evidence_refs': sorted(known)}
    bound = bound_head(head, RunJournal(tmp_path / 'journal.sqlite'), entry)
    controller = head.build_controller(bound, {'store': store})
    assert graded['credit'] > 0
    assert controller.state().current_credit == graded['credit']
    assert type(controller.state().stop) is bool
