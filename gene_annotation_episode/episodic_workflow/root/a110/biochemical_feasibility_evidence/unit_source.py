"""The A110 model-selected unit source on the generic runner (episode_runtime).

The A110 head and every A110 binding whose units are scientific tool actions,
reasoning commits or child commissions (the head and the seven literature
bindings) run this source. Each binding supplies what is its own:

- ``tool_registry``: its own A110 ``ToolRegistry``, built by the A110 home
  factory over the run's shared Store (ruling C4);
- ``instructions()``: its own decision instructions;
- ``assignment_form``: its commission. ``scope`` is the subject scope; a
  ``tools`` ``SubsetField`` (C6) is the subset of the binding's own operations the
  commissioner selected, and the source offers only those; any other field is the
  commissioner's record for this episode and is presented with every decision.

One unit per model selection:

- ``tool``: one offered operation, executed with the episode's scope and a
  deterministic operation key;
- ``reason``: one typed reasoning commit into the Store (``store.commit_reasoning``),
  idempotent per operation key;
- ``child``: one commissioned child Episode in a declared child slot. The model
  fills the child's ``assignment`` record, its ``ChoiceField`` / ``SubsetField``
  choices (C3/C6; the runner checks membership) and its objective; the head never
  invents a value for any other field.

Credit is the episode's own unbounded cumulative value: one finding unit per
distinct retained finding among the assessments this episode knows (its own
committed assessments and those its children returned), projected by the A110
``ScientificFindingProgress`` policy over the actual store. A child's own credit
number is never added to the parent. Credit is never clamped or rescaled. The
episode's YieldController owns continuation; there is no model stop action.

Every model decision (``a110.decision.<p>.<attempt>``), every executed outcome
(``a110.outcome.<p>``) and every unit's state entry (``a110.unit.<p>``) is
recorded through ``bound.recorder``; a resumed episode reads them back. A
response that fails admission is returned to the model as feedback before any
unit is acquired and creates no executed action. An executed tool or reasoning
action enters the iterator with its credit whatever its status.
"""
from __future__ import annotations

from collections.abc import Mapping
import json

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import ChoiceField, Commission, DeclaredField, SubsetField
from method_loop import ChildEpisodeUnit, Episode, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import ToolRegistry
from .axis_task_context import finding_progress
from .runtime_contract import CHILD_REPORT, RuntimeRecord

MODEL_ROLE = 'REASONING'
# Tools that read only the records this episode has received (the A110 scientific operations rule).
_PERMITTED_RECORD_TOOLS = ('partner.', 'chemistry.')
_PERMITTED_RECORD_TOOL_NAMES = frozenset({'source.locate'})
# What a parent's child slot must return for this source to admit it: its own credit and its finding (text,
# or a record such as a progress monitor's monitoring facts). A child whose return form also declares
# ``assessment_refs`` returns the assessments it knows; a child that declares none (a progress monitor)
# returns no assessment, so it adds no finding to this episode's credit.
_CHILD_RETURN_TYPES = {'credit': ('number',), 'finding': ('text', 'record')}
_CHILD_ASSESSMENTS = 'assessment_refs'
_CHOSEN = (ChoiceField, SubsetField)

