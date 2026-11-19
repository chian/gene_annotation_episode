"""The A107 progress monitor on the generic runner (``episode_runtime``).

Every A107 ``execution_progress_assessment`` binding mixes in ``A107MonitorRuntime``;
each binding declares its own path, commissioning parent, child slots and how
its commission carries the monitor assignment (``role_assignment`` /
``child_assignment``).

One monitor Episode improves knowledge of the progress of one assigned
execution target. Each unit is one of the monitor's own progress tools
(``progress.observe``, ``progress.read``, ``progress.log``) or, where the binding
declares a monitor child slot, one commissioned monitor for an exposed direct
job dependency of its target. The A107 model collaborator selects each unit from
the monitor's decision state. Every executed tool outcome, including an invalid
or failed one, is one unit. A selection rejected before execution creates no
unit; the model receives that rejection as feedback and decides again.

Credit is the monitor's own ``ProgressInformationCredit``: one information unit
per newly informative progress snapshot this Episode received (its own and the
snapshots its dependency monitors delivered), over the assignment's original
baseline. It is never bounded, clamped or rescaled. Continuation is the
monitor's own information-accumulation yield controller; each unit's controller
input carries its cumulative credit and the Episode's progress-time receipt.

Every model decision (``decision.<position>.<attempt>``) and every unit outcome
(``outcome.<position>``) is recorded through the Episode's ``EpisodeRecorder``; a
resumed Episode reads them back and does not ask the model or execute again.

Runtime collaborators (``required_collaborators``), each required:

- ``model_provider`` (standard): the run's one model provider;
- ``store`` (standard): the run's shared Store; the assignment's ``scope`` must be
  exactly the scope this Store admits, and the binding's own tool registry must
  be over this Store;
- ``a107_progress_provider``: A107's ``library.progress_provider.ProgressProvider``
  over that Store (``observe``, ``read_progress``, ``describe_target``,
  ``direct_dependencies``, ``resolve``).

``progress.log`` reads its exact source byte window through the binding's own
tool registry (construction operand ``tool_registry``, built by the A107 home
factory over the shared Store), permitted only the window's received source.

A parent's per-commission typed report form (C5) may add any of the monitor's
recorded facts (``FACT_FORM_TYPES``) as top-level fields; a fact that was not
observed stays absent, and a field with no recorded fact, or typed differently,
raises when the Episode is built.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import math
from types import MappingProxyType

from jsonschema import Draft202012Validator, ValidationError

from method_loop import Commission
from method_loop import ChildEpisodeUnit, ClosedRecord, Episode, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import REF, RECORD_SCHEMAS, ContractError, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.grading.partner_presence_evidence.progress_information_credit import ProgressInformationCredit
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.partner_presence_evidence.progress_provider import FIELDS

MODEL = 'model_provider'
STORE = 'store'
PROGRESS = 'a107_progress_provider'
REQUIRED_COLLABORATORS = (MODEL, STORE, PROGRESS)
_INTERFACES = MappingProxyType({
    MODEL: ('complete',),
    STORE: ('validate_scope', 'get'),
    PROGRESS: ('observe', 'read_progress', 'describe_target', 'direct_dependencies', 'resolve'),
})

EPOCH = 'monitor'
MODEL_ROLE = 'REASONING'
STATES = ('pending', 'executing', 'returned', 'admitted')
_TEXT = {'type': 'string', 'minLength': 1}
_REFS = {'type': 'array', 'items': REF, 'uniqueItems': True}
_OBSERVED_STATUSES = ('completed', 'partial', 'invalid', 'failed', 'unavailable')

# The parent's monitor assignment (monitor_assignment_v1).
ASSIGNMENT_SCHEMA = obj({
    'version': {'const': 'monitor_assignment_v1'}, 'target_handle': _TEXT,
    'requested_fields': {'type': 'array', 'items': {'enum': list(FIELDS)}, 'uniqueItems': True},
    'known_progress_refs': _REFS,
    'permitted_committed_record_types': {'type': 'array', 'uniqueItems': True,
                                         'items': {'enum': sorted(RECORD_SCHEMAS)}}})


class A107MonitorRuntimeError(ValueError):
    """A monitor collaborator, assignment or decision does not satisfy this binding's contract."""


