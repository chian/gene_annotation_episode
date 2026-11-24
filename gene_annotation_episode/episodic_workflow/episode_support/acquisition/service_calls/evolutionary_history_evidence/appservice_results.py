"""The AppService handoffs of the A104 execution result acquisition episode.

An API handoff whose configured resource is one of this binding's own BV-BRC AppService services was returned by
``api_job_execution`` (``appservice_source``): its finding names the configured ``resource_id``, original
``request``, ``original_job_owner`` and ``handoff_ref`` (the ``TaskHandoff`` receipt the API job episode retained
on the run's shared Store). Its commission also assigns the ``ResultSelector`` naming the outputs of that job to
acquire.

Each ``appservice_result`` unit is one AppService result operation (``RESULT_OPERATIONS``: status, task_info,
workspace_metadata, list_outputs, download_capability, download) of one handoff, chosen by the model:

- admission resolves the selection's ``BoundInputs`` (``result_inputs.ResultInputs``: the original job owner,
  the handoff receipt, the selector and this episode's own receipts of that handoff), refuses a remote effect
  slot this episode already issued, and prepares the operation locally (``BVBRCAppServiceService.prepare`` with
  the selector). A failure there is a rejection before acquisition;
- an admitted selection is one unit. A remote-mutating operation (download_capability) records its intent and
  effect rows first; an intent found without an outcome after an interruption is never issued again. The
  service makes its one request, the response is retained as a Store source, decoded, its effects confirmed and
  its typed receipt built (a download's ``AcquisitionReceipt`` from its ``PublicationInputs``) and retained with
  the admitted scope it ran under.

A handoff's results are acquired when, for every requirement of its selector, this episode holds a usable
``AcquisitionReceipt`` (status ok, no failure, complete body and object) naming it.

Publication step: in the same unit, after a download's usable ``AcquisitionReceipt`` is retained, the
handoff's acquisitions so far are published through ``BVBRCAppServiceService.publish`` with that download's
``PublicationInputs``; the service's ``publication_callback`` is ``appservice_publication.AppServicePublication``
over the run's shared Store. The outcome carries ``publication`` (its status, the publication record ref and
its record refs, or the failure code); the publication records join the outcome's ``record_refs``. A failed
publication leaves the acquisition and its credit unchanged and is fed back to the model.
"""
from __future__ import annotations

import asyncio
import json

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.evolutionary_history_evidence.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.tools.service_calls.evolutionary_history_evidence.bvbrc_appservice_tool_info import PREFIX
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.appservice_receipt_records import retain_receipt
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.appservice_receipt_values import build_appservice_receipt
from gene_annotation_episode.episodic_workflow.root.evolutionary_history_evidence.execution_job_submission.api_job_execution.appservice_source import (
    common_receipt, confirmed_rows, effect_rows, now, snapshot_binding, unconfirmed)
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_native_sources import retain_native_source
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.held_inputs import AppServiceInputError, digest
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.appservice_acquisition_values import _usable, build_acquisition_value
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.result_inputs import ResultInputs

ACTION = 'appservice_result'
SERVICE = 'bvbrc_appservice'


def admit_handoff(request_id, handoff, finding, service):
    """One returned AppService handoff with its assigned selector, admitted by the binding's own service."""
    credit = handoff['child_return'].get('credit')
    if (type(credit) not in (int, float) or not credit > 0 or finding.get('handoff_ready') is not True
            or not isinstance(finding.get('handoff_ref'), str)):
        raise ContractError('a104_result_acquisition_appservice_handoff_not_usable:' + request_id)
    if 'selector' not in handoff:
        raise ContractError('a104_result_acquisition_appservice_handoff_requires_a_selector:' + request_id)
    try:
        request = service.validate_request(plain(finding['request']), None)
        owner = validate_contract('OriginalJobOwner', plain(finding['original_job_owner']))
        selector = validate_contract('ResultSelector', plain(handoff['selector']))
        service.result_catalog(request, selector)
    except (ValueError, KeyError) as error:
        raise ContractError('a104_result_acquisition_appservice_handoff_not_admitted:' + request_id + ':'
                            + str(error)) from error
    return {'resource_id': finding['resource_id'], 'service': service, 'request': request, 'owner': owner,
            'handoff_ref': finding['handoff_ref'], 'selector': selector}


