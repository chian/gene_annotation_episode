"""A102 HPC resource prediction links on the generic runner and fits over its owner's real ledger.

Real bindings, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called) and a real ``HPCLedger``. The commission is a test-written,
deliberately unlaunchable contract fixture: no model, network or HPC job is used.
"""
import asyncio

import pytest

from episode_runtime import (BindingRegistry, BoundEpisode, EpisodeRecorder, Field, LinkError, ProgressClock,
                             RecordForm, RunJournal, link)
from gene_annotation_episode.episodic_workflow.episode_support.tools.commissioned_report import CommissionedReportError
from method_loop import END_EXHAUSTED, EpisodeRecord, EpisodeRef
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning import hpc_runtime
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import digest
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from yield_control import AccumulationYieldController
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.hpc_resource_prediction.episode import \
    HPCEpisode as prediction_binding


def entry_input(scope, owner):
    return {'scope': scope, 'role_assignment': {'owner_episode_id': owner}}

PREDICTION = 'structural_homology_evidence/hpc_work_planning/hpc_resource_prediction'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
RESOURCES = {'aurora': {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/contract-fixture', 'account': 'fixture',
                        'python_executable': '/not-an-executable-contract-fixture', 'ssh_argv': ['false']}}


def commission():
    # Deliberately unlaunchable command: these inputs test contracts and mathematics, never an HPC job.
    model = {'features': [{'name': 'size', 'transform': 'log1p', 'scale': 1}],
             'priors': {name: {'median_seconds': 100, 'log_sigma': .5, 'coefficient_variance': .2}
                        for name in ('queue', 'setup', 'work', 'return')}, 'success_prior': [2, 1]}
    history = [{'id': 'measurement-' + str(i), 'observed_at': i, 'features': {'size': i},
                'metrics': {'work': {'seconds': 20 * i, 'censored': False}}, 'success': True,
                'provenance': ['mathematical_test_case']} for i in range(1, 9)]
    return {'objective': 'Exercise the contract without running a job', 'resource_id': 'aurora',
            'model': model, 'history': history, 'validation_ids': ['measurement-7', 'measurement-8'],
            'obligations': {'original-work': {'credit': 10., 'acceptance': [
                {'field': ['quality'], 'operator': 'ge', 'value': .9}]}},
            'candidates': [{'id': 'one-portfolio', 'queue': 'debug', 'nodes': 1, 'wall_seconds': 3600,
                            'features': {'size': 10}, 'units': [{
                                'unit_id': 'unit-1', 'obligation_id': 'original-work', 'effort': 1.,
                                'argv': ['/not-an-executable-contract-fixture'], 'environment': {}}]}],
            'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
                {'id': 'original-queue', 'metric': 'queue', 'phase': 'planned', 'weight': 1.,
                 'minimum_elapsed_seconds': 0}]},
            'preferences': {'elapsed_cost_per_second': .0001, 'node_hour_cost': .01},
            'limits': {'result_limit_bytes': 4096, 'queue_max_age_seconds': 600},
            'yield_bindings': {role: {'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05}}
                               for role in ('hpc', 'hpc_prediction', 'hpc_execution')}}


def test_prediction_requires_its_hpc_services(tmp_path):
    with Store(tmp_path / 'state') as store:
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        with pytest.raises(LinkError, match='collaborator_required:' + PREDICTION + ':a102_hpc'):
            link(BindingRegistry([prediction_binding()]), PREDICTION,
                 entry_input({'subject_refs': ['unadmitted']}, 'owner'), run_id='run',
                 journal=RunJournal(tmp_path / 'journal.sqlite'),
                 collaborators={'store': store, 'model_provider': provider})


