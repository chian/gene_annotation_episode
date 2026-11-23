"""The operands one A103 AppService API job episode holds for its next selected AppService operation.

``BVBRCAppServiceService.prepare`` needs the operation's ``BoundInputs``: the original job owner, the
request, and every receipt, object, definition and input the selection names, each authenticated. On
this runner the API job episode is the custody boundary. What it holds is exactly:

- its commission: the assigned ``request`` (its input bindings, definition inputs and workspace
  targets) and the Store sources that request names;
- the typed receipts its own earlier units produced (``held``: receipt ref -> its contract, the
  prepared operation that produced it and the effect rows of that operation), retained in the
  run's shared Store.

A selection naming anything else (another episode's receipt, an acquisition manifest, which only a
results episode can hold) is rejected before acquisition with ``AppServiceInputError``. Nothing is
searched for, defaulted or substituted.

The results episode's resolver (``execution_result_acquisition/result_inputs.ResultInputs``) derives from
``HeldInputs`` and ``_Selection``: it admits the result operations, authenticates the original job from the
returned handoff receipt on the Store and adds the result operands (``Workspace.ls`` rows, acquisition
manifest members, download capabilities) through the hooks ``operations``, ``selection``,
``workspace_methods``, ``manifest_member`` and ``operands``.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from urllib.parse import urlsplit

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_analysis_protocol import parse_workspace_records
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_definitions import get_application_spec
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.gene_context_evidence.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.gene_context_evidence.bvbrc_appservice_readers import _object_binding, decode_task_info, decode_upload
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.gene_context_evidence.appservice_receipt_records import RECEIPT_PROVIDER, _decode
from gene_annotation_episode.episodic_workflow.episode_support.tools.service_calls.gene_context_evidence.bvbrc_appservice_tool_info import LAUNCH_OPERATIONS, PREFIX
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical

DEFINITION_PROVIDER = 'episode.bvbrc_appservice_definition'
DEFINITION_VERSION = 'bvbrc_appservice_definition_extraction'
_UUID = re.compile(r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\Z')


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


class AppServiceInputError(ValueError):
    """A selection whose operands this episode does not hold or that conflict with its original job."""

    def __init__(self, code, *, refs=()):
        self.code, self.refs = code, tuple(refs)
        super().__init__(code)


def _require(condition, code, *, refs=()):
    if not condition:
        raise AppServiceInputError(code, refs=refs)


def _same(left, right):
    return canonical(left) == canonical(right)


def _pointer(parent, token):
    return parent + '/' + str(token).replace('~', '~0').replace('/', '~1')


def _resolve_pointer(value, pointer):
    if pointer == '':
        return value
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(value, list):
            _require(token.isdecimal() and int(token) < len(value), 'source_pointer_unresolved')
            value = value[int(token)]
        else:
            _require(isinstance(value, dict) and token in value, 'source_pointer_unresolved')
            value = value[token]
    return value


def _reference_same(left, right):
    if left == right:
        return left is not None
    if type(left) is not str or type(right) is not str:
        return False
    if _UUID.fullmatch(left) and _UUID.fullmatch(right):
        return left.lower() == right.lower()
    if left.startswith('/') and right.startswith('/'):
        return (re.sub(r'/+', '/', left).rstrip('/') or '/') == (re.sub(r'/+', '/', right).rstrip('/') or '/')
    return False


def _one(rows, condition, code):
    matches = [row for row in rows if condition(row)]
    _require(len(matches) == 1, code)
    return matches[0]


def object_identity(resource_id, obj):
    """The Workspace object's identity within its resource: its UUID when known, else its normalised path."""
    if obj['uuid'] is not None:
        return 'workspace:' + resource_id + ':uuid:' + obj['uuid'].lower()
    return 'workspace:' + resource_id + ':path:' + (re.sub(r'/+', '/', obj['path']).rstrip('/') or '/')


def read_receipt(store, reference, contract):
    """Decode one retained receipt record of ``contract`` from the Store."""
    record = store.get(reference)
    _require(record.get('record_type') == 'source' and record.get('provider') == RECEIPT_PROVIDER,
             'appservice_receipt_record_invalid', refs=[reference])
    stored = json.loads(store.get_artifact(record['artifact_ref']))
    _require(stored.get('contract') == contract, 'appservice_receipt_contract_conflict', refs=[reference])
    return _decode(contract, stored['value'], reference)


