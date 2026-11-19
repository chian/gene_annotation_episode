"""A104 execution result acquisition on the generic runner: its assignment, decision source and continuation.

The episode is commissioned with the usable handoffs ``execution_job_submission`` returned (``handoffs``: each
the ``request_id``, the route ``slot`` that produced it and that route child's admitted ``child_return``). It
acquires the native results those handoffs point to, from what the route children retained on the run's
shared Store:

- an API handoff (``api_job_execution``) names its configured ``resource_id``, original ``request``,
  ``native_handle`` and the Store refs of its retained native responses. A ``result_request`` unit issues one
  operation of that service's own ``result_catalog`` (status or fetch) for the original handle and retains the
  received response as a ``source`` record; a ``result_publication`` unit publishes one retained fetch response
  through the service's own ``publish``, with the original submission response read back from the Store.
  An API handoff of a BV-BRC AppService resource names instead its ``original_job_owner`` and ``handoff_ref``
  (the ``TaskHandoff`` receipt the API job episode retained) and its commission assigns its ``selector``; an
  ``appservice_result`` unit issues one AppService result operation of it (``appservice_results``); a download
  that yields a usable ``AcquisitionReceipt`` also publishes the handoff's acquired bundle on the shared Store
  (``appservice_publication``);
- an HPC handoff (``hpc_job_execution``) or a local handoff (``local_job_execution``) names its native result
  receipts (``receipt_refs``: the ``source`` records of provider ``episode.practical_receipt`` its route child
  published on the shared Store; the local job runtime publishes each command receipt with ``publish_receipt``).
  An ``output_snapshot`` unit acquires one available output snapshot of a receipt: the captured bytes are
  verified against the receipt's size and sha256 and retained as a ``source`` record that points back to the
  receipt.

A request's native results are acquired when an API publication of it completed (or partially completed with
retained records), when this episode holds a usable ``AcquisitionReceipt`` for every requirement of an AppService
handoff's selector, or when every available output snapshot of its receipts is retained. Credit is the number
of requests with acquired results (one per request; never bounded or rescaled). Continuation is the completion
yield controller with target = the number of assigned handoffs. Each decision is recorded as
``decision.<position>.<attempt>`` and each outcome, including an invalid or failed one, as
``outcome.<position>``; a response that fails admission creates no unit and the model decides again.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Field, RecordForm
from method_loop import Episode, Leaf

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.evolutionary_history_evidence.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.findings.evolutionary_history_evidence.terminal_scientific_evidence import snapshot_bytes
# ---- A104's own forms and records (the axis-specific part of this module) ----------------------------------
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.evolutionary_history_evidence.api_services import build_service
from ..execution_job_submission.api_job_execution.configuration import build_api_service
from gene_annotation_episode.episodic_workflow.episode_support.records.service_calls.evolutionary_history_evidence.appservice_publication import AppServicePublication
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.evolutionary_history_evidence.appservice_results import ACTION as APPSERVICE_ACTION, SERVICE as APPSERVICE, AppServiceResults, admit_handoff
from ..runtime_bindings import SCOPE, DescendantBinding, UnitInput as Record

AXIS = 'A104'
PREFIX = 'a104'
# The record field of A104's descendant assignment that carries the handoffs.
ASSIGNMENT_FIELD = 'assignment'
# The launch's route slots (its children's roles), by the kind of handoff each returns.
ROUTES = {'launch_api': 'api', 'launch_hpc': 'hpc', 'launch_local': 'local'}
REQUIRED_COLLABORATORS = ('model_provider', 'store', 'continuation')


def child_finding(child_return):
    """The handoff finding of a route child's admitted return (A104: its ``report`` record)."""
    return child_return.get('report')


def returned(credit, finding, known_refs):
    """This episode's result in A104's descendant return form: its ``report`` with the records it rests on."""
    return {'credit': credit, 'report': {**finding, 'record_refs': list(known_refs)}}


def controller_input(credit, receipt, position, outcome):
    return Record({'credit': credit, 'estimation_context': {'progress_time': receipt},
                   'unit': {'position': position, 'kind': outcome['kind'], 'request_id': outcome['request_id'],
                            'status': outcome['status']}})


def listed_handoffs(assignment):
    """The assigned handoff list: ``handoffs`` of A104's descendant ``assignment`` record."""
    record = assignment[ASSIGNMENT_FIELD]
    return record.get('handoffs') if isinstance(record, Mapping) else None


