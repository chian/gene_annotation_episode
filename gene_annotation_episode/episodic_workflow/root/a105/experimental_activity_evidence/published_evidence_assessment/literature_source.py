"""A105 literature decision source on the generic runner (all seven literature bindings).

It follows the head's source (``experimental_activity_evidence/runtime_source.py``)
and the A108 literature reference port:

- each unit is chosen by the model: the source presents the episode's actual
  state and asks ``model_provider.complete`` for one selection under this
  binding's action schema; the response is recorded
  (``decision.<position>.<attempt>``), so a resumed run repeats it;
- a selection that fails admission is rejected before acquisition: no unit,
  no observation; the model decides again with that feedback;
- an admitted selection is one unit: an evidence-interpreting reasoning commit,
  a tool action (an access/acquisition tool of the binding's own registry or an
  A105 sheet population), or a child literature episode. Its outcome,
  including an invalid or failed one, is recorded as ``outcome.<position>`` and
  enters the iterator with the task credit measured after it.

A reasoning commit always goes through ``library.literature_required_grading``
(AGENTS.md, A105): interpreting applicable evidence selects its
purpose-specific grader (``literature.a105.assay_grading``) and saves its
subscoring sheet within the same action, before any credit is measured; the
only grading-free interpretation is a source-grounded ``no_applicable_evidence``
finding over authenticated examined spans; every assessment keeps its typed
``investigation_finding``. A lead judgment (``source_lead``) is verified against
its exact source witness in the same action.

Credit (``literature_credit.task_credit``) reads this episode's recorded
outcomes, the records it holds and its children's returned answers.
"""
from __future__ import annotations

from collections.abc import Mapping
import math

from jsonschema import Draft202012Validator, ValidationError

from method_loop import ChildEpisodeUnit, Leaf

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.experimental_activity_evidence.action_transport import decode_response, generation_schema
from gene_annotation_episode.episodic_workflow.episode_support.forms.boundary_validation import schema_failure_diagnostic
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import canonical, identity, obj, plain, source_location_inputs, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_contract_error import ExperimentalContractError
from ..runtime_binding import A105Record, require_tool_registry
from ..runtime_source import _embedded
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from .literature_binding import (ACCESS_TOOLS, ACQUISITION_TOOLS, CELL_FIELDS, answer_field, assigned_page,
                                 require_reference, within_source)
from .literature_credit import (credit_policy, lead_dispositions, lead_schema, require_target_annotation,
                                screening_answers, task_credit, validate_lead)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_populations import ACCESS_AUTHORITIES, TOOLS as POPULATION_TOOLS, LiteraturePopulations, population_sources

MODEL_ROLE = 'REASONING'
_EXECUTED = ('completed', 'partial')
_RECEIVED_READERS = frozenset({'source.locate', 'source.sequence.references', 'source.experimental.records'})
_AUTHORIZED_READERS = frozenset({'source.read', 'source.locate', 'source.sequence.references',
                                 'source.experimental.records'})
_DISPLAYED_KINDS = frozenset({'reference', 'term', 'context', 'observation', 'hypothesis', 'assessment', 'source'})
_DOMAIN_ERRORS = (ContractError, ExperimentalContractError)
# Each requested sheet a child may return: cells field -> (repository key, cells schema reader).
_CELL_REPOSITORIES = {
    'literature_assay_grading_cells': ('grading', 'literature_assay_grading_storage', 'assay_grading_cells_schema'),
    'literature_a105_aggregation_cells': ('aggregation', 'literature_aggregation_storage',
                                          'aggregation_cells_schema'),
    'literature_quantity_cells': ('quantity', 'literature_quantity_storage', 'quantity_cells_schema'),
}




class _State:
    """What this episode holds, rebuilt on resume from its recorded outcomes."""

    def __init__(self, received):
        self.applied = 0
        self.outcomes = []
        self.received_refs = list(dict.fromkeys(received))
        self.known_assessment_refs = []
        self.last_outcome = None
        self.feedback = None

    def apply(self, outcome):
        for name, refs in (('received_refs', outcome['record_refs']),
                           ('known_assessment_refs', outcome['assessment_refs'])):
            current = getattr(self, name)
            current.extend(ref for ref in refs if ref not in current)
        self.outcomes.append(outcome)
        self.last_outcome = outcome
        self.feedback = None if outcome['status'] in _EXECUTED else outcome['feedback']
        self.applied += 1


