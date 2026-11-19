"""A104 head (``evolutionary_history_evidence``) decision source on the generic runner.

Each unit is chosen by the model:

- the source presents the episode's actual state (scope, working records, the
  A104 evolutionary-history credit and its target sheets, controller state,
  last outcome and feedback, the real tool catalog and the child options) with
  the A104 investigation instructions, and asks ``model_provider.complete``
  (role ``REASONING``) for one selection under the head's
  action schema (strict provider transport: ``action_transport``). The decision
  presents the A104 evidence-axis entry of the head's library and the thought
  pattern the commissioning parent chose (``assignment['thought_pattern']``),
  and offers only the tools the parent chose (``assignment['tools']``, C3/C6);
- the response is recorded with ``bound.recorder`` (``decision.<position>.<attempt>``),
  so a resumed run repeats the selections it made;
- a selection that fails admission (schema, empty reasoning commit) is rejected
  before acquisition: it creates no unit and the model decides again with that
  feedback;
- an admitted selection becomes one unit: a reasoning commit into the Store
  (``store.commit_reasoning``), a tool action on the head's own tool registry
  (built by the home factory over the run's shared store, C4) or a narrower
  ``evolutionary_history_evidence`` child commissioned through ``child_builders``
  with the head's own choices of thought pattern and tools and its typed report
  form (C5), or any other declared child (``hpc``, the job children launch,
  monitor and results, ``literature``) over a sub-scope, whose assignment the
  model fills from that child's own declared assignment form and whose typed
  report adds the record references it rests on (C5). Each executed outcome,
  including an invalid or failed one, is recorded as ``outcome.<position>`` and
  enters the iterator with the credit measured after it.

Credit is the head's own ``A104EvolutionaryCredit`` (``a104_credit``,
``head_credit_projector``) over the assignment's Store scope and the record
references this episode actually holds: the scope's subjects, those its own
reasoning and tool outcomes returned, and those its children returned in their
findings. The parent never adds a child's credit to its own. Each controller
input carries the episode's progress receipt (``bound.progress``). Nothing is
defaulted and the credit is never clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, Field, RecordForm, SubsetField
from method_loop import ChildEpisodeUnit, ClosedRecord, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.schema_support import _schema_nodes


from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.credit import A104EvolutionaryCredit
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.forms.evolutionary_history_evidence.evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import evidence_axis_instruction_view
from gene_annotation_episode.episodic_workflow.episode_support.instructions.evolutionary_history_evidence.runtime_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.evolutionary_history_evidence.action_transport import decode_response, generation_schema

ROLE = 'evolutionary_history_evidence'
AXIS = 'A104'

MODEL_ROLE = 'REASONING'
# Source readers bound to the records this episode actually received (ToolRegistry.execute_async).
_RECEIVED_SOURCE_READERS = frozenset({'source.locate', 'source.sequence.scan', 'source.sequence.references',
                                      'source.experimental.records'})
_EXECUTED = ('completed', 'partial')
_CHILD_PURPOSE = {
    ROLE: 'Commission a narrower A104 evolutionary-history investigation over a sub-scope of this scope; it '
          'returns its own credit and the record references its findings rest on.',
}
REPORT_CONTRACT = {
    'decision': 'Admit the A104 evolutionary-history findings into the commissioning episode',
    'measurements': {'credit': "This commission's A104 evolutionary-history credit on its own scale"},
    'information': {'finding': 'The A104 evolutionary-history findings of this commission and the records they rest on'},
}
# The typed report a parent head commissions from a recursive head child (C5): the head's own return
# fields unchanged, plus the record references the child's findings rest on as a typed list, so the
# parent admits them by form rather than by reading inside the finding.
CHILD_REPORT_CONTRACT = {
    **REPORT_CONTRACT,
    'information': {**REPORT_CONTRACT['information'],
                    'evidence_refs': 'The record references the findings of this commission rest on'},
}
CHILD_REPORT_FORM = RecordForm({
    'credit': Field('number', "The head's own unbounded evolutionary-history axis credit"),
    'finding': Field('record', 'The typed evolutionary-history findings report'),
    'evidence_refs': Field('list', 'The record references the findings of this commission rest on'),
})
EVIDENCE_REFS = 'evidence_refs'
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


def descendant_report(builder):
    """The typed report the head commissions from a non-head child (C5): the child's own return fields
    unchanged plus the record references its work rests on."""
    if EVIDENCE_REFS in builder.return_form.fields:
        raise ContractError('a104_child_return_form_already_declares:' + EVIDENCE_REFS + ':' + builder.slot)
    form = RecordForm({**builder.return_form.fields, EVIDENCE_REFS: CHILD_REPORT_FORM.fields[EVIDENCE_REFS]})
    measured = {name: spec.meaning for name, spec in builder.return_form.fields.items() if name == 'credit'}
    information = {name: spec.meaning for name, spec in form.fields.items() if name != 'credit'}
    contract = {'decision': 'Admit the ' + builder.slot + ' report into the commissioning A104 head',
                'measurements': measured, 'information': information}
    return contract, form


def head_credit_projector():
    """The head's own credit for a root-commissioned assignment (no ``a104_task``)."""
    return A104EvolutionaryCredit()


