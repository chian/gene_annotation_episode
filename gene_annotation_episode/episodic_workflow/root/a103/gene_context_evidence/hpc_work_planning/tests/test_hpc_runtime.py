"""A103 HPC resource prediction links on the generic runner and fits over its owner's real ledger.

Real bindings, the run's shared Store, the real episode_runtime registry, journal and linker, a real
``ModelProvider`` (never called) and a real ``HPCLedger``. The commission is a test-written,
deliberately unlaunchable contract fixture: no model, network or HPC job is used.
"""
import asyncio
from copy import deepcopy

import pytest

from episode_runtime import BindingRegistry, LinkError, RunJournal, link
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning import \
    hpc_runtime
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.episode import \
    HPCEpisode as Planning
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.hpc_resource_prediction.episode import \
    HPCEpisode as Prediction
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.hpc_queue import digest
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.gene_context_evidence.tests.test_hpc_calculations import base_commission
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from yield_control import AccumulationYieldController

PREDICTION = 'gene_context_evidence/hpc_work_planning/hpc_resource_prediction'
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
RESOURCES = {'aurora': {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/contract-fixture', 'account': 'fixture',
                        'python_executable': '/not-an-executable-contract-fixture', 'ssh_argv': ['false']}}
SCOPE = {'subject_refs': []}


def commission():
    value = deepcopy(base_commission())
    value['limits'] = {'result_limit_bytes': 4096, 'queue_max_age_seconds': 600}
    value['yield_bindings'] = {role: {'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05}}
                               for role in ('hpc', 'hpc_prediction', 'hpc_execution')}
    return value


def owner_ledger(directory, run_id, owner, scope):
    """The ledger the planning owner writes for its commission (``hpc_runtime.open_ledger``)."""
    ledger = HPCLedger(directory / 'hpc' / digest([run_id, owner]), commission())
    ledger.put('owner', {'run_id': run_id, 'episode_id': owner, 'scope': scope}, identity='owner')
    return ledger


def test_prediction_requires_its_hpc_services(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry([Prediction()])
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        with pytest.raises(LinkError, match='collaborator_required:' + PREDICTION + ':a103_hpc'):
            link(registry, PREDICTION, {'scope': SCOPE, 'role_assignment': {'owner_episode_id': 'owner'}},
                 run_id='run', journal=RunJournal(tmp_path / 'journal.sqlite'),
                 collaborators={'store': store, 'model_provider': provider})


def test_prediction_fits_over_its_owner_ledger_and_reads_unbounded_model_credit(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc',
                                       shared_execution_memory=None)
    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        scope = {'subject_refs': list(store.problem()['subject_refs'])}
        ledger = owner_ledger(services.directory, 'run', 'owner-episode', scope)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        run = link(BindingRegistry([Prediction()]), PREDICTION,
                   {'scope': scope, 'role_assignment': {'owner_episode_id': 'owner-episode'}}, run_id='run',
                   journal=RunJournal(tmp_path / 'journal.sqlite'),
                   collaborators={'store': store, 'model_provider': provider, 'a103_hpc': services})
        source = run.episode.source
        assert isinstance(source, hpc_runtime.HPCSource)
        names = [entry['name'] for entry in source.catalog]
        assert 'hpc.model.fit' in names and 'hpc.plan' not in names
        assert source.credit()['credit'] == 0.
        episode_id = source._bound.episode_id
        opened = run.episode.grain.controller(source._bound.path)
        assert isinstance(opened, AccumulationYieldController)
        assert opened.state().stop is False and opened.initial_credit == 0.
        outcome = asyncio.run(hpc_runtime.execute(
            'hpc_prediction', services, ledger, 'hpc.model.fit',
            {'training_ids': ['measurement-' + str(i) for i in range(1, 7)]}, 'run:fit:0', episode_id))
        assert outcome['status'] == 'completed'
        result = outcome['result']
        gain = result['validation_quality'] - result['reference_quality']
        view = hpc_runtime.credit_view('hpc_prediction', ledger, episode_id)
        assert view['model_quality_improvement'] == pytest.approx(gain)
        assert view['credit'] == pytest.approx(0.01 * gain)
        assert ledger.credit_view()['components']['model'] == pytest.approx(0.01 * gain)
        invalid = asyncio.run(hpc_runtime.execute(
            'hpc_prediction', services, ledger, 'hpc.model.fit', {'training_ids': ['measurement-8']},
            'run:fit:1', episode_id))
        assert invalid['status'] == 'invalid'
        assert invalid['feedback']['code'] == 'training_ids_must_be_original_nonvalidation_cases'
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_planning_requires_a_commission_with_yield_bindings(tmp_path):
    services = hpc_runtime.HPCServices(resources=RESOURCES, directory=tmp_path / 'hpc',
                                       shared_execution_memory=None)
    value = commission()
    del value['yield_bindings']
    with pytest.raises(hpc_runtime.HPCRuntimeError, match='a103_hpc_commission_yield_bindings_required'):
        hpc_runtime.planning_assignment({'commission': value}, services)
    assert Planning().required_collaborators == ('model_provider', 'store', 'a103_hpc')
