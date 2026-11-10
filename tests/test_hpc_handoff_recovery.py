"""Receipt ownership and operation dispatch; no SSH or scheduler simulation."""
import asyncio
from dataclasses import replace
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.hpc_episodes import HPCEpisodes
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from method_loop.identities import EpisodeRef
from hpc_helpers import commission, resources


def test_results_before_receipt_delivery_returns_recovery_feedback(tmp_path):
    parent = BindingContext('run', 'parent', 'hpc', (('hpc', 'root'),), {'subject_refs': []},
                            {'commission_id': 'commission'}, {})
    binding = HPCEpisodes(None, store=None, run_id='run', directory=tmp_path,
                          resources=resources(), commissions={'commission': commission()})
    binding.initialize(parent)
    plan_ref = binding.state(parent).put('plan', {'plan_id': 'frozen-original'})
    result = asyncio.run(binding.execute(parent, 'hpc.results', {'plan_ref': plan_ref}, 'early-results'))
    assert result['status'] == 'invalid'
    assert result['feedback']['code'] == 'original_handoff_not_attached'
    assert 'redeliver_report' in result['feedback']['recovery']


def test_recovery_requires_original_owner_plan_and_scope(tmp_path):
    c = commission()
    path = (('hpc', 'root'),)
    owner = EpisodeRef('run', path).episode_id
    parent = BindingContext('run', owner, 'hpc', path, {'subject_refs': []},
                            {'commission_id': 'commission'}, {})
    db = sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE runtime_episodes(run_id,episode_id,path); '
                    'CREATE TABLE runtime_actions(run_id,episode_id,result);')
    binding = HPCEpisodes(None, store=SimpleNamespace(db=db), run_id='run', directory=tmp_path,
                          resources=resources(), commissions={'commission': c})
    binding.initialize(parent)
    assignment = {'frozen_assignment': 'original'}
    binding.state(parent).put('plan', {'practical_assignment': assignment})
    launch = BindingContext('run', 'receiver', 'launch_hpc', (*path, ('launch_hpc', 'repair')),
                            parent.scope, assignment, {})
    for identity, source_path, ref in (
            ('other', (('hpc', 'unrelated'), ('launch_hpc', 'first')), 'unrelated'),
            ('first', (*path, ('launch_hpc', 'first')), 'original')):
        db.execute('INSERT INTO runtime_episodes VALUES (?,?,?)', ('run', identity, json.dumps(source_path)))
        db.execute('INSERT INTO runtime_actions VALUES (?,?,?)', ('run', identity,
            json.dumps({'result': {'outcome': {'facts': {'requested_job': {'handoff': {'id': identity}}}}},
                        'record_refs': [ref]})))
    reads = []
    def read_target(reference, scope):
        reads.append(reference)
        return {'assignment': assignment}
    binding._targets = SimpleNamespace(read_target=read_target)
    assert binding.original_launch_handoff(launch) == 'original'
    assert reads == ['original']
    with pytest.raises(ValueError, match='plan_identity_conflict'):
        binding.original_launch_handoff(replace(launch, assignment={'frozen_assignment': 'different'}))
    with pytest.raises(ValueError, match='plan_identity_conflict'):
        binding.original_launch_handoff(replace(launch, scope={'subject_refs': ['different']}))


@pytest.mark.parametrize('selected,native', [
    ('practical.job.start', 'practical.job.status'),
    ('practical.job.status', 'practical.job.status'),
    ('practical.job.collect', 'practical.job.collect')])
def test_recovered_submission_only_observes_original_job(tmp_path, monkeypatch, selected, native):
    """A report repair cannot reach the backend's submission operation."""
    from gene_annotation_episode import practical_resource_episodes as module
    original_state = object()
    hpc = SimpleNamespace(original_launch_handoff=lambda context: 'original-receipt')
    registry = SimpleNamespace(roles=('hpc',), for_role=lambda role: hpc)
    binding = PracticalResourceEpisodes(SimpleNamespace(workflow=SimpleNamespace(episode_bindings=registry)),
        directory=tmp_path, resources={'hpc': resources()['aurora']})
    assignment = {'resource_kind': 'hpc', 'requested_job': {}, 'progress_requirements': []}
    context = BindingContext('run', 'repair', 'launch_hpc', (('launch_hpc', 'repair'),),
                            {'subject_refs': []}, assignment, {})
    calls = []
    async def execute(state, operation, operands, key):
        assert state is original_state
        assert operation != 'practical.job.start'
        calls.append(operation)
        return {'facts': {'requested_job': {'execution_id': 'original-job'}}}, None
    backend = SimpleNamespace(execute=execute, initial_outcome=lambda _: {'facts': {'paths': []}})
    state = SimpleNamespace(begin=lambda *args: {'state': 'pending'}, context=lambda: {},
        finish=lambda key, outcome, validations, **kwargs: {'outcome': outcome})
    monkeypatch.setattr(binding, '_operations', lambda kind: backend)
    monkeypatch.setattr(binding, 'catalog', lambda _: module.operation_catalog('hpc'))
    monkeypatch.setattr(binding, '_received_target', lambda *args: (original_state, 'original-job'))
    monkeypatch.setattr(binding, 'state', lambda _: state)
    monkeypatch.setattr(module, 'assess_validations', lambda *args, **kwargs: [])
    arguments = {'queue': 'debug', 'resources': ['select=1']} if selected.endswith('.start') else {}
    result = asyncio.run(binding.execute(context, selected, arguments, 'repair-operation'))
    assert result['status'] == 'completed'
    assert calls == [native]
    outcome = result['result']['outcome']
    assert outcome['recovered_original_handoff_ref'] == 'original-receipt'
    assert outcome['native_operation'] == native
