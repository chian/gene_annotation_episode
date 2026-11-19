"""The A106 API job-execution decision source on the generic runner (BV-BRC AppService).

The commission assigns one AppService job: a configured ``resource_id`` (one of the binding's own
AppService services) and the original ``AppServiceRequest``. Each unit is one AppService launch
operation, chosen by the model:

- the source presents the job, the operations, the receipts this episode holds, its credit and the
  controller state, and asks ``model_provider.complete`` for one selection (recorded as
  ``decision.<position>.<attempt>``);
- admission resolves the selection's ``BoundInputs`` from what this episode holds
  (``held_inputs.HeldInputs``), refuses a remote effect slot this episode already issued, and
  prepares the operation locally (``BVBRCAppServiceService.prepare``). A failure there is a rejection
  before acquisition: no unit, no observation; the model decides again with the feedback;
- an admitted selection is one unit. A remote-mutating operation records its intent (and its effect
  rows, ``issued_unknown``) first; an intent found without an outcome after an interruption is never
  issued again and its outcome is ``issued_outcome_unknown``. The service makes its one request, the
  response is retained in the Store as its native source with its ``bvbrc_appservice_native_source_v1``
  record (``bvbrc_appservice_native_sources.retain_native_source``; a submission's record is what the
  proteome bundle reader checks the handoff's original task against), the service decodes it into an event, the effects
  are confirmed from that response (``confirm_appservice_effects``) and the typed receipt is built
  (``build_appservice_receipt``) and retained in the Store with the admitted scope it ran under
  (``scope``, whose digest is the receipt's ``origin.scope_sha256``). The outcome, including an invalid or
  failed one, is recorded as ``outcome.<position>`` and enters the iterator with the credit measured
  after it.

The receipts and confirmed effects this episode retains are its custody: later operations (prepare
from an enumerated definition, upload into a created node, submit from a preparation, status and
task_info of the original handoff) may name only them.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timezone
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from method_loop import Leaf

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.perturbation_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.forms.service_calls.perturbation_evidence.bvbrc_appservice_contracts import ContractValidationError, validate_contract
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_receipt_values import build_appservice_receipt, confirm_appservice_effects
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_records import VERSION as RECEIPT_VERSION, _encode, provisional_receipt_ref
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.bvbrc_appservice_native_sources import retain_native_source
from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import canonical, obj
from ...episode_contract import ContractRecord as Record
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.held_inputs import RECEIPT_PROVIDER, AppServiceInputError, HeldInputs, digest

MODEL_ROLE = 'REASONING'
CREDIT_DEFINITION = {
    'kind': 'a106_api_job_usable_handoff_v1',
    'unit': "the assigned AppService job, counted while this episode holds its confirmed TaskHandoff receipt and "
            "no later status observation of that task reports it failed",
    'target': 1,
    'scientific_credit': False,
}
INSTRUCTIONS = (
    'You run one assigned BV-BRC AppService job: the configured resource_id and its original request. Choose '
    'exactly one AppService launch operation per decision with its arguments. Operations are single requests: '
    'enumerate_apps reads the application catalog; prepare validates the original application and parameters '
    'locally against one selected definition (packaged, supplied by the request, or a record of a catalog '
    'receipt you hold); workspace_create, upload and workspace_metadata act on the request\'s own workspace '
    'targets, inputs and the rows of Workspace receipts you hold; submit issues the original prepared job once '
    'from your preparation receipt and the input evidence receipts you hold, and is never repeated; status and '
    'task_info read the original task of the handoff receipt you hold once, without waiting or polling. Name '
    'only receipts listed under held_receipts. The commission is complete when you hold a usable handoff whose '
    'latest status is not failed. This is operational progress, not scientific evidence; the configured '
    'controller owns continuation.'
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _effect_rows(prepared, operation_key, issued_at):
    return [validate_contract('EffectReceipt', {
        'version': 'selected_api_effect_receipt_v1',
        'effect_ref': 'api_effect_' + digest({'operation_key': operation_key, 'descriptor': descriptor}),
        'descriptor': descriptor, 'operation_key': operation_key, 'state': 'issued_unknown',
        'issued_at': issued_at, 'confirmation_source_ref': None, 'native_effect_identifiers': {},
        'ancillary_effects': [], 'failure': None}) for descriptor in prepared['effects']]


def _unconfirmed(rows, code, phase, outcome):
    failure = {'code': code, 'phase': phase, 'affected_refs': [row['effect_ref'] for row in rows],
               'affected_pointers': [], 'effect_outcome': outcome, 'valid_record_refs': [], 'requirements': []}
    state = 'not_sent' if outcome == 'not_sent' else 'issued_unknown'
    return [validate_contract('EffectReceipt', {**row, 'state': state, 'failure': failure}) for row in rows]


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied, self.outcomes, self.feedback = 0, [], None

    def apply(self, outcome):
        self.outcomes.append(outcome)
        self.feedback = outcome['feedback']
        self.applied += 1

    @property
    def held(self):
        """Receipt ref -> its contract, the prepared operation that produced it and that operation's effects."""
        return {outcome['receipt']['ref']: {'contract': outcome['receipt']['contract'], 'prepared': outcome['prepared'],
                                            'effects': outcome['effects']}
                for outcome in self.outcomes if outcome['receipt'] is not None}

    @property
    def issued_slots(self):
        return {canonical(row['descriptor']['slot']) for outcome in self.outcomes for row in outcome['effects']
                if row['state'] != 'not_sent'}

    @property
    def handoff(self):
        rows = [outcome for outcome in self.outcomes if outcome['receipt'] is not None
                and outcome['receipt']['contract'] == 'TaskHandoff']
        return rows[-1] if rows else None

    @property
    def latest_task_state(self):
        handoff = self.handoff
        if handoff is None:
            return None
        state = handoff['receipt']['state']
        for outcome in self.outcomes[self.outcomes.index(handoff) + 1:]:
            if outcome['receipt'] is not None and outcome['receipt']['contract'] == 'TaskObservation':
                state = outcome['receipt']['state']
        return state

    @property
    def record_refs(self):
        return list(dict.fromkeys(ref for outcome in self.outcomes for ref in outcome['record_refs']))