@dataclass(frozen=True)
class MonitorRecord(ClosedRecord):
    """A plain JSON record: one unit's controller input, a request message or the monitor's result."""
    value: Mapping

    def as_record(self):
        return deepcopy(dict(self.value))


def collaborator(collaborators, name):
    """The named runtime collaborator, with the interface this module calls on it."""
    if name not in collaborators:
        raise A107MonitorRuntimeError('a107_monitor_collaborator_required:' + name)
    value = collaborators[name]
    for method in _INTERFACES[name]:
        if not callable(getattr(value, method, None)):
            raise A107MonitorRuntimeError('a107_monitor_collaborator_interface_required:' + name + ':' + method)
    return value


def store_scope(store, scope):
    """The assignment's scope, which must be exactly the scope the run's Store admits."""
    value = plain(scope)
    if plain(store.validate_scope(value)) != value:
        raise A107MonitorRuntimeError('a107_monitor_scope_must_be_store_admitted')
    return value


def monitor_assignment(provider, role_assignment, scope):
    """Admit the parent's monitor assignment: its schema, its target in scope, its baseline on that target."""
    value = plain(role_assignment)
    validate_schema(value, ASSIGNMENT_SCHEMA)
    if not provider.resolve(value['target_handle'], plain(scope), 'execution_handle'):
        raise ContractError('progress_target_unavailable_or_outside_scope')
    for reference in value['known_progress_refs']:
        if provider.read_progress(reference, plain(scope))['target_handle'] != value['target_handle']:
            raise ContractError('monitor_known_progress_target_mismatch')
    return value


def fact_sources():
    """The monitor's recorded report facts and their meanings."""
    definitions = {
        'monitoring_progress_refs': (
            {**_REFS, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'episode_progress'}},
            'Original delivered progress observation identities, including those delivered by dependency monitors.'),
        'monitoring_target_handle': (
            {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handle'},
            'The immutable assigned semantic target handle.'),
        'monitoring_execution_state': (
            {'type': ['string', 'null'], 'enum': [*STATES, None]},
            'Assigned target state in the latest delivered observation; unknown without an observation.'),
        'monitoring_result_available': (
            {'type': ['boolean', 'null']},
            'Assigned target result availability in the latest delivered observation.'),
        'monitoring_observed_at_unix_seconds': (
            {'type': ['number', 'null'], 'minimum': 0},
            'Original assigned-target observation time, converted from UTC without refreshing it.'),
        'monitoring_committed_record_refs': (
            {**_REFS, 'items': {'type': 'string', 'format': 'reference'}},
            'Parent-permitted committed records actually delivered in these progress observations.'),
        'monitoring_dependency_handles': (
            {'type': 'array', 'uniqueItems': True,
             'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handle'}},
            'Exposed direct dependencies in the latest delivered assigned-target observation; no descendant '
            'traversal.'),
    }
    return {name: {'type': schema['type'], 'meaning': meaning, 'report_schema': {**schema, 'x-source': name}}
            for name, (schema, meaning) in definitions.items()}


# The RecordForm field type of each recorded fact a parent's commissioned report form (C5) may add.
FACT_FORM_TYPES = MappingProxyType({
    'monitoring_progress_refs': 'list', 'monitoring_target_handle': 'text', 'monitoring_execution_state': 'text',
    'monitoring_result_available': 'boolean', 'monitoring_observed_at_unix_seconds': 'number',
    'monitoring_committed_record_refs': 'list', 'monitoring_dependency_handles': 'list'})


def commissioned_fact_fields(return_form, report_form):
    """The recorded facts a commissioned report form adds to the binding's return form, by name.

    A field the monitor records no fact for, or one typed differently from that fact, raises.
    """
    added = [name for name in report_form.fields if name not in return_form.fields]
    for name in added:
        if name not in FACT_FORM_TYPES:
            raise A107MonitorRuntimeError('a107_monitor_commissioned_report_field_has_no_source:' + name)
        spec = report_form.fields[name]
        if spec.type != FACT_FORM_TYPES[name] or spec.form is not None or spec.items is not None:
            raise A107MonitorRuntimeError('a107_monitor_commissioned_report_field_type_differs:' + name)
    return tuple(added)


