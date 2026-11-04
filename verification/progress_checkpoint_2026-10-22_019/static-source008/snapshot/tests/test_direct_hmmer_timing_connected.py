"""Joined ordinary-search custody and episode receipt tests with scripted choices.

Only an explicitly bound loopback HTTP fixture runs. These checks establish
application behavior, not configured-model science or public-service deployment.
"""
import asyncio
from contextlib import closing
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning_direct,
)
from gene_annotation_episode.direct_hmmer_timing import DIRECT_MODE
from gene_annotation_episode.state import Store
import test_api_execution_planning_connected as planning
from test_api_execution_planning_connected import (
    close, estimate_arguments, planning_host, synthetic_ap_source,
)
from test_api_timing_connected import reported_service
from test_hmmer_api_connected import MONITOR
from test_resource_receipt_runtime import observations, own
from test_resource_service_setup import resources
from test_runtime import obj


def direct_host(r, directory, client, monkeypatch, **arguments):
    """Reuse the existing actual Workflow fixture with explicit direct setup."""
    from gene_annotation_episode.resource_episodes import HomologyResourceAdapter
    def native_capability(adapter):
        return {'resource_id': adapter.resource_id, 'kind': 'local', 'availability': 'unknown',
            'observed_at': '2026-10-22T00:00:00+00:00', 'provenance_refs': [],
            'knowledge_entry_ids': [], 'tool_names': []}
    monkeypatch.setattr(HomologyResourceAdapter, 'capability', native_capability)
    def setup(store, **operands):
        return bind_assembled_services_with_public_search_timing_planning_direct(
            store, ordinary_hmmer_timing=deepcopy(DIRECT_MODE), **operands)
    monkeypatch.setattr(planning,
        'bind_assembled_services_with_public_search_timing_planning', setup)
    return planning_host(r, directory, client, **arguments)


def assert_final_owners(h):
    direct = h.tools.api_direct_hmmer_timing
    planner = h.tools.api_execution_planner
    adapter = next(a for a in h.workflow.episode_bindings.for_role('launch').adapters.values()
        if a.capability()['kind'] == 'api')
    assert direct.planner is planner
    assert direct.reader is h.workflow.api_timing_reader is adapter.timing_reader
    assert planner.ports is direct.reader.ports is adapter.ports
    assert planner.timing is direct.reader.ledger is adapter.timing
    assert planner.store is adapter.store is h.tools.store is h.workflow.store
    assert planner.ports.operations.remote_searches is h.tools.remote_searches
    assert adapter.as_record()['version'] == 'hmmer_service_resource_adapter_v4'
    return direct


