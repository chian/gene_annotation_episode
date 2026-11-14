import asyncio
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.a104.acquisition import SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a104.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.episodic_workflow.root.a104.api_selected_call import perform_selected_call
from gene_annotation_episode.episodic_workflow.root.a104.api_selected_effects import SelectedAPIEffects
from gene_annotation_episode.episodic_workflow.root.a104.execution_job_submission.api_job_execution.api_service import APIJobService as APIServiceExecution
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_custody import AppServiceCustody
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_inputs import AppServiceInputs
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_records import AppServiceRecords, provisional_receipt_ref
from gene_annotation_episode.episodic_workflow.root.a104.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from gene_annotation_episode.episodic_workflow.root.a104.communication import plain
from gene_annotation_episode.episodic_workflow.root.a104.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a104.practical_execution_state import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.appservice_transport_fixture import CONFIG, PREFIX, SHOCK_UUID, Client
from gene_annotation_episode.episodic_workflow.root.a104.tests.proteome_partner.commissioned_records_fixture import SavedRecords, selector

class NativeClient(Client):
    """In-memory native fixture; no network transport and no invented science."""

    def upload(self, url, supplied, *, filename):
        self.calls.append(('upload', url, supplied, filename))
        boundary = 'gene-annotation-' + hashlib.sha256(filename.encode() + b'\x00' + hashlib.sha256(supplied).digest()).hexdigest()
        prefix = f'--{boundary}\r\nContent-Disposition: form-data; name="upload"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
        sent = prefix + supplied + f'\r\n--{boundary}--\r\n'.encode()
        body = json.dumps({'status': 200, 'error': None, 'data': {'id': SHOCK_UUID, 'file': {'size': len(supplied), 'checksum': {'sha256': hashlib.sha256(supplied).hexdigest()}}}}).encode()
        return SourceSnapshot('bvbrc_analysis', url, {'kind': 'upload', 'node_url': url, 'filename': filename, 'input_bytes': len(supplied), 'input_sha256': hashlib.sha256(supplied).hexdigest(), 'multipart_field': 'upload', 'multipart_boundary': boundary}, '2026-10-24T12:00:00+00:00', body, 'application/json', {'status': 200, 'body_complete': True, 'received_body_bytes': len(body), 'effective_url': url, 'automatic_redirects': False, 'headers': {}, 'request': {'method': 'PUT', 'url': url, 'body_bytes': len(sent), 'body_sha256': hashlib.sha256(sent).hexdigest()}})

    def download(self, url, *, max_bytes, byte_range=None):
        self.calls.append(('download', url, byte_range))
        body = self.body
        assert len(body) <= max_bytes, 'this complete-response fixture exceeds the selected byte limit'
        return SourceSnapshot('bvbrc_analysis', url, {'kind': 'download', 'url': url, 'requested_byte_range': None if byte_range is None else list(byte_range), 'max_bytes': max_bytes}, '2026-10-24T12:00:00+00:00', body, 'application/json', {'status': 200, 'body_complete': True, 'received_body_bytes': len(body), 'effective_url': url, 'response_byte_limit': max_bytes, 'observed_body_bytes': len(body), 'retained_body_bytes': len(body), 'declared_body_bytes': len(body), 'automatic_redirects': False, 'headers': {'content-length': str(len(body))}, 'request': {'method': 'GET', 'url': url}})

