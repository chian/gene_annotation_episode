"""The A107 head's own iteration cycle on the generic runner (``episode_runtime``).

One unit of the head is one decision of its own made by the model provider and
then executed: a selected actual tool, a scientific reasoning commit to the
store, or a commissioned child episode (one of the head's declared slots). The
cycle works on ``bound``, its collaborators and the head's own library and tools:

- **Decision.** The model provider (``complete(episode_id, role, instructions,
  context, output_schema)``, the shared ``gene_annotation_episode.model_provider.ModelProvider``)
  receives the A107 axis instructions, the store's reasoning view of the
  episode's scope, the tool catalog with each tool's input schema, the store's
  reasoning schema, the declared child slots with their assignment forms, the
  previous outcome and any feedback. Each response is recorded through
  ``bound.recorder`` so a resumed run repeats it. A provider failure ends the
  source (``source_failed``).
- **Rejection.** A response that does not select a valid action creates no
  unit: its feedback is shown on the next decision of the same position.
- **Execution.** A tool runs through the head's own ``A107ToolRegistry`` (built by the
  home factory over the run's shared store) with the episode scope, a deterministic
  operation key and the action's ``ActionInvocation`` (context/partner tools receive only the
  record references this episode has received; the invocation also carries the admitted
  request and assignment, the unit position, the recorded decision's name and the
  recorder, from which ``received_inputs.ReceivedInputs`` establishes the producer of each
  received File/Source it reads); a reasoning commit goes to
  ``store.commit_reasoning``; a child is built through its slot's
  ``ChildBuilder`` with a ``Commission`` whose assignment fills exactly the
  child's declared form. Every returned outcome, including an invalid or
  failed one, enters the controller with the episode's measured credit.
- **Credit.** ``investigation_progress.ScientificFindingProgress``: one
  explicit ``finding_unit`` per distinct retained typed finding among the
  assessment references this episode has received (opening baseline: the
  assessments visible when it was commissioned; then every assessment shown in
  a decision, written by its own reasoning, or returned by a child). Corrections
  and withdrawals retire findings. A child's own credit is recorded with the
  unit but is never summed into the parent: the parent receives the child's
  findings and projects them itself. Credit is cumulative and unbounded; it is
  never clamped or rescaled. Each unit carries its recorded progress-time
  receipt (``bound.progress``) as the yield controller's estimation context.
- **Result.** ``{'credit': current - opening, 'finding': <the projection with
  the received assessment references>}``.

Selection (C3/C6): the commission chooses one library thought pattern and a subset of
the head's own tools; only those tools are offered and the thought pattern and the
library's A107 evidence-axis entry are presented with every decision. A child slot's
choice and subset fields are chosen by this decision (``assignment_json``).

The cycle has no contract-information exchanges, no ``wait`` action over pending
jobs, no shared-information operations and no report-redelivery action.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, ClosedRecord, Episode, EpisodeGoal, EpisodeRequest, Leaf, ReportContract
from method_loop.episode import SourceEnd

from gene_annotation_episode.episodic_workflow.episode_support.tools.action_invocation import ActionInvocation
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError
from gene_annotation_episode.model_provider import ModelCallError

from .axis_instructions import INSTRUCTIONS

CYCLE_VERSION = 'a107_head_cycle_v1'
MODEL_ROLE = 'REASONING'
# Tools that read only records this episode has received.
_RECEIVED_RECORD_TOOLS = ('context.', 'partner.')
_RECEIVED_RECORD_TOOL_NAMES = frozenset({'reference.neighborhood', 'result.blast.hsp', 'source.locate'})
_ACTIONS = ('tool', 'reason', 'child')

CHILD_REPORT_CONTRACT = {
    'decision': 'Choose the next A107 action or child for the parent partner-presence investigation',
    'measurements': {'credit': "The child's own credit on the A107 finding-unit scale (recorded, not summed)"},
    'information': {'finding': "The child's retained typed A107 findings and the assessment references it received"},
}

CYCLE_GUIDANCE = (
    'Each decision selects exactly one action of this episode. kind=tool runs one tool from the supplied '
    'tool_catalog: name it in tool and give its arguments as JSON text in arguments_json matching that '
    "tool's input_schema. kind=reason commits a scientific interpretation: give commit_json, JSON text "
    'matching reasoning_schema. kind=child commissions one declared child slot: name the slot, its '
    'objective, its scope as JSON text in scope_json (within this episode scope) and, when the slot form '
    "lists further fields, a JSON object of exactly those fields as assignment_json (choose each choice and subset "
    "field from its listed options). Set every field the selected "
    'kind does not use to null. Only the supplied tools and child slots exist. Credit counts distinct '
    'retained typed findings this episode has received; the configured controller owns continuation.')


class CycleError(ContractError):
    """A collaborator or recorded value does not satisfy the A107 head cycle."""


@dataclass(frozen=True)
class CycleRecord(ClosedRecord):
    """One A107 controller input, request message or result: plain JSON values."""
    value: dict

    def as_record(self):
        return dict(self.value)


def _finite(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CycleError('a107_' + what + '_must_be_a_finite_number')
    return float(value)


def collaborator(collaborators, name, methods):
    """A required runtime collaborator exposing the named methods."""
    if name not in collaborators:
        raise CycleError('a107_collaborator_required:' + name)
    value = collaborators[name]
    missing = [method for method in methods if not callable(getattr(value, method, None))]
    if missing:
        raise CycleError('a107_collaborator_interface:' + name + ':' + ','.join(missing))
    return value


STORE_METHODS = ('validate_scope', 'reasoning_view', 'reasoning_schema', 'commit_reasoning', 'get', 'read_snapshot')
PROVIDER_METHODS = ('complete',)


def head_settings(collaborators, binding_path):
    """The head's explicit continuation and credit settings: ``{cutoff, parameters, finding_unit}``."""
    continuation = collaborators['continuation']
    settings = continuation.get(binding_path) if isinstance(continuation, Mapping) else None
    if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters', 'finding_unit'}:
        raise CycleError('a107_head_continuation_settings_required:' + binding_path
                         + ':{cutoff,parameters,finding_unit}')
    return settings