def assignment_form(handoff_form):
    """A104's descendant assignment for the ``results`` role: the scope and the record carrying ``handoffs``."""
    return RecordForm({'scope': SCOPE, 'assignment': Field('record', "The parent's results assignment")})
# ------------------------------------------------------------------------------------------------------------

MODEL_ROLE = 'REASONING'
CONTINUATION = 'continuation'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RESPONSE_PROVIDER = 'execution_result_acquisition.'
SNAPSHOT_PROVIDER = 'execution_result_acquisition.output_snapshot'

HANDOFF_FORM = RecordForm({
    'request_id': Field('text', 'The requested job this handoff completed in the submission'),
    'slot': Field('text', 'The submission route slot that returned the handoff: ' + ', '.join(sorted(ROUTES))),
    'child_return': Field('record', "The route child's admitted return exactly as the submission recorded it"),
    'selector': Field('record', 'For an API handoff of a BV-BRC AppService resource only (required there): the '
                                'result selector (bvbrc_appservice_result_selector_v1) naming the outputs of '
                                'this job to acquire', required=False),
})
ASSIGNMENT_FORM = assignment_form(HANDOFF_FORM)
INSTRUCTIONS = (
    'You run the ' + AXIS + ' execution result acquisition episode. Each assigned handoff is a submitted job whose '
    'native results are to be acquired from what its route retained. Choose one action per decision: for an API '
    'handoff, one result_request (one operation of its service result catalog for the original native handle; '
    'single requests, no waiting or polling) or one result_publication (publish one retained, available result '
    'response of that request); for a BV-BRC AppService handoff, one appservice_result (one AppService result '
    'operation of its original task with its arguments: status and task_info read the original task; '
    'workspace_metadata, list_outputs and download_capability act on the request\'s own workspace targets and '
    'the rows of receipts you hold for that handoff; download acquires one object with a capability you hold or '
    'the selector supplies, for the selector requirements it meets; name only receipts listed under that '
    'handoff\'s held_receipts); for an HPC or local handoff, one output_snapshot (acquire one available '
    'output snapshot of one of its native result receipts). A request is acquired when its API result is '
    'published, every requirement of an AppService handoff\'s selector has a usable acquisition, or every '
    'available output snapshot of its receipts is retained. Use the events, facts '
    '(including any earliest_request_after_seconds spacing) and feedback in the context. The configured '
    'controller owns continuation. Return exactly {"selection": ...}.')


def _settings(binding_path, collaborators):
    continuation = collaborators[CONTINUATION]
    settings = continuation.get(binding_path) if isinstance(continuation, Mapping) else None
    if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters'}:
        raise ContractError(PREFIX + '_result_acquisition_continuation_requires_cutoff_and_parameters:' + binding_path)
    return settings


def handoffs_of(assignment, binding_path):
    """The assigned handoffs keyed by their distinct request ids; an empty, malformed or repeating list
    raises."""
    listed = listed_handoffs(assignment)
    if not isinstance(listed, list) or not listed:
        raise ContractError(PREFIX + '_result_acquisition_requires_handoffs')
    handoffs = {}
    for index, handoff in enumerate(listed):
        handoff = HANDOFF_FORM.admit(handoff, PREFIX + '_result_acquisition_handoff[' + str(index) + ']')
        if handoff['request_id'] in handoffs:
            raise ContractError(PREFIX + '_result_acquisition_request_id_repeats:' + handoff['request_id'])
        if handoff['slot'] not in ROUTES:
            raise ContractError(PREFIX + '_result_acquisition_unknown_route_slot:' + handoff['slot'])
        handoffs[handoff['request_id']] = handoff
    return handoffs


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied, self.outcomes, self.feedback = 0, [], None

    def apply(self, outcome):
        self.outcomes.append(outcome)
        self.feedback = outcome.get('feedback')
        self.applied += 1

    def of(self, request_id, kind=None):
        return [(position, outcome) for position, outcome in enumerate(self.outcomes)
                if outcome['request_id'] == request_id and (kind is None or outcome['kind'] == kind)]

    @property
    def record_refs(self):
        return list(dict.fromkeys(ref for outcome in self.outcomes for ref in outcome['record_refs']))


