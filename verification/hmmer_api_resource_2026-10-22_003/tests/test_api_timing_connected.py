"""Joined caller/HTTP/episode evidence, with explicit engineering decisions.

No public provider, configured model or native job runs. The HTTP response,
continuation counts and decisions are fixtures; all custody, typed delivery,
received-information projection and journal consumers are actual application code.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
import threading
from types import SimpleNamespace

from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import bind_assembled_services_with_public_search_timing
from gene_annotation_episode.communication import plain
from gene_annotation_episode.resource_estimation import ResourceToolEstimator, recorded_api_forecasts
from gene_annotation_episode.resource_episodes import RESULTS_VERSION
from gene_annotation_episode.run_statistics import RunHistory
import test_hmmer_api_connected as connected
from test_hmmer_api_progress import LocalHmmerClient, REMOTE
from test_resource_receipt_runtime import observations, own, resource_episode
from test_resource_service_setup import resources
from test_runtime import ScriptedProvider, obj


@contextmanager
def reported_service():
    state = SimpleNamespace(calls=[], elapsed=2.75)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def respond(self, body):
            raw = json.dumps(body).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state.calls.append(('POST', self.path, body))
            self.respond({'id': REMOTE})

        def do_GET(self):
            state.calls.append(('GET', self.path, None))
            if self.path.startswith('/result/'):
                self.respond({'status': 'SUCCESS', 'result': {'stats': {
                    'id': REMOTE, 'algo': 'phmmer', 'database': 'fixture',
                    'elapsed': state.elapsed}, 'hits': []}})
            else:
                self.respond({'id': REMOTE, 'algo': 'phmmer', 'database': 'fixture',
                    'task': {'status': 'SUCCESS'}})

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield state, LocalHmmerClient('http://127.0.0.1:' + str(server.server_address[1]))
    finally:
        server.shutdown()
        server.server_close()
        worker.join(10)


def test_prechoice_forecasts_result_return_parent_use_and_original_history(resources, tmp_path, monkeypatch):
    r = resources
    history_path = tmp_path / 'shared-statistics.sqlite3'
    history = RunHistory(history_path)
    history.close()
    r.estimator = ResourceToolEstimator.with_reported_results()
    def explicit_factory(store, **operands):
        return bind_assembled_services_with_public_search_timing(store, api_timing=timing, **operands)

    monkeypatch.setattr(connected, 'bind_assembled_services_with_public_search', explicit_factory)
    with reported_service() as (http, client):
        timing = ApiTimingBinding(ledger_path=tmp_path / 'api-timing.sqlite3',
            history_path=history_path, resource_id=connected.registry(client)['resource_id'],
            monitoring_information_unit=connected.MONITOR)
        initial_forecasts = []

        def select_api(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['status'] == 'no_matching_history'
            assert forecast['reported_result_support'] == {'reported_result_count': 0}
            assert not http.calls
            assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 0
            initial_forecasts.append(deepcopy(forecast))
            return connected.api_child(r, h.workflow)

        def select_submit(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['status'] == 'no_matching_history'
            assert not http.calls
            assert r.store.db.execute('SELECT count(*) FROM provider_jobs').fetchone()[0] == 1
            return own('api_search.submit', retry_of=None)

        h = connected.host(r, tmp_path / 'runtime', client,
            script=[select_api, select_submit, own('api_search.check_handoff'),
                own('resource.capabilities')], counts={'annotation': 2})
        launch, boundary = resource_episode(h, r, 'launch', r.launch)
        record = asyncio.run(launch.run_async(boundary))
        asyncio.run(launch.build_result(record))
        handoff = json.loads(r.journal.row('runtime_forms', launch.source.episode_id)['form'])['handoff']
        assert record.units_consumed == 2
        assert [call[0] for call in http.calls] == ['POST', 'GET']

        timing_schema = h.workflow.report_sources('results')['api_execution_measurements']['report_schema']
        return_schema = obj({'timing': deepcopy(timing_schema)})
        assignment = {'version': RESULTS_VERSION, 'handoff': handoff,
            'requested_data_selector': {'version': 'public_search_result_selector_v1',
                'provider': 'hmmer', 'first_page': 1, 'last_page': 2, 'page_size': 2}}

        def select_results(_context):
            return {'selection': {'kind': 'episode_child', 'role': 'results',
                'goal': 'Obtain only the original assigned fixture result pages', 'scope': r.scope,
                'purpose': 'Return only the source-qualified reported duration',
                'schema_json': json.dumps(return_schema), 'initial_report_json': '{}',
                'assignment': assignment}, 'report_update': {}}

        parent_use = []

        def use_return(context):
            child_form, = context['child_reports']
            fact, = child_form['timing']
            assert fact['elapsed_seconds'] == http.elapsed
            assert fact['observation_unit'] == 'logical_provider_job_reported_result'
            assert fact['duration_measure'] == 'hmmer_reported_search_elapsed_seconds'
            assert fact['job_ref'] == handoff['execution_handle']
            assert context['current_credit'] == 0
            assert context['monitoring_information_credit'] == connected.MONITOR
            parent_use.append(deepcopy(fact))
            return own('episode.history', view='records', decision_indices=[0])

        provider = ScriptedProvider([select_results, own('api_search.acquire', page=1),
            own('api_search.acquire', page=2), use_return])
        h.workflow.provider = provider
        parent = h.owner
        parent_record = asyncio.run(parent.run_async(h.workflow.context))
        asyncio.run(parent.build_result(parent_record))
        assert parent_record.units_consumed == 2 and len(parent_use) == 1
        assert [call[0] for call in http.calls] == ['POST', 'GET', 'GET', 'GET']
        acquired_sources = [row for row in r.store.list('source')
            if row.get('provider') == 'fixture_hmmer' and '/result/' in (row.get('uri') or '')]
        assert acquired_sources and all(row['version'] is None for row in acquired_sources)
        child_row = next(row for row in r.store.db.execute('SELECT * FROM runtime_episodes')
            if json.loads(row['path'])[-1][0] == 'results')
        child_id = child_row['episode_id']
        child_form = json.loads(r.journal.row('runtime_forms', child_id)['form'])
        assert child_form == {'timing': parent_use}
        assert len(observations(r, child_id)) == 2
        assert len(observations(r, parent.source.episode_id)) == 2
        child_path = tuple(tuple(part) for part in json.loads(child_row['path']))
        assert h.controllers[child_path].scores == [0, 0]
        assert h.controllers[parent.source.path].scores == [0, 0]
        assert h.workflow.source_credit_view(parent.source)['monitoring_information_credit'] == connected.MONITOR
        assert r.store.count('assessment') == r.store.count('annotation') == 0
        with sqlite3.connect(history_path) as db:
            assert db.execute('SELECT count(*) FROM reported_result_statistics').fetchone()[0] == 1
            assert db.execute('SELECT count(*) FROM run_statistics').fetchone()[0] == 0
        receipt = r.store.db.execute('SELECT receipt_kind FROM runtime_record_receipts '
            'WHERE episode_id=? AND record_ref=?',
            (parent.source.episode_id, parent_use[0]['receipt_ref'])).fetchone()
        assert receipt[0] == 'child_form'
        before = deepcopy(observations(r, parent.source.episode_id))
        h.workflow.receive_form(parent.source, child_form, return_schema, 0, redelivery=True)
        assert observations(r, parent.source.episode_id) == before
        assert h.workflow.source_credit_view(parent.source)['monitoring_information_credit'] == connected.MONITOR

        def use_future_forecast(context):
            forecast, = context['api_reported_execution_forecasts']
            assert forecast['expected_total_seconds'] == http.elapsed
            assert forecast['reported_result_support'] == {'reported_result_count': 1}
            assert forecast['outcome_support'] is None
            assert forecast['job_ref'] is None and forecast['sample_ref'] is None
            assert forecast['elapsed_seconds'] is None
            return own('resource.capabilities')

        h.workflow.provider = ScriptedProvider([use_future_forecast, use_future_forecast])
        future, future_boundary = resource_episode(h, r, 'launch', plain(r.launch), key='later-launch')
        future_record = asyncio.run(future.run_async(future_boundary))
        asyncio.run(future.build_result(future_record))
        assert future_record.units_consumed == 2
        assert [call[0] for call in http.calls] == ['POST', 'GET', 'GET', 'GET']
        original = json.loads(r.store.db.execute('SELECT request FROM runtime_model_calls '
            'WHERE episode_id=? ORDER BY call_index LIMIT 1', (launch.source.episode_id,)).fetchone()[0])
        assert original['context']['api_reported_execution_forecasts'] == initial_forecasts
        recorded = recorded_api_forecasts(r.store, run_id=r.run_id, episode_id=future.source.episode_id)
        assert len(recorded) == 1 and recorded[0]['expected_total_seconds'] == http.elapsed
