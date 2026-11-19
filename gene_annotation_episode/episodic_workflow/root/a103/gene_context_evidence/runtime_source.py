"""A103 head (``gene_context_evidence``) decision source on the generic runner.

Each unit is chosen by the model (``model_provider.complete``) from the episode's
actual state: its scope, working records, measured-context credit and its
per-target sheets, the controller state, the last outcome and feedback, the
selected thought pattern, the commission's selected A103 tools and the child
options. The action schema reaches the provider in its strict structured-output
form and the response is decoded back before the original schema validates it
(``episode_support/model_exchange/gene_context_evidence/action_transport.py``).
The response is recorded (``decision.<position>.<attempt>``), so a
resumed run repeats it. A response that fails admission creates no unit and no
observation; the model decides again with that feedback.

An admitted selection is one unit:

- ``reason``: a reasoning commit into the shared Store (``store.commit_reasoning``);
- ``tool``: one of the commission's selected tools, executed by the head's own
  ``A103ToolRegistry`` inside its current-invocation binding (``A103Invocation``:
  this episode's identity, scope and the records it holds);
- ``episode_child``: a narrower ``gene_context_evidence`` commission over a
  sub-scope, with its own thought pattern and tool subset.

Every executed outcome, including an invalid or failed one, is recorded
(``outcome.<position>``) and enters the iterator with the credit measured after
it and the episode's progress receipt. Received measurements are attributed by
the registry's own receipt callback (``received_attributions``) before credit is
read. Credit is ``A103ContextCredit`` over the scope and the records this episode
holds; it is never bounded, clamped or rescaled here. A child's admitted
``finding`` hands its ``evidence_refs`` to this episode; the parent never sums
child credits into its own.

A tool reads a supplied genomic file only through the action's received-file
reader (``a103/received_inputs.ReceivedFiles``). A parent's commissioned report
form (C5) may add any of the head's finding fields (``HEAD_REPORT_FIELDS``) at
the top level of its result; any other added field raises when the Episode is
built.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.schema_support import _schema_nodes

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.gene_context_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.gene_context_evidence.literature_investigation_prompt import INSTRUCTIONS, REASONING_COMMIT_REQUIREMENT
from gene_annotation_episode.episodic_workflow.episode_support.readers.gene_context_evidence.received_inputs import ReceivedFiles
from .contract_binding import ContractRecord

MODEL_ROLE = 'REASONING'
_EXECUTED = ('completed', 'partial')
_SOURCE_READERS = frozenset({'source.locate', 'source.sequence.scan', 'source.sequence.references'})

GUIDANCE = (
    'A103 owns gene-context work. Scientific descendants remain A103. Context measurements are graded when '
    'they are published or received. Each target/locus, neighbouring component, domain and regulatory footprint '
    'retains its own attribution. An identity score, source label or fetched record alone is not an association '
    'score. Unknown flanks and unevaluated detections are not absence. Preserve optional modules, paralogs and '
    'related sampling. Use one small local job at a time. Credit comes from actual measured context, not '
    'narrative judgments.\n\n'
    "Determine what the supplied target does within the parent's assigned question, scope and constraints. "
    'Start with the supplied sequence, selected file contents or snippets, preserving their boundaries, '
    'completeness and known context. No initial candidate annotation or publicly searchable name is required. '
    'Apply the selected investigation instructions and thought-pattern guidance on every decision. Use actual '
    'outcomes and received child results to choose and revise your approach. Selected instructions describe how '
    'to investigate; they are not evidence about this target. Preserve the measured subject, conditions, '
    'controls, native measurements, uncertainty and limits of inference. Missing information remains unknown.\n'
    'Choose a selected tool action, commit a scientific interpretation through the reasoning action, or '
    'commission a narrower gene-context child with its own thought pattern and tool selection. Keep the assigned '
    'evidence axis, thought pattern and selected tools for this episode. Children own their iterative choices. '
    'The configured controller owns continuation.\n')
_CHILD_PURPOSE = {
    'gene_context_evidence': 'Commission a narrower A103 gene-context investigation over a sub-scope of this '
                             'scope, with its own thought pattern and tool subset; it returns its credit and the '
                             'records it established.',
    'execution_job_submission': 'Commission the launch of selected execution work over a sub-scope of this scope; '
                                'it returns its credit and its finding with the records it established.',
    'execution_progress_assessment': "Commission an assessment of the progress of this episode's pending work over "
                                     'a sub-scope of this scope; it returns its credit and its finding.',
    'execution_result_acquisition': 'Commission the acquisition of the results of launched work over a sub-scope '
                                    'of this scope; it returns its credit and its finding with the records it '
                                    'established.',
    'hpc_work_planning': 'Commission the planning and execution of HPC work over a sub-scope of this scope; it '
                         'returns its credit and its finding with the records it established.',
    'resource_work_submission': 'Commission the submission of resource work over a sub-scope of this scope; it '
                                'returns its credit and its finding with the records it established.',
    'resource_result_acquisition': 'Commission the acquisition of resource work results over a sub-scope of this '
                                   'scope; it returns its credit and its finding with the records it established.',
    'published_evidence_assessment': 'Commission an assessment of published gene-context evidence over a sub-scope '
                                     'of this scope; it returns its credit and its finding with the records it '
                                     'established.',
}
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
class A103Invocation:
    """This episode's identity as the host of one tool action (``ToolRegistry.current_invocation``)."""
    run_id: str
    episode_id: str
    path: tuple
    role: str
    scope: dict
    received_record_refs: tuple

    def as_record(self):
        return {'run_id': self.run_id, 'episode_id': self.episode_id, 'path': [list(part) for part in self.path],
                'role': self.role, 'scope': self.scope, 'received_record_refs': list(self.received_record_refs)}