def test_scientific_child_direct_search_returns_one_timing_fact_and_future_forecast(
        resources, tmp_path, monkeypatch):
    r = resources
    source = synthetic_ap_source(tmp_path / 'synthetic-options')
    initial, received, later = [], [], []
    with reported_service() as (http, client):
        def first_estimate(context):
            assert not http.calls and 'api_execution_proposal' not in context
            return own('execution.estimate', **estimate_arguments(h, r))

        def commission(context):
            proposal = deepcopy(context['api_execution_proposal'])
            assert proposal['api_reported_execution_forecasts'][0][
                'reported_result_support'] == {'reported_result_count': 0}
            assert not http.calls
            initial.append(proposal)
            library = h.workflow.scientific_process_binding.library
            schema = obj({'timing': deepcopy(h.workflow.report_sources(
                'scientific_process')['api_execution_measurements']['report_schema'])})
            return {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
                'goal': 'Obtain the selected fixture sequence comparison', 'scope': r.scope,
                'purpose': 'Return only the original source-qualified search duration',
                'schema_json': json.dumps(schema), 'initial_report_json': '{}',
                'assignment': {'selection': {'version': 'scientific_process_selection_v2',
                    'annotation_ref': library.reference('A01'),
                    'thought_ref': library.reference('P01'),
                    'tools': ['public.hmmer.search']},
                    'evidence_refs': list(r.scope['subject_refs']),
                    'constraints': {'target_only': True},
                    'context': {'search_arguments': deepcopy(proposal['arguments'])}}},
                'report_update': {}}

        def child_search(context):
            assert 'scientific_process' in context
            assert context['controller']['scores'] == []
            assert context['monitoring_information_credit'] == 0
            assert not http.calls
            return own('public.hmmer.search', **context['scientific_process'][
                'assignment']['context']['search_arguments'])

        def child_after_search(context):
            assert context['last_local_outcome']['status'] == 'completed'
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == MONITOR
            assert len(context['last_local_outcome']['api_timing_refs']) == 1
            return own('episode.history', view='records', decision_indices=[0])

        def parent_receives(context):
            form, = context['child_reports']
            fact, = form['timing']
            assert set(form) == {'timing'}
            assert fact['elapsed_seconds'] == http.elapsed
            assert fact['observation_unit'] == 'logical_provider_job_reported_result'
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == MONITOR
            assert context['api_execution_proposal'] == initial[0]
            received.append(deepcopy(form))
            return own('execution.estimate', **estimate_arguments(h, r))

        def parent_uses_future(context):
            proposal = context['api_execution_proposal']
            forecast, = proposal['api_reported_execution_forecasts']
            assert forecast['reported_result_support'] == {'reported_result_count': 1}
            assert forecast['expected_total_seconds'] == http.elapsed
            assert forecast['outcome_support'] is None
            assert forecast['job_ref'] is forecast['sample_ref'] is None
            later.append(deepcopy(proposal))
            return own('episode.history', view='records', decision_indices=[0, 1])

        h = direct_host(r, tmp_path / 'first-run', client, monkeypatch,
            source_directory=source, counts={'annotation': 4, 'scientific_process': 2},
            script=[first_estimate, commission, child_search, child_after_search,
                    parent_receives, parent_uses_future])
        assert_final_owners(h)
        record = close(h)
        assert record.units_consumed == 4 and len(received) == len(later) == 1
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
        parent_id = h.owner.source.episode_id
        child = r.store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? "
            "AND json_extract(path,'$[#-1][0]')='scientific_process'", (r.run_id,)).fetchone()
        child_id = child['episode_id']
        child_path = tuple(tuple(v) for v in json.loads(child['path']))
        assert len(observations(r, parent_id)) == 4
        assert len(observations(r, child_id)) == 2
        assert h.controllers[h.owner.source.path].scores == [0] * 4
        assert h.controllers[child_path].scores == [0] * 2
        fact = received[0]['timing'][0]
        receipt = r.store.db.execute('SELECT receipt_kind FROM runtime_record_receipts '
            'WHERE run_id=? AND episode_id=? AND record_ref=?',
            (r.run_id, parent_id, fact['receipt_ref'])).fetchone()
        assert receipt[0] == 'child_form'
        child_form = json.loads(r.store.db.execute('SELECT form FROM runtime_forms '
            'WHERE run_id=? AND episode_id=?', (r.run_id, child_id)).fetchone()[0])
        assert child_form == received[0]
        before = deepcopy(observations(r, parent_id))
        original_request = r.journal.row('runtime_model_calls', parent_id, 1)['request']
        original_action = r.journal.row('runtime_actions', parent_id, 0)['result']
        schema = json.loads(child['request'])['report_contract']['measurements']['schema']
        h.workflow.receive_form(h.owner.source, child_form, schema, 1, redelivery=True)
        assert observations(r, parent_id) == before
        assert h.workflow.source_credit_view(h.owner.source)[
            'monitoring_information_credit'] == MONITOR
        assert r.store.count('assessment') == r.store.count('annotation') == 0
        with closing(sqlite3.connect(h.timing.history_path)) as db:
            assert db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0] == 1
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 0

        # A separate explicit run receives only the compatible typed history.
        def other_estimate(context):
            assert context['controller']['scores'] == []
            assert 'api_execution_proposal' not in context
            return own('execution.estimate', **estimate_arguments(second, other))
        def other_uses(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['reported_result_support'] == {'reported_result_count': 1}
            assert forecast['expected_total_seconds'] == http.elapsed
            assert context['monitoring_information_credit'] == 0
            return own('episode.history', view='records', decision_indices=[0])
        with Store(tmp_path / 'second-workspace') as other_store:
            other = SimpleNamespace(**{**vars(r), 'store': other_store,
                'run_id': 'different-direct-timing-fixture-run'})
            second = direct_host(other, tmp_path / 'second-run', client, monkeypatch,
                source_directory=source, counts={'annotation': 2},
                script=[other_estimate, other_uses])
            assert_final_owners(second)
            assert close(second).units_consumed == 2
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
        assert h.workflow.journal.row('runtime_model_calls', parent_id, 1)['request'] == original_request
        assert h.workflow.journal.row('runtime_actions', parent_id, 0)['result'] == original_action
        assert json.loads(original_request)['context']['api_execution_proposal'] == initial[0]


def test_failed_ordinary_science_retains_timing_but_no_observation_then_selected_collect(
        resources, tmp_path, monkeypatch):
    r = resources
    seen = []
    with reported_service() as (http, client):
        def selected_search(_context):
            return own('public.hmmer.search', **estimate_arguments(h, r)['arguments'])
        def after_failure(context):
            failure = context['last_local_outcome']
            assert failure['status'] == 'failed' and failure['record_refs'] == []
            assert failure['feedback']['code'] == 'adapter_execution_failed'
            assert len(failure['api_timing_refs']) == 1
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == MONITOR
            assert context['controller']['scores'] == []
            monkeypatch.setattr(h.tools, '_perform', perform)
            job, = r.store.db.execute('SELECT id FROM provider_jobs').fetchall()
            seen.append(job[0])
            return own('public.hmmer.collect', job_ref=job[0])
        def after_collect(context):
            assert context['last_local_outcome']['status'] == 'completed'
            assert context['monitoring_information_credit'] == MONITOR
            assert context['current_credit'] == 0
            return own('episode.history', view='records', decision_indices=[0, 1])
        h = direct_host(r, tmp_path / 'failure-run', client, monkeypatch,
            counts={'annotation': 2}, script=[selected_search, after_failure, after_collect])
        perform = h.tools._perform
        def fail_science(name, *args, **kwargs):
            if name == 'public.hmmer.search':
                raise RuntimeError('isolated fixture failure before any scientific publication')
            return perform(name, *args, **kwargs)
        monkeypatch.setattr(h.tools, '_perform', fail_science)
        assert close(h).units_consumed == 2 and len(seen) == 1
        assert [c[0] for c in http.calls] == ['POST', 'GET', 'GET']
        rows = r.store.db.execute('SELECT result,credit FROM runtime_actions '
            'WHERE run_id=? AND episode_id=? ORDER BY decision_index',
            (r.run_id, h.owner.source.episode_id)).fetchall()
        assert len(rows) == 3 and rows[0]['credit'] is None
        failed, collected = [json.loads(row['result']) for row in rows[:2]]
        assert failed['status'] == 'failed' and failed['record_refs'] == []
        assert collected['status'] == 'completed'
        assert failed['api_timing_refs'] == collected['api_timing_refs']
        assert len(observations(r, h.owner.source.episode_id)) == 2
        assert h.controllers[h.owner.source.path].scores == [0, 0]
        assert h.workflow.source_credit_view(h.owner.source)[
            'monitoring_information_credit'] == MONITOR
        assert r.store.count('native_execution') == 0
