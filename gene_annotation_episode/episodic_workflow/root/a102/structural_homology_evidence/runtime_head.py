"""The A102 head (``structural_homology_evidence``) on the generic runner.

Each unit is chosen by the model:

- the source presents the Episode's actual state (scope, commissioned A102 task,
  proposed annotation, selected thought pattern, working records, the head's own
  credit and controller state, last outcome and feedback, the selected tools and
  the declared child options) with A102's own investigation instructions, and
  asks ``model_provider.complete`` for one selection under the head's action
  schema; the response is recorded with ``bound.recorder``
  (``decision.<position>.<attempt>``), so a resumed run repeats it;
- a selection that fails admission is rejected before acquisition: it creates no
  unit and the model decides again with that feedback;
- an admitted selection is one unit: a reasoning commit into the Store, a tool
  action of the head's own ``ToolRegistry`` (only the commission's selected tools),
  or a child Episode commissioned through ``child_builders``. Each executed
  outcome, including an invalid or failed one, is recorded (``outcome.<position>``)
  and enters the iterator with the credit measured after it.

Credit is the head's own projector for the commissioned ``a102_task``
(``task_projector.original_task_projector``): native structural correspondence or
its task-specific forms (record receipts) or received scientific finding progress
(assessment receipts), over the Store scope, the proposed annotation and the
references this Episode actually received (the proposed annotation its commission
delivers, its own outcomes and its children's
admitted findings). The continuation is the head's own yield controller declared
for ``A102:<task>``; its credit definition must be the projector's. Nothing is
defaulted, and no credit is bounded, clamped or rescaled here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import TASKS, is_merged_entry, task_context
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.instructions.structural_homology_evidence.runtime_prompt import REASONING_COMMIT_REQUIREMENT
from gene_annotation_episode.episodic_workflow.episode_support.configuration.structural_homology_evidence.process_options import evidence_axis_instruction_view
from .runtime_continuation import A102Continuation, episode_epoch, unit_input
from .scientific_guidance import scientific_guidance
from .task_projector import original_task_projector

AXIS = 'A102'
MODEL_ROLE = 'REASONING'
_EXECUTED = ('completed', 'partial')
# Source readers bound to the records this Episode actually received (as in the original dispatch).
_RECEIVED_READERS = frozenset({'source.locate', 'result.blast.hsp'})
_ELEMENT = {'text': {'type': 'string', 'minLength': 1}, 'number': {'type': 'number'},
            'integer': {'type': 'integer'}, 'boolean': {'type': 'boolean'}}


def field_schema(spec):
    """The JSON Schema of one model-filled field of a child's declared assignment form."""
    if isinstance(spec, ChoiceField):
        return {'enum': list(spec.options), 'description': spec.meaning}
    if isinstance(spec, SubsetField):
        return {'type': 'array', 'uniqueItems': True, 'items': {'enum': list(spec.options)},
                'description': spec.meaning}
    if spec.type == 'record':
        schema = form_schema(spec.form) if spec.form is not None else {'type': 'object'}
    elif spec.type == 'list':
        schema = {'type': 'array', 'items': form_schema(spec.items) if spec.items is not None else {}}
    else:
        schema = dict(_ELEMENT[spec.type])
    return {**schema, 'description': spec.meaning}


def form_schema(form, *, held=()):
    """The JSON Schema of the fields of ``form`` its commissioner chooses (declared and held fields excluded)."""
    fields = {name: spec for name, spec in form.fields.items()
              if not isinstance(spec, DeclaredField) and name not in held}
    return obj({name: field_schema(spec) for name, spec in fields.items()},
               required=[name for name, spec in fields.items() if spec.required])