def finding_progress(settings):
    from gene_annotation_episode.episodic_workflow.episode_support.findings.partner_presence_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=settings['finding_unit']))


def visible_assessment_refs(view):
    """The assessment references shown to a decision in one reasoning view."""
    return [row['id'] for row in view.get('assessments', ())]


def opening_known(bound, store):
    """The assessments visible when this episode was commissioned (recorded once; the baseline)."""
    scope = store.validate_scope(bound.assignment['scope'])
    return bound.recorder.recorded('a107_opening_known_assessment_refs',
                                   lambda: sorted(visible_assessment_refs(store.reasoning_view(scope))))


def project(store, scope, settings, known):
    return finding_progress(settings)(store, scope, known_assessment_refs=sorted(known))


def opening_credit(bound, store, settings):
    scope = store.validate_scope(bound.assignment['scope'])
    return _finite(project(store, scope, settings, opening_known(bound, store))['credit'], 'opening_credit')


def _json_text(value, what):
    if type(value) is not str:
        raise CycleError('a107_' + what + '_json_required')
    try:
        return json.loads(value)
    except ValueError as error:
        raise CycleError('a107_' + what + '_json_invalid') from error


def decision_schema(slots):
    """The closed response schema: one selection whose unused fields are null."""
    nullable = {'type': ['string', 'null']}
    properties = {'kind': {'enum': list(_ACTIONS)}, 'tool': nullable, 'arguments_json': nullable,
                  'commit_json': nullable, 'slot': {'enum': [*slots, None]}, 'objective': nullable,
                  'scope_json': nullable, 'assignment_json': nullable}
    selection = {'type': 'object', 'properties': properties, 'required': list(properties),
                 'additionalProperties': False}
    return {'type': 'object', 'properties': {'selection': selection}, 'required': ['selection'],
            'additionalProperties': False}