# The fields of the head's finding (``GeneContextEvidenceSource.result``) a commissioned report form may add.
HEAD_REPORT_FIELDS = ('scope', 'evidence_refs', 'target_sheets', 'a103_sheet', 'source_contribution_count',
                      'credit_binding', 'ended_by', 'units')


def commissioned_report_fields(return_form, report_form, binding_path):
    """The fields a parent's commissioned report form (C5) adds to the head's return form.

    Each added field is one of the head's finding fields (``HEAD_REPORT_FIELDS``), returned at the top level
    of its result; a field the finding does not hold raises when the Episode is built.
    """
    added = tuple(name for name in report_form.fields if name not in return_form.fields)
    missing = [name for name in added if name not in HEAD_REPORT_FIELDS]
    if missing:
        raise ContractError('a103_head_commissioned_report_field_not_held:' + binding_path + ':' + ','.join(missing))
    return added


def head_scope(store, scope):
    """The assignment scope, which must be a scope the run's Store admits."""
    try:
        return store.validate_scope(scope)
    except ContractError as error:
        raise ContractError('a103_head_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error


def initial_known(assignment):
    """The records the commission hands this episode: the parent's evidence and its proposed annotation."""
    refs = list(assignment.get('evidence_refs', ()))
    if any(type(ref) is not str or not ref for ref in refs):
        raise ContractError('a103_head_evidence_refs_must_be_record_refs')
    if 'proposed_annotation_ref' in assignment and assignment['proposed_annotation_ref'] not in refs:
        refs.append(assignment['proposed_annotation_ref'])
    return refs


def _embedded(schema):
    """A tool input schema embedded in the action schema keeps its own $ref resolution."""
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + digest}
    return schema


class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self, known):
        self.applied = 0
        self.known = list(known)
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        self.known.extend(ref for ref in outcome['record_refs'] if ref not in self.known)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome.get('feedback') or {
            'status': outcome['status'], 'category': 'work_failed'}
        self.applied += 1