@dataclass(frozen=True)
class Record:
    """A closed A102 record (child request message or head result)."""
    value: dict

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def evidence_axis_entry(library):
    """The head library's own published evidence-axis entry (``A102``); the library may publish other axes too."""
    try:
        reference = library.reference(AXIS)
    except ValueError as error:
        raise ContractError('a102_head_library_requires_its_evidence_axis_entry') from error
    if reference['slot'] != 'evidence_axis':
        raise ContractError('a102_head_library_requires_its_evidence_axis_entry')
    entry = library.resolve(reference)
    if entry.get('entry_version') not in (INSTRUCTION_VERSION, EVIDENCE_AXIS_VERSION):
        raise ContractError('scientific_task_credit_not_declared')
    return entry


def thought_patterns(library):
    """The library's thought-pattern options, by option id."""
    return {header['option_ref']['option_id']: header['option_ref'] for header in library.headers()
            if header['option_ref']['slot'] == 'thought_pattern'}


def task_projector(library, task):
    """The head's credit projector for the commissioned A102 task."""
    if task not in TASKS:
        raise ContractError('a102_unknown_structural_evidence_task')
    return original_task_projector(task, merged_a102=is_merged_entry(evidence_axis_entry(library)))


def head_credit(projector, store, scope, proposed_annotation_ref, received_refs):
    """The head's credit over the references it received, on the projector's own scale."""
    assignment = {'scope': scope, 'proposed_annotation_ref': proposed_annotation_ref}
    refs = list(dict.fromkeys(received_refs))
    if projector.requires_known_record_refs:
        view = projector(store, scope, known_record_refs=refs, assignment=assignment)
    else:
        assessments = [ref for ref in refs if store.get(ref).get('record_type') == 'assessment']
        view = projector(store, scope, known_assessment_refs=assessments, assignment=assignment)
    credit = view['credit']
    if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
        raise ContractError('a102_head_credit_must_be_finite')
    return credit, view


def commission_refs(assignment):
    """The references the commission itself delivers to the Episode: the proposed annotation it evaluates."""
    return (assignment['proposed_annotation_ref'],)


def head_controller(binding, bound, store):
    """The head's own yield controller for ``A102:<task>``, opened at its credit before any unit."""
    from yield_control import (AccumulationYieldController, BoundedQualityYieldController, CompletionYieldController,
                               YieldParameters)
    task = bound.assignment['a102_task']
    key = AXIS + ':' + task
    if key not in binding.yield_bindings:
        raise ContractError('scientific_yield_binding_missing_for_task:' + key)
    declaration = binding.yield_bindings[key]
    projector = task_projector(binding.library, task)
    if canonical(projector.as_record()) != canonical(declaration['credit_definition']):
        raise ContractError('scientific_yield_credit_definition_mismatch:' + key)
    if projector.yield_method != declaration['kind']:
        raise ContractError('scientific_yield_method_credit_mismatch:' + key)
    scope = store.validate_scope(bound.assignment['scope'])
    initial, _ = head_credit(projector, store, scope, bound.assignment['proposed_annotation_ref'],
                             commission_refs(bound.assignment))
    parameters = YieldParameters(**declaration['parameters'])
    epoch = episode_epoch(bound)
    if declaration['kind'] == 'accumulation':
        controller = AccumulationYieldController(epoch, initial, declaration['cutoff'], parameters)
    elif declaration['kind'] == 'bounded_quality':
        controller = BoundedQualityYieldController(epoch, initial, declaration['cutoff'], projector.native_score_maximum,
                                                   parameters)
    elif declaration['kind'] == 'completion':
        controller = CompletionYieldController(epoch, initial, declaration['cutoff'],
                                               projector.as_record()['maximum_credit'], parameters)
    else:
        raise ContractError('scientific_yield_method_unavailable:' + key)
    return A102Continuation(controller)


