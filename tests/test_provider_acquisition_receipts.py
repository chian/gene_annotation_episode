"""Engineered provider replies through actual custody owners; no live API claim.

The small native objects below are explicit engineering operands. ToolOperations
are written by the actual registry writer after the actual publisher returns;
there are no invented RuntimeAction completions or scientific child episodes.
"""
from copy import deepcopy
from dataclasses import replace
import asyncio
import hashlib
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import alphafold_acquisition as af
from gene_annotation_episode import alphafold_acquisition_host as host
from gene_annotation_episode import emdb_acquisition as emdb
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode.communication import plain
from gene_annotation_episode.data_acquisition_receipts import acquisition_receipt_schema
from gene_annotation_episode.domain import ContractError, canonical, identity
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController


SOURCE = 'source_' + 'a' * 24
PDB = 'https://alphafold.ebi.ac.uk/files/AF-P69905-F1-model_v6.pdb'
CIF = 'https://alphafold.ebi.ac.uk/files/AF-P69905-F2-model_v6.cif'
MODELS = [
    {'uniprotAccession': 'P69905', 'entryId': 'AF-P69905-F1', 'modelEntityId': 'AF-P69905-F1',
        'pdbUrl': PDB, 'globalMetricValue': 0, 'unknown': [None, False, 0]},
    {'uniprotAccession': 'P69905', 'modelEntityId': 'AF-P69905-F2', 'cifUrl': CIF,
        'sequenceStart': 101, 'sequenceEnd': 142, 'unknown': {'unit': 'uninterpreted'}},
]
ENTRY = {'emdb_id': 'EMD-8117', 'unknown': [None, 0, False],
    'structure_determination_list': [{'resolution': None}, {'resolution': {'value': 0, 'unit': 'native'}}]}
FILE_BYTES = b'Engineered selected representation; native identity is not parsed.\x00\n'


def _forbidden(*args, **kwargs):
    raise AssertionError('receipt verification attempted network, model or native work')


class NoModel:
    complete = _forbidden
    release = _forbidden


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    return FixtureController(str(path), initial, 1)


def _snapshot(provider='alphafold', *, native=None, raw=None, arguments=None, url=None):
    if arguments is None:
        arguments = ({'identifier': 'P69905', 'max_bytes': 8192} if provider == 'alphafold'
            else {'entry_id': 'EMD-8117', 'max_bytes': 8192})
    if raw is None:
        native = (MODELS if provider == 'alphafold' else ENTRY) if native is None else native
        raw = ('  ' + json.dumps(native, separators=(',', ':')) + '\n').encode()
    if url is None:
        url = (af.alphafold_prediction_url(arguments['identifier']) if provider == 'alphafold'
            else emdb.emdb_entry_url(arguments['entry_id']))
    return SourceSnapshot(provider, url, deepcopy(arguments), '2026-11-01T00:00:00Z', raw,
        'application/json', {'request': {'method': 'GET', 'url': url}, 'status': 200,
            'headers': {'content-type': 'application/json'}, 'body_complete': True,
            'retained_body_bytes': len(raw), 'observed_body_bytes': len(raw),
            'declared_body_bytes': len(raw), 'response_byte_limit': arguments['max_bytes'],
            'request_policy': {'automatic_redirects': False, 'timeout_seconds': 3}})


def _value(snapshot):
    return af.alphafold_prediction_value(snapshot, arguments=snapshot.request,
        artifact_ref='artifact_' + hashlib.sha256(snapshot.content).hexdigest())


def _publish(registry, key, name, arguments, scope, publisher, *args, **kwargs):
    """Actual publication and ToolOp writer, with an engineered caller key."""
    token = registry._publications.set([])
    try:
        with registry.store.transaction():
            value, refs = publisher(registry, arguments, *args, **kwargs)
            acquired = value.get('acquired', not value.get('issues'))
            outcome = {'status': 'completed' if acquired else 'failed',
                'operation_ref': identity('operation', {'key': key, 'name': name, 'arguments': arguments}),
                'record_refs': refs, 'changed_record_refs': refs, 'result': value,
                'feedback': None if acquired else {'category': 'acquisition', 'code': value['failure_code']}}
            registry._save(key, name, arguments, scope, outcome)
    finally:
        registry._publications.reset(token)
    return outcome


