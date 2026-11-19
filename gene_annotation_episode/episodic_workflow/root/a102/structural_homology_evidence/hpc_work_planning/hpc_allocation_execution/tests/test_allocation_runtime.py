"""A102 HPC allocation execution opens on its owner's frozen plan and binds the launch handoff it received.

Real binding, the run's shared Store, a real ``RunJournal``/``EpisodeRecorder``/``ProgressClock`` bound
episode, a real ``HPCLedger`` with a plan frozen by ``hpc_campaign.build_plan`` and a practical receipt
published to the Store by the real ``HpcJobTools.publish`` from a ``PracticalState`` that recorded a
scheduler-audit outcome in the worker's own shape. The configured transport is ``false``: no model,
network or HPC job is used, and every remote observation returns its real transport failure.
"""
import asyncio

import pytest

from episode_runtime import Field, RecordForm
from episode_runtime.journal import EpisodeRecorder, RunJournal
from episode_runtime.progress import ProgressClock
from episode_runtime.runner import BoundEpisode
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_job_submission.\
    hpc_job_execution.runtime import TOOL, HpcJobTools
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning import hpc_runtime
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.\
    hpc_allocation_execution import allocation_runtime
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.\
    hpc_allocation_execution.episode import HPCEpisode as AllocationExecution
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_campaign import build_plan
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import digest
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.tests.test_hpc_runtime import commission
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (assess_validations,
                                                                                            digest as job_digest)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.structural_homology_evidence.practical_execution_state import PracticalState
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.commissioned_report import CommissionedReportError
from method_loop import END_EXHAUSTED, EpisodeRecord, EpisodeRef
from yield_control import AccumulationYieldController

RUN = 'allocation-run'
OWNER = 'planning-owner-episode'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
RESOURCES = {'aurora': {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/contract-fixture', 'account': 'fixture',
                        'python_executable': '/not-an-executable-contract-fixture', 'ssh_argv': ['false'],
                        'scheduler': {'kind': 'pbs'}}}
JOB_ID = '4242.aurora-pbs-0001'
# This axis's HPC services collaborator, its allocation binding and its entry input.
SERVICES = 'a102_hpc'


def allocation_binding():
    return AllocationExecution()


def entry_input(scope, plan_ref):
    return {'scope': scope, 'role_assignment': {'owner_episode_id': OWNER, 'plan_ref': plan_ref}}


def frozen_plan(services, scope):
    """The owner's ledger with one plan frozen the way ``hpc_runtime._plan`` freezes it."""
    ledger = HPCLedger(services.directory / 'hpc' / digest([RUN, OWNER]), commission())
    ledger.put('owner', {'run_id': RUN, 'episode_id': OWNER, 'scope': scope}, identity='owner')
    ledger.put('model', prediction.prior_model(ledger.commission['model']), identity='reference_model')
    candidate = ledger.commission['candidates'][0]
    plan = build_plan(ledger.commission, candidate, services.resources['aurora'], ledger.read('owner'), 0)
    predicted = prediction.predict(ledger.read('reference_model'), hpc_runtime._features(candidate, {}))
    plan.update(model_ref='reference_model', queue_ref='queue:recorded', original_prediction=predicted,
                original_reference=predicted, operation_key=RUN + ':' + OWNER + ':0', prediction_episode_id=None)
    return ledger, ledger.put('plan', plan), plan


def bound_allocation(binding, journal, scope, plan_ref, report_form=None):
    commission_ = binding.entry_request(entry_input(scope, plan_ref), {}, parent_goal=None)
    path = ((binding.grain_name, 'allocation'),)
    journal.open_run(RUN, {'entry_path': binding.binding_path})
    journal.open_episode(RUN, path, binding.binding_path, commission_.as_record())
    recorder = EpisodeRecorder(journal, RUN, path)
    episode_id = EpisodeRef(RUN, path).episode_id
    return BoundEpisode(run_id=RUN, binding_path=binding.binding_path, path=path, key='allocation',
                        episode_id=episode_id, request=commission_.request,
                        assignment=binding.assignment_form.admit(commission_.assignment, 'assignment'),
                        recorder=recorder, progress=ProgressClock(recorder, run_id=RUN, episode_id=episode_id),
                        report_form=binding.return_form if report_form is None else report_form)


