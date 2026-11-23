"""The operands one A107 results episode holds for its next selected AppService result operation.

``BVBRCAppServiceService.prepare`` prepares a result operation (``RESULT_OPERATIONS``) only with its
``BoundInputs``: the original job owner, the handoff receipt and the result selector, and every receipt,
object and capability the selection names, each authenticated. A results episode holds, per assigned handoff:

- the returned handoff: the original job owner, resource, request and ``handoff_ref`` the API job episode
  returned. The handoff receipt is read from the run's shared Store and authenticated there (a confirmed
  ``submit`` ``TaskHandoff`` of that owner, resource and request, whose retained native submission record
  is the one it names);
- the ``ResultSelector`` its commission assigned for that handoff (its output requirements, supplied
  metadata and supplied download capabilities);
- the typed receipts its own earlier result units produced for that handoff (``held``: receipt ref -> its
  contract, the prepared operation that produced it and that operation's effect rows).

The custody checks are those of ``api_job_execution/held_inputs`` (``_Selection``); this module adds what
only a results episode holds: ``Workspace.ls`` rows, acquisition manifest members, download capabilities and
their predecessors. A selection naming anything else is rejected before acquisition with
``AppServiceInputError``. Nothing is searched for, defaulted or substituted.
"""
from __future__ import annotations

from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.bvbrc_appservice_contracts import validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.readers.service_calls.partner_presence_evidence.bvbrc_appservice_readers import decode_job_result
from gene_annotation_episode.episodic_workflow.episode_support.tools.service_calls.partner_presence_evidence.bvbrc_appservice_tool_info import PREFIX, RESULT_OPERATIONS
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.held_inputs import (
    AppServiceInputError, HeldInputs, _one, _require, _same, _Selection, digest, read_receipt)

_FROZEN = ('operation', 'request_sha256', 'arguments_sha256', 'native_operands')


class ResultInputs(HeldInputs):
    """Resolves ``BoundInputs`` for one result selection from a returned handoff and this episode's receipts."""
    operations = RESULT_OPERATIONS

    def __init__(self, store, *, owner, resource_id, request, handoff_ref, selector, held):
        super().__init__(store, owner=owner, resource_id=resource_id, request=request, held=held, origin=None)
        self.handoff_ref, self.selector = handoff_ref, validate_contract('ResultSelector', selector)

    def selection(self, name, arguments):
        return _ResultSelection(self, name, arguments)

    def original_task(self):
        """The original task of the returned handoff, authenticated from the Store."""
        return _ResultSelection(self, None, {}).task

    def publication_inputs(self, prepared, snapshot_binding, prior_acquisition_refs):
        """The ``PublicationInputs`` of one download this episode prepared from its own bound inputs."""
        operation = {'name': prepared['operation'], 'arguments': prepared['native_operands']['arguments']}
        _require(operation['name'] == PREFIX + 'download', 'publication_operation_conflict')
        arguments = operation['arguments']
        requirements = {row['requirement_id']: row for row in self.selector['requirements']}
        evidence = [*self.selector['supplied_metadata'],
                    *(requirements[ref]['producer_rule_evidence'] for ref in arguments['requirement_ids']
                      if ref in requirements and requirements[ref]['producer_rule_evidence'] is not None),
                    *arguments['declared_format']['transformation_evidence']]
        supplied = []
        check = _ResultSelection(self, None, {})
        for row in evidence:
            check.evidence(row)
            if not any(_same(row, item) for item in supplied):
                supplied.append(deepcopy(row))
        return validate_contract('PublicationInputs', {
            'version': 'bvbrc_appservice_publication_inputs', 'request': self.request, 'selector': self.selector,
            'original_handoff_ref': self.handoff_ref, 'current_operation': operation,
            'current_snapshot': snapshot_binding, 'prior_acquisition_receipt_refs': list(prior_acquisition_refs),
            'support_receipt_refs': prepared['bound_inputs']['support_receipt_refs'], 'supplied_evidence': supplied,
            'adapter': self.selector['adapter']})

    def content_bytes(self, binding):
        """The bytes of one Store source a ``ContentBinding`` names, checked against that binding."""
        return _ResultSelection(self, None, {}).content(binding)

    def supplied_values(self, evidence):
        """Each supplied ``SourceEvidence`` row with the JSON value it points to in its Store source."""
        check = _ResultSelection(self, None, {})
        return [{'evidence': deepcopy(row), 'value': check.evidence(row)} for row in evidence]


