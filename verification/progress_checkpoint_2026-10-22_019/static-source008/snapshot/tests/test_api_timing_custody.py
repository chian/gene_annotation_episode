"""Actual offline selected-operation custody; no public service or model calls."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
import sqlite3
import threading

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.api_reported_statistics import ApiReportedStatistics
from gene_annotation_episode.api_timing_records import (
    ApiTimingBinding, ApiTimingLedger, reported_result_identity)
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.provider_jobs import RemoteSearches
from gene_annotation_episode.public_search_operations import ProviderJobOperations
from gene_annotation_episode.public_search_publication import PublicSearchResultPublisher
from gene_annotation_episode.run_statistics import RunHistory
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_hmmer_api_operations import FixtureClient, JOB, registry, result_body, snapshot


class TimingClient(FixtureClient):
    def __init__(self, *, job_id=JOB, seconds=2.5):
        super().__init__()
        self.job_id, self.seconds, self.body = job_id, seconds, None
        self.omit_elapsed = False

    def hmmer_submit(self, query_fasta, **kwargs):
        self.calls.append(('submit', query_fasta, kwargs))
        self.entered.set(); self.release.wait(10)
        if self.submit_error:
            raise self.submit_error
        return snapshot({'id': self.job_id})

    def hmmer_status(self, job_id):
        self.calls.append(('status', job_id))
        return snapshot({'id': self.job_id, 'task': {'status': self.state}})

    def hmmer_result(self, job_id, **kwargs):
        self.calls.append(('result', job_id, kwargs))
        body = deepcopy(self.body) if self.body is not None else result_body(kwargs['page'])
        body['result']['stats'].setdefault('elapsed', self.seconds)
        body['result']['stats']['id'] = self.job_id
        if self.omit_elapsed:
            body['result']['stats'].pop('elapsed', None)
        return snapshot(body)


def build(path, *, history=True, client=None, parameters=None, bind=True, run_id='fixture_run'):
    path.mkdir(parents=True, exist_ok=True)
    store = Store(path/'workspace')
    problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
    client = client or TimingClient()
    reg = registry(client)
    binding = ApiTimingBinding(ledger_path=path/'timing.sqlite', history_path=path/'history.sqlite',
        resource_id=reg['resource_id'], monitoring_information_unit=0.25)
    if history:
        RunHistory(binding.history_path).close()
    statistics = ApiReportedStatistics(binding, registry=reg)
    ledger = ApiTimingLedger(store=store, run_id=run_id, registry=reg,
        binding=binding, statistics=statistics)
    ops = ProviderJobOperations(store, RemoteSearches(store, client), registry=reg,
        timing=ledger if bind else None)
    subject = problem['subject_refs'][0]
    order = ops.order(operation_key='order', provider='hmmer', subject_ref=subject,
        query_fasta=f'>{subject}\nMACDEFGH', algorithm='phmmer', database='swissprot',
        parameters=parameters or {}, page_size=2, scope={'subject_refs': [subject]})
    return store, client, ops, order, ledger


async def acquire(ops, order, client, *, key='result', page=1):
    await ops.submit_once(order['job_ref'], operation_key='submit')
    client.state = 'SUCCESS'
    await ops.status_once(order['job_ref'], operation_key='status')
    return await ops.result_once(order['job_ref'], operation_key=key, page=page, page_size=2)


def rows(ledger, table):
    with sqlite3.connect(ledger.binding.ledger_path) as db:
        return [json.loads(row[0]) for row in db.execute('SELECT data FROM '+table+' ORDER BY rowid')]


def shared_rows(ledger):
    with sqlite3.connect(ledger.binding.history_path) as db:
        return list(db.execute('SELECT data FROM reported_result_statistics'))


def test_actual_order_submit_result_preserve_ports_and_first_witness(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        assert client.calls == []
        assert set(order) == {'version', 'registry_ref', 'job_ref', 'order_operation_key',
            'request_sha256', 'request_ref', 'query_fasta_ref'}
        assert rows(ledger, 'api_timing_orders')[0]['scope'] == ops.open_scope(order['job_ref'])['scope']
        receipt = asyncio.run(acquire(ops, order, client))
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['state'] == 'available'
        witness = ledger.read_measurement(disposition['measurement_ref'])
        assert witness['elapsed_seconds'] == 2.5
        assert witness['observed_at'] == receipt['observed_at']
        assert witness['entity_sha256'] == ops.read_snapshot(receipt['receipt_ref']).sha256
        assert witness['acquisition_receipt_ref'] == receipt['receipt_ref']
        assert witness['start_context']['condition_capture'] == 'captured_before_submission'
        assert witness['start_context']['condition_ref'] is None
        assert set(receipt) == {'version', 'receipt_ref', 'operation_key', 'selection_sha256',
            'operation', 'registry_ref', 'job_ref', 'provider', 'request_sha256', 'observed_at',
            'outcome', 'state', 'provider_chronology', 'remote_id', 'snapshot_ref',
            'result_ready', 'result_cached', 'result_snapshot_refs', 'failure'}
        original = canonical(witness)
        calls = list(client.calls)
        cached = asyncio.run(ops.result_once(order['job_ref'], operation_key='cached', page=1, page_size=2))
        assert cached['observed_at'] != receipt['observed_at']
        assert ledger.receive_result(ops, cached['receipt_ref'])['measurement_ref'] == witness['measurement_ref']
        assert client.calls == calls
        asyncio.run(ops.result_once(order['job_ref'], operation_key='next_page', page=2, page_size=2))
        assert canonical(ledger.read_measurement(witness['measurement_ref'])) == original
        assert len(rows(ledger, 'api_timing_measurements')) == len(shared_rows(ledger)) == 1
        assert len(rows(ledger, 'api_timing_submission_intents')) == 1
        assert len(rows(ledger, 'api_timing_submission_bindings')) == 1
        assert ledger.retry_exports()['pending_count'] == 0
        # Ordinary scientific source projection remains independently usable.
        publisher = PublicSearchResultPublisher(store, ToolRegistry(store, clients=client), operations=ops)
        biology = publisher.publish(receipt['receipt_ref'], scope=ops.open_scope(order['job_ref'])['scope'], operation_key='biology')
        assert len(biology['result']['publication_rows']) == 2
        assert ledger.read_measurement(witness['measurement_ref']) == witness


def test_selected_not_sent_retry_keeps_each_original_condition_and_winning_receipt(tmp_path):
    async def run():
        store, client, ops, order, ledger = build(tmp_path)
        with store:
            history = RunHistory(ledger.binding.history_path, create=False)
            first_condition = history.set_condition(operation_sha256='1'*64, resource_id=ledger.binding.resource_id,
                state='degraded', reason='outage', reported_at='2026-10-22T12:00:00Z')
            client.submit_error = AcquisitionError('preflight_not_sent', submission_outcome='not_sent')
            failed = await ops.submit_once(order['job_ref'], operation_key='first')
            assert failed['failure']['submission_outcome'] == 'not_sent'
            second_condition = history.set_condition(operation_sha256='2'*64, resource_id=ledger.binding.resource_id,
                state='normal', reason='recovered', reported_at='2026-10-22T12:01:00Z')
            history.close()
            client.submit_error = None
            original_bind = ledger.bind_submission_receipt
            ledger.bind_submission_receipt = lambda *args: (_ for _ in ()).throw(OSError('cut after provider commit'))
            successful = await ops.submit_once(order['job_ref'], operation_key='retry', retry_of=failed['receipt_ref'])
            ledger.bind_submission_receipt = original_bind
            assert successful['outcome'] == 'completed'
            assert rows(ledger, 'api_timing_submission_bindings') == []
            intents = rows(ledger, 'api_timing_submission_intents')
            assert [i['submission_operation_key'] for i in intents] == ['first', 'retry']
            assert [i['start_context']['condition_ref'] for i in intents] == [first_condition, second_condition]
            ledger.statistics.capture_start = lambda *args: (_ for _ in ()).throw(AssertionError('recaptured condition'))
            assert await ops.submit_once(order['job_ref'], operation_key='first') == failed
            assert await ops.submit_once(order['job_ref'], operation_key='retry', retry_of=failed['receipt_ref']) == successful
            recovered = ops.recover_submission(order['job_ref'], operation_key='recover')
            assert recovered['outcome'] == 'completed'
            bound = rows(ledger, 'api_timing_submission_bindings')[0]
            assert bound['submission_receipt_ref'] == successful['receipt_ref']
            assert bound['submission_operation_key'] == 'retry'
            assert bound['intent_ref'] == intents[1]['intent_ref']
            client.state = 'SUCCESS'
            await ops.status_once(order['job_ref'], operation_key='ready')
            receipt = await ops.result_once(order['job_ref'], operation_key='result', page=1, page_size=2)
            witness = ledger.read_measurement(ledger.receive_result(ops, receipt['receipt_ref'])['measurement_ref'])
            assert witness['start_context']['condition_ref'] == second_condition
            assert witness['intent_ref'] == intents[1]['intent_ref']
            assert len(client.calls) == 4 and len(shared_rows(ledger)) == 1
    asyncio.run(run())


def test_no_retroactive_eligibility_for_existing_order(tmp_path):
    store, client, ops, order, ledger = build(tmp_path, bind=False)
    with store:
        ops.timing = ledger
        assert ops.order(operation_key='order', provider='hmmer', subject_ref=ops.inspect(order['job_ref'])['request']['subject_ref'],
            query_fasta=store.get_artifact(order['query_fasta_ref']).decode(), algorithm='phmmer', database='swissprot',
            page_size=2, scope=ops.open_scope(order['job_ref'])['scope']) == order
        receipt = asyncio.run(acquire(ops, order, client))
        assert ledger.receive_result(ops, receipt['receipt_ref'])['code'] == 'not_opted_in_order'
        assert rows(ledger, 'api_timing_orders') == rows(ledger, 'api_timing_submission_intents') == rows(ledger, 'api_timing_measurements') == []
        assert shared_rows(ledger) == [] and len(client.calls) == 3


@pytest.mark.parametrize('seconds', [-1, None, True, '2', float('nan'), float('inf')])
def test_invalid_elapsed_does_not_block_selected_result_or_biology(tmp_path, seconds):
    store, client, ops, order, ledger = build(tmp_path, client=TimingClient(seconds=seconds))
    with store:
        receipt = asyncio.run(acquire(ops, order, client))
        assert receipt['outcome'] == 'completed'
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['code'] == 'reported_duration_invalid'
        assert disposition['measurement_ref'] is None
        assert rows(ledger, 'api_timing_measurements') == shared_rows(ledger) == []
        publisher = PublicSearchResultPublisher(store, ToolRegistry(store, clients=client), operations=ops)
        # JSON NaN is not valid scientific source JSON either; timing adds no
        # new constraint and preserves the successful source custody receipt.
        if type(seconds) is not float or seconds == seconds and abs(seconds) != float('inf'):
            assert publisher.publish(receipt['receipt_ref'], scope=ops.open_scope(order['job_ref'])['scope'], operation_key='bio')['record_refs']


def test_missing_elapsed_qualified_identity_and_conflicting_later_page(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        receipt = asyncio.run(acquire(ops, order, client))
        original = rows(ledger, 'api_timing_measurements')[0]
        client.seconds = 99
        later = asyncio.run(ops.result_once(order['job_ref'], operation_key='conflict', page=2, page_size=2))
        disposition = ledger.receive_result(ops, later['receipt_ref'])
        assert later['outcome'] == 'completed'
        assert disposition['state'] == 'conflict' and disposition['code'] == 'reported_duration_conflict'
        assert disposition['measurement_ref'] == original['measurement_ref']
        assert ledger.read_measurement(original['measurement_ref']) == original
        assert len(shared_rows(ledger)) == 1
        client.body = result_body(3); client.body['result']['stats'].pop('database')
        missing = asyncio.run(ops.result_once(order['job_ref'], operation_key='missing_identity', page=3, page_size=2))
        assert missing['outcome'] == 'completed'
        conflict = ledger.receive_result(ops, missing['receipt_ref'])
        assert conflict['code'] == 'reported_duration_identity_conflict'
        assert conflict['measurement_ref'] == original['measurement_ref']
        assert len(rows(ledger, 'api_timing_measurements')) == 1


def test_missing_duration_preserves_custody_without_sample(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        client.omit_elapsed = True
        receipt = asyncio.run(acquire(ops, order, client))
        assert receipt['outcome'] == 'completed'
        assert ledger.receive_result(ops, receipt['receipt_ref'])['code'] == 'reported_duration_missing'
        assert rows(ledger, 'api_timing_measurements') == shared_rows(ledger) == []


@pytest.mark.parametrize('field', ['algo', 'database'])
def test_failed_foreign_identity_receipt_is_separate_from_unavailable_qualified_timing(tmp_path, field):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        original = asyncio.run(acquire(ops, order, client))
        first = rows(ledger, 'api_timing_measurements')[0]
        shared = shared_rows(ledger)
        client.body = result_body(2)
        client.body['result']['stats'][field] = 'foreign_value'
        failed = asyncio.run(ops.result_once(order['job_ref'], operation_key='foreign_identity', page=2, page_size=2))
        assert failed['outcome'] == 'failed'
        assert failed['failure']['code'] == 'remote_identity_conflict'
        disposition = ledger.receive_result(ops, failed['receipt_ref'])
        # The provider conflict is authoritative. A failed result cannot be a
        # qualified timing acquisition, even when its raw body had elapsed.
        assert disposition['state'] == 'unavailable'
        assert disposition['code'] == 'reported_duration_missing'
        assert disposition['measurement_ref'] is None
        assert rows(ledger, 'api_timing_measurements') == [first]
        assert shared_rows(ledger) == shared
        publisher = PublicSearchResultPublisher(store, ToolRegistry(store, clients=client), operations=ops)
        assert len(publisher.publish(original['receipt_ref'], scope=ops.open_scope(order['job_ref'])['scope'],
            operation_key='original_valid_biology')['result']['publication_rows']) == 2
        assert ledger.read_measurement(first['measurement_ref']) == first


def test_unknown_prepost_condition_never_becomes_observed_unspecified(tmp_path):
    store, client, ops, order, ledger = build(tmp_path, history=False)
    with store:
        receipt = asyncio.run(acquire(ops, order, client))
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['code'] == 'start_condition_unknown'
        original = ledger.read_measurement(disposition['measurement_ref'])
        assert original['start_context']['condition_capture'] == 'unavailable_before_submission'
        assert original['start_context']['condition_ref'] is None
        assert not ledger.binding.history_path.exists()
        RunHistory(ledger.binding.history_path).close()
        recovery = ledger.retry_exports()
        assert recovery['pending_count'] == recovery['unavailable_count'] == 1
        assert recovery['recorded_count'] == 0
        assert shared_rows(ledger) == []
        assert ledger.read_measurement(original['measurement_ref']) == original


def test_known_condition_export_storage_failure_then_recovery_without_work(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        original_export = ledger.statistics.export
        ledger.statistics.export = lambda witness: (_ for _ in ()).throw(OSError('export storage unavailable'))
        receipt = asyncio.run(acquire(ops, order, client))
        first = rows(ledger, 'api_timing_measurements')[0]
        assert rows(ledger, 'api_timing_export_dispositions') == []
        assert shared_rows(ledger) == []
        calls = list(client.calls)
        ledger.statistics.export = original_export
        assert ledger.retry_exports() == {'version': 'api_timing_recovery_v1', 'scan_state': 'available',
            'pending_count': 1, 'recorded_count': 1, 'unavailable_count': 0, 'conflict_count': 0}
        assert ledger.receive_result(ops, receipt['receipt_ref'])['state'] == 'available'
        assert ledger.read_measurement(first['measurement_ref']) == first
        assert len(shared_rows(ledger)) == 1 and client.calls == calls


def test_cut_after_shared_history_write_before_export_disposition_is_idempotent(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        actual_export = ledger.statistics.export
        def cut(witness):
            assert actual_export(witness)['state'] == 'recorded'
            raise OSError('cut after shared write before local disposition')
        ledger.statistics.export = cut
        receipt = asyncio.run(acquire(ops, order, client))
        first = rows(ledger, 'api_timing_measurements')[0]
        assert len(shared_rows(ledger)) == 1
        assert rows(ledger, 'api_timing_export_dispositions') == []
        calls = list(client.calls)
        ledger.statistics.export = actual_export
        recovered = ledger.retry_exports()
        assert recovered['pending_count'] == recovered['recorded_count'] == 1
        assert len(shared_rows(ledger)) == 1 and client.calls == calls
        assert ledger.read_measurement(first['measurement_ref']) == first


def test_missing_reported_table_preserves_known_context_and_explicit_upgrade_recovers(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        with sqlite3.connect(ledger.binding.history_path) as history:
            history.execute('DROP TABLE reported_result_statistics')
        receipt = asyncio.run(acquire(ops, order, client))
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert receipt['outcome'] == 'completed' and disposition['code'] == 'history_schema_unavailable'
        first = ledger.read_measurement(disposition['measurement_ref'])
        assert first['start_context']['condition_capture'] == 'captured_before_submission'
        assert first['start_context']['condition_ref'] is None
        calls = list(client.calls)
        # Only this explicit external history initialization installs schema.
        RunHistory(ledger.binding.history_path).close()
        assert ledger.retry_exports()['recorded_count'] == 1
        assert ledger.read_measurement(first['measurement_ref']) == first
        assert len(shared_rows(ledger)) == 1 and client.calls == calls


def test_actual_locked_history_during_export_retains_original_known_start(tmp_path):
    async def run():
        store, client, ops, order, ledger = build(tmp_path)
        with store:
            await ops.submit_once(order['job_ref'], operation_key='submit')
            intent = rows(ledger, 'api_timing_submission_intents')[0]
            with sqlite3.connect(ledger.binding.history_path, isolation_level=None) as locked:
                locked.execute('BEGIN EXCLUSIVE')
                client.state = 'SUCCESS'
                await ops.status_once(order['job_ref'], operation_key='status')
                receipt = await ops.result_once(order['job_ref'], operation_key='result', page=1, page_size=2)
                disposition = ledger.receive_result(ops, receipt['receipt_ref'])
                assert receipt['outcome'] == 'completed' and disposition['code'] == 'history_unavailable'
                first = ledger.read_measurement(disposition['measurement_ref'])
                assert first['start_context'] == intent['start_context']
                locked.rollback()
            calls = list(client.calls)
            assert ledger.retry_exports()['recorded_count'] == 1
            assert ledger.read_measurement(first['measurement_ref']) == first
            assert len(shared_rows(ledger)) == 1 and client.calls == calls
    asyncio.run(run())


def test_contradictory_saved_winning_submit_receipts_are_ambiguous_not_latest(tmp_path):
    async def run():
        store, client, ops, order, ledger = build(tmp_path)
        with store:
            successful = await ops.submit_once(order['job_ref'], operation_key='submit')
            first_binding = rows(ledger, 'api_timing_submission_bindings')[0]
            # Fault injection into the actual saved receipt producer: there is
            # no API path which silently permits this competing submission.
            # Recovery must still refuse to choose its latest saved context.
            with store.transaction():
                extra = ops._receipt(order['job_ref'], 'submit', 'contradictory_saved_submit',
                    ops._selection(order['job_ref'], 'submit', 'contradictory_saved_submit', {'retry_of': None}),
                    snapshot_ref=successful['snapshot_ref'])
            assert extra['remote_id'] == successful['remote_id']
            resolved = ledger.resolve_submission_binding(ops, order['job_ref'], JOB)
            assert resolved['state'] == 'conflict' and resolved['code'] == 'submission_binding_ambiguous'
            client.state = 'SUCCESS'
            await ops.status_once(order['job_ref'], operation_key='status')
            receipt = await ops.result_once(order['job_ref'], operation_key='result', page=1, page_size=2)
            disposition = ledger.receive_result(ops, receipt['receipt_ref'])
            witness = ledger.read_measurement(disposition['measurement_ref'])
            assert disposition['code'] == 'submission_binding_ambiguous'
            assert witness['intent_ref'] is None and witness['start_context'] is None
            assert rows(ledger, 'api_timing_submission_bindings') == [first_binding]
            assert shared_rows(ledger) == []
            assert ledger.retry_exports()['recorded_count'] == 0
    asyncio.run(run())


def test_missing_start_intent_keeps_source_qualified_binding_and_local_witness(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        original = ledger.before_actual_submit
        ledger.before_actual_submit = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('intent storage unavailable'))
        receipt = asyncio.run(acquire(ops, order, client))
        ledger.before_actual_submit = original
        binding = rows(ledger, 'api_timing_submission_bindings')[0]
        assert binding['intent_state'] == 'unavailable' and binding['intent_ref'] is None
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['code'] == 'start_binding_unavailable'
        witness = ledger.read_measurement(disposition['measurement_ref'])
        assert witness['start_context'] is None and witness['intent_ref'] is None
        assert witness['submission_binding_ref'] == binding['binding_ref']
        assert shared_rows(ledger) == [] and len(client.calls) == 3


def test_unsupported_taxonomy_is_valid_work_local_witness_without_numeric_export(tmp_path):
    store, client, ops, order, ledger = build(tmp_path, parameters={'include_taxonomy': [562]})
    with store:
        receipt = asyncio.run(acquire(ops, order, client))
        assert receipt['outcome'] == 'completed'
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['code'] == 'unsupported_statistics_configuration'
        witness = ledger.read_measurement(disposition['measurement_ref'])
        assert witness['start_context'] is None and witness['intent_ref'] is None
        assert rows(ledger, 'api_timing_submission_intents') == [] and shared_rows(ledger) == []
        assert ledger.retry_exports()['pending_count'] == 0


def test_unsupported_witness_cut_before_derived_disposition_recovers_original_reason(tmp_path):
    store, client, ops, order, ledger = build(tmp_path, parameters={'exclude_taxonomy': [562]})
    with store:
        actual_export = ledger._export
        ledger._export = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('cut after unsupported witness'))
        receipt = asyncio.run(acquire(ops, order, client))
        first = rows(ledger, 'api_timing_measurements')[0]
        assert first['start_context'] is None and first['intent_ref'] is None
        assert rows(ledger, 'api_timing_export_dispositions') == []
        ledger._export = actual_export
        ledger.statistics.capture_start = lambda request: (_ for _ in ()).throw(AssertionError('condition recaptured'))
        calls = list(client.calls)
        recovery = ledger.retry_exports()
        assert recovery['pending_count'] == recovery['unavailable_count'] == 1
        assert recovery['recorded_count'] == 0
        assert rows(ledger, 'api_timing_export_dispositions')[0]['code'] == 'unsupported_statistics_configuration'
        assert ledger.receive_result(ops, receipt['receipt_ref'])['code'] == 'unsupported_statistics_configuration'
        assert ledger.read_measurement(first['measurement_ref']) == first
        assert shared_rows(ledger) == [] and client.calls == calls


def test_cancellation_survives_capture_and_original_winning_intent_recovery(tmp_path):
    async def run():
        store, client, ops, order, ledger = build(tmp_path)
        with store:
            client.release.clear()
            task = asyncio.create_task(ops.submit_once(order['job_ref'], operation_key='submit'))
            assert await asyncio.to_thread(client.entered.wait, 3)
            intent = rows(ledger, 'api_timing_submission_intents')[0]
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            client.release.set()
            await asyncio.get_running_loop().shutdown_default_executor()
            assert rows(ledger, 'api_timing_submission_bindings') == []
            recovered = ops.recover_submission(order['job_ref'], operation_key='recover')
            assert recovered['remote_id'] == JOB
            binding = rows(ledger, 'api_timing_submission_bindings')[0]
            assert binding['submission_receipt_ref'] != recovered['receipt_ref']
            assert binding['submission_operation_key'] == 'submit'
            assert binding['intent_ref'] == intent['intent_ref']
            assert len(client.calls) == 1 and len(rows(ledger, 'api_timing_submission_intents')) == 1
    asyncio.run(run())


def test_cut_before_result_hook_recovers_original_acquisition_timestamp_from_cache(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store:
        original_hook = ledger.receive_result
        ledger.receive_result = lambda *args: (_ for _ in ()).throw(OSError('cut before witness'))
        original_receipt = asyncio.run(acquire(ops, order, client))
        assert rows(ledger, 'api_timing_measurements') == []
        ledger.receive_result = original_hook
        calls = list(client.calls)
        cached = asyncio.run(ops.result_once(order['job_ref'], operation_key='cached_after_cut', page=1, page_size=2))
        witness = rows(ledger, 'api_timing_measurements')[0]
        assert witness['acquisition_receipt_ref'] == original_receipt['receipt_ref']
        assert witness['observed_at'] == original_receipt['observed_at'] != cached['observed_at']
        assert client.calls == calls and len(shared_rows(ledger)) == 1


def test_store_identity_is_exact_and_saved_records_cannot_mutate_binding(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store, Store(tmp_path/'foreign') as foreign:
        record = ledger.as_record(); record['registry']['resource_id'] = 'changed'
        assert ledger.as_record()['registry'] == registry(client)
        detached = ledger.registry; detached['resource_id'] = 'changed'
        assert ledger.registry == registry(client)
        assert ledger.as_record()['store_path'] == str(store.path.resolve())
        assert ledger.binding_ref == 'api_timing_binding_' + hashlib.sha256(canonical(ledger.as_record()).encode()).hexdigest()
        with pytest.raises(ValueError, match='owner_mismatch'):
            ProviderJobOperations(foreign, RemoteSearches(foreign, client), registry=registry(client), timing=ledger)
        with pytest.raises(ValueError, match='binding_conflict'):
            ApiTimingLedger(store=foreign, run_id=ledger.run_id, registry=registry(client),
                binding=ledger.binding, statistics=ledger.statistics)
        assert client.calls == []


def test_locked_timing_journal_does_not_prevent_selected_post_or_result(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    with store, sqlite3.connect(ledger.binding.ledger_path, isolation_level=None) as locked:
        locked.execute('BEGIN IMMEDIATE')
        receipt = asyncio.run(acquire(ops, order, client))
        assert receipt['outcome'] == 'completed' and len(client.calls) == 3
        locked.rollback()
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        witness = ledger.read_measurement(disposition['measurement_ref'])
        assert witness['start_context'] is None and witness['intent_ref'] is None
        assert disposition['code'] == 'start_binding_unavailable' and shared_rows(ledger) == []


def test_constructor_unavailable_ledger_never_backfills_eligibility_or_condition(tmp_path):
    path = tmp_path/'workspace'
    with Store(path) as store:
        problem = store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        client = TimingClient(); reg = registry(client)
        binding = ApiTimingBinding(ledger_path=tmp_path/'locked.sqlite', history_path=tmp_path/'history.sqlite',
            resource_id=reg['resource_id'], monitoring_information_unit=0.25)
        RunHistory(binding.history_path).close()
        statistics = ApiReportedStatistics(binding, registry=reg)
        captures = []
        original_capture = statistics.capture_start
        statistics.capture_start = lambda request: (captures.append(request), original_capture(request))[1]
        with sqlite3.connect(binding.ledger_path, isolation_level=None) as locked:
            locked.execute('BEGIN EXCLUSIVE')
            ledger = ApiTimingLedger(store=store, run_id='constructor_unavailable', registry=reg,
                binding=binding, statistics=statistics)
            assert ledger.as_record()['binding'] == binding.as_record()
            ops = ProviderJobOperations(store, RemoteSearches(store, client), registry=reg, timing=ledger)
            subject = problem['subject_refs'][0]
            order = ops.order(operation_key='order', provider='hmmer', subject_ref=subject,
                query_fasta=f'>{subject}\nMACDEFGH', algorithm='phmmer', database='swissprot',
                parameters={}, page_size=2, scope={'subject_refs': [subject]})
            receipt = asyncio.run(acquire(ops, order, client))
            assert receipt['outcome'] == 'completed' and len(client.calls) == 3
            assert captures == []
            assert ledger.retry_exports()['scan_state'] == 'unavailable'
            locked.rollback()
        # Recovery can establish only the exact caller owner. The original
        # order was not eligible, so it acquires no historical start/witness.
        disposition = ledger.receive_result(ops, receipt['receipt_ref'])
        assert disposition['code'] == 'not_opted_in_order'
        assert captures == []
        assert rows(ledger, 'api_timing_orders') == rows(ledger, 'api_timing_submission_intents') == rows(ledger, 'api_timing_measurements') == []
        assert shared_rows(ledger) == []


def test_reconstruction_unavailable_with_existing_eligibility_preserves_unknown_start(tmp_path):
    store, client, ops, order, original = build(tmp_path)
    with store, sqlite3.connect(original.binding.ledger_path, isolation_level=None) as locked:
        locked.execute('BEGIN EXCLUSIVE')
        statistics = ApiReportedStatistics(original.binding, registry=original.registry)
        captures = []
        statistics.capture_start = lambda request: captures.append(request)
        ledger = ApiTimingLedger(store=store, run_id=original.run_id, registry=original.registry,
            binding=original.binding, statistics=statistics)
        restored = ProviderJobOperations(store, RemoteSearches(store, client), registry=original.registry, timing=ledger)
        receipt = asyncio.run(acquire(restored, order, client))
        assert receipt['outcome'] == 'completed' and captures == []
        locked.rollback()
        disposition = ledger.receive_result(restored, receipt['receipt_ref'])
        assert disposition['code'] == 'start_binding_unavailable'
        witness = ledger.read_measurement(disposition['measurement_ref'])
        assert witness['intent_ref'] is None and witness['start_context'] is None
        assert captures == [] and shared_rows(ledger) == []


def test_equal_durations_different_actual_uuids_are_distinct_observations(tmp_path):
    store, client, ops, order, ledger = build(tmp_path/'one')
    with store:
        asyncio.run(acquire(ops, order, client))
        first = rows(ledger, 'api_timing_measurements')[0]
    store2, client2, ops2, order2, ledger2 = build(tmp_path/'two', client=TimingClient(job_id='c4f0ce97-4a66-42ee-8579-eb1084745402'))
    with store2:
        asyncio.run(acquire(ops2, order2, client2))
        second = rows(ledger2, 'api_timing_measurements')[0]
        assert first['elapsed_seconds'] == second['elapsed_seconds']
        assert first['measurement_ref'] != second['measurement_ref']
        assert first['measurement_ref'] == reported_result_identity(first['registry_ref'], first['remote_id'])['measurement_ref']


def test_two_reconstructed_stores_concurrently_recover_one_first_witness(tmp_path):
    store, client, ops, order, ledger = build(tmp_path)
    hook = ledger.receive_result
    ledger.receive_result = lambda *args: None
    receipt = asyncio.run(acquire(ops, order, client))
    ledger.receive_result = hook
    binding, reg, run_id, store_path = ledger.binding, ledger.registry, ledger.run_id, store.path
    store.close()
    barrier = threading.Barrier(2)
    init_lock = threading.Lock()

    def receive():
        with init_lock:
            own_store = Store(store_path)
            own_client = TimingClient()
            stats = ApiReportedStatistics(binding, registry=reg)
            own_ledger = ApiTimingLedger(store=own_store, run_id=run_id, registry=reg, binding=binding, statistics=stats)
            own_ops = ProviderJobOperations(own_store, RemoteSearches(own_store, own_client), registry=reg, timing=own_ledger)
        with own_store:
            barrier.wait(timeout=10)
            outcome = own_ledger.receive_result(own_ops, receipt['receipt_ref'])
            assert own_client.calls == []
            return outcome

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: receive(), range(2)))
    assert any(outcome['measurement_ref'] is not None for outcome in outcomes)
    assert len(rows(ledger, 'api_timing_measurements')) == 1
    # A nonblocking losing writer can retry only the existing witness/export.
    with Store(store_path) as reopened:
        stats = ApiReportedStatistics(binding, registry=reg)
        restored = ApiTimingLedger(store=reopened, run_id=run_id, registry=reg, binding=binding, statistics=stats)
        restored.retry_exports()
    assert len(shared_rows(ledger)) == 1
