"""Root-owned workflow_values.py"""
from __future__ import annotations
from .task_action_units import ActionFailure
from .task_action_units import ActionLeaf
from gene_annotation_episode.episodic_workflow.root.method_loop import ChildEpisodeUnit
from gene_annotation_episode.episodic_workflow.root.method_loop import ClosedChildUnit
from gene_annotation_episode.episodic_workflow.root.method_loop import Context
from .decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.episodic_workflow.root.method_loop import DeferredUnit
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .report_facts import FACT_MEANINGS
from .report_facts import FACT_SOURCES
from gene_annotation_episode.episodic_workflow.root.method_loop.communication import ReportContract as GenericReportContract
from .episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.method_loop import Leaf
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.method_loop import PendingAction
from .task_values import Record
from .communication import ReportBoundaryError
from gene_annotation_episode.episodic_workflow.root.method_loop import ReportRedelivery
from types import SimpleNamespace
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import UnitRef
from .episode_journal import WorkflowError
from .task_values import _digest
from .task_values import _json
from .task_action_contracts import _object
from .task_values import _plain
from .wait_events import completed_action_context
from dataclasses import dataclass
from datetime import datetime
from . import execution_timing
from dataclasses import field
import inspect
import json
from .boundary_validation import parse_json_object
from .received_episode_yield import report_sources as runtime_report_sources
from datetime import timezone
import tomllib
from .communication import validate_closed_schema
from .communication import validate_form
EPISODE_BRANCH_LIFECYCLE = 'owned_child_turn_taking_v2'

def _now():
    return datetime.now(timezone.utc).isoformat()

def _annotation_child_roles(value):
    if value is not None and (not isinstance(value, tuple) or any((not isinstance(role, str) or not role.isidentifier() for role in value)) or len(set(value)) != len(value)):
        raise ValueError('explicit_unique_annotation_child_roles_required')
    return value

def _decision_protocol(value):
    if value not in (None, DECISION_EXCHANGE_PROTOCOL):
        raise ValueError('unsupported_decision_protocol')
    return value

class TypedReportContract(GenericReportContract):
    """The generic method boundary plus the actual typed domain form guard."""

    def __init__(self, decision, schema, reference_resolver, semantic_validator=None, *, recorded_admission=None):
        admitted = validate_closed_schema(schema)
        super().__init__(decision=decision, measurements={'schema': admitted}, information={key: value.get('description', key) for key, value in admitted['properties'].items()})
        object.__setattr__(self, 'reference_resolver', reference_resolver)
        object.__setattr__(self, 'semantic_validator', semantic_validator)
        object.__setattr__(self, 'recorded_admission', recorded_admission)

    @property
    def schema(self):
        return _plain(self.measurements['schema'])

    def admit(self, value, *, audit_identifiers):
        recorded = self.recorded_admission
        if recorded is not None and recorded(value) is not None:
            admitted = _plain(value)
        else:
            admitted = validate_form(value, self.schema, self.reference_resolver)
            if self.semantic_validator is not None:
                self.semantic_validator(admitted)
        try:
            if self.semantic_validator is not None:
                from .protein_structure_report_boundary import admit_recorded_protein_report, recorded_protein_fields
                fields = recorded_protein_fields(self.schema)
                if fields:
                    return admit_recorded_protein_report(self, admitted, fields=fields, audit_identifiers=audit_identifiers)
            return super().admit(admitted, audit_identifiers=audit_identifiers)
        except ValueError as error:
            raise ReportBoundaryError('Internal audit identity is unavailable in a scientific form', code='audit_identity') from error

def _array(item):
    return {'type': 'array', 'items': item}

def _wait_condition_schema():
    return _object({'version': {'type': 'string', 'const': 'event_condition_v1'}, 'events': _array(_object({'handle': {'type': 'string', 'minLength': 1}, 'event': {'type': 'string', 'enum': ['returned', 'state_changed', 'progress_committed']}, 'after_cursor': {'type': 'integer', 'minimum': 0}})), 'reconsider_at': {'type': ['string', 'null'], 'format': 'date-time'}})

