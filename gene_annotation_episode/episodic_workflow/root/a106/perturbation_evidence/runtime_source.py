"""A106 head (``perturbation_evidence``) decision source on the generic runner.

This is the head's decision behaviour on ``episode_runtime``. Each unit is
chosen by the model:

- the source presents the episode's actual state (scope, working records, the
  commissioned A106 process: evidence axis, thought pattern, selected tools and
  assignment, finding-progress credit, controller state, last outcome and
  feedback, and the child options) with the head's own A106 instructions, and
  asks ``model_provider.complete`` for one selection under the head's action
  schema (strict provider transport: ``a106.action_transport``);
- the response is recorded with ``bound.recorder`` (``decision.<position>.<attempt>``),
  so a resumed run repeats the selections it made;
- a selection that fails admission (schema, empty reasoning commit) is rejected
  before acquisition: it creates no unit and the model decides again with that
  feedback;
- an admitted selection becomes one unit: a reasoning commit into the Store
  (``store.commit_reasoning``), a selected tool action
  (``tool_registry.execute_async``), or a child commissioned through
  ``child_builders`` (a sub-scope ``perturbation_evidence`` head of the same
  proposed annotation, a ``literature`` assessment of it, or an operational
  ``launch``, ``monitor`` or ``results`` child over a sub-scope, whose
  assignment the model fills from that child's own declared assignment form and
  whose report the head commissions with the record references it acquired,
  contract C5). Each executed
  outcome, including an invalid or failed one, enters the iterator with the
  credit measured after it.

The head's commission (its ``assignment_form``, contracts C3 and C6) carries
what its commissioner decides, as in the original A106 commission: the A106
process (one library thought pattern, ``ChoiceField``, and a subset of the
head's tools, ``SubsetField``), the proposed annotation the commission
evaluates, and the commissioner's evidence references and constraints. The
head offers only the selected tools, executed by its own tool registry over the
run's shared store (C4).

Credit is the head's own A106 finding progress (``credit.original_task_projector``)
restricted to assessments of the commissioned proposed annotation, over the
assignment's Store scope and the assessment references this episode actually
holds: its initial references (the parent's evidence references and the
proposed annotation), those its own reasoning and tool outcomes returned and
those its children returned in their findings. Each controller input carries
the episode's progress receipt (``bound.progress``). Nothing is defaulted and no
credit is bounded or rescaled.

The head offers only its own registry's tools, each executed directly by that
registry; an evidence-axis entry without published instructions raises when
reached.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField
from method_loop import ChildEpisodeUnit, ClosedRecord, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.perturbation_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import FOOTPRINT, ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.perturbation_evidence.literature_investigation_prompt import REASONING_COMMIT_REQUIREMENT
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.construction_records import selection_fields, selector_selection
from .credit import original_task_projector
from .scientific_contracts import EVIDENCE_AXIS_VERSION, INSTRUCTION_VERSION, _REFERENCE

MODEL_ROLE = 'REASONING'
HEAD_SLOT = 'perturbation_evidence'
LITERATURE_SLOT = 'literature'
# The commission operands a head's commissioner decides for it (contracts C3 and C6).
PARENT_OPERANDS = ('proposed_annotation_ref', 'evidence_refs', 'constraints', 'thought_pattern', 'tools')
# Operational children: the model fills each one's own declared assignment form over a sub-scope.
OPERATIONAL_SLOTS = ('launch', 'monitor', 'results')
# The child slots whose commission this source fills (every slot the head declares); a builder for any other
# slot raises when the source is built.
COMMISSIONED_CHILD_SLOTS = (HEAD_SLOT, LITERATURE_SLOT, *OPERATIONAL_SLOTS)
# The field the head adds to an operational child's report (C5): the Store records it acquired.
ACQUIRED_RECORDS = 'record_refs'
ACQUIRED_RECORDS_FIELD = Field('list', 'The Store record references this commission acquired within its scope; '
                                       'the commissioning A106 head receives exactly these')
# Tools bound to the records this episode actually received (as in the original dispatch): the source readers
# and the SRA file acquisition, whose advertisement File must be a received record.
_RECEIVED_SOURCE_READERS = frozenset({'source.locate', 'source.sequence.scan', 'source.sequence.references',
                                      'public.ncbi.sra.file'})
_EXECUTED = ('completed', 'partial')
_THOUGHT_FIELDS = ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                   'outcome_contingencies', 'boundary')
_CHILD_PURPOSE = {
    HEAD_SLOT: 'Commission a narrower A106 perturbation-evidence investigation of the same proposed annotation over '
               'a sub-scope of this scope, with its own selected A106 process, evidence references and '
               'constraints; it returns its credit and the retained findings it holds.',
    LITERATURE_SLOT: 'Commission an A106 published-evidence assessment of the commissioned proposed annotation for '
                     'one literature task; it returns its credit and the findings it retained.',
    'launch': 'Commission the launch of analysis work over a sub-scope of this scope; it returns its credit, its '
              'finding and the Store records it acquired (retained handoffs and native records).',
    'monitor': "Commission an assessment of the progress of this episode's pending work over a sub-scope of this "
               'scope; it returns its credit, its finding (the newly informative progress) and the Store records '
               'it acquired.',
    'results': 'Commission the acquisition of the results of launched work over a sub-scope of this scope; it '
               'returns its credit, its finding and the Store records it acquired.',
}
_ELEMENT = {'text': {'type': 'string', 'minLength': 1}, 'number': {'type': 'number'},
            'integer': {'type': 'integer'}, 'boolean': {'type': 'boolean'}}
# A child's scope, in the closed form ``store.validate_scope`` admits (which then checks it lies within this scope).
SUB_SCOPE = {**obj({'subject_refs': {'type': 'array', 'items': _REFERENCE, 'minItems': 1, 'uniqueItems': True},
                    'read_selection_refs': {'type': 'array', 'items': _REFERENCE, 'minItems': 1, 'uniqueItems': True},
                    'segments': {**FOOTPRINT, 'minItems': 1}}, required=['subject_refs']),
             'description': 'A Store scope within this scope: its subjects, and optionally the frozen read '
                            'selections or the segments that narrow them.'}


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
class Record(ClosedRecord):
    """A closed A106 record (controller input, child message or result)."""
    value: dict

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def store_scope(store, scope):
    """The assignment scope as an A106 Store scope; any other record raises."""
    try:
        return store.validate_scope(scope)
    except ContractError as error:
        raise ContractError('a106_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error


def initial_references(store, scope, assignment):
    """What the head holds when it opens: the commissioner's evidence references and the proposed annotation."""
    proposed = assignment['proposed_annotation_ref']
    store._require(proposed, {'hypothesis'})
    evidence = assignment['evidence_refs']
    if any(type(ref) is not str for ref in evidence):
        raise ContractError('a106_head_evidence_refs_must_be_record_refs')
    initial = list(dict.fromkeys([*evidence, proposed]))
    if store.reference_subset(initial, scope) != initial:
        raise ContractError('a106_head_initial_references_outside_scope')
    return initial