def _rows(store):
    return {name: sorted((tuple(row) for row in store.db.execute('SELECT * FROM "' + name + '"')), key=repr)
        for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _selected(tools, workflow, root, name, arguments, index):
    """Engineering action selection; actual registry returns its actual outcome."""
    context = workflow.binding_context(root.source)
    key = f'{workflow.run_id}:{context.episode_id}:{index}'
    action = {'kind': 'tool', 'tool': name, 'arguments': arguments}
    workflow.journal.save('runtime_actions', {'episode_id': context.episode_id,
        'decision_index': index, 'action': canonical(action), 'result': None, 'credit': None})
    with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
            tool_name=name, arguments=arguments, operation_key=key):
        outcome = asyncio.run(tools.execute_async(name, arguments, scope=plain(context.scope), operation_key=key))
    workflow.journal.save('runtime_actions', {'episode_id': context.episode_id,
        'decision_index': index, 'action': canonical(action), 'result': canonical(outcome), 'credit': None})
    workflow.receipts.receive(context.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
    return outcome, context, key


@pytest.fixture
def caller(tmp_path, monkeypatch):
    monkeypatch.setattr(PublicClients, '_http', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_lifecycle.prepare_job', _forbidden)
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store)
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        snapshot = _snapshot()
        outcome = _publish(tools, 'engineered-original-metadata', host.PREDICTION_TOOL,
            snapshot.request, scope, host.publish_alphafold_prediction_receipt, snapshot)
        assert outcome['result']['acquired']
        source = store.get(outcome['result']['source_ref'])
        workflow = Workflow(store, tools, NoModel(), tmp_path / 'run', 'provider-receipt-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True,
            initial_known_record_refs=outcome['record_refs'])
        root = workflow.build('annotation', 'root', 'Use an explicitly received existing data File.', scope)
        context = workflow.binding_context(root.source)
        arguments = {'metadata_source_ref': source['id'], 'url_pointer': '/1/cifUrl',
            'file_format': 'pdbx_mmcif_text', 'max_bytes': 8192}
        yield SimpleNamespace(store=store, tools=tools, scope=scope, snapshot=snapshot,
            metadata=outcome, source=source, workflow=workflow, context=context,
            authority=(context, workflow.services.read_received_molecular_input), arguments=arguments)


def test_source_free_value_shares_literal_legacy_projection_and_preserves_every_model():
    snapshot = _snapshot()
    value = _value(snapshot)
    assert 'source_ref' not in value and value['native_json'] == MODELS
    assert af.alphafold_prediction_identity(value) == 'confirmed'
    legacy = af.alphafold_prediction_result(snapshot, arguments=snapshot.request,
        source_ref=SOURCE, artifact_ref=value['raw_artifact_ref'])
    assert legacy == af.alphafold_prediction_result_from_value(value, source_ref=SOURCE)
    assert set(legacy) == {'version', 'source_ref', 'raw_artifact_ref', 'requested',
        'response', 'parse_state', 'native_json', 'issues'}
    assert legacy['version'] == 'alphafold_prediction_result_v1'
    receipt = af.alphafold_prediction_receipt(value, source_ref=SOURCE)
    assert receipt == {'acquired': True, 'source_ref': SOURCE,
        'data_ref': value['raw_artifact_ref'], 'failure_code': None}
    value['native_json'][0]['unknown'].append('detached')
    assert legacy['native_json'] == json.loads(snapshot.content) == MODELS


@pytest.mark.parametrize('native,state', [
    ([], 'unavailable'), ({'uniprotAccession': 'P69905'}, 'unavailable'),
    (None, 'unavailable'), (False, 'unavailable'), (['P69905'], 'unavailable'),
    ([{}], 'unavailable'), ([{'uniprotAccession': None}], 'unavailable'),
    ([{'uniprotAccession': 69905}], 'unavailable'),
    ([{'uniprotAccession': 'p69905'}], 'conflict'),
    ([{'uniprotAccession': 'P69905-2'}], 'conflict'),
    ([MODELS[0], {'uniprotAccession': 'OTHER'}], 'conflict'),
    ([MODELS[0], {'uniprotAccession': 'P69905', 'entryId': 'old', 'modelEntityId': 'new'}], 'conflict'),
    ([{'uniprotAccession': 'P69905', 'entryId': False}], 'unavailable'),
    ([{'uniprotAccession': 'P69905', 'modelEntityId': 17}], 'unavailable'),
    ([{'uniprotAccession': 'P69905', 'entryId': ''}], 'unavailable'),
])
def test_prediction_identity_never_uses_first_row_url_alias_or_case_folding(native, state):
    snapshot = _snapshot(raw=json.dumps(native).encode())
    value = _value(snapshot)
    assert value['native_json'] == native and af.alphafold_prediction_identity(value) == state
    receipt = af.alphafold_prediction_receipt(value, source_ref=SOURCE)
    assert receipt == af.failed_alphafold_receipt('alphafold_prediction_identity_' + state, source_ref=SOURCE)
    # The legacy record continues to retain scalars/nulls without inventing identity.
    assert af.alphafold_prediction_result_from_value(value, source_ref=SOURCE)['native_json'] == native


def test_explicit_uniprot_match_does_not_select_fragments_or_require_quality_or_model_identifiers():
    native = [{'uniprotAccession': 'P69905', 'entryId': 'literal-fragment2', 'quality': None},
        {'uniprotAccession': 'P69905', 'modelEntityId': 'literal-fragment1', 'quality': -999},
        {'uniprotAccession': 'P69905'}]
    value = _value(_snapshot(native=native))
    assert af.alphafold_prediction_receipt(value, source_ref=SOURCE)['acquired']
    assert value['native_json'] == native


@pytest.mark.parametrize('aliases', [
    {'entryId': None}, {'modelEntityId': None}, {'entryId': None, 'modelEntityId': None},
    {'entryId': None, 'modelEntityId': 'AF-P69905-F1'},
    {'entryId': 'AF-P69905-F1', 'modelEntityId': None},
])
def test_optional_null_model_alias_does_not_erase_exact_uniprot_identity(aliases):
    native = [{'uniprotAccession': 'P69905', **aliases}, MODELS[1]]
    value = _value(_snapshot(native=native))
    assert af.alphafold_prediction_identity(value) == 'confirmed'
    assert af.alphafold_prediction_receipt(value, source_ref=SOURCE)['acquired']
    assert value['native_json'] == native


@pytest.mark.parametrize('changes,code', [
    ({'status': 404}, 'alphafold_http_not_success'),
    ({'status': None}, 'alphafold_transport_metadata_unavailable'),
    ({'body_complete': False}, 'alphafold_response_incomplete'),
    ({'retained_body_bytes': 0}, 'alphafold_transport_metadata_unavailable'),
    ({'response_byte_limit': True}, 'alphafold_transport_metadata_unavailable'),
    ({'observed_body_bytes': 0}, 'alphafold_response_incomplete'),
    ({'declared_body_bytes': 0}, 'alphafold_response_incomplete'),
])
def test_prediction_identity_cannot_override_unconfirmed_transfer(changes, code):
    snapshot = _snapshot()
    value = _value(replace(snapshot, transport={**snapshot.transport, **changes}))
    assert af.alphafold_prediction_identity(value) == 'confirmed'
    assert af.alphafold_prediction_receipt(value, source_ref=SOURCE) == af.failed_alphafold_receipt(code, source_ref=SOURCE)


@pytest.mark.parametrize('provider', [af, emdb])
@pytest.mark.parametrize('change', [
    {'acquired': 1}, {'source_ref': None}, {'data_ref': None}, {'failure_code': 'unknown'},
    {'source_ref': SOURCE + '\n'}, {'data_ref': 'artifact_' + 'f' * 63}, {'extra': None},
])
def test_common_four_field_authority_rejects_shape_type_and_reference_relationships(provider, change):
    validate = provider.validate_alphafold_receipt if provider is af else provider.validate_emdb_receipt
    with pytest.raises(ContractError):
        validate({'acquired': True, 'source_ref': SOURCE, 'data_ref': 'artifact_' + 'f' * 64,
            'failure_code': None, **change})


@pytest.mark.parametrize('provider', [af, emdb])
def test_failure_helpers_never_invent_a_source_or_data_and_share_actual_common_schema(provider):
    if provider is af:
        failed, schema, codes = af.failed_alphafold_receipt, af.alphafold_receipt_schema, af.ALPHAFOLD_FAILURE_CODES
    else:
        failed, schema, codes = emdb.failed_emdb_receipt, emdb.emdb_receipt_schema, emdb.EMDB_FAILURE_CODES
    assert schema() == acquisition_receipt_schema(failure_codes=codes)
    assert failed('data_acquisition_failed') == {'acquired': False, 'source_ref': None,
        'data_ref': None, 'failure_code': 'data_acquisition_failed'}
    assert Draft202012Validator(schema()).is_valid(failed('data_acquisition_failed', source_ref=SOURCE))
    with pytest.raises(ContractError):
        failed('unbounded-arbitrary-failure')


def test_new_metadata_source_retains_private_value_raw_bytes_and_explicit_data_only(caller):
    source, outcome = caller.source, caller.metadata
    assert outcome['record_refs'] == [source['id'], source['artifact_ref']]
    assert caller.store.get_artifact(source['artifact_ref']) == caller.snapshot.content
    assert source['provider'] == 'alphafold' and source['version'] is None and source['accession'] == 'P69905'
    value = host._control(caller.store, source['auxiliary_artifact_refs'][0])
    assert value == _value(caller.snapshot) and 'source_ref' not in value
    known = set(caller.workflow.receipts.known(caller.context.episode_id))
    assert {source['id'], source['artifact_ref']} <= known
    assert {source['request_ref'], *source['auxiliary_artifact_refs']}.isdisjoint(known)
    selected = host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
    assert selected['association']['advertised_url'] == CIF
    assert selected['association']['url_pointer'] == '/1/cifUrl'
    assert selected['association']['metadata_artifact_ref'] == source['artifact_ref']
    assert selected['metadata_operation']['operation_key'] == 'engineered-original-metadata'
    assert caller.store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1
    for table in ('runtime_actions', 'runtime_model_calls', 'runtime_observations'):
        assert caller.store.db.execute('SELECT count(*) FROM ' + table).fetchone()[0] == 0


@pytest.mark.parametrize('provider', ['alphafold', 'emdb'])
@pytest.mark.parametrize('kind', ['http', 'incomplete', 'parse', 'identity', 'request'])
def test_captured_failure_publishes_source_only_and_preserves_native_entity(tmp_path, provider, kind):
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store)
        snapshot = _snapshot(provider)
        args = deepcopy(snapshot.request)
        if kind == 'http': snapshot = replace(snapshot, transport={**snapshot.transport, 'status': 403})
        elif kind == 'incomplete': snapshot = replace(snapshot, transport={**snapshot.transport, 'body_complete': False})
        elif kind == 'parse': snapshot = _snapshot(provider, raw=b'{')
        elif kind == 'identity': snapshot = _snapshot(provider, native=[{'uniprotAccession': 'OTHER'}]
            if provider == 'alphafold' else {'emdb_id': 'EMD-0008117'})
        else: snapshot = replace(snapshot, url='https://example.invalid/original-request')
        publisher = host.publish_alphafold_prediction_receipt if provider == 'alphafold' else emdb.publish_emdb_entry_receipt
        token = tools._publications.set([])
        try:
            receipt, refs = publisher(tools, args, snapshot)
        finally:
            tools._publications.reset(token)
        source = store.get(receipt['source_ref'])
        assert not receipt['acquired'] and receipt['data_ref'] is None
        assert refs == [source['id']] and receipt['failure_code'].startswith(provider + '_')
        assert store.get_artifact(source['artifact_ref']) == snapshot.content
        assert source['uri'] == snapshot.url
        assert host._control(store, source['request_ref']) == {'request': snapshot.request, 'transport': snapshot.transport}