class AppServiceResults:
    """The assigned AppService handoffs: their authenticated original tasks, operations and custody."""

    def __init__(self, store, scope, bound, handoffs):
        self._store, self._scope, self._bound, self._handoffs = store, scope, bound, handoffs
        self._tasks = {}
        for request_id in handoffs:
            try:
                self._tasks[request_id] = self.inputs(request_id, []).original_task()
            except (ValueError, KeyError) as error:
                raise ContractError('a104_result_acquisition_appservice_handoff_not_authenticated:' + request_id
                                    + ':' + str(error)) from error

    def __contains__(self, request_id):
        return request_id in self._handoffs

    # -- custody ---------------------------------------------------------------------------------------------
    @staticmethod
    def _own(request_id, outcomes):
        return [outcome for outcome in outcomes if outcome['request_id'] == request_id and outcome['kind'] == ACTION]

    def held(self, request_id, outcomes):
        """Receipt ref -> its contract, the prepared operation that produced it and that operation's effects."""
        return {outcome['appservice_receipt']['ref']: {'contract': outcome['appservice_receipt']['contract'],
                                                       'prepared': outcome['prepared'], 'effects': outcome['effects']}
                for outcome in self._own(request_id, outcomes) if outcome['appservice_receipt'] is not None}

    @staticmethod
    def issued_slots(outcomes):
        return {canonical(row['descriptor']['slot']) for outcome in outcomes if outcome['kind'] == ACTION
                for row in outcome['effects'] if row['state'] != 'not_sent'}

    def inputs(self, request_id, outcomes):
        handoff = self._handoffs[request_id]
        return ResultInputs(self._store, owner=handoff['owner'], resource_id=handoff['resource_id'],
                            request=handoff['request'], handoff_ref=handoff['handoff_ref'],
                            selector=handoff['selector'], held=self.held(request_id, outcomes))

    def acquired(self, request_id, outcomes):
        wanted = {row['requirement_id'] for row in self._handoffs[request_id]['selector']['requirements']}
        met = {ref for outcome in self._own(request_id, outcomes) if outcome['appservice_receipt'] is not None
               and outcome['appservice_receipt']['contract'] == 'AcquisitionReceipt'
               and outcome['appservice_receipt']['usable']
               for ref in outcome['appservice_receipt']['requirement_ids']}
        return wanted <= met

    # -- presentation ------------------------------------------------------------------------------------------
    def operations(self, request_id):
        handoff = self._handoffs[request_id]
        return {item['name']: item for item in handoff['service'].result_catalog(handoff['request'],
                                                                                 handoff['selector'])}

    def options(self, request_id):
        """The selection schemas of this handoff's result operations."""
        return [{'action': {'const': ACTION}, 'request_id': {'const': request_id}, 'operation': {'const': name},
                 'arguments': item['input_schema']} for name, item in sorted(self.operations(request_id).items())]

    def context(self, request_id, outcomes):
        handoff = self._handoffs[request_id]
        return {'resource_id': handoff['resource_id'], 'service': handoff['service'].service,
                'request': handoff['request'], 'handoff_ref': handoff['handoff_ref'],
                'original_task': self._tasks[request_id], 'selector': handoff['selector'],
                'operations': {name: item['description'] for name, item in sorted(self.operations(request_id).items())},
                'held_receipts': [{'receipt_ref': outcome['appservice_receipt']['ref'],
                                   'contract': outcome['appservice_receipt']['contract'],
                                   'operation': outcome['operation'], 'status': outcome['appservice_receipt']['status']}
                                  for outcome in self._own(request_id, outcomes)
                                  if outcome['appservice_receipt'] is not None],
                'events': [{'operation': outcome['operation'], 'event': outcome['event']}
                           for outcome in self._own(request_id, outcomes) if outcome['event'] is not None],
                'publications': [outcome['publication'] for outcome in self._own(request_id, outcomes)
                                 if outcome['publication'] is not None],
                'acquired': self.acquired(request_id, outcomes)}

    # -- admission ----------------------------------------------------------------------------------------------
    def admit(self, selection, outcomes):
        """Resolve what one selection names from its handoff and prepare it locally; any failure is a rejection."""
        request_id, name, arguments = selection['request_id'], selection['operation'], selection['arguments']
        handoff = self._handoffs[request_id]
        bound_inputs = self.inputs(request_id, outcomes).bind(name, arguments)
        prepared = handoff['service'].prepare(
            name, handoff['request'], arguments, scope=self._scope, previous_events=[],
            handle={'task_id': self._tasks[request_id]['task_id']}, selector=handoff['selector'],
            bound_inputs=bound_inputs)
        repeated = [row['slot'] for row in prepared['effects'] if canonical(row['slot']) in self.issued_slots(outcomes)]
        if repeated:
            raise AppServiceInputError('a104_result_effect_slot_already_issued_by_this_episode:' + canonical(repeated))
        return prepared

    # -- execution ------------------------------------------------------------------------------------------------
    def _origin(self, position, name, arguments_sha256):
        return {'run_id': self._bound.run_id, 'episode_id': self._bound.episode_id,
                'operation_key': self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position),
                'name': name, 'arguments_sha256': arguments_sha256,
                'assignment_sha256': digest(plain(self._bound.assignment)), 'scope_sha256': digest(self._scope)}

    @staticmethod
    def _outcome(outcome, selection, prepared, status, *, event=None, effects=(), receipt=None, record_refs=(),
                 feedback=None, publication=None):
        return outcome(selection, status, prepared=prepared, event=event, effects=list(effects),
                       appservice_receipt=receipt, record_refs=list(dict.fromkeys(record_refs)), feedback=feedback,
                       publication=publication)

    def _receipt(self, selection, prepared, event, snapshot, common, rows, binding, outcomes):
        """The typed receipt of one result operation (a download's AcquisitionReceipt, else its C4 receipt) and,
        for a download, the ``PublicationInputs`` it was built from (else None)."""
        if prepared['operation'] != PREFIX + 'download':
            return build_appservice_receipt(prepared, event, snapshot, common_receipt=common,
                                            effect_receipts=rows), None
        request_id = selection['request_id']
        prior = [outcome['appservice_receipt']['ref'] for outcome in self._own(request_id, outcomes)
                 if outcome['appservice_receipt'] is not None
                 and outcome['appservice_receipt']['contract'] == 'AcquisitionReceipt']
        inputs = self.inputs(request_id, outcomes).publication_inputs(prepared, binding, prior)
        return build_acquisition_value(prepared, event, snapshot, common_receipt=common, publication_inputs=inputs,
                                       acquisition_receipt_ref=common['receipt_ref']), inputs

    def _publish(self, handoff, snapshot, operation_key, inputs, reference):
        """The publication step after one usable acquisition: the handoff's bundle published on the Store."""
        try:
            published = handoff['service'].publish(handoff['request'], handoff['selector'], snapshot, self._scope,
                                                   operation_key, publication_inputs=inputs,
                                                   acquisition_receipt_ref=reference)
        except ValueError as error:
            return {'status': 'failed', 'publication_ref': None, 'record_refs': [], 'adapter_status': None,
                    'code': getattr(error, 'code', None) or str(error)}
        return {'status': published['status'], 'publication_ref': published['publication_ref'],
                'record_refs': list(published['record_refs']), 'adapter_status': published['adapter_status'],
                'code': None}

    def intent(self, position, selection, prepared, outcome):
        """Record a remote-mutating operation's intent; the recovered outcome of an interrupted one, else None."""
        if not prepared['mutates_remote']:
            return [], None
        origin = self._origin(position, selection['operation'], prepared['arguments_sha256'])
        first = []
        effects = self._bound.recorder.recorded('intent.' + str(position), lambda: first.append(True) or
                                                effect_rows(prepared, origin['operation_key'], now()))
        if first:
            return effects, None
        return effects, self._outcome(
            outcome, selection, prepared, 'failed',
            effects=unconfirmed(effects, 'issued_effect_unknown', 'recovery', 'unknown'),
            feedback={'category': 'recovery', 'code': 'issued_outcome_unknown',
                      'detail': 'the original request was issued before an interruption; it is not issued again'})

    async def execute(self, position, selection, prepared, effects, outcomes, outcome):
        """One admitted result operation: its single request, retained response and typed receipt."""
        operation = selection['operation']
        origin = self._origin(position, operation, prepared['arguments_sha256'])
        service = self._handoffs[selection['request_id']]['service']
        try:
            snapshot = await asyncio.to_thread(service.invoke, prepared)
        except AcquisitionError as error:
            refs = [] if error.snapshot is None else [retain_native_source(
                self._store, error.snapshot, origin=origin, prepared=prepared)['source_ref']]
            sent = 'not_sent' if error.submission_outcome == 'not_sent' and error.snapshot is None else 'unknown'
            return self._outcome(outcome, selection, prepared, 'failed', record_refs=refs,
                                 effects=unconfirmed(effects, error.code, 'transport', sent), feedback={
                                     'category': 'acquisition', 'code': error.code, 'phase': error.phase,
                                     'submission_outcome': error.submission_outcome})
        binding, refs = None, []
        if snapshot is not None:
            content = retain_native_source(self._store, snapshot, origin=origin, prepared=prepared)
            refs.append(content['source_ref'])
            binding = snapshot_binding(content, snapshot, prepared)
        try:
            event = json.loads(canonical(service.decode(prepared, snapshot)))
            rows = confirmed_rows(prepared, event, snapshot, binding, effects)
            built, inputs = self._receipt(selection, prepared, event, snapshot,
                                          common_receipt(prepared, origin, binding, rows), rows, binding, outcomes)
        except (ValueError, KeyError, TypeError, AcquisitionError, ContractValidationError) as error:
            return self._outcome(outcome, selection, prepared, 'invalid', record_refs=refs, effects=unconfirmed(
                effects, 'native_response_invalid', 'native_decode', 'unknown'), feedback={
                'category': 'native_decode', 'code': getattr(error, 'code', None) or str(error)})
        reference = retain_receipt(self._store, built, self._scope, refs)
        value = built['value']
        publication = None
        if built['contract'] == 'AcquisitionReceipt':
            status = value['status']
            receipt = {'ref': reference, 'contract': built['contract'], 'status': status, 'usable': _usable(value),
                       'requirement_ids': list(value['requirement_ids'])}
            if receipt['usable']:
                publication = self._publish(self._handoffs[selection['request_id']], snapshot,
                                            origin['operation_key'], inputs, reference)
        else:
            status = (value if built['contract'] == 'CommonReceipt' else value['receipt'])['status']
            receipt = {'ref': reference, 'contract': built['contract'], 'status': status}
        failed = event['failure_code'] is not None or status in ('failed', 'invalid', 'unknown')
        feedback = None if not failed else {
            'category': 'service_state', 'code': event['failure_code'] or status,
            'state': event['state'], 'diagnostics': built['diagnostics']}
        if feedback is None and publication is not None and publication['status'] == 'failed':
            feedback = {'category': 'publication', 'code': publication['code']}
        published = [] if publication is None else publication['record_refs']
        return self._outcome(outcome, selection, prepared, 'failed' if failed else 'completed', event=event,
                             effects=rows, receipt=receipt, record_refs=[*refs, reference, *published],
                             feedback=feedback, publication=publication)


__all__ = ['ACTION', 'AppServiceResults', 'SERVICE', 'admit_handoff']
