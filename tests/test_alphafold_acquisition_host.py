"""Actual Store/tool custody with engineered HTTP entities; no archive claim."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import AcquisitionError, PublicClients, SourceSnapshot
from gene_annotation_episode import alphafold_acquisition as af
from gene_annotation_episode import alphafold_acquisition_host as host
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_scientific_process_runtime import action


URL = 'https://alphafold.ebi.ac.uk/files/engineered-model_v99.pdb'
OTHER = 'https://alphafold.ebi.ac.uk/files/engineered-other_v123.pdb'
IDENTIFIER = 'P69905'
NATIVE = [{'uniprotAccession': IDENTIFIER, 'arbitrary_file': URL, 'native_confidence_like': [0, None]},
    {'uniprotAccession': IDENTIFIER, 'arbitrary_file': OTHER}]
RAW = ('  ' + json.dumps(NATIVE) + '\n').encode()
COORDINATES = b'Engineering file bytes; native identity deliberately not parsed.\x00\n'


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    return FixtureController(str(path), initial, 1 if len(path) == 1 else 2)


def _forbidden(*args, **kwargs):
    raise AssertionError('AlphaFold retained proof attempted forbidden work')


class Provider:
    def __init__(self, script=()):
        self.script, self.contexts = iter(script), []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        return response(context) if callable(response) else deepcopy(response)

    async def release(self, episode_id):
        pass


@pytest.fixture
def transport(monkeypatch):
    requests = []
    def http(client, service, url, params, media_type, **kwargs):
        assert service == af.SERVICE and kwargs['follow_redirects'] is False
        assert type(kwargs['max_bytes']) is int
        raw = RAW if url == af.alphafold_prediction_url(IDENTIFIER) else COORDINATES
        assert url in {af.alphafold_prediction_url(IDENTIFIER), URL}
        requests.append(url)
        return SourceSnapshot(service, url, deepcopy(params), '2026-10-31T00:00:00Z', raw, media_type,
            {'request': {'method': 'GET', 'url': url}, 'status': 200,
                'headers': {'content-type': media_type}, 'body_complete': True,
                'retained_body_bytes': len(raw), 'observed_body_bytes': len(raw),
                'declared_body_bytes': len(raw), 'response_byte_limit': kwargs['max_bytes']})
    monkeypatch.setattr(PublicClients, '_http', http)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.native_lifecycle.prepare_job', _forbidden)
    return requests


def _selected(registry, workflow, root, name, arguments, index, *, record):
    context = workflow.binding_context(root.source)
    key = f'{workflow.run_id}:{context.episode_id}:{index}'
    selected = {'kind': 'tool', 'tool': name, 'arguments': arguments}
    # Explicit ENGINEERING action records drive actual tool publication. No
    # action result, observation, Source or HTTP outcome is invented here.
    workflow.journal.save('runtime_actions', {'episode_id': context.episode_id,
        'decision_index': index, 'action': canonical(selected), 'result': None, 'credit': None})
    with registry.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
            tool_name=name, arguments=arguments, operation_key=key):
        outcome = asyncio.run(registry.execute_async(name, arguments, scope=plain(context.scope), operation_key=key))
    if record:
        workflow.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
            'action': canonical(selected), 'result': canonical(outcome), 'credit': None})
        workflow.receipts.receive(context.episode_id, outcome['record_refs'], kind='own_action', source_index=index)
    return outcome


@pytest.fixture
def acquired(tmp_path, transport):
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        workflow = Workflow(store, tools, Provider(), tmp_path / 'run', 'alphafold-host-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True, initial_known_record_refs=[])
        root = workflow.build('annotation', 'root', 'Retain selected engineering AlphaFold evidence.', scope)
        prediction_args = {'identifier': IDENTIFIER, 'max_bytes': 4096}
        metadata = _selected(tools, workflow, root, host.PREDICTION_TOOL, prediction_args, 0, record=True)
        assert metadata['status'] == 'completed' and af.validate_alphafold_receipt(metadata['result'])['acquired']
        source_ref = metadata['result']['source_ref']
        arguments = {'metadata_source_ref': source_ref, 'url_pointer': '/0/arbitrary_file',
            'file_format': 'pdb_3x_text', 'max_bytes': 4096}
        context = workflow.binding_context(root.source)
        yield SimpleNamespace(store=store, tools=tools, workflow=workflow, root=root, metadata=metadata,
            arguments=arguments, authority=(context, workflow.services.read_received_molecular_input), requests=transport)


def test_selection_binds_exact_received_original_bytes_and_producer(acquired):
    selection = host.prepare_alphafold_file(acquired.tools, acquired.arguments, authority=acquired.authority)
    assert selection == {'version': host.SELECTION_VERSION, 'arguments': acquired.arguments,
        'association': {'version': 'alphafold_advertised_file_association_v1',
            'metadata_source_ref': acquired.arguments['metadata_source_ref'],
            'metadata_artifact_ref': 'artifact_' + hashlib.sha256(RAW).hexdigest(),
            'url_pointer': '/0/arbitrary_file', 'advertised_url': URL, 'file_format': 'pdb_3x_text'},
        'metadata_operation': {'operation_key': f'{acquired.workflow.run_id}:{acquired.authority[0].episode_id}:0',
            'operation_ref': acquired.metadata['operation_ref']}}
    native = host._metadata(acquired.tools, acquired.arguments['metadata_source_ref'])[3]['native_json']
    assert native == NATIVE and af.alphafold_advertised_file_url(native, arguments=acquired.arguments) == URL
    assert acquired.requests == [af.alphafold_prediction_url(IDENTIFIER)]


def test_actual_caller_acquisition_operation_can_be_explicitly_received_without_invented_runtime_producer(tmp_path, transport):
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        outcome = asyncio.run(tools.execute_async(host.PREDICTION_TOOL,
            {'identifier': IDENTIFIER, 'max_bytes': 4096}, scope=scope, operation_key='caller-original-prediction'))
        assert outcome['status'] == 'completed'
        source_ref = outcome['result']['source_ref']
        workflow = Workflow(store, tools, Provider(), tmp_path / 'run', 'alphafold-caller-engineering',
            _controller, _credit, project_child_credit=_credit, episode_record_receipts=True,
            initial_known_record_refs=[source_ref, outcome['result']['data_ref']])
        root = workflow.build('annotation', 'root', 'Use explicitly supplied existing provider evidence.', scope)
        arguments = {'metadata_source_ref': source_ref, 'url_pointer': '/0/arbitrary_file',
            'file_format': 'pdb_3x_text', 'max_bytes': 4096}
        selection = host.prepare_alphafold_file(tools, arguments,
            authority=(workflow.binding_context(root.source), workflow.services.read_received_molecular_input))
        assert selection['metadata_operation']['operation_key'] == 'caller-original-prediction'
        assert store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 0


def test_source_shaped_caller_record_does_not_establish_producer_authority(acquired):
    original = acquired.store.get(acquired.arguments['metadata_source_ref'])
    payload = {key: value for key, value in original.items() if key not in {'id', 'record_type', 'origin'}}
    forged = acquired.store.put('source', payload, origin='caller')['id']
    acquired.workflow.receipts.receive(acquired.authority[0].episode_id, [forged], kind='initial')
    with pytest.raises(ContractError):
        host.prepare_alphafold_file(acquired.tools, {**acquired.arguments, 'metadata_source_ref': forged}, authority=acquired.authority)


def test_genuine_unreceived_metadata_source_still_cannot_select_a_download(acquired):
    other = _selected(acquired.tools, acquired.workflow, acquired.root, host.PREDICTION_TOOL,
        {'identifier': IDENTIFIER, 'max_bytes': 8192}, 2, record=False)
    assert other['status'] == 'completed'
    assert other['result']['source_ref'] != acquired.arguments['metadata_source_ref']
    with pytest.raises(ContractError, match='alphafold_file_metadata_not_received'):
        host.prepare_alphafold_file(acquired.tools,
            {**acquired.arguments, 'metadata_source_ref': other['result']['source_ref']}, authority=acquired.authority)


@pytest.mark.parametrize('change', ['receipt', 'missing', 'changed_bytes'])
def test_original_metadata_requires_an_actual_received_verified_file(acquired, change):
    reference = acquired.metadata['result']['data_ref']
    digest = reference[9:]
    path = acquired.store.path / 'artifacts' / digest[:2] / digest
    if change == 'receipt':
        acquired.store.db.execute('DELETE FROM runtime_record_receipts WHERE record_ref=?', (reference,))
    elif change == 'missing':
        path.unlink()
    else:
        path.write_bytes(b'engineered corrupt original entity')
    with pytest.raises(ContractError, match='alphafold_file_metadata_bytes_not_received'):
        host.prepare_alphafold_file(acquired.tools, acquired.arguments, authority=acquired.authority)


@pytest.mark.parametrize('change', ['missing', 'wrong_tool', 'arguments', 'operation_ref', 'native_json', 'action', 'outcome', 'pending_wrapper'])
def test_engineered_original_producer_tampering_is_rejected(acquired, change):
    row = acquired.store.db.execute('SELECT * FROM tool_operations').fetchone()
    if change == 'missing':
        acquired.store.db.execute('DELETE FROM tool_operations WHERE operation_key=?', (row['operation_key'],))
    elif change == 'wrong_tool':
        acquired.store.db.execute('UPDATE tool_operations SET name=?', ('public.rcsb.entry',))
    elif change == 'arguments':
        acquired.store.db.execute('UPDATE tool_operations SET arguments=?', (canonical({'identifier': 'OTHER', 'max_bytes': 4096}),))
    elif change == 'operation_ref':
        acquired.store.db.execute('UPDATE tool_operations SET id=?', ('operation_' + 'f' * 24,))
    elif change == 'native_json':
        source = acquired.store.get(acquired.metadata['result']['source_ref'])
        reference = source['auxiliary_artifact_refs'][0]
        value = host._control(acquired.store, reference)
        value['native_json'][0]['arbitrary_file'] = OTHER
        digest = reference[9:]
        (acquired.store.path / 'artifacts' / digest[:2] / digest).write_text(canonical(value))
    elif change == 'action':
        value = {'kind': 'tool', 'tool': host.PREDICTION_TOOL, 'arguments': {'identifier': 'OTHER', 'max_bytes': 4096}}
        acquired.store.db.execute('UPDATE runtime_actions SET action=?', (canonical(value),))
    elif change == 'outcome':
        value = deepcopy(acquired.metadata); value['feedback'] = {'code': 'engineered_tamper'}
        acquired.store.db.execute('UPDATE runtime_actions SET result=?', (canonical(value),))
    else:
        value = deepcopy(acquired.metadata)
        value['pending_work_after_action'] = {'version': 'forged', 'captured_at': 'invalid', 'items': []}
        acquired.store.db.execute('UPDATE runtime_actions SET result=?', (canonical(value),))
    with pytest.raises((ValueError, ContractError)):
        host.prepare_alphafold_file(acquired.tools, acquired.arguments, authority=acquired.authority)


@pytest.mark.parametrize('change', ['url', 'pointer', 'format', 'metadata_artifact', 'producer', 'extra'])
def test_mutable_selection_cannot_change_advertisement_before_publication(acquired, change):
    selection = host.prepare_alphafold_file(acquired.tools, acquired.arguments, authority=acquired.authority)
    if change == 'url': selection['association']['advertised_url'] = OTHER
    elif change == 'pointer': selection['association']['url_pointer'] = '/1/arbitrary_file'
    elif change == 'format': selection['association']['file_format'] = 'pdbx_mmcif_text'
    elif change == 'metadata_artifact': selection['association']['metadata_artifact_ref'] = 'artifact_' + 'f' * 64
    elif change == 'producer': selection['metadata_operation']['operation_ref'] = 'operation_' + 'f' * 24
    else: selection['extra'] = None
    with pytest.raises((ValueError, ContractError)):
        host.publish_alphafold_file(acquired.tools, acquired.arguments, None, selection=selection)
    assert len(acquired.requests) == 1


def test_actual_saved_file_authenticates_pending_action_without_original_entity_reads(acquired, monkeypatch):
    outcome = _selected(acquired.tools, acquired.workflow, acquired.root, host.FILE_TOOL, acquired.arguments, 1, record=False)
    assert outcome['status'] == 'completed' and len(acquired.requests) == 2
    source = acquired.store.get(outcome['result']['source_ref'])
    assert source['version'] is source['accession'] is None
    assert source['parent_source_refs'] == [acquired.arguments['metadata_source_ref']]
    assert len(source['auxiliary_artifact_refs']) == 1 and 'query_selection_ref' not in source
    assert outcome['record_refs'] == [source['id'], source['artifact_ref']]
    assert acquired.store.db.execute('SELECT result FROM runtime_actions WHERE decision_index=1').fetchone()[0] is None
    assert af.validate_alphafold_receipt(outcome['result']) == {'acquired': True,
        'source_ref': source['id'], 'data_ref': source['artifact_ref'], 'failure_code': None}
    forbidden = {acquired.metadata['result']['data_ref'], outcome['result']['data_ref']}
    actual_get, blocked = Store.get_artifact, []
    def guarded(store, reference):
        if reference in forbidden:
            blocked.append(reference); raise AssertionError('saved auth read an original entity')
        return actual_get(store, reference)
    monkeypatch.setattr(Store, 'get_artifact', guarded)
    monkeypatch.setattr(PublicClients, '_http', _forbidden)
    monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
    monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
    def metadata_only(context, reference, namespace, **kwargs):
        assert kwargs.get('file_format') is None
        return acquired.authority[1](context, reference, namespace, **kwargs)
    authority = acquired.authority[0], metadata_only
    host.authenticate_saved_alphafold_file(acquired.tools, acquired.arguments, authority=authority, outcome=outcome)
    assert blocked == []
    for field, value in [('source_ref', acquired.metadata['result']['source_ref']),
            ('data_ref', acquired.metadata['result']['data_ref']), ('acquired', False),
            ('failure_code', 'alphafold_response_incomplete')]:
        changed = deepcopy(outcome); changed['result'][field] = value
        with pytest.raises((ValueError, ContractError)):
            host.authenticate_saved_alphafold_file(acquired.tools, acquired.arguments, authority=authority, outcome=changed)


@pytest.mark.parametrize('with_response', [True, False])
def test_selected_http_failure_replays_exact_outcome_without_reacquisition(acquired, monkeypatch, with_response):
    original_http = PublicClients._http
    def fail_file(client, *args, **kwargs):
        snapshot = original_http(client, *args, **kwargs)
        assert snapshot.url == URL
        failed = replace(snapshot, transport={**snapshot.transport, 'status': 403}) if with_response else None
        raise AcquisitionError('engineered_alphafold_http_failure', snapshot=failed)
    monkeypatch.setattr(PublicClients, '_http', fail_file)
    outcome = _selected(acquired.tools, acquired.workflow, acquired.root, host.FILE_TOOL,
        acquired.arguments, 1, record=False)
    assert outcome['status'] == ('partial' if with_response else 'failed') and len(acquired.requests) == 2
    if with_response:
        receipt = af.validate_alphafold_receipt(outcome['result'])
        source = acquired.store.get(receipt['source_ref'])
        assert receipt == af.failed_alphafold_receipt('alphafold_http_not_success', source_ref=source['id'])
        assert host._control(acquired.store, source['request_ref'])['transport']['status'] == 403
        assert acquired.store.get_artifact(source['artifact_ref']) == COORDINATES
        assert outcome['record_refs'] == [source['id']]
    else:
        receipt = af.validate_alphafold_receipt(outcome['result'])
        assert not receipt['acquired'] and receipt['source_ref'] is receipt['data_ref'] is None
        assert outcome['record_refs'] == []
    forbidden = {acquired.metadata['result']['data_ref'],
        'artifact_' + hashlib.sha256(COORDINATES).hexdigest()}
    original_get, blocked = Store.get_artifact, []
    def guarded(store, reference):
        if reference in forbidden:
            blocked.append(reference)
            raise AssertionError('cached failure reopened an original entity')
        return original_get(store, reference)
    monkeypatch.setattr(Store, 'get_artifact', guarded)
    monkeypatch.setattr(PublicClients, '_http', _forbidden)
    monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
    monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
    def metadata_only(context, reference, namespace, **kwargs):
        assert kwargs.get('file_format') is None
        return acquired.authority[1](context, reference, namespace, **kwargs)
    context = acquired.authority[0]
    key = f'{acquired.workflow.run_id}:{context.episode_id}:1'
    with acquired.tools.current_invocation(context, read_received=metadata_only,
            tool_name=host.FILE_TOOL, arguments=acquired.arguments, operation_key=key):
        cached = asyncio.run(acquired.tools.execute_async(host.FILE_TOOL, acquired.arguments,
            scope=plain(context.scope), operation_key=key))
    assert cached == outcome and blocked == [] and len(acquired.requests) == 2
    assert acquired.store.db.execute('SELECT count(*) FROM tool_operations').fetchone()[0] == 2


def _tables(store):
    return {row[0]: sorted((tuple(value) for value in store.db.execute('SELECT * FROM "' + row[0] + '"')), key=repr)
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def _inventory(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob('*') if path.is_file()}


def test_actual_current_episode_download_pending_recovery_and_closed_replay(tmp_path, monkeypatch, transport):
    class LostReply(RuntimeError): pass
    with Store(tmp_path / 'store') as store:
        tools = ToolRegistry(store, clients=PublicClients(timeout=3))
        scope = {'subject_refs': store.create_problem(raw_sequence='MKWAA', molecule='protein')['subject_refs']}
        directory = tmp_path / 'run'
        question = ('Evaluate structural evidence for the supplied protein, keeping unresolved its correspondence '
            'to caller-selected reference data. These two acquisition steps do not settle a scientific conclusion.')
        def choose_file(context):
            result = context['last_local_outcome']['result']
            return action(host.FILE_TOOL, {'metadata_source_ref': result['source_ref'],
                'url_pointer': '/0/arbitrary_file', 'file_format': 'pdb_3x_text', 'max_bytes': 4096})
        provider = Provider([action(host.PREDICTION_TOOL, {'identifier': IDENTIFIER, 'max_bytes': 4096}), choose_file])
        def current_controller(path, initial):
            return FixtureController(str(path), initial, 2)
        def workflow(actor):
            return Workflow(store, tools, actor, directory, 'alphafold-current-workflow', current_controller, _credit,
                project_child_credit=_credit, root_role='improvement',
                episode_record_receipts=True, initial_known_record_refs=[])
        current = workflow(provider)
        root = current.build('improvement', 'root', question, scope)
        baseline = set(current.receipts.known(root.source.episode_id))
        assert current.permits_common_action(root.source, 'tool')
        assert {host.PREDICTION_TOOL, host.FILE_TOOL} <= {item['name'] for item in current.catalog(scope, source=root.source)}
        actual_execute, lost = ToolRegistry.execute_async, []
        async def lose(registry, name, args, **kwargs):
            result = await actual_execute(registry, name, args, **kwargs)
            if name == host.FILE_TOOL and not lost:
                assert result['status'] == 'completed'; lost.append(deepcopy(result)); raise LostReply()
            return result
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, 'execute_async', lose)
            with pytest.raises(LostReply): asyncio.run(root.run_async(current.context))
        assert len(transport) == 2 and len(provider.contexts) == 2
        assert store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0] == 1
        assert store.db.execute('SELECT result FROM runtime_actions WHERE decision_index=1').fetchone()[0] is None
        operations = list(store.db.execute('SELECT name,result FROM tool_operations ORDER BY operation_key'))
        metadata = next(json.loads(row['result'])['result'] for row in operations if row['name'] == host.PREDICTION_TOOL)
        file = lost[0]['result']
        assert af.validate_alphafold_receipt(metadata)['acquired'] and af.validate_alphafold_receipt(file)['acquired']
        file_source = store.get(file['source_ref'])
        assert file_source['accession'] is file_source['version'] is None
        assert file_source['uri'] == URL and store.get_artifact(file_source['artifact_ref']) == COORDINATES
        control = host._control(store, file_source['request_ref'])
        association = host._control(store, file_source['auxiliary_artifact_refs'][0])['selection']['association']
        native_file = af.alphafold_file_result(SourceSnapshot(af.SERVICE, file_source['uri'],
            control['request'], file_source['retrieved_at'], COORDINATES,
            store.get(file_source['artifact_ref'])['media_type'], control['transport']),
            arguments=control['request'], association=association,
            source_ref=file_source['id'], artifact_ref=file_source['artifact_ref'])
        assert native_file['observed_identity'] == {'native_model_id': None, 'state': 'not_parsed'}
        forbidden, actual_get, blocked = {metadata['data_ref'], file['data_ref']}, Store.get_artifact, []
        def guarded(current_store, reference):
            if reference in forbidden:
                blocked.append(reference); raise AssertionError('retained Workflow reopened an original entity')
            return actual_get(current_store, reference)
        monkeypatch.setattr(Store, 'get_artifact', guarded)
        monkeypatch.setattr(PublicClients, '_http', _forbidden)
        monkeypatch.setattr(af, 'resolve_alphafold_file_selection', _forbidden)
        monkeypatch.setattr(af, 'alphafold_prediction_result', _forbidden)
        actual_reader = WorkflowServices.read_received_molecular_input
        def metadata_only(services, context, reference, namespace, **kwargs):
            assert not (reference in {metadata['source_ref'], metadata['data_ref']}
                and kwargs.get('file_format') is not None)
            return actual_reader(services, context, reference, namespace, **kwargs)
        monkeypatch.setattr(WorkflowServices, 'read_received_molecular_input', metadata_only)
        recovered = workflow(Provider())
        recovered_root = recovered.build('improvement', 'root', question, scope)
        record = asyncio.run(recovered_root.run_async(recovered.context))
        final = asyncio.run(recovered_root.build_result(record)).as_record()
        episodes = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 1 and episodes[0]['state'] == 'yielded'
        assert json.loads(episodes[0]['path']) == [['improvement', 'root']]
        assert store.db.execute('SELECT count(*) FROM runtime_forms').fetchone()[0] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_report_attempts').fetchone()[0] == 0
        assert set(file) == {'acquired', 'source_ref', 'data_ref', 'failure_code'}
        contexts = EpisodeReturnRecords(store, recovered.run_id, failure_prefix='alphafold_selected_test_')
        owner = contexts.context(episodes[0]['episode_id'])
        returned = {metadata['source_ref'], metadata['data_ref'], file['source_ref'], file['data_ref']}
        assert set(recovered.receipts.known(owner.episode_id)) == baseline | returned
        assert {row[0] for row in store.db.execute('SELECT record_ref FROM runtime_record_receipts '
            "WHERE episode_id=? AND receipt_kind='own_action'", (owner.episode_id,))} == returned
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
        actions = [json.loads(row[0]) for row in store.db.execute('SELECT action FROM runtime_actions ORDER BY decision_index')]
        assert [value['kind'] for value in actions] == ['tool', 'tool']
        assert [value['tool'] for value in actions] == [host.PREDICTION_TOOL, host.FILE_TOOL]
        counts = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'tool_operations')}
        assert counts == dict(runtime_actions=2, runtime_observations=2, runtime_model_calls=2, tool_operations=2)
        before, before_files, before_archive = _tables(store), _inventory(store.path / 'artifacts'), _inventory(directory / 'archive')
        monkeypatch.setattr(ToolRegistry, 'execute_async', _forbidden)
        replay = workflow(Provider())
        replay_root = replay.build('improvement', 'root', question, scope)
        replay_record = asyncio.run(replay_root.run_async(replay.context))
        assert asyncio.run(replay_root.build_result(replay_record)).as_record() == final
        assert _tables(store) == before and _inventory(store.path / 'artifacts') == before_files and blocked == []
        assert _inventory(directory / 'archive') == before_archive