@pytest.mark.parametrize('native,code', [
    ({}, 'native_entry_id_missing'), ({'emdb_id': None}, 'native_entry_id_null'),
    ({'emdb_id': False}, 'native_entry_id_invalid'), ({'emdb_id': 'EMD-8118'}, 'native_entry_id_differs_from_request'),
    ([], 'response_not_object'), (0, 'response_not_object'),
])
def test_emdb_receipt_reuses_exact_native_id_qualification_without_request_fill(native, code):
    snapshot = _snapshot('emdb', raw=json.dumps(native).encode())
    result = emdb.emdb_entry_result(snapshot, arguments=snapshot.request,
        source_ref=SOURCE, artifact_ref='artifact_' + hashlib.sha256(snapshot.content).hexdigest())
    assert result['native_json'] == native
    assert emdb.emdb_entry_receipt(result) == emdb.failed_emdb_receipt('emdb_' + code, source_ref=SOURCE)


def test_emdb_success_keeps_all_native_fields_in_original_primary_file(tmp_path):
    snapshot = _snapshot('emdb')
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store)
        token = tools._publications.set([])
        try:
            receipt, refs = emdb.publish_emdb_entry_receipt(tools, snapshot.request, snapshot)
        finally:
            tools._publications.reset(token)
        source = store.get(receipt['source_ref'])
        assert receipt == {'acquired': True, 'source_ref': source['id'],
            'data_ref': source['artifact_ref'], 'failure_code': None}
        assert refs == [source['id'], source['artifact_ref']]
        assert json.loads(store.get_artifact(receipt['data_ref'])) == ENTRY
        assert source['accession'] == 'EMD-8117' and source['version'] is None