def _timestamp_seconds(value):
    try:
        moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if moment.tzinfo is None or moment.utcoffset().total_seconds() != 0:
            raise ValueError
    except (ValueError, AttributeError) as error:
        raise ContractError('progress_utc_timestamp_required') from error
    return moment.timestamp()


def monitor_facts(provider, store, assignment, scope, received):
    """The monitor's recorded facts from the progress observations it received."""
    snapshots = [provider.read_progress(reference, plain(scope)) for reference in received]
    target = [row for row in snapshots if row['target_handle'] == assignment['target_handle']]
    latest = target[-1] if target else None
    permitted = set(assignment['permitted_committed_record_types'])
    committed = list(dict.fromkeys(reference for row in snapshots for reference in row['committed_record_refs']
                                   if store.get(reference)['record_type'] in permitted))
    return {'monitoring_progress_refs': list(received),
            'monitoring_target_handle': assignment['target_handle'],
            'monitoring_execution_state': latest['execution_status']['lifecycle_state'] if latest else None,
            'monitoring_result_available': latest['result_available'] if latest else None,
            'monitoring_observed_at_unix_seconds': _timestamp_seconds(latest['observed_at']) if latest else None,
            'monitoring_committed_record_refs': committed,
            'monitoring_dependency_handles': [row['handle'] for row in latest['dependencies']] if latest else []}


def tool_catalog():
    """The monitor's own progress tools."""
    return [
        {'name': 'progress.observe',
         'description': 'Observe selected exposed fields of your assigned target. Retain the original observation '
                        'identity when facts are unchanged. This operation never traverses dependent work.',
         'input_schema': obj({'requested_fields': deepcopy(ASSIGNMENT_SCHEMA['properties']['requested_fields'])})},
        {'name': 'progress.read', 'description': 'Read an already delivered exact progress observation.',
         'input_schema': obj({'progress_ref': REF})},
        {'name': 'progress.log',
         'description': 'Read one exact retained log window from an already delivered progress observation, '
                        'preserving source/artifact byte custody.',
         'input_schema': obj({'progress_ref': REF, 'log_index': {'type': 'integer', 'minimum': 0}})},
    ]


def action_schema(catalog, dependency_handles):
    """The closed decision form: one progress tool with its arguments, or one dependency monitor commission."""
    options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
               for entry in catalog]
    if dependency_handles:
        options.append(obj({'kind': {'const': 'monitor_dependency'},
                            'dependency_handle': {'enum': list(dependency_handles)}}))
    return obj({'selection': {'anyOf': options}})


ACTION_BOUNDARY = ('Do not emit a stop action or invent a turn budget, approval review, quality gate, experiment, '
                   'term or observation.\n')
CREDIT_GUIDANCE = ('current_credit is this monitor\'s information credit from the projector recorded in '
                   'credit_binding; it describes monitoring information, not biological truth.\n')
HOST_EXECUTION_GUIDANCE = 'Do not execute native provider tools. The host executes your selected action.\n'


def instructions(dependency_monitoring):
    """The monitor's goal and its decision boundary."""
    goal = ('Investigate which further exposed progress information is useful for the assigned target. Use actual '
            'status, measured quantities, committed references and source-bound logs. Liveness establishes process '
            'presence only; elapsed time alone establishes neither productive work nor a stall. Unknown information '
            'stays unknown. Earlier outcomes inform later decisions. ')
    if dependency_monitoring:
        goal += ('You may explicitly commission an ordinary monitor for one exposed direct job dependency '
                 '(kind monitor_dependency); no descendant traversal, fanout, cadence or depth is prescribed. ')
    goal += ('Your closure returns the recorded monitoring facts even while the target remains active. '
             "The monitor's information-credit projector and bound yield rule govern continuation. "
             'Repeated observation identities and read timestamps alone earn no new information.')
    return goal + '\n' + ACTION_BOUNDARY + CREDIT_GUIDANCE + HOST_EXECUTION_GUIDANCE


