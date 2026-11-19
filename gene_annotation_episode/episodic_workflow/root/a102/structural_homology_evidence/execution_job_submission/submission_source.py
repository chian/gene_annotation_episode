"""A102 execution job submission on the generic runner: its assignment, decision source and continuation.

Every A102 submission binding (under the head, ``hpc_work_planning`` and ``hpc_allocation_execution``) mixes in
``JobSubmissionBinding`` before ``A102ContractBinding``.

The submission episode is commissioned with the concrete execution requests its parent selected
(``requests``: each a ``request_id`` and the requested ``job`` with its original inputs, settings and
constraints). Each unit is the model's choice of one request and one execution route child
(``api_job_execution``, ``local_job_execution`` or ``hpc_job_execution``) with that child's own declared
assignment. The route child owns iterative execution; this episode receives its typed return.

- A selection that fails admission (schema, an unknown request, an assignment the child's form refuses) creates
  no unit; the model decides again with that feedback.
- A route child's admitted return is that request's handoff. It is usable when the child's own credit is
  positive (the child measured that it got the computation accepted or running); a return without positive
  credit leaves the request pending for another route or attempt.
- Credit is the number of distinct requests with a usable handoff (one per request; never bounded or
  rescaled). Continuation is the completion yield controller with the commission's finite target, the number
  of requested jobs: a usable handoff of every request leaves exact zero remaining credit.
- Each decision is recorded through ``bound.recorder`` (``decision.<position>.<attempt>``) and each outcome as
  ``outcome.<position>``, so a resumed run repeats its selections and rebuilds its state.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Commission, DeclaredField, Field, RecordForm
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, ReportContract

from gene_annotation_episode.domain import ContractError

from ..contract_binding import CHILD_ASSIGNMENT, REPORT, RETURN, ContractRecord as Record
from ..runtime_continuation import A102UnitInput

AXIS = 'A102'
RETURN_FORM = RETURN
SCOPE = CHILD_ASSIGNMENT.fields['scope']
# Model decisions, the run's one shared Store, and this binding's completion settings by binding path.
COLLABORATORS = ('model_provider', 'store')

MODEL_ROLE = 'REASONING'
CONTINUATION = 'continuation'
REQUEST_FORM = RecordForm({
    'request_id': Field('text', 'The identity of this requested job within the commission'),
    'job': Field('record', 'The requested computation exactly as the parent selected it: its tool, original '
                           'inputs, settings and constraints'),
})
SUBMISSION_ASSIGNMENT = RecordForm({
    'scope': SCOPE,
    'requests': Field('list', 'The concrete execution requests to hand off to execution routes', items=REQUEST_FORM),
})
INSTRUCTIONS = (
    'You run the A102 execution job submission episode. Choose one requested job that has no usable handoff yet '
    'and the execution route child (API, local or HPC) to commission for it, with that child\'s own declared '
    'assignment. Capabilities, recorded inventory and timing information in the context inform the choice. '
    'Preserve the original job, its immutable inputs, constraints and pinned instructions in the child '
    'assignment. The route child owns iterative execution and returns its typed handoff with its own credit. A '
    'returned handoff with positive child credit is usable and completes that request; otherwise the request '
    'stays pending and you may choose another route or attempt. The configured controller owns continuation. '
    'Return exactly {"selection": ...}; the assignment is JSON text of the child assignment without its scope.')


def requests_of(assignment):
    """The commissioned requests keyed by their distinct ids; an empty or repeating list raises."""
    requests = {}
    for request in assignment['requests']:
        if request['request_id'] in requests:
            raise ContractError('a102_submission_request_id_repeats:' + request['request_id'])
        requests[request['request_id']] = request
    if not requests:
        raise ContractError('a102_submission_requires_requests')
    return requests


def _settings(binding_path, collaborators):
    continuation = collaborators[CONTINUATION]
    settings = continuation.get(binding_path) if isinstance(continuation, Mapping) else None
    if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters'}:
        raise ContractError('a102_submission_continuation_settings_require_cutoff_and_parameters:' + binding_path)
    return settings


def _assignment_schema(form):
    fields = {name: spec for name, spec in form.fields.items() if name != 'scope' and not isinstance(spec, DeclaredField)}
    return {'type': 'object', 'additionalProperties': False, 'required': [n for n, s in fields.items() if s.required],
            'properties': {name: {'description': spec.meaning} for name, spec in fields.items()}}


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied, self.handoffs, self.attempts, self.known_refs = 0, {}, [], []
        self.last_outcome = self.feedback = None

    def apply(self, outcome):
        self.attempts.append({key: outcome[key] for key in ('request_id', 'slot', 'child_credit', 'usable')})
        if outcome['usable'] and outcome['request_id'] not in self.handoffs:
            self.handoffs[outcome['request_id']] = {key: outcome[key] for key in ('slot', 'child_credit', 'child_return')}
        self.known_refs.extend(ref for ref in outcome['record_refs'] if ref not in self.known_refs)
        self.last_outcome, self.feedback = outcome, None
        self.applied += 1


class JobSubmissionSource:
    """The submission episode's model-selected route commissions over ``bound`` and its collaborators."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound, self._builders = binding, bound, child_builders
        self._store, self._provider = collaborators['store'], collaborators['model_provider']
        self._scope = self._store.validate_scope(dict(bound.assignment['scope']))
        self._requests = requests_of(bound.assignment)
        if not child_builders:
            raise ContractError('a102_submission_requires_route_children:' + bound.binding_path)
        for slot, builder in child_builders.items():
            if builder.return_form != RETURN_FORM:
                raise ContractError('a102_submission_child_return_form_differs:' + slot)
        self._state = _State()

    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    @property
    def credit(self):
        return len(self._state.handoffs)

    def action_schema(self):
        pending = [request_id for request_id in self._requests if request_id not in self._state.handoffs]
        options = [{'type': 'object', 'additionalProperties': False,
                    'required': ['kind', 'slot', 'request_id', 'objective', 'assignment'], 'properties': {
                        'kind': {'type': 'string', 'enum': ['episode_child']},
                        'slot': {'type': 'string', 'enum': [slot]},
                        'request_id': {'type': 'string', 'enum': pending or list(self._requests)},
                        'objective': {'type': 'string', 'minLength': 1},
                        'assignment': {'type': 'string', 'description': 'JSON text of the child assignment (without '
                                       'scope) admitted by: ' + json.dumps(builder.assignment_form.as_record())}}}
                   for slot, builder in sorted(self._builders.items())]
        return {'type': 'object', 'additionalProperties': False, 'required': ['selection'],
                'properties': {'selection': {'anyOf': options}}}

    def decision_context(self, view):
        state = view.controller_state
        return {'goal': self._bound.request.goal.as_record(), 'evidence_axis': AXIS, 'scope': self._scope,
                'requests': list(self._requests.values()),
                'handoffs': self._state.handoffs, 'attempts': self._state.attempts,
                'pending_request_ids': [r for r in self._requests if r not in self._state.handoffs],
                'current_credit': self.credit, 'completion_target': len(self._requests),
                'controller': state.as_record(),
                'units_consumed': view.units_consumed, 'last_local_outcome': self._state.last_outcome,
                'feedback': self._state.feedback,
                'route_children': {slot: {'binding_path': builder.binding_path,
                                          'assignment_form': builder.assignment_form.as_record()}
                                   for slot, builder in sorted(self._builders.items())}}

    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            schema, context = self.action_schema(), self.decision_context(view)
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context, schema))
            try:
                selection, commission = self.admit(response, schema)
            except (ValueError, KeyError, TypeError, ValidationError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract', 'detail': str(error)}
                attempt += 1
                continue
            return self._child(position, selection, commission)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a102_submission_response_must_be_exactly_selection')
        Draft202012Validator(schema).validate(response)
        selection = dict(response['selection'])
        assignment = json.loads(selection['assignment'])
        if not isinstance(assignment, dict) or 'scope' in assignment:
            raise ValueError('a102_submission_child_assignment_must_be_a_record_without_scope')
        Draft202012Validator(_assignment_schema(self._builders[selection['slot']].assignment_form)).validate(assignment)
        return selection, self._commission(selection, assignment)

    def _commission(self, selection, assignment):
        builder = self._builders[selection['slot']]
        assignment = {'scope': self._scope, **assignment, **builder.assignment_form.declared}
        builder.assignment_form.admit(assignment, 'a102_submission_child_assignment:' + selection['slot'])
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                 result_contract=dict(REPORT))
        message = Record({'scope': self._scope, 'request': self._requests[selection['request_id']]})
        return Commission(EpisodeRequest(goal, message, ReportContract(**REPORT)), assignment, builder.return_form)

    def _controller_input(self, position, outcome):
        return A102UnitInput(self.credit, self._bound.progress.receipt(position), tuple(outcome['record_refs']))

    def _child(self, position, selection, commission):
        slot, request_id = selection['slot'], selection['request_id']
        builder = self._builders[slot]
        child = builder(slot + '_' + str(position), commission)
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result, commission.report_form)
            refs = admitted['finding'].get('record_refs', [])
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a102_submission_child_record_refs_must_be_refs:' + slot)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'request_id': request_id, 'slot': slot, 'child_credit': admitted['credit'],
                'usable': admitted['credit'] > 0, 'child_return': admitted, 'record_refs': list(dict.fromkeys(refs)),
                'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, commission.report_form)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report)

    def result(self, record):
        self._catch_up(record.units_consumed)
        return Record({'credit': self.credit, 'finding': {
            'evidence_axis': AXIS, 'scope': self._scope, 'requests': list(self._requests.values()),
            'handoffs': self._state.handoffs,
            'pending_request_ids': [r for r in self._requests if r not in self._state.handoffs],
            'record_refs': list(self._state.known_refs),
            'ended_by': record.ended_by, 'units': record.units_consumed}})


class JobSubmissionBinding:
    """The submission hooks; mixed in before ``A102ContractBinding`` by each A102 submission binding."""

    required_collaborators = (*COLLABORATORS, CONTINUATION)
    assignment_form = SUBMISSION_ASSIGNMENT

    def build_controller(self, bound, collaborators):
        """Completion of the commissioned requests: target = their number, opened at zero handoffs."""
        from yield_control import CompletionYieldController, YieldParameters
        settings = _settings(self.binding_path, collaborators)
        return CompletionYieldController(bound.episode_id, 0, settings['cutoff'], len(requests_of(bound.assignment)),
                                         YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        source = JobSubmissionSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['INSTRUCTIONS', 'JobSubmissionBinding', 'JobSubmissionSource', 'SUBMISSION_ASSIGNMENT', 'requests_of']