def head_credit(store, scope, evidence_task, proposed_annotation_ref, known_assessment_refs):
    """The head's finding progress over its held assessments of the commissioned proposed annotation."""
    projector = original_task_projector({'context': {'evidence_task': dict(evidence_task)}})
    return projector(store, scope, known_assessment_refs=list(known_assessment_refs),
                     assignment={'scope': scope, 'proposed_annotation_ref': proposed_annotation_ref})


def operational_commission(store, parent_scope, parent_goal, report_contract, builder, selection):
    """An operational child's Commission: its sub-scope, the model-filled fields of its own declared
    assignment form, and its commissioner's report form adding the records it acquired (C5)."""
    slot = selection['role']
    scope = store.validate_scope(selection['scope'], parent_scope=parent_scope)
    assignment = {'scope': scope, **dict(selection.get('assignment') or {}), **builder.assignment_form.declared}
    builder.assignment_form.admit(assignment, 'a106_operational_assignment:' + slot)
    if ACQUIRED_RECORDS in builder.return_form.fields:
        raise ContractError('a106_operational_return_form_already_declares:' + ACQUIRED_RECORDS + ':' + slot)
    form = RecordForm({**builder.return_form.fields, ACQUIRED_RECORDS: ACQUIRED_RECORDS_FIELD})
    report_contract = {**dict(report_contract),
                       'information': {**dict(report_contract['information']),
                                       ACQUIRED_RECORDS: ACQUIRED_RECORDS_FIELD.meaning}}
    goal = EpisodeGoal.child(parent_goal, objective=selection['objective'], result_contract=report_contract)
    return Commission(EpisodeRequest(goal, Record({'assignment': assignment}), ReportContract(**report_contract)),
                      assignment, form)


