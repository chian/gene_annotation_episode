"""A108 head (``sample_context_evidence``) decision source on the generic runner.

Each unit is chosen by the model:

- the source presents the episode's actual state (scope, working records,
  finding-progress credit, controller state, last outcome and feedback, the
  real tool catalog and the child options) with A108's own investigation
  instructions, and asks ``model_provider.complete`` for one selection under
  A108's action schema (strict provider transport: ``action_transport``);
- the response is recorded with ``bound.recorder`` (``decision.<position>.<attempt>``),
  so a resumed run repeats the selections it made;
- a selection that fails admission (schema, empty reasoning commit) is rejected
  before acquisition: it creates no unit and the model decides again with that
  feedback;
- an admitted selection becomes one unit: a reasoning commit into the Store
  (``store.commit_reasoning``), a tool action (``tool_registry.execute_async``),
  or a child Episode commissioned through ``child_builders`` (a narrower
  ``sample_context_evidence`` scope, or a ``literature`` assessment). Each
  executed outcome, including an invalid or failed one, enters the iterator
  with the credit measured after it.

Credit is the head's own finding progress
(``investigation_progress.ScientificFindingProgress``) with the commissioned
finding unit, over the assignment's Store scope and the assessment references
this episode actually holds: those its own reasoning and tool outcomes returned
and those its children returned in their findings. Each controller input
carries the episode's progress receipt (``bound.progress``) for the A108
forecast. Nothing is defaulted and no credit is bounded or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Commission
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.sample_context_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.sample_context_evidence.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.findings.sample_context_evidence.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.sample_context_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT

MODEL_ROLE = 'REASONING'
# Source readers bound to the records this episode actually received.
_RECEIVED_SOURCE_READERS = frozenset({'source.locate', 'source.sequence.scan', 'source.sequence.references'})
_EXECUTED = ('completed', 'partial')
_CHILD_PURPOSE = {
    'sample_context_evidence': 'Commission a narrower A108 sample-context investigation over a sub-scope of '
                               'this scope; it returns its credit and retained findings.',
    'literature': 'Commission an A108 published-evidence assessment of one proposed annotation; it returns its '
                  'credit and the findings it retained.',
}
_REFERENCE = {'type': 'string', 'minLength': 1}
# A child's scope in the closed form ``Store.validate_scope`` admits (BINDING_CONTRACT.md, C1). Strict
# provider output carries closed objects only, so the scope is declared field by field; the Store still
# admits each selected scope and checks that it lies within the commissioning scope.
SCOPE_SCHEMA = {**obj({
    'subject_refs': {'type': 'array', 'minItems': 1, 'items': _REFERENCE,
                     'description': 'Subject references of this scope the child investigates.'},
    'segments': {'type': 'array', 'minItems': 1,
                 'description': 'Optional original-coordinate intervals; one or more per subject.',
                 'items': obj({'target_ref': _REFERENCE, 'start': {'type': 'integer', 'minimum': 0},
                               'end': {'type': 'integer', 'minimum': 1}, 'unit': _REFERENCE,
                               'member_ref': _REFERENCE}, required=['target_ref', 'start', 'end', 'unit'])},
    'read_selection_refs': {'type': 'array', 'minItems': 1, 'items': _REFERENCE,
                            'description': 'Optional read selections of library subjects in this scope.'},
}, required=['subject_refs']), 'description': 'A Store scope within this scope.'}


@dataclass(frozen=True)
class Record:
    """A closed A108 record (controller input, child message or result)."""
    value: dict

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def head_credit_projector(evidence_task):
    """The head's finding-progress projector for its commissioned evidence task."""
    if (not isinstance(evidence_task, Mapping)
            or set(evidence_task) != {'version', 'kind', 'evidence_axis', 'credit_unit'}
            or evidence_task['version'] != 'evidence_axis_task_v1'
            or evidence_task['kind'] != 'whole_axis_findings' or evidence_task['evidence_axis'] != 'A108'):
        raise ContractError('original_axis_finding_task_required')
    return ScientificFindingProgress(FindingProgressPolicy(evidence_task['credit_unit']))


