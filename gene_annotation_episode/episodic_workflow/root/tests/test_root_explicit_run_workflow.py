"""Explicit original root policy through the real saved run entry point.

These engineering tests deliberately supply no transport response. A genuine
provider-unavailable error occurs before any acquired action; it is not an
executed failed scientific unit. Real Store/Journal/root/native credit/controller
objects remain in use. Empty private topology is explicit, not the default.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.evidence_root import NativeEvidenceRootCredit
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal, WorkflowError
from gene_annotation_episode.episodic_workflow.root.run_execution import run_workflow
from gene_annotation_episode.episodic_workflow.root.tests.test_root_native_factory import controller_factory
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import (
    ConstructorTools, InputOnlyProvider, ProviderUnavailable)


def explicit_options(store, directory):
    project = NativeEvidenceRootCredit(axes=('A102',))
    scope = store.validate_scope()
    return {
        'run_dir': directory, 'controller_factory': controller_factory,
        'project_credit': project, 'episode_record_receipts': True,
        'initial_known_record_refs': list(scope['subject_refs']),
        'episode_binding_factories': (), 'annotation_child_roles': (),
        'binding_definitions': {
            'credit': project.as_record(),
            'controller': {'version': 'engineering_original_native_factory_controller_v1',
                           'cost': 0, 'continuation': 'original_yield_controller'}},
        'goal': 'Engineering explicit run persistence, no acquisition',
    }


def attempt(store, tools, directory, *, resume=False, options=None):
    provider = InputOnlyProvider()
    kwargs = explicit_options(store, directory) if options is None else options
    before = store.db.total_changes
    summary = asyncio.run(run_workflow(store, tools, provider=provider, resume=resume, **kwargs))
    assert len(provider.requests) == (0 if resume else 1) and tools.execution_calls == []
    if resume:
        assert store.db.total_changes == before
    manifest = json.loads((directory/'run.json').read_bytes())
    journal = Journal(store, manifest['run_id'])
    run = dict(journal.row('runtime_runs'))
    settings = json.loads(run['settings'])
    assert {k: v for k, v in manifest.items() if k != 'run_id'} == settings
    assert settings['binding_definitions'] == kwargs['binding_definitions']
    assert settings['episode_bindings'] == [] and settings['annotation_child_roles'] == []
    assert settings['controller'] is None and settings['credit_policy'] is None
    assert run['state'] == 'yielded'
    assert json.loads(run['summary']) == summary == json.loads((directory/'summary.json').read_bytes())
    assert summary == {
        'run_id': manifest['run_id'], 'directory': str(directory), 'state': 'yielded',
        'pending_handles': [], 'ended_by': 'source_failed',
        'scientific_completion': 'not_established_by_termination',
        'completed_actions': 0, 'credit': 0.0, 'episode_count': 1,
        'pending_report_deliveries': 0, 'annotation_score_status': 'unavailable_no_scorer_bound'}
    rows = lambda table: [dict(row) for row in store.db.execute(
        'SELECT * FROM '+table+' WHERE run_id=?', (manifest['run_id'],))]
    assert rows('runtime_actions') == rows('runtime_observations') == []
    episodes = rows('runtime_episodes')
    calls = rows('runtime_model_calls')
    assert len(episodes) == 1 and len(calls) == 1
    assert calls[0]['response'] is None and calls[0]['purpose'] == 'decision'
    if not resume:
        assert provider.requests[0]['context'] == json.loads(calls[0]['request'])['context']
    assert calls[0]['episode_id'] == episodes[0]['episode_id']
    failures = rows('runtime_source_failures')
    assert len(failures) == 1 and failures[0]['episode_id'] == episodes[0]['episode_id']
    assert failures[0]['decision_index'] == 0
    assert json.loads(failures[0]['failure']) == {
        'category': 'episode_execution', 'cause_code': 'selected_operation_failed',
        'exception_type': ProviderUnavailable.__name__}
    return manifest, settings, episodes[0], calls[0], failures[0], summary


def test_explicit_original_native_policy_reaches_actual_pending_provider(tmp_path):
    with Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQ', molecule='protein')
        attempt(store, ConstructorTools(), tmp_path/'workflow')


def test_explicit_run_reopens_saved_source_failure_without_retry(tmp_path):
    directory = tmp_path/'workflow'
    with Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQ', molecule='protein')
        first = attempt(store, ConstructorTools(), directory)
    with Store(tmp_path/'store') as store:
        second = attempt(store, ConstructorTools(), directory, resume=True)
        assert second == first


def test_explicit_run_rejects_changed_recorded_policy_before_provider(tmp_path):
    directory = tmp_path/'workflow'
    with Store(tmp_path/'store') as store:
        store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQ', molecule='protein')
        first = attempt(store, ConstructorTools(), directory)
        options = explicit_options(store, directory)
        options['binding_definitions'] = deepcopy(options['binding_definitions'])
        options['binding_definitions']['controller']['cost'] = 1
        provider, tools = InputOnlyProvider(), ConstructorTools()
        before = store.db.total_changes
        with pytest.raises(WorkflowError) as caught:
            asyncio.run(run_workflow(store, tools, provider=provider, resume=True, **options))
        assert str(caught.value) == "resumption cannot replace the run's custom binding definitions"
        assert provider.requests == [] and tools.execution_calls == []
        assert store.db.total_changes == before
        assert json.loads((directory/'run.json').read_bytes()) == first[0]