def published_launch_receipt(store, tmp_path, scope, job):
    """A launch Episode's practical receipt in the Store, its outcome recorded in the worker's scheduler-audit shape."""
    tools = HpcJobTools(store, resource=RESOURCES['aurora'], directory=tmp_path / 'launch')
    state = PracticalState(tmp_path / 'launch-state', RUN, 'launch-episode', job, initial_outcome={'facts': {}})
    key = RUN + ':launch-episode:0'
    workspace = job['workspace']
    arguments = {'cmd': ['/bin/bash', '-c', 'qsub runner.pbs'], 'workdir': workspace, 'env': {}, 'target': 'resource'}
    state.begin(key, TOOL, arguments)
    event = workspace + '/.episode-execution/run/scheduler/events/recorded/result.json'
    actual = {'job_id': JOB_ID, 'argv': ['/opt/pbs/bin/qsub', workspace + '/runner.pbs'], 'environment': {},
              'returncode': None, 'status': 'submitted', 'requested_job_sha256': job_digest(job['requested_job']),
              'assignment_sha256': job_digest(job), 'submission_event': event,
              'script': {'path': event[:-len('result.json')] + 'runner.pbs', 'original_path': workspace + '/runner.pbs',
                         'sha256': '0' * 64, 'bytes': 120}}
    outcome = {'facts': {'command': {'argv': arguments['cmd'], 'environment': {}, 'returncode': 0,
                                     'execution_id': workspace + '/intent.json'}, 'paths': [],
                         'requested_job': {'argv': actual['argv'], 'environment': {}, 'returncode': None,
                                           'execution_id': JOB_ID, 'requested_job_sha256': actual['requested_job_sha256'],
                                           'resource_kind': 'hpc', 'status': 'submitted', 'output_paths': [],
                                           'handoff': {'execution_id': JOB_ID, 'monitor_operation': 'exec_command',
                                                       'results_operation': 'exec_command'}}},
               'native_outcome': {'execution_command': {'returncode': 0}, 'scheduler_events': [], 'actual_job': actual}}
    after = state.context()
    receipt = state.finish(key, outcome, assess_validations(state.assignment, outcome, after, tool_name=TOOL),
                           context_after=after)
    return tools.publish(state, scope, receipt)


def test_allocation_execution_declares_its_collaborators_and_operations():
    assert allocation_binding().required_collaborators == ('model_provider', 'store', SERVICES)
    names = {entry['name'] for entry in allocation_runtime.catalog()}
    assert names == {'hpc.read', 'hpc.handoff', 'hpc.monitor', 'hpc.results', 'hpc.allocation.order'}