def evidence_axis_view(library):
    """The library's A104 evidence-axis entry, in its own instruction view."""
    entry = library.resolve(library.reference(AXIS))
    if entry.get('entry_version') == INSTRUCTION_VERSION:
        return instruction_view(entry)
    if entry.get('entry_version') == EVIDENCE_AXIS_VERSION:
        return evidence_axis_instruction_view(entry)
    raise ContractError('a104_evidence_axis_entry_invalid')


def thought_pattern_views(library):
    """The library's thought patterns by option id, with the fields presented with each decision."""
    return {header['option_ref']['option_id']: {
        name: value for name, value in library.resolve(header['option_ref']).items()
        if name in ('id', 'name', 'description', 'use_when', 'live_alternatives', 'decision_guidance',
                    'outcome_contingencies', 'boundary')}
        for header in library.headers() if header['option_ref']['slot'] == 'thought_pattern'}


def store_scope(store, scope):
    """The assignment scope as an A104 Store scope; any other record raises."""
    try:
        return store.validate_scope(scope)
    except ContractError as error:
        raise ContractError('a104_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error


def opening_record_refs(scope):
    """The records an A104 head holds when it opens: its scope's subjects (the old initial receipt)."""
    return list(dict.fromkeys(scope['subject_refs']))


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self, scope):
        self.applied = 0
        self.known_record_refs = opening_record_refs(scope)
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        self.known_record_refs.extend(ref for ref in outcome['record_refs'] if ref not in self.known_record_refs)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome.get('feedback') or {
            'status': outcome['status'], 'category': 'work_failed'}
        self.applied += 1


