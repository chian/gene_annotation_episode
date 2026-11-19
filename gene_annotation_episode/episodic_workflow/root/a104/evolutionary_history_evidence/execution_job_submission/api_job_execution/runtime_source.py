"""The A104 API job-execution decision source on the generic runner.

The commission assigns one API job: a configured ``resource_id`` (one of this
binding's own API services) and the service ``request``. Each unit is one
operation of that service's launch catalog, chosen by the model:

- the source presents the job, the service's operations, the decoded events so
  far, the job's current handoff credit and the controller state, and asks
  ``model_provider.complete`` for one selection (recorded as
  ``decision.<position>.<attempt>``);
- a selection that fails admission (schema, or the service's own local
  ``prepare``, e.g. a second original submission) is rejected before
  acquisition: no unit, no observation; the model decides again with feedback;
- an admitted selection is one unit: the service makes its one request
  (``invoke``), the received response is retained in the Store as a source
  record, and the service decodes it into an event. The outcome, including a
  failed or invalid one, is recorded as ``outcome.<position>`` and enters the
  iterator with the credit measured after it.

Each recorded outcome is also published on the shared Store as an ``episode.api_job_receipt`` source
record (``api_job_receipts``) carrying the run, Episode, resource, request and assignment identity and the
scope; the outcome names it as ``receipt_ref`` and the handoff finding lists them as ``receipt_refs``. The
axis job provider (``library/job_provider``) builds the API job's progress target from these receipts.

A remote-mutating operation records its intent first; an intent recorded
without an outcome (an interrupted run) is never issued again: its outcome is
recorded as ``issued_outcome_unknown``.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from method_loop import Leaf

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical, obj
from ...runtime_bindings import UnitInput
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.api_job_receipts import ApiJobReceipts
from .runtime_credit import CREDIT_DEFINITION, handoff_credit

MODEL_ROLE = 'REASONING'
PROVIDER_PREFIX = 'api_job_execution.'
INSTRUCTIONS = (
    'You run one assigned API job: the configured remote service resource_id and its request. Choose exactly '
    'one operation of that service per decision. Operations are single requests: a submission is issued once '
    'for the original assigned request and is never repeated; a status operation reads the original native '
    'handle once and does not wait or poll. A preparation is local and sends nothing. The commission is '
    'complete when the original job has a usable handoff (its native handle accepted, running or complete); '
    'a failed or unknown status is not a handoff. Use the decoded events and their facts (including any '
    'earliest_request_after_seconds spacing) to choose the next operation. This is operational progress, not '
    'scientific evidence; the configured controller owns continuation.'
)


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied = 0
        self.outcomes = []
        self.feedback = None

    def apply(self, outcome):
        self.outcomes.append(outcome)
        self.feedback = outcome.get('feedback')
        self.applied += 1

    @property
    def events(self):
        return [outcome['event'] for outcome in self.outcomes if outcome['event'] is not None]

    @property
    def previous_events(self):
        return [{'name': outcome['operation'], 'event': outcome['event']}
                for outcome in self.outcomes if outcome['event'] is not None]

    @property
    def handle(self):
        handles = [event['native_handle'] for event in self.events if event['native_handle'] is not None]
        return handles[-1] if handles else None

    @property
    def record_refs(self):
        return list(dict.fromkeys(ref for outcome in self.outcomes for ref in outcome['record_refs']))

    @property
    def receipt_refs(self):
        return [outcome['receipt_ref'] for outcome in self.outcomes]


class ApiJobExecutionSource:
    """One assigned API job's model-selected operations over the binding's own services."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        if binding.tool_registry.store is not self._store:
            raise ContractError('a104_api_job_tool_registry_is_not_over_the_run_store:' + bound.binding_path)
        self._provider = collaborators['model_provider']
        self._scope = self._store.validate_scope(dict(bound.assignment['scope']))
        job = bound.assignment['assignment']
        if set(job) != {'resource_id', 'request'} or job['resource_id'] not in binding.services:
            raise ContractError('a104_api_job_assignment_requires_a_configured_resource_id_and_request:'
                                + ','.join(sorted(binding.services)))
        self._resource_id = job['resource_id']
        self._service = binding.services[self._resource_id]
        try:
            self._request = self._service.validate_request(dict(job['request']), self._scope)
        except ValueError as error:
            raise ContractError('a104_api_job_request_not_admitted:' + str(error)) from error
        self._state = _State()
        self._receipts = ApiJobReceipts(self._store, bound, self._scope, self._resource_id, self._service.service,
                                       self._request)

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit(self):
        return handoff_credit(self._state.events)

    def _controller_input(self, position, outcome):
        return UnitInput({'credit': self.credit(),
                               'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                               'unit': {'position': position, 'kind': 'api_operation',
                                        'operation': outcome['operation'], 'status': outcome['status']}})

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
            'operations': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                           for name, item in sorted(self.operations().items())},
            'events': self._state.previous_events,
            'native_handle': self._state.handle,
            'current_credit': self.credit(),
            'credit_binding': CREDIT_DEFINITION,
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_outcome': self._state.outcomes[-1] if self._state.outcomes else None,
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
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context, schema))
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
                        'api:' + str(position))

    def admit(self, response, schema):
        """Admit one response and prepare its operation locally; any failure is a rejection before acquisition."""
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a104_api_job_decision_response_must_be_exactly_selection')
        selection = json.loads(json.dumps(response['selection'], allow_nan=False))
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        prepared = self._service.prepare(selection['operation'], self._request, selection['arguments'],
                                         scope=self._scope, previous_events=self._state.previous_events,
                                         handle=self._state.handle)
        return selection, prepared

    # -- execution ------------------------------------------------------------------
    def _retain(self, operation, snapshot):
        """Retain one received service response as a source record in the shared Store."""
        artifact = self._store.artifact(snapshot.content, snapshot.media_type)
        request = self._store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}),
                                       'application/json')
        return self._store.put('source', {
            'provider': PROVIDER_PREFIX + operation, 'accession': None, 'uri': snapshot.url,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': request, 'version': None,
            'retrieved_at': snapshot.retrieved_at}, origin='external')['id']

    def _outcome(self, operation, status, *, event=None, record_refs=(), feedback=None):
        return {'kind': 'api_operation', 'operation': operation, 'status': status, 'event': event,
                'record_refs': list(record_refs), 'feedback': feedback}

    def _published(self, position, outcome):
        """The outcome with the reference of the receipt it is published as on the shared Store."""
        return {**outcome, 'receipt_ref': self._receipts.publish(position, outcome)}

    async def _execute(self, position, selection, prepared):
        operation = selection['operation']
        first = []
        if prepared['mutates_remote']:
            self._bound.recorder.recorded('intent.' + str(position), lambda: first.append(True) or {
                'operation': operation, 'request': self._request, 'native_handle': self._state.handle})
            if not first:
                outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._published(
                    position, self._outcome(operation, 'failed', feedback={
                        'category': 'recovery', 'code': 'issued_outcome_unknown',
                        'detail': 'the original request was issued before an '
                                  'interruption; it is not issued again'})))
                self._state.apply(outcome)
                return outcome

        async def attempt():
            try:
                snapshot = await asyncio.to_thread(self._service.invoke, prepared)
            except AcquisitionError as error:
                refs = [] if error.snapshot is None else [self._retain(operation, error.snapshot)]
                return self._outcome(operation, 'failed', record_refs=refs, feedback={
                    'category': 'acquisition', 'code': error.code, 'phase': error.phase,
                    'submission_outcome': error.submission_outcome})
            refs = [] if snapshot is None else [self._retain(operation, snapshot)]
            try:
                event = json.loads(canonical(self._service.decode(prepared, snapshot)))
            except (ValueError, AcquisitionError) as error:
                return self._outcome(operation, 'invalid', record_refs=refs, feedback={
                    'category': 'native_decode', 'code': getattr(error, 'code', None) or str(error)})
            if event['failure_code'] is not None:
                return self._outcome(operation, 'failed', event=event, record_refs=refs, feedback={
                    'category': 'service_state', 'code': event['failure_code'], 'state': event['state']})
            return self._outcome(operation, 'completed', event=event, record_refs=refs)

        async def issue():
            return self._published(position, await attempt())
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), issue)
        self._state.apply(outcome)
        return outcome

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The API job handoff: its credit and the original handle, events and retained responses."""
        self._catch_up(record.units_consumed)
        credit = self.credit()
        if isinstance(credit, bool) or not math.isfinite(credit):
            raise ContractError('a104_api_job_credit_must_be_finite')
        events = self._state.events
        latest = events[-1] if events else None
        return UnitInput({'credit': credit, 'report': {
            'resource_id': self._resource_id, 'service': self._service.service, 'request': self._request,
            'native_handle': self._state.handle,
            'handoff_ready': bool(credit),
            'result_available': bool(latest and latest['result_available']),
            'latest_state': None if latest is None else latest['state'],
            'operations': [{key: outcome[key] for key in ('operation', 'status', 'event', 'record_refs', 'receipt_ref',
                                                         'feedback')}
                           for outcome in self._state.outcomes],
            'receipt_refs': self._state.receipt_refs,
            'known_record_refs': self._state.record_refs,
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['ApiJobExecutionSource', 'INSTRUCTIONS', 'MODEL_ROLE']
