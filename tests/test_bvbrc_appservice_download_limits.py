"""Selected-byte limits over controlled HTTP and real engineering Store records.

These checks make no live BV-BRC or GenomeAnnotation claim. Existing uncapped
fixtures below are retained-format inputs, never permission for a new request.
"""
from copy import deepcopy
from contextlib import closing
from dataclasses import replace
import hashlib
from http.client import IncompleteRead
import asyncio
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.bvbrc_analysis_transport import BVBRCAnalysisClient
from gene_annotation_episode.bvbrc_appservice_contracts import (
    ContractValidationError, contract_schema, download_request, validate_contract,
)
from gene_annotation_episode.bvbrc_appservice_tool_info import operation_catalog
from gene_annotation_episode.bvbrc_appservice_readers import _bounded_capture
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_api_bvbrc_appservice import CONFIG
from test_api_bvbrc_appservice import PREFIX, harness
from test_bvbrc_analysis_transport import server
from test_bvbrc_appservice_bundle_values import acquisition, bundle, fixture, refreeze
from test_bvbrc_appservice_host import driver
from test_bvbrc_appservice_publication import setup
from test_bvbrc_appservice_inputs import download_args, output_target
from test_bvbrc_appservice_custody import selector
from test_interval_results_presentation import _canonical, _inventory, _tables
from test_api_selected_effects import OWNER, context as effect_context, descriptor, outcomes
from gene_annotation_episode.api_selected_effects import SelectedAPIEffects


@pytest.mark.parametrize('body,limit', [(b'', 1), (b'ab', 3), (b'abc', 3)])
def test_exact_selected_cap_preserves_complete_actual_body(body, limit):
    with server(body) as (url, calls):
        snapshot = BVBRCAnalysisClient({'Workspace': url}).download(url + '/raw', max_bytes=limit)
    assert len(calls) == 1 and calls[0]['path'] == '/raw'
    assert snapshot.content == body and snapshot.sha256 == hashlib.sha256(body).hexdigest()
    assert snapshot.request == {'kind': 'download', 'url': url + '/raw',
        'requested_byte_range': None, 'max_bytes': limit}
    assert snapshot.transport['response_byte_limit'] == limit
    assert snapshot.transport['observed_body_bytes'] == len(body)
    assert snapshot.transport['retained_body_bytes'] == snapshot.transport['received_body_bytes'] == len(body)
    assert snapshot.transport['declared_body_bytes'] == len(body)
    assert snapshot.transport['body_complete'] is True


@pytest.mark.parametrize('status,selected_range,headers', [
    (200, None, {}),
    (200, (2, 5), {}),
    (206, (2, 7), {'Content-Range': 'bytes 2-7/10'}),
])
def test_cap_retains_prefix_and_cap_plus_one_observation_without_rewriting_range(status, selected_range, headers):
    with server(b'abcdef', status=status, headers=headers) as (url, calls):
        with pytest.raises(AcquisitionError) as raised:
            BVBRCAnalysisClient({'Workspace': url}).download(url + '/raw?key=exact',
                max_bytes=3, byte_range=selected_range)
    snapshot = raised.value.snapshot
    assert raised.value.code == 'bvbrc_response_byte_limit'
    assert len(calls) == 1 and calls[0]['path'] == '/raw?key=exact'
    assert calls[0]['headers'].get('Range') == (None if selected_range is None else
        'bytes=' + str(selected_range[0]) + '-' + str(selected_range[1]))
    assert snapshot.request['requested_byte_range'] == (None if selected_range is None else list(selected_range))
    assert snapshot.content == b'abc' and snapshot.transport['status'] == status
    assert snapshot.transport['observed_body_bytes'] == 4
    assert snapshot.transport['retained_body_bytes'] == snapshot.transport['received_body_bytes'] == 3
    assert snapshot.transport['declared_body_bytes'] == 6
    assert snapshot.transport['body_complete'] is False
    assert snapshot.transport['body_capture_failure'] == 'provider_response_byte_limit'