@pytest.mark.parametrize('kind', ['success', 'http', 'incomplete', 'service', 'uri', 'request', 'wire'])
def test_new_file_receipt_and_cached_auth_preserve_selected_representation_without_entity_reads(caller, monkeypatch, kind):
    selection = host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
    snapshot = _snapshot(raw=FILE_BYTES, arguments=caller.arguments, url=CIF)
    if kind == 'http': snapshot = replace(snapshot, transport={**snapshot.transport, 'status': 404})
    elif kind == 'incomplete': snapshot = replace(snapshot, transport={**snapshot.transport, 'body_complete': False})
    elif kind == 'service': snapshot = replace(snapshot, service='literal-other-service')
    elif kind == 'uri': snapshot = replace(snapshot, url='https://example.invalid/retained-actual')
    elif kind == 'request': snapshot = replace(snapshot, request={**snapshot.request, 'max_bytes': 4096})
    elif kind == 'wire': snapshot = replace(snapshot, transport={**snapshot.transport,
        'request': {'method': 'GET', 'url': 'https://example.invalid/actual-wire'}})
    outcome = _publish(caller.tools, 'engineered-original-file', host.FILE_TOOL, caller.arguments,
        caller.scope, host.publish_alphafold_file_receipt, snapshot, selection=selection)
    receipt = outcome['result']
    assert receipt['acquired'] == (kind == 'success')
    source = caller.store.get(receipt['source_ref'])
    assert source['version'] is source['accession'] is None
    assert source['parent_source_refs'] == [caller.source['id']]
    assert source['uri'] == snapshot.url
    assert caller.store.get_artifact(source['artifact_ref']) == FILE_BYTES
    evidence = host._control(caller.store, source['auxiliary_artifact_refs'][0])
    assert evidence == {'version': host.FILE_EVIDENCE_VERSION, 'selection': selection,
        'observed_snapshot_service': snapshot.service}
    assert outcome['record_refs'] == [source['id'], *([source['artifact_ref']] if kind == 'success' else [])]
    original_get, forbidden = Store.get_artifact, {source['artifact_ref'], caller.source['artifact_ref']}
    def controls_only(store, reference):
        assert reference not in forbidden, 'completed acquisition cache reopened original entity bytes'
        return original_get(store, reference)
    def metadata_only(context, reference, namespace, **kwargs):
        assert kwargs.get('file_format') is None
        return caller.authority[1](context, reference, namespace, **kwargs)
    monkeypatch.setattr(Store, 'get_artifact', controls_only)
    monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
    monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
    before = _rows(caller.store)
    host.authenticate_saved_alphafold_file(caller.tools, caller.arguments,
        authority=(caller.context, metadata_only), outcome=outcome)
    assert _rows(caller.store) == before
    changed = deepcopy(outcome)
    changed['result']['data_ref'] = caller.source['artifact_ref']
    with pytest.raises((ValueError, ContractError)):
        host.authenticate_saved_alphafold_file(caller.tools, caller.arguments,
            authority=(caller.context, metadata_only), outcome=changed)


