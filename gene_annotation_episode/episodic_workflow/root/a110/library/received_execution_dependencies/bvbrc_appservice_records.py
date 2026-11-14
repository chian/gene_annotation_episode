from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import download_request, validate_contract
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_readers import qualify_download
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain
from gene_annotation_episode.episodic_workflow.root.a110.domain import identity
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
PROVIDER = 'episode.bvbrc_appservice_receipt'
NATIVE_PROVIDER = 'bvbrc_appservice'
VERSION = 'bvbrc_appservice_retained_receipt_v1'
NATIVE_VERSION = 'bvbrc_appservice_native_source_v1'
_CONTRACTS = {'CommonReceipt', 'CatalogReceipt', 'PreparationReceipt', 'WorkspaceReceipt', 'UploadReceipt', 'TaskInfoReceipt', 'TaskObservation', 'CapabilityReceipt', 'TaskHandoff', 'AcquisitionReceipt'}

def _common(contract, value):
    if contract == 'AcquisitionReceipt':
        return {'origin': value['origin'], 'snapshot': value['snapshot'], 'receipt_ref': value['artifact']['transfer']['receipt_ref']}
    return value if contract == 'CommonReceipt' else value['receipt']

def _decode(contract, value, reference):
    value = deepcopy(value)
    if contract == 'AcquisitionReceipt':
        if 'receipt_ref' in value['artifact']['transfer']:
            raise ValueError('appservice_receipt_stored_self_reference')
        if value['publication_ref'] is not None:
            raise ValueError('appservice_acquisition_publication_reference_conflict')
        value['artifact']['transfer']['receipt_ref'] = reference
        return validate_contract(contract, value)
    common = _common(contract, value)
    if 'receipt_ref' in common:
        raise ValueError('appservice_receipt_stored_self_reference')
    common['receipt_ref'] = reference
    if contract == 'TaskHandoff':
        if 'submission_receipt_ref' in value['original_task']:
            raise ValueError('appservice_receipt_stored_self_reference')
        value['original_task']['submission_receipt_ref'] = reference
    return validate_contract(contract, value)

