"""Caller-owned scientific forecast roles through the actual fixed-case adapter.

The fixture opens the real Store, native registry and shared statistics, but does
not run a model, controller, episode or native search.
"""
from dataclasses import replace
import json
from unittest.mock import patch

import pytest

from gene_annotation_episode.case_execution import (
    PolicyBindings, _load_policy, prepare_case_run, prepared_case_bindings,
)
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.execution_expectations import ExecutionExpectations
from gene_annotation_episode.homology_jobs import HomologyJobs, digest
from gene_annotation_episode.state import Store
from test_case_execution import PARAMETERS, POLICY, prepared


PLANNING_ROLES = ('annotation', 'scientific_process')
ROLE_POLICY = POLICY + '''
from dataclasses import replace

_original_create_policy = create_policy

def create_policy(parameters):
    return replace(_original_create_policy(parameters),
        execution_planning_roles=tuple(parameters['planning_roles']))
'''


def unexecuted(*args, **kwargs):
    raise AssertionError('Forecast role configuration must not execute policy')


def policy_fixture():
    definition = {'kind': 'fixture_unexecuted_policy'}
    return PolicyBindings(unexecuted, unexecuted, unexecuted, unexecuted,
        unexecuted, definition, definition, definition, definition, definition)


def test_policy_accepts_explicit_unique_forecast_roles_without_running_policy():
    legacy = policy_fixture()
    assert legacy.execution_planning_roles is None
    selected = replace(legacy, execution_planning_roles=PLANNING_ROLES)
    assert selected.execution_planning_roles == PLANNING_ROLES
    assert selected.project_task_credit is legacy.project_task_credit
    assert selected.controller_factory is legacy.controller_factory


@pytest.mark.parametrize('roles', [
    [], ['annotation', 'scientific_process'], (),
    ('annotation', 'annotation'), ('annotation', ''),
    ('scientific process',), ('scientific-process',),
    ('annotation', None), ('annotation', 1), False,
])
def test_policy_rejects_nonexplicit_or_nonunique_forecast_role_names(roles):
    with pytest.raises(ValueError, match='explicit_unique_execution_planning_roles_required'):
        replace(policy_fixture(), execution_planning_roles=roles)


def test_prepared_case_forwards_and_reopens_scientific_forecast_selector(tmp_path):
    case, configuration, policy_file = prepared(tmp_path)
    policy_file.write_text(ROLE_POLICY)
    run = tmp_path/'run'
    parameters = {**PARAMETERS, 'planning_roles': list(PLANNING_ROLES)}
    with patch('subprocess.Popen', side_effect=AssertionError('Configuration cannot launch work')):
        manifest = prepare_case_run(case, run, configuration)
        with Store(case/'workspace') as store:
            with prepared_case_bindings(store, run, policy_file=policy_file,
                    parameters=parameters, resume=False) as (actual_manifest, options):
                assert actual_manifest == manifest
                expectations = options['execution_expectations']
                first_binding = expectations.as_record()
                assert expectations.planning_roles == frozenset(PLANNING_ROLES)
                assert expectations.applies('annotation')
                assert expectations.applies('scientific_process')
                assert not expectations.applies('improvement')
                assert expectations.episode_types == (
                    frozenset(PLANNING_ROLES) | frozenset(options['job_episodes'].roles))
                assert first_binding['homology']['planning_roles'] == list(PLANNING_ROLES)
                assert ExecutionExpectations.from_record(first_binding).as_record() == first_binding

                # Actual prospective protein classes can reach this role before
                # any job is commissioned. Configuring the role chooses no job.
                classes = options['job_episodes'].prospective_execution_classes(
                    store, {'subject_refs': [manifest['target_ref']]})
                assert len(classes) == 1 and classes[0].query_residues == 253
                captured = expectations.capture('scientific_process', planning_scopes=classes)
                assert captured['status'] == 'available'
                assert [item['query_residues'] for item in captured['execution_classes']] == [253]
                assert 'assigned_execution_class_ref' not in captured

            marker = run/'policy-binding.json'
            before = marker.read_bytes()
            recorded = json.loads(before)
            assert recorded['execution_planning_roles'] == list(PLANNING_ROLES)
            assert recorded['parameters'] == parameters
            assert (run/recorded['snapshot_file']).read_text() == ROLE_POLICY

            # The original staging policy is no longer consulted on reopen.
            policy_file.write_text('raise AssertionError("Use the pinned policy snapshot")')
            with prepared_case_bindings(store, run, resume=True) as (reopened_manifest, reopened):
                assert reopened_manifest == manifest
                assert reopened['execution_expectations'].as_record() == first_binding
            assert marker.read_bytes() == before
            assert store.count('annotation') == store.count('assessment') == 0
            assert store.db.execute("SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='runtime_runs'").fetchall() == []

    jobs = HomologyJobs(run/'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()


@pytest.mark.parametrize('changed_roles', [
    ['annotation', 'improvement'], ['scientific_process', 'annotation'], None,
])
def test_resume_rejects_replaced_or_removed_forecast_selector_without_overwrite(tmp_path, changed_roles):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    policy_file.write_text(ROLE_POLICY)
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    parameters = {**PARAMETERS, 'planning_roles': list(PLANNING_ROLES)}
    _load_policy(run, policy_file, parameters, resume=False)
    marker = run/'policy-binding.json'
    recorded = json.loads(marker.read_text())
    if changed_roles is None:
        del recorded['execution_planning_roles']
    else:
        recorded['execution_planning_roles'] = changed_roles
    marker.write_text(json.dumps(recorded))
    before = marker.read_bytes()
    with Store(case/'workspace') as store:
        with pytest.raises(ValueError, match='restored_policy_definition_changed'):
            with prepared_case_bindings(store, run, resume=True):
                pytest.fail('Changed forecast roles must not be yielded to the runtime')
    assert marker.read_bytes() == before


def test_default_case_retains_historical_policy_marker_and_forecast_roles(tmp_path):
    case, configuration, policy_file = prepared(tmp_path, with_protein=False)
    assert policy_file.read_text() == POLICY
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    expected = {'source_sha256': digest(policy_file),
        'snapshot_file': 'policy-'+digest(policy_file)+'.py', 'parameters': PARAMETERS,
        'definitions': {key: {'kind': 'fixture_constant', 'score': PARAMETERS['score']}
            for key in ('credit', 'scientific_child_credit', 'job_credit', 'monitoring_credit')}}
    expected['definitions']['controller'] = {'kind': 'fixture_estimator',
        'cost': PARAMETERS['cost'], 'numerical': PARAMETERS['numerical']}
    # Historical policy persistence canonically copies these two nested values
    # before writing the outer record in its declared field order.
    expected['parameters'] = json.loads(canonical(expected['parameters']))
    expected['definitions'] = json.loads(canonical(expected['definitions']))

    with patch('subprocess.Popen', side_effect=AssertionError('Configuration cannot launch work')):
        with Store(case/'workspace') as store:
            with prepared_case_bindings(store, run, policy_file=policy_file,
                    parameters=PARAMETERS, resume=False) as (_, options):
                first = options['execution_expectations'].as_record()
                assert first['homology']['planning_roles'] == ['annotation', 'improvement']
                assert not options['execution_expectations'].applies('scientific_process')
            marker = run/'policy-binding.json'
            before = marker.read_bytes()
            assert before == json.dumps(expected, allow_nan=False).encode()
            assert 'execution_planning_roles' not in json.loads(before)
            policy_file.unlink()
            with prepared_case_bindings(store, run, resume=True) as (_, options):
                assert options['execution_expectations'].as_record() == first
            assert marker.read_bytes() == before
