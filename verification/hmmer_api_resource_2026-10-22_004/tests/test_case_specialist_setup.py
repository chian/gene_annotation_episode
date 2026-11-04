"""Fixed-case setup policy pins and forwarding, without running specialist work.

The setup callable and numerical policy are explicit engineering fixtures. The
real Store and native registry are reopened, but no model, controller, episode or
native search executes in these checks.
"""
import asyncio
from dataclasses import replace
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode.case_execution import (
    PolicyBindings, _load_policy, prepare_case_run, prepared_case_bindings,
    run_prepared_case,
)
from gene_annotation_episode.episode_application_services import service_binding
from gene_annotation_episode.homology_jobs import HomologyJobs, digest
from gene_annotation_episode.state import Store
from test_case_execution import PARAMETERS, POLICY, prepared


SETUP_POLICY = '''from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.episode_application_services import EpisodeApplicationServices

SETUP_CALLS = []
LAST_POLICY = None

def fixture_setup(store, *, run_id, directory, job_episodes, resource_estimator):
    SETUP_CALLS.append(run_id)
    return EpisodeApplicationServices([], {})

def unexecuted(*args, **kwargs):
    raise AssertionError('Policy forwarding must not execute work')

def create_policy(parameters):
    global LAST_POLICY
    definition = {'kind': 'fixture_unexecuted_policy'}
    LAST_POLICY = PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
        unexecuted, definition, definition, definition, definition, definition,
        episode_service_factory=fixture_setup,
        episode_service_binding=parameters['services'])
    return LAST_POLICY
'''

SETUP_PARAMETERS = {'services': {'kind': 'fixture_specialist_setup',
    'revision': 1, 'features': {'monitoring': True, 'resources': []}}}


def fixture_policy(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    policy_file.write_text(SETUP_POLICY)
    run = tmp_path/'run'
    manifest = prepare_case_run(case, run, configuration)
    return case, run, policy_file, manifest


def assert_original_setup(options):
    factory = options['episode_service_factory']
    original = factory.__globals__['LAST_POLICY']
    assert factory is original.episode_service_factory
    assert options['episode_service_binding'] is original.episode_service_binding
    assert options['episode_service_binding'] == SETUP_PARAMETERS['services']
    assert factory.__globals__['SETUP_CALLS'] == []


def test_policy_binding_accepts_optional_paired_setup_without_invocation():
    def unexecuted(*args, **kwargs):
        raise AssertionError('Validation must not invoke policy callables')

    definition = {'kind': 'fixture_unexecuted_policy'}
    legacy = PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
        unexecuted, definition, definition, definition, definition, definition)
    assert legacy.episode_service_factory is legacy.episode_service_binding is None
    supplied = replace(legacy, episode_service_factory=unexecuted,
        episode_service_binding=SETUP_PARAMETERS['services'])
    assert supplied.episode_service_factory is unexecuted
    assert supplied.episode_service_binding is SETUP_PARAMETERS['services']


@pytest.mark.parametrize(('factory', 'definition'), [
    (lambda: None, None),
    (None, {'kind': 'fixture'}),
    (False, {'kind': 'fixture'}),
    (lambda: None, {}),
    (lambda: None, []),
    (lambda: None, {'value': float('nan')}),
    (lambda: None, {'value': float('inf')}),
    (lambda: None, {'value': object()}),
])
def test_policy_binding_rejects_incomplete_or_nonfinite_setup(factory, definition):
    def unexecuted(*args, **kwargs):
        raise AssertionError('Validation must not invoke policy callables')

    binding = {'kind': 'fixture_unexecuted_policy'}
    with pytest.raises((ValueError, TypeError)):
        PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
            unexecuted, binding, binding, binding, binding, binding,
            episode_service_factory=factory, episode_service_binding=definition)


def test_setup_pin_uses_original_policy_snapshot_on_resume(tmp_path):
    _, run, policy_file, _ = fixture_policy(tmp_path)
    policy, recorded = _load_policy(run, policy_file, SETUP_PARAMETERS, resume=False)
    expected = service_binding(policy.episode_service_factory, policy.episode_service_binding)
    assert recorded['episode_application_services'] == expected
    assert expected == {'version': 'episode_application_services_v1',
        'factory': 'fixed_gene_policy_'+recorded['source_sha256']+'.fixture_setup',
        'definition': SETUP_PARAMETERS['services']}
    assert 'episode_application_services' not in recorded['definitions']
    assert (run/recorded['snapshot_file']).read_bytes() == policy_file.read_bytes()
    assert json.loads((run/'policy-binding.json').read_text()) == recorded
    assert policy.episode_service_factory.__globals__['SETUP_CALLS'] == []

    policy_file.write_text('raise AssertionError("Original staging policy is no longer authoritative")')
    restored, replay = _load_policy(run, None, None, resume=True)
    assert replay == recorded
    assert service_binding(restored.episode_service_factory, restored.episode_service_binding) == expected
    assert restored.episode_service_factory.__globals__['SETUP_CALLS'] == []