def test_new_file_receipt_confirms_transfer_without_claiming_native_model_identity(caller):
    selection = host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
    snapshot = _snapshot(raw=FILE_BYTES, arguments=caller.arguments, url=CIF)
    legacy = af.alphafold_file_result(snapshot, arguments=caller.arguments,
        association=selection['association'], source_ref=SOURCE,
        artifact_ref='artifact_' + hashlib.sha256(FILE_BYTES).hexdigest())
    assert legacy['observed_identity'] == {'native_model_id': None, 'state': 'not_parsed'}
    assert af.alphafold_file_receipt(legacy)['acquired']
    assert set(legacy) == {'version', 'source_ref', 'file', 'requested', 'response', 'association', 'observed_identity', 'issues'}


def test_new_file_no_response_failure_authenticates_without_controls_or_source(caller, monkeypatch):
    def no_response(registry, arguments):
        return af.failed_alphafold_receipt('data_acquisition_failed'), []
    outcome = _publish(caller.tools, 'engineered-no-response', host.FILE_TOOL,
        caller.arguments, caller.scope, no_response)
    before = _rows(caller.store)
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    host.authenticate_saved_alphafold_file(caller.tools, caller.arguments,
        authority=caller.authority, outcome=outcome)
    assert _rows(caller.store) == before and outcome['record_refs'] == []