@pytest.mark.parametrize('status', [302, 403, 503])
def test_http_failure_retains_bounded_native_prefix_without_redirect_or_retry(status):
    with server(b'error-body', status=status, headers={'Location': '/unselected'}) as (url, calls):
        with pytest.raises(AcquisitionError) as raised:
            BVBRCAnalysisClient({'Workspace': url}).download(url + '/selected', max_bytes=4)
    snapshot = raised.value.snapshot
    assert len(calls) == 1 and calls[0]['path'] == '/selected'
    assert snapshot.content == b'erro' and snapshot.transport['status'] == status
    assert snapshot.transport['observed_body_bytes'] == 5
    assert snapshot.transport['retained_body_bytes'] == 4
    assert snapshot.transport['automatic_redirects'] is False
    assert snapshot.transport['body_complete'] is False
    assert raised.value.code == 'bvbrc_response_byte_limit'


def test_partial_read_exception_retains_actual_prefix_and_failure(monkeypatch):
    from email.message import Message
    class Response:
        status = 200
        headers = Message()
        headers['Content-Length'] = '9'
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def geturl(self): return 'https://fixture.invalid/selected'
        def read(self, size):
            assert size == 5
            raise IncompleteRead(b'abc', 6)
    calls = []
    def open_once(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()
    monkeypatch.setattr('urllib.request.OpenerDirector.open', open_once)
    with pytest.raises(AcquisitionError) as raised:
        BVBRCAnalysisClient({'Workspace': 'https://fixture.invalid'}).download(
            'https://fixture.invalid/selected', max_bytes=4)
    snapshot = raised.value.snapshot
    assert len(calls) == 1 and snapshot.content == b'abc'
    assert raised.value.code == 'bvbrc_response_body_incomplete'
    assert snapshot.transport['observed_body_bytes'] == snapshot.transport['retained_body_bytes'] == 3
    assert snapshot.transport['body_capture_failure'] == 'provider_body_capture_failed'
    assert snapshot.transport['body_complete'] is False


@pytest.mark.parametrize('length,transfer_encoding,declared', [
    ('3', None, 3), (' 3 ', None, None), ('3', '', None), ('3', 'chunked', None),
])
def test_declared_length_evidence_matches_bounded_reader_without_header_rewriting(monkeypatch, length, transfer_encoding, declared):
    from email.message import Message
    class Response:
        status = 200
        def __init__(self):
            self.headers = Message()
            self.headers['Content-Length'] = length
            if transfer_encoding is not None:
                self.headers['Transfer-Encoding'] = transfer_encoding
            self.body = b'abc'
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def geturl(self): return 'https://fixture.invalid/selected'
        def read(self, size):
            result, self.body = self.body[:size], self.body[size:]
            return result
    monkeypatch.setattr('urllib.request.OpenerDirector.open', lambda *a, **k: Response())
    snapshot = BVBRCAnalysisClient({'Workspace': 'https://fixture.invalid'}).download(
        'https://fixture.invalid/selected', max_bytes=8)
    assert snapshot.content == b'abc'
    assert snapshot.transport['headers']['content-length'] == length
    assert snapshot.transport['declared_body_bytes'] == declared
    assert _bounded_capture(snapshot.request, snapshot.transport, 3,
        snapshot.transport['headers']) == (True, [])


@pytest.mark.parametrize('limit', [None, False, True, 0, -1, 1.0, '4'])
def test_invalid_or_absent_explicit_limit_sends_no_request(limit, monkeypatch):
    monkeypatch.setattr('urllib.request.OpenerDirector.open',
        lambda *args, **kwargs: pytest.fail('invalid byte limit attempted transport'))
    client = BVBRCAnalysisClient({'Workspace': 'https://fixture.invalid'})
    with pytest.raises(ValueError, match='byte_limit_required'):
        client.download('https://fixture.invalid/selected', max_bytes=limit)


def test_current_catalog_requires_cap_but_retained_schema_and_legacy_json_stay_literal(harness, monkeypatch):
    case = fixture(harness)
    arguments = case['prepared']['native_operands']['arguments']
    before = deepcopy(case)
    assert 'max_bytes' not in arguments
    validate_contract('Arguments_download', arguments)
    current = next(row for row in operation_catalog('results') if row['name'] == PREFIX + 'download')
    with pytest.raises(ContractError):
        validate_schema(arguments, current['input_schema'])
    validate_schema({**arguments, 'max_bytes': 4}, current['input_schema'])
    assert validate_contract('OperationSelection', {'name': PREFIX + 'download',
        'arguments': {**arguments, 'max_bytes': 4}})['arguments']['max_bytes'] == 4
    assert validate_contract('OperationSelection', {'name': PREFIX + 'download',
        'arguments': arguments})['arguments'] == arguments
    assert 'max_bytes' not in contract_schema('Arguments_download')['$defs']['Arguments_download']['required']
    assert acquisition(case)['contract'] == 'AcquisitionReceipt'
    assert bundle(case)['status'] == 'ok'
    harness.service.client.download = lambda *a, **k: pytest.fail('legacy prepared work attempted transport')
    with pytest.raises(ValueError, match='byte_limit_required'):
        harness.service.invoke(case['prepared'])
    assert case == before


@pytest.mark.parametrize('change', ['cap', 'range', 'bool_cap', 'extra'])
def test_download_request_joins_exact_original_selected_operands(change):
    call = {'url': 'https://fixture.invalid/exact', 'byte_range': [2, 4], 'max_bytes': 3}
    arguments = {'byte_range': [2, 4], 'max_bytes': 3}
    if change == 'cap': arguments['max_bytes'] = 4
    elif change == 'range': arguments['byte_range'] = [1, 4]
    elif change == 'bool_cap': call['max_bytes'] = True
    else: call['unselected'] = 1
    with pytest.raises(ContractValidationError):
        download_request(call, arguments=arguments)


def bounded_case(harness, *, complete=False, limit=3, content=b'abc', observed=4):
    """Pure engineered selection; not a native response or custody witness."""
    case = fixture(harness, content=content, complete=complete,
        metadata_size=6, headers={'Content-Length': '6'})
    native = case['prepared']['native_operands']
    native['arguments']['max_bytes'] = native['call']['max_bytes'] = limit
    snapshot = case['snapshot']
    transport = {**snapshot.transport, 'response_byte_limit': limit,
        'observed_body_bytes': observed, 'retained_body_bytes': len(content),
        'declared_body_bytes': 6, 'body_capture_failure': 'provider_response_byte_limit'}
    case['snapshot'] = replace(snapshot,
        request={**snapshot.request, 'max_bytes': limit}, transport=transport)
    case['common_receipt']['snapshot']['transport'] = deepcopy(transport)
    refreeze(case)
    case['event'] = harness.service.decode(case['prepared'], case['snapshot'])
    return case


def test_capped_prefix_is_retained_but_never_completes_artifact_or_bundle(harness):
    case = bounded_case(harness)
    result = acquisition(case)
    assert result['contract'] == 'AcquisitionReceipt'
    value = result['value']
    assert value['artifact']['byte_count'] == 3
    assert value['artifact']['sha256'] == hashlib.sha256(b'abc').hexdigest()
    assert value['artifact']['transfer']['body_complete'] is False
    assert value['artifact']['transfer']['object_complete'] == 'no'
    assert value['status'] != 'ok' and bundle(case)['status'] != 'ok'
    assert 'download_byte_limit_exceeded' in {row['code'] for row in result['diagnostics']}


@pytest.mark.parametrize('field,value', [
    ('response_byte_limit', 4), ('response_byte_limit', True),
    ('observed_body_bytes', 2), ('observed_body_bytes', 4.0),
    ('retained_body_bytes', 4), ('received_body_bytes', False),
    ('declared_body_bytes', 3), ('declared_body_bytes', '6'),
    ('body_complete', True), ('body_capture_failure', False),
])
def test_conflicting_capture_counts_cannot_promote_complete_saved_artifact(harness, field, value):
    case = bounded_case(harness)
    transport = {**case['snapshot'].transport, field: value}
    case['snapshot'] = replace(case['snapshot'], transport=transport)
    case['common_receipt']['snapshot']['transport'] = deepcopy(transport)
    refreeze(case)
    case['event'] = harness.service.decode(case['prepared'], case['snapshot'])
    result = acquisition(case)
    assert result['value']['status'] != 'ok'
    if result['contract'] == 'AcquisitionReceipt':
        assert result['value']['artifact']['transfer']['object_complete'] != 'yes'
        assert bundle(case)['status'] != 'ok'


def test_real_selected_cap_receipt_and_same_key_cache_preserve_prefix_without_new_download(driver, monkeypatch):
    d = driver
    context, arguments = setup(d)
    arguments['max_bytes'] = 3
    d.client.body = b'abcdef'
    original = d.client.download
    def bounded_download(url, *, max_bytes, byte_range=None):
        snapshot = original(url, max_bytes=64, byte_range=byte_range)
        snapshot = replace(snapshot, content=snapshot.content[:max_bytes],
            request={**snapshot.request, 'max_bytes': max_bytes},
            transport={**snapshot.transport, 'response_byte_limit': max_bytes,
                'observed_body_bytes': max_bytes + 1, 'retained_body_bytes': max_bytes,
                'received_body_bytes': max_bytes, 'body_complete': False,
                'body_capture_failure': 'provider_response_byte_limit'})
        raise AcquisitionError('bvbrc_response_byte_limit', snapshot=snapshot,
            phase='http_response', submission_outcome='unknown')
    monkeypatch.setattr(d.client, 'download', bounded_download)
    context, key = d.selection('download', arguments, context=context)
    outcome = d.invoke(context, 'download', arguments, key)
    assert outcome['status'] == 'partial'
    reference = outcome['result']['support_receipt_ref']
    value = d.records.read(reference)['value']
    assert value['artifact']['byte_count'] == 3
    assert d.store.get_artifact(value['artifact']['raw_artifact_ref']) == b'abc'
    assert value['artifact']['transfer']['body_complete'] is False
    assert value['artifact']['transfer']['object_complete'] == 'no'
    assert d.api._completion(context) is None
    rows = [tuple(row) for row in d.store.db.execute('SELECT * FROM records ORDER BY id')]
    calls = deepcopy(d.client.calls)
    monkeypatch.setattr(d.client, 'download', lambda *a, **k: pytest.fail('cache repeated transport'))
    assert d.invoke(context, 'download', arguments, key) == outcome
    assert d.client.calls == calls
    assert [tuple(row) for row in d.store.db.execute('SELECT * FROM records ORDER BY id')] == rows


def test_fresh_uncapped_selected_action_cannot_use_legacy_read_permission(driver):
    d = driver
    context, arguments = setup(d)
    arguments.pop('max_bytes')
    calls, count = deepcopy(d.client.calls), d.store.count('source')
    context, key = d.selection('download', arguments, context=context)
    outcome = d.invoke(context, 'download', arguments, key)
    assert outcome['status'] == 'invalid'
    assert d.client.calls == calls and d.store.count('source') == count
    assert d.api.appservice.legacy_cached_download(context, PREFIX + 'download', arguments, key) is None


@pytest.mark.parametrize('problem', ['forged_context', 'unreceived_handoff', 'unselected_arguments'])
def test_legacy_cache_denies_unauthorized_context_or_action_before_private_control_bytes(driver, monkeypatch, problem):
    from test_bvbrc_appservice_custody import request
    d = driver
    query = request()
    obj = output_target(query)
    d.tree(query)
    handoff = d.launch_task()
    # This actual Results commission precedes delivery of the real handoff to
    # its parent; the later legitimate delivery cannot backfill its cutoff.
    earlier = d.saved.child(d.saved.root, 'results', {
        'version': 'execution_results_assignment_v1', 'handoff_ref': handoff['source_ref'],
        'selector': selector()}, 3)
    current = d.results(handoff, index=4)
    d.client.value = ['https://fixture.invalid/exact-output']
    cap = d.call('download_capability', {'objects': [obj], 'generation': 0,
        'predecessor_receipt_ref': None}, context=current)
    arguments = download_args(obj, {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0})
    arguments.pop('max_bytes')
    context, key = d.selection('download', arguments,
        context=earlier if problem == 'unreceived_handoff' else current)
    if problem == 'forged_context':
        context = replace(context, scope={'subject_refs': []})
        code = 'bvbrc_appservice_custody_context_conflict'
    elif problem == 'unselected_arguments':
        arguments = {**arguments, 'byte_range': [0, 1]}
        code = 'api_selected_action_conflict'
    else:
        code = 'bvbrc_appservice_custody_input_not_received_before_commission'
    def forbidden(*args, **kwargs):
        pytest.fail('unauthorized cache admission read private control/entity bytes')
    monkeypatch.setattr('gene_annotation_episode.bvbrc_appservice_host._read', forbidden)
    monkeypatch.setattr('gene_annotation_episode.bvbrc_appservice_records._read', forbidden)
    monkeypatch.setattr(d.store, 'get_artifact', forbidden)
    with pytest.raises(ValueError, match='^' + code + '$'):
        d.api.appservice.legacy_cached_download(context, PREFIX + 'download', arguments, key)


LEGACY_CASE = Path('/home/chia/repos/gene_annotation_episode/verification/'
    'tool_graders_bvbrc_homology_pairwise_workflow_2026-10-24/runs/pairwise-ih4zrdlw')
LEGACY_INVENTORY = 'b91b13fe8dbef99136f6be8d93f1dff86256ef0e77c2e9e993379f56c354cec7'
LEGACY_EPISODE = 'episode_098e9c0bbcd989e657cb4608a363af187cd0c7fef97ec489823c9f2cb90ffa17'
LEGACY_RUN = 'homology-pairwise-selected-workflow'


def _deny_original_mutations(directory):
    """Audit real constructor ports; never redirect an original write."""
    active = [True]
    directory = directory.resolve()
    def original(path):
        return isinstance(path, (str, bytes, os.PathLike)) and Path(os.fsdecode(path)).absolute().is_relative_to(directory)
    def guard(event, args):
        if not active[0]:
            return
        if event == 'open':
            path, mode, flags = args
            writing = (isinstance(mode, str) and any(letter in mode for letter in 'wax+')) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
            if writing and original(path):
                raise AssertionError('retained original write attempted')
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime',
                'os.truncate', 'os.rename', 'os.link', 'os.symlink'}:
            paths = args[:2] if event in {'os.rename', 'os.link', 'os.symlink'} else args[:1]
            if any(original(path) for path in paths):
                raise AssertionError('retained original mutation attempted')
    sys.addaudithook(guard)
    return active


