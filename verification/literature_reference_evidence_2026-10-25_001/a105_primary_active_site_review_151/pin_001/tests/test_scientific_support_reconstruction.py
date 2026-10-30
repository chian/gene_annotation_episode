"""Stable-source reconstruction and one real detached engineering consumer.

Uses CP5's isolated ordinary caller fixture. Prior CP5 artifacts are never read
as current execution evidence, modified or relabeled. Protocol decisions and
controller limits remain explicit fixtures, with no native/scientific run.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import shutil

import pytest

from method_loop.durable import DurableExecutionError, canonical, content_digest
from gene_annotation_episode import independent_execution as independent
from gene_annotation_episode.providers import ModelConnection
from gene_annotation_episode.scientific_support_metadata import (
    annotation_policy_routes, support_observation_kinds)
from gene_annotation_episode.state import Store
import test_assembled_case_reconstruction as assembled
from test_homology_episode_runtime import Provider
from test_scientific_support_runtime import SupportCase, GOAL, action, complete, observations, records
from test_runtime import ScriptedProvider


def forbidden(*args, **kwargs):
    pytest.fail('Changed frozen support identity reached transport or re-projection')


def test_completed_selected_entry_and_frame_replay_keep_original_routes_without_refresh(tmp_path, monkeypatch):
    with Store(tmp_path/'state') as store:
        case = SupportCase(tmp_path, store, stops={1: 2, 2: 1})
        before = records(store)
        provider = ScriptedProvider([action('process.entry', {'option_id': 'A01'}),
            case.commission([]), action('process.entry', {'option_id': 'A01'}, 'measured')])
        workflow = case.workflow(provider)
        root = workflow.build('annotation', 'root', GOAL, case.scope)
        complete(workflow, root)
        saved_observations = observations(store)
        actions = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')]
        frames = [tuple(row) for row in store.db.execute('SELECT * FROM runtime_model_calls ORDER BY episode_id,call_index')]
        binding = workflow.annotation_score_binding
        parent_entry = json.loads(store.db.execute('SELECT result FROM runtime_actions WHERE episode_id=? AND decision_index=0',
            (root.source.episode_id,)).fetchone()[0])['result']
        assert parent_entry['annotation_support_routes']['annotation_binding_sha256'] == content_digest(binding)
        shutil.rmtree(case.source)
        replay = case.workflow(ScriptedProvider([]))
        replay_root = replay.build('annotation', 'root', GOAL, case.scope)
        # This is replay of the already selected/completed original action,
        # including the automatic frame. New reads would legitimately format
        # their unchanged binding, but completed work may not refresh it.
        monkeypatch.setattr(replay, 'source_credit_view', forbidden)
        monkeypatch.setattr(replay.services, 'scientific_support_routes', forbidden)
        monkeypatch.setattr(replay.scientific_process_binding.library, 'execute', forbidden)
        # Legacy in-process Episode reconstruction performs fresh context reads
        # before saved calls. The completed action itself has its own replay
        # boundary, which must reuse the exact saved result/credit.
        outcome = asyncio.run(replay_root.source.execute(
            {'kind': 'tool', 'tool': 'process.entry', 'arguments': {'option_id': 'A01'}}, 0))
        assert outcome.as_record()['credit'] == 0
        assert replay_root.source.last_outcome['result'] == parent_entry
        assert records(store) == before
        assert observations(store) == saved_observations
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_actions ORDER BY episode_id,decision_index')] == actions
        assert [tuple(row) for row in store.db.execute('SELECT * FROM runtime_model_calls ORDER BY episode_id,call_index')] == frames
        saved_call = json.loads(store.db.execute('SELECT request FROM runtime_model_calls WHERE episode_id=? AND call_index=0',
            (root.source.episode_id,)).fetchone()[0])
        replay_root.source.calls = 0
        response, index, actual_context, schema = asyncio.run(replay_root.source.call({}, {}))
        assert actual_context == saved_call['context'] and index == 0
        child = replay.selected(replay_root.source, case.commission([])['selection'], 1).child
        child_response, child_index, child_context, _ = asyncio.run(child.source.call({}, {}))
        assert child_index == 0
        assert child_context['scientific_process']['annotation']['support'] == parent_entry['entry']['support']
        assert child_context['scientific_process']['annotation_support_routes'] == parent_entry['annotation_support_routes']
        assert replay.provider.contexts == []


def test_unchanged_frozen_support_body_and_routes_reopen_after_research_source_removed(tmp_path, monkeypatch):
    fixture = assembled.commission_fixture(tmp_path, monkeypatch)
    source_body = fixture['directory']/'scientific-process-library/entries/A01.json'
    exact_bytes = source_body.read_bytes()
    shutil.rmtree(fixture['source'])
    entered = []
    async def enter(provider):
        entered.append(provider)
        return provider
    monkeypatch.setattr(ModelConnection, '__aenter__', enter)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    monkeypatch.setattr(ModelConnection, 'release', lambda *_: None)
    async def reopen():
        async with independent.open_commission(fixture['spec']) as opened:
            episode = opened['episode']
            workflow = episode.source.workflow
            body = workflow.scientific_process_binding.library.entry('A01')['entry']
            frame = workflow.scientific_process_binding.decision_context(workflow.binding_context(episode.source), {})['scientific_process']
            assert frame['annotation']['support'] == body['support']
            routes = annotation_policy_routes(workflow.project_annotation_score,
                workflow.annotation_score_binding, observation_kinds=support_observation_kinds(body))
            assert routes['status'] == 'available'
            assert frame['annotation_support_routes'] == routes
            assert frame['selection'] == fixture['selection']
            assert episode.request.as_record() == fixture['spec']['child']['request']
            assert source_body.read_bytes() == exact_bytes
            assert observations(workflow.store) == []
    asyncio.run(reopen())
    assert len(entered) == 1 and not fixture['turns'].exists()


@pytest.mark.parametrize('changed', ['support_body', 'support_sources', 'descriptor_version',
    'descriptor_pin', 'annotation_definition', 'annotation_parameters', 'implementation_pin'])
def test_support_or_policy_drift_fails_before_transport(tmp_path, monkeypatch, changed):
    fixture = assembled.commission_fixture(tmp_path, monkeypatch)
    spec, settings = deepcopy(fixture['spec']), deepcopy(fixture['settings'])
    directory = fixture['directory']
    if changed in ('support_body', 'support_sources'):
        relative = 'entries/A01.json' if changed == 'support_body' else 'sources/A01.json'
        path = directory/'scientific-process-library'/relative
        # Exact byte drift alone must invalidate both instruction and source pin.
        path.write_bytes(path.read_bytes() + b' \n')
    elif changed == 'descriptor_version':
        settings['episode_bindings'][0]['version'] = 'scientific_process_episodes_v4'
        assembled.rewrite_settings(fixture, spec, settings)
    elif changed == 'descriptor_pin':
        settings['episode_bindings'][0]['implementation_sha256'] = '0'*64
        assembled.rewrite_settings(fixture, spec, settings)
    elif changed == 'annotation_definition':
        settings['binding_definitions']['annotation_score']['definition']['policy']['scale'] += 1
        assembled.rewrite_settings(fixture, spec, settings)
    elif changed == 'annotation_parameters':
        path = directory/'policy-binding.json'
        value = json.loads(path.read_text())
        value['parameters']['policy']['scientific']['scale'] += 1
        path.write_text(canonical(value)+'\n')
        # Keep the old commission's actual caller binding pin authoritative.
    else:
        spec['runtime_binding']['implementation_sha256'] = '0'*64
    entered = []
    async def enter(provider):
        entered.append(provider)
        forbidden()
    monkeypatch.setattr(ModelConnection, '__aenter__', enter)
    monkeypatch.setattr(ModelConnection, 'complete', forbidden)
    async def reopen():
        with pytest.raises((DurableExecutionError, ValueError)):
            async with independent.open_commission(spec):
                pytest.fail('Drifted support/policy reconstructed as the original binding')
    asyncio.run(reopen())
    assert entered == [] and not fixture['turns'].exists()
    with Store(fixture['workspace']) as store:
        assert observations(store) == []
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 1


def test_real_detached_support_frame_original_form_receipt_and_retirement(tmp_path, monkeypatch):
    # Extend only this new execution's transport assertions. CP5's original
    # fixture/test and all historical permanent evidence retain their owners.
    extra = """        support_frame = context['scientific_process']
        assert set(support_frame['annotation']) == {'id','name','description','support'}
        assert support_frame['annotation']['support']['operands']
        routes = support_frame['annotation_support_routes']
        assert routes['status'] == 'available'
        assert routes['policy'] == context['annotation_score_binding']['definition']['definition']['policy']