def _invalid(feedback):
    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': feedback}


def _references(value, fields):
    """References at ``fields`` anywhere in ``value``."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in fields and isinstance(child, str):
                yield child
            else:
                yield from _references(child, fields)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child, fields)


def _cells_schema(field):
    from importlib import import_module
    _, module, reader = _CELL_REPOSITORIES[field]
    return getattr(import_module('gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.' + module), reader)()


class LiteratureSource:
    """The model-selected units of one A105 literature episode."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._store = collaborators['store']
        self._provider = collaborators['model_provider']
        self._tools = require_tool_registry(binding.tool_registry, self._store, binding.binding_path)
        try:
            self._scope = self._store.validate_scope(bound.assignment['scope'])
        except ContractError as error:
            raise ContractError('a105_literature_scope_must_be_a_store_scope', detail={'reason': str(error)}) from error
        self._assignment = binding.validate_assignment(self._store, bound.assignment['episode_assignment'],
                                                       self._scope)
        self._task = self._assignment['literature_task']
        self._proposed = self._assignment['proposed_annotation_ref']
        require_target_annotation(self._store, self._scope, self._proposed)
        passed = list(bound.assignment['received_record_refs'])
        if any(type(ref) is not str for ref in passed) or set(
                self._store.reference_subset(passed, self._scope)) != set(passed):
            raise ContractError('a105_literature_received_records_must_be_in_scope')
        assignment_refs = list(_references(self._assignment, {'source_ref', 'artifact_ref', 'proposed_annotation_ref'}))
        assignment_refs.extend(ref for field, refs in self._assignment.items() if field.endswith('_refs')
                               for ref in refs)
        page = assigned_page(binding.role, self._assignment)
        if page is not None:
            assignment_refs.extend((*page['question_context_refs'], *page['prior_delivery_refs']))
        self._state = _State([*self._scope['subject_refs'], *passed, *assignment_refs])
        self._populations = LiteraturePopulations(self._store, bound.run_id, binding.populations)
        self._grading = self._populations.repository('grading')
        self._builders = child_builders
        for role, builder in child_builders.items():
            if builder.return_form != binding.return_form:
                raise ContractError('a105_child_return_form_differs:' + role)
        self._children = binding.children if child_builders else {}
        # The commissioner's typed return (C5): exactly the form this task requires, checked before any unit.
        self._answer_fields = binding.required_report_fields(self._assignment, bound.report_form)

    # -- state ------------------------------------------------------------------------------------------------------
    def _catch_up(self, position):
        """Apply the outcomes recorded for units before ``position`` (replayed units on resume)."""
        while self._state.applied < position:
            self._state.apply(self._bound.recorder.recall('outcome.' + str(self._state.applied)))

    def context(self):
        return LiteratureContext(self._bound.run_id, self._bound.episode_id, self._binding.role, self._bound.path,
                                 self._scope, self._assignment, self._bound.request.as_record(),
                                 tuple(self._state.received_refs))

    def credit_view(self):
        return task_credit(self._populations, self.context(), self._task, self._proposed, self._state.outcomes,
                           self._state.received_refs)

    def _controller_input(self, position, outcome):
        return A105Record({'credit': self.credit_view()['credit'],
                           'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                           'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    def _assessments(self, refs):
        return [ref for ref in refs if self._store.get(ref)['record_type'] == 'assessment']

    def _operation_key(self, position):
        return self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

    # -- tools ------------------------------------------------------------------------------------------------------
    def catalog(self):
        """This role's tools from its own registry, and the A105 sheet populations it declares."""
        allowed = set(ACCESS_TOOLS) | (set(ACQUISITION_TOOLS) if self._binding.acquisition else set())
        registry = self._tools.catalog(self._scope)
        missing = sorted(allowed - set(registry))
        if missing:
            raise ContractError('a105_literature_tools_not_in_registry:' + ','.join(missing))
        result = {}
        for name in allowed:
            entry = plain(registry[name])
            if name == 'public.ncbi.search':
                entry['input_schema']['properties']['database'] = {'enum': ['pubmed']}
            result[name] = entry
        for entry in self._populations.catalog():
            result[entry['name']] = {key: value for key, value in entry.items() if key != 'name'}
        return {name: {**entry, 'input_schema': source_location_inputs(entry['input_schema'])}
                for name, entry in result.items()}

    def tool_arguments(self, context, tool_name, arguments, catalog=None):
        """Admit a tool call's arguments for this assignment; a violation raises ``ContractError``."""
        entries = self.catalog() if catalog is None else catalog
        if tool_name not in entries:
            raise ContractError('tool_not_available_to_literature_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        page = assigned_page(self._binding.role, self._assignment)
        if page:
            source_ref = arguments.get('source_ref')
            if tool_name == 'source.archive.extract':
                member = require_reference(self._store, arguments['member_ref'], self._scope, 'archive_member')
                source_ref = member['source_ref']
            if source_ref is not None and not within_source(self._store, source_ref, page['source_ref'], self._scope):
                raise ContractError('literature_reading_outside_assigned_source')
            if tool_name in POPULATION_TOOLS and any(
                    not within_source(self._store, ref, page['source_ref'], self._scope)
                    for ref in population_sources(tool_name, arguments)):
                raise ContractError('literature_reading_outside_assigned_source')
        for key in ACCESS_AUTHORITIES:
            repository = self._populations.repository(key)
            if tool_name in _AUTHORIZED_READERS:
                representation = ('original' if tool_name in {'source.sequence.references', 'source.experimental.records'}
                                  else arguments.get('representation', 'text'))
                repository.authorize_source_access(context, arguments['source_ref'], representation, tool_name)
            elif tool_name == 'state.query' and 'refs' in arguments:
                for ref in arguments['refs']:
                    repository.authorize_record_access(context, self._store.get(ref))
        return arguments

    def _authorize_read(self, context, ref, representation):
        self.tool_arguments(context, 'source.read', {'source_ref': ref, 'representation': representation})

    def _population_arguments(self, context, arguments, repository, operation_key):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_assay_inputs import materialize_text_witness_inputs, saved_text_witness_inputs
        saved = saved_text_witness_inputs(arguments, repository=repository, episode_id=context.episode_id,
                                          operation_key=operation_key)
        if saved is not None:
            return saved

        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._authorize_read(context, ref, representation)
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': self._store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)

    async def execute_tool(self, context, name, arguments, operation_key):
        operation = identity('operation', {'key': operation_key, 'name': name, 'arguments': plain(arguments)})
        try:
            arguments = self.tool_arguments(context, name, arguments)
        except ContractError as error:
            return {**_invalid({'category': 'arguments_or_reference', 'code': str(error),
                                **({'detail': error.detail} if error.detail else {})}), 'operation_ref': operation}
        if name in POPULATION_TOOLS:
            try:
                repository = self._populations.tool_repository(name, arguments)
                return self._populations.populate(
                    context, name, repository,
                    self._population_arguments(context, arguments, repository, operation_key), operation_key)
            except _DOMAIN_ERRORS as error:
                detail = getattr(error, 'detail', None)
                return {**_invalid({'category': 'arguments_or_reference', 'code': str(error),
                                    'field': getattr(error, 'field', None),
                                    **({'detail': plain(detail)} if detail is not None else {})}),
                        'operation_ref': operation}
        permitted = tuple(context.received_record_refs) if name in _RECEIVED_READERS else None
        outcome = await self._tools.execute_async(name, arguments, scope=self._scope, operation_key=operation_key,
                                                  permitted_record_refs=permitted)
        if name == 'state.query' and outcome['status'] in _EXECUTED:
            try:
                for record in outcome['result']['records']:
                    for key in ACCESS_AUTHORITIES:
                        self._populations.repository(key).authorize_record_access(context, record)
            except ContractError as error:
                return {**_invalid({'category': 'arguments_or_reference', 'code': str(error)}),
                        'operation_ref': operation}
        return outcome

    # -- reasoning (interpretation coupled with its grader) -------------------------------------------------------------
    def reasoning_schema(self):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_required_grading
        schema = literature_required_grading.action_schema(
            self._store.reasoning_schema(), source_location_inputs(self._grading.population_schema()))
        if self._task['kind'] == 'verified_source_leads':
            schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema)

    def execute_reasoning(self, context, selection, operation_key):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence import literature_required_grading
        authorize = lambda ref, representation: self._authorize_read(context, ref, representation)
        if 'source_lead' not in selection:
            return literature_required_grading.execute(context, selection, operation_key, self._grading,
                                                       authorize_source_access=authorize)
        try:
            witness = selection['source_lead']['witness']
            self.tool_arguments(context, 'source.read', {'source_ref': witness['source_ref'],
                                                         'representation': witness['representation'],
                                                         'offset': witness['start'],
                                                         'limit': witness['end'] - witness['start']})
            with self._store.transaction():
                native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                result = literature_required_grading.execute(context, native, operation_key, self._grading,
                                                             authorize_source_access=authorize)
                if result['status'] not in _EXECUTED:
                    return result
                return {**result, 'literature_source_lead': validate_lead(
                    self._store, self._task, self._proposed, context.received_record_refs,
                    selection['source_lead'], result)}
        except _DOMAIN_ERRORS as error:
            return _invalid({'category': 'source_lead', 'code': getattr(error, 'code', str(error))})

    # -- presentation -------------------------------------------------------------------------------------------------
    def action_schema(self, catalog):
        options = [{**self.reasoning_schema(), 'description': self._reasoning_requirement()}]
        for name, item in sorted(catalog.items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'tool'}, 'tool': {'type': 'string', 'const': name},
                                'arguments': _embedded(item['input_schema'])}))
        for role, child in sorted(self._children.items()):
            options.append(obj({'kind': {'type': 'string', 'const': 'episode_child'},
                                'role': {'type': 'string', 'const': role},
                                'objective': {'type': 'string', 'minLength': 1,
                                              'description': 'The child episode objective.'},
                                'scope': {'type': 'object', 'description': 'A Store scope within this scope.'},
                                'assignment': child.assignment_schema()}))
        return obj({'selection': {'anyOf': options}})

    @staticmethod
    def _reasoning_requirement():
        from gene_annotation_episode.episodic_workflow.episode_support.literature.prompts.experimental_activity_evidence.literature_investigation_prompt import REASONING_COMMIT_REQUIREMENT
        return REASONING_COMMIT_REQUIREMENT

    def _custody(self):
        page = assigned_page(self._binding.role, self._assignment)
        sources = [page['source_ref']] if page else [ref for field, refs in self._assignment.items()
                                                    if field.endswith('_refs') and field != 'question_context_refs'
                                                    for ref in refs]
        return [{'source_ref': ref, **{key: self._store.get(ref).get(key) for key in
                                       ('version', 'artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref',
                                        'parent_source_refs')}} for ref in sources]

    def _received_display(self):
        records = {}
        for ref in self._state.received_refs:
            record = self._store.get(ref)
            if record['record_type'] in _DISPLAYED_KINDS:
                records[ref] = record
        return {'records': records, 'received_refs': list(self._state.received_refs)}

    def decision_context(self, view, catalog):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import current_scoring_sheets
        credit = self.credit_view()
        state = view.controller_state
        page_size = self._binding.outcome_page_size
        return {
            'goal': self._bound.request.goal.as_record(),
            'role': self._binding.role,
            'scope': self._scope,
            'literature_assignment': self._assignment,
            'literature_goal_plan': {'commissioned_result': self._task, 'proposed_annotation_ref': self._proposed,
                                     'progress_definition': credit_policy(self._task)},
            'literature_source_custody': self._custody(),
            'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                                             'aspect': 'source_experimental_evidence', 'evidence_axis': 'A105'},
            'working_state': self._store.reasoning_view(self._scope),
            'literature_received_fact_display': self._received_display(),
            'known_assessment_refs': list(self._state.known_assessment_refs),
            'current_credit': credit['credit'],
            'task_status': credit['task_status'],
            'source_contributions': credit['source_contributions'],
            'literature_current_scoring_sheets': current_scoring_sheets(self._store, self.context()),
            'controller': state.as_record(),
            'units_consumed': view.units_consumed,
            'own_literature_outcomes': [{key: outcome.get(key) for key in
                                         ('position', 'kind', 'action', 'role', 'status', 'record_refs', 'feedback')}
                                        for outcome in self._state.outcomes[-page_size:]],
            'last_local_outcome': self._state.last_outcome,
            'feedback': self._state.feedback,
            'tools': {name: {key: value for key, value in item.items() if key != 'input_schema'}
                      for name, item in sorted(catalog.items())},
            'child_options': {role: child.purpose for role, child in sorted(self._children.items())},
        }

    # -- decisions ----------------------------------------------------------------------------------------------------
    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            catalog = self.catalog()
            schema = self.action_schema(catalog)
            context = self.decision_context(view, catalog)
            instructions = self._binding.instructions()
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._provider.complete(self._bound.episode_id, MODEL_ROLE, instructions, context,
                                                generation_schema(schema)))
            try:
                selection = self.admit(response, schema)
                prepared = self.prepare(position, selection, catalog)
            except (ValueError, KeyError, TypeError, ValidationError, ContractError) as error:
                # Rejected before acquisition: no unit, no observation; decide again with the feedback.
                self._state.feedback = {'status': 'invalid', 'category': 'action_contract',
                                        'detail': schema_failure_diagnostic(error)
                                        if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            return self.unit(position, selection, prepared)

    def admit(self, response, schema):
        if not isinstance(response, Mapping) or set(response) != {'selection'}:
            raise ValueError('a105_decision_response_must_be_exactly_selection')
        selection = decode_response(dict(response), schema)['selection']
        Draft202012Validator(schema['properties']['selection']).validate(selection)
        if selection['kind'] == 'reason':
            Draft202012Validator(self.reasoning_schema()).validate(selection)
            commit = selection['commit']
            if (all(rows == [] for rows in commit.values()) and 'source_lead' not in selection
                    and selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                raise ValueError('empty_reasoning_commit')
        return selection

    def prepare(self, position, selection, catalog):
        """What an admitted selection needs before acquisition; ``None`` for own work."""
        if selection['kind'] != 'episode_child':
            return None
        role = selection['role']
        child = self._children[role]
        scope = self._store.validate_scope(selection['scope'], parent_scope=self._scope)
        admitted = child.validate_assignment(self._store, selection['assignment'], scope)
        if admitted['proposed_annotation_ref'] != self._proposed:
            raise ContractError('literature_child_proposed_annotation_differs_from_parent')
        require_target_annotation(self._store, scope, self._proposed)
        page = assigned_page(self._binding.role, self._assignment)
        child_page = assigned_page(role, admitted)
        if page is not None and child_page is not None and not within_source(
                self._store, child_page['source_ref'], page['source_ref'], scope):
            raise ContractError('literature_reading_outside_assigned_source')
        assignment = {'scope': scope,
                      'received_record_refs': self._store.reference_subset(self._state.received_refs, scope),
                      'episode_assignment': selection['assignment']}
        return child.commission(self._bound.request.goal, selection['objective'], assignment)

    def unit(self, position, selection, prepared):
        kind = selection['kind']
        if kind == 'reason':
            return Leaf(selection, lambda chosen: self._reason(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'reason:' + str(position))
        if kind == 'tool':
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome), 'tool:' + str(position))
        return self._child(position, selection['role'], prepared)

    # -- execution ----------------------------------------------------------------------------------------------------
    def _outcome(self, position, kind, action, result):
        refs = list(dict.fromkeys(result.get('record_refs') or []))
        outcome = {'position': position, 'kind': kind, 'action': action, 'status': result['status'],
                   'record_refs': refs, 'assessment_refs': self._assessments(refs), 'result': result}
        outcome['feedback'] = None if result['status'] in _EXECUTED else (result.get('feedback') or {
            'status': result['status'], 'category': result.get('error_code') or 'work_failed'})
        return outcome

    def _reason(self, position, selection):
        def execute():
            try:
                result = self.execute_reasoning(self.context(), selection, self._operation_key(position))
            except _DOMAIN_ERRORS as error:
                result = {'status': 'failed', 'record_refs': [], 'result': None,
                          'feedback': {'category': 'reasoning_execution', 'code': getattr(error, 'code', str(error))}}
            return self._outcome(position, 'reason', {'kind': 'reason'}, result)
        outcome = self._bound.recorder.recorded('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    async def _tool(self, position, selection):
        name, arguments = selection['tool'], selection['arguments']

        async def execute():
            try:
                result = await self.execute_tool(self.context(), name, arguments, self._operation_key(position))
            except _DOMAIN_ERRORS as error:
                result = {'status': 'failed', 'record_refs': [], 'result': None,
                          'feedback': {'category': 'tool_execution', 'code': getattr(error, 'code', str(error))}}
            return self._outcome(position, 'tool', {'kind': 'tool', 'tool': name, 'arguments': plain(arguments)},
                                 result)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), execute)
        self._state.apply(outcome)
        return outcome

    def _child(self, position, role, commission):
        builder = self._builders[role]
        child = builder(role + '_' + str(position), commission)
        scope = commission.assignment['scope']
        form = commission.report_form
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result, form)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: self._child_outcome(
                position, role, scope, admitted, completion.as_record()))
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def failed(error):
            if not isinstance(error, _DOMAIN_ERRORS):
                raise error
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'position': position, 'kind': 'child', 'role': role, 'status': 'failed', 'record_refs': [],
                'assessment_refs': [], 'finding': {}, 'answer': {},
                'feedback': {'category': 'child_episode', 'code': getattr(error, 'code', str(error))}})
            self._state.apply(outcome)
            return self._controller_input(position, outcome)

        def report(result, completion, request):
            admitted = builder.admit(result, form)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report, receive_failure=failed)

    def _child_outcome(self, position, role, scope, admitted, completion):
        """Receive a child's return, admitted against the form this parent commissioned: its records,
        its typed answer (leads, assessments, screening or sheet cells) and its requested sheet cells."""
        finding = admitted['finding']
        refs = finding.get('evidence_refs')
        if (not isinstance(refs, list) or any(type(ref) is not str for ref in refs)
                or set(self._store.reference_subset(refs, scope)) != set(refs)):
            raise ContractError('a105_literature_child_finding_requires_evidence_refs_in_scope:' + role)
        if finding.get('proposed_annotation_ref') != self._proposed:
            raise ContractError('a105_literature_child_finding_question_mismatch:' + role)
        answer = {name: plain(value) for name, value in admitted.items() if name not in ('credit', 'finding')}
        for lead in answer.get('source_lead_dispositions', []):
            validate_schema(lead, lead_schema())
            if lead['proposed_annotation_ref'] != self._proposed:
                raise ContractError('a105_literature_child_lead_question_mismatch:' + role)
        for item in answer.get('screening_answers', []):
            if item['proposed_annotation_ref'] != self._proposed:
                raise ContractError('a105_literature_child_screening_question_mismatch:' + role)
        assessments = answer.get('changed_assessment_refs', [])
        if any(type(ref) is not str for ref in assessments) or not set(assessments) <= set(refs):
            raise ContractError('a105_literature_child_assessments_not_returned_records:' + role)
        received = list(refs)
        for field, (key, _, _) in _CELL_REPOSITORIES.items():
            cells = answer.get(field, [])
            if not cells:
                continue
            repository = self._populations.repository(key)
            validate_schema(cells, _cells_schema(field))
            sheets = list(dict.fromkeys(row['sheet_ref'] for row in cells))
            for sheet in sheets:
                expected = repository.project_cells([sheet], permitted_record_refs=[sheet],
                                                    components=list(dict.fromkeys(
                                                        row['component'] for row in cells if row['sheet_ref'] == sheet)))
                if canonical(expected) != canonical([row for row in cells if row['sheet_ref'] == sheet]):
                    raise ContractError('a105_literature_child_cells_differ_from_saved_sheet:' + role)
            context = self.context()
            receiving = LiteratureContext(context.run_id, context.episode_id, context.role, context.path,
                                          context.scope, context.assignment, context.request,
                                          tuple(dict.fromkeys([*context.received_record_refs, *sheets])))
            repository.receive_cells(receiving, cells,
                                     'child_return:' + self._bound.run_id + ':' + self._bound.episode_id + ':'
                                     + str(position) + ':' + field)
            received.extend(repository.cell_record_refs(cells))
        received = list(dict.fromkeys(received))
        return {'position': position, 'kind': 'child', 'role': role, 'status': 'completed', 'record_refs': received,
                'assessment_refs': self._assessments(received), 'finding': plain(finding), 'answer': answer,
                'child_credit': admitted['credit'], 'child_completion': completion, 'feedback': None}

    # -- result -------------------------------------------------------------------------------------------------------
    def _requested_cells(self, context):
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import current_sheet_refs
        cells = {}
        candidates = list(dict.fromkeys([*context.received_record_refs, *current_sheet_refs(self._store, context)]))
        view = LiteratureContext(context.run_id, context.episode_id, context.role, context.path, context.scope,
                                 context.assignment, context.request, tuple(candidates))
        for requested, (field, _) in CELL_FIELDS.items():
            if field not in self._answer_fields:
                continue
            repository = self._populations.repository(_CELL_REPOSITORIES[field][0])
            selected = [ref for ref in candidates if self._store.get(ref)['record_type'] == 'source'
                        and self._store.get(ref).get('provider') == repository.provider
                        and self._store.get(ref).get('version') == repository.record_version]
            cells[field] = repository.fact_cells(view, selected, components=list(self._assignment[requested]))
        return cells

    def result(self, record):
        """The literature return, exactly the commissioned form: credit, finding and the typed answer."""
        from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_sheet_updates import current_scoring_sheets
        self._catch_up(record.units_consumed)
        view = self.credit_view()
        credit = view['credit']
        if isinstance(credit, bool) or not isinstance(credit, (int, float)) or not math.isfinite(credit):
            raise ContractError('a105_literature_credit_must_be_finite')
        context = self.context()
        answer = self._requested_cells(context)
        sheet_refs = [row['sheet_ref'] for rows in answer.values() for row in rows]
        name, _ = answer_field(self._task)
        if name == 'source_lead_dispositions':
            answer[name] = lead_dispositions(self._store, self._proposed, self._state.outcomes)
        elif name == 'screening_answers':
            answer[name] = screening_answers(self._store, self._task, self._proposed, self._state.outcomes)
        elif name == 'changed_assessment_refs':
            answer[name] = list(self._state.known_assessment_refs)
        lead_refs = [ref for lead in answer.get('source_lead_dispositions', [])
                     for ref in (lead['source_ref'], lead['subject_ref'])]
        if set(answer) != set(self._answer_fields):
            raise ContractError('literature_answer_differs_from_commissioned_form')
        finding = {'role': self._binding.role, 'scope': self._scope, 'task': self._task,
                   'proposed_annotation_ref': self._proposed, 'task_status': view['task_status'],
                   'policy': view['policy'], 'source_contributions': view['source_contributions'],
                   'known_assessment_refs': list(self._state.known_assessment_refs),
                   'literature_current_scoring_sheets': current_scoring_sheets(self._store, context),
                   'evidence_refs': list(dict.fromkeys([*self._state.known_assessment_refs, *sheet_refs, *lead_refs])),
                   'ended_by': record.ended_by, 'units': record.units_consumed}
        return A105Record({'credit': credit, 'finding': finding, **answer})


__all__ = ['LiteratureContext', 'LiteratureSource', 'MODEL_ROLE']
