"""A105 head (``experimental_activity_evidence``) decision source on the generic runner.

Each unit is chosen by the model:

- the source presents the episode's actual state (scope, held proposed
  annotation, evidence task, the A105 evidence-axis instructions, the thought
  pattern its commissioner chose, working records, finding-progress credit,
  controller state, last outcome and feedback, the tools its commissioner
  selected from the head's own registry, and its child options) and asks
  ``model_provider.complete`` for one selection under the head's action schema
  (strict provider transport: ``..action_transport``);
- the response is recorded with ``bound.recorder`` (``decision.<position>.<attempt>``)
  so a resumed run repeats the selections it made;
- a selection that fails admission (schema, empty reasoning commit, a child
  commission its child's own declarations reject) is rejected before
  acquisition: it creates no unit and the model decides again with that
  feedback;
- an admitted selection becomes one unit: a reasoning commit into the shared
  Store, a tool action through the head's own registry, a narrower A105 head
  (with the thought pattern and tools this head chooses for it), or a
  ``literature`` published-evidence assessment commissioned with the typed
  report its task requires (C5). Each executed outcome, including an invalid
  or failed one, is recorded as ``outcome.<position>`` and enters the iterator
  with the credit measured after it.

Knowledge is the head's ``EpisodeReceipts`` in the Store: its subject, what an
A105 parent head had received when this head was commissioned, the records its
own outcomes return and the findings its children return. Credit is the head's
finding progress over those receipts (``credit.py``); each controller input
carries ``bound.progress.receipt(position)`` for the A105 real-time yield
estimator. Nothing is defaulted and no credit is bounded or rescaled.
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

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT

MODEL_ROLE = 'REASONING'
HEAD_ROLE = 'experimental_activity_evidence'
_EXECUTED = ('completed', 'partial')
# The head passes the records this episode received to the source locator only.
_RECEIVED_SOURCE_READERS = frozenset({'source.locate'})
_CHILD_PURPOSE = {
    HEAD_ROLE: 'Commission a narrower A105 experimental-activity investigation over a sub-scope of this scope; '
               'it returns its credit and the findings it retained.',
    'literature': 'Commission an A105 published-evidence assessment of one proposed annotation; it grades each '
                  'applicable experiment with its purpose-specific subscoring sheet and returns its credit, '
                  'retained findings and the typed answer its task requires.',
}
# The report this head asks of a commissioned A105 head (its return form: credit + finding).
CHILD_REPORT_CONTRACT = {
    'decision': 'Which experimental-activity evidence to investigate next within this A105 investigation',
    'measurements': {'credit': "The child's A105 credit on its own unbounded scale"},
    'information': {'finding': 'The findings the child retained: its known assessment references and their '
                               'finding-progress projection'},
}
HEAD_INSTRUCTIONS = (
    "Determine what the supplied target does from actual experiments and their results, published or in "
    "experiment databases. Start with the supplied sequence, selected file contents or snippets, preserving their "
    "boundaries, completeness and known context. No initial candidate annotation or publicly searchable name is "
    "required. Possible functions can emerge from the evidence and be compared or revised. Apply the A105 "
    "evidence-axis investigation instructions on every decision; the thought pattern chosen for this commission "
    "describes a way to reason and when it applies. Use actual outcomes and received child results to choose "
    "and revise your approach. Library instructions describe how to investigate; they are not evidence about "
    "this target. Preserve the measured subject, conditions, controls, native measurements, uncertainty and "
    "limits of inference when interpreting evidence. Missing information remains unknown.\n\n"
    "Choose an available tool action, commit a scientific interpretation through the reasoning action, or "
    "commission a narrower A105 investigation of a sub-scope or a published-evidence assessment of one "
    "proposed annotation. Use only the supplied actual tools and their "
    "declared input contracts. Recorded facts come from actual records. Keep inherited information distinct "
    "from new findings and completed work distinct from attempts. Children own their iterative choices. The "
    "configured controller owns continuation. Unchanged observations do not manufacture progress.")


@dataclass(frozen=True)
class Record:
    """A closed A105 record (controller input, child message or result)."""
    value: dict

    def as_record(self):
        return json.loads(json.dumps(self.value, sort_keys=True, allow_nan=False))


def store_scope(store, scope):
    """The assignment scope as an A105 Store scope; any other record raises."""
    try:
        return store.validate_scope(scope)
    except ContractError as error:
        raise ContractError('a105_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


class _State:
    """What this episode last saw, rebuilt on resume from its recorded outcomes."""

    def __init__(self):
        self.applied = 0
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome['feedback']
        self.applied += 1


class ExperimentalActivityEvidenceSource:
    """The A105 head's model-selected units over ``bound``, its collaborators and its own tool registry."""

    def __init__(self, binding, bound, collaborators, child_builders):
        from .runtime_binding import require_tool_registry
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = require_tool_registry(binding.tool_registry, self._store, binding.binding_path)
        self._scope = store_scope(self._store, bound.assignment['scope'])
        self._proposed = bound.assignment.get('proposed_annotation_ref')
        self._projector = binding.credit_projector(bound.assignment)
        self._receipts = binding.open_receipts(self._store, bound)
        self._builders = child_builders
        for role, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a105_child_return_form_differs:' + role)
        self._literature = binding.literature_binding if 'literature' in child_builders else None
        self._state = _State()

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            index = self._state.applied
            self._apply(index, self._bound.recorder.recall('outcome.' + str(index)))

    def _apply(self, position, outcome):
        """Receive an outcome's records into this episode's receipts (idempotent) and remember it."""
        kind = 'child_form' if outcome['kind'] == 'child' else 'own_action'
        self._receipts.receive(self._bound.episode_id, outcome['record_refs'], kind=kind, source_index=position)
        self._state.apply(outcome)

    def credit_view(self):
        return self._binding.known_finding_credit(self._store, self._bound)

    def _known_refs(self):
        return list(self._receipts.known(self._bound.episode_id))

    def _controller_input(self, position, outcome):
        return Record({'credit': self.credit_view()['credit'], 'estimation_action_index': position,
                       'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                       'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    # -- presentation -------------------------------------------------------------
    def _tool_catalog(self):
        """Only the tools this commission selected (``assignment['tools']``)."""
        selected = set(self._bound.assignment['tools'])
        catalog = self._tools.catalog(self._scope)
        missing = sorted(selected - set(catalog))
        if missing:
            raise ContractError('a105_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: item for name, item in catalog.items() if name in selected}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        objective = {'type': 'string', 'minLength': 1, 'description': 'The child episode objective.'}
        if HEAD_ROLE in self._builders:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': HEAD_ROLE},
                                'objective': objective,
                                'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                                'thought_pattern': {'enum': sorted(self._binding.thought_patterns)},
                                'tools': {'type': 'array', 'uniqueItems': True,
                                          'items': {'enum': list(self._binding.selectable_tools)}}}))
        if self._literature is not None:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': 'literature'},
                                'objective': objective,
                                'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                                'assignment': self._literature.assignment_schema()}))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view, credit_view):
        catalog = self._tool_catalog()
        state = view.controller_state
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'proposed_annotation_ref': self._proposed,
            'evidence_task': dict(self._bound.assignment['evidence_task']),
            'evidence_axis': self._binding.evidence_axis,
            'thought_pattern': self._binding.thought_patterns[self._bound.assignment['thought_pattern']],
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': self._known_refs(),
            'current_credit': credit_view['credit'],
            'investigation_progress': {key: credit_view[key] for key in
                                       ('retained_finding_count', 'inactive_dependencies', 'detail_pages')},
            'credit_binding': self._projector.as_record(),
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(catalog.items())},
            'child_options': {role: _CHILD_PURPOSE[role] for role in self._builders},
        }

    def instructions(self):
        return INSTRUCTIONS + '\n' + HEAD_INSTRUCTIONS + '\n' + REASONING_COMMIT_REQUIREMENT

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
                commission = self.prepare(selection)
            except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': schema_failure_diagnostic(error)
                                        if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return self.unit(position, selection, commission)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a105_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        return selection

    def prepare(self, selection):
        """A child selection's commission, checked by the child's own declarations before acquisition."""
        if selection['kind'] != 'episode_child':
            return None
        role = selection['role']
        builder = self._builders[role]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        if role == HEAD_ROLE:
            assignment = {'scope': scope, 'thought_pattern': selection['thought_pattern'], 'tools': selection['tools'],
                          **({'proposed_annotation_ref': self._proposed} if self._proposed is not None else {}),
                          **builder.assignment_form.declared}
            goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                     result_contract=CHILD_REPORT_CONTRACT)
            return Commission(EpisodeRequest(goal, Record({'scope': scope, 'objective': selection['objective']}),
                                             ReportContract(**CHILD_REPORT_CONTRACT)), assignment)
        from .published_evidence_assessment.literature_credit import require_target_annotation
        admitted = self._literature.validate_assignment(self._store, selection['assignment'], scope)
        if self._proposed is not None and admitted['proposed_annotation_ref'] != self._proposed:
            raise ContractError('literature_child_proposed_annotation_differs_from_parent')
        require_target_annotation(self._store, scope, admitted['proposed_annotation_ref'])
        # The literature commission carries the typed report its task requires (C5).
        assignment = {'scope': scope,
                      'received_record_refs': self._store.reference_subset(self._known_refs(), scope),
                      'episode_assignment': selection['assignment']}
        return self._literature.commission(self._bound.request.goal, selection['objective'], assignment)

    def unit(self, position, selection, commission):
        kind = selection['kind']
        if kind == 'reason':
            return Leaf(selection, lambda chosen: self._reason(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'reason:' + str(position))
        if kind == 'tool':
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'tool:' + str(position))
        return self._child(position, selection['role'], commission)

    # -- execution ------------------------------------------------------------------
    def _operation_key(self, position):
        return self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

    def _outcome(self, kind, result):
        """A tool result carries its ``feedback``; a reasoning commit result carries its ``error_code``."""
        outcome = {'kind': kind, 'status': result['status'],
                   'record_refs': list(dict.fromkeys(result['record_refs'])), 'result': result}
        if result['status'] not in _EXECUTED:
            outcome['feedback'] = (result['feedback'] if kind == 'tool'
                                   else {'status': result['status'], 'category': result['error_code']})
        return outcome

    def _reason(self, position, selection):
        commit = selection['commit']
        owner = {'account_owner': (self._bound.run_id, self._bound.episode_id)} \
            if commit.get('interpretation_accounts') else {}
        outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._outcome(
            'reason', self._store.commit_reasoning(commit, self._scope, self._operation_key(position), **owner)))
        self._apply(position, outcome)
        return outcome

    async def _tool(self, position, selection):
        name, arguments = selection['tool'], selection['arguments']

        async def execute():
            permitted = tuple(self._known_refs()) if name in _RECEIVED_SOURCE_READERS else None
            result = await self._tools.execute_async(name, arguments, scope=self._scope,
                                                     operation_key=self._operation_key(position),
                                                     permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._apply(position, outcome)
        return outcome

    def _child(self, position, role, commission):
        builder = self._builders[role]
        child = builder(role + '_' + str(position), commission)
        form = commission.report_form
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            refs = admitted['finding'].get('known_assessment_refs')
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a105_child_finding_requires_known_assessment_refs:' + role)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': role, 'record_refs': list(refs),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._apply(position, outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report)

    # -- result ---------------------------------------------------------------------
    def result(self, record, opening_credit):
        """The head's return: this commission's credit gain and the retained findings it holds.

        ``credit`` is the closing finding-progress credit minus the credit the
        controller opened with (inherited knowledge is not this commission's
        gain), on A105's own unbounded scale.
        """
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        closing = view['credit']
        if isinstance(closing, bool) or not isinstance(closing, (int, float)) or not math.isfinite(closing):
            raise ContractError('a105_head_credit_must_be_finite')
        known = list(self._receipts.known(self._bound.episode_id, record_type='assessment'))
        return Record({'credit': closing - opening_credit, 'finding': {
            'scope': self._scope, 'known_assessment_refs': known, 'evidence_refs': known,
            'opening_credit': opening_credit, 'closing_credit': closing,
            'retained_finding_count': view['retained_finding_count'],
            'source_contributions': view['source_contributions'],
            'inactive_dependencies': view['inactive_dependencies'], 'policy': view['policy'],
            'ended_by': record.ended_by, 'units': record.units_consumed}})


__all__ = ['CHILD_REPORT_CONTRACT', 'ExperimentalActivityEvidenceSource', 'HEAD_INSTRUCTIONS', 'MODEL_ROLE',
           'Record', 'store_scope']