def test_cached_file_rechecks_current_metadata_admission_before_private_controls(caller, monkeypatch):
    selection = host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
    snapshot = _snapshot(raw=FILE_BYTES, arguments=caller.arguments, url=CIF)
    outcome = _publish(caller.tools, 'engineered-original-file', host.FILE_TOOL, caller.arguments,
        caller.scope, host.publish_alphafold_file_receipt, snapshot, selection=selection)
    other = Workflow(caller.store, caller.tools, NoModel(), caller.store.path.parent / 'other-run',
        'provider-unreceived-engineering', _controller, _credit, project_child_credit=_credit,
        episode_record_receipts=True, initial_known_record_refs=[])
    root = other.build('annotation', 'root', 'Unreceived metadata confers no File selection.', caller.scope)
    authority = other.binding_context(root.source), other.services.read_received_molecular_input
    monkeypatch.setattr(Store, 'get_artifact', _forbidden)
    for action in (lambda: host.prepare_alphafold_file(caller.tools, caller.arguments, authority=authority),
            lambda: host.authenticate_saved_alphafold_file(caller.tools, caller.arguments,
                authority=authority, outcome=outcome)):
        with pytest.raises(ContractError, match='alphafold_file_metadata_not_received'):
            action()


def test_changed_private_value_bytes_deny_file_selection_without_new_publication(caller):
    reference = caller.source['auxiliary_artifact_refs'][0]
    digest = reference[9:]
    path = caller.store.path / 'artifacts' / digest[:2] / digest
    original, before = path.read_bytes(), _rows(caller.store)
    try:
        path.write_bytes(original + b' ')
        with pytest.raises(ContractError, match='^artifact_digest_mismatch$'):
            host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
        assert _rows(caller.store) == before
    finally:
        path.write_bytes(original)


def test_legacy_file_publisher_and_cached_rich_form_remain_literal(caller, monkeypatch):
    selection = host.prepare_alphafold_file(caller.tools, caller.arguments, authority=caller.authority)
    snapshot = _snapshot(raw=FILE_BYTES, arguments=caller.arguments, url=CIF)
    outcome = _publish(caller.tools, 'engineered-original-legacy-file', host.FILE_TOOL,
        caller.arguments, caller.scope, host.publish_alphafold_file, snapshot, selection=selection)
    value = af.validate_alphafold_file_result(outcome['result'])
    source = caller.store.get(value['source_ref'])
    assert host._control(caller.store, source['auxiliary_artifact_refs'][0]) == selection
    assert value['observed_identity'] == {'native_model_id': None, 'state': 'not_parsed'}
    original_get = Store.get_artifact
    def controls_only(store, reference):
        assert reference not in {caller.source['artifact_ref'], source['artifact_ref']}
        return original_get(store, reference)
    monkeypatch.setattr(Store, 'get_artifact', controls_only)
    monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
    monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
    before = _rows(caller.store)
    host.authenticate_saved_alphafold_file(caller.tools, caller.arguments,
        authority=caller.authority, outcome=outcome)
    assert _rows(caller.store) == before