class GeneContextEvidenceSource:
    """The A103 head's model-selected units over ``bound``, its collaborators and its own tool registry."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = binding.tool_registry
        if self._tools.store is not self._store:
            raise ContractError('a103_tool_registry_is_not_over_the_run_store')
        self._scope = head_scope(self._store, bound.assignment['scope'])
        self._builders = child_builders
        for role, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a103_child_return_form_differs:' + role)
        # A commissioned report form (C5) may add any of the head's finding fields at the top level.
        self._report_fields = commissioned_report_fields(binding.return_form, bound.report_form,
                                                         binding.binding_path)
        assignment = bound.assignment
        self._annotation = ({'scope': self._scope, 'proposed_annotation_ref': assignment['proposed_annotation_ref']}
                            if 'proposed_annotation_ref' in assignment else None)
        self._thought = binding.thought_patterns[assignment['thought_pattern']]
        self._selected_tools = tuple(assignment['tools'])
        self._state = _State(initial_known(assignment))

    # -- state ------------------------------------------------------------------
    def _catch_up(self, position):
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def credit_view(self):
        return self._binding.credit_projector(self._store, self._scope, known_record_refs=list(self._state.known),
                                              assignment=self._annotation)

    def _controller_input(self, position, outcome):
        credit = self.credit_view()['credit']
        return ContractRecord({'credit': credit,
                               'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                               'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    def _invocation(self, known=None):
        return A103Invocation(self._bound.run_id, self._bound.episode_id, tuple(self._bound.path),
                              self._binding.binding_path, self._scope,
                              tuple(self._state.known if known is None else known))

    # -- presentation -------------------------------------------------------------
    def _tool_catalog(self):
        catalog = self._tools.catalog(self._scope)
        missing = sorted(set(self._selected_tools) - set(catalog))
        if missing:
            raise ContractError('a103_selected_tools_not_in_registry:' + ','.join(missing))
        return {name: catalog[name] for name in self._selected_tools}

    def action_schema(self):
        options = [{**obj({'kind': {'type': 'string', 'const': 'reason'}, 'commit': self._store.reasoning_schema()}),
                    'description': REASONING_COMMIT_REQUIREMENT}]
        for name, item in sorted(self._tool_catalog().items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        if 'gene_context_evidence' in self._builders:
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': 'gene_context_evidence'},
                                'objective': {'type': 'string', 'minLength': 1},
                                'scope': SCOPE_SCHEMA,
                                'thought_pattern': {'enum': sorted(self._binding.thought_patterns)},
                                'tools': {'type': 'array', 'uniqueItems': True,
                                          'items': {'enum': list(self._binding.selectable_tools)}}}))
        for role, builder in sorted(self._builders.items()):
            if role == 'gene_context_evidence':
                continue
            # Any other child: the model fills that child's own declared assignment form (scope is held).
            properties = {'kind': {'type': 'string', 'const': 'episode_child'},
                          'role': {'type': 'string', 'const': role}, 'objective': {'type': 'string', 'minLength': 1},
                          'scope': SCOPE_SCHEMA}
            assignment = form_schema(builder.assignment_form, held=('scope',))
            if assignment['properties']:
                properties['assignment'] = assignment
            options.append(obj(properties))
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view, credit_view):
        state = view.controller_state
        assignment = self._bound.assignment
        return {
            'goal': self._bound.request.goal.as_record(),
            'scope': self._scope,
            'evidence_task': dict(assignment['evidence_task']),
            'evidence_axis': self._binding.evidence_axis,
            'thought_pattern': self._thought,
            'proposed_annotation_ref': assignment.get('proposed_annotation_ref'),
            'constraints': assignment.get('constraints'),
            'working_state': self._store.reasoning_view(self._scope),
            'visible_record_refs': list(self._state.known),
            'current_credit': credit_view['credit'],
            'target_sheets': credit_view['target_sheets'],
            'source_contribution_count': credit_view['source_contribution_count'],
            'credit_binding': self._binding.credit_projector.as_record(),
            'controller': state.as_record() if hasattr(state, 'as_record') else None,
            'units_consumed': view.units_consumed,
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(self._tool_catalog().items())},
            'child_options': {role: _CHILD_PURPOSE[role] for role in self._builders},
        }

    def instructions(self):
        return GUIDANCE + INSTRUCTIONS + '\n' + REASONING_COMMIT_REQUIREMENT

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
                                        'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return self.unit(position, selection)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a103_decision_response_must_be_exactly_selection')
        # Undo the provider's strict-output representation; the original schema then validates the selection.
        selection = decode_response(json.loads(json.dumps(dict(response), allow_nan=False)), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason' and all(rows == [] for rows in selection['commit'].values()):
            raise ValueError('empty_reasoning_commit')
        if selection['kind'] == 'episode_child':
            # The child's own scope and assignment form checks, before acquisition (a failure is a rejection).
            self._child_assignment(selection)
        return selection

    def _child_assignment(self, selection):
        """The child's assignment from an admitted selection, admitted against the child's own form."""
        role = selection['role']
        builder = self._builders[role]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        if role == 'gene_context_evidence':
            assignment = {'scope': scope, 'thought_pattern': selection['thought_pattern'],
                          'tools': selection['tools'],
                          'evidence_refs': self._store.reference_subset(self._state.known, scope),
                          **builder.assignment_form.declared}
            for name in ('proposed_annotation_ref', 'constraints'):
                if name in self._bound.assignment:
                    assignment[name] = self._bound.assignment[name]
        else:
            assignment = {'scope': scope, **dict(selection.get('assignment') or {}),
                          **builder.assignment_form.declared}
        return builder.assignment_form.admit(assignment, 'a103_child_assignment:' + role)

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

    def _received(self, refs):
        """Attribute received measurements (the registry's receipt callback); its generated records are held too."""
        known = list(dict.fromkeys([*self._state.known, *refs]))
        generated, _ = self._tools.received_attributions(self._invocation(known), known)
        return list(dict.fromkeys([*refs, *generated]))

    def _outcome(self, kind, result):
        refs = self._received(list(dict.fromkeys(result.get('record_refs') or [])))
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
        key = self._operation_key(position)

        async def execute():
            permitted = tuple(self._state.known) if name in _SOURCE_READERS else None
            invocation = self._invocation()
            reader = ReceivedFiles(self._store, invocation, self._bound.recorder, position)
            with self._tools.current_invocation(invocation, read_received=reader,
                                                tool_name=name, arguments=arguments, operation_key=key):
                result = await self._tools.execute_async(name, arguments, scope=self._scope, operation_key=key,
                                                         permitted_record_refs=permitted)
            return self._outcome('tool', result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    def _child(self, position, selection):
        role = selection['role']
        builder = self._builders[role]
        assignment = self._child_assignment(selection)
        scope = assignment['scope']
        report = dict(self._binding.report_contract)
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'], result_contract=report)
        commission = Commission(EpisodeRequest(goal, ContractRecord({'scope': scope}), ReportContract(**report)),
                                assignment)
        child = builder(role + '_' + str(position), commission)
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result)
            refs = admitted['finding'].get('evidence_refs')
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise ContractError('a103_child_finding_requires_evidence_refs:' + role)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'role': role, 'record_refs': self._received(refs),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report_of(result, completion, request):
            admitted = builder.admit(result)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report_of)

    # -- result ---------------------------------------------------------------------
    def result(self, record):
        """The head's return: its measured-context credit and the records it established."""
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a103_head_credit_must_be_finite')
        finding = {
            'scope': self._scope, 'evidence_refs': list(self._state.known),
            'target_sheets': view['target_sheets'], 'a103_sheet': view['a103_sheet'],
            'source_contribution_count': view['source_contribution_count'],
            'credit_binding': self._binding.credit_projector.as_record(),
            'ended_by': record.ended_by, 'units': record.units_consumed}
        # Each field the commissioned report form adds; a null finding value stays absent and the runner's
        # admission raises when the form requires it.
        added = {name: finding[name] for name in self._report_fields if finding[name] is not None}
        return ContractRecord({'credit': credit, 'finding': finding, **added})


__all__ = ['A103Invocation', 'GUIDANCE', 'GeneContextEvidenceSource', 'HEAD_REPORT_FIELDS', 'MODEL_ROLE', 'SCOPE_SCHEMA',
           'commissioned_report_fields', 'head_scope', 'initial_known']