def store_scope(store, scope):
    """The assignment scope as an A108 Store scope; any other record raises."""
    try:
        return store.validate_scope(scope)
    except ContractError as error:
        raise ContractError('a108_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied = 0
        self.known_assessment_refs = []
        self.received_refs = []
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        for name, refs in (('known_assessment_refs', outcome['assessment_refs']),
                           ('received_refs', outcome['record_refs'])):
            current = getattr(self, name)
            current.extend(ref for ref in refs if ref not in current)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome.get('feedback') or {
            'status': outcome['status'], 'category': 'work_failed'}
        self.applied += 1


class SampleContextEvidenceSource:
    """The A108 head's model-selected units over ``bound``, its collaborators and its own tool registry."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a108_tool_registry_is_not_over_the_run_store')
        self._scope = store_scope(self._store, bound.assignment['scope'])
        self._projector = head_credit_projector(bound.assignment['evidence_task'])
        self._builders = child_builders
        for role, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a108_child_return_form_differs:' + role)
        self._literature_schema = (binding.literature_assignment_schema() if 'literature' in child_builders
                                   else None)
        self._state = _State()

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        return self._projector(self._store, self._scope,
                               known_assessment_refs=list(self._state.known_assessment_refs))

    def _assessments(self, refs):
        return [ref for ref in refs if self._store.get(ref).get('record_type') == 'assessment']

    def _controller_input(self, position, outcome):
        credit = self.credit_view()['credit']
        return Record({'credit': credit, 'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def _tool_catalog(self):
        """Only the tools this commission selected (``assignment['tools']``)."""
        selected = set(self._bound.assignment['tools'])
        catalog = self._tools.catalog(self._scope)
        missing = sorted(selected - set(catalog))
        if missing:
            raise ContractError('a108_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: item for name, item in catalog.items() if name in selected}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        objective = {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'}
        if 'sample_context_evidence' in self._builders:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': 'sample_context_evidence'},
                                'objective': objective,
                                'scope': SCOPE_SCHEMA,
                                'thought_pattern': {'enum': sorted(self._binding.thought_patterns)},
                                'tools': {'type': 'array', 'uniqueItems': True,
                                          'items': {'enum': list(self._binding.selectable_tools)}}}))
        if self._literature_schema is not None:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': 'literature'},
                                'objective': objective,
                                'scope': SCOPE_SCHEMA,
                                'assignment': self._literature_schema}))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view, credit_view):
        catalog = self._tool_catalog()
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'evidence_task': dict(self._bound.assignment['evidence_task']),
            'evidence_axis': self._binding.evidence_axis,
            'thought_pattern': self._binding.thought_patterns[self._bound.assignment['thought_pattern']],
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.received_refs),
            'known_assessment_refs': list(self._state.known_assessment_refs),
            'current_credit': credit_view['credit'],
            'investigation_progress': {key: credit_view[key] for key in
                                       ('retained_finding_count', 'inactive_dependencies', 'detail_pages')},
            'credit_binding': self._projector.as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(catalog.items())},
            'child_options': {role: _CHILD_PURPOSE[role] for role in self._builders},
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
            raise ValueError('a108_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child' and selection['role'] == 'literature':
            # The literature binding's own commission check, before acquisition (a failure is a rejection).
            literature = self._binding.literature_binding
            scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
            from .published_evidence_assessment.literature_credit import require_target_annotation
            admitted = literature.validate_assignment(self._store, selection['assignment'], scope)
            require_target_annotation(self._store, scope, admitted['proposed_annotation_ref'])
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
        refs = list(dict.fromkeys(result.get('record_refs') or []))
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

    def _child(self, position, selection):
        role = selection['role']
        builder = self._builders[role]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        if role == 'sample_context_evidence':
            assignment = {'scope': scope, 'thought_pattern': selection['thought_pattern'], 'tools': selection['tools'],
                          **builder.assignment_form.declared}
            goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                     result_contract=self._binding.report_contract)
            commission = Commission(EpisodeRequest(goal, Record({'scope': scope}),
                                                   ReportContract(**self._binding.report_contract)), assignment)
        else:
            # The literature commission carries the typed report its task requires (C5).
            assignment = {'scope': scope,
                          'received_record_refs': self._store.reference_subset(self._state.received_refs, scope),
                          'episode_assignment': selection['assignment']}
            commission = self._binding.literature_binding.commission(self._bound.request.goal,
                                                                     selection['objective'], assignment)
        child = builder(role + '_' + str(position), commission)
        form = commission.report_form
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            finding = admitted['finding']
            refs = finding['known_assessment_refs']
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a108_child_finding_requires_known_assessment_refs:' + role)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': role, 'record_refs': list(refs),
                'assessment_refs': self._assessments(refs), 'child_credit': admitted['credit'],
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
            raise ContractError('a108_head_credit_must_be_finite')
        return Record({'credit': credit, 'finding': {
            'scope': self._scope, 'known_assessment_refs': list(self._state.known_assessment_refs),
            'evidence_refs': list(self._state.known_assessment_refs),
            'retained_finding_count': view['retained_finding_count'],
            'source_contributions': view['source_contributions'],
            'inactive_dependencies': view['inactive_dependencies'], 'policy': view['policy'],
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['MODEL_ROLE', 'Record', 'SCOPE_SCHEMA', 'SampleContextEvidenceSource', 'head_credit_projector', 'store_scope']
