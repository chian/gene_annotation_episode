"""Actual Store/Journal Homology fixture plus exact public/callback boundaries.

Reuses the preserved eighteen-case fixture. Calculator values below are
explicit test operands, never scientific projections or producer evidence.
"""
import asyncio
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a104.tests.test_homology_private import case, ROLES

TOOLS = {'job_launch': ('homology.environment', 'homology.configure', 'homology.stage',
    'homology.submit', 'homology.resume_start', 'homology.check_handoff'),
    'job_monitor': ('homology.sample',), 'job_results': ('homology.extract', 'homology.coverage', 'homology.errors')}

def source_for(case, role):
    return SimpleNamespace(**{**vars(case.source), 'path': ((role, 'controlled'),)})

def emit(record_property, value):
    record_property('original_homology_owner_boundary', json.dumps(value, sort_keys=True, allow_nan=False))

def test_public_goal_and_tool_contracts_preserve_foreign_role_reads(case, record_property):
    records = {}
    for role in ROLES:
        catalog = case.binding.catalog(source_for(case, role))
        assert tuple(row['name'] for row in catalog) == TOOLS[role]
        records[role] = {'goal': case.binding.instructions(role), 'tools': catalog}
        assert records[role]['goal']
    for role in ('unknown_job_role', []):
        expected = KeyError if isinstance(role, str) else TypeError
        with pytest.raises(expected): case.binding.instructions(role)
        with pytest.raises(expected): case.binding.catalog(source_for(case, role))
    emit(record_property, records)

def test_original_guarded_commissions_fact_schemas_and_optional_information(case, monkeypatch, record_property):
    def monitor(*args, **kwargs): return 3.
    monitor.include_handoff_checks = True
    monitor.information_roles = ROLES
    monitor.information_view = lambda *args, **kwargs: {'monitoring_information_credit': 7., 'monitoring_findings': {}}
    monitor.information_report_source = lambda: {'type': 'object', 'meaning': 'Controlled test information',
        'report_schema': {'type': 'object', 'x-source': 'monitoring_findings'}}
    monitor.report_source = lambda: {'type': 'object', 'meaning': 'Original optional scalar-report fixture'}
    monitor.as_record = lambda: {'version': 'explicit_homology_owner_test_monitor_v1'}
    monkeypatch.setattr(case.binding, 'monitoring_projector', monitor)
    scientific = {'type': 'object', 'properties': {'kind': {'const': 'scientific_child'}, 'goal': {'type': 'string'}}}
    records = {}
    for enabled in (False, True):
        monitor.include_handoff_checks = enabled
        schemas = case.binding.commission_schemas(scientific)
        assert len(schemas) == (2 if case.role == 'job_launch' else 1)
        assert all(value['properties']['role']['const'] == case.role for value in schemas)
        assert all('prior_checked_statuses' in value['properties'] for value in schemas) == (enabled or case.role == 'job_monitor')
        facts = {role: case.binding.fact_sources(role) for role in ROLES}
        assert all(facts[role] == {} for role in ROLES if role != case.role)
        assert ('job_checked_status' in facts[case.role]) == (case.role == 'job_launch')
        assert ('job_result_progress' in facts[case.role]) == (case.role == 'job_results')
        records[str(enabled)] = {'commissions': schemas, 'fact_sources': facts}
    for role in ROLES:
        if role == case.role: assert case.binding.credit_kind(role) == ('monitoring' if role == 'job_monitor' else 'operational')
        else:
            with pytest.raises(ValueError, match='unknown_job_episode_role'):
                case.binding.assign(case.store, role, {}, case.scope, operation_key='not-acquired')
            with pytest.raises(ValueError, match='unknown_job_episode_role'): case.binding.credit_kind(role)
    emit(record_property, records)