@pytest.mark.parametrize('changed', ['definition', 'factory', 'removed'])
def test_setup_pin_rejects_changed_saved_descriptor_before_overwrite(tmp_path, changed):
    _, run, policy_file, _ = fixture_policy(tmp_path)
    _, recorded = _load_policy(run, policy_file, SETUP_PARAMETERS, resume=False)
    if changed == 'definition':
        recorded['episode_application_services']['definition']['revision'] = 2
    elif changed == 'factory':
        recorded['episode_application_services']['factory'] = 'fixture.replacement'
    else:
        del recorded['episode_application_services']
    marker = run/'policy-binding.json'
    marker.write_text(json.dumps(recorded))
    before = marker.read_bytes()
    with pytest.raises(ValueError, match='restored_policy_definition_changed'):
        _load_policy(run, None, None, resume=True)
    assert marker.read_bytes() == before


@pytest.mark.parametrize('changed', ['source', 'snapshot', 'parameters'])
def test_setup_keeps_existing_source_and_parameter_resume_pins(tmp_path, changed):
    _, run, policy_file, _ = fixture_policy(tmp_path)
    _, recorded = _load_policy(run, policy_file, SETUP_PARAMETERS, resume=False)
    options = {}
    if changed == 'source':
        policy_file.write_text(SETUP_POLICY+'\n# Changed caller source\n')
        options['policy_file'] = policy_file
        message = 'resume_cannot_replace_policy_source'
    elif changed == 'snapshot':
        (run/recorded['snapshot_file']).write_text(SETUP_POLICY+'\n# Changed saved source\n')
        message = 'recorded_policy_source_changed'
    else:
        options['parameters'] = {'services': {'kind': 'fixture_specialist_setup', 'revision': 2}}
        message = 'resume_cannot_replace_policy_parameters'
    before = (run/'policy-binding.json').read_bytes()
    with pytest.raises(ValueError, match=message):
        _load_policy(run, options.get('policy_file'), options.get('parameters'), resume=True)
    assert (run/'policy-binding.json').read_bytes() == before


def test_prepared_bindings_forward_original_setup_without_running_it(tmp_path):
    case, run, policy_file, manifest = fixture_policy(tmp_path)
    with Store(case/'workspace') as store:
        with prepared_case_bindings(store, run, policy_file=policy_file,
                parameters=SETUP_PARAMETERS, resume=False) as (actual_manifest, options):
            assert actual_manifest == manifest
            assert_original_setup(options)
            assert options['job_episodes'] is not None
            assert options['resource_estimator'] is not None
        policy_file.unlink()
        with prepared_case_bindings(store, run, resume=True) as (replay_manifest, replay):
            assert replay_manifest == manifest
            assert_original_setup(replay)
        assert store.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='runtime_runs'").fetchall() == []
        assert store.count('annotation') == store.count('assessment') == 0
    jobs = HomologyJobs(run/'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()


def test_case_entrypoint_forwards_setup_to_common_runtime_without_invocation(tmp_path):
    case, run, policy_file, manifest = fixture_policy(tmp_path)
    calls = []
    provider = object()

    async def capture_runtime(store, tools, **options):
        assert_original_setup(options)
        assert store.path == (case/'workspace').resolve()
        assert options['goal'] == manifest['goal']
        assert options['provider'] is provider
        calls.append(options)
        return {'fixture_runtime_boundary': True}

    with patch('gene_annotation_episode.case_execution.run_workflow', capture_runtime):
        assert asyncio.run(run_prepared_case(run, policy_file=policy_file,
            parameters=SETUP_PARAMETERS, provider=provider)) == {'fixture_runtime_boundary': True}
        policy_file.unlink()
        assert asyncio.run(run_prepared_case(run, resume=True,
            provider=provider)) == {'fixture_runtime_boundary': True}
    assert len(calls) == 2
    assert calls[0]['resume'] is False and calls[1]['resume'] is True


def test_legacy_policy_pin_and_forwarding_retain_absent_setup_fields(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    assert policy_file.read_text() == POLICY
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    _, recorded = _load_policy(run, policy_file, PARAMETERS, resume=False)
    expected = {'source_sha256': digest(policy_file),
        'snapshot_file': 'policy-'+digest(policy_file)+'.py', 'parameters': PARAMETERS,
        'definitions': {key: {'kind': 'fixture_constant', 'score': PARAMETERS['score']}
            for key in ('credit', 'scientific_child_credit', 'job_credit', 'monitoring_credit')}}
    expected['definitions']['controller'] = {'kind': 'fixture_estimator',
        'cost': PARAMETERS['cost'], 'numerical': PARAMETERS['numerical']}
    assert recorded == expected
    before = (run/'policy-binding.json').read_bytes()
    policy_file.unlink()
    with Store(case/'workspace') as store:
        with prepared_case_bindings(store, run, resume=True) as (_, options):
            assert 'episode_service_factory' not in options
            assert 'episode_service_binding' not in options
    assert (run/'policy-binding.json').read_bytes() == before
