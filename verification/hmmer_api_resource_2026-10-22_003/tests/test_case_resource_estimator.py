"""Actual fixed-case construction and resume, with no episode or native work."""
from dataclasses import replace
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode import case_execution
from gene_annotation_episode.case_execution import prepare_case_run, prepared_case_bindings
from gene_annotation_episode.resource_estimation import ResourceToolEstimator
from gene_annotation_episode.state import Store
from test_case_execution import PARAMETERS, POLICY, prepared


def explicit_policy(path):
    source = ('from dataclasses import replace\n'
        'from gene_annotation_episode.resource_estimation import ResourceToolEstimator\n' +
        POLICY.replace('    return PolicyBindings(', '    bindings = PolicyBindings(') +
        "    return replace(bindings, resource_estimator=ResourceToolEstimator.from_record(parameters['resource_estimator']))\n")
    path.write_text(source)


def test_default_case_preserves_original_policy_shape_and_estimator(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    run = tmp_path/'default-run'
    with patch('subprocess.Popen', side_effect=AssertionError('Construction cannot launch work')):
        manifest = prepare_case_run(case, run, configuration)
        with Store(case/'workspace') as store, prepared_case_bindings(store, run,
                policy_file=policy_file, parameters=PARAMETERS, resume=False) as (opened, options):
            assert opened == manifest
            assert type(options['resource_estimator']) is ResourceToolEstimator
            assert options['resource_estimator'].as_record() == ResourceToolEstimator().as_record()
        original = (run/'policy-binding.json').read_bytes()
        recorded = json.loads(original)
        policy, actual = case_execution._load_policy(run, None, None, resume=True)
        assert policy.resource_estimator is None
        assert actual == recorded
        assert set(recorded) == {'source_sha256', 'snapshot_file', 'parameters', 'definitions'}
        assert set(recorded['definitions']) == {
            'credit', 'scientific_child_credit', 'job_credit', 'monitoring_credit', 'controller'}
        with Store(case/'workspace') as store, prepared_case_bindings(store, run, resume=True) as (_, restored):
            assert restored['resource_estimator'].as_record() == options['resource_estimator'].as_record()
        assert (run/'policy-binding.json').read_bytes() == original
        assert not (run/'run.json').exists()


@pytest.mark.parametrize('record', [ResourceToolEstimator().as_record(),
    ResourceToolEstimator.with_reported_results().as_record()])
def test_explicit_caller_estimator_reaches_actual_prepared_bindings_and_resume(tmp_path, monkeypatch, record):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    explicit_policy(policy_file)
    run = tmp_path/'explicit-run'
    parameters = {**PARAMETERS, 'resource_estimator': record}
    loaded = []
    original_loader = case_execution._load_policy

    def observe_policy(*args, **kwargs):
        result = original_loader(*args, **kwargs)
        loaded.append(result[0])
        return result

    # Observe actual policy construction, without replacing its selected value.
    monkeypatch.setattr(case_execution, '_load_policy', observe_policy)
    with patch('subprocess.Popen', side_effect=AssertionError('Construction cannot launch work')):
        manifest = prepare_case_run(case, run, configuration)
        with Store(case/'workspace') as store, prepared_case_bindings(store, run,
                policy_file=policy_file, parameters=parameters, resume=False) as (opened, options):
            assert opened == manifest
            assert options['resource_estimator'] is loaded[-1].resource_estimator
            assert options['resource_estimator'].as_record() == record
        recorded_bytes = (run/'policy-binding.json').read_bytes()
        recorded = json.loads(recorded_bytes)
        assert recorded['definitions']['resource_estimator'] == record
        assert recorded['parameters'] == parameters
        # Resume uses the immutable policy snapshot rather than this original.
        policy_file.write_text('raise AssertionError("Do not use changed original policy")\n')
        with Store(case/'workspace') as store, prepared_case_bindings(store, run, resume=True) as (_, restored):
            assert restored['resource_estimator'] is loaded[-1].resource_estimator
            assert restored['resource_estimator'].as_record() == record
        assert (run/'policy-binding.json').read_bytes() == recorded_bytes
        assert not (run/'run.json').exists()


def test_policy_requires_exact_existing_estimator_type(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    run = tmp_path/'typed-run'
    prepare_case_run(case, run, configuration)
    policy, _ = case_execution._load_policy(run, policy_file, PARAMETERS, resume=False)

    class DerivedEstimator(ResourceToolEstimator):
        pass

    for untyped in (object(), ResourceToolEstimator().as_record(), 'v3', DerivedEstimator()):
        with pytest.raises(TypeError, match='typed_resource_tool_estimator_required'):
            replace(policy, resource_estimator=untyped)
    assert replace(policy, resource_estimator=None).resource_estimator is None


def test_resume_rejects_replacement_estimator_parameters_and_definitions(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    explicit_policy(policy_file)
    run = tmp_path/'immutable-run'
    parameters = {**PARAMETERS, 'resource_estimator': ResourceToolEstimator.with_reported_results().as_record()}
    prepare_case_run(case, run, configuration)
    with Store(case/'workspace') as store, prepared_case_bindings(store, run,
            policy_file=policy_file, parameters=parameters, resume=False):
        pass
    original = (run/'policy-binding.json').read_bytes()
    changed = {**parameters, 'resource_estimator': ResourceToolEstimator().as_record()}
    with Store(case/'workspace') as store:
        with pytest.raises(ValueError, match='resume_cannot_replace_policy_parameters'):
            with prepared_case_bindings(store, run, parameters=changed, resume=True):
                raise AssertionError('Replaced estimator cannot be supplied')
    assert (run/'policy-binding.json').read_bytes() == original
    # A changed definition cannot agree with the original typed policy factory.
    tampered = json.loads(original)
    tampered['definitions']['resource_estimator'] = ResourceToolEstimator().as_record()
    (run/'policy-binding.json').write_text(json.dumps(tampered))
    tampered_bytes = (run/'policy-binding.json').read_bytes()
    with Store(case/'workspace') as store:
        with pytest.raises(ValueError, match='restored_policy_definition_changed'):
            with prepared_case_bindings(store, run, resume=True):
                raise AssertionError('Replaced estimator definition cannot be supplied')
    assert (run/'policy-binding.json').read_bytes() == tampered_bytes
    assert not (run/'run.json').exists()