def test_prediction_fits_over_its_owner_ledger_and_reads_unbounded_model_credit(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        # The ledger the planning owner writes for its commission (hpc_runtime.open_ledger).
        ledger = HPCLedger(services.directory / 'hpc' / digest(['run', 'owner-episode']), commission())
        ledger.put('owner', {'run_id': 'run', 'episode_id': 'owner-episode', 'scope': scope}, identity='owner')
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        run = link(BindingRegistry([prediction_binding()]), PREDICTION, entry_input(scope, 'owner-episode'),
                   run_id='run', journal=RunJournal(tmp_path / 'journal.sqlite'),
                   collaborators={'store': store, 'model_provider': provider, 'a102_hpc': services})
        source = run.episode.source
        names = [entry['name'] for entry in source.catalog]
        assert 'hpc.model.fit' in names and 'hpc.plan' not in names
        opened = run.episode.grain.controller(source._bound.path)
        assert isinstance(opened, AccumulationYieldController)
        assert opened.state().stop is False and opened.initial_credit == 0.
        episode_id = source._bound.episode_id
        outcome = asyncio.run(hpc_runtime.execute(
            'hpc_prediction', services, ledger, 'hpc.model.fit',
            {'training_ids': ['measurement-' + str(i) for i in range(1, 7)]}, 'run:fit:0', episode_id))
        assert outcome['status'] == 'completed'
        gain = outcome['result']['validation_quality'] - outcome['result']['reference_quality']
        view = hpc_runtime.credit_view('hpc_prediction', ledger, episode_id)
        assert view['credit'] == pytest.approx(0.01 * gain)
        assert ledger.credit_view()['components']['model'] == pytest.approx(0.01 * gain)
        invalid = asyncio.run(hpc_runtime.execute(
            'hpc_prediction', services, ledger, 'hpc.model.fit', {'training_ids': ['measurement-8']},
            'run:fit:1', episode_id))
        assert invalid['feedback']['code'] == 'training_ids_must_be_original_nonvalidation_cases'
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_prediction_fills_a_commissioned_report_form_from_its_recorded_finding(tmp_path):
    """C5: a parent's report form may add the role's recorded finding facts; a field with no fact raises."""
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc', shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        ledger = HPCLedger(services.directory / 'hpc' / digest(['run', 'owner-episode']), commission())
        ledger.put('owner', {'run_id': 'run', 'episode_id': 'owner-episode', 'scope': scope}, identity='owner')
        binding = prediction_binding()
        journal = RunJournal(tmp_path / 'journal.sqlite')
        journal.open_run('run', {'entry_path': binding.binding_path})
        collaborators = {'store': store, 'a102_hpc': services,
                         'model_provider': ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)}

        def bound(key, report_form):
            commission_ = binding.entry_request(entry_input(scope, 'owner-episode'), {}, parent_goal=None)
            path = ((binding.grain_name, key),)
            journal.open_episode('run', path, binding.binding_path, commission_.as_record())
            recorder = EpisodeRecorder(journal, 'run', path)
            episode_id = EpisodeRef('run', path).episode_id
            return BoundEpisode('run', binding.binding_path, path, key, episode_id, commission_.request,
                                binding.assignment_form.admit(commission_.assignment, 'assignment'), recorder,
                                ProgressClock(recorder, run_id='run', episode_id=episode_id), report_form)

        form = RecordForm({**binding.return_form.fields,
                           'hpc_model_ref': Field('text', 'The current model'),
                           'units': Field('integer', 'Units the Episode consumed')})
        filled = bound('filled', form)
        source = hpc_runtime.HPCSource(binding, 'hpc_prediction', filled, collaborators, {}, hpc_runtime.REPORT)
        record = EpisodeRecord(scope_level=binding.grain_name, scope_key='filled', units_consumed=0,
                               ended_by=END_EXHAUSTED, unit_records=(), controller_state=None, request=filled.request)
        report = form.admit(source.build_result(record), 'report')
        assert report['hpc_model_ref'] == 'reference_model' == report['finding']['hpc_model_ref']
        assert report['units'] == 0 and report['credit'] == 0.

        refused = bound('refused', RecordForm({**binding.return_form.fields,
                                               'hpc_job_id': Field('text', 'Not a planning fact', required=False)}))
        with pytest.raises(CommissionedReportError, match='commissioned_report_field_has_no_fact:hpc_job_id'):
            hpc_runtime.HPCSource(binding, 'hpc_prediction', refused, collaborators, {}, hpc_runtime.REPORT)