def acquired_records(store, scope, slot, admitted):
    """The Store records an operational child's admitted report delivers; each must be in ``scope``."""
    refs = admitted[ACQUIRED_RECORDS]
    if any(type(ref) is not str for ref in refs):
        raise ContractError('a106_operational_record_refs_must_be_record_refs:' + slot)
    if store.reference_subset(list(refs), scope) != list(refs):
        raise ContractError('a106_operational_record_refs_outside_scope:' + slot)
    return list(dict.fromkeys(refs))


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self, received_refs, known_assessment_refs):
        self.applied = 0
        self.known_assessment_refs = list(known_assessment_refs)
        self.received_refs = list(received_refs)
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        for name, refs in (('known_assessment_refs', outcome['assessment_refs']),
                           ('received_refs', outcome['record_refs'])):
            current = getattr(self, name)
            current.extend(ref for ref in refs if ref not in current)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome['feedback']
        self.applied += 1


class PerturbationEvidenceSource:
    """The A106 head's model-selected units over ``bound`` and its collaborators."""

    def __init__(self, binding, bound, collaborators, child_builders):
        undeclared = sorted(set(child_builders) - set(COMMISSIONED_CHILD_SLOTS))
        if undeclared:
            raise ContractError('a106_head_child_slot_not_commissioned_by_head:' + ','.join(undeclared))
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a106_head_tool_registry_must_be_over_the_run_store')
        self._scope = store_scope(self._store, bound.assignment['scope'])
        self._operands = {name: deepcopy(bound.assignment[name]) for name in PARENT_OPERANDS}
        self._projector = original_task_projector({'context': {'evidence_task': dict(bound.assignment['evidence_task'])}})
        self._builders = child_builders
        for slot, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a106_child_return_form_differs:' + slot)
        self._selection = binding.commissioned_selection(self._operands['thought_pattern'], self._operands['tools'],
                                                         self._tools.catalog(self._scope))
        initial = initial_references(self._store, self._scope, self._operands)
        self._state = _State(initial, self._assessments(initial))

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        """Finding progress over the held assessments of the commissioned proposed annotation."""
        return head_credit(self._store, self._scope, self._bound.assignment['evidence_task'],
                           self._operands['proposed_annotation_ref'], self._state.known_assessment_refs)

    def _assessments(self, refs):
        return [ref for ref in refs if self._store.get(ref).get('record_type') == 'assessment']

    def _controller_input(self, position, outcome):
        credit = self.credit_view()['credit']
        return Record({'credit': credit, 'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def _selected_tools(self):
        """The parent-selected tools, resolved by the head's tool library against its own registry's catalog.

        Each resolved row is that registry's own catalog entry, which the registry executes directly.
        """
        resolved = self._binding.tool_library.resolve_invocations(self._selection['child_tool_info'],
                                                                  self._tools.catalog(self._scope))
        return {row['name']: row for row in resolved}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._selected_tools().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        objective = {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'}
        if HEAD_SLOT in self._builders:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': HEAD_SLOT}, 'objective': objective,
                                'scope': SUB_SCOPE,
                                **self._sub_scope_operands()}))
        if LITERATURE_SLOT in self._builders:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': LITERATURE_SLOT}, 'objective': objective,
                                'assignment': self._binding.literature_binding.assignment_schema()}))
        for slot in OPERATIONAL_SLOTS:
            if slot in self._builders:
                properties = {'kind': {'type': 'string', 'const': 'episode_child'},
                              'role': {'type': 'string', 'const': slot}, 'objective': objective,
                              'scope': SUB_SCOPE}
                assignment = form_schema(self._builders[slot].assignment_form, held=('scope',))
                if assignment['properties']:
                    properties['assignment'] = assignment
                options.append(obj(properties))
        return obj({'selection': {'anyOf': options}})

    def _sub_scope_operands(self):
        """The operands this head decides for a sub-scope head, from that child's own declared assignment form.

        The child evaluates this head's proposed annotation (inherited, as in
        the original preparation); the model chooses its A106 process among the
        options the child offers, its evidence references and its constraints.
        """
        fields = self._builders[HEAD_SLOT].assignment_form.fields
        missing = [name for name in PARENT_OPERANDS if name not in fields]
        if missing:
            raise ContractError('a106_head_child_commission_lacks_parent_operands:' + ','.join(missing))
        thought, tools = fields['thought_pattern'], fields['tools']
        return {'thought_pattern': {'enum': list(thought.options), 'description': thought.meaning},
                'tools': {'type': 'array', 'items': {'enum': list(tools.options)}, 'uniqueItems': True,
                          'description': tools.meaning},
                'evidence_refs': {'type': 'array', 'items': _REFERENCE, 'uniqueItems': True,
                                  'description': 'Records this head holds that the child receives as evidence.'},
                'constraints': {'type': 'object', 'description': 'The constraints of the child investigation.'}}

    def process_view(self):
        """The commissioned A106 process, as the original head presented it with each decision."""
        library = self._binding.library
        axis, thought = (library.resolve(self._selection[key]) for key in selection_fields(self._selection)[:2])
        if axis.get('entry_version') == INSTRUCTION_VERSION:
            axis_view = self._binding.evidence_axis
        elif axis.get('entry_version') == EVIDENCE_AXIS_VERSION:
            raise ContractError('a106_head_evidence_axis_entry_without_published_instructions: the head presents '
                                'only a published instruction entry of its evidence axis')
        else:
            raise ContractError('scientific_support_entry_invalid')
        return {'selection': selector_selection(self._selection), 'evidence_axis': axis_view,
                'thought_pattern': {name: deepcopy(thought[name]) for name in _THOUGHT_FIELDS if name in thought},
                'child_tool_info': deepcopy(self._selection['child_tool_info']),
                'assignment': {**deepcopy(self._operands), 'selection': selector_selection(self._selection),
                               'evidence_task': dict(self._bound.assignment['evidence_task'])},
                'permitted_children': list(self._builders)}

    def decision_context(self, view, credit_view):
        tools = self._selected_tools()
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'perturbation_evidence': self.process_view(),
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'known_assessment_refs': list(self._state.known_assessment_refs),
            'current_credit': credit_view['credit'],
            'investigation_progress': {key: credit_view[key] for key in
                                       ('retained_finding_count', 'inactive_dependencies', 'detail_pages')},
            'credit_binding': self._projector.as_record(),
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(tools.items())},
            'child_options': {slot: _CHILD_PURPOSE[slot] for slot in self._builders},
        }

    def instructions(self):
        return self._binding.instructions()

    # -- decisions ----------------------------------------------------------------
    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            schema = self.action_schema()
            context = self.decision_context(view, self.credit_view())
            instructions = self.instructions()
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, instructions, context,
                                                generation_schema(schema)))
            try:
                selection = self.admit(response, schema)
            except (ValueError, KeyError, TypeError, ValidationError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': schema_failure_diagnostic(error)
                                        if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return self.unit(position, selection)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a106_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child' and selection['role'] == HEAD_SLOT:
            self._store.validate_scope(selection['scope'], parent_scope=self._scope)
            unknown = [ref for ref in selection['evidence_refs'] if ref not in self._state.received_refs]
            if unknown:
                raise ValueError('a106_child_evidence_not_held_by_parent:' + ','.join(unknown))
        if selection['kind'] == 'episode_child' and selection['role'] == LITERATURE_SLOT:
            # The literature binding's own commission check, before acquisition (a failure is a rejection).
            admitted = self._binding.literature_binding.validate_assignment(self._store, selection['assignment'],
                                                                            self._scope)
            if admitted['proposed_annotation_ref'] != self._operands['proposed_annotation_ref']:
                raise ValueError('a106_literature_child_must_evaluate_the_commissioned_proposed_annotation')
        if selection['kind'] == 'episode_child' and selection['role'] in OPERATIONAL_SLOTS:
            # The child's own assignment form check, before acquisition (a failure is a rejection).
            self._operational_commission(selection)
        return selection

    def unit(self, position, selection):
        kind = selection['kind']
        if kind == 'reason':
            return Leaf(selection, lambda chosen: self._reason(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'reason:' + str(position))
        if kind == 'tool':
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'tool:' + str(position))
        return self._child(position, selection)

    # -- execution ------------------------------------------------------------------
    def _operation_key(self, position):
        return self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

    def _outcome(self, kind, result):
        refs = list(dict.fromkeys(result['record_refs']))
        outcome = {'kind': kind, 'status': result['status'], 'record_refs': refs,
                   'assessment_refs': self._assessments(refs), 'result': result}
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
            permitted = tuple(self._state.received_refs) if name in _RECEIVED_SOURCE_READERS else None
            result = await self._tools.execute_async(name, arguments, scope=self._scope,
                                                     operation_key=self._operation_key(position),
                                                     permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    def _operational_commission(self, selection):
        return operational_commission(self._store, self._scope, self._bound.request.goal,
                                      self._binding.report_contract, self._builders[selection['role']], selection)

    def _child_refs(self, slot, admitted):
        """The record references a child's admitted report delivers to this head."""
        if slot in OPERATIONAL_SLOTS:
            return acquired_records(self._store, self._scope, slot, admitted)
        refs =admitted['finding'].get('known_assessment_refs')
        if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
            raise ContractError('a106_child_finding_requires_known_assessment_refs:' + slot)
        return list(refs)

    def _child(self, position, selection):
        slot = selection['role']
        builder = self._builders[slot]
        proposed = self._operands['proposed_annotation_ref']
        if slot in OPERATIONAL_SLOTS:
            commission = self._operational_commission(selection)
        elif slot == HEAD_SLOT:
            assignment = {'scope': self._store.validate_scope(selection['scope'], parent_scope=self._scope),
                          **builder.assignment_form.declared, 'proposed_annotation_ref': proposed,
                          'evidence_refs': list(selection['evidence_refs']), 'constraints': selection['constraints'],
                          'thought_pattern': selection['thought_pattern'], 'tools': list(selection['tools'])}
            report_contract = dict(self._binding.report_contract)
            goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                     result_contract=report_contract)
            commission = Commission(EpisodeRequest(goal, Record({'assignment': assignment}),
                                                   ReportContract(**report_contract)), assignment)
        else:
            # The literature child evaluates the head's own commissioned proposed annotation and carries the typed
            # report its task requires (C5).
            assignment = {'scope': self._scope,
                          'received_record_refs': self._store.reference_subset(self._state.received_refs, self._scope),
                          'episode_assignment': selection['assignment']}
            commission = self._binding.literature_binding.commission(self._bound.request.goal,
                                                                     selection['objective'], assignment)
        form = commission.report_form
        information = tuple(commission.request.report_contract.information)
        child = builder(slot + '_' + str(position), commission)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            refs = self._child_refs(slot, admitted)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': slot, 'record_refs': list(refs),
                'assessment_refs': self._assessments(refs), 'child_credit': admitted['credit'],
                **({'child_finding': admitted['finding']} if slot in OPERATIONAL_SLOTS else {}),
                'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The head's return: its finding-progress credit and the retained findings it holds."""
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a106_head_credit_must_be_finite')
        return Record({'credit': credit, 'finding': {
            'scope': self._scope, 'proposed_annotation_ref': self._operands['proposed_annotation_ref'],
            'known_assessment_refs': list(self._state.known_assessment_refs),
            'evidence_refs': list(self._state.known_assessment_refs),
            'retained_finding_count': view['retained_finding_count'],
            'source_contributions': view['source_contributions'],
            'inactive_dependencies': view['inactive_dependencies'], 'policy': view['policy'],
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['ACQUIRED_RECORDS', 'COMMISSIONED_CHILD_SLOTS', 'MODEL_ROLE', 'OPERATIONAL_SLOTS', 'PARENT_OPERANDS',
           'PerturbationEvidenceSource', 'Record', 'acquired_records', 'form_schema', 'head_credit', 'initial_references',
           'operational_commission', 'store_scope']