def test_original_scalar_operands_detachment_and_information_credit_order(case, monkeypatch, record_property):
    calls = []
    def scalar(store, *, role, assignment, episode_id, run_id):
        assert store is case.store and episode_id == case.source.episode_id and run_id == case.journal.run_id
        assert assignment == case.assignment and assignment is not case.assignment
        calls.append(['scalar', role]); assignment['fixture_mutation'] = True
        return {'credit': {'job_launch': 2., 'job_results': 4.}[role]}
    def monitor(store, *, role, assignment, episode_id, run_id):
        assert store is case.store and assignment == case.assignment and assignment is not case.assignment
        calls.append(['monitor', role]); assignment['fixture_mutation'] = True
        return 3.
    def information(store, *, assignment, episode_id, run_id):
        assert store is case.store and assignment == case.assignment
        calls.append(['information'])
        return {'monitoring_information_credit': 7., 'monitoring_findings': {'fixture': 'controlled'}}
    monkeypatch.setattr(case.binding, '_job_credit_calculator', scalar)
    monkeypatch.setattr(case.binding, 'monitoring_projector', monitor)
    records = {}
    for role, expected in zip(ROLES, (2., 3., 4.)):
        calls.clear()
        value = case.binding.initial_credit(case.store, role, case.assignment, case.source.episode_id, case.journal.run_id)
        assert value == expected and calls == [[('monitor' if role == 'job_monitor' else 'scalar'), role]]
        assert 'fixture_mutation' not in case.assignment
        records[role] = {'value': value, 'calls': deepcopy(calls)}
    monitor.include_handoff_checks = True; monitor.information_roles = ROLES; monitor.information_view = information
    for role, expected in zip(ROLES, (2., 7., 4.)):
        calls.clear(); value = case.binding.credit_view(source_for(case, role))
        assert value['credit'] == expected and value['monitoring_information_credit'] == 7.
        assert calls == ([['information']] if role == 'job_monitor' else [['information'], ['scalar', role]])
        records['information_' + role] = {'value': value, 'calls': deepcopy(calls)}
    calls.clear()
    with pytest.raises(ValueError, match='unknown_job_episode_role'):
        case.binding.initial_credit(case.store, 'unknown_job_role', case.assignment, case.source.episode_id, case.journal.run_id)
    assert calls == []
    monkeypatch.setattr(case.binding, '_job_credit_calculator', lambda *args, **kwargs: float('nan'))
    with pytest.raises(ValueError, match='finite_operational_credit_required'):
        case.binding.initial_credit(case.store, 'job_launch', case.assignment, case.source.episode_id, case.journal.run_id)
    emit(record_property, records)

def test_actual_unsubmitted_fact_reads_keep_all_public_source_roles(case, record_property):
    def normalize(value):
        if isinstance(value, dict): return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list): return [normalize(item) for item in value]
        if value == case.assignment['job_ref']: return '<ACTUAL_ASSIGNED_JOB>'
        if value == case.assignment['query_ref']: return '<ACTUAL_QUERY>'
        if value == case.jobs.config['registry_ref']: return '<ACTUAL_REGISTRY>'
        return value
    records = {}
    for role in (*ROLES, 'unknown_job_role'):
        facts = case.binding.facts(source_for(case, role))
        assert facts['job_ref'] == case.assignment['job_ref'] and facts['job_cpu'] == case.assignment['cpu']
        assert facts['job_handoff'] is None and facts['job_handoff_state'] == 'unavailable'
        assert facts['job_handoff_failure'] == 'job_not_submitted'
        assert ('job_checked_status' in facts) == (role == 'job_launch')
        assert ('job_result_progress' in facts) == (role == 'job_results')
        records[role] = normalize(facts)
    emit(record_property, records)

def test_original_bound_execute_callback_result_and_exception_identity(case, monkeypatch, record_property):
    calls, result = [], {'status': 'controlled_callback_result'}
    async def operation(source, name, arguments, *, operation_key):
        calls.append((source, name, arguments, operation_key)); return result
    monkeypatch.setattr(case.binding, '_execute', operation)
    records = []
    for role in ROLES:
        source, args = source_for(case, role), {'controlled': role}
        value = asyncio.run(case.binding.execute(source, TOOLS[role][0], args, operation_key='original-bound-callback'))
        assert value is result and calls[-1] == (source, TOOLS[role][0], args, 'original-bound-callback')
        assert calls[-1][0] is source and calls[-1][2] is args
        records.append({'role': role, 'tool': TOOLS[role][0], 'result_identity_preserved': True})
    events = []
    def bind_events(source, job_ref):
        assert source is case.source and job_ref == case.assignment['job_ref']
        events.append('bind')
    def targets(job_ref):
        assert job_ref == case.assignment['job_ref']; events.append('targets'); return []
    monkeypatch.setattr(case.binding, 'native_event_provider', SimpleNamespace(controlled='callback-postprocessing'))
    monkeypatch.setattr(case.binding, 'bind_job_native_events', bind_events)
    monkeypatch.setattr(case.jobs, 'native_event_targets', targets)
    # Original public callback results still enter their complete optional
    # postprocessing even if the injected callback accepts a foreign name.
    assert asyncio.run(case.binding.execute(case.source, 'homology.submit', {}, operation_key='controlled-postprocessing')) is result
    assert events == ['bind', 'targets'] and result['native_event_targets'] == []
    records.append({'foreign_callback_native_event_order': events})
    marker = RuntimeError('original_controlled_callback_failure')
    async def failed(*args, **kwargs): raise marker
    monkeypatch.setattr(case.binding, '_execute', failed)
    with pytest.raises(RuntimeError) as caught:
        asyncio.run(case.binding.execute(case.source, TOOLS[case.role][0], {}, operation_key='callback-failure'))
    assert caught.value is marker
    emit(record_property, records)