class _State:
    """What this Episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self, commission_refs):
        self.applied = 0
        self.received_refs = list(commission_refs)
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        self.received_refs.extend(ref for ref in outcome['record_refs'] if ref not in self.received_refs)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome['feedback']
        self.applied += 1


class StructuralHomologyEvidenceSource:
    """The A102 head's model-selected units over ``bound``, its collaborators and its own tool registry."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a102_tool_registry_is_not_over_the_run_store')
        try:
            self._scope = self._store.validate_scope(bound.assignment['scope'])
        except ContractError as error:
            raise ContractError('a102_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error
        self._task = bound.assignment['a102_task']
        self._proposed = bound.assignment['proposed_annotation_ref']
        self._projector = task_projector(binding.library, self._task)
        self._builders = child_builders
        for slot, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a102_child_return_form_differs:' + slot)
        self._state = _State(commission_refs(bound.assignment))

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        return head_credit(self._projector, self._store, self._scope, self._proposed, self._state.received_refs)

    def _controller_input(self, position):
        credit, _ = self.credit_view()
        return unit_input(self._bound, position, credit, self._state.received_refs)

    # -- presentation -------------------------------------------------------------
    def _tool_catalog(self):
        """Only the tools this commission selected (``assignment['tools']``)."""
        selected = set(self._bound.assignment['tools'])
        catalog = self._tools.catalog(self._scope)
        missing = sorted(selected - set(catalog))
        if missing:
            raise ContractError('a102_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: item for name, item in catalog.items() if name in selected}

    def _child_options(self):
        return {slot: self._binding.child_purpose(path) for slot, path in sorted(self._binding.child_slots.items())
                if slot in self._builders}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': item['input_schema']}))
        objective = {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'}
        scope = {'type': 'object', 'description': 'A Store scope within this scope.'}
        for slot in self._child_options():
            fields = {'kind': {'type': 'string', 'const': 'episode_child'}, 'slot': {'type': 'string', 'const': slot},
                      'objective': objective, 'scope': scope}
            if slot == self._binding.binding_path:
                fields.update({'a102_task': {'enum': list(TASKS)},
                               'thought_pattern': {'enum': sorted(self._binding.thought_patterns)},
                               'tools': {'type': 'array', 'uniqueItems': True,
                                         'items': {'enum': list(self._binding.selectable_tools)}}})
            else:
                # Any other child: the model fills the child's own declared assignment form (scope is held).
                assignment = form_schema(self._builders[slot].assignment_form, held=('scope',))
                if assignment['properties']:
                    fields['assignment'] = assignment
            options.append(obj(fields))
        return obj({'selection': {'anyOf': options}})

    def instructions(self):
        entry = evidence_axis_entry(self._binding.library)
        view = (instruction_view(entry)['investigation_instructions'] if entry['entry_version'] == INSTRUCTION_VERSION
                else evidence_axis_instruction_view(entry))
        return scientific_guidance(entry) + view + '\n' + REASONING_COMMIT_REQUIREMENT

    def decision_context(self, view):
        credit, credit_view = self.credit_view()
        state = view.controller_state
        pattern = self._binding.thought_patterns[self._bound.assignment['thought_pattern']]
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'evidence_axis': AXIS,
            'a102_task': task_context(self._task),
            'proposed_annotation_ref': self._proposed,
            'thought_pattern': self._binding.library.resolve(pattern),
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'current_credit': credit,
            'credit_binding': self._projector.as_record(),
            'credit_details': {key: value for key, value in credit_view.items() if key != 'credit'},
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self._tool_catalog().items())},
            'child_options': self._child_options(),
        }

    # -- decisions ----------------------------------------------------------------
    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            schema = self.action_schema()
            context = json.loads(json.dumps(self.decision_context(view), sort_keys=True, allow_nan=False))
            instructions = self.instructions()
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, instructions, context, schema))
            try:
                selection = self.admit(response, schema)
            except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': getattr(error, 'message', None) or str(error)}
                attempt += 1
                continue
            return self.unit(position, selection)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a102_decision_response_must_be_exactly_selection')
        selection = json.loads(json.dumps(response['selection'], allow_nan=False))
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child':
            # The child's own scope and assignment form checks, before acquisition (a failure is a rejection).
            self._child_assignment(selection)
        return selection

    def _child_assignment(self, selection):
        """The child's assignment from an admitted selection, admitted against the child's own form."""
        slot = selection['slot']
        builder = self._builders[slot]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        if slot == self._binding.binding_path:
            assignment = {'scope': scope, 'a102_task': selection['a102_task'],
                          'proposed_annotation_ref': self._proposed,
                          'thought_pattern': selection['thought_pattern'], 'tools': selection['tools'],
                          **builder.assignment_form.declared}
        else:
            assignment = {'scope': scope, **dict(selection.get('assignment') or {}),
                          **builder.assignment_form.declared}
        return builder.assignment_form.admit(assignment, 'a102_child_assignment:' + slot)

    def unit(self, position, selection):
        kind = selection['kind']
        if kind == 'reason':
            return Leaf(selection, lambda chosen: self._reason(position, chosen),
                        lambda chosen, outcome: self._controller_input(position), 'reason:' + str(position))
        if kind == 'tool':
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position), 'tool:' + str(position))
        return self._child(position, selection)

    # -- execution ------------------------------------------------------------------
    def _operation_key(self, position):
        return self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

    def _outcome(self, kind, result):
        outcome = {'kind': kind, 'status': result['status'],
                   'record_refs': list(dict.fromkeys(result.get('record_refs') or [])), 'result': result}
        if result['status'] not in _EXECUTED:
            outcome['feedback'] = result.get('feedback') or {'status': result['status'],
                                                             'category': result.get('error_code') or 'work_failed'}
        return outcome

    def _reason(self, position, selection):
        outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._outcome(
            'reason', self._store.commit_reasoning(selection['commit'], self._scope, self._operation_key(position))))
        self._state.apply(outcome)
        return outcome

    async def _tool(self, position, selection):
        name, arguments = selection['tool'], selection['arguments']

        async def execute():
            permitted = (tuple(self._state.received_refs)
                         if name in _RECEIVED_READERS or name.startswith('structure.') else None)
            result = await self._tools.execute_async(name, arguments, scope=self._scope,
                                                     operation_key=self._operation_key(position),
                                                     permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    def _child(self, position, selection):
        slot = selection['slot']
        builder = self._builders[slot]
        assignment = self._child_assignment(selection)
        scope = assignment['scope']
        report = self._binding.report_contract
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'], result_contract=dict(report))
        # The child's report is admitted against its own return form plus the head's report contract (C5).
        commission = Commission(EpisodeRequest(goal, Record({'scope': scope}), ReportContract(**report)), assignment,
                                self._binding.return_form)
        child = builder(slot + '_' + str(position), commission)

        def receive(result, completion, request):
            admitted = builder.admit(result, commission.report_form)
            refs = admitted['finding'].get('record_refs')
            if not isinstance(refs, list) or any(type(ref) is not str or not ref for ref in refs):
                raise ContractError('a102_child_finding_requires_record_refs:' + slot)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'slot': slot, 'record_refs': list(dict.fromkeys(refs)),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position)

        def report_fields(result, completion, request):
            admitted = builder.admit(result, commission.report_form)
            return {name: admitted[name] for name in commission.request.report_contract.information}
        return ChildEpisodeUnit(child, receive, report_fields)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The head's return: its own credit and the structural findings it received."""
        self._catch_up(record.units_consumed)
        credit, view = self.credit_view()
        refs = list(self._state.received_refs)
        assessments = [ref for ref in refs if self._store.get(ref).get('record_type') == 'assessment']
        return Record({'credit': credit, 'finding': {
            'scope': self._scope, 'a102_task': self._task, 'proposed_annotation_ref': self._proposed,
            'record_refs': refs, 'evidence_refs': assessments, 'credit_binding': self._projector.as_record(),
            'credit_details': {key: value for key, value in view.items() if key != 'credit'},
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['AXIS', 'MODEL_ROLE', 'Record', 'StructuralHomologyEvidenceSource', 'evidence_axis_entry', 'head_controller',
           'head_credit', 'task_projector', 'thought_patterns']