class EvolutionaryHistoryEvidenceSource:
    """The A104 head's model-selected units over ``bound`` and its collaborators."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a104_tool_registry_is_not_over_the_run_store')
        self._scope = store_scope(self._store, bound.assignment['scope'])
        self._projector = head_credit_projector()
        self._head_child = child_builders[ROLE]
        if self._head_child.return_form != binding.return_form:
            raise ContractError('a104_recursive_child_return_form_differs')
        # Every other declared child: its own form, its own typed report (C5).
        self._descendants = {slot: builder for slot, builder in child_builders.items() if slot != ROLE}
        self._descendant_reports = {slot: descendant_report(builder) for slot, builder in self._descendants.items()}
        self._thought_pattern = binding.thought_patterns[bound.assignment['thought_pattern']]
        self._state = _State(self._scope)

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        return self._projector(self._store, self._scope, known_record_refs=list(self._state.known_record_refs))

    def _controller_input(self, position, outcome):
        from .runtime_bindings import UnitInput  # runtime_bindings imports this module at load
        credit = self.credit_view()['credit']
        return UnitInput({'credit': credit, 'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def _tool_catalog(self):
        """Only the tools this commission's parent chose (``assignment['tools']``)."""
        selected = set(self._bound.assignment['tools'])
        catalog = self._tools.catalog(self._scope)
        missing = sorted(selected - set(catalog))
        if missing:
            raise ContractError('a104_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: item for name, item in catalog.items() if name in selected}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                            'role': {'type': 'string', 'const': ROLE},
                            'objective': {'type': 'string', 'minLength': 1,
                                          'description': 'The child episode objective.'},
                            'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                            'thought_pattern': {'enum': sorted(self._binding.thought_patterns)},
                            'tools': {'type': 'array', 'uniqueItems': True,
                                      'items': {'enum': list(self._binding.selectable_tools)}}}))
        for slot, builder in sorted(self._descendants.items()):
            properties = {'kind': {'type': 'string', 'const': 'episode_child'},
                          'role': {'type': 'string', 'const': slot},
                          'objective': {'type': 'string', 'minLength': 1,
                                        'description': 'The child episode objective.'},
                          'scope': {'type': 'object', 'description': 'A Store scope within this scope.'}}
            assignment = form_schema(builder.assignment_form, held=('scope',))
            if assignment['properties']:
                properties['assignment'] = assignment
            options.append(obj(properties))
        return obj({'selection': {'anyOf': options}})

    def child_options(self):
        """Each declared child slot with what commissioning it does."""
        from .runtime_bindings import ROLE_TEXT
        options = dict(_CHILD_PURPOSE)
        for slot, builder in self._descendants.items():
            goal, unit, result = ROLE_TEXT[slot]
            options[slot] = {'binding_path': builder.binding_path, 'improves': goal, 'unit': unit, 'returns': result,
                             'report_information': dict(self._descendant_reports[slot][0]['information'])}
        return options

    def decision_context(self, view, credit_view):
        catalog = self._tool_catalog()
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'evidence_task': self._bound.assignment['evidence_task'],
            'evidence_axis': self._binding.evidence_axis,
            'thought_pattern': self._thought_pattern,
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.known_record_refs),
            'current_credit': credit_view['credit'],
            'target_sheets': credit_view['target_sheets'],
            'source_contribution_count': credit_view['source_contribution_count'],
            'credit_binding': self._projector.as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(catalog.items())},
            'child_options': self.child_options(),
        }

    def instructions(self):
        return INSTRUCTIONS + '\n' + REASONING_COMMIT_REQUIREMENT

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
            raise ValueError('a104_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child' and selection['role'] != ROLE:
            # The child's own scope and assignment form checks, before acquisition (a failure is a rejection).
            self._descendant_assignment(selection)
        return selection

    def _descendant_assignment(self, selection):
        slot = selection['role']
        builder = self._descendants[slot]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        assignment = {'scope': scope, **dict(selection.get('assignment') or {}), **builder.assignment_form.declared}
        return builder.assignment_form.admit(assignment, 'a104_child_assignment:' + slot)

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
        refs = list(dict.fromkeys(result.get('record_refs') or []))
        outcome = {'kind': kind, 'status': result['status'], 'record_refs': refs, 'result': result}
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
            permitted = tuple(self._state.known_record_refs) if name in _RECEIVED_SOURCE_READERS else None
            result = await self._tools.execute_async(name, arguments, scope=self._scope,
                                                     operation_key=self._operation_key(position),
                                                     permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    def _child(self, position, selection):
        from .runtime_bindings import UnitInput  # runtime_bindings imports this module at load
        slot = selection['role']
        if slot == ROLE:
            builder = self._head_child
            scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
            assignment = {'scope': scope, 'thought_pattern': selection['thought_pattern'], 'tools': selection['tools'],
                          **builder.assignment_form.declared}
            contract, form = CHILD_REPORT_CONTRACT, CHILD_REPORT_FORM
        else:
            builder = self._descendants[slot]
            assignment = self._descendant_assignment(selection)
            scope = assignment['scope']
            contract, form = self._descendant_reports[slot]
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'], result_contract=contract)
        child = builder(slot + '_' + str(position),
                        Commission(EpisodeRequest(goal, UnitInput({'scope': scope}), ReportContract(**contract)),
                                   assignment, form))

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            refs = admitted[EVIDENCE_REFS]
            if any(type(ref) is not str for ref in refs):
                raise ContractError('a104_child_report_requires_record_references')
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': slot, 'record_refs': list(refs),
                'child_credit': admitted['credit'],
                **({} if slot == ROLE else {'child_report': {name: admitted[name] for name in admitted
                                                             if name not in ('credit', EVIDENCE_REFS)}}),
                'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in contract['information']}
        return ChildEpisodeUnit(child, receive, report)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The head's return: its A104 credit and the findings it holds."""
        from .runtime_bindings import UnitInput  # runtime_bindings imports this module at load
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a104_head_credit_must_be_finite')
        finding = {
            'scope': self._scope, 'known_record_refs': list(self._state.known_record_refs),
            'evidence_refs': list(self._state.known_record_refs),
            'thought_pattern': self._bound.assignment['thought_pattern'], 'tools': list(self._bound.assignment['tools']),
            'target_sheets': view['target_sheets'], 'source_contribution_count': view['source_contribution_count'],
            'credit_binding': self._projector.as_record(), 'interpretation': view['interpretation'],
            'ended_by': record.ended_by, 'units': record.units_consumed}
        returned = {'credit': credit, 'finding': finding}
        # A commissioned report form (C5) may add fields; the head supplies only those it holds.
        held = {'evidence_refs': list(self._state.known_record_refs)}
        for name in self._bound.report_form.fields:
            if name not in returned:
                if name not in held:
                    raise ContractError('a104_report_form_field_not_held:' + name)
                returned[name] = held[name]
        return UnitInput(returned)


__all__ = ['CHILD_REPORT_CONTRACT', 'CHILD_REPORT_FORM', 'EvolutionaryHistoryEvidenceSource', 'MODEL_ROLE', 'REPORT_CONTRACT',
           'evidence_axis_view', 'head_credit_projector', 'opening_record_refs', 'store_scope',
           'thought_pattern_views']
