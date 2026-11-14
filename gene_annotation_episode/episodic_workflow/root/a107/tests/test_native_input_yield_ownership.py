"""Own-native input admission and estimator selection with explicit controlled ports.

Actual methods and BindingContext are used. Constructors and scientific/native
operations are not executed. Original error/return and call-order observations
are compared with the retained canonical baseline.
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a107'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning',
    'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, 'execution_job_submission', child))), role)
    for prefix in PREFIXES for child, role in (('api_job_execution', 'launch_api'),
        ('local_job_execution', 'launch_local'), ('hpc_job_execution', 'launch_hpc'))]


def capture(call):
    try:
        return {'value': call()}
    except (ValueError, TypeError, KeyError) as error:
        return {'exception': type(error).__module__ + '.' + type(error).__name__, 'message': str(error)}


def observations(home, role):
    from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
    from gene_annotation_episode.episodic_workflow.root.a107.practical_yield import PracticalYieldEstimator
    owner_class = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode').ExecutionEpisode
    owner = object.__new__(owner_class)
    assert owner.roles == (role,)
    scope, assignment = {'subject_refs': []}, {'controlled': 'original-assignment'}
    def context(parent):
        path = (('launch', 'original-parent'), (role, 'original-child')) if parent else ((role, 'original-child'),)
        return BindingContext('controlled-run', 'controlled-episode', role, path, scope, assignment, {})
    original = {'immutable_input_versions': [], 'controlled': 'original-parent-assignment'}
    events = []
    row = {'request': json.dumps({'message': {'episode_assignment': original}})}
    def execute(query, args):
        events.append({'query': query, 'args': list(args)})
        return SimpleNamespace(fetchone=lambda: row)
    owner.run_id = 'controlled-run'
    owner.store = SimpleNamespace(db=SimpleNamespace(execute=execute))
    def launch(value):
        events.append({'launch': value})
        return value
    owner._launch = launch
    def api(value, selected, supplied_scope):
        captured_scope = dict(supplied_scope)
        assert captured_scope == {'subject_refs': ()}
        assert type(captured_scope['subject_refs']) is tuple
        # The original baseline writer stores this immutable tuple as a JSON array.
        captured_scope['subject_refs'] = list(captured_scope['subject_refs'])
        events.append({'api_parent': value, 'assignment': dict(selected), 'scope': captured_scope})
    owner._validate_blast_api_parent_request = api
    def masking(supplied, selected):
        assert supplied.role == role and dict(selected) == assignment
        events.append({'masking': role})
        raise ValueError('controlled_input_boundary_after_original_role_selection')
    owner._masking_inputs = masking
    result = {}
    for case in ('not_launch_child', 'missing_parent', 'existing_parent', 'invalid_parent_request'):
        events.clear()
        row = None if case == 'missing_parent' else {'request': 'invalid-json' if case == 'invalid_parent_request' else json.dumps({'message': {'episode_assignment': original}})}
        result[case] = {'outcome': capture(lambda: owner._check_parent_inputs(context(case != 'not_launch_child'))), 'events': list(events)}
    assert result['not_launch_child'] == {'outcome': {'value': None}, 'events': []}
    assert result['missing_parent']['outcome']['message'] == 'execution_original_launch_assignment_unavailable'
    assert result['existing_parent']['outcome']['message'] == 'controlled_input_boundary_after_original_role_selection'
    assert any('api_parent' in event for event in result['existing_parent']['events']) == (role == 'launch_api')
    assert result['invalid_parent_request']['outcome']['exception'] == 'json.decoder.JSONDecodeError'
    supplied = context(True)
    for fail in (False, True):
        events.clear()
        def practical(value):
            assert value is supplied
            events.append('practical_context')
            return value
        def delegated(value):
            assert value is supplied
            events.append('delegate.estimator')
            if fail: raise ValueError('controlled_delegate_estimator_failure')
            return {'original_delegate': role}
        def delegate(value):
            assert value is supplied
            events.append('delegate')
            return SimpleNamespace(practical_estimator=delegated)
        def verify(value, proof):
            assert value is supplied and proof == {'status': 'invalid'}
            events.append('verify_completion')
            if fail: raise ValueError('controlled_original_verifier_failure')
            return False
        owner._practical_context, owner._delegate, owner.verify_completion = practical, delegate, verify
        def estimator():
            value = owner.practical_estimator(supplied)
            if role == 'launch_api':
                assert type(value) is PracticalYieldEstimator
                record = value.as_record()
                return {'record': record, 'proof_result': value.verify_completion({'status': 'invalid'})}
            return value
        result['estimator_failure' if fail else 'estimator_return'] = {'outcome': capture(estimator), 'events': list(events)}
    return result


@pytest.mark.parametrize('home,role', HOMES)
def test_private_native_inputs_and_estimator_preserve_original_outcomes(home, role):
    golden = json.loads((Path(__file__).parent / 'fixtures/organization_original/a107_native_input_yield_baseline.json').read_text())
    assert observations(home, role) == golden['observations'][home]
