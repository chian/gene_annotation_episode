"""Typed API timing integration fixtures; no model, public service or native jobs."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_timing_information import (
    API_MEASUREMENT_SCHEMA, ApiReportedTimingFactReader, ReceivedExecutionTimingInformation)
from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import bind_assembled_services_with_public_search_timing
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.native_timing_information import NativeTimingInformation, record_native_measurement
from gene_annotation_episode.resource_episodes import RESULTS_VERSION
from gene_annotation_episode.resource_estimation import ResourceToolEstimator, reported_report_source
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.runtime import ActionFailure
from test_hmmer_api_connected import host, MONITOR
import test_hmmer_api_connected as connected
from test_hmmer_api_operations import FixtureClient, JOB, snapshot
from test_resource_service_setup import resources
from test_resource_receipt_runtime import resource_episode, own, FORM
from test_runtime import ScriptedProvider, obj


class TimingClient(FixtureClient):
    def hmmer_result(self, job_id, **kwargs):
        self.calls.append(('result', job_id, kwargs))
        return snapshot({'status': 'SUCCESS', 'page_count': 2, 'result': {'stats': {
            'id': JOB, 'algo': 'phmmer', 'database': getattr(self, 'result_database', 'fixture'),
            'elapsed': 18.5}, 'hits': []}})


def timing_host(r, path, monkeypatch, *, script=(), counts=None, native=None):
    from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
    def native_capability(adapter):
        return {'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
            'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
            'knowledge_entry_ids': [], 'tool_names': []}
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', native_capability)
    history = path.parent/'reported-history.sqlite'
    if not history.exists():
        RunHistory(history).close()
    binding = ApiTimingBinding(ledger_path=path.parent/'timing.sqlite', history_path=history,
        resource_id='fixture_hmmer_resource', monitoring_information_unit=MONITOR)
    def services(store, **operands):
        return bind_assembled_services_with_public_search_timing(store, api_timing=binding, **operands)
    monkeypatch.setattr(connected, 'bind_assembled_services_with_public_search', services)
    r.estimator = ResourceToolEstimator.with_reported_results()
    client = TimingClient()
    h = host(r, path, client, script=script, counts=counts)
    api = next(a for a in h.workflow.episode_bindings.for_role('launch_api').adapters.values()
        if a.capability()['kind'] == 'api')
    return SimpleNamespace(**vars(h), api=api, client=client, timing_binding=binding)


def launch_and_handoff(h, r):
    h.client.state = 'SUCCESS'
    context_parent, _ = resource_episode(h, r, 'launch', r.launch)
    assignment = h.api.prepare_assignment(h.workflow.binding_context(context_parent.source), 'launch_api',
        {**r.launch, 'resource_selection': h.api.information.selection()}, r.scope, r.run_id+':order')
    child, boundary = resource_episode(h, r, 'launch_api', assignment)
    h.workflow.provider = ScriptedProvider([own('api_search.submit', retry_of=None), own('api_search.check_handoff')])
    record = asyncio.run(child.run_async(boundary))
    asyncio.run(child.build_result(record))
    return json.loads(h.workflow.journal.row('runtime_forms', child.source.episode_id)['form'])['handoff']


def result_assignment(handoff):
    return {'version': RESULTS_VERSION, 'handoff': handoff,
        'requested_data_selector': {'version': 'public_search_result_selector_v1', 'provider': 'hmmer',
            'first_page': 1, 'last_page': 2, 'page_size': 2}}


def timing_form(*, forecasts=False):
    fields = {'science': {'type': 'number', 'x-source': 'credit'},
        'monitoring': {'type': 'number', 'x-source': 'monitoring_information_credit'},
        'durations': {'type': 'array', 'items': deepcopy(API_MEASUREMENT_SCHEMA), 'x-source': 'api_execution_measurements'}}
    if forecasts:
        fields['forecasts'] = reported_report_source()['report_schema']
    return obj(fields)


def test_prechoice_forecasts_are_separate_original_snapshots_and_do_not_enter_waits(resources, tmp_path, monkeypatch):
    r = resources
    h = timing_host(r, tmp_path/'forecast', monkeypatch)
    parent, _ = resource_episode(h, r, 'launch', r.launch, schema=timing_form(forecasts=True))
    bound = h.workflow.binding_context(parent.source)
    values = h.workflow.specialist(parent.source).decision_context(bound, None)
    from method_loop.durable import DurableExecutionError
    from gene_annotation_episode.hmmer_resource_adapter import HmmerServiceResourceAdapter
    original_reader = h.workflow.api_timing_reader
    saved_owner = original_reader.ledger.as_record()
    reopened_ports = h.workflow.services.public_search_ports(h.registry, timing=saved_owner)
    reopened = ApiReportedTimingFactReader(reopened_ports.operations.timing, ports=reopened_ports)
    assert reopened.as_record() == original_reader.as_record()
    for mutate in ('store_path', 'registry', 'binding'):
        changed = deepcopy(saved_owner)
        if mutate == 'store_path':
            changed[mutate] = str(tmp_path/'foreign-workspace')
        elif mutate == 'registry':
            changed[mutate]['resource_id'] = 'foreign-resource'
        else:
            changed[mutate]['monitoring_information_unit'] *= 2
        with pytest.raises(DurableExecutionError):
            h.workflow.services.public_search_ports(h.registry, timing=changed)
    with pytest.raises(ValueError, match='unit_mismatch'):
        ReceivedExecutionTimingInformation(NativeTimingInformation(2*MONITOR), original_reader)
    with pytest.raises(ValueError, match='adapter_binding_mismatch'):
        HmmerServiceResourceAdapter(h.workflow.services, r.store, h.workflow.journal,
            ports=h.api.ports, timing=h.api.timing, resource_estimator=ResourceToolEstimator())
    forecast, = values['api_reported_execution_forecasts']
    capture, = values['api_reported_execution_expectations']
    option, = values['api_execution_options']
    assert forecast['job_ref'] is forecast['sample_ref'] is forecast['outcome_support'] is None
    assert forecast['reported_result_support'] == {'reported_result_count': 0}
    assert capture['status'] == 'available' and option['execution_class_ref'] == forecast['execution_class_ref']
    assert values['resource_tool_estimates'] == [] and h.client.calls == []
    assert r.store.db.execute('SELECT count(*) FROM public_search_orders').fetchone()[0] == 0
    context = {'pending_work': h.workflow.pending_work(parent.source), **values}
    support = h.workflow.waiting_support(parent.source, context)
    assert support['duration_expectations'] == []
    selected = h.api.prepare_assignment(bound, 'launch_api',
        {**r.launch, 'resource_selection': h.api.information.selection()}, r.scope, 'new-assigned-order')
    child, _ = resource_episode(h, r, 'launch_api', selected)
    second = h.api.decision_context(h.workflow.binding_context(child.source))
    assert second['api_execution_options'] == values['api_execution_options'] and h.client.calls == []
    # Execute the actual parent boundary. The existing controller fixture closes
    # after its declared two actions, preserving original completed contexts.
    parent, boundary = resource_episode(h, r, 'launch', r.launch, key='forecast-run', schema=timing_form(forecasts=True))
    h.workflow.provider = ScriptedProvider([own('resource.capabilities'), own('resource.capabilities')])
    record = asyncio.run(parent.run_async(boundary)); asyncio.run(parent.build_result(record))
    contexts = [json.loads(row[0]) for row in r.store.db.execute(
        'SELECT data FROM runtime_estimation_contexts WHERE episode_id=? ORDER BY decision_index', (parent.source.episode_id,))]
    calls = [json.loads(row[0])['context'] for row in r.store.db.execute(
        'SELECT request FROM runtime_model_calls WHERE episode_id=? ORDER BY call_index', (parent.source.episode_id,))]
    assert len(contexts) == 2
    assert contexts[0]['api_reported_execution_expectations'] == calls[0]['api_reported_execution_expectations']
    assert contexts[0]['api_reported_execution_forecasts_at_selection'] == calls[0]['api_reported_execution_forecasts']
    form = json.loads(h.workflow.journal.row('runtime_forms', parent.source.episode_id)['form'])
    assert parent.request.report_contract.admit(form, audit_identifiers=()).as_record() == form
    assert form['forecasts'][0]['estimate_ref'] == calls[-1]['api_reported_execution_forecasts'][0]['estimate_ref']


def test_actual_typed_return_receipt_baseline_redelivery_and_no_extra_score(resources, tmp_path, monkeypatch):
    r = resources
    h = timing_host(r, tmp_path/'typed-return', monkeypatch, counts={'annotation': 2, 'results': 2})
    handoff = launch_and_handoff(h, r)
    h.client.state = 'SUCCESS'
    form = timing_form()
    validate_closed_schema(form)
    selection = {'selection': {'kind': 'episode_child', 'role': 'results', 'goal': 'Acquire assigned result pages',
        'scope': r.scope, 'purpose': 'Return source-qualified search duration', 'schema_json': json.dumps(form),
        'initial_report_json': '{}', 'assignment': result_assignment(handoff)}, 'report_update': {}}
    seen = []
    def parent_followup(context):
        returned, = context['child_reports']
        assert returned['science'] == context['current_credit'] == 0
        assert returned['monitoring'] == context['monitoring_information_credit'] == MONITOR
        assert len(returned['durations']) == 1
        seen.append(deepcopy(returned))
        return own('episode.monitoring_information', limit=1, offset=0)
    h.workflow.provider = ScriptedProvider([selection, own('api_search.acquire', page=1),
        own('api_search.acquire', page=2), parent_followup])
    record = asyncio.run(h.owner.run_async(h.workflow.context)); asyncio.run(h.owner.build_result(record))
    assert record.units_consumed == 2 and seen
    assert len([call for call in h.client.calls if call[0] == 'result']) == 2
    details = h.workflow.execution_timing_information.read_details(r.store, r.scope,
        details_limit=0, details_offset=0, **h.workflow.timing_arguments(h.owner.source))
    assert details['reported_result_count'] == details['api_receipt_count'] == 1
    assert details['measured_attempt_count'] == details['native_receipt_count'] == 0
    assert details['credit'] == MONITOR and details['api_execution_measurements'] == []
    sources = h.workflow.report_sources('annotation')
    assert not {'api_timing_information_credit', 'reported_api_timing_information'} & sources.keys()
    assert sources['monitoring_information_credit'] == h.workflow.execution_timing_information.report_sources()['monitoring_information_credit']
    assert h.controllers[h.owner.source.path].scores == [0, 0]
    original_credit = h.workflow.source_credit_view(h.owner.source)
    attempt = r.store.db.execute('SELECT delivery_ref FROM runtime_report_attempts WHERE parent_episode_id=?',
        (h.owner.source.episode_id,)).fetchone()[0]
    delivered = h.workflow.redeliver(h.owner.source, {'delivery_ref': attempt,
        'purpose': 'Return the same original duration', 'schema_json': json.dumps(form)}, 2)
    assert delivered.failure is None and delivered.report.as_record() == seen[0]
    assert h.workflow.source_credit_view(h.owner.source) == original_credit
    source_ref = seen[0]['durations'][0]['receipt_ref']
    # A later child inherits the exact original duration as baseline.
    child, _ = resource_episode(h, r, 'results', h.api.prepare_assignment(
        h.workflow.binding_context(h.owner.source), 'results', result_assignment(handoff), r.scope, 'inherited-results'), key='inherited')
    assert h.workflow.source_credit_view(child.source)['monitoring_information_credit'] == 0
    assert source_ref in h.workflow.record_selection(child.source.episode_id)['initial_known_record_refs']


def test_failed_biology_keeps_timing_without_completing_failed_action(resources, tmp_path, monkeypatch):
    r = resources
    h = timing_host(r, tmp_path/'failed-publication', monkeypatch, counts={'results': 1})
    handoff = launch_and_handoff(h, r); h.client.state = 'SUCCESS'
    assigned = h.api.prepare_assignment(h.workflow.binding_context(h.owner.source), 'results', result_assignment(handoff), r.scope, 'results')
    episode, boundary = resource_episode(h, r, 'results', assigned, schema=timing_form())
    def fail(*args, **kwargs):
        raise ContractError('injected_biology_failure')
    monkeypatch.setattr(h.api.ports.result_publisher, 'publish', fail)
    def after_failure(context):
        assert context['last_local_outcome']['status'] == 'failed'
        assert context['monitoring_information_credit'] == MONITOR
        assert context['controller']['scores'] == [] and context['current_credit'] == 0
        return own('episode.monitoring_information', limit=1, offset=0)
    h.workflow.provider = ScriptedProvider([own('api_search.acquire', page=1), after_failure])
    record = asyncio.run(episode.run_async(boundary)); asyncio.run(episode.build_result(record))
    assert record.units_consumed == 1
    rows = r.store.db.execute('SELECT result,credit FROM runtime_actions WHERE episode_id=? ORDER BY decision_index',
        (episode.source.episode_id,)).fetchall()
    assert len(rows) == 2 and rows[0]['credit'] is None
    failed = json.loads(rows[0]['result'])
    assert len(failed['api_timing_refs']) == 1 and failed['record_refs'] == []
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
        (episode.source.episode_id,)).fetchone()[0] == 1


def test_reader_rejects_tampered_facts_and_cross_scope_references(resources, tmp_path, monkeypatch):
    r = resources
    h = timing_host(r, tmp_path/'fact-validation', monkeypatch, counts={'results': 1})
    h.client.result_database = {'id': 'fixture', 'version': 'synthetic-provider-metadata'}
    handoff = launch_and_handoff(h, r); h.client.state = 'SUCCESS'
    assigned = h.api.prepare_assignment(h.workflow.binding_context(h.owner.source), 'results', result_assignment(handoff), r.scope, 'results')
    episode, boundary = resource_episode(h, r, 'results', assigned, schema=timing_form())
    h.workflow.provider = ScriptedProvider([own('api_search.acquire', page=1)])
    record = asyncio.run(episode.run_async(boundary)); asyncio.run(episode.build_result(record))
    form = json.loads(h.workflow.journal.row('runtime_forms', episode.source.episode_id)['form'])
    row, = form['durations']
    h.workflow.validate_report(form, r.scope, schema=timing_form(), source=episode.source)
    wrong = deepcopy(form); wrong['durations'][0]['elapsed_seconds'] += 1
    with pytest.raises(ReportBoundaryError, match='differ from their source'):
        h.workflow.validate_report(wrong, r.scope, schema=timing_form(), source=episode.source)
    with pytest.raises(ValueError, match='outside_scope'):
        h.workflow.api_timing_reader.read_source(row['receipt_ref'], scope={'subject_refs': r.scope['subject_refs'],
            'segments': [{'target_ref': r.scope['subject_refs'][0], 'start': 0, 'end': 1, 'unit': 'aa'}]})
    source = r.store.get(row['receipt_ref'])
    original = r.store.get_artifact(source['artifact_ref'])
    body = json.loads(original); body['witness']['elapsed_seconds'] += 1
    # Fault injection preserves the source handle to prove body integrity is checked.
    from gene_annotation_episode.materials import artifact_path as material_path
    actual_path = material_path(r.store, source['artifact_ref'])
    actual_path.write_bytes(canonical(body).encode())
    with pytest.raises((ValueError, ContractError)):
        h.workflow.api_timing_reader.read_source(row['receipt_ref'], scope=r.scope)
    actual_path.write_bytes(original)
    # Explicit synthetic native receipt: this verifies typed set composition,
    # without starting a native process or claiming a measured fixture run.
    from gene_annotation_episode.execution_recording import NativeMeasurement
    from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic
    native_class = ExecutionClass('pairwise_sequence_alignment', 'local', 'native-fixture', None,
        'a'*64, 1024, 1024, None, 5, 5, 1, 'available')
    measured = NativeMeasurement(native_class, RunStatistic('b'*64, 'c'*64,
        '2026-10-22T00:00:00+00:00', 'succeeded', 'complete', 18.5, None), 'captured_before_submission')
    native_ref = record_native_measurement(r.store, measured, operation='align_pair', operands=[
        {'role': 'query', 'subject_ref': r.scope['subject_refs'][0]},
        {'role': 'reference', 'subject_ref': r.scope['subject_refs'][0]}])
    union = h.workflow.execution_timing_information
    details = union.read_details(r.store, r.scope, known_execution_refs=[native_ref, native_ref],
        initial_execution_refs=[], known_record_refs=[row['receipt_ref'], row['receipt_ref']],
        initial_known_record_refs=[], details_limit=1, details_offset=0)
    assert details['monitoring_information_credit'] == 2*MONITOR
    assert details['measured_attempt_count'] == details['reported_result_count'] == 1
    inherited = union.read_details(r.store, r.scope, known_execution_refs=[native_ref],
        initial_execution_refs=[native_ref], known_record_refs=[row['receipt_ref']],
        initial_known_record_refs=[row['receipt_ref']], details_limit=None, details_offset=0)
    assert inherited['credit'] == 0 and inherited['api_execution_measurements'] == inherited['native_execution_measurements'] == []


def test_unrequested_child_duration_source_does_not_enter_automatic_parent_state(resources, tmp_path, monkeypatch):
    r = resources
    h = timing_host(r, tmp_path/'unrequested', monkeypatch, counts={'annotation': 2, 'results': 1})
    handoff = launch_and_handoff(h, r)
    form = obj({'monitoring': {'type': 'number', 'x-source': 'monitoring_information_credit'}})
    selected = {'selection': {'kind': 'episode_child', 'role': 'results', 'goal': 'Acquire assigned result page',
        'scope': r.scope, 'purpose': 'Return only the requested scalar', 'schema_json': json.dumps(form),
        'initial_report_json': '{}', 'assignment': result_assignment(handoff)}, 'report_update': {}}
    def parent(context):
        assert context['child_reports'][0]['monitoring'] == MONITOR
        assert context['monitoring_information_credit'] == 0
        return own('episode.monitoring_information', limit=5, offset=0)
    h.workflow.provider = ScriptedProvider([selected, own('api_search.acquire', page=1), parent])
    record = asyncio.run(h.owner.run_async(h.workflow.context)); asyncio.run(h.owner.build_result(record))
    assert h.workflow.source_credit_view(h.owner.source)['monitoring_information_credit'] == 0
    assert not [ref for ref in h.workflow.record_selection(h.owner.source.episode_id)['known_record_refs']
        if r.store.get(ref).get('provider') == 'episode.hmmer_reported_timing']
    source_ref = next(row['id'] for row in r.store.list('source')
        if row.get('provider') == 'episode.hmmer_reported_timing')
    before = list(h.client.calls)
    explicit = h.workflow.build('annotation', 'explicit-source-read', 'Inspect an explicitly selected source', r.scope)
    def after_selected_read(context):
        assert context['monitoring_information_credit'] == MONITOR
        assert context['current_credit'] == 0
        assert context['last_local_outcome']['result']['records'][0]['id'] == source_ref
        return own('episode.monitoring_information', limit=1, offset=0)
    h.workflow.provider = ScriptedProvider([own('state.query', refs=[source_ref]), after_selected_read])
    closed = asyncio.run(explicit.run_async(h.workflow.context)); asyncio.run(explicit.build_result(closed))
    assert closed.units_consumed == 2 and h.client.calls == before


def test_opted_in_union_fact_precedence_preserves_native_specialist_fields(resources, tmp_path, monkeypatch):
    """Synthetic typed duration; no native process or native status read."""
    r = resources
    class OriginalMonitoring:
        include_handoff_checks = True
        information_roles = ('job_launch', 'job_results')
        def __call__(self, *args, **kwargs):
            return 0
        def information_view(self, *args, **kwargs):
            return {'monitoring_information_credit': 3, 'monitoring_findings': []}
    r.homology.monitoring_projector = OriginalMonitoring()
    r.homology.project_credit = lambda *args, **kwargs: 0
    h = timing_host(r, tmp_path/'specialist-precedence', monkeypatch)
    binding = h.workflow.episode_bindings.for_role('launch_local')
    native = next(a for a in binding.adapters.values() if a.capability()['kind'] == 'local')
    assignment = {**deepcopy(r.launch), 'job_request': {'query_ref': r.scope['subject_refs'][0], 'cpu': 1},
        'constraints': {'allowed_kinds': ['local']}, 'resource_selection': native._selection(1)}
    assigned = binding.prepare_assignment(h.workflow.binding_context(h.owner.source), 'launch_local',
        assignment, r.scope, 'native-order-only')
    episode, _ = resource_episode(h, r, 'launch_local', assigned, schema=timing_form())
    from gene_annotation_episode.execution_recording import NativeMeasurement
    from gene_annotation_episode.run_statistics import ExecutionClass, RunStatistic
    measured = NativeMeasurement(ExecutionClass('pairwise_sequence_alignment', 'local', 'native-fixture',
        None, 'a'*64, 1024, 1024, None, 5, 5, 1, 'available'),
        RunStatistic('e'*64, 'f'*64, '2026-10-22T00:00:00+00:00', 'succeeded', 'complete', 4, None),
        'captured_before_submission')
    reference = record_native_measurement(r.store, measured, operation='align_pair', operands=[
        {'role': 'query', 'subject_ref': r.scope['subject_refs'][0]},
        {'role': 'reference', 'subject_ref': r.scope['subject_refs'][0]}])
    h.workflow.receive_native_outcome(episode.source, {'native_execution_refs': [reference]}, 0)
    view = h.workflow.source_credit_view(episode.source)
    details = h.workflow.execution_timing_information.read_details(r.store, r.scope,
        details_limit=None, details_offset=0, **h.workflow.timing_arguments(episode.source))
    facts = h.workflow.facts(episode.source)
    assert view['credit'] == 0 and view['monitoring_information_credit'] == details['credit'] == MONITOR
    assert facts['monitoring_information_credit'] == view['monitoring_information_credit']
    assert facts['native_execution_measurements'] == details['native_execution_measurements']
    assert facts['job_ref'] == assigned['adapter_assignment']['job_ref']
    assert facts['job_cpu'] == 1 and facts['monitoring_findings'] == []
    assert h.client.calls == []
    assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
