"""Production executor acquisition with real Store and controlled HTTP bytes."""
from copy import deepcopy
from dataclasses import replace

import pytest

from gene_annotation_episode.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.practical_execution_state import _read
from test_bvbrc_appservice_host import driver
from test_bvbrc_appservice_inputs import output_target, download_args
from test_bvbrc_appservice_custody import request, selector


def setup(d, *, two=False, projection=False):
    query = request()
    obj = output_target(query)
    d.tree(query)
    handoff = d.launch_task()
    selected = selector()
    if two:
        selected['requirements'].append({**deepcopy(selected['requirements'][0]),
            'requirement_id': 'second', 'role': 'second_output'})
    if projection:
        selected['endpoint'] = 'requested_projection'
        selected['adapter'] = {'adapter_id': 'not_installed', 'adapter_version': '1', 'parameters': {}}
        selected['requested_schema'] = {'type': 'object', 'properties': {'hits': {'type': 'integer'}},
            'required': ['hits'], 'additionalProperties': False}
    context = d.results(handoff, selection=selected)
    d.client.value = ['https://fixture.invalid/exact-output']
    cap = d.call('download_capability', {'objects': [obj], 'generation': 0,
        'predecessor_receipt_ref': None}, context=context)
    args = download_args(obj, {'kind': 'acquired', 'receipt_ref': cap['source_ref'], 'input_index': 0})
    return context, args


def test_acquisition_retains_bytes_and_completes_original_artifact_assignment(driver):
    d = driver
    context, args = setup(d)
    d.client.body = b'actual result bytes'
    acquired = d.call('download', args, context=context)
    assert acquired['contract'] == 'AcquisitionReceipt'
    assert acquired['value']['artifact']['transfer']['receipt_ref'] == acquired['source_ref']
    assert acquired['value']['publication_ref'] is None
    facts = d.api.facts(context, {})
    assert len(facts['execution_result_refs']) == 1 and facts['execution_completed']
    reference = facts['execution_result_refs'][0]
    body = d.api.read_result(reference, context.scope)
    assert body['version'] == 'bvbrc_appservice_acquired_bundle_v1'
    assert body['bundle']['status'] == 'ok'
    artifact = body['bundle']['artifacts'][0]
    assert d.store.get_artifact(artifact['raw_artifact_ref']) == d.client.body
    assert d.api.resolve(context, acquired['source_ref'], 'execution_result') is False
    assert d.api.resolve(context, reference, 'execution_result') is True
    proof = d.api._completion(context)
    assert proof['operation_key'] == acquired['value']['origin']['operation_key']
    assert d.api.verify_completion(context, proof)
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_partial_bundle_later_output_preserves_prior_publication_and_recovery(driver):
    d = driver
    context, args = setup(d, two=True)
    d.client.body = b'first'
    first = d.call('download', args, context=context)
    first_ref = d.api.facts(context, {})['execution_result_refs'][0]
    old = d.api.read_result(first_ref, context.scope)
    assert old['bundle']['status'] == 'partial' and d.api._completion(context) is None
    assert [row['requirement_id'] for row in old['bundle']['missing_requirements']] == ['second']
    second_args = {**args, 'requirement_ids': ['second'], 'role': 'second_output'}
    d.client.body = b'second'
    second = d.call('download', second_args, context=context)
    assert d.api._completion(context) is not None
    result = d.api.read_result(d.last_outcome['result']['source_ref'], context.scope)
    assert [row['receipt_ref'] if 'receipt_ref' in row else row['transfer']['receipt_ref']
        for row in result['bundle']['artifacts']] == [first['source_ref'], second['source_ref']]
    assert result['publication_inputs']['prior_acquisition_receipt_refs'] == [first['source_ref']]
    assert d.api.read_result(first_ref, context.scope) == old
    calls = len(d.client.calls)
    expected = deepcopy(d.last_outcome)
    assert d.invoke(context, 'download', second_args, second['value']['origin']['operation_key']) == expected
    assert len(d.client.calls) == calls


def test_duplicate_retrieval_keeps_receipts_without_new_result_identity(driver):
    d = driver
    context, args = setup(d, two=True)
    d.client.body = b'same bytes'
    first = d.call('download', args, context=context)
    first_ref = d.last_outcome['result']['source_ref']
    second = d.call('download', args, context=context)
    second_ref = d.last_outcome['result']['source_ref']
    assert first['source_ref'] != second['source_ref'] and first_ref != second_ref
    assert d.api.result_identity(first_ref, context.scope) == d.api.result_identity(second_ref, context.scope)
    credit = d.api.credit_view(context, {'known_record_refs': d.saved.receipts.known(context.episode_id),
        'initial_known_record_refs': []})
    assert credit['new_acquired_record_count'] == 1 and credit['credit'] == 3