def test_legacy_prediction_toolop_and_file_cache_need_no_new_value_or_entity_reread(tmp_path, monkeypatch):
    snapshot = _snapshot()
    def legacy_prediction(registry, arguments, observed):
        source = registry._source(af.SERVICE, None, snapshot=observed, accession=arguments['identifier'])
        value = af.alphafold_prediction_result(observed, arguments=arguments,
            source_ref=source['id'], artifact_ref=source['artifact_ref'])
        return value, [source['id']]
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store)
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        metadata = _publish(tools, 'legacy-caller-metadata', host.PREDICTION_TOOL,
            snapshot.request, scope, legacy_prediction, snapshot)
        source = store.get(metadata['result']['source_ref'])
        assert 'auxiliary_artifact_refs' not in source
        workflow = Workflow(store, tools, NoModel(), tmp_path / 'run', 'legacy-caller-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True,
            initial_known_record_refs=[source['id'], source['artifact_ref']])
        root = workflow.build('annotation', 'root', 'Use literal previously received metadata.', scope)
        context = workflow.binding_context(root.source)
        authority = context, workflow.services.read_received_molecular_input
        arguments = {'metadata_source_ref': source['id'], 'url_pointer': '/0/pdbUrl',
            'file_format': 'pdb_3x_text', 'max_bytes': 8192}
        selection = host.prepare_alphafold_file(tools, arguments, authority=authority)
        assert selection['association']['advertised_url'] == PDB
        file_snapshot = _snapshot(raw=FILE_BYTES, arguments=arguments, url=PDB)
        outcome = _publish(tools, 'legacy-caller-file', host.FILE_TOOL, arguments,
            scope, host.publish_alphafold_file, file_snapshot, selection=selection)
        original_get = Store.get_artifact
        def controls_only(current, reference):
            assert reference not in {source['artifact_ref'], outcome['result']['file']['artifact_ref']}
            return original_get(current, reference)
        monkeypatch.setattr(Store, 'get_artifact', controls_only)
        monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
        monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
        monkeypatch.setattr(PublicClients, '_http', _forbidden)
        before = _rows(store)
        host.authenticate_saved_alphafold_file(tools, arguments, authority=authority, outcome=outcome)
        assert _rows(store) == before