def child_slot_options(child_builders):
    """Each declared child slot, its child binding and the assignment fields the parent fills (with their options)."""
    options = {}
    for slot, builder in child_builders.items():
        fields = builder.assignment_form.fields
        if 'scope' not in fields or isinstance(fields['scope'], DeclaredField):
            raise CycleError('a107_child_assignment_requires_scope:' + slot)
        for name in ('credit', 'finding'):
            if name not in builder.return_form.fields:
                raise CycleError('a107_child_return_form_missing:' + slot + ':' + name)
        chosen = {}
        for name, spec in fields.items():
            if isinstance(spec, DeclaredField) or name == 'scope':
                continue
            chosen[name] = {'type': spec.type, 'meaning': spec.meaning, 'required': spec.required}
            if isinstance(spec, (ChoiceField, SubsetField)):
                chosen[name]['options'] = list(spec.options)
                chosen[name]['choose'] = 'one' if isinstance(spec, ChoiceField) else 'subset'
        options[slot] = {'binding_path': builder.binding_path, 'assignment_fields': chosen}
    return options


class HeadCycleSource:
    """The A107 head's decision source (``next(view)``), executing each selected action."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound, self._builders = binding, bound, child_builders
        self._store = collaborator(collaborators, 'store', STORE_METHODS)
        # The head's own tool registry (C4), built by the home factory over the run's shared store.
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise CycleError('a107_tool_registry_is_not_over_the_run_store')
        self._provider = collaborator(collaborators, 'model_provider', PROVIDER_METHODS)
        self._settings = head_settings(collaborators, binding.binding_path)
        self._scope = self._store.validate_scope(bound.assignment['scope'])
        self._selected_tools = tuple(bound.assignment['tools'])
        self._thought_pattern = binding.thought_patterns[bound.assignment['thought_pattern']]
        self._slots = child_slot_options(child_builders)
        self._objective = bound.request.message.as_record()['objective']
        self._position = None
        self._known, self._received = set(), set()
        self._last_outcome, self._feedback = None, None

    # -- state -------------------------------------------------------------

    def _restore(self, position):
        """Rebuild the source state at ``position`` from what it recorded (replayed units are not shown)."""
        if position == 0:
            self._known = set(opening_known(self._bound, self._store))
            self._received = set(self._known)
            self._last_outcome, self._feedback = None, None
        else:
            saved = self._bound.recorder.recall('a107_state_' + str(position - 1))
            self._known, self._received = set(saved['known']), set(saved['received'])
            self._last_outcome, self._feedback = saved['last_outcome'], saved['feedback']
        self._position = position

    def _record_state(self, position):
        state = {'known': sorted(self._known), 'received': sorted(self._received),
                 'last_outcome': self._last_outcome, 'feedback': self._feedback}
        return self._bound.recorder.recorded('a107_state_' + str(position), lambda: state)

    def _timing(self, position):
        """The unit's recorded progress-time receipt, which the yield controller fits its forecast on."""
        return {'progress_time': self._bound.progress.receipt(position)}

    def _credit(self):
        return project(self._store, self._scope, self._settings, self._known)

    # -- decision ----------------------------------------------------------

    def instructions(self):
        return INSTRUCTIONS['A107'] + '\n\n' + CYCLE_GUIDANCE

    def catalog(self):
        """Only the tools this commission selected (``assignment['tools']``) from the head's own registry."""
        catalog = self._tools.catalog(self._scope)
        missing = sorted(set(self._selected_tools) - set(catalog))
        if missing:
            raise CycleError('a107_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: catalog[name] for name in self._selected_tools}

    def context(self, position, attempt, controller_state):
        view = self._store.reasoning_view(self._scope)
        shown = visible_assessment_refs(view)
        self._known.update(shown)
        self._received.update(shown)
        self._received.update(row['id'] for field in ('observations', 'sources', 'hypotheses', 'annotations')
                              for row in view.get(field, ()))
        return {'version': CYCLE_VERSION, 'objective': self._objective, 'scope': self._scope,
                'evidence_axis': self._binding.evidence_axis, 'thought_pattern': self._thought_pattern,
                'position': position, 'attempt': attempt,
                'credit': controller_state.current_credit,
                'records': view, 'tool_catalog': self.catalog(), 'reasoning_schema': self._store.reasoning_schema(),
                'child_slots': self._slots, 'last_outcome': self._last_outcome, 'feedback': self._feedback}

    async def next(self, view):
        position = view.units_consumed
        if self._position != position:
            self._restore(position)
        attempt = 0
        while True:
            name = 'a107_decision_' + str(position) + '_' + str(attempt)
            context = self.context(position, attempt, view.controller_state)
            schema = decision_schema(tuple(self._slots))
            try:
                response = await self._bound.recorder.recorded_async(name, lambda: self._provider.complete(
                    self._bound.episode_id, MODEL_ROLE, self.instructions(), context, schema))
            except ModelCallError as error:
                self._feedback = {'status': 'failed', 'category': 'decision_source',
                                  'exception_type': type(error).__name__, 'detail': str(error)}
                return SourceEnd('source_failed')
            try:
                unit = self._unit(position, response, schema, name)
            except (CycleError, ValidationError, ValueError, KeyError, TypeError) as error:
                self._feedback = {'status': 'invalid', 'category': 'action_contract',
                                  'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            self._feedback = None
            return unit

    # -- units -------------------------------------------------------------

    def _unit(self, position, response, schema, decision_name):
        Draft202012Validator(schema).validate(response)
        selection = response['selection']
        kind = selection['kind']
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)
        if kind == 'tool':
            return self._tool_unit(position, selection, key, decision_name)
        if kind == 'reason':
            return self._reason_unit(position, selection, key)
        return self._child_unit(position, selection)

    def _leaf(self, position, label, execute):
        async def extract(_unit):
            return await self._bound.recorder.recorded_async('a107_outcome_' + str(position), execute)

        def result(_unit, outcome):
            return self._observe(position, label, outcome)
        return Leaf(unit=label, extract=extract, result=result, label=label + ':' + str(position))

    def _tool_unit(self, position, selection, key, decision_name):
        name = selection['tool']
        catalog = self.catalog()
        if name not in catalog:
            raise CycleError('a107_tool_not_in_catalog:' + str(name))
        arguments = _json_text(selection['arguments_json'], 'arguments')
        Draft202012Validator(catalog[name]['input_schema']).validate(arguments)
        options = ({'permitted_record_refs': sorted(self._received)}
                   if name.startswith(_RECEIVED_RECORD_TOOLS) or name in _RECEIVED_RECORD_TOOL_NAMES else {})
        invocation = ActionInvocation(self._bound.run_id, self._bound.episode_id, self._binding.binding_path,
                                      self._scope, tuple(sorted(self._received)), self._bound.request.as_record(),
                                      plain(self._bound.assignment), position, decision_name, self._bound.recorder)

        async def execute():
            outcome = await self._tools.execute_async(name, arguments, scope=self._scope, operation_key=key,
                                                      invocation=invocation, **options)
            return {'kind': 'tool', 'tool': name, 'arguments': arguments, 'outcome': outcome}
        return self._leaf(position, 'tool', execute)

    def _reason_unit(self, position, selection, key):
        payload = _json_text(selection['commit_json'], 'commit')
        Draft202012Validator(self._store.reasoning_schema()).validate(payload)

        async def execute():
            outcome = self._store.commit_reasoning(payload, self._scope, key)
            return {'kind': 'reason', 'outcome': outcome}
        return self._leaf(position, 'reason', execute)

    def _observe(self, position, label, executed):
        """Every returned outcome enters the controller with this episode's measured credit."""
        outcome = executed['outcome']
        if not isinstance(outcome, Mapping) or not isinstance(outcome.get('status'), str):
            raise CycleError('a107_outcome_status_required:' + label)
        refs = [ref for ref in outcome.get('record_refs', ()) if isinstance(ref, str)]
        self._received.update(refs)
        if label == 'reason':
            self._known.update(ref for ref in refs if self._store.get(ref).get('record_type') == 'assessment')
        if outcome['status'] not in ('completed', 'partial'):
            self._feedback = outcome.get('feedback') or {'status': outcome['status'],
                                                         'category': outcome.get('error_code') or 'work_failed'}
        self._last_outcome = executed
        projected = self._credit()
        self._record_state(position)
        return CycleRecord({'credit': _finite(projected['credit'], 'credit'), 'kind': label,
                            'status': outcome['status'],
                            'retained_finding_count': projected['retained_finding_count'],
                            'estimation_context': self._timing(position)})

    def _child_unit(self, position, selection):
        slot = selection['slot']
        if slot not in self._builders:
            raise CycleError('a107_child_slot_not_declared:' + str(slot))
        objective = selection['objective']
        if type(objective) is not str or not objective.strip():
            raise CycleError('a107_child_objective_required:' + slot)
        scope = self._store.validate_scope(_json_text(selection['scope_json'], 'scope'), self._scope)
        builder = self._builders[slot]
        chosen = self._slots[slot]['assignment_fields']
        supplied = _json_text(selection['assignment_json'], 'assignment') if chosen else {}
        if not isinstance(supplied, Mapping) or set(supplied) - set(chosen):
            raise CycleError('a107_child_assignment_fields_must_be_the_slot_fields:' + slot)
        # Declared values are copied, the scope is this episode's narrowed scope and every other field
        # (including choice and subset fields) is this decision's choice; the runner admits the whole form.
        assignment = {**builder.assignment_form.declared, **supplied, 'scope': scope}
        goal = EpisodeGoal.child(self._bound.request.goal, objective=objective,
                                 result_contract=CHILD_REPORT_CONTRACT)
        request = EpisodeRequest(goal, CycleRecord({'objective': objective}),
                                 ReportContract(**CHILD_REPORT_CONTRACT))
        child = builder(slot + '_' + str(position), Commission(request, assignment))

        def receive(result, completion, _request):
            returned = builder.admit(result)
            finding = returned['finding']
            refs = finding.get('known_assessment_refs')
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise CycleError('a107_child_finding_requires_known_assessment_refs:' + slot)
            for ref in refs:
                if self._store.get(ref).get('record_type') != 'assessment':
                    raise CycleError('a107_child_finding_reference_is_not_an_assessment:' + slot)
            self._known.update(refs)
            self._received.update(refs)
            self._last_outcome = {'kind': 'child', 'slot': slot, 'ended_by': completion.ended_by,
                                  'child_credit': returned['credit'],
                                  'retained_finding_count': finding.get('retained_finding_count')}
            projected = self._credit()
            self._record_state(position)
            return CycleRecord({'credit': _finite(projected['credit'], 'credit'), 'kind': 'child', 'slot': slot,
                                'child_credit': _finite(returned['credit'], 'child_credit'),
                                'retained_finding_count': projected['retained_finding_count'],
                                'estimation_context': self._timing(position)})

        def report(result, _completion, _request):
            return {'finding': builder.admit(result)['finding']}
        return ChildEpisodeUnit(child, receive, report)


def head_result(store, scope, settings, opening, known):
    """The head's returned record: credit since opening (unbounded) and its finding projection."""
    projected = project(store, scope, settings, known)
    finding = {**projected, 'known_assessment_refs': sorted(known)}
    return CycleRecord({'credit': _finite(projected['credit'], 'credit') - opening, 'finding': finding})


def build_head_episode(binding, grain, bound, collaborators, child_builders):
    """The A107 head Episode: its own decision source, executed units and finding-progress result."""
    source = HeadCycleSource(binding, bound, collaborators, child_builders)

    def build_result(record):
        # The state recorded after the last completed unit (or the opening
        # baseline), whether the units ran now or replayed on resume.
        source._restore(record.units_consumed)
        return head_result(source._store, source._scope, source._settings,
                           opening_credit(bound, source._store, source._settings), source._known)
    return Episode(grain=grain, key=bound.key, source=source, request=bound.request, build_result=build_result)


__all__ = ['CHILD_REPORT_CONTRACT', 'CycleError', 'CycleRecord', 'HeadCycleSource', 'build_head_episode',
           'child_slot_options', 'decision_schema', 'head_result', 'head_settings', 'opening_credit',
           'opening_known', 'visible_assessment_refs']