def _wait_estimate_operation():
    return {'name': 'episode.estimate_wait', 'description': 'Inspect the supported estimate for a proposed wait using your received progress, original duration snapshots and completed own-action history. Unknown event probabilities and gains remain unknown. This tool selects no wait, timer, resource or work.', 'input_schema': _object({'condition': _wait_condition_schema()})}

def _embedded_tool_schema(schema):
    """Give local tool references an isolated resource when embedding them."""
    from gene_annotation_episode.schema_support import _schema_nodes
    schema = _plain(schema)
    if any((isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node) for _, node in _schema_nodes(schema))) and '$id' not in schema:
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + _digest(schema)}
    return schema

@dataclass(frozen=True)
class TimedChildUnit(ChildEpisodeUnit):
    journal: Journal
    parent_episode_id: str
    decision_index: int
    scheduled: bool = field(default=False, kw_only=True)

    def collection_measure(self):
        return self.journal.measure('runtime_actions', self.parent_episode_id, self.decision_index)

    def collection_returned(self):
        if self.scheduled:
            self.journal.commission_returned(self.parent_episode_id, self.decision_index)

    async def acquire_async(self, ctx):
        row = self.journal.row('runtime_actions', self.parent_episode_id, self.decision_index)
        if row['result'] is not None:
            if self.scheduled:
                self.journal.commission_returned(self.parent_episode_id, self.decision_index)
            return await super().acquire_async(ctx)
        with self.journal.measure('runtime_actions', self.parent_episode_id, self.decision_index):
            if self.scheduled:
                await self.journal.await_child_commission(self.parent_episode_id, self.decision_index)
            result = await super().acquire_async(ctx)
            if self.scheduled and (not isinstance(result, PendingAction)):
                self.journal.commission_returned(self.parent_episode_id, self.decision_index)
            return result

@dataclass(frozen=True, kw_only=True)
class ReportAcquisitionLeaf(ActionLeaf):
    report_delivery: ReportRedelivery

@dataclass(frozen=True, kw_only=True)
class DeferredActionUnit(DeferredUnit):
    decision_index: int

@dataclass(frozen=True, kw_only=True)
class OwnedChildActionUnit(DeferredActionUnit):
    collect: object

    def acquire(self, ctx):
        raise TypeError('owned child execution requires the async method loop')

    async def acquire_async(self, ctx):
        handle = self.dispatch(ctx)
        if inspect.isawaitable(handle):
            handle = await handle
        return await self.collect(ctx, handle)

@dataclass(frozen=True, kw_only=True)
class ReturnedActionUnit(ClosedChildUnit):
    decision_index: int

class ReleasingContext(Context):

    def leave(self, scope):
        super().leave(scope)
        self.runtime._controllers.pop(scope, None)