PROTOCOL = (
    'Each decision returns one JSON object with two fields. finding is your current interpretation of what '
    'this investigation has established so far, written before the selected action runs; keep the evidence, '
    'conditions, uncertainty and unknowns explicit. selection chooses exactly one next unit:\n'
    '- tool: one operation from tools. arguments_json is the JSON encoding of its exact argument object; the '
    'host validates it against that operation\'s input_schema before execution.\n'
    '- reason: one typed scientific commit. commit_json is the JSON encoding of an object matching '
    'reasoning_commit_schema. Committed assessments with a retained investigation_finding are the findings '
    'this episode knows.\n'
    '- child: commission one child episode in a declared child slot. objective states the child\'s scoped '
    'question; scope_json encodes the child\'s subject scope, which must lie within your scope; '
    'assignment_json encodes the record the slot\'s assignment field asks for; choices_json encodes an object '
    'with one value for every choice field the slot\'s assignment_form offers (an option, or a list of '
    'distinct options for a subset field). The child returns its finding, its own credit and the assessments '
    'it knows.\n'
    'A response that fails admission is returned to you as feedback and is not executed. Executed outcomes, '
    'failed or invalid ones included, are recorded in history. credit counts one unit per distinct retained '
    'finding among the assessments this episode knows; reads, attempts and waiting earn nothing by '
    'themselves. The numerical controller decides continuation from your credit history; there is no stop '
    'action.')


def _closed(properties):
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def _text():
    return {'type': 'string', 'minLength': 1}


def plain_json(value, what):
    """A closed JSON copy; anything that is not JSON raises."""
    try:
        return json.loads(json.dumps(value, sort_keys=True, allow_nan=False, ensure_ascii=False))
    except (TypeError, ValueError) as error:
        raise ContractError('a110_value_must_be_closed_json:' + what) from error


def _decoded(text, what):
    try:
        value = json.loads(text)
    except (TypeError, ValueError) as error:
        raise ContractError('a110_invalid_json_field:' + what) from error
    if not isinstance(value, dict):
        raise ContractError('a110_json_field_must_encode_an_object:' + what)
    return value


def _record_ids(value):
    """Every record identity in a reasoning view or outcome (rows carrying an ``id``)."""
    found = []
    if isinstance(value, Mapping):
        if isinstance(value.get('id'), str):
            found.append(value['id'])
        for item in value.values():
            found.extend(_record_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_record_ids(item))
    return found


def finding_credit(store, scope, known_assessment_refs):
    """The cumulative credit and retained finding count over the assessments an episode knows.

    One finding unit per distinct retained finding (A110 ``finding_progress``); unbounded, never rescaled.
    """
    projected = finding_progress()(store, scope, known_assessment_refs=list(known_assessment_refs))
    return projected['credit'], projected['retained_finding_count']


def selectable_tools(tool_registry, names=None):
    """The operation names a binding offers for selection: its registry's catalog, or ``names`` within it."""
    if not isinstance(tool_registry, ToolRegistry):
        raise ContractError('a110_binding_requires_its_own_a110_tool_registry:' + type(tool_registry).__name__)
    catalog = tool_registry.catalog(None)
    if names is None:
        return tuple(sorted(catalog))
    missing = sorted(set(names) - set(catalog))
    if missing:
        raise ContractError('a110_declared_tools_not_in_registry:' + ','.join(missing))
    return tuple(sorted(names))


def check_child_slots(child_builders):
    """Every declared child slot must return what this source admits and ask only for what it can fill."""
    for slot, builder in child_builders.items():
        fields = builder.return_form.fields
        for name, kinds in _CHILD_RETURN_TYPES.items():
            if name not in fields or fields[name].type not in kinds:
                raise ContractError('a110_child_return_form_requires_' + name + '_' + '_or_'.join(kinds) + ':' + slot)
        if _CHILD_ASSESSMENTS in fields and fields[_CHILD_ASSESSMENTS].type != 'list':
            raise ContractError('a110_child_return_form_assessment_refs_must_be_a_list:' + slot)
        for name, spec in builder.assignment_form.fields.items():
            if not isinstance(spec, (DeclaredField, *_CHOSEN)) and name not in ('scope', 'assignment'):
                raise ContractError('a110_cannot_supply_child_assignment_field:' + slot + ':' + name)


