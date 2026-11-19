"""A106 execution result acquisition on the generic runner: its binding, decision source and continuation.

Both A106 results bindings (``execution_result_acquisition`` under the head and under
``published_evidence_assessment``) derive from ``ResultAcquisitionBinding``. The commission assigns the usable
handoffs its sibling ``execution_job_submission`` returned (``handoffs``: each the ``request_id``, the route
``slot`` that produced it (``launch_api``), that route child's admitted ``child_return`` and the
``ResultSelector`` naming the outputs to acquire for that job). Each returned handoff names its configured
``resource_id``, original ``request``, ``original_job_owner`` and ``handoff_ref`` (the ``TaskHandoff``
receipt the API job episode retained on the run's shared Store); the resource must be one of this binding's
own AppService services.

Each unit is one AppService result operation (``RESULT_OPERATIONS``: status, task_info, workspace_metadata,
list_outputs, download_capability, download) of one handoff, chosen by the model:

- admission resolves the selection's ``BoundInputs`` (``result_inputs.ResultInputs``: the original job
  owner, the handoff receipt, the selector and this episode's own receipts of that handoff), refuses a remote
  effect slot this episode already issued, and prepares the operation locally
  (``BVBRCAppServiceService.prepare`` with the selector). A failure there is a rejection before acquisition:
  no unit, no observation; the model decides again with the feedback;
- an admitted selection is one unit. A remote-mutating operation (download_capability) records its intent
  and effect rows first; an intent found without an outcome after an interruption is never issued again.
  The service makes its one request, the response is retained as a Store source, decoded, its effects
  confirmed and its typed receipt built and retained (a download's ``AcquisitionReceipt`` from its
  ``PublicationInputs``). The outcome, including an invalid or failed one, is recorded as
  ``outcome.<position>`` and enters the iterator with the credit measured after it.

A handoff's results are acquired when, for every requirement of its selector, this episode holds a usable
``AcquisitionReceipt`` (status ok, no failure, complete body and object) naming it. Credit is the number of
acquired handoffs (never bounded or rescaled); continuation is the completion yield controller with
target = the number of assigned handoffs.

Publication step: in the same unit, after a download's usable ``AcquisitionReceipt`` is retained, the
handoff's acquisitions so far are published through ``BVBRCAppServiceService.publish`` with that download's
``PublicationInputs``; the service's ``publication_callback`` is ``appservice_publication.AppServicePublication``
over the run's shared Store, which publishes the ``bvbrc_appservice_acquired_bundle_v1`` record (and, for a
selected scientific adapter, its saved sheet and components) the A106 literature grading reads as
``bvbrc_application_outcomes``. The outcome carries ``publication`` (its status, the publication record ref and
its record refs, or the failure code); the publication records join the outcome's ``record_refs`` and so the
records the commissioning parent receives. A failed publication leaves the acquisition and its credit unchanged
and is fed back to the model.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Field, RecordForm
from method_loop import Episode, Leaf

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.perturbation_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_bundle_values import _usable, build_acquisition_value
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.perturbation_evidence.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_records import VERSION as RECEIPT_VERSION, _encode, provisional_receipt_ref
from gene_annotation_episode.episodic_workflow.episode_support.tools.service_calls.perturbation_evidence.bvbrc_appservice_tool_info import PREFIX
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import canonical, obj
from ..episode_contract import MODEL_PROVIDER, SCOPE, STORE, ContractRecord as Record, EpisodeContract
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.held_inputs import RECEIPT_PROVIDER, AppServiceInputError, digest
from ..execution_job_submission.api_job_execution.runtime_source import _effect_rows, _now, _unconfirmed
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.perturbation_evidence.appservice_publication import AppServicePublication
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.result_inputs import ResultInputs

AXIS = 'A106'
MODEL_ROLE = 'REASONING'
CONTINUATION = 'continuation'
ROUTE_SLOT = 'launch_api'
NATIVE_PROVIDER = 'bvbrc_appservice.'
# The field of the report form in which the commissioning A106 parent receives acquired records (C5).
ACQUIRED_RECORDS = 'record_refs'
HANDOFF_FORM = RecordForm({
    'request_id': Field('text', 'The requested job this handoff completed in the submission'),
    'slot': Field('text', 'The submission route slot that returned the handoff: ' + ROUTE_SLOT),
    'child_return': Field('record', "The API job child's admitted return exactly as the submission recorded it"),
    'selector': Field('record', 'The result selector (bvbrc_appservice_result_selector_v1) naming the outputs of '
                                'this job to acquire'),
})
ASSIGNMENT_FORM = RecordForm({
    'scope': SCOPE,
    'handoffs': Field('list', 'The usable AppService job handoffs whose native results to acquire', items=HANDOFF_FORM),
})
CREDIT_DEFINITION = {
    'kind': 'a106_result_acquisition_acquired_handoffs_v1',
    'unit': 'one assigned handoff, counted while this episode holds, for every requirement of its selector, a '
            'usable AcquisitionReceipt naming it',
    'target': 'the number of assigned handoffs',
    'scientific_credit': False,
}
INSTRUCTIONS = (
    'You run the A106 execution result acquisition episode. Each assigned handoff is a submitted BV-BRC AppService '
    'job (its resource, original request, original task and handoff_ref) with a result selector naming the outputs '
    'to acquire. Choose exactly one AppService result operation of one handoff per decision with its arguments. '
    'Operations are single requests, without waiting or polling: status and task_info read the original task of '
    'the handoff_ref; workspace_metadata, list_outputs and download_capability act on the request\'s own workspace '
    'targets and the rows of Workspace, task_info or acquisition receipts you hold for that handoff; download '
    'acquires one object with a capability you hold or the selector supplies, for the selector requirements it '
    'meets. Name only receipts listed under that handoff\'s held_receipts. A handoff is acquired when every '
    'requirement of its selector has a usable acquisition. This is operational progress, not scientific evidence; '
    'the configured controller owns continuation.')


def handoffs_of(assignment, services):
    """The assigned handoffs keyed by their distinct request ids, each from an admitted launch_api return."""
    listed = assignment['handoffs']
    if not isinstance(listed, list) or not listed:
        raise ContractError('a106_result_acquisition_requires_handoffs')
    handoffs = {}
    for index, handoff in enumerate(listed):
        handoff = HANDOFF_FORM.admit(plain(handoff), 'a106_result_acquisition_handoff[' + str(index) + ']')
        request_id = handoff['request_id']
        if request_id in handoffs:
            raise ContractError('a106_result_acquisition_request_id_repeats:' + request_id)
        if handoff['slot'] != ROUTE_SLOT:
            raise ContractError('a106_result_acquisition_unknown_route_slot:' + handoff['slot'])
        returned = handoff['child_return']
        finding = returned.get('finding')
        credit = returned.get('credit')
        if (not isinstance(finding, Mapping) or type(credit) not in (int, float) or not credit > 0
                or finding.get('handoff_ready') is not True or not isinstance(finding.get('handoff_ref'), str)):
            raise ContractError('a106_result_acquisition_handoff_not_usable:' + request_id)
        service = services.get(finding.get('resource_id'))
        if service is None or service.service != finding.get('service'):
            raise ContractError('a106_result_acquisition_api_resource_not_configured:' + request_id)
        try:
            request = service.validate_request(finding['request'], None)
            owner = validate_contract('OriginalJobOwner', finding['original_job_owner'])
            selector = validate_contract('ResultSelector', handoff['selector'])
            service.result_catalog(request, selector)
        except (ValueError, KeyError) as error:
            raise ContractError('a106_result_acquisition_handoff_not_admitted:' + request_id + ':' + str(error)) \
                from error
        handoffs[request_id] = {'resource_id': finding['resource_id'], 'service': service, 'request': request,
                                'owner': owner, 'handoff_ref': finding['handoff_ref'], 'selector': selector}
    return handoffs


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied, self.outcomes, self.feedback = 0, [], None

    def apply(self, outcome):
        self.outcomes.append(outcome)
        self.feedback = outcome.get('feedback')
        self.applied += 1

    def of(self, request_id):
        return [outcome for outcome in self.outcomes if outcome['request_id'] == request_id]

    def held(self, request_id):
        """Receipt ref -> its contract, the prepared operation that produced it and that operation's effects."""
        return {outcome['receipt']['ref']: {'contract': outcome['receipt']['contract'], 'prepared': outcome['prepared'],
                                            'effects': outcome['effects']}
                for outcome in self.of(request_id) if outcome['receipt'] is not None}

    @property
    def issued_slots(self):
        return {canonical(row['descriptor']['slot']) for outcome in self.outcomes for row in outcome['effects']
                if row['state'] != 'not_sent'}

    @property
    def record_refs(self):
        return list(dict.fromkeys(ref for outcome in self.outcomes for ref in outcome['record_refs']))