class ExecutionContextController:
    """Supply recorded context at the existing completed-own-action boundary.

    A child acquisition's parent timer closes before observe is called. Reading
    it inside the child's receive_result callback would record a running timer
    and make replay depend on when that callback happened to execute.
    """

    def __init__(self, controller, journal, episode_id, *, include_native=False, capture_current_completion=None):
        if capture_current_completion is not None and (not callable(capture_current_completion)):
            raise TypeError('completion_evidence_capture_must_be_callable')
        self.controller, self.journal, self.episode_id = (controller, journal, episode_id)
        self.include_native = include_native
        self.capture_current_completion = capture_current_completion
        self.epoch = controller.epoch

    def observe(self, unit_label, value, *, is_root):
        return self._observe(unit_label, value, is_root=is_root)

    def observe_unit(self, unit_label, value, *, unit_ref, is_root):
        if not isinstance(unit_ref, UnitRef) or unit_ref.episode_id != self.episode_id:
            raise ValueError('completion_observation_unit_identity_mismatch')
        return self._observe(unit_label, value, is_root=is_root, unit_ref=unit_ref)

    def _completion_packet(self, value, index, unit_ref):
        from .completion_evidence import validate_completion_evidence
        return validate_completion_evidence(value, run_id=self.journal.run_id, episode_id=self.episode_id, original_decision_index=index, unit_ref=unit_ref)

    def _observe(self, unit_label, value, *, is_root, unit_ref=None):
        body = value.as_record()
        index = body.get('estimation_action_index')
        if index is None:
            return self.controller.observe(unit_label, value, is_root=is_root)
        key = (self.journal.run_id, self.episode_id, index)
        old = self.journal.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? AND episode_id=? AND decision_index=?', key).fetchone()
        if old:
            context = json.loads(old[0])
            if context.get('completed_annotation_axis') != body.get('completed_annotation_axis'):
                raise ValueError('reconstructed_annotation_axis_completion_differs')
            if unit_ref is not None and 'current_completion_evidence' in context:
                self._completion_packet(context['current_completion_evidence'], index, unit_ref)
            practical = body.get('practical_completion')
            if practical is not None:
                expected = {**practical, 'action_index': index, 'unit_ref': unit_ref.as_record()}
                if context.get('practical_completion') != expected:
                    raise ValueError('reconstructed_practical_completion_context_differs')
        else:
            call = self.journal.row('runtime_model_calls', self.episode_id, index)
            action = self.journal.row('runtime_actions', self.episode_id, index)
            decision_context = json.loads(call['request'])['context']
            supplied = decision_context.get('execution_expectations')
            context = {'version': 'completed_action_estimation_context_v1', 'expectations': supplied, 'decision_time': execution_timing.snapshot(call['timing']), 'selected_work_time': execution_timing.snapshot(action['timing']), 'progress_time': execution_timing.capture_progress_time(self.journal, self.episode_id, original_decision_index=index)}
            if body.get('completed_annotation_axis') is not None:
                context['completed_annotation_axis'] = body['completed_annotation_axis']
            if self.include_native:
                context.update(version='completed_action_estimation_context_v2', native_expectations=decision_context.get('native_execution_expectations'))
            after = json.loads(action['result'])
            packet = None
            if unit_ref is not None and self.capture_current_completion is not None:
                packet = self._completion_packet(self.capture_current_completion(unit_ref, index, value), index, unit_ref)
            if 'pending_work' in decision_context and (after.get('pending_work_after_action') is not None or after.get('wait_outcome') is not None or packet is not None):
                support = decision_context.get('waiting_support', {})
                context = completed_action_context(context, pending_at_selection=decision_context['pending_work'], pending_after_action=after.get('pending_work_after_action'), wait_estimate_at_selection=after.get('wait_estimate'), wait_outcome=after.get('wait_outcome'), progress_records=support.get('progress_records', ()), duration_expectations=support.get('duration_expectations', ()), own_completed_action_history=support.get('own_completed_action_history', ()), local_return_history_at_selection=support.get('local_return_history'), current_completion_evidence=packet)
            elif packet is not None:
                context = completed_action_context(context, pending_at_selection=None, pending_after_action=after.get('pending_work_after_action'), current_completion_evidence=packet)
            if 'resource_tool_estimates' in decision_context or 'resource_tool_estimates' in after:
                context['resource_tool_estimates_at_selection'] = decision_context.get('resource_tool_estimates', [])
                context['resource_tool_estimates_after_action'] = after.get('resource_tool_estimates', [])
            if body.get('practical_completion') is not None:
                if unit_ref is None or packet is None:
                    raise ValueError('practical_completion_requires_actual_completed_unit')
                context['practical_completion'] = {**body['practical_completion'], 'action_index': index, 'unit_ref': unit_ref.as_record()}
            if body.get('hpc_continuation') is not None:
                context['hpc_continuation'] = body['hpc_continuation']
            self.journal.save('runtime_estimation_contexts', {'episode_id': self.episode_id, 'decision_index': index, 'data': _json(context)})
        return self.controller.observe(unit_label, Record({'credit': body['credit'], 'estimation_context': context}), is_root=is_root)

    def state(self):
        return self.controller.state()

    def transitioned(self, epoch):
        return type(self)(self.controller.transitioned(epoch), self.journal, self.episode_id, include_native=self.include_native, capture_current_completion=self.capture_current_completion)