class ApiJobExecutionSource:
    """One assigned AppService job's model-selected operations over the binding's own services."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        if binding.tool_registry.store is not self._store:
            raise ContractError('a106_api_job_tool_registry_is_not_over_the_run_store:' + bound.binding_path)
        self._provider = collaborators['model_provider']
        self._scope = self._store.validate_scope(plain(bound.assignment['scope']))
        self._resource_id = bound.assignment['resource_id']
        self._service = binding.services[self._resource_id]
        try:
            self._request = self._service.validate_request(plain(bound.assignment['request']), self._scope)
        except ValueError as error:
            raise ContractError('a106_api_job_request_not_admitted:' + str(error)) from error
        self._owner = validate_contract('OriginalJobOwner', {
            'run_id': bound.run_id, 'launch_episode_id': bound.episode_id,
            # The commission that made this episode: its full structural path (parent path and own key).
            'parent_commission_operation_key': '/'.join(name + ':' + key for name, key in bound.path),
            'original_launch_assignment_sha256': digest(plain(bound.assignment))})
        self._state = _State()

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit(self):
        return 1.0 if self._state.handoff is not None and self._state.latest_task_state != 'failed' else 0.0

    def _controller_input(self, position, outcome):
        return Record({'credit': self.credit(),
                       'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': 'api_operation', 'operation': outcome['operation'],
                                'status': outcome['status']}})

    def _origin(self, position, name, arguments_sha256):
        return {'run_id': self._bound.run_id, 'episode_id': self._bound.episode_id,
                'operation_key': self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position),
                'name': name, 'arguments_sha256': arguments_sha256,
                'assignment_sha256': digest(plain(self._bound.assignment)), 'scope_sha256': digest(self._scope)}

    # -- presentation -------------------------------------------------------------
    def operations(self):
        return {item['name']: item for item in self._service.launch_catalog(self._request)}

    def action_schema(self):
        options = [obj({'operation': {'type': 'string', 'const': name}, 'arguments': item['input_schema']})
                   for name, item in sorted(self.operations().items())]
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'resource_id': self._resource_id,
            'service': self._service.service,
            'request': self._request,
            'operations': {name: item['description'] for name, item in sorted(self.operations().items())},
            'held_receipts': [{'receipt_ref': outcome['receipt']['ref'], 'contract': outcome['receipt']['contract'],
                               'operation': outcome['operation'], 'status': outcome['receipt']['status']}
                              for outcome in self._state.outcomes if outcome['receipt'] is not None],
            'events': [{'operation': outcome['operation'], 'event': outcome['event']}
                       for outcome in self._state.outcomes if outcome['event'] is not None],
            'current_credit': self.credit(),
            'credit_binding': CREDIT_DEFINITION,
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'last_outcome': self._summary(self._state.outcomes[-1]) if self._state.outcomes else None,
            'feedback': self._state.feedback,
        }

    # -- decisions ----------------------------------------------------------------
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
                selection, prepared = self.admit(position, response, schema)
            except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': schema_failure_diagnostic(error)
                                        if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return Leaf(selection, lambda chosen: self._execute(position, chosen, prepared),
                        lambda chosen, outcome: self._controller_input(position, outcome),
                        'api:' + str(position))

    def admit(self, position, response, schema):
        """Admit one response, resolve what it names and prepare it locally; any failure is a rejection."""
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a106_api_job_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        name, arguments = selection['operation'], selection['arguments']
        holder = HeldInputs(self._store, owner=self._owner, resource_id=self._resource_id, request=self._request,
                            held=self._state.held,
                            origin={key: value for key, value in self._origin(position, name, digest(arguments)).items()
                                    if key in ('run_id', 'episode_id', 'operation_key', 'assignment_sha256')})
        bound_inputs = holder.bind(name, arguments)
        handoff = self._state.handoff
        handle = ({'task_id': bound_inputs['resolved']['original_task']['task_id']}
                  if bound_inputs['resolved'].get('original_task') is not None and handoff is not None else None)
        prepared = self._service.prepare(name, self._request, arguments, scope=self._scope,
                                         previous_events=[], handle=handle, bound_inputs=bound_inputs)
        repeated = [row['slot'] for row in prepared['effects'] if canonical(row['slot']) in self._state.issued_slots]
        if repeated:
            raise AppServiceInputError('a106_api_effect_slot_already_issued_by_this_episode:' + canonical(repeated))
        return selection, prepared

    # -- execution ------------------------------------------------------------------
    def _retain_receipt(self, built, parents):
        """Retain one typed receipt in the Store; its record id is its receipt ref.

        The retained receipt records the admitted scope its operation ran under (``scope``) beside the typed
        value, whose ``origin.scope_sha256`` is that scope's digest: a watcher reads the task's scope from it.
        """
        common = built['value'] if built['contract'] == 'CommonReceipt' else built['value']['receipt']
        if common['origin']['scope_sha256'] != digest(self._scope):
            raise ContractError('a106_api_job_receipt_scope_digest_conflict')
        artifact = self._store.artifact(canonical({'version': RECEIPT_VERSION, 'contract': built['contract'],
                                                   'scope': self._scope,
                                                   'value': _encode(built['contract'], built['value'])}),
                                        'application/json')
        return self._store.put('source', {
            'provider': RECEIPT_PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None,
            'request_ref': None, 'version': RECEIPT_VERSION, 'retrieved_at': None,
            'parent_source_refs': list(dict.fromkeys(parents))}, origin='tool')['id']

    def _outcome(self, operation, prepared, status, *, event=None, effects=(), receipt=None, record_refs=(),
                 feedback=None):
        return {'kind': 'api_operation', 'operation': operation, 'status': status, 'prepared': prepared,
                'event': event, 'effects': list(effects), 'receipt': receipt,
                'record_refs': list(dict.fromkeys(record_refs)), 'feedback': feedback}

    async def _execute(self, position, selection, prepared):
        operation = selection['operation']
        origin = self._origin(position, operation, prepared['arguments_sha256'])
        effects = []
        if prepared['mutates_remote']:
            first = []
            effects = self._bound.recorder.recorded('intent.' + str(position), lambda: first.append(True) or
                                                    _effect_rows(prepared, origin['operation_key'], _now()))
            if not first:
                outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._outcome(
                    operation, prepared, 'failed',
                    effects=_unconfirmed(effects, 'issued_effect_unknown', 'recovery', 'unknown'),
                    feedback={'category': 'recovery', 'code': 'issued_outcome_unknown',
                              'detail': 'the original request was issued before an interruption; it is not '
                                        'issued again'}))
                self._state.apply(outcome)
                return outcome
        upload = {}
        if prepared['native_kind'] == 'upload':
            # The Store's connection belongs to this thread: the selected bytes are read here, not in transport.
            upload['upload_content'] = self._store.get_artifact(prepared['native_operands']['call']['content']['artifact_ref'])

        async def issue():
            try:
                snapshot = await asyncio.to_thread(self._service.invoke, prepared, **upload)
            except AcquisitionError as error:
                refs = [] if error.snapshot is None else [retain_native_source(
                    self._store, error.snapshot, origin=origin, prepared=prepared)['source_ref']]
                sent = 'not_sent' if error.submission_outcome == 'not_sent' and error.snapshot is None else 'unknown'
                return self._outcome(operation, prepared, 'failed', record_refs=refs,
                                     effects=_unconfirmed(effects, error.code, 'transport', sent), feedback={
                                         'category': 'acquisition', 'code': error.code, 'phase': error.phase,
                                         'submission_outcome': error.submission_outcome})
            binding = None
            refs = []
            if snapshot is not None:
                content = retain_native_source(self._store, snapshot, origin=origin, prepared=prepared)
                refs.append(content['source_ref'])
                binding = {'source_ref': content['source_ref'], 'content': content,
                           'retrieved_at': snapshot.retrieved_at, 'media_type': snapshot.media_type,
                           'transport': snapshot.transport, 'selected_operands': {
                               key: prepared[key] for key in
                               ('operation', 'request_sha256', 'arguments_sha256', 'native_operands')}}
            try:
                event = json.loads(canonical(self._service.decode(prepared, snapshot)))
                rows = effects
                if effects:
                    confirmed = confirm_appservice_effects(prepared, event, snapshot, snapshot_binding=binding,
                                                           effect_receipts=effects)
                    by_ref = {row['effect_ref']: row for row in confirmed}
                    rows = [validate_contract('EffectReceipt', {**row, **by_ref[row['effect_ref']]}) for row in effects]
                common = {'version': 'bvbrc_appservice_support_receipt_v1',
                          'receipt_ref': provisional_receipt_ref(origin), 'purpose': prepared['purpose'],
                          'origin': origin, 'snapshot': binding, 'effect_receipt_refs': [row['effect_ref'] for row in rows],
                          'status': 'ok', 'diagnostics': []}
                built = build_appservice_receipt(prepared, event, snapshot, common_receipt=common, effect_receipts=rows)
            except (ValueError, KeyError, TypeError, AcquisitionError, ContractValidationError) as error:
                return self._outcome(operation, prepared, 'invalid', record_refs=refs, effects=_unconfirmed(
                    effects, 'native_response_invalid', 'native_decode', 'unknown'), feedback={
                    'category': 'native_decode', 'code': getattr(error, 'code', None) or str(error)})
            reference = self._retain_receipt(built, refs)
            value = built['value']
            common = value if built['contract'] == 'CommonReceipt' else value['receipt']
            receipt = {'ref': reference, 'contract': built['contract'], 'status': common['status']}
            if built['contract'] in ('TaskHandoff', 'TaskObservation'):
                receipt['state'] = value['state']
            failed = event['failure_code'] is not None or common['status'] in ('failed', 'invalid', 'unknown')
            feedback = None if not failed else {
                'category': 'service_state', 'code': event['failure_code'] or common['status'],
                'state': event['state'], 'diagnostics': built['diagnostics']}
            return self._outcome(operation, prepared, 'failed' if failed else 'completed', event=event, effects=rows,
                                 receipt=receipt, record_refs=[*refs, reference], feedback=feedback)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), issue)
        self._state.apply(outcome)
        return outcome

    # -- result ---------------------------------------------------------------------
    @staticmethod
    def _summary(outcome):
        return {key: outcome[key] for key in ('operation', 'status', 'event', 'receipt', 'record_refs', 'feedback')}

    def result(self, record):
        """The API job handoff: its credit, the original task and the receipts and sources it retained."""
        self._catch_up(record.units_consumed)
        credit = self.credit()
        if isinstance(credit, bool) or not math.isfinite(credit):
            raise ContractError('a106_api_job_credit_must_be_finite')
        handoff = self._state.handoff
        return Record({'credit': credit, 'finding': {
            'resource_id': self._resource_id, 'service': self._service.service, 'request': self._request,
            'original_job_owner': self._owner,
            'handoff_ref': None if handoff is None else handoff['receipt']['ref'],
            'native_handle': None if handoff is None else handoff['event']['native_handle'],
            'handoff_ready': bool(credit), 'latest_task_state': self._state.latest_task_state,
            'operations': [self._summary(outcome) for outcome in self._state.outcomes],
            'record_refs': self._state.record_refs,
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['ApiJobExecutionSource', 'CREDIT_DEFINITION', 'INSTRUCTIONS', 'MODEL_ROLE']