class ResultAcquisitionSource:
    """Model-selected AppService result operations over the assigned handoffs and the run's shared Store."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._store, self._provider = collaborators[STORE], collaborators[MODEL_PROVIDER]
        if binding.tool_registry.store is not self._store:
            raise ContractError('a106_result_acquisition_tool_registry_is_not_over_the_run_store:'
                                + bound.binding_path)
        self._scope = self._store.validate_scope(plain(bound.assignment['scope']))
        self._handoffs = handoffs_of(bound.assignment, binding.services)
        self._tasks = {}
        for request_id in self._handoffs:
            try:
                self._tasks[request_id] = self.inputs(request_id, {}).original_task()
            except (ValueError, KeyError) as error:
                raise ContractError('a106_result_acquisition_handoff_not_authenticated:' + request_id + ':'
                                    + str(error)) from error
        self._state = _State()

    # -- state ------------------------------------------------------------------------------------------------
    def inputs(self, request_id, held):
        handoff = self._handoffs[request_id]
        return ResultInputs(self._store, owner=handoff['owner'], resource_id=handoff['resource_id'],
                            request=handoff['request'], handoff_ref=handoff['handoff_ref'],
                            selector=handoff['selector'], held=held)

    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def acquired(self, request_id):
        wanted = {row['requirement_id'] for row in self._handoffs[request_id]['selector']['requirements']}
        met = {ref for outcome in self._state.of(request_id) if outcome['receipt'] is not None
               and outcome['receipt']['contract'] == 'AcquisitionReceipt' and outcome['receipt']['usable']
               for ref in outcome['receipt']['requirement_ids']}
        return wanted <= met

    @property
    def credit(self):
        return sum(1 for request_id in self._handoffs if self.acquired(request_id))

    def _controller_input(self, position, outcome):
        return Record({'credit': self.credit,
                       'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': 'result_operation', 'request_id': outcome['request_id'],
                                'operation': outcome['operation'], 'status': outcome['status']}})

    def _origin(self, position, name, arguments_sha256):
        return {'run_id': self._bound.run_id, 'episode_id': self._bound.episode_id,
                'operation_key': self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position),
                'name': name, 'arguments_sha256': arguments_sha256,
                'assignment_sha256': digest(plain(self._bound.assignment)), 'scope_sha256': digest(self._scope)}

    # -- presentation -------------------------------------------------------------------------------------------
    def operations(self, request_id):
        handoff = self._handoffs[request_id]
        return {item['name']: item for item in handoff['service'].result_catalog(handoff['request'],
                                                                                 handoff['selector'])}

    def action_schema(self):
        options = [obj({'request_id': {'type': 'string', 'const': request_id},
                        'operation': {'type': 'string', 'const': name}, 'arguments': item['input_schema']})
                   for request_id in sorted(self._handoffs)
                   for name, item in sorted(self.operations(request_id).items())]
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'evidence_axis': AXIS,
            'scope': self._scope,
            'handoffs': {request_id: {
                'resource_id': handoff['resource_id'], 'service': handoff['service'].service,
                'request': handoff['request'], 'handoff_ref': handoff['handoff_ref'],
                'original_task': self._tasks[request_id], 'selector': handoff['selector'],
                'operations': {name: item['description'] for name, item in sorted(self.operations(request_id).items())},
                'held_receipts': [{'receipt_ref': outcome['receipt']['ref'], 'contract': outcome['receipt']['contract'],
                                   'operation': outcome['operation'], 'status': outcome['receipt']['status']}
                                  for outcome in self._state.of(request_id) if outcome['receipt'] is not None],
                'events': [{'operation': outcome['operation'], 'event': outcome['event']}
                           for outcome in self._state.of(request_id) if outcome['event'] is not None],
                'publications': [outcome['publication'] for outcome in self._state.of(request_id)
                                 if outcome['publication'] is not None],
                'acquired': self.acquired(request_id)} for request_id, handoff in sorted(self._handoffs.items())},
            'current_credit': self.credit,
            'completion_target': len(self._handoffs),
            'credit_binding': CREDIT_DEFINITION,
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_outcome': self._summary(self._state.outcomes[-1]) if self._state.outcomes else None,
            'feedback': self._state.feedback,
        }

    # -- decisions ----------------------------------------------------------------------------------------------
    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            schema = self.action_schema()
            context = json.loads(canonical(self.decision_context(view)))
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context,
                                                generation_schema(schema)))
            try:
                selection, prepared = self.admit(response, schema)
            except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': schema_failure_diagnostic(error)
                                        if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return Leaf(selection, lambda chosen: self._execute(position, chosen, prepared),
                        lambda chosen, outcome: self._controller_input(position, outcome),
                        'result:' + str(position))

    def admit(self, response, schema):
        """Admit one response, resolve what it names from the handoff and prepare it locally."""
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a106_result_acquisition_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        request_id, name, arguments = selection['request_id'], selection['operation'], selection['arguments']
        handoff = self._handoffs[request_id]
        bound_inputs = self.inputs(request_id, self._state.held(request_id)).bind(name, arguments)
        prepared = handoff['service'].prepare(
            name, handoff['request'], arguments, scope=self._scope, previous_events=[],
            handle={'task_id': self._tasks[request_id]['task_id']}, selector=handoff['selector'],
            bound_inputs=bound_inputs)
        repeated = [row['slot'] for row in prepared['effects'] if canonical(row['slot']) in self._state.issued_slots]
        if repeated:
            raise AppServiceInputError('a106_result_effect_slot_already_issued_by_this_episode:' + canonical(repeated))
        return selection, prepared

    # -- execution ----------------------------------------------------------------------------------------------
    def _retain(self, operation, snapshot):
        """Retain one received native response as a source record; return its snapshot content binding."""
        artifact = self._store.artifact(snapshot.content, snapshot.media_type)
        request = self._store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}),
                                       'application/json')
        source = self._store.put('source', {
            'provider': NATIVE_PROVIDER + operation.removeprefix(PREFIX), 'accession': None, 'uri': snapshot.url,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': request, 'version': None,
            'retrieved_at': snapshot.retrieved_at}, origin='external')['id']
        return {'source_ref': source, 'artifact_field': 'artifact_ref', 'artifact_ref': artifact,
                'sha256': snapshot.sha256, 'byte_count': len(snapshot.content)}

    def _retain_receipt(self, built, parents):
        """Retain one typed receipt in the Store; its record id is its receipt ref."""
        artifact = self._store.artifact(canonical({'version': RECEIPT_VERSION, 'contract': built['contract'],
                                                   'value': _encode(built['contract'], built['value'])}),
                                        'application/json')
        return self._store.put('source', {
            'provider': RECEIPT_PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None,
            'request_ref': None, 'version': RECEIPT_VERSION, 'retrieved_at': None,
            'parent_source_refs': list(dict.fromkeys(parents))}, origin='tool')['id']

    def _outcome(self, selection, prepared, status, *, event=None, effects=(), receipt=None, record_refs=(),
                 feedback=None, publication=None):
        return {'kind': 'result_operation', 'request_id': selection['request_id'], 'operation': selection['operation'],
                'status': status, 'prepared': prepared, 'event': event, 'effects': list(effects), 'receipt': receipt,
                'record_refs': list(dict.fromkeys(record_refs)), 'feedback': feedback,
                'publication': publication}

    def _receipt(self, selection, prepared, event, snapshot, common, rows, binding):
        """The typed receipt of one result operation (a download's AcquisitionReceipt, else its C4 receipt) and,
        for a download, the ``PublicationInputs`` it was built from (else None)."""
        if prepared['operation'] != PREFIX + 'download':
            return build_appservice_receipt(prepared, event, snapshot, common_receipt=common,
                                            effect_receipts=rows), None
        request_id = selection['request_id']
        prior = [outcome['receipt']['ref'] for outcome in self._state.of(request_id)
                 if outcome['receipt'] is not None and outcome['receipt']['contract'] == 'AcquisitionReceipt']
        inputs = self.inputs(request_id, self._state.held(request_id)).publication_inputs(prepared, binding, prior)
        return build_acquisition_value(prepared, event, snapshot, common_receipt=common, publication_inputs=inputs,
                                       acquisition_receipt_ref=common['receipt_ref']), inputs

    def _publish(self, request_id, snapshot, operation_key, inputs, reference):
        """The publication step after one usable acquisition: the handoff's bundle published on the Store."""
        handoff = self._handoffs[request_id]
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

    async def _execute(self, position, selection, prepared):
        operation = selection['operation']
        origin = self._origin(position, operation, prepared['arguments_sha256'])
        service = self._handoffs[selection['request_id']]['service']
        effects = []
        if prepared['mutates_remote']:
            first = []
            effects = self._bound.recorder.recorded('intent.' + str(position), lambda: first.append(True) or
                                                    _effect_rows(prepared, origin['operation_key'], _now()))
            if not first:
                outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._outcome(
                    selection, prepared, 'failed',
                    effects=_unconfirmed(effects, 'issued_effect_unknown', 'recovery', 'unknown'),
                    feedback={'category': 'recovery', 'code': 'issued_outcome_unknown',
                              'detail': 'the original request was issued before an interruption; it is not '
                                        'issued again'}))
                self._state.apply(outcome)
                return outcome

        async def issue():
            try:
                snapshot = await asyncio.to_thread(service.invoke, prepared)
            except AcquisitionError as error:
                refs = [] if error.snapshot is None else [self._retain(operation, error.snapshot)['source_ref']]
                sent = 'not_sent' if error.submission_outcome == 'not_sent' and error.snapshot is None else 'unknown'
                return self._outcome(selection, prepared, 'failed', record_refs=refs,
                                     effects=_unconfirmed(effects, error.code, 'transport', sent), feedback={
                                         'category': 'acquisition', 'code': error.code, 'phase': error.phase,
                                         'submission_outcome': error.submission_outcome})
            binding, refs = None, []
            if snapshot is not None:
                content = self._retain(operation, snapshot)
                refs.append(content['source_ref'])
                binding = {'source_ref': content['source_ref'], 'content': content,
                           'retrieved_at': snapshot.retrieved_at, 'media_type': snapshot.media_type,
                           'transport': snapshot.transport, 'selected_operands': {
                               key: prepared[key] for key in
                               ('operation', 'request_sha256', 'arguments_sha256', 'native_operands')}}
            try:
                event = json.loads(canonical(service.decode(prepared, snapshot)))
                rows = effects
                if effects:
                    confirmed = confirm_appservice_effects(prepared, event, snapshot, snapshot_binding=binding,
                                                           effect_receipts=effects)
                    by_ref = {row['effect_ref']: row for row in confirmed}
                    rows = [validate_contract('EffectReceipt', {**row, **by_ref[row['effect_ref']]}) for row in effects]
                common = {'version': 'bvbrc_appservice_support_receipt_v1',
                          'receipt_ref': provisional_receipt_ref(origin), 'purpose': prepared['purpose'],
                          'origin': origin, 'snapshot': binding,
                          'effect_receipt_refs': [row['effect_ref'] for row in rows], 'status': 'ok', 'diagnostics': []}
                built, inputs = self._receipt(selection, prepared, event, snapshot, common, rows, binding)
            except (ValueError, KeyError, TypeError, AcquisitionError, ContractValidationError) as error:
                return self._outcome(selection, prepared, 'invalid', record_refs=refs, effects=_unconfirmed(
                    effects, 'native_response_invalid', 'native_decode', 'unknown'), feedback={
                    'category': 'native_decode', 'code': getattr(error, 'code', None) or str(error)})
            reference = self._retain_receipt(built, refs)
            value = built['value']
            publication = None
            if built['contract'] == 'AcquisitionReceipt':
                status = value['status']
                receipt = {'ref': reference, 'contract': built['contract'], 'status': status, 'usable': _usable(value),
                           'requirement_ids': list(value['requirement_ids'])}
                if receipt['usable']:
                    publication = self._publish(selection['request_id'], snapshot, origin['operation_key'], inputs,
                                                reference)
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
            return self._outcome(selection, prepared, 'failed' if failed else 'completed', event=event, effects=rows,
                                 receipt=receipt, record_refs=[*refs, reference, *published], feedback=feedback,
                                 publication=publication)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), issue)
        self._state.apply(outcome)
        return outcome

    # -- result -------------------------------------------------------------------------------------------------
    @staticmethod
    def _summary(outcome):
        return {key: outcome[key] for key in ('request_id', 'operation', 'status', 'event', 'receipt', 'record_refs',
                                              'feedback', 'publication')}

    def result(self, record):
        """The acquired results: credit, the acquired and pending handoffs and the records this episode retained."""
        self._catch_up(record.units_consumed)
        credit = self.credit
        if isinstance(credit, bool) or not math.isfinite(credit):
            raise ContractError('a106_result_acquisition_credit_must_be_finite')
        value = {'credit': credit, 'finding': {
            'evidence_axis': AXIS, 'scope': self._scope,
            'acquired_request_ids': [r for r in self._handoffs if self.acquired(r)],
            'pending_request_ids': [r for r in self._handoffs if not self.acquired(r)],
            'acquisition_receipt_refs': {r: [o['receipt']['ref'] for o in self._state.of(r) if o['receipt'] is not None
                                             and o['receipt']['contract'] == 'AcquisitionReceipt']
                                         for r in self._handoffs},
            'operations': [self._summary(outcome) for outcome in self._state.outcomes],
            'record_refs': self._state.record_refs, 'ended_by': record.ended_by, 'units': record.units_consumed}}
        if ACQUIRED_RECORDS in self._bound.report_form.fields:
            # The commissioning A106 parent asks for the records this commission acquired within its scope (C5).
            value[ACQUIRED_RECORDS] = self._store.reference_subset(self._state.record_refs, self._scope)
        return Record(value)