@pytest.mark.parametrize('state', ['confirmed', 'not_sent'])
def test_completed_effect_read_authenticates_terminal_state_without_filesystem_writes(tmp_path, state):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    reservation = journal.reserve(effect_context(), 'run:api:0', [descriptor()])
    journal.mark_issued(reservation)
    expected, = journal.record_outcome(reservation, outcomes(reservation, state))
    before = _inventory(tmp_path)
    active = _deny_original_mutations(tmp_path)
    try:
        actual = journal.read_completed(reservation['effect_refs'][0], original_job_owner=OWNER)
        assert actual == expected
        actual['native_effect_identifiers']['unowned'] = 'changed returned copy'
        assert journal.read_completed(reservation['effect_refs'][0], original_job_owner=OWNER) == expected
    finally:
        active[0] = False
    assert _inventory(tmp_path) == before


@pytest.mark.parametrize('state', ['prepared_not_issued', 'issued_unknown', 'absent', 'wrong_owner'])
def test_completed_effect_read_denies_nonterminal_or_unowned_effect_without_writes(tmp_path, state):
    journal = SelectedAPIEffects(tmp_path, run_id='run')
    reservation = journal.reserve(effect_context(), 'run:api:0', [descriptor()])
    if state == 'issued_unknown':
        journal.mark_issued(reservation)
    reference = 'absent_effect' if state == 'absent' else reservation['effect_refs'][0]
    owner = {**OWNER, 'launch_episode_id': 'different'} if state == 'wrong_owner' else OWNER
    before = _inventory(tmp_path)
    active = _deny_original_mutations(tmp_path)
    try:
        code = 'api_effect_not_owned_or_recorded' if state in {'absent', 'wrong_owner'} else 'api_effect_completed_outcome_required'
        with pytest.raises(ValueError, match='^' + code + '$'):
            journal.read_completed(reference, original_job_owner=owner)
    finally:
        active[0] = False
    assert _inventory(tmp_path) == before