class ResultAcquisitionSource:
    """Model-selected acquisition actions over the assigned handoffs and the run's shared Store."""

    def __init__(self, binding, bound, collaborators):
        self._binding, self._bound = binding, bound
        self._store, self._provider = collaborators['store'], collaborators['model_provider']
        if binding.tool_registry.store is not self._store:
            raise ContractError(PREFIX + '_result_acquisition_tool_registry_is_not_over_the_run_store:'
                                + bound.binding_path)
        self._scope = self._store.validate_scope(dict(bound.assignment['scope']))
        self._handoffs = handoffs_of(bound.assignment, bound.binding_path)
        self._api, self._receipts, appservice = {}, {}, {}
        for request_id, handoff in self._handoffs.items():
            finding = child_finding(handoff['child_return'])
            if not isinstance(finding, Mapping):
                raise ContractError(PREFIX + '_result_acquisition_handoff_requires_a_finding:' + request_id)
            service = None
            if ROUTES[handoff['slot']] == 'api':
                service = self._binding.services.get(finding.get('resource_id'))
                if service is None or service.service != finding.get('service'):
                    raise ContractError(PREFIX + '_result_acquisition_api_resource_not_configured:' + request_id)
            if 'selector' in handoff and (service is None or service.service != APPSERVICE):
                raise ContractError(PREFIX + '_result_acquisition_selector_is_for_appservice_handoffs_only:'
                                    + request_id)
            if service is not None and service.service == APPSERVICE:
                appservice[request_id] = admit_handoff(request_id, handoff, finding, service)
            elif service is not None:
                self._api[request_id] = self._api_handoff(request_id, finding, service)
            else:
                self._receipts[request_id] = self._receipt_handoff(request_id, finding)
        self._appservice = AppServiceResults(self._store, self._scope, bound, appservice)
        self._state = _State()

    # -- the assigned handoffs, read from the shared Store ----------------------------------------------------
    def _api_handoff(self, request_id, finding, service):
        request = service.validate_request(dict(finding['request']), self._scope)
        if not finding.get('native_handle'):
            raise ContractError(PREFIX + '_result_acquisition_api_handoff_has_no_native_handle:' + request_id)
        submissions = [operation for operation in finding['operations']
                       if operation['status'] == 'completed' and operation['event'] is not None
                       and operation['event']['kind'] == 'job' and operation['event']['state'] == 'submitted'
                       and operation['record_refs']]
        if len(submissions) != 1:
            raise ContractError(PREFIX + '_result_acquisition_api_handoff_requires_one_retained_submission:'
                                + request_id)
        return {'service': service, 'request': request, 'handle': finding['native_handle'],
                'events': [{'name': operation['operation'], 'event': operation['event']}
                           for operation in finding['operations'] if operation['event'] is not None],
                'submission_ref': submissions[0]['record_refs'][0]}

    def _receipt_handoff(self, request_id, finding):
        refs = finding.get('receipt_refs')
        if not isinstance(refs, list) or not refs:
            raise ContractError(PREFIX + '_result_acquisition_receipt_handoff_has_no_receipt_refs:' + request_id)
        snapshots = []
        for ref in refs:
            source = self._store.get(ref)
            if source.get('record_type') != 'source' or source.get('provider') != RECEIPT_PROVIDER:
                raise ContractError(PREFIX + '_result_acquisition_receipt_ref_is_not_a_practical_receipt:' + ref)
            receipt = json.loads(self._store.get_artifact(source['artifact_ref']))['receipt']
            native = receipt['outcome'].get('native_outcome') or {}
            for row in native.get('output_snapshots') or []:
                if row.get('available') is True:
                    snapshots.append({'receipt_ref': ref, 'operation_key': receipt['operation_key'],
                                      'path': row['path'], 'sha256': row['sha256'], 'size_bytes': row['size_bytes'],
                                      'row': row})
        return snapshots

    def _snapshot(self, ref, service_name):
        """A retained native response read back from its Store ``source`` record."""
        source = self._store.get(ref)
        if source.get('record_type') != 'source':
            raise ContractError(PREFIX + '_result_acquisition_response_ref_is_not_a_source:' + ref)
        sent = json.loads(self._store.get_artifact(source['request_ref']))
        return SourceSnapshot(service=service_name, url=source['uri'], request=sent['request'],
                              retrieved_at=source['retrieved_at'], content=self._store.get_artifact(source['artifact_ref']),
                              media_type=self._store.get(source['artifact_ref'])['media_type'],
                              transport=sent['transport'])

    # -- credit ---------------------------------------------------------------------------------------------
    def acquired(self, request_id):
        if request_id in self._appservice:
            return self._appservice.acquired(request_id, self._state.outcomes)
        if request_id in self._api:
            return any(outcome['status'] in {'completed', 'partial'} and outcome['record_refs']
                       for _, outcome in self._state.of(request_id, 'result_publication'))
        retained = {outcome['path'] for _, outcome in self._state.of(request_id, 'output_snapshot')
                    if outcome['status'] == 'completed'}
        wanted = {row['path'] for row in self._receipts[request_id]}
        return bool(wanted) and wanted <= retained

    @property
    def credit(self):
        return sum(1 for request_id in self._handoffs if self.acquired(request_id))

    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    # -- presentation ---------------------------------------------------------------------------------------
    def _publishable(self, request_id):
        return [position for position, outcome in self._state.of(request_id, 'result_request')
                if outcome['status'] == 'completed' and outcome['event']['result_available']]

    def action_schema(self):
        options = []
        for request_id, api in sorted(self._api.items()):
            for item in api['service'].result_catalog(api['request'], {}):
                options.append(_object({'action': {'const': 'result_request'}, 'request_id': {'const': request_id},
                                         'operation': {'const': item['name']}, 'arguments': item['input_schema']}))
            publishable = self._publishable(request_id)
            if publishable:
                options.append(_object({'action': {'const': 'result_publication'},
                                        'request_id': {'const': request_id},
                                        'response_position': {'enum': publishable}}))
        for request_id in sorted(self._handoffs):
            if request_id in self._appservice:
                options.extend(_object(option) for option in self._appservice.options(request_id))
        for request_id, snapshots in sorted(self._receipts.items()):
            if snapshots:
                options.append(_object({'action': {'const': 'output_snapshot'}, 'request_id': {'const': request_id},
                                        'receipt_ref': {'enum': sorted({row['receipt_ref'] for row in snapshots})},
                                        'path': {'enum': sorted({row['path'] for row in snapshots})}}))
        if not options:
            raise ContractError(PREFIX + '_result_acquisition_offers_no_action:' + self._bound.binding_path)
        return _object({'selection': {'anyOf': options}})

    def decision_context(self, view):
        state = view.controller_state
        return {'goal': self._bound.request.goal.as_record(), 'evidence_axis': AXIS, 'scope': self._scope,
                'api_handoffs': {request_id: {'service': api['service'].service, 'request': api['request'],
                                              'native_handle': api['handle'], 'handoff_events': api['events'],
                                              'result_catalog': [{k: v for k, v in item.items() if k != 'input_schema'}
                                                                 for item in api['service'].result_catalog(
                                                                     api['request'], {})],
                                              'acquired': self.acquired(request_id)}
                                 for request_id, api in sorted(self._api.items())},
                'appservice_handoffs': {request_id: self._appservice.context(request_id, self._state.outcomes)
                                        for request_id in sorted(self._handoffs) if request_id in self._appservice},
                'receipt_handoffs': {request_id: {'output_snapshots': [{k: row[k] for k in (
                                                      'receipt_ref', 'operation_key', 'path', 'sha256', 'size_bytes')}
                                                      for row in snapshots],
                                                  'acquired': self.acquired(request_id)}
                                     for request_id, snapshots in sorted(self._receipts.items())},
                'outcomes': [{'position': position, **{k: v for k, v in outcome.items()}}
                             for position, outcome in enumerate(self._state.outcomes)],
                'current_credit': self.credit, 'completion_target': len(self._handoffs),
                'controller': state.as_record() if hasattr(state, 'as_record') else None,
                'units_consumed': view.units_consumed, 'feedback': self._state.feedback}

    # -- decisions --------------------------------------------------------------------------------------------
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
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': str(error)}
                attempt += 1
                continue
            return Leaf(selection, lambda chosen: self._execute(position, chosen, prepared),
                        lambda chosen, outcome: self._controller_input(position, outcome),
                        selection['action'] + ':' + str(position))

    def admit(self, response, schema):
        """Admit one response and prepare its action locally; any failure is a rejection before acquisition."""
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError(PREFIX + '_result_acquisition_response_must_be_exactly_selection')
        Draft202012Validator(schema).validate(response)
        selection = dict(response['selection'])
        request_id = selection['request_id']
        if selection['action'] == 'result_request':
            api = self._api[request_id]
            own = [{'name': outcome['operation'], 'event': outcome['event']}
                   for _, outcome in self._state.of(request_id, 'result_request') if outcome['event'] is not None]
            return selection, api['service'].prepare(selection['operation'], api['request'], selection['arguments'],
                                                     scope=self._scope, previous_events=api['events'] + own,
                                                     handle=api['handle'], selector={})
        if selection['action'] == 'result_publication':
            return selection, None
        if selection['action'] == APPSERVICE_ACTION:
            return selection, self._appservice.admit(selection, self._state.outcomes)
        row = [row for row in self._receipts[request_id]
               if row['receipt_ref'] == selection['receipt_ref'] and row['path'] == selection['path']]
        if not row:
            raise ValueError(PREFIX + '_result_acquisition_receipt_has_no_such_output_snapshot')
        return selection, row[0]

    # -- execution ------------------------------------------------------------------------------------------
    def _outcome(self, selection, status, **fields):
        outcome = {'kind': selection['action'], 'request_id': selection['request_id'], 'status': status,
                   'operation': selection.get('operation'), 'path': selection.get('path'), 'event': None,
                   'record_refs': [], 'feedback': None}
        outcome.update(fields)
        return outcome

    def _retain(self, operation, snapshot):
        artifact = self._store.artifact(snapshot.content, snapshot.media_type)
        request = self._store.artifact(canonical({'request': snapshot.request, 'transport': snapshot.transport}),
                                       'application/json')
        return self._store.put('source', {
            'provider': RESPONSE_PROVIDER + operation, 'accession': None, 'uri': snapshot.url,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': request, 'version': None,
            'retrieved_at': snapshot.retrieved_at}, origin='external')['id']

    async def _execute(self, position, selection, prepared):
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)
        effects = []
        if selection['action'] == APPSERVICE_ACTION:
            effects, recovered = self._appservice.intent(position, selection, prepared, self._outcome)
            if recovered is not None:
                outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: recovered)
                self._state.apply(outcome)
                return outcome

        # The Store is bound to the loop's thread: only a remote service request leaves it.
        async def run():
            if selection['action'] == APPSERVICE_ACTION:
                return await self._appservice.execute(position, selection, prepared, effects, self._state.outcomes,
                                                      self._outcome)
            if selection['action'] == 'result_request':
                return await self._request(selection, prepared)
            if selection['action'] == 'result_publication':
                return self._publish(selection, key)
            return self._output_snapshot(selection, prepared)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), run)
        self._state.apply(outcome)
        return outcome

    async def _request(self, selection, prepared):
        service = self._api[selection['request_id']]['service']
        try:
            snapshot = await asyncio.to_thread(service.invoke, prepared)
        except AcquisitionError as error:
            refs = [] if error.snapshot is None else [self._retain(selection['operation'], error.snapshot)]
            return self._outcome(selection, 'failed', record_refs=refs, feedback={
                'category': 'acquisition', 'code': error.code, 'phase': error.phase})
        refs = [] if snapshot is None else [self._retain(selection['operation'], snapshot)]
        try:
            event = json.loads(canonical(service.decode(prepared, snapshot)))
        except (ValueError, AcquisitionError) as error:
            return self._outcome(selection, 'invalid', record_refs=refs, feedback={
                'category': 'native_decode', 'code': getattr(error, 'code', None) or str(error)})
        if event['failure_code'] is not None:
            return self._outcome(selection, 'failed', event=event, record_refs=refs, feedback={
                'category': 'service_state', 'code': event['failure_code'], 'state': event['state']})
        return self._outcome(selection, 'completed', event=event, record_refs=refs)

    def _publish(self, selection, key):
        api = self._api[selection['request_id']]
        response = self._state.outcomes[selection['response_position']]
        name = api['service'].service
        try:
            published = api['service'].publish(
                api['request'], {}, self._snapshot(response['record_refs'][0], name), self._scope, key,
                submission_snapshot=self._snapshot(api['submission_ref'], name), handle=api['handle'])
        except (ValueError, ContractError, AcquisitionError) as error:
            return self._outcome(selection, 'failed', feedback={
                'category': 'publication', 'code': getattr(error, 'code', None) or str(error)})
        return self._outcome(selection, published['status'], record_refs=list(published['record_refs']),
                             feedback=published['feedback'])

    def _output_snapshot(self, selection, row):
        try:
            content = snapshot_bytes(row['row'])
        except (ValueError, OSError) as error:
            return self._outcome(selection, 'failed', feedback={
                'category': 'output_snapshot', 'code': 'captured_output_not_verified',
                'exception_type': type(error).__name__, 'detail': str(error)})
        with self._store.transaction():
            artifact = self._store.artifact(content, 'application/octet-stream')
            request = self._store.artifact(canonical({'receipt_ref': row['receipt_ref'],
                                                      'operation_key': row['operation_key'], 'path': row['path'],
                                                      'sha256': row['sha256']}), 'application/json')
            receipt = self._store.get(row['receipt_ref'])
            ref = self._store.put('source', {
                'provider': SNAPSHOT_PROVIDER, 'accession': row['sha256'], 'uri': None, 'artifact_ref': artifact,
                'text_ref': None, 'request_ref': request, 'version': None,
                'retrieved_at': receipt['retrieved_at']}, origin='tool')['id']
        return self._outcome(selection, 'completed', record_refs=[ref])

    def _controller_input(self, position, outcome):
        return controller_input(self.credit, self._bound.progress.receipt(position), position, outcome)

    def result(self, record):
        self._catch_up(record.units_consumed)
        return Record(returned(self.credit, {
            'evidence_axis': AXIS, 'scope': self._scope,
            'acquired_request_ids': [r for r in self._handoffs if self.acquired(r)],
            'pending_request_ids': [r for r in self._handoffs if not self.acquired(r)],
            'outcomes': list(self._state.outcomes), 'known_record_refs': self._state.record_refs,
            'ended_by': record.ended_by, 'units': record.units_consumed}, self._state.record_refs))