class HeldInputs:
    """Resolves ``BoundInputs`` for one selection from what the API job episode holds."""
    operations = LAUNCH_OPERATIONS

    def __init__(self, store, *, owner, resource_id, request, held, origin):
        self.store, self.owner, self.resource, self.request = store, owner, resource_id, request
        self.held, self.origin = held, origin

    def selection(self, name, arguments):
        return _Selection(self, name, arguments)

    def bind(self, name, arguments):
        selection = validate_contract('OperationSelection', {'name': name, 'arguments': deepcopy(arguments)})
        _require(name in self.operations, 'bvbrc_appservice_operation_not_available')
        return self.selection(selection['name'], selection['arguments']).resolve()


def native_pointer(method, row):
    """The JSON pointer of one parsed Workspace record within its native ``/result/0`` value."""
    if method == 'ls':
        return _pointer(_pointer('/result/0', row['listing_path']), row['row_index'])
    return _pointer('/result/0', row['row_index'])


class _Selection:
    """Per-selection state; nothing outlives one resolution."""
    # A launch episode's Workspace receipts are Workspace.get or Workspace.create (never Workspace.ls).
    workspace_methods = ('get', 'create')

    def __init__(self, holder, name, arguments):
        self.h, self.store, self.name, self.args = holder, holder.store, name, arguments
        self.request, self.resource = holder.request, holder.resource
        self.support, self.proofs, self.inputs, self.objects = [], [], [], []
        self.definition = self.handoff_ref = self.task = self.capability = None

    # -- custody -----------------------------------------------------------------------
    def content(self, binding):
        """Bytes of a Store source this episode holds, checked against their binding."""
        binding = validate_contract('ContentBinding', binding)
        reference = binding['source_ref']
        try:
            record = self.store.get(reference)
            data = self.store.get_artifact(binding['artifact_ref'])
        except (ValueError, KeyError, OSError) as error:
            raise AppServiceInputError('input_not_possessed', refs=[reference]) from error
        _require(record.get('record_type') == 'source'
                 and record.get(binding['artifact_field']) == binding['artifact_ref'], 'input_not_possessed',
                 refs=[reference])
        _require(len(data) == binding['byte_count'] and hashlib.sha256(data).hexdigest() == binding['sha256'],
                 'input_bytes_mismatch', refs=[reference])
        self.proofs.append(reference)
        return data

    def evidence(self, evidence):
        """The JSON value an evidence binding points to in a held source."""
        evidence = validate_contract('SourceEvidence', evidence)
        try:
            value = json.loads(self.content(evidence['content']))
        except ValueError as error:
            if isinstance(error, AppServiceInputError):
                raise
            raise AppServiceInputError('source_evidence_not_json', refs=[evidence['content']['source_ref']]) from error
        return _resolve_pointer(value, evidence['pointer'])

    def receipt(self, reference, contract=None):
        """A receipt one of this episode's own earlier units produced."""
        held = self.h.held.get(reference)
        _require(held is not None, 'appservice_receipt_not_held_by_this_episode', refs=[reference])
        _require(contract is None or held['contract'] == contract, 'appservice_receipt_contract_conflict',
                 refs=[reference])
        value = read_receipt(self.store, reference, held['contract'])
        prepared = validate_contract('PreparedOperation', held['prepared'])
        common = value if held['contract'] == 'CommonReceipt' else value['receipt']
        _require(common['receipt_ref'] == reference and common['origin']['name'] == prepared['operation']
                 and common['origin']['arguments_sha256'] == prepared['arguments_sha256'],
                 'appservice_receipt_identity_conflict', refs=[reference])
        bound = prepared['bound_inputs']
        _require(_same(bound['original_job_owner'], self.h.owner) and bound['resource_id'] == self.resource
                 and prepared['request_sha256'] == digest(self.request)
                 and _same(prepared['native_operands']['request'], self.request), 'original_task_mismatch',
                 refs=[reference])
        if self.task is not None and bound['resolved'].get('original_task') is not None:
            _require(_same(bound['resolved']['original_task'], self.task), 'original_task_mismatch', refs=[reference])
        self.support.append(reference)
        return value, prepared, held

    # -- the original job ----------------------------------------------------------------
    def handoff(self, reference):
        value, prepared, held = self.receipt(reference, 'TaskHandoff')
        task, common = value['original_task'], value['receipt']
        _require(common['status'] == 'ok' and value['usable_handoff'] and _same(value['original_job_owner'], self.h.owner)
                 and task['resource_id'] == self.resource
                 and task['required_application_id'] == self.request['required_application_id']
                 and _same(task['submitted_parameters'], self.request['parameters'])
                 and _same(task['submitted_start_parameters'], self.request['start_parameters'])
                 and task['submission_receipt_ref'] == reference and common['snapshot'] is not None
                 and task['submission_source_ref'] == common['snapshot']['source_ref']
                 and prepared['operation'] == PREFIX + 'submit', 'original_task_mismatch', refs=[reference])
        effects = [row for row in held['effects'] if row['effect_ref'] == value['effect_receipt_ref']]
        _require(len(effects) == 1 and effects[0]['state'] == 'confirmed'
                 and effects[0]['descriptor']['kind'] == 'appservice_submit'
                 and effects[0]['native_effect_identifiers'].get('task_id') == task['task_id']
                 and effects[0]['confirmation_source_ref'] == task['submission_source_ref'],
                 'original_task_mismatch', refs=[reference])
        native = self.evidence({'content': common['snapshot']['content'], 'pointer': '/result/0'})
        _require(_same(native, value['native_submission_record']), 'original_task_mismatch', refs=[reference])
        self.handoff_ref, self.task = reference, deepcopy(task)
        return self.task

    def input(self, binding_id):
        binding = _one(self.request['input_bindings'], lambda row: row['binding_id'] == binding_id,
                       'input_not_possessed')
        if binding['content'] is not None:
            self.content(binding['content'])
        if binding['link_evidence'] is not None:
            _require(_same(self.evidence(binding['link_evidence']), binding['inline_value']), 'input_bytes_mismatch')
        for member in binding['members']:
            if member['evidence'] is not None:
                self.evidence(member['evidence'])
        if binding not in self.inputs:
            self.inputs.append(deepcopy(binding))
        return deepcopy(binding)

    def association(self, obj, *, kind='unverified_original_path', evidence_ref=None, pointer=None):
        _require(self.task is not None, 'original_task_mismatch')
        return validate_contract('TaskAssociation', {
            'kind': kind, 'evidence_ref': evidence_ref, 'pointer': pointer, 'task_id': self.task['task_id'],
            'output_path': obj['path'], 'output_uuid': obj['uuid'], 'byte_version_status': 'unknown',
            'version_evidence': []})

    def metadata_task(self, row):
        if self.task is None:
            return
        native = row['native_row']
        metadata = native[0] if type(native) is list and len(native) in (1, 2) and type(native[0]) is list else native
        for field in (7, 8):
            values = metadata[field]
            if type(values) is dict and 'task_data' in values:
                task_data = values['task_data']
                _require(type(task_data) is dict, 'task_manifest_mismatch')
                for key, expected in (('task_id', self.task['task_id']),
                                      ('app_id', self.task['native_application_id'])):
                    _require(key not in task_data or task_data[key] is None or task_data[key] == expected,
                             'task_manifest_mismatch')

    # -- Workspace objects ---------------------------------------------------------------------
    def object(self, selection):
        selection = validate_contract('ObjectSelection', selection)
        kind, metadata, association = selection['kind'], None, None
        if kind == 'original_input':
            binding = _one(self.request['input_bindings'],
                           lambda row: row['binding_id'] == selection['input_binding_id'], 'input_not_possessed')
            _require(binding['workspace_path'] is not None, 'workspace_target_conflict')
            obj = {'path': binding['workspace_path'], 'uuid': None, 'type': None, 'metadata_receipt_ref': None}
            reference = obj['path']
        elif kind == 'original_target':
            target = _one(self.request['workspace_targets'], lambda row: row['target_id'] == selection['target_id'],
                          'workspace_target_conflict')
            obj = {'path': target['path'], 'uuid': None, 'type': target['type'], 'metadata_receipt_ref': None}
            reference = obj['path']
            if self.task is not None and target['purpose'] == 'output_parent':
                association = self.association(obj)
        elif kind == 'receipt_row':
            value, prepared, _ = self.receipt(selection['receipt_ref'], 'WorkspaceReceipt')
            metadata = _one(value['rows'], lambda row: row['pointer'] == selection['row_pointer'],
                            'workspace_row_ambiguous')
            _require(metadata['valid'], 'workspace_member_failed', refs=[selection['receipt_ref']])
            snapshot = value['receipt']['snapshot']
            _require(snapshot is not None, 'workspace_member_failed')
            _require(_same(self.evidence({'content': snapshot['content'], 'pointer': metadata['pointer']}),
                           metadata['native_row']), 'workspace_target_conflict')
            native = self.evidence({'content': snapshot['content'], 'pointer': '/result/0'})
            _require(_same(native, value['native_value']), 'workspace_target_conflict')
            call = prepared['native_operands']['call']['rpc_request']
            _require(call['method'] == value['method'], 'workspace_target_conflict')
            method, options = value['method'].split('.')[1], call['params'][0]
            _require(method in self.workspace_methods, 'workspace_target_conflict')
            references = {'create': lambda: [row[0] for row in options['objects']], 'get': lambda: options['objects'],
                          'ls': lambda: options['paths']}[method]()
            parsed = parse_workspace_records(native, operation=method, requested_paths=references)
            native_record = _one(parsed['records'], lambda row: native_pointer(method, row) == metadata['pointer'],
                                 'workspace_row_ambiguous')
            _require(native_record['status'] == 'ok', 'workspace_member_failed')
            obj = {key: metadata[key] for key in ('path', 'uuid', 'type')}
            obj['metadata_receipt_ref'] = selection['receipt_ref']
            _object_binding({'object': obj, 'metadata': metadata})
            reference = obj['path'] or obj['uuid']
            association = self.row_association(value, prepared, native_record, obj)
            if association is not None:
                self.metadata_task(metadata)
        elif kind == 'task_info_object':
            value, prepared, _ = self.receipt(selection['receipt_ref'], 'TaskInfoReceipt')
            if self.task is None:
                self.handoff(value['original_handoff_ref'])
            _require(value['original_handoff_ref'] == self.handoff_ref and value['task_id'] == self.task['task_id']
                     and value['receipt']['status'] == 'ok' and value['body_complete']
                     and value['file'] in ('job_result_id', 'job_result_folder')
                     and value['reported_object_uuid'] is not None and prepared['operation'] == PREFIX + 'task_info'
                     and prepared['native_operands']['call'] == {'task_id': self.task['task_id'], 'file': value['file']},
                     'task_info_object_invalid')
            snapshot = value['receipt']['snapshot']
            _require(snapshot is not None, 'task_info_object_invalid')
            parsed = decode_task_info(self.content(snapshot['content']), task_id=value['task_id'], file=value['file'])
            _require(parsed['status'] == 'ok' and parsed['value']['reported_object_uuid'] == value['reported_object_uuid'],
                     'task_info_object_invalid')
            reference = value['reported_object_uuid']
            obj = {'path': None, 'uuid': reference, 'type': None, 'metadata_receipt_ref': None}
            association = self.association(obj, kind='task_info_object', evidence_ref=selection['receipt_ref'],
                                           pointer='/reported_object_uuid')
        else:
            obj, association = self.manifest_member(selection)
            reference = obj['path']
        row = validate_contract('ResolvedObject', {
            'selection': selection, 'native_reference': reference, 'object': obj, 'metadata': metadata,
            'task_association': association, 'identity': object_identity(self.resource, obj)})
        self.objects.append(deepcopy(obj))
        return row

    def manifest_member(self, selection):
        # An acquisition manifest is produced only by a results episode's download.
        raise AppServiceInputError('appservice_manifest_member_not_held_by_an_api_job_episode',
                                   refs=[selection['manifest_receipt_ref']])

    def row_association(self, receipt, prepared, native, obj):
        if self.task is None:
            return None
        resolved = prepared['bound_inputs']['resolved']
        if receipt['method'] == 'Workspace.ls':
            # A listed member is associated through the listed parent this episode resolved for its ls.
            parent = _one([row for row in resolved['objects'] if any(
                _reference_same(native['listing_path'], value)
                for value in (row['native_reference'], row['object']['path'], row['object']['uuid']))],
                lambda _: True, 'output_association_missing')
            association = parent['task_association']
            _require(association is not None and association['task_id'] == self.task['task_id'],
                     'original_task_mismatch')
            kind = 'unverified_original_path'
            if association['kind'] == 'task_info_object':
                info, _, _ = self.receipt(association['evidence_ref'], 'TaskInfoReceipt')
                _require(info['file'] == 'job_result_folder' and info['task_id'] == self.task['task_id']
                         and info['original_handoff_ref'] == self.handoff_ref, 'output_association_missing')
                kind = 'task_info_folder_member'
            return self.association(obj, kind=kind, evidence_ref=receipt['receipt']['receipt_ref'],
                                    pointer=native_pointer('ls', native))
        if receipt['method'] == 'Workspace.create':
            args = prepared['native_operands']['arguments']
            selected = [args['objects'][i] for i in native['request_indices']]
            target = _one(self.request['workspace_targets'], lambda row: any(
                item['target_id'] == row['target_id'] for item in selected), 'output_association_missing')
            return self.association(obj) if target['purpose'] == 'output_parent' else None
        index = native['request_index']
        _require(index is not None and index < len(resolved['objects']), 'output_association_missing')
        prior = resolved['objects'][index]
        for key in ('path', 'uuid'):
            _require(prior['object'][key] is None or _reference_same(prior['object'][key], obj[key]),
                     'workspace_target_conflict')
        association = prior['task_association']
        if association is None:
            selection = prior['selection']
            if selection['kind'] != 'original_target':
                return None
            target = _one(self.request['workspace_targets'], lambda row: row['target_id'] == selection['target_id'],
                          'output_association_missing')
            return self.association(obj) if target['purpose'] == 'output_parent' else None
        _require(association['task_id'] == self.task['task_id'], 'original_task_mismatch')
        return {**deepcopy(association), 'output_path': obj['path'], 'output_uuid': obj['uuid']}

    # -- preparation and submission ----------------------------------------------------------------
    def definition_input(self):
        selection, original_evidence = self.args['definition'], None
        if selection['kind'] == 'packaged':
            _require(selection['required_application_id'] == self.request['required_application_id'],
                     'definition_extraction_mismatch')
            envelope = get_application_spec(selection['required_application_id'])
            raw = envelope['source']['content'].encode('utf-8')
            original_source = {'kind': 'packaged', 'source': deepcopy(envelope['source'])}
            original_source['source'].pop('content')
        else:
            if selection['kind'] == 'supplied':
                binding = _one(self.request['definition_inputs'],
                               lambda row: row['binding_id'] == selection['definition_binding_id'],
                               'definition_not_possessed')
                original_evidence = binding['evidence']
                definition = self.evidence(original_evidence)
            else:
                catalog, prepared, _ = self.receipt(selection['catalog_receipt_ref'], 'CatalogReceipt')
                _require(prepared['operation'] == PREFIX + 'enumerate_apps', 'definition_extraction_mismatch')
                row = _one(catalog['records'], lambda row: row['record_index'] == selection['record_index'],
                           'definition_extraction_mismatch')
                _require(row['valid'] and row['pointer'] == '/result/0/' + str(selection['record_index'])
                         and catalog['receipt']['snapshot'] is not None, 'definition_extraction_mismatch')
                original_evidence = {'content': catalog['receipt']['snapshot']['content'], 'pointer': row['pointer']}
                definition = self.evidence(original_evidence)
                _require(_same(definition, row['native_record']), 'definition_extraction_mismatch')
                if row['definition_content'] is not None:
                    _require(_same(definition, self.evidence({'content': row['definition_content'], 'pointer': ''})),
                             'definition_extraction_mismatch')
            _require(type(definition) is dict, 'definition_extraction_mismatch')
            raw = canonical(definition).encode('utf-8')
            source = self.store.get(original_evidence['content']['source_ref'])
            envelope = {'required_id': self.request['required_application_id'], 'native_id': definition.get('id'),
                        'definition': definition, 'source': {
                            'kind': 'retained_service_definition',
                            'url': source.get('uri') or 'urn:source:' + original_evidence['content']['source_ref'],
                            'content': raw.decode('utf-8'), 'sha256': hashlib.sha256(raw).hexdigest()},
                        'parse_corrections': [], 'duplicate_object_keys': []}
            original_source = {'kind': selection['kind'], 'evidence': original_evidence}
        provenance = {'version': DEFINITION_VERSION, **self.h.origin, 'selection': deepcopy(selection),
                      'original_source': original_source, 'envelope': envelope}
        provenance_ref = self.store.artifact(canonical(provenance), 'application/json')

        def retain(content, part, parents):
            artifact_ref = self.store.artifact(content, 'application/json')
            source = self.store.put('source', {
                'provider': DEFINITION_PROVIDER, 'accession': part + '_' + digest(provenance),
                'uri': envelope['source']['url'], 'artifact_ref': artifact_ref, 'text_ref': None,
                'request_ref': provenance_ref, 'version': DEFINITION_VERSION, 'retrieved_at': None,
                'parent_source_refs': parents}, origin='tool')
            self.proofs.append(source['id'])
            return {'source_ref': source['id'], 'artifact_field': 'artifact_ref', 'artifact_ref': artifact_ref,
                    'sha256': hashlib.sha256(content).hexdigest(), 'byte_count': len(content)}

        parents = [] if original_evidence is None else [original_evidence['content']['source_ref']]
        retained = retain(raw, 'source', parents)
        extracted = retain(canonical(envelope['definition']).encode('utf-8'), 'definition', [retained['source_ref']])
        self.definition = {'content': extracted, 'pointer': ''}
        return envelope

    def submit_inputs(self):
        evidence = [self.receipt(ref) for ref in self.args['input_evidence_refs']]
        originals = {row['binding_id']: row for row in self.request['input_bindings']}
        targets = {row['target_id']: row for row in self.request['workspace_targets']}
        for value, prepared, _ in evidence:
            operation = prepared['operation']
            if operation == PREFIX + 'upload':
                upload = prepared['bound_inputs']['resolved']['upload']
                binding = upload['input']
                _require(binding['binding_id'] in originals and _same(binding, originals[binding['binding_id']])
                         and value.get('input_binding_id') == binding['binding_id']
                         and _same(value.get('input_content'), binding['content'])
                         and _same(value.get('created_object'), upload['object']['object'])
                         and value.get('shock_node_id') == upload['shock_node_id']
                         and value.get('filename') == prepared['native_operands']['arguments']['filename'],
                         'input_evidence_conflict')
                snapshot = value['receipt']['snapshot']
                _require(snapshot is not None, 'input_evidence_conflict')
                parsed = decode_upload(self.evidence({'content': snapshot['content'], 'pointer': ''}),
                                       expected_node_id=upload['shock_node_id'],
                                       expected_bytes=binding['content']['byte_count'],
                                       supplied_sha256=binding['content']['sha256'])
                _require(all(_same(value[key], parsed['value'][key]) for key in
                             ('native_reply', 'observed_node_id', 'observed_file_size', 'observed_checksums')),
                         'input_evidence_conflict')
            elif operation in (PREFIX + 'workspace_create', PREFIX + 'workspace_metadata'):
                selections = value.get('requested_objects', [])
                direct = any(row['kind'] == 'original_input' and row['input_binding_id'] in originals
                             or row['kind'] == 'original_target' and row['target_id'] in targets
                             and targets[row['target_id']]['input_binding_id'] in originals for row in selections)
                paths = [row['workspace_path'] for row in originals.values() if row['workspace_path'] is not None]
                paths.extend(row['path'] for row in targets.values() if row['input_binding_id'] in originals)
                objects = prepared['bound_inputs']['resolved'].get('objects', [])
                _require(direct or any(_reference_same(row['object']['path'], path)
                                       for row in objects for path in paths), 'input_evidence_conflict')
            else:
                raise AppServiceInputError('input_evidence_conflict')
        for original in self.request['input_bindings']:
            binding = self.input(original['binding_id'])
            if binding['kind'] == 'retained_bytes':
                _require(any(value.get('input_binding_id') == binding['binding_id']
                             and _same(value.get('input_content'), binding['content'])
                             and _reference_same(value['created_object']['path'], binding['workspace_path'])
                             and value['confirmation'] in ('accepted_bytes_match', 'accepted_identity_only')
                             and value['receipt']['status'] == 'ok' for value, _, _ in evidence),
                         'input_evidence_missing')

    # -- resolution ---------------------------------------------------------------------------------
    def resolve(self):
        resolved = {'operation': self.name, **self.operands()}
        return validate_contract('BoundInputs', {
            'version': 'bvbrc_appservice_bound_inputs', 'original_job_owner': self.h.owner,
            'request_sha256': digest(self.request), 'selected_argument_sha256': digest(self.args),
            'definition': self.definition, 'inputs': self.inputs, 'objects': self.objects,
            'support_receipt_refs': list(dict.fromkeys(self.support)), 'original_handoff_ref': self.handoff_ref,
            'capability': self.capability, 'custody_proof_refs': list(dict.fromkeys(self.proofs)),
            'resource_id': self.resource, 'resolved': resolved})

    def operands(self):
        """The selected launch operation's resolved operands."""
        suffix = self.name.removeprefix(PREFIX)
        resolved = {}
        if suffix == 'prepare':
            for item in self.request['input_bindings']:
                self.input(item['binding_id'])
            resolved['definition_envelope'] = self.definition_input()
        elif suffix == 'workspace_create':
            selected = [row['data_binding_id'] for row in self.args['objects'] if row['data_binding_id'] is not None]
            resolved['data_bindings'] = [self.input(ref) for ref in dict.fromkeys(selected)]
        elif suffix == 'upload':
            binding = self.input(self.args['input_binding_id'])
            obj = self.object({'kind': 'receipt_row', **self.args['created_object']})
            receipt, prepared, _ = self.receipt(self.args['created_object']['receipt_ref'], 'WorkspaceReceipt')
            _require(receipt['method'] == 'Workspace.create' and binding['kind'] == 'retained_bytes'
                     and binding['content'] is not None
                     and _reference_same(obj['object']['path'], binding['workspace_path']), 'workspace_target_conflict')
            targets = {row['target_id']: row for row in self.request['workspace_targets']}
            _require(any(targets[row['target_id']]['input_binding_id'] == binding['binding_id']
                         and _reference_same(targets[row['target_id']]['path'], obj['object']['path'])
                         and row['data_binding_id'] in (None, binding['binding_id'])
                         for row in prepared['native_operands']['arguments']['objects']), 'workspace_target_conflict')
            url = obj['metadata']['shock_url']
            _require(type(url) is str, 'upload_node_mismatch')
            parsed = urlsplit(url)
            node = parsed.path.rstrip('/').rsplit('/', 1)[-1]
            _require(_UUID.fullmatch(node) is not None and parsed.path.rstrip('/').endswith('/node/' + node)
                     and not parsed.query and not parsed.fragment, 'upload_node_mismatch')
            resolved['upload'] = {'object': obj, 'input': binding, 'shock_url': url, 'shock_node_id': node}
        elif suffix == 'submit':
            preparation, prepared, _ = self.receipt(self.args['preparation_receipt_ref'], 'PreparationReceipt')
            _require(preparation['receipt']['status'] == 'ok' and preparation['request_sha256'] == digest(self.request)
                     and prepared['operation'] == PREFIX + 'prepare'
                     and _same(preparation['definition_selection'], prepared['native_operands']['arguments']['definition'])
                     and _same(preparation['definition_evidence'], prepared['bound_inputs']['definition'])
                     and _same(preparation['c3_result'], prepared['native_operands']['call'].get('c3_result'))
                     and _same(preparation['native_parameters'], self.request['parameters'])
                     and _same(preparation['start_parameters'], self.request['start_parameters']),
                     'application_preparation_invalid')
            _require(_same(self.evidence(preparation['definition_evidence']),
                           prepared['bound_inputs']['resolved']['definition_envelope']['definition']),
                     'definition_extraction_mismatch')
            self.submit_inputs()
            resolved['preparation'] = preparation
        elif suffix in ('status', 'task_info'):
            resolved['original_task'] = self.handoff(self.args['handoff_ref'])
        elif suffix == 'workspace_metadata':
            resolved['objects'] = [self.object(row) for row in self.args['objects']]
            if self.task is not None:
                resolved['original_task'] = self.task
        return resolved


__all__ = ['AppServiceInputError', 'HeldInputs', 'RECEIPT_PROVIDER', 'digest', 'native_pointer', 'object_identity',
           'read_receipt']