class _ResultSelection(_Selection):
    """Per-selection state of one result operation; nothing outlives one resolution."""
    # A results episode's Workspace receipts are Workspace.get (workspace_metadata) or Workspace.ls (list_outputs).
    workspace_methods = ('get', 'ls')

    def __init__(self, holder, name, arguments):
        super().__init__(holder, name, arguments)
        self.handoff(holder.handoff_ref)

    # -- the original job, from the returned handoff ------------------------------------------------------------
    def handoff(self, reference):
        _require(reference == self.h.handoff_ref, 'original_task_mismatch', refs=[reference])
        if self.task is not None:
            return self.task
        value = read_receipt(self.store, reference, 'TaskHandoff')
        task, common = value['original_task'], value['receipt']
        _require(common['status'] == 'ok' and value['usable_handoff'] and common['origin']['name'] == PREFIX + 'submit'
                 and _same(value['original_job_owner'], self.h.owner)
                 and common['origin']['run_id'] == self.h.owner['run_id']
                 and common['origin']['episode_id'] == self.h.owner['launch_episode_id']
                 and common['origin']['assignment_sha256'] == self.h.owner['original_launch_assignment_sha256']
                 and task['resource_id'] == self.resource
                 and task['required_application_id'] == self.request['required_application_id']
                 and _same(task['submitted_parameters'], self.request['parameters'])
                 and _same(task['submitted_start_parameters'], self.request['start_parameters'])
                 and task['submission_receipt_ref'] == reference
                 and task['submission_operation_key'] == common['origin']['operation_key']
                 and common['snapshot'] is not None and task['submission_source_ref'] == common['snapshot']['source_ref']
                 and value['effect_receipt_ref'] in common['effect_receipt_refs'], 'original_task_mismatch',
                 refs=[reference])
        native = self.evidence({'content': common['snapshot']['content'], 'pointer': '/result/0'})
        _require(_same(native, value['native_submission_record']), 'original_task_mismatch', refs=[reference])
        self.support.append(reference)
        self.handoff_ref, self.task = reference, deepcopy(task)
        return self.task

    # -- acquisition manifests ------------------------------------------------------------------------------------
    def manifest_member(self, selection):
        """One output member of a job-result manifest this episode downloaded."""
        reference = selection['manifest_receipt_ref']
        held = self.h.held.get(reference)
        _require(held is not None and held['contract'] == 'AcquisitionReceipt',
                 'appservice_receipt_not_held_by_this_episode', refs=[reference])
        acquisition = read_receipt(self.store, reference, 'AcquisitionReceipt')
        prepared = validate_contract('PreparedOperation', held['prepared'])
        bound = prepared['bound_inputs']
        _require(_same(bound['original_job_owner'], self.h.owner) and bound['resource_id'] == self.resource
                 and prepared['request_sha256'] == digest(self.request)
                 and _same(prepared['native_operands']['request'], self.request)
                 and acquisition['original_handoff_ref'] == self.handoff_ref
                 and bound['original_handoff_ref'] == self.handoff_ref
                 and acquisition['origin']['name'] == PREFIX + 'download' == prepared['operation']
                 and acquisition['origin']['arguments_sha256'] == prepared['arguments_sha256'],
                 'original_task_mismatch', refs=[reference])
        artifact, snapshot = acquisition['artifact'], acquisition['snapshot']
        selected = prepared['native_operands']['arguments']
        _require(_same(snapshot['selected_operands'], {key: prepared[key] for key in _FROZEN})
                 and acquisition['selector_sha256'] == digest(self.h.selector)
                 and _same(acquisition['capability_selection'], selected['capability'])
                 and _same(acquisition['object_selection'], selected['object'])
                 and _same(acquisition['requirement_ids'], selected['requirement_ids'])
                 and artifact['role'] == selected['role']
                 and _same(artifact['declared_format'], selected['declared_format'])
                 and _same(artifact['transfer']['requested_range'], selected['byte_range']), 'task_manifest_mismatch',
                 refs=[reference])
        _require(artifact['transfer']['receipt_ref'] == reference
                 and artifact['task_association']['task_id'] == self.task['task_id']
                 and artifact['transfer']['object_complete'] == 'yes' and artifact['transfer']['body_complete']
                 and acquisition['status'] in ('ok', 'partial') and artifact['source_ref'] == snapshot['source_ref']
                 and artifact['raw_artifact_ref'] == snapshot['content']['artifact_ref']
                 and artifact['sha256'] == snapshot['content']['sha256']
                 and artifact['byte_count'] == snapshot['content']['byte_count'], 'task_manifest_mismatch',
                 refs=[reference])
        original = bound['resolved']['object']
        _require(_same(acquisition['object_selection'], original['selection'])
                 and _same(artifact['workspace_object'], original['object']), 'task_manifest_mismatch', refs=[reference])
        if original['metadata'] is not None:
            self.metadata_task(original['metadata'])
        decoded = decode_job_result(self.content(snapshot['content']), original_task=self.task,
                                    object_binding=artifact['workspace_object'], evidence_ref=artifact['source_ref'])
        member = _one(decoded['records'], lambda row: row['output_index'] == selection['output_index'],
                      'task_manifest_mismatch')
        _require(member['valid'] and member['association'] is not None, 'task_manifest_mismatch', refs=[reference])
        path, uuid = member['native_record']
        self.support.append(reference)
        return {'path': path, 'uuid': uuid, 'type': None, 'metadata_receipt_ref': None}, member['association']

    # -- download capabilities ------------------------------------------------------------------------------------
    def predecessor(self, objects):
        """The effect refs of the previous capability generation of the same objects, from this episode's receipt."""
        reference = self.args['predecessor_receipt_ref']
        if reference is None:
            return []
        value, prepared, held = self.receipt(reference)
        common = value if held['contract'] == 'CommonReceipt' else value['receipt']
        _require(prepared['operation'] == PREFIX + 'download_capability'
                 and prepared['native_operands']['arguments']['generation'] == self.args['generation'] - 1,
                 'capability_predecessor_conflict', refs=[reference])
        previous = prepared['bound_inputs']['resolved']['objects']
        refs = []
        for obj in objects:
            old = _one(previous, lambda item: item['identity'] == obj['identity'], 'capability_predecessor_conflict')
            effect = _one(held['effects'], lambda row: row['descriptor']['kind'] == 'download_capability'
                          and row['descriptor']['resource_id'] == self.resource
                          and row['descriptor']['slot']['object_identity'] == old['identity']
                          and row['descriptor']['slot']['generation'] == self.args['generation'] - 1
                          and row['operation_key'] == common['origin']['operation_key']
                          and row['state'] in ('confirmed', 'issued_unknown'), 'capability_predecessor_conflict')
            refs.append(effect['effect_ref'])
        return list(dict.fromkeys(refs))

    def download_capability(self, obj):
        """The selected capability for one resolved object: acquired by this episode or supplied by the selector."""
        selected = self.args['capability']
        if selected['kind'] == 'acquired':
            value, prepared, _ = self.receipt(selected['receipt_ref'], 'CapabilityReceipt')
            _require(prepared['operation'] == PREFIX + 'download_capability'
                     and value['generation'] == prepared['native_operands']['arguments']['generation']
                     and value['predecessor_receipt_ref']
                     == prepared['native_operands']['arguments']['predecessor_receipt_ref'],
                     'capability_not_possessed')
            entry = _one(value['entries'], lambda row: row['input_index'] == selected['input_index'],
                         'capability_not_possessed')
            original = prepared['bound_inputs']['resolved']['objects']
            _require(selected['input_index'] < len(original), 'capability_not_possessed')
            original = original[selected['input_index']]
            snapshot = value['receipt']['snapshot']
            _require(snapshot is not None and entry['issued_observed_at'] == snapshot['retrieved_at']
                     and _same(entry['object_selection'], original['selection'])
                     and _same(entry['object'], original['object'])
                     and _same(entry['task_association'], original['task_association']), 'capability_not_possessed')
            # A missing native batch member is retained as an unavailable entry; a malformed present member
            # cannot supply a replacement URL.
            native = self.evidence({'content': snapshot['content'], 'pointer': '/result/0'})
            _require(type(native) is list, 'capability_not_possessed')
            native_url = native[selected['input_index']] if selected['input_index'] < len(native) else None
            if entry['url'] is not None:
                _require(native_url == entry['url'], 'capability_not_possessed')
            if entry['expiry_evidence'] is not None:
                _require(self.evidence(entry['expiry_evidence']) == entry['expires_at'], 'capability_not_possessed')
            _require(_same(entry['object_selection'], obj['selection']) and _same(entry['object'], obj['object'])
                     and _same(entry['task_association'], obj['task_association']), 'output_association_missing')
        else:
            supplied = _one(self.h.selector['supplied_capabilities'],
                            lambda row: row['binding_id'] == selected['binding_id'], 'capability_not_possessed')
            _require(supplied['original_handoff_ref'] == self.handoff_ref
                     and _same(supplied['object_selection'], obj['selection'])
                     and _same(supplied['task_association'], obj['task_association']), 'original_task_mismatch')
            url = self.evidence(supplied['url_evidence'])
            _require(type(url) is str and bool(url), 'capability_not_possessed')
            source = self.store.get(supplied['url_evidence']['content']['source_ref'])
            _require(type(source.get('retrieved_at')) is str and bool(source['retrieved_at']),
                     'capability_observation_time_unavailable')
            entry = {'input_index': 0, 'object_selection': obj['selection'], 'object': obj['object'],
                     'task_association': obj['task_association'], 'url': url,
                     'issued_observed_at': source['retrieved_at'], 'expires_at': None, 'expiry_evidence': None}
        self.capability = selected
        return validate_contract('ResolvedCapability', {'selection': selected, 'entry': entry})

    # -- resolution -----------------------------------------------------------------------------------------------
    def operands(self):
        suffix = self.name.removeprefix(PREFIX)
        resolved = {'original_task': self.task}
        if suffix in ('status', 'task_info'):
            self.handoff(self.args['handoff_ref'])
        elif suffix in ('workspace_metadata', 'list_outputs', 'download_capability'):
            resolved['objects'] = [self.object(row) for row in self.args['objects']]
            if suffix == 'download_capability':
                resolved['predecessor_effect_refs'] = self.predecessor(resolved['objects'])
        elif suffix == 'download':
            obj = self.object(self.args['object'])
            resolved.update(object=obj, capability=self.download_capability(obj))
        else:
            raise AppServiceInputError('bvbrc_appservice_operation_not_available')
        return resolved


__all__ = ['ResultInputs']
