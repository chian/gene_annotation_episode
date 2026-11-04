"""Production API executor/host with real records and synthetic native replies.

Selections are saved explicitly here; shared method_loop and live service
verification remain separate requirements.
"""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.state import Store
from test_api_bvbrc_appservice import CONFIG, PREFIX, SHOCK_UUID, metadata
from test_bvbrc_appservice_custody import SavedRecords, request
from test_bvbrc_appservice_inputs import Driver, NativeClient, retained_input, output_target


class ProductionDriver(Driver):
    def __init__(self, store, directory):
        self.saved, self.store = SavedRecords(store), store
        self.api = APIServiceExecution(store, run_id=self.saved.run_id, directory=directory,
            configuration={'selected-api': CONFIG},
            tool_registry=SimpleNamespace(store=store, clients={}),
            handoff_unit=2, acquired_record_unit=3)
        self.client = NativeClient()
        self.service = self.api.services['selected-api']
        self.service.client = self.client
        self.records, self.custody = self.api.appservice.records, self.api.appservice.custody
        self.last_outcome = None

    def invoke(self, context, suffix, args, key):
        outcome = asyncio.run(self.api.execute(context, PREFIX + suffix, args, key))
        self.last_outcome = outcome
        if outcome['status'] in {'completed', 'partial'}:
            index = int(key.rsplit(':', 1)[1])
            row = self.saved.journal.row('runtime_actions', context.episode_id, index)
            self.saved.journal.save('runtime_actions', {**row, 'result': canonical(outcome), 'credit': 0})
            self.saved.receipts.receive(context.episode_id, outcome['record_refs'],
                kind='own_action', source_index=index)
        return outcome

    def call(self, suffix, args, *, context=None):
        context, key = self.selection(suffix, args, context=context)
        outcome = self.invoke(context, suffix, args, key)
        assert outcome['status'] in {'completed', 'partial'}, outcome
        ref = outcome['result'].get('handoff_ref') or outcome['result']['support_receipt_ref']
        return self.records.read(ref)


@pytest.fixture
def driver(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('host verification attempted live transport')
    monkeypatch.setattr('socket.create_connection', forbidden)
    with Store(tmp_path / 'state') as store:
        yield ProductionDriver(store, tmp_path)


def test_actual_factory_preparation_is_support_only_and_recovery_makes_no_call(driver):
    d = driver
    context = d.tree()
    args = {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}}
    receipt = d.call('prepare', args)
    assert receipt['contract'] == 'PreparationReceipt'
    assert d.client.calls == []
    facts = d.api.facts(context, {})
    assert facts['bvbrc_appservice_support_refs'] == [receipt['source_ref']]
    assert facts['execution_handoff_refs'] == facts['execution_result_refs'] == []
    assert facts['execution_completed'] is False
    assert d.api.is_handoff_source(receipt['source_ref']) is False
    assert d.api.resolve(context, receipt['source_ref'], 'source') is True
    assert d.api.resolve(context, receipt['source_ref'], 'execution_result') is False
    key = receipt['value']['receipt']['origin']['operation_key']
    original_outcome = deepcopy(d.last_outcome)
    assert d.invoke(context, 'prepare', args, key) == original_outcome
    assert len(d.api.appservice._own_receipts(context)) == 1
    assert d.api.credit_view(context, {'known_record_refs': d.saved.receipts.known(context.episode_id),
        'initial_known_record_refs': []})['credit'] == 0


def test_create_upload_then_submit_uses_exact_submit_not_first_mutation(driver):
    d = driver
    context = d.tree(retained_input(d))
    preparation = d.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    node = 'https://shock.example.invalid/node/' + SHOCK_UUID
    d.client.value = [metadata(shock_url=node)['native_row']]
    created = d.call('workspace_create', {'objects': [{'target_id': 'query', 'data_binding_id': 'query',
        'creation_time': None}], 'options': {'createUploadNodes': 1}})
    assert d.api._completion(context) is None
    upload = d.call('upload', {'created_object': {'receipt_ref': created['source_ref'], 'row_pointer': '/result/0/0'},
        'input_binding_id': 'query', 'filename': 'query.fa'})
    assert upload['contract'] == 'UploadReceipt'
    assert d.api._completion(context) is None
    d.client.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
    handoff = d.call('submit', {'preparation_receipt_ref': preparation['source_ref'],
        'input_evidence_refs': [upload['source_ref']]})
    assert handoff['contract'] == 'TaskHandoff'
    assert [call[0] for call in d.client.calls] == ['rpc', 'upload', 'rpc']
    target = d.api.read_target(handoff['source_ref'], context.scope)
    assert target['execution_id'] == '123'
    snapshot = d.api._submission_snapshot(target)
    assert snapshot.request['rpc']['method'] == 'AppService.start_app2'
    assert d.api.scope(handoff['source_ref']) == plain(context.scope)
    assert d.api._read_handoff(handoff['source_ref'], context.scope)['receipt']['tool_name'] == PREFIX + 'submit'
    proof = d.api._completion(context)
    assert proof['operation_key'] == handoff['value']['original_task']['submission_operation_key']
    assert d.api.verify_completion(context, proof)
    assert d.api.facts(context, {})['execution_result_refs'] == []
    known = d.saved.receipts.known(context.episode_id)
    credit = d.api.credit_view(context, {'known_record_refs': known, 'initial_known_record_refs': []})
    assert credit['credit'] == 2 and credit['new_handoff_count'] == 1 and credit['new_acquired_record_count'] == 0
    assert d.store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_lost_submit_response_recovers_unknown_without_reissuing(driver, monkeypatch):
    d = driver
    context = d.tree()
    preparation = d.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    args = {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []}
    def interrupted(rpc):
        d.client.calls.append(('rpc', rpc))
        raise KeyboardInterrupt()
    monkeypatch.setattr(d.client, 'rpc', interrupted)
    context, key = d.selection('submit', args)
    with pytest.raises(KeyboardInterrupt):
        d.invoke(context, 'submit', args, key)
    result = d.invoke(context, 'submit', args, key)
    assert result['status'] == 'partial' and result['feedback']['code'] == 'issued_effect_unknown'
    assert d.api._completion(context) is None
    context, later = d.selection('submit', args)
    result = d.invoke(context, 'submit', args, later)
    assert result['status'] == 'invalid'
    assert len(d.client.calls) == 1


