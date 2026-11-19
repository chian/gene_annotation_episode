"""A101 head (``sequence_homology_evidence``) decision source on the generic runner.

This replaces the old-Workflow head task (``task.py``, ``task_decision.py``,
``task_state.py``, ``decision_inputs.py``, ``waiting.py``, ``report_delivery.py``
and the head's ``to_child_*``/``from_child_*``/``from_parent``/``to_parent``
modules). Each unit is chosen by the model:

- the source presents the episode's actual state (scope, working records, its
  native sequence-correspondence credit, controller state, last outcome and
  feedback, the commissioned tools and the child options with each child's own
  declared assignment form) with A101's investigation instructions, and asks
  ``model_provider.complete`` for one selection under A101's action schema
  (strict provider transport: ``action_transport``);
- the response is recorded with ``bound.recorder`` (``decision.<position>.<attempt>``),
  so a resumed run repeats the selections it made;
- a selection that fails admission (schema, empty reasoning commit, a child
  scope outside this scope, a child assignment its form refuses) is rejected
  before acquisition: it creates no unit and the model decides again with that
  feedback;
- an admitted selection becomes one unit: a reasoning commit into the Store
  (``store.commit_reasoning``), a tool action of the head's own registry
  (``tool_registry.execute_async``), or a child Episode commissioned through
  ``child_builders`` with the child's own assignment and the head's report form
  (C5). Each executed outcome, including an invalid or failed one, is recorded
  as ``outcome.<position>`` and enters the iterator with the credit measured
  after it.

The records an outcome returns are delivered to this episode's receipts
(``EpisodeReceipts``); the head's credit is A101's native sequence
correspondence over exactly those receipts (``runtime_credit``). A child's
admitted finding feeds the head's receipts; child credits are never summed into
the head's. Nothing is defaulted and no credit is bounded or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sequence_homology_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sequence_homology_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from .contract_binding import AXIS, REPORT, RETURN_FORM, Record
from .native_correspondence_credit import A101SequenceCredit
from .runtime_credit import head_credit_view, head_scope, head_store, open_head_receipts

MODEL_ROLE = 'REASONING'
# Readers bound to the records this episode actually received (as in the original dispatch).
RECEIVED_RECORD_READERS = frozenset({'source.locate', 'source.sequence.scan', 'source.sequence.references',
                                     'source.experimental.records', 'result.blast.hsp'})
EVIDENCE_RECORD_TYPES = frozenset({'observation', 'assessment'})
_EXECUTED = ('completed', 'partial')
GUIDANCE = (
    'A101 owns sequence-similarity evidence. Determine what the supplied target does within the assigned '
    'question, scope and constraints, starting from the supplied sequence and its known context. No initial '
    'candidate annotation or publicly searchable name is required: possible functions can emerge from the '
    'evidence and be compared or revised. Choose the search database for the scientific question (for an initial '
    'blastx search consider ClusteredNR, nr_clustered_seq) and preserve the selected database in the request. '
    'An execution handoff is operational progress, not homology evidence. Apply the supplied evidence-axis '
    'instructions and the commissioned thought pattern on every decision; they describe how to investigate and '
    'are not evidence about this target. Preserve the measured subject, conditions, native measurements, '
    'uncertainty and limits of inference. Missing information remains unknown.\n'
    'Choose one action: a tool among the commissioned tools, a reasoning commit of a scientific interpretation, '
    'or a child commission. A child commission names its slot, its objective, a Store scope within this scope and '
    'the assignment its own form declares; a sub-scope sequence_homology_evidence child also takes its thought '
    'pattern and tools from this head\'s options. Children own their iterative choices and return their credit '
    'and finding; their records become available to this episode. The configured controller owns continuation.'
)


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


_ELEMENT = {'text': {'type': 'string', 'minLength': 1}, 'number': {'type': 'number'},
            'integer': {'type': 'integer'}, 'boolean': {'type': 'boolean'}}
_REF = {'type': 'string', 'minLength': 1}
# The closed form ``Store.validate_scope`` admits (BINDING_CONTRACT.md, C1). Strict provider output carries
# closed objects only, so a child scope is declared field by field; the Store still admits each selected scope.
SCOPE_SCHEMA = {**obj({
    'subject_refs': {'type': 'array', 'minItems': 1, 'items': _REF,
                     'description': 'Subject references of this scope the child investigates.'},
    'segments': {'type': 'array', 'minItems': 1, 'description': 'Optional intervals; one or more per subject.',
                 'items': obj({'target_ref': _REF, 'start': {'type': 'integer', 'minimum': 0},
                               'end': {'type': 'integer', 'minimum': 0}, 'unit': _REF, 'member_ref': _REF},
                              required=['target_ref', 'start', 'end', 'unit'])},
    'read_selection_refs': {'type': 'array', 'minItems': 1, 'items': _REF,
                            'description': 'Optional read selections of library subjects in this scope.'},
}, required=['subject_refs']), 'description': 'A Store scope within this scope.'}


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
    """The JSON Schema of the fields of ``form`` its supplier chooses (declared and held fields excluded)."""
    fields = {name: spec for name, spec in form.fields.items()
              if not isinstance(spec, DeclaredField) and name not in held}
    return obj({name: field_schema(spec) for name, spec in fields.items()},
               required=[name for name, spec in fields.items() if spec.required])


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied = 0
        self.received_refs = []
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        self.received_refs.extend(ref for ref in outcome['record_refs'] if ref not in self.received_refs)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome['feedback']
        self.applied += 1


class SequenceHomologyEvidenceSource:
    """The A101 head's model-selected units over ``bound``, its collaborators and its own tool registry."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = head_store(binding, collaborators)
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        self._scope = head_scope(bound, self._store)
        self._receipts = open_head_receipts(bound, self._store)
        self._builders = child_builders
        if bound.report_form.as_record() != RETURN_FORM.as_record():
            # The head reports exactly its credit and finding; it has no source for a field a commissioner adds.
            raise ContractError('a101_head_report_form_must_be_its_return_form:' + bound.binding_path)
        for slot, builder in child_builders.items():
            if builder.return_form != RETURN_FORM:
                raise ContractError('a101_child_return_form_differs:' + slot)
        self._state = _State()

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        return head_credit_view(self._bound, self._store, self._receipts)

    def _receive(self, position, refs, kind):
        """Deliver an outcome's records to this episode's receipts (idempotent on resume)."""
        if refs:
            self._receipts.receive(self._bound.episode_id, list(refs), kind=kind, source_index=position)

    def _controller_input(self, position, outcome):
        return Record({'credit': self.credit_view()['credit'],
                       'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def tool_catalog(self):
        """Only the tools this commission selected (``assignment['tools']``)."""
        selected = set(self._bound.assignment['tools'])
        catalog = self._tools.catalog(self._scope)
        missing = sorted(selected - set(catalog))
        if missing:
            raise ContractError('a101_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: item for name, item in catalog.items() if name in selected}

    def child_schema(self, slot):
        builder = self._builders[slot]
        properties = {'kind': {'type': 'string', 'const': 'episode_child'}, 'slot': {'type': 'string', 'const': slot},
                      'objective': {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'},
                      'scope': SCOPE_SCHEMA}
        assignment = form_schema(builder.assignment_form, held=('scope',))
        if assignment['properties']:
            properties['assignment'] = assignment
        return obj(properties)

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self.tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        options.extend(self.child_schema(slot) for slot in sorted(self._builders))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view, credit_view):
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'evidence_task': self._bound.assignment['evidence_task'],
            'evidence_axis': self._binding.evidence_axis,
            'thought_pattern': self._binding.thought_patterns[self._bound.assignment['thought_pattern']],
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'current_credit': credit_view['credit'],
            'native_correspondence': {key: credit_view[key] for key in
                                      ('a101_sheet', 'interpretation', 'detail_pages')},
            'credit_binding': A101SequenceCredit().as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self.tool_catalog().items())},
            'child_options': {slot: {'binding_path': builder.binding_path,
                                     'assignment_form': builder.assignment_form.as_record()}
                              for slot, builder in sorted(self._builders.items())},
        }

    @staticmethod
    def instructions():
        return INSTRUCTIONS + '\n' + REASONING_COMMIT_REQUIREMENT + '\n' + GUIDANCE

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
        """Admit one model response as a selection; any failure is a rejection before acquisition."""
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a101_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child':
            self._commission(selection)
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

    @staticmethod
    def _outcome(kind, result):
        outcome = {'kind': kind, 'status': result['status'],
                   'record_refs': list(dict.fromkeys(result['record_refs'])), 'result': result}
        if result['status'] not in _EXECUTED:
            # A reasoning commit reports its error_code; a tool result carries its own feedback.
            outcome['feedback'] = ({'status': result['status'], 'category': result['error_code']}
                                   if kind == 'reason' else result['feedback'])
        return outcome

    def _reason(self, position, selection):
        outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._outcome(
            'reason', self._store.commit_reasoning(selection['commit'], self._scope, self._operation_key(position))))
        self._receive(position, outcome['record_refs'], 'own_action')
        self._state.apply(outcome)
        return outcome

    async def _tool(self, position, selection):
        name, arguments = selection['tool'], selection['arguments']

        async def execute():
            permitted = (tuple(self._receipts.known(self._bound.episode_id))
                         if name in RECEIVED_RECORD_READERS else None)
            result = await self._tools.execute_async(name, arguments, scope=self._scope,
                                                     operation_key=self._operation_key(position),
                                                     permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._receive(position, outcome['record_refs'], 'own_action')
        self._state.apply(outcome)
        return outcome

    def _commission(self, selection):
        """The child's Commission from an admitted selection; its own form check raises on a bad assignment."""
        slot = selection['slot']
        builder = self._builders[slot]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        # The child schema carries 'assignment' exactly when the slot's form has model-chosen fields.
        chosen = selection['assignment'] if 'assignment' in self.child_schema(slot)['properties'] else {}
        assignment = {'scope': scope, **dict(chosen), **builder.assignment_form.declared}
        builder.assignment_form.admit(assignment, 'a101_child_assignment:' + slot)
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                 result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, Record({'scope': scope}), ReportContract(**REPORT)), assignment,
                          builder.return_form)

    def _child(self, position, selection):
        slot = selection['slot']
        builder = self._builders[slot]
        commission = self._commission(selection)
        child = builder(slot + '_' + str(position), commission)
        form = commission.report_form
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            refs = admitted['finding'].get('known_record_refs')
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a101_child_finding_requires_known_record_refs:' + slot)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'slot': slot, 'record_refs': list(dict.fromkeys(refs)),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._receive(position, outcome['record_refs'], 'child_form')
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The head's return: its native-correspondence credit and the records it established."""
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a101_head_credit_must_be_finite')
        received = list(self._state.received_refs)
        return Record({'credit': credit, 'finding': {
            'evidence_axis': AXIS, 'scope': self._scope, 'known_record_refs': received,
            'evidence_refs': [ref for ref in received
                              if self._store.get(ref).get('record_type') in EVIDENCE_RECORD_TYPES],
            'native_correspondence': {key: view[key] for key in ('a101_sheet', 'interpretation', 'detail_pages')},
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['MODEL_ROLE', 'SCOPE_SCHEMA', 'SequenceHomologyEvidenceSource', 'field_schema', 'form_schema']
