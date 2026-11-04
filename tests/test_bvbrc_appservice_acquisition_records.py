"""Real Store/action/source records with explicitly synthetic download bytes.

These component checks do not establish live service access, scientific grading,
or a complete shared-method-loop publication and return path.
"""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.bvbrc_appservice_bundle_values import build_acquisition_value
from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.bvbrc_appservice_records import (
    AppServiceRecords, PROVIDER, VERSION, _decode, _encode,
)
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _immutable, _read
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import PREFIX
from test_bvbrc_appservice_inputs import Driver, download_args


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('acquisition record verification attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    monkeypatch.setattr('urllib.request.OpenerDirector.open', forbidden)


@pytest.fixture
def acquisition(tmp_path, request):
    with Store(tmp_path / 'state') as store:
        driver = Driver(store, tmp_path)
        driver.tree()
        handoff = driver.launch_task()
        context = driver.results(handoff)
        info = driver.call('task_info', {'handoff_ref': handoff['source_ref'],
            'file': 'job_result_id'}, context=context)
        obj = {'kind': 'task_info_object', 'receipt_ref': info['source_ref']}
        driver.client.value = ['https://download.example.invalid/exact-capability']
        capability = driver.call('download_capability', {'objects': [obj],
            'generation': 0, 'predecessor_receipt_ref': None}, context=context)
        args = download_args(obj, {'kind': 'acquired', 'receipt_ref': capability['source_ref'],
            'input_index': 0})
        driver.client.body = b'abcdef\x00\xff\n'
        case = getattr(request, 'param', None)
        if case is not None:
            driver.client.body = case['body']
            args['byte_range'] = case['range']
            original_download = driver.client.download
            def download(url, *, max_bytes, byte_range=None):
                snapshot = original_download(url, max_bytes=max_bytes, byte_range=byte_range)
                return replace(snapshot, transport={**snapshot.transport,
                    'status': case['http_status'], 'body_complete': case['body_complete'],
                    'declared_body_bytes': (int(case['headers']['content-length'])
                        if 'content-length' in case['headers'] else None),
                    'headers': case['headers']})
            driver.client.download = download
        call = driver.call('download', args, context=context)
        inputs = validate_contract('PublicationInputs', {
            'version': 'bvbrc_appservice_publication_inputs_v1',
            'request': call.prepared['native_operands']['request'],
            'selector': call.prepared['native_operands']['selector'],
            'original_handoff_ref': handoff['source_ref'],
            'current_operation': {'name': PREFIX + 'download', 'arguments': args},
            'current_snapshot': call.binding, 'prior_acquisition_receipt_refs': [],
            'support_receipt_refs': call.prepared['bound_inputs']['support_receipt_refs'],
            'supplied_evidence': [], 'adapter': None, 'adapter_implementation_sha256': None})
        _immutable(call.directory / 'publication_inputs.json', inputs)
        result = build_acquisition_value(call.prepared, call.event, call.snapshot,
            common_receipt=call.common, publication_inputs=inputs,
            acquisition_receipt_ref=call.common['receipt_ref'])
        assert result['contract'] == 'AcquisitionReceipt', result
        yield SimpleNamespace(driver=driver, call=call, inputs=inputs,
            value=result['value'], handoff=handoff)


def publish(fixture, value=None):
    f = fixture
    return f.driver.records.publish(f.call.context, 'AcquisitionReceipt',
        f.value if value is None else value, operation_key=f.call.key)


def complete(fixture, published):
    f = fixture
    f.driver.complete(f.call.context, f.call.key, f.call.directory, published,
        [published['source_ref'], f.call.binding['source_ref']])


def replace_json(path, value):
    """Deliberately corrupt a test's retained state, bypassing immutability."""
    path.write_text(canonical(value) + '\n', encoding='utf-8')


def test_actual_bytes_and_single_self_reference_replay_without_new_work(acquisition):
    f, d = acquisition, acquisition.driver
    before = deepcopy(f.value)
    published = publish(f)
    source = d.store.get(published['source_ref'])
    assert source['provider'] == PROVIDER and source['version'] == VERSION
    raw = d.store.get_artifact(source['artifact_ref'])
    encoded = json.loads(raw)
    expected = deepcopy(before)
    del expected['artifact']['transfer']['receipt_ref']
    assert encoded == {'version': VERSION, 'contract': 'AcquisitionReceipt', 'value': expected}
    assert 'receipt' not in encoded['value']
    assert before['artifact']['transfer']['receipt_ref'].encode() not in raw
    assert f.value == before
    value = published['value']
    assert value['artifact']['transfer']['receipt_ref'] == published['source_ref']
    assert value['publication_ref'] is None
    assert d.store.get_artifact(value['artifact']['raw_artifact_ref']) == b'abcdef\x00\xff\n'
    assert value['artifact']['byte_count'] == 9
    assert value['artifact']['sha256'] == f.call.snapshot.sha256
    assert d.records.read(published['source_ref'], require_completed=False) == published
    complete(f, published)
    count, calls = d.store.count('source'), deepcopy(d.client.calls)
    reopened = AppServiceRecords(d.api)
    assert reopened.read(published['source_ref']) == published
    assert publish(f) == published
    assert d.store.count('source') == count and d.client.calls == calls
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0
    assert _read(f.call.directory / 'typed_receipt.json') == published


def test_interrupted_receipt_file_publication_recovers_same_source(acquisition, monkeypatch):
    f, d = acquisition, acquisition.driver
    import gene_annotation_episode.bvbrc_appservice_records as module
    original = module._immutable
    def interrupted(path, value):
        if path.name == 'typed_receipt.json':
            raise KeyboardInterrupt()
        return original(path, value)
    monkeypatch.setattr(module, '_immutable', interrupted)
    with pytest.raises(KeyboardInterrupt):
        publish(f)
    count, calls = d.store.count('source'), deepcopy(d.client.calls)
    assert not (f.call.directory / 'typed_receipt.json').exists()
    monkeypatch.setattr(module, '_immutable', original)
    published = publish(f)
    assert d.store.count('source') == count and d.client.calls == calls
    complete(f, published)
    assert AppServiceRecords(d.api).read(published['source_ref']) == published


@pytest.mark.parametrize('acquisition, expected', [
    ({'body': b'ab', 'range': [0, 5], 'http_status': 206, 'body_complete': False,
      'headers': {'content-range': 'bytes 0-5/10', 'content-length': '6'}}, ('partial', False, 'no')),
    ({'body': b'abcdef', 'range': [0, 5], 'http_status': 206, 'body_complete': True,
      'headers': {'content-range': 'bytes 0-5/10', 'content-length': '6'}}, ('ok', True, 'no')),
    ({'body': b'', 'range': None, 'http_status': 200, 'body_complete': True,
      'headers': {'content-length': '0'}}, ('ok', True, 'yes')),
    ({'body': b'forbidden', 'range': None, 'http_status': 403, 'body_complete': True,
      'headers': {'content-length': '9'}}, ('failed', True, 'unknown')),
    ({'body': b'abcdef', 'range': None, 'http_status': 200, 'body_complete': True,
      'headers': {}}, ('ok', True, 'unknown')),
    ({'body': b'abcdef', 'range': [0, 2], 'http_status': 200, 'body_complete': True,
      'headers': {'content-length': '6'}}, ('ok', True, 'yes')),
], indirect=['acquisition'], ids=['partial-206', 'complete-range', 'empty-object',
    'http-error', 'unknown-size', 'range-ignored'])
def test_retained_transfer_qualifications_preserve_all_actual_bytes(acquisition, expected):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    complete(f, published)
    value = d.records.read(published['source_ref'])['value']
    transfer = value['artifact']['transfer']
    assert (value['status'], transfer['body_complete'], transfer['object_complete']) == expected
    assert d.store.get_artifact(value['artifact']['raw_artifact_ref']) == f.call.snapshot.content
    assert value['artifact']['byte_count'] == len(f.call.snapshot.content)


@pytest.mark.parametrize('change', ['missing_outcome', 'pending_runtime', 'different_runtime',
    'missing_reference', 'failed_outcome'])
def test_default_read_requires_exact_completed_runtime_outcome(acquisition, change):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    if change != 'missing_outcome':
        complete(f, published)
        index = int(f.call.key.rsplit(':', 1)[1])
        row = d.saved.journal.row('runtime_actions', f.call.context.episode_id, index)
        if change == 'pending_runtime':
            row['result'] = None
        elif change == 'different_runtime':
            row['result'] = canonical({'status': 'completed', 'record_refs': []})
        else:
            outcome = _read(f.call.directory / 'outcome.json')
            if change == 'missing_reference':
                outcome['record_refs'].remove(published['source_ref'])
            else:
                outcome['status'] = 'failed'
            replace_json(f.call.directory / 'outcome.json', outcome)
            row['result'] = canonical(outcome)
        d.saved.journal.save('runtime_actions', row)
    assert d.records.read(published['source_ref'], require_completed=False) == published
    with pytest.raises((ValueError, FileNotFoundError)):
        d.records.read(published['source_ref'])


@pytest.mark.parametrize('change', ['self_ref', 'publication_ref', 'origin', 'handoff', 'selector',
    'publication_digest', 'snapshot', 'capability', 'object_selection', 'requirement_ids',
    'artifact_source', 'artifact_ref', 'artifact_digest', 'artifact_bytes', 'task', 'workspace',
    'role', 'format', 'range', 'transfer', 'status'])
def test_forged_acquisition_fields_are_rejected_before_publication(acquisition, change):
    f = acquisition
    value = deepcopy(f.value)
    if change == 'self_ref':
        value['artifact']['transfer']['receipt_ref'] = f.handoff['source_ref']
    elif change == 'publication_ref':
        value['publication_ref'] = f.handoff['source_ref']
    elif change == 'origin':
        value['origin']['arguments_sha256'] = '0' * 64
    elif change == 'handoff':
        value['original_handoff_ref'] = f.call.binding['source_ref']
    elif change == 'selector':
        value['selector_sha256'] = '0' * 64
    elif change == 'publication_digest':
        value['publication_inputs_sha256'] = '0' * 64
    elif change == 'snapshot':
        value['snapshot']['retrieved_at'] = 'later'
    elif change == 'capability':
        value['capability_selection']['input_index'] = 1
    elif change == 'object_selection':
        value['object_selection']['receipt_ref'] = f.handoff['source_ref']
    elif change == 'requirement_ids':
        value['requirement_ids'] = []
    elif change == 'artifact_source':
        value['artifact']['source_ref'] = f.handoff['source_ref']
    elif change == 'artifact_ref':
        value['artifact']['raw_artifact_ref'] = f.driver.store.artifact(b'other bytes', 'application/octet-stream')
    elif change == 'artifact_digest':
        value['artifact']['sha256'] = '0' * 64
    elif change == 'artifact_bytes':
        value['artifact']['byte_count'] = 8
        value['artifact']['transfer']['total_size'] = 8
    elif change == 'task':
        value['artifact']['task_association']['task_id'] = 'another-task'
    elif change == 'workspace':
        value['artifact']['workspace_object']['path'] = '/another/object'
    elif change == 'role':
        value['artifact']['role'] = 'other_output'
    elif change == 'format':
        value['artifact']['declared_format']['format'] = 'different_format'
    elif change == 'range':
        value['artifact']['transfer']['requested_range'] = [0, 5]
    elif change == 'transfer':
        value['artifact']['transfer']['object_complete'] = 'unknown'
    else:
        value['status'] = 'partial'
    with pytest.raises(ValueError):
        publish(f, value)
    assert not (f.call.directory / 'typed_receipt.json').exists()


@pytest.mark.parametrize('change', ['request', 'selector', 'handoff', 'operation_name',
    'operation_arguments', 'current_snapshot'])
def test_rehashed_frozen_inputs_must_still_match_selected_work(acquisition, change):
    f = acquisition
    inputs, value = deepcopy(f.inputs), deepcopy(f.value)
    if change == 'request':
        inputs['request']['parameters']['output_file'] = 'different-result'
    elif change == 'selector':
        inputs['selector']['requirements'][0]['required'] = False
        value['selector_sha256'] = digest(inputs['selector'])
    elif change == 'handoff':
        inputs['original_handoff_ref'] = f.call.binding['source_ref']
        value['original_handoff_ref'] = inputs['original_handoff_ref']
    elif change == 'operation_name':
        inputs['current_operation'] = {'name': PREFIX + 'status',
            'arguments': {'handoff_ref': f.handoff['source_ref']}}
    elif change == 'operation_arguments':
        inputs['current_operation']['arguments']['capability']['input_index'] = 1
    else:
        inputs['current_snapshot']['media_type'] = 'text/plain'
    value['publication_inputs_sha256'] = digest(inputs)
    replace_json(f.call.directory / 'publication_inputs.json', inputs)
    with pytest.raises(ValueError):
        publish(f, value)


@pytest.mark.parametrize('change', ['missing', 'dependencies', 'support', 'extra_member'])
def test_frozen_publication_file_is_required_and_authenticated_on_read(acquisition, change):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    complete(f, published)
    path = f.call.directory / 'publication_inputs.json'
    if change == 'missing':
        path.unlink()
    else:
        inputs = _read(path)
        if change == 'dependencies':
            inputs['prior_acquisition_receipt_refs'] = [f.handoff['source_ref']]
        elif change == 'support':
            inputs['support_receipt_refs'] = []
        else:
            inputs['invented'] = True
        replace_json(path, inputs)
    with pytest.raises((ValueError, FileNotFoundError)):
        d.records.read(published['source_ref'])


def test_json_false_cannot_replace_selected_integer_zero_on_read(acquisition):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    complete(f, published)
    index = int(f.call.key.rsplit(':', 1)[1])
    row = d.saved.journal.row('runtime_actions', f.call.context.episode_id, index)
    action = json.loads(row['action'])
    action['arguments']['capability']['input_index'] = False
    row['action'] = canonical(action)
    d.saved.journal.save('runtime_actions', row)
    with pytest.raises(ValueError, match='publication_inputs_conflict'):
        d.records.read(published['source_ref'])


@pytest.mark.parametrize('change', ['task', 'artifact_digest', 'selector', 'publication_digest'])
def test_read_rejects_self_consistent_forged_envelope_and_outcome(acquisition, change):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    value = deepcopy(published['value'])
    if change == 'task':
        value['artifact']['task_association']['task_id'] = 'another-task'
    elif change == 'artifact_digest':
        value['artifact']['sha256'] = '0' * 64
    elif change == 'selector':
        value['selector_sha256'] = '0' * 64
    else:
        value['publication_inputs_sha256'] = '0' * 64
    encoded = {'version': VERSION, 'contract': 'AcquisitionReceipt',
        'value': _encode('AcquisitionReceipt', value)}
    artifact = d.store.artifact(canonical(encoded), 'application/json')
    source = d.store.get(published['source_ref'])
    payload = {key: item for key, item in source.items() if key not in {'id', 'record_type', 'origin'}}
    payload.update(artifact_ref=artifact, request_ref=artifact)
    forged = d.store.put('source', payload, origin='tool')
    record = {'source_ref': forged['id'], 'contract': 'AcquisitionReceipt',
        'value': _decode('AcquisitionReceipt', encoded['value'], forged['id'])}
    replace_json(f.call.directory / 'typed_receipt.json', record)
    complete(f, record)
    with pytest.raises(ValueError):
        d.records.read(forged['id'])


@pytest.mark.parametrize('change', ['native_source', 'native_bytes', 'prepared', 'selected_name'])
def test_read_reauthenticates_native_source_bytes_and_original_action(acquisition, change):
    f, d = acquisition, acquisition.driver
    published = publish(f)
    complete(f, published)
    if change == 'native_source':
        binding = _read(f.call.directory / 'native_source.json')
        binding['source_ref'] = f.handoff['source_ref']
        replace_json(f.call.directory / 'native_source.json', binding)
    elif change == 'native_bytes':
        sha256 = f.call.binding['content']['sha256']
        artifact = d.store.path / 'artifacts' / sha256[:2] / sha256
        artifact.write_bytes(b'changed retained bytes')
    elif change == 'prepared':
        intent = _read(f.call.directory / 'intent.json')
        intent['prepared']['native_operands']['call']['url'] = 'https://other.example.invalid/file'
        replace_json(f.call.directory / 'intent.json', intent)
    else:
        index = int(f.call.key.rsplit(':', 1)[1])
        row = d.saved.journal.row('runtime_actions', f.call.context.episode_id, index)
        action = json.loads(row['action'])
        action['tool'] = PREFIX + 'task_info'
        row['action'] = canonical(action)
        d.saved.journal.save('runtime_actions', row)
    with pytest.raises(ValueError):
        d.records.read(published['source_ref'])


def test_codec_rejects_stored_self_reference_and_nonnull_publication(acquisition):
    f = acquisition
    encoded = _encode('AcquisitionReceipt', f.value)
    assert _decode('AcquisitionReceipt', encoded, 'actual-source')['artifact']['transfer']['receipt_ref'] == 'actual-source'
    encoded['artifact']['transfer']['receipt_ref'] = 'invented-placeholder'
    with pytest.raises(ValueError, match='stored_self_reference'):
        _decode('AcquisitionReceipt', encoded, 'actual-source')
    del encoded['artifact']['transfer']['receipt_ref']
    encoded['publication_ref'] = 'later-publication'
    with pytest.raises(ValueError, match='publication_reference_conflict'):
        _decode('AcquisitionReceipt', encoded, 'actual-source')


def test_common_fallback_uses_existing_single_typed_receipt_file(acquisition):
    f, d = acquisition, acquisition.driver
    common = deepcopy(f.call.common)
    common['status'] = 'invalid'
    fallback = d.records.publish(f.call.context, 'CommonReceipt', common, operation_key=f.call.key)
    complete(f, fallback)
    assert d.records.read(fallback['source_ref']) == fallback
    with pytest.raises(ValueError):
        publish(f)
    assert _read(f.call.directory / 'typed_receipt.json') == fallback


def test_original_task_handoff_encoding_and_read_remain_unchanged(acquisition):
    f, d = acquisition, acquisition.driver
    handoff = d.records.read(f.handoff['source_ref'])
    source = d.store.get(handoff['source_ref'])
    encoded = json.loads(d.store.get_artifact(source['artifact_ref']))
    assert encoded['contract'] == 'TaskHandoff'
    expected = deepcopy(handoff['value'])
    del expected['receipt']['receipt_ref']
    del expected['original_task']['submission_receipt_ref']
    assert encoded == {'version': VERSION, 'contract': 'TaskHandoff', 'value': expected}
    assert handoff == f.handoff