def test_authentic_completed_uncapped_download_cache_uses_original_control_anchor_without_writes(tmp_path, monkeypatch):
    """Current read-side cache, not original configured-binding/native replay."""
    gate = os.environ.get('HMMER_NATIVE_ORACLE_APPSERVICE_LEGACY_DOWNLOAD_CASE_JSON')
    if gate is None:
        pytest.skip('requires the exact retained engineering Homology case')
    selected = json.loads(gate)
    assert set(selected) == {'directory', 'inventory_sha256'}
    original = Path(selected['directory']).resolve()
    assert original == LEGACY_CASE and selected['inventory_sha256'] == LEGACY_INVENTORY
    before = _inventory(original)
    assert hashlib.sha256(_canonical(before).encode()).hexdigest() == LEGACY_INVENTORY
    assert before['state/state.sqlite3']['sha256'] == '86ff2bc1836a3768d5146175f28ef491d5b920774e72b880dfdbc2ee84c05f89'
    assert before['state/state.sqlite3-wal']['size_bytes'] == 0
    copied = tmp_path / 'owned-engineering-homology'
    shutil.copytree(original, copied)
    assert _inventory(copied) == before
    with closing(sqlite3.connect((copied / 'state/state.sqlite3').as_uri() + '?mode=ro&immutable=1', uri=True)) as historical:
        old_tables = _tables(historical)

    def forbidden(*args, **kwargs):
        pytest.fail('completed legacy cache attempted new native/scientific work')
    for target in ('socket.create_connection', 'socket.socket.connect', 'socket.socket.connect_ex',
            'urllib.request.OpenerDirector.open', 'subprocess.run', 'subprocess.Popen',
            'gene_annotation_episode.api_bvbrc_appservice.BVBRCAppServiceService.invoke',
            'gene_annotation_episode.bvbrc_homology_bundle_adapter.consume_bundle',
            'gene_annotation_episode.bvbrc_homology_grader.calculate_homology_scores'):
        monkeypatch.setattr(target, forbidden)
    from gene_annotation_episode import bvbrc_homology_bundle_adapter as adapter
    config = deepcopy(CONFIG)
    # Genuine current adapter identity, whose closure includes the evolved
    # AppService contracts/schema; never substitute the old configured hash.
    config['scientific_adapters'] = [{'adapter_id': adapter.ADAPTER_ID,
        'adapter_version': adapter.ADAPTER_VERSION, 'implementation_sha256': adapter.implementation_sha256()}]
    active = _deny_original_mutations(original)
    try:
        with Store(copied / 'state') as store:
            tools = ToolRegistry(store)
            initial = _tables(store.db)
            for name, table in old_tables.items():
                columns = table['columns']
                quoted = ','.join('"' + item.replace('"', '""') + '"' for item in columns)
                rows = [list(row) for row in store.db.execute('SELECT ' + quoted + ' FROM "' + name.replace('"', '""') + '"')]
                assert sorted(rows, key=_canonical) == table['rows']
                for column in set(initial[name]['columns']) - set(columns):
                    assert store.db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') +
                        '" WHERE "' + column.replace('"', '""') + '" IS NOT NULL').fetchone()[0] == 0
            assert all(not table['rows'] for name, table in initial.items() if name not in old_tables)
            api = APIServiceExecution(store, run_id=LEGACY_RUN, directory=original / 'run',
                configuration={'selected-api': config}, tool_registry=tools,
                handoff_unit=2, acquired_record_unit=3)
            context = api.appservice.records.context(LEGACY_EPISODE)
            key = LEGACY_RUN + ':' + LEGACY_EPISODE + ':6'
            row = store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index=6', (LEGACY_RUN, LEGACY_EPISODE)).fetchone()
            action, stored = json.loads(row['action']), json.loads(row['result'])
            assert action['kind'] == 'tool' and action['tool'] == PREFIX + 'download'
            assert 'max_bytes' not in action['arguments']
            directory = api._manifest(context, create=False) / 'actions' / digest(key)
            controls = {name: (directory / name).read_bytes() for name in (
                'intent.json', 'call_intent.json', 'call_response.json', 'outcome.json')}
            assert {name: hashlib.sha256(raw).hexdigest() for name, raw in controls.items()} == {
                'intent.json': '661fa9c9b2a523a3c5476c345e32017a89008c26f8414bc07627787410ca9927',
                'call_intent.json': '853672773893d1b263a253c4dcb1108e9a6613b02b88555a6ab84df52891374e',
                'call_response.json': 'd57007e85b6630ae033974b947593da8a1c6f64c59a9d4c104bb7742025fc741',
                'outcome.json': '85e4c6d111bffa89d840536618f81b0414ff181759e7820d83b4d0b460b66691'}
            expected = json.loads(controls['outcome.json'])
            assert all(stored[field] == value for field, value in expected.items())
            old_inputs = json.loads((directory / 'publication_inputs.json').read_text())
            old_adapter_pin = old_inputs['adapter_implementation_sha256']
            assert old_adapter_pin == '6431e9b48d6015056915c610f125653a9bbb886e0195bd1a24a1fc531896a809'
            assert api.configuration == {'selected-api': config}
            for target in ('initialize', '_index_result', '_execute_locked'):
                monkeypatch.setattr(api, target, forbidden)
            result = asyncio.run(api.execute(context, action['tool'], action['arguments'], key))
            assert canonical(result) == canonical(expected), result.get('feedback')
            result['record_refs'].clear()
            assert asyncio.run(api.execute(context, action['tool'], action['arguments'], key)) == expected
            wrong_range = {**action['arguments'], 'byte_range': [0, 1]}
            denied = asyncio.run(api.execute(context, action['tool'], wrong_range, key))
            assert denied['status'] == 'invalid' and denied['record_refs'] == []
            assert denied['feedback']['code'] == 'api_selected_action_conflict'
            assert _tables(store.db) == initial
            assert all((directory / name).read_bytes() == raw for name, raw in controls.items())
            witness = {'scope': 'current completed-download cache read over retained engineering Homology',
                'original_inventory_sha256': LEGACY_INVENTORY,
                'original_configured_adapter_pin': old_adapter_pin,
                'current_read_side_configuration': api.configuration,
                'original_configured_adapter_reexecution': False,
                'native_calls': 0, 'original_control_anchor': str(original / 'run'),
                'outcome_sha256': hashlib.sha256(controls['outcome.json']).hexdigest(),
                'old_tables_sha256': hashlib.sha256(_canonical(old_tables).encode()).hexdigest(),
                'current_tables_before_after_sha256': hashlib.sha256(_canonical(initial).encode()).hexdigest(),
                'added_empty_tables': sorted(set(initial) - set(old_tables)),
                'added_nullable_columns': {name: sorted(set(initial[name]['columns']) - set(table['columns']))
                    for name, table in old_tables.items() if set(initial[name]['columns']) != set(table['columns'])}}
    finally:
        active[0] = False
    assert _inventory(original) == before
    current_copy = _inventory(copied)
    family = {'state/state.sqlite3', 'state/state.sqlite3-wal', 'state/state.sqlite3-shm'}
    assert {name: row for name, row in current_copy.items() if name not in family} == {
        name: row for name, row in before.items() if name not in family}
    (tmp_path / 'APPSERVICE_LEGACY_DOWNLOAD_CACHE.json').write_text(_canonical(witness) + '\n')