def _object(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': sorted(properties),
            'properties': properties}


class ResultAcquisitionBinding:
    """The result acquisition hooks; mixed in before the axis contract binding. Constructed by the home factory
    with its own tool registry over the run's shared store and the API resources the submission's API route
    uses, so each API handoff's ``resource_id`` names one of its own services."""

    required_collaborators = REQUIRED_COLLABORATORS
    assignment_form = ASSIGNMENT_FORM

    def __init__(self, *, tool_registry, api_resources):
        if not isinstance(api_resources, Mapping):
            raise ContractError(PREFIX + '_result_acquisition_api_resources_must_be_a_mapping')
        services = {}
        for resource_id, configuration in api_resources.items():
            if not isinstance(configuration, Mapping) or not isinstance(configuration.get('service'), str):
                raise ContractError(PREFIX + '_result_acquisition_api_resource_must_name_its_service:'
                                    + str(resource_id))
            if configuration['service'] == APPSERVICE:
                # This binding's AppService services publish its acquired bundles on the run's shared Store.
                services[resource_id] = build_service(APPSERVICE, dict(configuration), tool_registry,
                                                      publication_callback=AppServicePublication(tool_registry.store))
            else:
                services[resource_id] = build_api_service(configuration['service'], configuration, tool_registry)
        self.tool_registry, self.services = tool_registry, services

    def build_controller(self, bound, collaborators):
        """Completion of the assigned handoffs: target = their number, opened at zero acquired."""
        from yield_control import CompletionYieldController, YieldParameters
        settings = _settings(self.binding_path, collaborators)
        target = len(handoffs_of(bound.assignment, self.binding_path))
        return CompletionYieldController(bound.episode_id, 0, settings['cutoff'], target,
                                         YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        if dict(child_builders):
            raise ContractError(PREFIX + '_result_acquisition_commissions_no_children')
        source = ResultAcquisitionSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ASSIGNMENT_FORM', 'INSTRUCTIONS', 'ResultAcquisitionBinding', 'ResultAcquisitionSource',
           'ResultsBinding', 'handoffs_of']


class ResultsBinding(ResultAcquisitionBinding, DescendantBinding):
    """An A104 ``results`` binding (each ``.../execution_result_acquisition`` path): the descendant hooks with
    this module's result acquisition source and completion continuation."""

    def __init__(self, binding_path, commissioning_parent, child_slots, roles_by_grain, *, tool_registry,
                 api_resources):
        DescendantBinding.__init__(self, binding_path, 'results', commissioning_parent, child_slots, roles_by_grain)
        ResultAcquisitionBinding.__init__(self, tool_registry=tool_registry, api_resources=api_resources)