def received_snapshot(provider, assignment, scope, received, reference):
    """A progress observation this monitor received (or its assignment's baseline); any other raises."""
    if reference not in received and reference not in assignment['known_progress_refs']:
        raise ContractError('monitor_progress_not_received')
    return provider.read_progress(reference, plain(scope))


def progress_outcome(tool, arguments, operation_key, *, provider, store, assignment, scope, received):
    """Execute ``progress.observe`` or ``progress.read``: the observation and its parent-permitted committed records."""
    if tool == 'progress.observe':
        if not set(arguments['requested_fields']) <= set(assignment['requested_fields']):
            raise ContractError('monitor_observation_expands_requested_fields')
        snapshot = provider.observe(assignment['target_handle'], arguments['requested_fields'], plain(scope),
                                    permitted_committed_record_types=assignment['permitted_committed_record_types'],
                                    operation_key=operation_key)
    elif tool == 'progress.read':
        snapshot = received_snapshot(provider, assignment, scope, received, arguments['progress_ref'])
    else:
        raise A107MonitorRuntimeError('a107_monitor_tool_is_not_an_observation:' + repr(tool))
    permitted = set(assignment['permitted_committed_record_types'])
    committed = [reference for reference in snapshot['committed_record_refs']
                 if store.get(reference)['record_type'] in permitted]
    return {'status': 'completed', 'kind': 'tool',
            'operation_ref': identity('operation', {'key': operation_key, 'name': tool, 'arguments': arguments}),
            'record_refs': committed, 'changed_record_refs': [], 'progress_refs': [snapshot['progress_ref']],
            'result': plain(snapshot)}


async def log_window_outcome(arguments, operation_key, *, provider, store, tools, assignment, scope, received):
    """Execute ``progress.log``: one exact retained log window of a received observation, read from its source."""
    snapshot = received_snapshot(provider, assignment, scope, received, arguments['progress_ref'])
    if arguments['log_index'] >= len(snapshot['log_windows']):
        raise ContractError('monitor_log_window_unavailable')
    window = snapshot['log_windows'][arguments['log_index']]
    source = store.get(window['source_ref'])
    representation = next((name for name, field in (('original', 'artifact_ref'), ('text', 'text_ref'),
                                                    ('stdout', 'stdout_ref'), ('stderr', 'stderr_ref'))
                           if source.get(field) == window['artifact_ref']), None)
    if representation is None:
        raise ContractError('progress_log_source_artifact_mismatch')
    if window['start_byte'] == window['end_byte']:
        result = {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                  'result': {'source_ref': window['source_ref'], 'artifact_ref': window['artifact_ref'],
                             'start': window['start_byte'], 'end': window['end_byte'], 'text': ''}}
    else:
        result = await tools.execute_async(
            'source.read', {'source_ref': window['source_ref'], 'representation': representation,
                            'offset': window['start_byte'], 'limit': window['end_byte'] - window['start_byte']},
            scope=plain(scope), operation_key=operation_key, permitted_record_refs=[window['source_ref']])
    return {**plain(result), 'kind': 'tool', 'progress_refs': [snapshot['progress_ref']]}


async def execute_progress_tool(selection, operation_key, *, provider, store, tools, assignment, scope, received):
    """Execute one selected progress tool; an argument or reference failure is a returned invalid outcome."""
    tool, arguments = selection['tool'], selection['arguments']
    try:
        if tool == 'progress.log':
            return await log_window_outcome(arguments, operation_key, provider=provider, store=store, tools=tools,
                                            assignment=assignment, scope=scope, received=received)
        return progress_outcome(tool, arguments, operation_key, provider=provider, store=store,
                                assignment=assignment, scope=scope, received=received)
    except ContractError as error:
        return {'status': 'invalid', 'kind': 'tool', 'record_refs': [], 'changed_record_refs': [],
                'progress_refs': [],
                'feedback': {'category': 'arguments_or_reference', 'code': str(error),
                             **({'detail': error.detail} if error.detail else {})}}