class FeedbackEpisode(Episode):

    async def _source_end_async(self, ctx, scope, records):
        workflow = self.source.workflow
        if workflow.execution_binding is not None:
            while True:
                item = await workflow.next_branch_return(self.source, self._view(ctx, scope, records))
                if item is None:
                    break
                await self._acquire_unit_async(ctx, scope, records, item)
        await super()._source_end_async(ctx, scope, records)

    async def _stop_end_async(self, ctx, scope, records, step):
        workflow = self.source.workflow
        if workflow.execution_binding is not None:
            while step.stop:
                item = await workflow.next_branch_return(self.source, self._view(ctx, scope, records))
                if item is None:
                    break
                step = await self._acquire_unit_async(ctx, scope, records, item)
                if step is None:
                    raise WorkflowError('branch_return_requires_completed_original_action')
            if not step.stop:
                return (scope, None)
        return await super()._stop_end_async(ctx, scope, records, step)

    async def _acquire_unit_async(self, ctx, scope, records, item, *, unit_offset=0):
        try:
            self.source._selection_view = self._view(ctx, scope, records, unit_offset=unit_offset)
            if isinstance(item, ReportAcquisitionLeaf):
                self._redeliver_report(ctx, scope, records, item.report_delivery)
            return await super()._acquire_unit_async(ctx, scope, records, item, unit_offset=unit_offset)
        except ActionFailure as error:
            if not isinstance(item, Leaf):
                raise
            self.source.feedback = error.feedback
            current = ctx.runtime.state(scope)
            return SimpleNamespace(stop=current.decision.stop, requests_transition=False)

def common_fact_sources():
    """Exact host-owned common return types, available to every child role."""
    return {name: {'type': 'number' if name == 'credit' else 'array', 'meaning': FACT_MEANINGS[name], 'report_schema': {'type': 'number', 'x-source': name} if name == 'credit' else {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'x-source': name}} for name in sorted(FACT_SOURCES)}

def _compile_form(text, extra_sources=None, *, include_runtime_sources=True):
    schema = validate_closed_schema(parse_json_object(text))
    extra_sources = (runtime_report_sources() if include_runtime_sources else {}) | (extra_sources or {})

    def check(node, top=False):
        if 'x-source' in node and (not top or node['x-source'] not in FACT_SOURCES | extra_sources.keys()):
            raise ValueError('fact binding must name an available top-level source')
        if 'x-source' in node:
            expected = extra_sources[node['x-source']]['type'] if node['x-source'] in extra_sources else 'number' if node['x-source'] == 'credit' else 'array'
            expected = expected if isinstance(expected, list) else [expected]
            kinds = node['type'] if isinstance(node['type'], list) else [node['type']]
            if not set(expected) <= set(kinds):
                raise ValueError('fact binding has a different declared value type')
            if expected == ['array'] and node['x-source'] in FACT_SOURCES:
                item = node['items']
                item_kinds = item['type'] if isinstance(item['type'], list) else [item['type']]
                if 'string' not in item_kinds:
                    raise ValueError('recorded reference arrays require string reference items')
        for child in node.get('properties', {}).values():
            check(child)
        if 'items' in node:
            check(node['items'])
    for field in schema['properties'].values():
        check(field, top=True)
    return schema

def _effective_restoration_configuration(provider_config=None, restoration_settings=None, *, base=None):
    """Caller-owned transport preview configuration, never a work budget."""
    if base is None:
        from .provider_configuration import default_config_path
        base = tomllib.loads(default_config_path().read_text())['restoration']
    if not isinstance(base, Mapping):
        raise TypeError('restoration settings must be a mapping')
    effective = dict(base)
    supplied = {} if provider_config is None else provider_config
    configured = supplied.get('restoration', {})
    if not isinstance(configured, Mapping) or (restoration_settings is not None and (not isinstance(restoration_settings, Mapping))):
        raise TypeError('restoration settings must be a mapping')
    effective.update(configured)
    if restoration_settings is not None:
        effective.update(restoration_settings)
    if set(effective) != {'preview_size'}:
        raise ValueError('restoration settings must declare only preview_size')
    if type(effective['preview_size']) is not int or effective['preview_size'] < 0:
        raise ValueError('restoration preview_size must be a nonnegative integer')
    return effective

def _binding_name(callback, default):
    if callback is None:
        return default
    declared = callback if hasattr(callback, '__qualname__') else type(callback)
    return f'{declared.__module__}.{declared.__qualname__}'