class UnitState:
    """The source state after a number of completed units, folded from their recorded entries."""

    def __init__(self):
        self.units = 0
        self.history = []
        self.known_assessment_refs = []
        self.received_refs = []
        self.child_reports = []
        self.finding = None
        self.credit = 0.
        self.last_outcome = None

    def apply(self, entry):
        if entry['position'] != self.units:
            raise ContractError('a110_unit_state_entry_out_of_order:' + str(entry['position']))
        self.units += 1
        self.history.append(entry['history'])
        for ref in entry['known_assessment_refs']:
            if ref not in self.known_assessment_refs:
                self.known_assessment_refs.append(ref)
        for ref in entry['received_refs']:
            if ref not in self.received_refs:
                self.received_refs.append(ref)
        if entry['child_report'] is not None:
            self.child_reports.append(entry['child_report'])
        self.finding = entry['finding']
        self.credit = entry['credit']
        self.last_outcome = entry['outcome']


class UnitSource:
    """The method_loop source: model-selected units over the actual store, the binding's tools and children."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self.binding, self.bound = binding, bound
        self.store, self.provider = collaborators['store'], collaborators['model_provider']
        self.tools = binding.tool_registry
        if self.tools.store is not self.store:
            raise ContractError('a110_tool_registry_must_use_the_run_store:' + binding.binding_path)
        if bound.report_form != binding.return_form:
            # A commissioner may add report fields (C5); no A110 decision fills them yet.
            raise ContractError('a110_cannot_fill_commissioned_report_fields:' + binding.binding_path + ':' + ','.join(
                sorted(set(bound.report_form.fields) - set(binding.return_form.fields))))
        self.recorder, self.request = bound.recorder, bound.request
        assignment = dict(bound.assignment)
        self.scope = self.store.validate_scope(plain_json(assignment.pop('scope'), 'scope'))
        if 'tools' not in assignment:
            raise ContractError('a110_commission_must_select_its_tools:' + binding.binding_path)
        self.offered_tools = tuple(assignment.pop('tools'))
        self.commission = plain_json(assignment, 'assignment')
        check_child_slots(child_builders)
        self.child_builders = child_builders
        self.progress = finding_progress()
        self._state = UnitState()
        self._feedback = None

    # -- state ----------------------------------------------------------------
    @staticmethod
    def _entry_name(position):
        return 'a110.unit.' + str(position)

    def state_at(self, position):
        """The source state before unit ``position``; a resumed source reads back its recorded entries."""
        if self._state.units > position:
            raise ContractError('a110_source_position_moved_backwards:' + str(position))
        while self._state.units < position:
            self._state.apply(self.recorder.recall(self._entry_name(self._state.units)))
        return self._state

    def _commit_entry(self, entry):
        recorded = self.recorder.recorded(self._entry_name(entry['position']), lambda: plain_json(entry, 'unit'))
        self._state.apply(recorded)
        self._feedback = None
        return recorded

    def credit(self, known_assessment_refs):
        return finding_credit(self.store, self.scope, known_assessment_refs)

    # -- decision -------------------------------------------------------------
    def catalog(self):
        entries = self.tools.catalog(self.scope)
        if not isinstance(entries, Mapping):
            raise ContractError('a110_tool_registry_catalog_must_be_a_mapping')
        names = list(self.offered_tools)
        missing = [name for name in names if name not in entries]
        if missing:
            raise ContractError('a110_offered_tools_not_in_catalog:' + ','.join(missing))
        return {name: plain_json({key: entries[name][key] for key in ('description', 'input_schema')}, 'tool:' + name)
                for name in sorted(names)}

    def response_schema(self, catalog):
        variants = [_closed({'kind': {'type': 'string', 'const': 'reason'}, 'commit_json': _text()})]
        if catalog:
            variants.insert(0, _closed({'kind': {'type': 'string', 'const': 'tool'},
                                        'tool': {'type': 'string', 'enum': sorted(catalog)},
                                        'arguments_json': _text()}))
        if self.child_builders:
            variants.append(_closed({'kind': {'type': 'string', 'const': 'child'},
                                     'slot': {'type': 'string', 'enum': sorted(self.child_builders)},
                                     'objective': _text(), 'scope_json': _text(), 'assignment_json': _text(),
                                     'choices_json': _text()}))
        return _closed({'finding': _text(), 'selection': {'anyOf': variants}})

    def context(self, view, state, catalog):
        with self.store.read_snapshot():
            records = self.store.reasoning_view(self.scope)
        credit, retained = self.credit(state.known_assessment_refs)
        return plain_json({
            'goal': self.request.goal.as_record(),
            'binding_path': self.binding.binding_path,
            'commission': self.commission,
            'scope': self.scope,
            'records': records,
            'current_credit': {'credit': credit, 'retained_finding_count': retained,
                               'credit_definition': self.progress.as_record()},
            'known_assessment_refs': state.known_assessment_refs,
            'controller': view.controller_state.as_record(),
            'current_finding': state.finding,
            'history': state.history,
            'last_outcome': state.last_outcome,
            'child_reports': state.child_reports,
            'feedback': self._feedback,
            'tools': [{'name': name, **entry} for name, entry in catalog.items()],
            'reasoning_commit_schema': self.store.reasoning_schema(),
            'child_slots': {slot: {'binding_path': builder.binding_path,
                                   'assignment_form': builder.assignment_form.as_record(),
                                   'return_form': builder.return_form.as_record()}
                            for slot, builder in sorted(self.child_builders.items())},
        }, 'decision_context')

    async def next(self, view):
        position = view.units_consumed
        state = self.state_at(position)
        attempt = 0
        while True:
            catalog = self.catalog()
            schema = self.response_schema(catalog)
            context = self.context(view, state, catalog)
            response = await self.recorder.recorded_async(
                'a110.decision.' + str(position) + '.' + str(attempt),
                lambda: self.provider.complete(self.bound.episode_id, MODEL_ROLE, self.binding.instructions(),
                                               context, schema))
            if not isinstance(response, dict):
                raise ContractError('a110_model_provider_response_must_be_a_record:' + type(response).__name__)
            try:
                build_unit = self.admit(position, response, schema, catalog, _record_ids(context['records']))
            except (ContractError, ValidationError, ValueError) as error:
                self._feedback = {'status': 'invalid', 'attempt': attempt,
                                  'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            # Admission is complete; building the unit (a child commission) is not a model error.
            return build_unit()

    def admit(self, position, response, schema, catalog, visible_refs):
        """Admit one model response; returns the builder of its unit. Inadmissible responses raise here."""
        Draft202012Validator(schema).validate(response)
        finding, selection = response['finding'], response['selection']
        kind = selection['kind']
        if kind == 'tool':
            arguments = _decoded(selection['arguments_json'], 'arguments_json')
            Draft202012Validator(catalog[selection['tool']]['input_schema']).validate(arguments)
            return lambda: self._tool_unit(position, selection['tool'], arguments, finding, visible_refs)
        if kind == 'reason':
            commit = _decoded(selection['commit_json'], 'commit_json')
            Draft202012Validator(self.store.reasoning_schema()).validate(commit)
            if all(rows == [] for rows in commit.values()):
                raise ContractError('empty_reasoning_commit')
            return lambda: self._reason_unit(position, commit, finding, visible_refs)
        prepared = self._child_commission(selection)
        return lambda: self._child_unit(position, prepared, finding, visible_refs)

    # -- units ----------------------------------------------------------------
    def _operation_key(self, position):
        return self.bound.run_id + ':' + self.bound.episode_id + ':' + str(position)

    def _complete(self, position, label, kind, selected, status, outcome, finding, new_assessments, received,
                  child_report=None):
        """Record the unit's state change once and return its controller input (credit and progress time)."""
        if not isinstance(status, str) or not status:
            raise ContractError('a110_outcome_status_required:' + label)
        known = list(dict.fromkeys([*self._state.known_assessment_refs, *new_assessments]))
        credit, retained = self.credit(known)
        entry = self._commit_entry({
            'position': position, 'finding': finding, 'credit': credit, 'child_report': child_report,
            'known_assessment_refs': list(new_assessments), 'received_refs': list(dict.fromkeys(received)),
            'outcome': outcome,
            'history': {'position': position, 'label': label, 'kind': kind, 'selected': selected, 'status': status,
                        'record_refs': list(outcome.get('record_refs') or ()), 'feedback': outcome.get('feedback'),
                        'credit': credit, 'retained_finding_count': retained}})
        return RuntimeRecord({'unit': label, 'kind': kind, 'status': entry['history']['status'],
                              'credit': entry['credit'],
                              'estimation_context': {'progress_time': self.bound.progress.receipt(position)}})

    def _tool_unit(self, position, name, arguments, finding, visible_refs):
        label = 'tool:' + str(position)

        async def execute(_unit):
            options = {}
            if name.startswith(_PERMITTED_RECORD_TOOLS) or name in _PERMITTED_RECORD_TOOL_NAMES:
                options['permitted_record_refs'] = list(dict.fromkeys([*self._state.received_refs, *visible_refs]))
            return await self.recorder.recorded_async(
                'a110.outcome.' + str(position), lambda: self._tool_outcome(name, arguments, position, options))

        def result(_unit, outcome):
            refs = list(outcome.get('record_refs') or ())
            return self._complete(position, label, 'tool', {'tool': name, 'arguments': arguments},
                                  outcome.get('status'), outcome, finding, [], [*visible_refs, *refs])
        return Leaf((name, position), execute, result, label)

    async def _tool_outcome(self, name, arguments, position, options):
        outcome = await self.tools.execute_async(name, arguments, scope=self.scope,
                                                 operation_key=self._operation_key(position), **options)
        if not isinstance(outcome, Mapping):
            raise ContractError('a110_tool_outcome_must_be_a_record:' + name)
        return plain_json(outcome, 'tool_outcome:' + name)

    def _reason_unit(self, position, commit, finding, visible_refs):
        label = 'reason:' + str(position)

        async def execute(_unit):
            # Store.commit_reasoning is idempotent per operation key; its outcome is also recorded.
            return await self.recorder.recorded_async(
                'a110.outcome.' + str(position), lambda: self._reason_outcome(commit, position))

        def result(_unit, outcome):
            refs = list(outcome.get('record_refs') or ())
            assessments = [ref for ref in refs if self.store.get(ref).get('record_type') == 'assessment']
            return self._complete(position, label, 'reason', {'commit': commit}, outcome.get('status'), outcome,
                                  finding, assessments, [*visible_refs, *refs])
        return Leaf(('reason', position), execute, result, label)

    async def _reason_outcome(self, commit, position):
        return plain_json(self.store.commit_reasoning(commit, self.scope, self._operation_key(position)), 'commit')

    def _child_commission(self, selection):
        """Admit a child selection into the slot's exact assignment and request (no child is built here)."""
        slot = selection['slot']
        builder = self.child_builders[slot]
        scope = self.store.validate_scope(_decoded(selection['scope_json'], 'scope_json'), self.scope)
        prepared = _decoded(selection['assignment_json'], 'assignment_json')
        choices = _decoded(selection['choices_json'], 'choices_json')
        fields = builder.assignment_form.fields
        if 'assignment' not in fields and prepared:
            raise ContractError('a110_child_slot_takes_no_assignment:' + slot)
        offered = {name for name, spec in fields.items() if isinstance(spec, _CHOSEN)}
        if set(choices) - offered:
            raise ContractError('a110_child_slot_offers_no_such_choice:' + slot + ':' + ','.join(
                sorted(set(choices) - offered)))
        assignment = {}
        for name, spec in fields.items():
            if isinstance(spec, DeclaredField):
                assignment[name] = spec.value
            elif isinstance(spec, _CHOSEN):
                if name in choices:
                    assignment[name] = choices[name]
                elif spec.required:
                    raise ContractError('a110_child_choice_required:' + slot + ':' + name)
            elif name == 'scope':
                assignment[name] = scope
            elif name == 'assignment':
                assignment[name] = prepared
            else:
                raise ContractError('a110_cannot_supply_child_assignment_field:' + slot + ':' + name)
        builder.assignment_form.admit(assignment, 'a110_child_assignment:' + slot)
        report = ReportContract(decision=self.binding.goal, measurements={}, information=CHILD_REPORT)
        goal = EpisodeGoal.child(self.request.goal, objective=selection['objective'],
                                 result_contract=report.as_record())
        message = RuntimeRecord({'commissioned_by': self.binding.binding_path, 'slot': slot,
                                 'objective': selection['objective']})
        return {'slot': slot, 'builder': builder, 'objective': selection['objective'], 'scope': scope,
                'prepared': prepared, 'choices': choices,
                'commission': Commission(EpisodeRequest(goal, message, report), assignment)}

    def _child_unit(self, position, prepared, finding, visible_refs):
        slot, builder = prepared['slot'], prepared['builder']
        # A child key is deterministic in the parent's unit position, so a resumed child is the recorded one.
        child = builder(slot + '_' + str(position), prepared['commission'])
        selected = {'slot': slot, 'objective': prepared['objective'], 'scope': prepared['scope'],
                    'assignment': prepared['prepared'], 'choices': prepared['choices']}

        returns_assessments = _CHILD_ASSESSMENTS in builder.return_form.fields

        def returned_record(child_result):
            returned = builder.admit(child_result)
            assessments = list(dict.fromkeys(returned[_CHILD_ASSESSMENTS])) if returns_assessments else []
            for ref in assessments:
                if type(ref) is not str or self.store.get(ref).get('record_type') != 'assessment':
                    raise ContractError('a110_child_returned_a_non_assessment_reference:' + slot)
            return returned, assessments

        def receive_result(child_result, completion, request):
            returned, assessments = returned_record(child_result)
            report = {'position': position, 'slot': slot, 'objective': prepared['objective'],
                      'finding': returned['finding'], 'child_credit': returned['credit'],
                      'assessment_refs': assessments, 'ended_by': completion.ended_by}
            outcome = {'status': 'completed', 'record_refs': assessments, 'child_finding': returned['finding']}
            return self._complete(position, child.label, 'child', selected, 'completed', outcome, finding,
                                  assessments, [*visible_refs, *assessments], child_report=report)

        def synthesize_report(child_result, completion, request):
            returned, _ = returned_record(child_result)
            return {'finding': returned['finding'], 'credit': returned['credit']}
        return ChildEpisodeUnit(child, receive_result, synthesize_report)

    # -- result ---------------------------------------------------------------
    def build_result(self, record):
        if record.units_consumed == 0:
            raise ContractError('a110_episode_closed_without_a_completed_unit:' + self.bound.binding_path)
        state = self.state_at(record.units_consumed)
        current = record.controller_state.as_record()['current_credit']
        if current != state.credit:
            raise ContractError('a110_controller_credit_differs_from_recorded_credit')
        return RuntimeRecord({'credit': state.credit, 'finding': state.finding,
                              'assessment_refs': list(state.known_assessment_refs)})


def build_unit_episode(binding, grain, bound, collaborators, child_builders):
    """The Episode: its own source and result; the runner supplies grain, key and request unchanged."""
    source = UnitSource(binding, bound, collaborators, child_builders)
    return Episode(grain, bound.key, source, bound.request, source.build_result)


__all__ = ['MODEL_ROLE', 'PROTOCOL', 'UnitSource', 'UnitState', 'build_unit_episode', 'check_child_slots',
           'finding_credit', 'plain_json', 'selectable_tools']