"""
    monkeypatch.setattr(assembled, 'TRANSPORT', assembled.TRANSPORT.replace(
        "        selected = context['scientific_process']['selection']['tools']", extra+
        "        selected = context['scientific_process']['selection']['tools']"))
    assembled.test_real_detached_assembled_worker_original_form_single_parent_receipt_and_replay(tmp_path, monkeypatch)
    evidence_path = tmp_path/'verification.json'
    evidence_record = json.loads(evidence_path.read_text())
    calls = [json.loads(line) for line in (tmp_path/'assembled-turns.jsonl').read_text().splitlines()]
    body_path = tmp_path/'run/scientific-process-library/entries/A01.json'
    body = json.loads(body_path.read_text())
    routes = calls[0]['context']['scientific_process']['annotation_support_routes']
    assert all(call['context']['scientific_process']['annotation']['support'] == body['support'] for call in calls)
    assert all(call['context']['scientific_process']['annotation_support_routes'] == routes for call in calls)
    envelope = calls[0]['context']['annotation_score_binding']
    assert routes['annotation_binding_sha256'] == content_digest(envelope)
    assert routes['policy'] == envelope['definition']['definition']['policy']
    assert evidence_record['implementation_sha256'] == independent.implementation_sha256()
    supplemental = {'version': 'scientific_support_construction_detached_verification_v1',
        'implementation_sha256': evidence_record['implementation_sha256'],
        'settings_sha256': evidence_record['settings_sha256'],
        'support_body_sha256': content_digest(body),
        'support_body_file_sha256': hashlib.sha256(body_path.read_bytes()).hexdigest(),
        'support_entry': body, 'annotation_support_routes': routes,
        'annotation_binding': envelope, 'original_requested_form': calls[0]['context']['requested_form'],
        'worker_pid': evidence_record['worker_identity']['pid'],
        'parent_completed_actions': len(evidence_record['parent_observations']),
        'child_completed_actions': len(evidence_record['child_observations']),
        'adopted_support_entries': 0, 'configured_model_science': False, 'native_jobs_submitted': 0}
    (tmp_path/'support-verification.json').write_text(canonical(supplemental)+'\n')