def test_original_report_validation_order_role_and_object_identity(case, monkeypatch, record_property):
    calls, value, schema = [], {'controlled': 'original-form'}, {'controlled': 'original-schema'}
    def sources(role, supplied):
        assert supplied is schema; calls.append(['sources', role])
    def recorded(form, assignment, *, store, schema):
        assert form is value and assignment is case.assignment and store is case.store
        calls.append(['recorded'])
    monkeypatch.setattr(case.binding, '_validate_role_return_sources', sources)
    monkeypatch.setattr(case.binding, '_validate_recorded_return', recorded)
    records = {}
    for role in ROLES:
        calls.clear()
        assert case.binding.validate_report(value, case.assignment, role=role, store=case.store, schema=schema) is None
        assert calls == [['sources', role], ['recorded']]; records[role] = deepcopy(calls)
    calls.clear()
    with pytest.raises(ValueError, match='homology_return_role_required'):
        case.binding.validate_report(value, case.assignment, role='unknown_job_role', store=case.store, schema=schema)
    assert calls == []
    marker = RuntimeError('original_first_report_boundary_failure')
    def rejected(*args): calls.append(['rejected']); raise marker
    monkeypatch.setattr(case.binding, '_validate_role_return_sources', rejected)
    with pytest.raises(RuntimeError) as caught:
        case.binding.validate_report(value, case.assignment, role=case.role, store=case.store, schema=schema)
    assert caught.value is marker and calls == [['rejected']]
    emit(record_property, records)

def test_actual_assigned_reference_keeps_original_query_scope_authority(case, record_property):
    reference = case.assignment['job_ref']
    assert case.binding.resolve(case.store, case.scope, reference, 'homology_job', assignment=case.assignment)
    assert not case.binding.resolve(case.store, {'subject_refs': []}, reference, 'homology_job', assignment=case.assignment)
    forged = {**case.assignment, 'query_ref': 'unrecorded-query'}
    assert not case.binding.resolve(case.store, case.scope, reference, 'homology_job', assignment=forged)
    emit(record_property, {'actual_assigned_reference': True, 'outside_original_scope': False, 'forged_query': False})


def _assert_unclassified_outer_callback(case, monkeypatch, record_property, *, boundary, outcome):
    # The original outer method has no source-role admission. Its supplied
    # bound callback runs first, before optional events/statistics processing.
    source = SimpleNamespace(**{key: value for key, value in vars(case.source).items() if key != 'path'})
    if boundary == 'unknown_role': source.path = (('unknown_job_role', 'controlled'),)
    else: assert boundary == 'missing_path' and not hasattr(source, 'path')
    monkeypatch.setattr(case.binding, 'statistics', None)
    monkeypatch.setattr(case.binding, 'native_event_provider', None)
    arguments, result, calls = {'controlled': boundary}, {'status': 'original_callback_identity'}, []
    marker = RuntimeError('original_unclassified_callback_failure')
    async def operation(selected, name, operands, *, operation_key):
        assert selected is source and operands is arguments
        assert name == 'controlled.callback' and operation_key == 'original-unclassified-callback'
        calls.append('invoked')
        if outcome == 'exception': raise marker
        assert outcome == 'return'
        return result
    monkeypatch.setattr(case.binding, '_execute', operation)
    coroutine = case.binding.execute(source, 'controlled.callback', arguments,
        operation_key='original-unclassified-callback')
    if outcome == 'exception':
        with pytest.raises(RuntimeError) as caught: asyncio.run(coroutine)
        assert caught.value is marker
    else: assert asyncio.run(coroutine) is result
    assert calls == ['invoked']
    emit(record_property, {'boundary': boundary, 'outcome': outcome,
        'actual_bound_callback_calls': 1, 'operand_and_result_or_exception_identity_preserved': True})


def test_unknown_source_role_preserves_original_outer_callback_return(case, monkeypatch, record_property):
    _assert_unclassified_outer_callback(case, monkeypatch, record_property, boundary='unknown_role', outcome='return')


def test_unknown_source_role_preserves_original_outer_callback_exception(case, monkeypatch, record_property):
    _assert_unclassified_outer_callback(case, monkeypatch, record_property, boundary='unknown_role', outcome='exception')


def test_missing_source_path_preserves_original_outer_callback_return(case, monkeypatch, record_property):
    _assert_unclassified_outer_callback(case, monkeypatch, record_property, boundary='missing_path', outcome='return')


def test_missing_source_path_preserves_original_outer_callback_exception(case, monkeypatch, record_property):
    _assert_unclassified_outer_callback(case, monkeypatch, record_property, boundary='missing_path', outcome='exception')