class Driver:

    def __init__(self, store, tmp_path):
        self.saved = SavedRecords(store)
        self.store = store
        self.api = APIServiceExecution.__new__(APIServiceExecution)
        self.api.store, self.api.run_id, self.api.directory = (store, self.saved.run_id, tmp_path / 'execution')
        self.api.selected_effects = SelectedAPIEffects(tmp_path, run_id=self.saved.run_id)
        self.records = AppServiceRecords(self.api)
        self.custody = AppServiceCustody(store, self.saved.run_id, read_original_handoff=self.read_handoff)
        self.client = NativeClient()
        self.service = BVBRCAppServiceService(SimpleNamespace(store=store), CONFIG, client=self.client)
        self.bindings = AppServiceInputs(self.api, records=self.records, custody=self.custody)
        self.receipt_transform = None
        self.api.read_target = self.target

    def read_handoff(self, reference):
        record = self.records.read(reference)
        assert record['contract'] == 'TaskHandoff'
        value = record['value']
        return {'reference': reference, 'original_job_owner': value['original_job_owner'], 'origin_context': self.custody.context(value['receipt']['origin']['episode_id'])}

    def target(self, reference, scope):
        origin = self.read_handoff(reference)['origin_context']
        self.store.validate_scope(plain(origin.scope), parent_scope=plain(scope))
        return {'assignment': plain(origin.assignment), 'resource_id': origin.assignment['resource_id']}

    def tree(self, query=None):
        self.launch, self.context = self.saved.tree(query)
        self.api._manifest(self.context)
        return self.context

    def selection(self, suffix, args, *, context=None):
        context = self.context if context is None else context
        index = self.store.db.execute('SELECT COALESCE(MAX(decision_index),-1)+1 FROM runtime_actions WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()[0]
        key = f'{context.run_id}:{context.episode_id}:{index}'
        self.saved.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index, 'action': canonical({'kind': 'tool', 'tool': PREFIX + suffix, 'arguments': args}), 'result': None, 'credit': None})
        self.api._manifest(context)
        return (context, key)

    def bind(self, suffix, args, *, context=None):
        context, key = self.selection(suffix, args, context=context)
        value = self.bindings.bind_inputs(context, PREFIX + suffix, args, operation_key=key)
        query = self.target(context.assignment['handoff_ref'], context.scope)['assignment']['request'] if context.role == 'results' else plain(context.assignment)['request']
        prepared = self.service.prepare(PREFIX + suffix, query, args, scope=plain(context.scope), previous_events=[], selector=plain(context.assignment)['selector'] if context.role == 'results' else None, bound_inputs=value)
        return (context, key, prepared)

    def call(self, suffix, args, *, context=None, allow_failure=False):
        context, key, prepared = self.bind(suffix, args, context=context)
        directory = self.api._manifest(context) / 'actions' / digest(key)
        directory.mkdir(exist_ok=True)
        _immutable(directory / 'intent.json', {'run_id': context.run_id, 'episode_id': context.episode_id, 'operation_key': key, 'name': PREFIX + suffix, 'arguments': args, 'assignment_sha256': digest(context.assignment), 'prepared': prepared, 'started_at': '2026-10-24T12:00:00+00:00'})
        call = asyncio.run(perform_selected_call(self.api, context, self.service, prepared, operation_key=key, directory=directory, fresh=True))
        assert allow_failure or call['failure'] is None
        snapshot = call['snapshot']
        binding = None if snapshot is None else self.records.retain_snapshot(context, prepared, snapshot, operation_key=key)
        event = self.service.decode(prepared, snapshot)
        effects = call['effect_receipts']
        if effects:
            effects = self.api.selected_effects.record_outcome(_read(directory / 'effect_reservation.json'), confirm_appservice_effects(prepared, event, snapshot, snapshot_binding=binding, effect_receipts=effects))
        origin = self.records._origin(context, prepared, key)
        common = {'version': 'bvbrc_appservice_support_receipt_v1', 'receipt_ref': provisional_receipt_ref(origin), 'purpose': prepared['purpose'], 'origin': origin, 'snapshot': binding, 'effect_receipt_refs': [row['effect_ref'] for row in effects], 'status': 'ok', 'diagnostics': []}
        if suffix == 'download':
            return SimpleNamespace(context=context, key=key, prepared=prepared, directory=directory, snapshot=snapshot, binding=binding, event=event, common=common)
        value = build_appservice_receipt(prepared, event, snapshot, common_receipt=common, effect_receipts=effects)
        if self.receipt_transform is not None:
            value = self.receipt_transform(value)
            self.receipt_transform = None
        published = self.records.publish(context, value['contract'], value['value'], operation_key=key)
        refs = [published['source_ref']]
        if binding is not None:
            refs.append(binding['source_ref'])
        if (directory / 'definition_inputs.json').exists():
            refs.extend(_read(directory / 'definition_inputs.json')['source_refs'])
        self.complete(context, key, directory, published, refs)
        return published

    def complete(self, context, key, directory, result, refs):
        outcome = {'status': 'completed', 'record_refs': refs, 'changed_record_refs': refs, 'result': result, 'feedback': None}
        _immutable(directory / 'outcome.json', outcome)
        index = int(key.rsplit(':', 1)[1])
        old = self.saved.journal.row('runtime_actions', context.episode_id, index)
        self.saved.journal.save('runtime_actions', {**old, 'result': canonical(outcome), 'credit': 0})
        self.saved.receipts.receive(context.episode_id, refs, kind='own_action', source_index=index)

    def launch_task(self):
        preparation = self.call('prepare', {'definition': {'kind': 'packaged', 'required_application_id': 'Homology'}})
        self.client.value = {'id': '123', 'application_id': 'Homology', 'state_code': 'Q'}
        return self.call('submit', {'preparation_receipt_ref': preparation['source_ref'], 'input_evidence_refs': []})

    def results(self, handoff, *, selection=None, index=3):
        self.saved.admit(self.launch, self.context, handoff['source_ref'])
        self.saved.admit(self.saved.root, self.launch, handoff['source_ref'])
        context = self.saved.child(self.saved.root, 'results', {'version': 'execution_results_assignment_v1', 'handoff_ref': handoff['source_ref'], 'selector': selector() if selection is None else selection}, index)
        self.api._manifest(context)
        return context

    def acquire(self, args, *, context):
        call = self.call('download', args, context=context)
        obj = call.prepared['bound_inputs']['resolved']['object']
        projection = call.event['facts']['projection']
        artifact = {'role': args['role'], 'source_ref': call.binding['source_ref'], 'raw_artifact_ref': call.binding['content']['artifact_ref'], 'sha256': call.snapshot.sha256, 'byte_count': len(call.snapshot.content), 'workspace_object': obj['object'], 'task_association': obj['task_association'], 'declared_format': args['declared_format'], 'transfer': {'receipt_ref': 'fixture-self-reference', 'body_complete': projection['body_complete'], 'requested_range': projection['requested_range'], 'observed_range': projection['observed_range'], 'total_size': projection['total_size'], 'object_complete': projection['object_complete']}}
        receipt = {'version': 'bvbrc_appservice_acquisition_v1', 'origin': call.common['origin'], 'original_handoff_ref': context.assignment['handoff_ref'], 'selector_sha256': digest(context.assignment['selector']), 'snapshot': call.binding, 'capability_selection': args['capability'], 'object_selection': args['object'], 'artifact': artifact, 'requirement_ids': args['requirement_ids'], 'publication_inputs_sha256': digest(call.prepared), 'publication_ref': None, 'valid_record_refs': [call.binding['source_ref']], 'status': 'ok', 'failure': None}
        encoded = deepcopy(receipt)
        del encoded['artifact']['transfer']['receipt_ref']
        binding = self.saved.source(canonical(encoded).encode(), provider='inputs.fixture.acquisition')
        reference = binding['source_ref']
        receipt['artifact']['transfer']['receipt_ref'] = reference
        validate_contract('AcquisitionReceipt', receipt)
        _immutable(call.directory / 'fixture_acquisition.json', receipt)
        self.complete(context, call.key, call.directory, receipt, [reference, call.binding['source_ref']])
        return reference

    def read_acquisition(self, reference):
        source = self.store.get(reference)
        assert source['provider'] == 'inputs.fixture.acquisition'
        value = json.loads(self.store.get_artifact(source['artifact_ref']))
        value['artifact']['transfer']['receipt_ref'] = reference
        origin = value['origin']
        producer = self.custody.context(origin['episode_id'])
        self.custody.possession(producer, reference)
        directory = self.api._manifest(producer) / 'actions' / digest(origin['operation_key'])
        assert _read(directory / 'fixture_acquisition.json') == value
        assert _read(directory / 'outcome.json')['result'] == value
        return validate_contract('AcquisitionReceipt', value)

def receipt_row(receipt, pointer='/result/0/0'):
    return {'kind': 'receipt_row', 'receipt_ref': receipt['source_ref'], 'row_pointer': pointer}
