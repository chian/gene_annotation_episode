"""Actual native yield methods with controlled delegate and verifier ports.

Owner constructors are bypassed. Compact records select the existing estimator
branch; they are not represented as validated scientific assignments.
"""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a110'
PREFIXES = ('', 'hpc_work_planning', 'hpc_work_planning/hpc_allocation_execution',
    'scientific_process', 'scientific_process/hpc_work_planning', 'scientific_process/hpc_work_planning/hpc_allocation_execution')
HOMES = [('/'.join(filter(None, (prefix, 'execution_job_submission', child))), role)
    for prefix in PREFIXES for child, role in (('local_job_execution', 'launch_local'), ('hpc_job_execution', 'launch_hpc'))]


def observations(home, role):
    from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import BindingContext
    from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import ASSIGNMENT_VERSION
    from gene_annotation_episode.episodic_workflow.root.a110.practical_yield import PracticalYieldEstimator
    owner_class = importlib.import_module(AXIS + '.' + home.replace('/', '.') + '.episode').ExecutionEpisode
    owner = object.__new__(owner_class)
    assert owner.roles == (role,)
    result = {}
    for compact in (False, True):
        for fail in (False, True):
            events = []
            assignment = {'version': ASSIGNMENT_VERSION} if compact else {'controlled': 'original-assignment'}
            supplied = BindingContext('controlled-run', 'controlled-episode', role,
                (('launch', 'original-parent'), (role, 'original-child')), {'subject_refs': []}, assignment, {})
            def practical(context):
                assert context is supplied
                events.append('practical_context')
                return context
            def delegated(context):
                assert context is supplied
                events.append('delegate.estimator')
                if fail: raise ValueError('controlled_delegate_estimator_failure')
                return {'original_delegate': role}
            def delegate(context):
                assert context is supplied
                events.append('delegate')
                return SimpleNamespace(practical_estimator=delegated)
            def verify(context, proof):
                assert context is supplied and proof == {'status': 'invalid'}
                events.append('verify_completion')
                if fail: raise ValueError('controlled_original_verifier_failure')
                return False
            owner._practical_context, owner._delegate, owner.verify_completion = practical, delegate, verify
            try:
                value = owner.practical_estimator(supplied)
                if compact:
                    assert type(value) is PracticalYieldEstimator
                    value = {'record': value.as_record(), 'proof_result': value.verify_completion({'status': 'invalid'})}
                outcome = {'value': value}
            except (ValueError, TypeError, KeyError) as error:
                outcome = {'exception': type(error).__module__ + '.' + type(error).__name__, 'message': str(error)}
            result[('compact' if compact else 'delegated') + ('_failure' if fail else '_return')] = {'outcome': outcome, 'events': events}
            assert events == (['practical_context', 'verify_completion'] if compact else ['practical_context', 'delegate', 'delegate.estimator'])
            if fail:
                assert outcome['exception'] == 'builtins.ValueError'
            elif compact:
                assert outcome['value']['proof_result'] is False
            else:
                assert outcome['value'] == {'original_delegate': role}
    return result


@pytest.mark.parametrize('home,role', HOMES)
def test_private_native_yield_preserves_original_outcomes(home, role):
    golden = json.loads((Path(__file__).parent / 'fixtures/organization_original/a110_native_yield_baseline.json').read_bytes())
    assert observations(home, role) == golden['observations'][home]