def test_allocation_binds_its_received_launch_handoff_and_returns_transport_failures(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        ledger, plan_ref, plan = frozen_plan(services, scope)
        binding = allocation_binding()
        bound = bound_allocation(binding, RunJournal(tmp_path / 'journal.sqlite'), scope, plan_ref)
        collaborators = {'store': store, SERVICES: services,
                         'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)}

        opened = binding.build_controller(bound, collaborators)
        assert isinstance(opened, AccumulationYieldController)
        assert opened.state().stop is False and opened.initial_credit == 0.
        source = allocation_runtime.AllocationSource(binding, bound, collaborators, {})
        assert source.credit()['credit'] == 0.
        operations = source._operations

        # Before any handoff, every allocation operation is a returned invalid outcome.
        early = asyncio.run(operations.execute('hpc.monitor', {'refresh_queue': False}, RUN + ':m:0', set()))
        assert early['status'] == 'invalid' and early['feedback']['code'] == 'original_handoff_not_attached'

        reference = published_launch_receipt(store, tmp_path, scope, plan['practical_assignment'])
        refused = asyncio.run(operations.execute('hpc.handoff', {'handoff_ref': reference}, RUN + ':h:0', set()))
        assert refused['status'] == 'invalid'
        assert refused['feedback']['code'] == 'handoff_not_received_by_this_episode'
        bound_handoff = asyncio.run(operations.execute('hpc.handoff', {'handoff_ref': reference}, RUN + ':h:1',
                                                       {reference}))
        assert bound_handoff['status'] == 'completed'
        assert bound_handoff['result'] == {'plan_id': plan['plan_id'], 'job_id': JOB_ID}
        assert bound_handoff['record_refs'] == [reference]
        handoff = ledger.read('handoff:' + plan['plan_id'])
        assert handoff['launch_episode_id'] == 'launch-episode' and handoff['actual_job']['job_id'] == JOB_ID

        # The configured transport fails for real; the failure is a returned outcome and earns nothing.
        observed = asyncio.run(operations.execute('hpc.monitor', {'refresh_queue': False}, RUN + ':m:1', set()))
        assert observed['status'] == 'invalid' and observed['feedback']['category'] == 'arguments_reference_or_transport'
        ordered = asyncio.run(operations.execute('hpc.allocation.order', {'unit_ids': ['unknown-unit']},
                                                 RUN + ':o:0', set()))
        assert ordered['status'] == 'invalid'
        assert ordered['feedback']['code'] == 'only_original_work_units_can_be_selected'
        assert source.credit()['credit'] == 0. and ledger.records('measured') == []


def test_allocation_fills_a_commissioned_report_form_from_its_recorded_facts(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        ledger, plan_ref, plan = frozen_plan(services, scope)
        binding = allocation_binding()
        form = RecordForm({**binding.return_form.fields,
                           'hpc_job_id': Field('text', 'The bound native job', required=False),
                           'hpc_closed': Field('boolean', 'Whether the allocation closed')})
        journal = RunJournal(tmp_path / 'journal.sqlite')
        bound = bound_allocation(binding, journal, scope, plan_ref, form)
        collaborators = {'store': store, SERVICES: services,
                         'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)}
        source = allocation_runtime.AllocationSource(binding, bound, collaborators, {})
        record = EpisodeRecord(scope_level=binding.grain_name, scope_key='allocation', units_consumed=0,
                               ended_by=END_EXHAUSTED, unit_records=(), controller_state=None, request=bound.request)

        # Before a handoff the job is unknown: the optional field stays absent.
        before = form.admit(source.build_result(record), 'report')
        assert 'hpc_job_id' not in before and before['hpc_closed'] is False
        assert before['credit'] == 0. and before['finding']['hpc_plan_ref'] == plan_ref

        reference = published_launch_receipt(store, tmp_path, scope, plan['practical_assignment'])
        asyncio.run(source._operations.execute('hpc.handoff', {'handoff_ref': reference}, RUN + ':h:0', {reference}))
        after = form.admit(source.build_result(record), 'report')
        assert after['hpc_job_id'] == JOB_ID == after['finding']['hpc_job_id']


@pytest.mark.parametrize('extra, code', [
    ({'hpc_unrecorded': Field('text', 'Not a recorded fact')}, 'commissioned_report_field_has_no_fact:hpc_unrecorded'),
    ({'hpc_job_id': Field('text', 'Required although it may be unknown')},
     'commissioned_report_field_may_be_unknown_must_be_optional:hpc_job_id'),
    ({'hpc_closed': Field('text', 'Mistyped')}, 'commissioned_report_field_type_differs_from_fact:hpc_closed'),
])
def test_allocation_refuses_a_commissioned_report_field_it_has_no_fact_for(tmp_path, extra, code):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        _, plan_ref, _ = frozen_plan(services, scope)
        binding = allocation_binding()
        form = RecordForm({**binding.return_form.fields, **extra})
        bound = bound_allocation(binding, RunJournal(tmp_path / 'journal.sqlite'), scope, plan_ref, form)
        collaborators = {'store': store, SERVICES: services,
                         'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)}
        with pytest.raises(CommissionedReportError, match=code):
            allocation_runtime.AllocationSource(binding, bound, collaborators, {})


def test_allocation_refuses_a_plan_its_owner_did_not_freeze(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        frozen_plan(services, scope)
        binding = allocation_binding()
        bound = bound_allocation(binding, RunJournal(tmp_path / 'journal.sqlite'), scope, 'reference_model')
        with pytest.raises(hpc_runtime.HPCRuntimeError, match='plan_ref_is_not_a_frozen_plan'):
            binding.build_controller(bound, {'store': store, SERVICES: services})