def test_missing_adapter_preserves_acquisition_but_never_completes_projection(driver):
    d = driver
    context, args = setup(d, projection=True)
    d.client.body = b'not yet graded'
    acquired = d.call('download', args, context=context)
    body = d.api.read_result(d.last_outcome['result']['source_ref'], context.scope)
    assert body['bundle']['status'] == 'ok' and d.api._completion(context) is None
    assert body['publication']['requested_form_status'] == 'unavailable'
    assert body['publication']['missing_requirements'][0]['reason_code'] == 'scientific_adapter_unbound'
    assert body['publication_inputs']['adapter_implementation_sha256'] is None
    assert acquired['value']['artifact']['byte_count'] == len(d.client.body)
    validate_contract('PublicationInputs', body['publication_inputs'])


def test_complete_zero_byte_artifact_is_distinct_from_missing(driver):
    d = driver
    context, args = setup(d)
    d.client.body = b''
    d.call('download', args, context=context)
    body = d.api.read_result(d.last_outcome['result']['source_ref'], context.scope)
    assert body['bundle']['artifacts'][0]['byte_count'] == 0
    assert body['publication']['requested_form_status'] == 'satisfied'


def test_interruption_after_outcome_repairs_index_without_second_download(driver, monkeypatch):
    d = driver
    context, args = setup(d)
    d.client.body = b'recovered'
    original = d.api._index_result
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt()
    monkeypatch.setattr(d.api, '_index_result', interrupted)
    context, key = d.selection('download', args, context=context)
    with pytest.raises(KeyboardInterrupt):
        d.invoke(context, 'download', args, key)
    calls = len(d.client.calls)
    monkeypatch.setattr(d.api, '_index_result', original)
    recovered = d.invoke(context, 'download', args, key)
    assert recovered['status'] == 'completed' and len(d.client.calls) == calls
    assert d.api.read_result(recovered['result']['source_ref'], context.scope)['publication']['completion_proof']


def test_non_store_identifier_does_not_block_other_binding_resolvers(driver):
    assert driver.api.appservice.resolve(driver.saved.root, 'genome:exact-native-id', 'genome') is None


@pytest.mark.parametrize('status,complete', [(503, True), (200, False)])
def test_failed_or_incomplete_response_retains_actual_bytes_without_completion(driver, monkeypatch, status, complete):
    d = driver
    context, args = setup(d)
    d.client.body = b'partial or error body'
    original = d.client.download
    def response(url, *, max_bytes, byte_range=None):
        snapshot = original(url, max_bytes=max_bytes, byte_range=byte_range)
        return replace(snapshot, transport={**snapshot.transport, 'status': status, 'body_complete': complete})
    monkeypatch.setattr(d.client, 'download', response)
    acquired = d.call('download', args, context=context)
    assert acquired['contract'] == 'AcquisitionReceipt'
    assert d.store.get_artifact(acquired['value']['artifact']['raw_artifact_ref']) == d.client.body
    assert acquired['value']['snapshot']['transport']['status'] == status
    assert d.api.facts(context, {})['execution_result_refs'] == []
    assert d.api._completion(context) is None and d.last_outcome['status'] == 'partial'


def test_unpossessed_producer_evidence_is_rejected_before_download(driver):
    d = driver
    context, args = setup(d)
    args['declared_format']['producer_source_ref'] = 'source_not_received'
    calls = len(d.client.calls)
    context, key = d.selection('download', args, context=context)
    result = d.invoke(context, 'download', args, key)
    assert result['status'] == 'invalid' and len(d.client.calls) == calls
    assert d.api._completion(context) is None


def test_acquisition_cannot_be_presented_as_capability_predecessor(driver):
    d = driver
    context, args = setup(d, two=True)
    d.client.body = b'actual first output'
    acquired = d.call('download', args, context=context)
    calls = len(d.client.calls)
    arguments = {'objects': [args['object']], 'generation': 1,
        'predecessor_receipt_ref': acquired['source_ref']}
    context, key = d.selection('download_capability', arguments, context=context)
    outcome = d.invoke(context, 'download_capability', arguments, key)
    assert outcome['status'] == 'invalid'
    assert outcome['feedback']['code'] == 'appservice_receipt_contract_conflict'
    assert len(d.client.calls) == calls