@pytest.mark.parametrize('provider', ['alphafold', 'emdb'])
def test_actual_same_episode_dispatch_returns_only_confirmation_and_explicit_data_then_caches(tmp_path, monkeypatch, provider):
    requests = []
    metadata = _snapshot(provider)
    file_arguments = {}
    def http(client, service, url, params, media_type, **kwargs):
        assert service == provider and kwargs['follow_redirects'] is False
        assert type(kwargs['max_bytes']) is int and kwargs['max_bytes'] == 8192
        requests.append(url)
        observed = metadata if url == metadata.url else _snapshot(raw=FILE_BYTES, arguments=file_arguments, url=CIF)
        assert url in {metadata.url, CIF}
        return replace(observed, request=deepcopy(params))
    monkeypatch.setattr(PublicClients, '_http', http)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_lifecycle.prepare_job', _forbidden)
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        workflow = Workflow(store, tools, NoModel(), tmp_path / 'run', 'ordinary-provider-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Acquire explicitly selected provider data in this episode.', scope)
        name = host.PREDICTION_TOOL if provider == 'alphafold' else 'public.emdb.entry'
        baseline = set(workflow.receipts.known(workflow.binding_context(root.source).episode_id))
        outcome, context, key = _selected(tools, workflow, root, name, metadata.request, 0)
        validate = af.validate_alphafold_receipt if provider == 'alphafold' else emdb.validate_emdb_receipt
        receipt = validate(outcome['result'])
        assert receipt['acquired'] and outcome['status'] == 'completed'
        source = store.get(receipt['source_ref'])
        assert receipt['data_ref'] == source['artifact_ref']
        assert store.get_artifact(receipt['data_ref']) == metadata.content
        expected = baseline | {source['id'], source['artifact_ref']}
        assert set(workflow.receipts.known(context.episode_id)) == expected
        private = {source['request_ref'], *source.get('auxiliary_artifact_refs', [])}
        if provider == 'alphafold':
            file_arguments.update(metadata_source_ref=source['id'], url_pointer='/1/cifUrl',
                file_format='pdbx_mmcif_text', max_bytes=8192)
            outcome, context, key = _selected(tools, workflow, root, host.FILE_TOOL, file_arguments, 1)
            receipt = af.validate_alphafold_receipt(outcome['result'])
            assert receipt['acquired'] and outcome['status'] == 'completed'
            source = store.get(receipt['source_ref'])
            assert source['uri'] == CIF and store.get_artifact(receipt['data_ref']) == FILE_BYTES
            expected |= {source['id'], source['artifact_ref']}
            private |= {source['request_ref'], *source.get('auxiliary_artifact_refs', [])}
            name, arguments = host.FILE_TOOL, file_arguments
        else:
            arguments = metadata.request
        assert set(workflow.receipts.known(context.episode_id)) == expected
        assert private.isdisjoint(expected)
        assert requests == [metadata.url, *([CIF] if provider == 'alphafold' else [])]
        original_get = Store.get_artifact
        entity_refs = {ref for ref in expected if ref.startswith('artifact_')} - baseline
        def controls_only(current, reference):
            assert reference not in entity_refs
            return original_get(current, reference)
        def metadata_only(current, reference, namespace, **kwargs):
            assert kwargs.get('file_format') is None
            return workflow.services.read_received_molecular_input(current, reference, namespace, **kwargs)
        monkeypatch.setattr(Store, 'get_artifact', controls_only)
        monkeypatch.setattr(PublicClients, '_http', _forbidden)
        monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
        monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
        before = _rows(store)
        with tools.current_invocation(context, read_received=metadata_only,
                tool_name=name, arguments=arguments, operation_key=key):
            cached = asyncio.run(tools.execute_async(name, arguments, scope=plain(context.scope), operation_key=key))
        assert cached == outcome and _rows(store) == before
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == (2 if provider == 'alphafold' else 1)


@pytest.mark.parametrize('provider', ['alphafold', 'emdb'])
def test_actual_no_response_dispatch_returns_finite_failure_without_source_or_data(tmp_path, monkeypatch, provider):
    calls = []
    def no_response(*args, **kwargs):
        calls.append('one selected request')
        raise AcquisitionError('provider_connection_failed')
    monkeypatch.setattr(PublicClients, '_http', no_response)
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store)
        monkeypatch.setattr(tools, '_source', _forbidden)
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        workflow = Workflow(store, tools, NoModel(), tmp_path / 'run', 'provider-no-response-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Retain an honest acquisition failure in this episode.', scope)
        args = _snapshot(provider).request
        name = host.PREDICTION_TOOL if provider == 'alphafold' else 'public.emdb.entry'
        outcome, context, key = _selected(tools, workflow, root, name, args, 0)
        validate = af.validate_alphafold_receipt if provider == 'alphafold' else emdb.validate_emdb_receipt
        receipt = validate(outcome['result'])
        assert not receipt['acquired'] and receipt['source_ref'] is receipt['data_ref'] is None
        assert outcome['record_refs'] == [] and outcome['status'] == 'failed'
        assert calls == ['one selected request']
        monkeypatch.setattr(PublicClients, '_http', _forbidden)
        before = _rows(store)
        with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                tool_name=name, arguments=args, operation_key=key):
            cached = asyncio.run(tools.execute_async(name, args, scope=plain(context.scope), operation_key=key))
        assert cached == outcome and _rows(store) == before
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1
        assert store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 0