class MonitorProgressSource:
    """Decide and execute the monitor's units; replay recorded decisions and outcomes on resume."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._model = collaborator(collaborators, MODEL)
        self._provider = collaborator(collaborators, PROGRESS)
        self._store = collaborator(collaborators, STORE)
        self._tools = binding.tool_registry
        if getattr(self._tools, 'store', None) is not self._store:
            raise A107MonitorRuntimeError('a107_monitor_tool_registry_is_not_over_the_run_store:'
                                          + binding.binding_path)
        builders = dict(child_builders)
        slot = binding.dependency_slot
        if set(builders) != ({slot} if slot is not None else set()):
            raise A107MonitorRuntimeError('a107_monitor_child_builders_differ_from_slots:' + binding.binding_path)
        self._dependency_builder = builders.get(slot) if slot is not None else None
        self.scope = store_scope(self._store, bound.assignment['scope'])
        self.assignment = monitor_assignment(self._provider, binding.role_assignment(bound.assignment), self.scope)
        self.credit = binding.information_credit(self._provider)
        self.catalog = tool_catalog()
        self.report_facts = commissioned_fact_fields(binding.return_form, bound.report_form)
        self.received = []
        self.units = 0
        self.last_outcome = None
        self.feedback = None

    def current_credit(self):
        return self.credit(self.scope, initial_progress_refs=self.assignment['known_progress_refs'],
                           known_progress_refs=self.received)

    def _receive(self, outcome):
        for reference in outcome['progress_refs']:
            if reference not in self.received:
                self.received.append(reference)
        # An executed outcome's own feedback (present on invalid/failed outcomes) replaces earlier feedback.
        self.feedback = outcome['feedback'] if 'feedback' in outcome else None
        self.last_outcome, self.units = outcome, self.units + 1

    def _restore(self, position):
        """Rebuild what the replayed units received from their recorded outcomes."""
        while self.units < position:
            self._receive(self._bound.recorder.recall('outcome.' + str(self.units)))

    def dependency_handles(self):
        """Exposed direct job dependencies of the target a dependency monitor may be commissioned for."""
        if self._dependency_builder is None:
            return []
        rows = self._provider.direct_dependencies(self.assignment['target_handle'], self.scope)
        return [row['handle'] for row in rows if row['kind'] == 'job']

    def decision_state(self, view, dependencies):
        credit = self.current_credit()
        return view.model_inputs({
            'goal': self._bound.request.goal.as_record(),
            'scope': self.scope,
            'monitor_assignment': self.assignment,
            'monitor_target_description': plain(self._provider.describe_target(self.assignment['target_handle'],
                                                                               self.scope)),
            'monitor_direct_dependencies': plain(self._provider.direct_dependencies(self.assignment['target_handle'],
                                                                                    self.scope)),
            'monitor_commissionable_dependencies': list(dependencies),
            'monitor_received_progress_refs': list(self.received),
            'monitor_information_meaning': 'Exposed direct relationships and already delivered observations. Empty '
                                           'measurements/log windows do not assert absence or a stall.',
            'monitor_goal': {'objective': self._bound.request.goal.as_record(),
                             'target_handle': self.assignment['target_handle'],
                             'requested_fields': self.assignment['requested_fields'],
                             'unresolved_question': 'Which exposed progress information would improve the original '
                                                    'requested report?',
                             'progress_definition': 'Actual received information under the monitoring projector; '
                                                    'repeated identities and timestamps alone earn no credit.',
                             'yield_settings': deepcopy(self._binding.yield_settings)},
            'tools': self.catalog,
            'last_local_outcome': self.last_outcome,
            'feedback': self.feedback,
            'current_credit': credit['credit'],
            'monitoring_information_credit': credit['monitoring_information_credit'],
            'monitoring_information_binding': credit['monitoring_information_binding'],
            'credit_binding': self.credit.as_record(),
            'controller': plain(view.controller_state.as_record()),
            'requested_report_purpose': (self._bound.request.report_contract.decision
                                         if self._bound.request.report_contract is not None else None),
            'available_report_facts': fact_sources(),
        }, reports=())

    async def _decide(self, position, attempt, view, schema, dependencies):
        """The recorded model decision for this attempt; the model is asked only when none is recorded."""
        async def ask():
            return await self._model.complete(
                self._bound.episode_id, MODEL_ROLE, instructions(self._dependency_builder is not None),
                self.decision_state(view, dependencies), schema)
        return await self._bound.recorder.recorded_async('decision.' + str(position) + '.' + str(attempt), ask)

    @staticmethod
    def _admit(response, schema):
        """The selection, or the rejection feedback (no unit) when the form is invalid."""
        try:
            Draft202012Validator(schema).validate(plain(response))
        except ValidationError as error:
            return None, {'status': 'invalid', 'category': 'action_contract', 'detail': error.message}
        return plain(response['selection']), None

    def _unit_input(self, position, outcome, label):
        credit = self.current_credit()['credit']
        return MonitorRecord({'credit': credit,
                              'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                              'decision_index': position, 'unit': label, 'status': outcome['status'],
                              'progress_refs': list(outcome['progress_refs'])})

    async def next(self, view):
        position = view.units_consumed
        self._restore(position)
        dependencies = self.dependency_handles()
        schema = action_schema(self.catalog, dependencies)
        attempt = 0
        while True:
            selection, feedback = self._admit(await self._decide(position, attempt, view, schema, dependencies),
                                              schema)
            if selection is not None:
                break
            self.feedback, attempt = feedback, attempt + 1
        if selection['kind'] == 'monitor_dependency':
            return self._dependency_unit(position, selection['dependency_handle'])
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position),
                                                            lambda: self.execute(selection, key))
        if outcome['status'] not in _OBSERVED_STATUSES:
            raise A107MonitorRuntimeError('a107_monitor_outcome_status_unknown:' + repr(outcome['status']))
        self._receive(outcome)
        unit = self._unit_input(position, outcome, selection['tool'])
        return Leaf(unit, extract=lambda value: value, result=lambda _, value: value,
                    label=selection['tool'] + ':' + str(position))

    def _dependency_unit(self, position, handle):
        """Commission one ordinary monitor of this kind for an exposed direct job dependency of the target."""
        builder, slot = self._dependency_builder, self._binding.dependency_slot
        role_assignment = {'version': 'monitor_assignment_v1', 'target_handle': handle,
                           'requested_fields': list(self.assignment['requested_fields']), 'known_progress_refs': [],
                           'permitted_committed_record_types':
                               list(self.assignment['permitted_committed_record_types'])}
        assignment = {**self._binding.child_assignment(self.scope, role_assignment),
                      **builder.assignment_form.declared}
        contract = self._binding.dependency_report_contract()
        goal = EpisodeGoal.child(self._bound.request.goal, objective=self._binding.goal, result_contract=contract)
        child = builder(slot + '_' + str(position),
                        Commission(EpisodeRequest(goal, MonitorRecord({'target_handle': handle}),
                                                  ReportContract(**contract)), assignment))
        field = self._binding.result_field

        def receive(result, completion, request):
            admitted = builder.admit(result)
            refs = admitted[field]['monitoring_progress_refs']
            if not isinstance(refs, list) or any(type(ref) is not str for ref in refs):
                raise A107MonitorRuntimeError('a107_dependency_monitor_report_requires_progress_refs')
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'monitor_dependency', 'status': 'completed', 'dependency_handle': handle,
                'record_refs': [], 'changed_record_refs': [], 'progress_refs': list(refs),
                'child_credit': admitted['credit'], 'child_completion': completion.as_record()})
            self._receive(outcome)
            return self._unit_input(position, outcome, 'monitor_dependency')

        def report(result, completion, request):
            return dict(builder.admit(result))
        return ChildEpisodeUnit(child, receive, report)

    async def execute(self, selection, operation_key):
        return await execute_progress_tool(selection, operation_key, provider=self._provider, store=self._store,
                                           tools=self._tools, assignment=self.assignment, scope=self.scope,
                                           received=self.received)

    def build_result(self, record):
        self._restore(record.units_consumed)
        credit = self.current_credit()['credit']
        if record.unit_records:
            recorded = record.unit_records[-1].controller_input.as_record()['credit']
            if recorded != credit:
                raise A107MonitorRuntimeError('a107_monitor_result_credit_differs_from_last_unit')
        finding = monitor_facts(self._provider, self._store, self.assignment, self.scope, self.received)
        # A fact the commissioned report form adds is supplied only when it was observed; an absent fact
        # stays absent and the runner's admission raises if the form requires it.
        added = {name: finding[name] for name in self.report_facts if finding[name] is not None}
        return MonitorRecord({'credit': credit, self._binding.result_field: finding, **added})


def _finite(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise A107MonitorRuntimeError(what + '_must_be_a_finite_number:' + repr(value))
    return float(value)


class A107MonitorRuntime:
    """The episode_runtime hooks of an A107 monitor binding (mixed in before the axis contract binding).

    The binding class declares ``dependency_slot`` (its monitor child slot, or
    ``None``), ``result_field`` (its return form's report field),
    ``role_assignment(assignment)`` (the monitor assignment inside its commission),
    ``child_assignment(scope, role_assignment)`` (the inverse, for a dependency
    monitor) and ``dependency_report_contract()``. Construction takes the monitor's
    information unit, its information-accumulation yield settings and its own tool
    registry (built by the A107 home factory over the run's shared Store), all required.
    """

    required_collaborators = REQUIRED_COLLABORATORS
    dependency_slot = None
    result_field = 'finding'

    def __init__(self, *, information_unit, yield_settings, tool_registry):
        if not callable(getattr(tool_registry, 'execute_async', None)):
            raise A107MonitorRuntimeError('a107_monitor_tool_registry_requires_execute_async')
        self.tool_registry = tool_registry
        self.information_unit = _finite(information_unit, 'a107_monitor_information_unit')
        if self.information_unit <= 0:
            raise A107MonitorRuntimeError('a107_monitor_information_unit_must_be_positive')
        settings = plain(yield_settings)
        if not isinstance(settings, dict) or set(settings) != {'kind', 'cutoff', 'uncertainty_alpha'} \
                or settings['kind'] != 'information_accumulation':
            raise A107MonitorRuntimeError('monitor_information_yield_settings_required')
        if _finite(settings['cutoff'], 'a107_monitor_cutoff') < 0 \
                or not 0 < _finite(settings['uncertainty_alpha'], 'a107_monitor_uncertainty_alpha') < 1:
            raise A107MonitorRuntimeError('monitor_information_yield_values_invalid')
        self.yield_settings = settings

    def as_record(self):
        return {'version': 'monitor_episode_binding_v2', 'binding_id': self.binding_path,
                'configuration': {'information_unit': self.information_unit,
                                  'yield_settings': deepcopy(self.yield_settings)}}

    def information_credit(self, progress_reader):
        return ProgressInformationCredit(progress_reader, information_unit=self.information_unit)

    def build_controller(self, bound, collaborators):
        """The monitor's information-accumulation yield controller, opened at the Episode's computed credit."""
        from yield_control import AccumulationYieldController, YieldParameters
        if bound.binding_path != self.binding_path:
            raise A107MonitorRuntimeError('a107_monitor_controller_opened_for_another_binding:'
                                          + bound.binding_path)
        provider = collaborator(collaborators, PROGRESS)
        scope = store_scope(collaborator(collaborators, STORE), bound.assignment['scope'])
        assignment = monitor_assignment(provider, self.role_assignment(bound.assignment), scope)
        initial = self.information_credit(provider)(scope, initial_progress_refs=assignment['known_progress_refs'],
                                                    known_progress_refs=())['credit']
        if not math.isfinite(initial):
            raise A107MonitorRuntimeError('a107_monitor_initial_credit_not_finite')
        return AccumulationYieldController(EPOCH, initial, self.yield_settings['cutoff'],
                                           YieldParameters(uncertainty_alpha=self.yield_settings['uncertainty_alpha']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        source = MonitorProgressSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.build_result)

    def restore_controller_input(self, record):
        return MonitorRecord(dict(record))


__all__ = ['ASSIGNMENT_SCHEMA', 'A107MonitorRuntime', 'A107MonitorRuntimeError', 'FACT_FORM_TYPES',
           'MonitorProgressSource', 'MonitorRecord', 'commissioned_fact_fields', 'REQUIRED_COLLABORATORS', 'action_schema', 'execute_progress_tool', 'fact_sources',
           'instructions', 'log_window_outcome', 'monitor_assignment', 'monitor_facts', 'progress_outcome',
           'received_snapshot', 'store_scope', 'tool_catalog']