class AppServiceRecords(EpisodeReturnRecords):

    def __init__(self, execution):
        self.api = execution
        super().__init__(execution.store, execution.run_id, failure_prefix='appservice_records_')

    def _origin(self, context, prepared, operation_key, *, _completed_download=False):
        self.authenticate(context)
        operands = prepared['native_operands']
        self.api._selected(context, prepared['operation'], operands['arguments'], operation_key)
        assignment = plain(context.assignment)
        if context.role == 'launch_api':
            request, selector = (assignment['request'], None)
            resource_id = assignment['resource_id']
        elif context.role == 'results':
            target = self.api.read_target(assignment['handoff_ref'], context.scope, **{'_completed_appservice_download': True} if _completed_download else {})
            request, selector = (target['assignment']['request'], assignment['selector'])
            resource_id = target['resource_id']
        else:
            raise ValueError('appservice_records_execution_role_required')
        if prepared['arguments_sha256'] != digest(operands['arguments']) or prepared['request_sha256'] != digest(operands['request']) or canonical(operands['request']) != canonical(request) or (canonical(operands['selector']) != canonical(selector)) or (prepared['bound_inputs']['resource_id'] != resource_id):
            raise ValueError('appservice_records_selected_operands_conflict')
        return validate_contract('ReceiptOrigin', {'run_id': context.run_id, 'episode_id': context.episode_id, 'operation_key': operation_key, 'name': prepared['operation'], 'arguments_sha256': prepared['arguments_sha256'], 'assignment_sha256': digest(context.assignment), 'scope_sha256': digest(context.scope)})

    def _recorded_snapshot(self, context, prepared, operation_key, metadata):
        directory = self.api._manifest(context, create=False) / 'actions' / digest(operation_key)
        intent = _read(directory / 'intent.json')
        call_intent = _read(directory / 'call_intent.json')
        response = _read(directory / 'call_response.json')
        if intent['operation_key'] != operation_key or canonical(intent['prepared']) != canonical(prepared) or call_intent['operation_key'] != operation_key or (call_intent['episode_id'] != context.episode_id) or (call_intent['run_id'] != context.run_id) or (call_intent['assignment_sha256'] != digest(context.assignment)) or (call_intent['scope_sha256'] != digest(context.scope)) or (canonical(call_intent['prepared']) != canonical(prepared)) or (response['intent_sha256'] != digest(call_intent)) or (canonical(response['snapshot']) != canonical(metadata)):
            raise ValueError('appservice_receipt_original_transport_conflict')

    def _source(self, reference, *, provider, origin, version):
        source = self.store.get(reference)
        payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        if source.get('record_type') != 'source' or source.get('provider') != provider or source.get('origin') != origin or (source.get('version') != version) or (reference != identity('source', {'origin': origin, 'record': payload})):
            raise ValueError('appservice_receipt_source_identity_conflict')
        return source

    def _artifact_json(self, reference):
        raw = self.store.get_artifact(reference)
        value = json.loads(raw)
        if reference != 'artifact_' + hashlib.sha256(raw).hexdigest() or raw != canonical(value).encode('utf-8'):
            raise ValueError('appservice_receipt_artifact_identity_conflict')
        return value

    def _native(self, binding, context, prepared, operation_key, *, _completed_download=False):
        binding = validate_contract('SnapshotBinding', binding)
        source = self._source(binding['source_ref'], provider=NATIVE_PROVIDER, origin='external', version=NATIVE_VERSION)
        retained = self._artifact_json(source['request_ref'])
        origin = self._origin(context, prepared, operation_key, **{'_completed_download': True} if _completed_download else {})
        if set(retained) != {'version', 'origin', 'snapshot', 'prepared'} or retained['version'] != NATIVE_VERSION or canonical(retained['origin']) != canonical(origin) or (canonical(retained['prepared']) != canonical(prepared)):
            raise ValueError('appservice_receipt_native_origin_conflict')
        snapshot = self.api._load_snapshot(retained['snapshot'])
        self._recorded_snapshot(context, prepared, operation_key, retained['snapshot'])
        content = binding['content']
        if binding['source_ref'] != content['source_ref'] or content['artifact_field'] != 'artifact_ref' or source['artifact_ref'] != content['artifact_ref'] or (content['artifact_ref'] != 'artifact_' + snapshot.sha256) or (source['uri'] != snapshot.url) or (source['retrieved_at'] != snapshot.retrieved_at) or (content['sha256'] != snapshot.sha256) or (content['byte_count'] != len(snapshot.content)) or (binding['retrieved_at'] != snapshot.retrieved_at) or (binding['media_type'] != snapshot.media_type) or (canonical(binding['transport']) != canonical(snapshot.transport)) or (canonical(binding['selected_operands']) != canonical({key: prepared[key] for key in ('operation', 'request_sha256', 'arguments_sha256', 'native_operands')})):
            raise ValueError('appservice_receipt_native_bytes_conflict')
        return snapshot

    def _acquisition(self, value, context, intent, directory, snapshot):
        """Authenticate the current receipt, not custody of prior dependencies."""
        inputs = validate_contract('PublicationInputs', _read(directory / 'publication_inputs.json'))
        prepared = validate_contract('PreparedOperation', intent['prepared'])
        origin, binding = (value['origin'], value['snapshot'])
        operands, bound = (prepared['native_operands'], prepared['bound_inputs'])
        args, resolved = (operands['arguments'], bound['resolved'])
        assignment = plain(context.assignment)
        selected = self.api._selected(context, prepared['operation'], args, origin['operation_key'])
        actual_args = json.loads(selected['action'])['arguments']
        if context.role != 'results' or prepared['operation'] != 'api.bvbrc_appservice.download' or prepared['purpose'] != 'acquisition' or (prepared['native_kind'] != 'download') or prepared['mutates_remote'] or prepared['effects'] or (intent['name'] != prepared['operation']) or (canonical(intent['arguments']) != canonical(args)) or (canonical(actual_args) != canonical(args)) or (inputs['current_operation'] != {'name': origin['name'], 'arguments': args}) or (digest(inputs['current_operation']['arguments']) != origin['arguments_sha256']) or (canonical(inputs['current_snapshot']) != canonical(binding)) or (canonical(inputs['request']) != canonical(operands['request'])) or (canonical(inputs['selector']) != canonical(operands['selector'])) or (canonical(inputs['selector']) != canonical(assignment['selector'])) or (value['selector_sha256'] != digest(inputs['selector'])) or (value['publication_inputs_sha256'] != digest(inputs)) or (value['publication_ref'] is not None):
            raise ValueError('appservice_acquisition_publication_inputs_conflict')
        if value['original_handoff_ref'] != inputs['original_handoff_ref'] or inputs['original_handoff_ref'] != assignment['handoff_ref'] or inputs['original_handoff_ref'] != bound['original_handoff_ref']:
            raise ValueError('appservice_acquisition_original_task_conflict')
        task, obj, capability = (resolved['original_task'], resolved['object'], resolved['capability'])
        request = inputs['request']
        if task['submission_receipt_ref'] != inputs['original_handoff_ref'] or task['resource_id'] != bound['resource_id'] or task['required_application_id'] != request['required_application_id'] or (canonical(task['submitted_parameters']) != canonical(request['parameters'])) or (canonical(task['submitted_start_parameters']) != canonical(request['start_parameters'])) or (obj['task_association'] is None) or (obj['task_association']['task_id'] != task['task_id']):
            raise ValueError('appservice_acquisition_original_task_conflict')
        artifact, content = (value['artifact'], binding['content'])
        if canonical(value['capability_selection']) != canonical(args['capability']) or canonical(value['object_selection']) != canonical(args['object']) or value['requirement_ids'] != args['requirement_ids'] or (artifact['role'] != args['role']) or (canonical(artifact['declared_format']) != canonical(args['declared_format'])) or (canonical(artifact['workspace_object']) != canonical(obj['object'])) or (canonical(artifact['task_association']) != canonical(obj['task_association'])) or (canonical(obj['selection']) != canonical(args['object'])) or (canonical(capability['selection']) != canonical(args['capability'])) or (canonical(bound['capability']) != canonical(args['capability'])) or (canonical(capability['entry']['object_selection']) != canonical(args['object'])) or (canonical(capability['entry']['object']) != canonical(obj['object'])) or (canonical(capability['entry']['task_association']) != canonical(obj['task_association'])):
            raise ValueError('appservice_acquisition_selected_artifact_conflict')
        if artifact['source_ref'] != binding['source_ref'] or artifact['raw_artifact_ref'] != content['artifact_ref'] or artifact['sha256'] != content['sha256'] or (artifact['byte_count'] != content['byte_count']):
            raise ValueError('appservice_acquisition_source_conflict')
        call = operands['call']
        if snapshot.service != 'bvbrc_analysis' or operands['local_failure'] is not None or call['url'] != capability['entry']['url'] or (snapshot.url != call['url']) or (canonical(snapshot.request) != canonical(download_request(call, arguments=args))):
            raise ValueError('appservice_acquisition_native_request_conflict')
        qualified = qualify_download(snapshot, capability=capability['entry'], object_binding={key: obj[key] for key in ('object', 'metadata')})
        if value['status'] != qualified['status'] or any((canonical(artifact['transfer'][key]) != canonical(qualified['value'][key]) for key in ('body_complete', 'requested_range', 'observed_range', 'total_size', 'object_complete'))):
            raise ValueError('appservice_acquisition_transfer_conflict')

    def read(self, reference, *, require_completed=True, _completed_download=False):
        source = self._source(reference, provider=PROVIDER, origin='tool', version=VERSION)
        encoded = self._artifact_json(source['artifact_ref'])
        if set(encoded) != {'version', 'contract', 'value'} or encoded['version'] != VERSION or encoded['contract'] not in _CONTRACTS:
            raise ValueError('appservice_receipt_envelope_invalid')
        value = _decode(encoded['contract'], encoded['value'], reference)
        common = _common(encoded['contract'], value)
        origin = common['origin']
        owner = self.context(origin['episode_id'])
        directory = self.api._manifest(owner, create=False) / 'actions' / digest(origin['operation_key'])
        intent = _read(directory / 'intent.json')
        expected = self._origin(owner, intent['prepared'], origin['operation_key'], **{'_completed_download': True} if _completed_download else {})
        if canonical(origin) != canonical(expected):
            raise ValueError('appservice_receipt_original_origin_required')
        result = {'source_ref': reference, 'contract': encoded['contract'], 'value': value}
        if canonical(_read(directory / 'typed_receipt.json')) != canonical(result):
            raise ValueError('appservice_receipt_original_publication_conflict')
        binding = common['snapshot']
        stamp = binding['retrieved_at'] if binding else intent['started_at']
        if source['accession'] != 'receipt_' + digest(origin) or source['uri'] is not None or source['text_ref'] is not None or (source['request_ref'] != source['artifact_ref']) or (source['retrieved_at'] != stamp):
            raise ValueError('appservice_receipt_source_metadata_conflict')
        if binding is not None:
            if canonical(binding) != canonical(_read(directory / 'native_source.json')):
                raise ValueError('appservice_receipt_native_source_conflict')
            snapshot = self._native(binding, owner, intent['prepared'], origin['operation_key'], **{'_completed_download': True} if _completed_download else {})
            if encoded['contract'] == 'AcquisitionReceipt':
                self._acquisition(value, owner, intent, directory, snapshot)
        if require_completed:
            outcome = _read(directory / 'outcome.json')
            selected = self.api._selected(owner, intent['name'], intent['arguments'], origin['operation_key'])
            actual = None if selected['result'] is None else json.loads(selected['result'])
            if actual is None or outcome.get('status') not in {'completed', 'partial'} or reference not in outcome.get('record_refs', []) or any((key not in actual or canonical(actual[key]) != canonical(item) for key, item in outcome.items())):
                raise ValueError('appservice_receipt_completed_action_required')
        return result