def test_submit_publication_interruption_recovers_same_task_and_receipt(driver, monkeypatch):
    d = driver
    context = d.tree()
    preparation = d.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    args = {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []}
    d.client.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
    publish = d.records.publish
    def interrupted(*arguments, **keywords):
        result = publish(*arguments, **keywords)
        assert result['contract'] == 'TaskHandoff'
        raise KeyboardInterrupt()
    monkeypatch.setattr(d.records, 'publish', interrupted)
    context, key = d.selection('submit', args)
    with pytest.raises(KeyboardInterrupt):
        d.invoke(context, 'submit', args, key)
    monkeypatch.setattr(d.records, 'publish', publish)
    outcome = d.invoke(context, 'submit', args, key)
    assert outcome['status'] == 'completed'
    assert d.api.read_target(outcome['result']['handoff_ref'], context.scope)['execution_id'] == '123'
    assert len(d.client.calls) == 1


def test_failed_task_acknowledgment_confirms_effect_without_completing_launch(driver):
    d = driver
    context = d.tree()
    preparation = d.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
    d.client.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'F'}
    receipt = d.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})
    assert receipt['contract'] == 'CommonReceipt'
    assert d.last_outcome['status'] == 'partial'
    assert d.api._completion(context) is None
    effect = d.api.selected_effects.read(receipt['value']['effect_receipt_refs'][0],
        original_job_owner=d.custody.original_job_owner(context))
    assert effect['state'] == 'confirmed' and effect['native_effect_identifiers']['task_id'] == '123'


def test_results_assignment_receives_original_handoff_through_both_returns(driver):
    d = driver
    d.tree()
    handoff = d.launch_task()
    context = d.results(handoff)
    d.api.initialize(context)
    assert d.api.appservice.initial_references(context) == [handoff['source_ref']]
    receipt = d.call('task_info', {'handoff_ref': handoff['source_ref'], 'file': 'job_result_id'}, context=context)
    assert receipt['contract'] == 'TaskInfoReceipt'
    assert d.api.facts(context, {})['execution_result_refs'] == []
    assert d.api._completion(context) is None


def test_original_service_versions_remain_explicit(driver):
    from gene_annotation_episode.api_services import validate_service_configuration
    value = deepcopy(CONFIG)
    value.pop('execution_contract')
    with pytest.raises(ValueError):
        validate_service_configuration('bvbrc_appservice', value)
    assert validate_service_configuration('uniprot', {'kind': 'api', 'service': 'uniprot'}) == {
        'kind': 'api', 'service': 'uniprot'}


def test_results_workspace_metadata_preserves_original_task_through_prepare(driver):
    d = driver
    query = request()
    obj = output_target(query)
    d.tree(query)
    handoff = d.launch_task()
    context = d.results(handoff)
    d.client.value = [[metadata(query['parameters']['output_path'], type='folder')['native_row'], None]]
    result = d.call('workspace_metadata', {'objects': [obj], 'options': {}}, context=context)
    assert result['contract'] == 'WorkspaceReceipt'
    assert result['value']['rows'][0]['valid']
    assert d.client.calls[-1][1]['method'] == 'Workspace.get'
    key = result['value']['receipt']['origin']['operation_key']
    directory = d.api._manifest(context) / 'actions' / digest(key)
    prepared = _read(directory / 'intent.json')['prepared']
    assert prepared['bound_inputs']['resolved']['original_task']['task_id'] == '123'
    assert d.api._completion(context) is None