class ResultAcquisitionBinding(EpisodeContract):
    """An A106 results binding: its own AppService services, result decisions and completion continuation.

    Constructed by the A106 home factory with ``tools`` (the settings of its own ``ToolRegistry``, built here over
    the run's shared store) and ``resources`` (``{resource_id: AppService ServiceConfiguration}``: the resources
    whose returned handoffs it acquires from).
    """
    required_collaborators = (STORE, MODEL_PROVIDER, CONTINUATION)
    assignment_form = ASSIGNMENT_FORM

    def __init__(self, services, *, tools, resources):
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.perturbation_evidence.api_services import build_service
        from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
        if STORE not in services:
            raise ContractError('a106_result_acquisition_requires_service:' + STORE)
        if not isinstance(tools, Mapping) or not isinstance(resources, Mapping) or not resources:
            raise ContractError('a106_result_acquisition_tools_and_resources_required:' + self.binding_path)
        tool_registry = ToolRegistry(services[STORE], **dict(tools))
        # This binding's AppService services publish its acquired bundles on the run's shared Store.
        publication = AppServicePublication(tool_registry.store)
        built = {}
        for resource_id, configuration in resources.items():
            if not isinstance(resource_id, str) or not resource_id or not isinstance(configuration, Mapping):
                raise ContractError('a106_result_acquisition_resource_invalid:' + str(resource_id))
            try:
                built[resource_id] = build_service(configuration.get('service'), dict(configuration), tool_registry,
                                                   publication_callback=publication)
            except ValueError as error:
                raise ContractError('a106_result_acquisition_resource_not_admitted:' + resource_id + ':'
                                    + str(error)) from error
        self.tool_registry, self.services = tool_registry, built

    def contract_credit_unit(self, assignment):
        """One acquired handoff; every assigned handoff must be admitted by one of this binding's services."""
        handoffs_of(assignment, self.services)
        return 1.0

    def build_controller(self, bound, collaborators):
        """Completion of the assigned handoffs: target = their number, opened at zero acquired."""
        from yield_control import CompletionYieldController, YieldParameters
        continuation = collaborators[CONTINUATION]
        settings = continuation.get(self.binding_path) if isinstance(continuation, Mapping) else None
        if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters'}:
            raise ContractError('a106_result_acquisition_continuation_settings_require_cutoff_and_parameters:'
                                + self.binding_path)
        return CompletionYieldController(bound.episode_id, 0, settings['cutoff'],
                                         len(handoffs_of(bound.assignment, self.services)),
                                         YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        if dict(child_builders):
            raise ContractError('a106_result_acquisition_commissions_no_children')
        source = ResultAcquisitionSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ASSIGNMENT_FORM', 'CREDIT_DEFINITION', 'HANDOFF_FORM', 'INSTRUCTIONS', 'ResultAcquisitionBinding',
           'ResultAcquisitionSource', 'handoffs_of']
