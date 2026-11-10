"""Shared method_loop binding for scoped, iterative reasoning improvements.

No biological departments, forced stages, model stop action or report composer.
The runtime journals selected work; the model owns scientific judgments; the
injected numerical controller owns continuation.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace
import uuid
import tomllib
import time

from jsonschema import Draft202012Validator, ValidationError
from method_loop import (ChildEpisodeUnit, ClosedChildUnit, DeferredUnit, ClosedRecord, Context, Episode,
    EpisodeGoal, EpisodeRecord, EpisodeRequest, EpisodeTree, Grain, Leaf,
    ReportDeliveryError, ReportRedelivery, PendingAction, SourceEnd)
from method_loop.archive import ArchivedRecord, JsonArchive
from method_loop.identities import EpisodeRef, UnitRef
from method_loop.communication import ReportContract as GenericReportContract
from .communication import (validate_closed_schema, validate_form,
    interpretation_schema, form_with_facts, ReportBoundaryError, REFERENCE_FORMATS)
from .boundary_validation import parse_json_object, schema_failure_diagnostic
from .domain import ContractError
from .acquisition import AcquisitionError
from . import execution_timing
from .execution_expectations import ExecutionExpectations, capture_execution_scopes
from .resource_estimation import (FORECAST_REFERENCE_FIELDS, ResourceToolEstimator, recorded_estimate,
    recorded_forecasts, validate_recorded_estimates, report_source as resource_report_source)
from .episode_reports import closing_yield, report_sources as runtime_report_sources
from .episode_receipts import EpisodeReceipts, RECEIPT_VERSION
from .native_timing_information import NativeTimingInformation, read_measurement, validate_native_measurements
from .run_statistics import ExecutionClass
from .tool_knowledge import ToolKnowledge, catalog as knowledge_catalog, INSTRUCTIONS as KNOWLEDGE_INSTRUCTIONS
from .launch_instructions import (LaunchInstructions, catalog as launch_instruction_catalog,
    INSTRUCTIONS as LAUNCH_INSTRUCTIONS)
from .episode_bindings import BindingContext, EpisodeBindingRegistry, native_job_event_configuration
from .episode_services import WorkflowServices
from .episode_application_services import EpisodeApplicationServices, service_binding, job_progress_binding
from .episode_journal import Journal, WorkflowError
from .episode_commissions import CommissionCoordinator
from .episode_completion import CompletionLedger, EFFECT_VERSION, observes_action_outcome
from .episode_admission import (ReceiverBindingV1, admit_return, load_return_admission,
    resolve_return_delivery)
from .waiting import WaitStore, estimate_wait, completed_action_context, validate_condition
from .wait_estimation_inputs import WaitInputs
from .local_return_history import LocalReturnHistory
from .decision_exchanges import DecisionExchanges
from .decision_history import lookup_schema, lookup_attempts, yield_table
from .decision_context import (PROTOCOL as DECISION_EXCHANGE_PROTOCOL,
    VERSION as DECISION_CONTEXT_VERSION, INSTRUCTIONS as DECISION_EXCHANGE_INSTRUCTIONS,
    model_snapshot, state_frame, instructional_model_context, apply_state_frame)
from .infernal_result_presentation import infernal_receiver_context
from .composition_information import (ROOT_BOUNDARY_VERSION, restricted_root,
    metadata_catalog as composition_catalog, lookup_schema as composition_lookup_schema,
    child_options as child_option_information, CONTRACT_INFORMATION_PROFILE,
    CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_OPERATIONS, requested_contract_information, is_contract_information)
from .episode_contract_information import (ContractInformationError, operation_contract_information,
    return_contract_information, expand_fact_form, validate_saved_fact_form)
from method_loop.durable import DurableExecutionStore, EventTargetError, canonical
from . import literature_numerical_contracts

EPISODE_BRANCH_LIFECYCLE = 'owned_child_turn_taking_v2'

def _plain(value):
    if hasattr(value, "as_record"):
        return _plain(value.as_record())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value

def _json(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)

def _digest(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()

def _now():
    return datetime.now(timezone.utc).isoformat()


def _annotation_child_roles(value):
    if value is not None and (not isinstance(value, tuple)
            or any(not isinstance(role, str) or not role.isidentifier() for role in value)
            or len(set(value)) != len(value)):
        raise ValueError('explicit_unique_annotation_child_roles_required')
    return value


def _recorded_annotation_child_roles(settings):
    if 'annotation_child_roles' not in settings:
        return None
    value = settings['annotation_child_roles']
    if not isinstance(value, list):
        raise ValueError('invalid_recorded_annotation_child_roles')
    return _annotation_child_roles(tuple(value))


def _decision_protocol(value):
    if value not in (None, DECISION_EXCHANGE_PROTOCOL):
        raise ValueError('unsupported_decision_protocol')
    return value


def _category_yield_parameters(controller_binding):
    """Read explicit yield operands from the supported controller layouts.

    This binds the separate category table's fit only. Caller identity wrappers
    add one declared definition layer; arbitrary custom definitions are not
    searched for numbers or interpreted as the existing yield controller.
    """
    if not isinstance(controller_binding, Mapping):
        return None
    definition = controller_binding.get('definition')
    if not isinstance(definition, Mapping):
        return None
    keys = ('window_size', 'subsample_size', 'uncertainty_alpha')
    if 'version' not in definition and 'uncertainty_alpha' in definition:
        parameters = definition
    else:
        versions = ('existing_yield_controller_explicit_parameters_v1',
                    'existing_yield_controller_explicit_role_costs_v2',
                    'existing_yield_controller_explicit_role_costs_v3')
        if definition.get('version') not in versions:
            definition = definition.get('definition')
        if not isinstance(definition, Mapping) or definition.get('version') not in versions:
            return None
        parameters = definition.get('parameters')
    if not isinstance(parameters, Mapping) or 'uncertainty_alpha' not in parameters:
        return None
    return {key: parameters[key] for key in keys if key in parameters}


_DEFAULT_DECISION_PROTOCOL = object()

class ActionFailure(WorkflowError):
    def __init__(self, feedback):
        self.feedback = feedback
        super().__init__(_json(feedback))


def _wait_target_feedback(error, *, status):
    return {"status": status, "category": "wait_target", "code": error.code,
        "affected_refs": list(error.affected_refs), "detail": str(error)}

@dataclass(frozen=True)
class Record(ClosedRecord):
    value: dict

    def as_record(self):
        return self.value

class TypedReportContract(GenericReportContract):
    """The generic method boundary plus the actual typed domain form guard."""

    def __init__(self, decision, schema, reference_resolver, semantic_validator=None, *, recorded_admission=None):
        admitted = validate_closed_schema(schema)
        super().__init__(decision=decision, measurements={"schema": admitted},
                         information={key: value.get("description", key)
                                      for key, value in admitted["properties"].items()})
        object.__setattr__(self, "reference_resolver", reference_resolver)
        object.__setattr__(self, "semantic_validator", semantic_validator)
        object.__setattr__(self, "recorded_admission", recorded_admission)

    @property
    def schema(self):
        return _plain(self.measurements["schema"])

    def admit(self, value, *, audit_identifiers):
        recorded = self.recorded_admission
        if recorded is not None and recorded(value) is not None:
            # Exact whole-form authority comes from the original successful
            # return and received projection, not a permissive ref resolver.
            admitted = _plain(value)
        else:
            admitted = validate_form(value, self.schema, self.reference_resolver)
            if self.semantic_validator is not None:
                self.semantic_validator(admitted)
        try:
            if self.semantic_validator is not None:
                from .protein_structure_report_boundary import (
                    admit_recorded_protein_report, recorded_protein_fields,
                )
                fields = recorded_protein_fields(self.schema)
                if fields:
                    return admit_recorded_protein_report(self, admitted, fields=fields,
                        audit_identifiers=audit_identifiers)
            return super().admit(admitted, audit_identifiers=audit_identifiers)
        except ValueError as error:
            raise ReportBoundaryError("Internal audit identity is unavailable in a scientific form",
                                      code="audit_identity") from error

def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}

def _array(item):
    return {"type": "array", "items": item}


def _wait_condition_schema():
    return _object({'version': {'type': 'string', 'const': 'event_condition_v1'},
        'events': _array(_object({'handle': {'type': 'string', 'minLength': 1},
            'event': {'type': 'string', 'enum': ['returned', 'state_changed', 'progress_committed']},
            'after_cursor': {'type': 'integer', 'minimum': 0}})),
        'reconsider_at': {'type': ['string', 'null'], 'format': 'date-time'}})


def _wait_estimate_operation():
    return {'name': 'episode.estimate_wait', 'description':
        'Inspect the supported estimate for a proposed wait using your received progress, original duration snapshots and completed own-action history. Unknown event probabilities and gains remain unknown. This tool selects no wait, timer, resource or work.',
        'input_schema': _object({'condition': _wait_condition_schema()})}

_ASSIGNMENT_TRANSPORT = 'atomic_composed_episode_assignment_json_v1'


def _action_generation_schema(schema, *, _legacy_episode_assignments=False):
    """Translate action JSON Schema; unlike return forms it includes goal text.

    Goals and tool input contracts are instructions into an episode, not its
    child-to-parent communication channel. The closed-form guard still applies
    independently to every commissioned report and its actual returned payload.
    """
    def translate(value):
        if isinstance(value, list):
            return [translate(item) for item in value]
        if not isinstance(value, dict):
            return value
        if _json_episode_assignment(value, composed=not _legacy_episode_assignments):
            properties = value['properties']
            return translate({**value, 'properties': {**properties, 'assignment': {
                'type': 'string', 'description': 'JSON encoding of the exact parent-selected episode '
                    'assignment. Preserve all supplied fields and values, including constraints, '
                    'allocations, input versions and selections. Preserve omitted fields and explicit '
                    'nulls. The host validates this complete original schema: ' + _json(properties['assignment'])}}})
        if _json_tool_arguments(value):
            properties = value['properties']
            requested_contract = value.get('x-argument-transport') == CONTRACT_ARGUMENT_TRANSPORT
            description = ('JSON encoding of the exact tool argument object. Preserve omitted fields and explicit '
                'nulls. Request this operation\'s authoritative complete argument contract as information when '
                'needed. The host validates the original complete standalone schema before execution.'
                if requested_contract else 'JSON encoding of the exact tool argument object. '
                    'Preserve omitted fields and explicit nulls. The host validates this complete '
                    'standalone JSON Schema before execution: ' + _json(properties['arguments']))
            transported = {key: item for key, item in value.items() if key != 'x-argument-transport'}
            transported = {**transported, 'properties': {**properties, 'arguments': {
                'type': 'string', 'description': description}}}
            return translate(transported)
        result = {key: _plain(item) for key, item in value.items()
                  if key not in ("uniqueItems", "pattern", "format", "x-source", "x-reference-namespace",
                                 'x-argument-transport')}
        # Traverse schema locations only. const/enum/default/examples can
        # contain arbitrary schema-looking data whose value must stay exact.
        for keyword in ('$defs', 'definitions', 'properties', 'patternProperties', 'dependentSchemas'):
            if isinstance(result.get(keyword), dict):
                result[keyword] = {name: translate(item) for name, item in result[keyword].items()}
        for keyword in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
            if isinstance(result.get(keyword), list):
                result[keyword] = [translate(item) for item in result[keyword]]
        for keyword in ('not', 'if', 'then', 'else', 'contains', 'propertyNames', 'items',
                        'additionalProperties', 'unevaluatedProperties', 'unevaluatedItems',
                        'additionalItems', 'contentSchema'):
            item = result.get(keyword)
            if isinstance(item, (dict, bool)):
                result[keyword] = translate(item)
            elif keyword == 'items' and isinstance(item, list):
                result[keyword] = [translate(child) for child in item]
        if "const" in result:
            result["enum"] = [result.pop("const")]
        if "enum" in result and "type" not in result:
            literals = result["enum"]
            if all(isinstance(item, str) for item in literals):
                result["type"] = "string"
            elif all(type(item) is int for item in literals):
                result["type"] = "integer"
        if result.get("type") == "object":
            properties = result.get("properties", {})
            # Durable contracts are canonicalized by key, which otherwise puts
            # arguments before the operation discriminator in strict output.
            # Let generation choose the action before producing its operands.
            # This changes presentation order only, not the admitted contract.
            first = ('response_type', 'kind', 'type', 'view', 'tool', 'role', 'domain', 'source',
                     'operation', 'selection')
            if {'terms', 'source_subjects', 'hypotheses', 'assessments',
                    'annotation_updates'} <= set(properties):
                # Match Store.commit_reasoning's dependency order: definitions
                # precede the hypotheses and assessments that reference them.
                first = ('structural_proposals', 'terms', 'source_subjects', 'contexts',
                         'observations', 'hypotheses', 'assessments',
                         'interpretation_accounts', 'annotation_updates')
            properties = {key: properties[key] for key in (
                *(key for key in first if key in properties),
                *(key for key in properties if key not in first))}
            required = set(value.get("required", []))
            result["properties"] = {key: (item if key in required else
                {"anyOf": [item, {"type": "null"}]}) for key, item in properties.items()}
            result["required"] = list(properties)
        return result
    return translate(schema)


def _json_episode_assignment(schema, *, composed=True):
    properties = schema.get('properties', {})
    kind, assignment = (properties.get(name) for name in ('kind', 'assignment'))
    return (isinstance(kind, dict) and kind.get('const') == 'episode_child'
            and isinstance(assignment, dict) and (assignment.get('type') == 'object'
                or composed and bool({'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef',
                                      '$recursiveRef'}.intersection(assignment))))


def _json_tool_arguments(schema):
    """Composed inputs retain their own JSON reference/presence semantics."""
    properties = schema.get('properties', {})
    kind = properties.get('kind')
    if not isinstance(kind, dict) or kind.get('const') != 'tool' or 'arguments' not in properties:
        return False
    if 'x-argument-transport' in schema:
        if (schema['x-argument-transport'] != CONTRACT_ARGUMENT_TRANSPORT
                or not isinstance(properties['arguments'], dict)
                or properties['arguments'].get('type') != 'object'):
            raise ValueError('unsupported_tool_argument_transport')
        return True
    from .schema_support import _schema_nodes
    keywords = {'allOf', 'anyOf', 'oneOf', '$ref', '$dynamicRef', '$recursiveRef',
                'if', 'then', 'else', 'dependentRequired', 'dependentSchemas', 'maxProperties'}
    return any(isinstance(node, dict) and keywords.intersection(node)
               for _, node in _schema_nodes(properties['arguments']))


def _embedded_tool_schema(schema):
    """Give local tool references an isolated resource when embedding them."""
    from .schema_support import _schema_nodes
    schema = _plain(schema)
    if any(isinstance(node, dict) and {'$ref', '$dynamicRef', '$recursiveRef'}.intersection(node)
           for _, node in _schema_nodes(schema)) and '$id' not in schema:
        schema = {**schema, '$id': 'urn:gene-annotation:tool-input:' + _digest(schema)}
    return schema

def _decode_action_response(value, schema, *, _legacy_episode_assignments=False):
    """Undo only the provider's optional-property representation.

    Strict structured output represents absent optional fields as null. A null
    is removed only where the original host contract made that field optional;
    required nulls remain invalid. Atomic assignment/argument objects preserve
    every supplied value. Historical expanded assignments use their original
    decoder only through explicit recorded-transport/selection verification.
    """
    def decode(item, contract):
        return _decode_action_response(item, contract,
            _legacy_episode_assignments=_legacy_episode_assignments)

    if not isinstance(schema, dict):
        return value
    if "anyOf" in schema:
        if isinstance(value, Mapping):
            tagged = []
            for option in schema['anyOf']:
                fields = option.get('properties', {}) if isinstance(option, dict) else {}
                tags = {key: field for key, field in fields.items()
                        if isinstance(field, dict)
                        and ('const' in field or len(field.get('enum', [])) == 1)}
                if tags and all(key in value and Draft202012Validator(field).is_valid(value[key])
                                for key, field in tags.items()):
                    tagged.append(option)
            if len(tagged) == 1:
                return decode(value, tagged[0])
        candidates = [decode(value, option) for option in schema["anyOf"]]
        for candidate, option in zip(candidates, schema["anyOf"]):
            if Draft202012Validator(option).is_valid(candidate):
                return candidate
        # Scientific rows can intentionally reach Store's partial-result path
        # while invalid under a host-only pattern. The declared action/type
        # discriminator still identifies their transport representation. Do not
        # leave optional transport nulls in place merely because a different
        # row is invalid, and do not infer a branch when tags are ambiguous.
        tagged = []
        if isinstance(value, Mapping):
            for candidate, option in zip(candidates, schema["anyOf"]):
                fields = option.get("properties", {}) if isinstance(option, dict) else {}
                tags = {key: field for key, field in fields.items()
                        if isinstance(field, dict)
                        and ("const" in field or len(field.get("enum", [])) == 1)}
                if tags and all(key in value and Draft202012Validator(field).is_valid(value[key])
                                for key, field in tags.items()):
                    tagged.append(candidate)
        if len(tagged) == 1:
            return tagged[0]
        return value
    if isinstance(value, dict) and schema.get("type") == "object":
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        encoded = _json_tool_arguments(schema)
        encoded_assignment = _json_episode_assignment(schema,
            composed=not _legacy_episode_assignments)
        return {key: (parse_json_object(item) if isinstance(item, str) else item)
                if encoded and key == 'arguments' or encoded_assignment and key == 'assignment'
                else decode(item, properties.get(key, {}))
                for key, item in value.items()
                if not (key in properties and key not in required and item is None)}
    if isinstance(value, list) and schema.get("type") == "array":
        return [decode(item, schema["items"]) for item in value]
    return value


def _recorded_action_generation_schema(generated, schema):
    """Match only the current and immediately preceding assignment transports."""
    return (_same_action_schema_required_members(generated, _action_generation_schema(schema))
        or _same_action_schema_required_members(generated,
            _action_generation_schema(schema, _legacy_episode_assignments=True)))


def _recorded_assignment_transport(saved):
    """Validate the private current-generator proof without inferring old data."""
    if 'assignment_transport' not in saved:
        return False
    if saved['assignment_transport'] != {'version': _ASSIGNMENT_TRANSPORT,
            'action_schema_sha256': _digest(saved['schema'])}:
        raise ValueError('original_assignment_transport_mismatch')
    return True


def _same_action_schema_required_members(left, right):
    """Only schema required-member order is lost by markerless serialization."""
    from .schema_support import _schema_nodes

    def normalized(value):
        value = _plain(value)
        for _, node in _schema_nodes(value):
            if not isinstance(node, dict) or 'required' not in node:
                continue
            members = node['required']
            if (not isinstance(members, list) or any(type(member) is not str for member in members)
                    or len(set(members)) != len(members)):
                return None
            node['required'] = sorted(members)
        return _json(value)

    original = normalized(left)
    return original is not None and original == normalized(right)


def _decode_recorded_action_response(value, schema, *, recorded_selection=None, exchanges=(),
        exchange_schema=None, unproven_replay=False):
    """Preserve an authoritative old selection without guessing absent values.

    A completed/selected action proves its entire original normalized selection.
    Before admission, an immutable matching exchange proves the original wire
    representation. The compatibility branch deliberately retains the old
    decoder, including its limits; it does not repair historical scientific data.
    """
    decoded = _decode_action_response(value, schema)
    if not isinstance(decoded, dict):
        return decoded

    def without_transport_proof():
        if unproven_replay:
            historical = _decode_action_response(value, schema, _legacy_episode_assignments=True)
            if _json(historical.get('selection')) != _json(decoded.get('selection')):
                raise ValueError('original_assignment_transport_unavailable')
        return decoded

    if recorded_selection is not None:
        if _json(decoded.get('selection')) == _json(recorded_selection):
            return decoded
        historical = _decode_action_response(value, schema, _legacy_episode_assignments=True)
        if _json(historical.get('selection')) == _json(recorded_selection):
            return historical
        raise ValueError('original_action_response_selection_mismatch')
    if not exchanges:
        return without_transport_proof()
    selected_schema = _object({'response_type': {'type': 'string', 'const': 'select_action'},
        **schema['properties']})
    selected_schema['required'] = ['response_type', *schema['required']]
    if exchange_schema is not None:
        # The frozen host copy preserves the exact schema used for dispatch.
        # Rebuilding from a live dict can reorder provider-required members.
        original = exchange_schema.get('properties', {}).get('response', {}).get('anyOf', [])
        if len(original) != 2 or _json(original[1]) != _json(selected_schema):
            raise ValueError('original_action_exchange_schema_mismatch')
    for row in exchanges:
        if not row.get('response_recorded') or not isinstance(row.get('response'), dict):
            continue
        original = row.get('response', {}).get('response', {})
        if (not isinstance(original, dict) or original.get('response_type') != 'select_action'
                or _json(original) != _json({'response_type': 'select_action', **value})):
            continue
        generated = row['request'].get('output_schema', {})
        if exchange_schema is not None:
            if _same_action_schema_required_members(generated, _action_generation_schema(exchange_schema)):
                return decoded
            if _same_action_schema_required_members(generated, _action_generation_schema(
                    exchange_schema, _legacy_episode_assignments=True)):
                return _decode_action_response(value, schema, _legacy_episode_assignments=True)
            continue
        alternatives = generated.get('properties', {}).get('response', {}).get('anyOf', [])
        if len(alternatives) == 2:
            if _same_action_schema_required_members(alternatives[1], _action_generation_schema(selected_schema)):
                return decoded
            if _same_action_schema_required_members(alternatives[1],
                    _action_generation_schema(selected_schema, _legacy_episode_assignments=True)):
                return _decode_action_response(value, schema, _legacy_episode_assignments=True)
    return without_transport_proof()

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
        row = self.journal.row("runtime_actions", self.parent_episode_id, self.decision_index)
        if row["result"] is not None:
            # Reconstructing recorded science is not another timed acquisition.
            if self.scheduled:
                self.journal.commission_returned(self.parent_episode_id, self.decision_index)
            return await super().acquire_async(ctx)
        with self.journal.measure("runtime_actions", self.parent_episode_id, self.decision_index):
            if self.scheduled:
                await self.journal.await_child_commission(self.parent_episode_id, self.decision_index)
            result = await super().acquire_async(ctx)
            if self.scheduled and not isinstance(result, PendingAction):
                self.journal.commission_returned(self.parent_episode_id, self.decision_index)
            return result


@dataclass(frozen=True, kw_only=True)
class ActionLeaf(Leaf):
    decision_index: int

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
        # Generic Context.leave releases the Episode but not its controller.
        # The closed record has its controller state; no closed controller is live.
        self.runtime._controllers.pop(scope, None)


class ExecutionContextController:
    """Supply recorded context at the existing completed-own-action boundary.

    A child acquisition's parent timer closes before observe is called. Reading
    it inside the child's receive_result callback would record a running timer
    and make replay depend on when that callback happened to execute.
    """
    def __init__(self, controller, journal, episode_id, *, include_native=False,
                 capture_current_completion=None):
        if capture_current_completion is not None and not callable(capture_current_completion):
            raise TypeError('completion_evidence_capture_must_be_callable')
        self.controller, self.journal, self.episode_id = controller, journal, episode_id
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
        return validate_completion_evidence(value, run_id=self.journal.run_id,
            episode_id=self.episode_id, original_decision_index=index, unit_ref=unit_ref)

    def _observe(self, unit_label, value, *, is_root, unit_ref=None):
        body = value.as_record()
        index = body.get('estimation_action_index')
        if index is None:
            return self.controller.observe(unit_label, value, is_root=is_root)
        key = (self.journal.run_id, self.episode_id, index)
        old = self.journal.db.execute("SELECT data FROM runtime_estimation_contexts "
            "WHERE run_id=? AND episode_id=? AND decision_index=?", key).fetchone()
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
            call = self.journal.row("runtime_model_calls", self.episode_id, index)
            action = self.journal.row("runtime_actions", self.episode_id, index)
            decision_context = json.loads(call["request"])["context"]
            supplied = decision_context.get('execution_expectations')
            context = {"version": "completed_action_estimation_context_v1", "expectations": supplied,
                "decision_time": execution_timing.snapshot(call["timing"]),
                "selected_work_time": execution_timing.snapshot(action["timing"]),
                "progress_time": execution_timing.capture_progress_time(self.journal,
                    self.episode_id, original_decision_index=index)}
            if body.get('completed_annotation_axis') is not None:
                context['completed_annotation_axis'] = body['completed_annotation_axis']
            if self.include_native:
                context.update(version='completed_action_estimation_context_v2',
                    native_expectations=decision_context.get('native_execution_expectations'))
            after = json.loads(action['result'])
            packet = None
            if unit_ref is not None and self.capture_current_completion is not None:
                packet = self._completion_packet(
                    self.capture_current_completion(unit_ref, index, value), index, unit_ref)
            if 'pending_work' in decision_context and (
                    after.get('pending_work_after_action') is not None or after.get('wait_outcome') is not None
                    or packet is not None):
                support = decision_context.get('waiting_support', {})
                context = completed_action_context(context,
                    pending_at_selection=decision_context['pending_work'],
                    pending_after_action=after.get('pending_work_after_action'),
                    wait_estimate_at_selection=after.get('wait_estimate'),
                    wait_outcome=after.get('wait_outcome'),
                    progress_records=support.get('progress_records', ()),
                    duration_expectations=support.get('duration_expectations', ()),
                    own_completed_action_history=support.get('own_completed_action_history', ()),
                    local_return_history_at_selection=support.get('local_return_history'),
                    current_completion_evidence=packet)
            elif packet is not None:
                # A historical/direct call can lack pending-work support.
                # Retain that missingness while supplying its actual current
                # identity and delivery, rather than recapturing selection.
                context = completed_action_context(context, pending_at_selection=None,
                    pending_after_action=after.get('pending_work_after_action'),
                    current_completion_evidence=packet)
            if 'resource_tool_estimates' in decision_context or 'resource_tool_estimates' in after:
                context["resource_tool_estimates_at_selection"] = decision_context.get('resource_tool_estimates', [])
                context["resource_tool_estimates_after_action"] = after.get(
                    "resource_tool_estimates", [])
            if body.get('practical_completion') is not None:
                if unit_ref is None or packet is None:
                    raise ValueError('practical_completion_requires_actual_completed_unit')
                context['practical_completion'] = {**body['practical_completion'],
                    'action_index': index, 'unit_ref': unit_ref.as_record()}
            if body.get('hpc_continuation') is not None:
                context['hpc_continuation'] = body['hpc_continuation']
            self.journal.save("runtime_estimation_contexts", {"episode_id": self.episode_id,
                "decision_index": index, "data": _json(context)})
        # The base controller still owns the only continuation rule. The child
        # estimator may use this context without changing the cumulative score.
        return self.controller.observe(unit_label,
            Record({"credit": body["credit"], "estimation_context": context}), is_root=is_root)

    def state(self):
        return self.controller.state()

    def transitioned(self, epoch):
        return type(self)(self.controller.transitioned(epoch), self.journal, self.episode_id,
            include_native=self.include_native, capture_current_completion=self.capture_current_completion)

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
        if (workflow.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
                and workflow.execution_binding is not None):
            # Yield ends selection of new work. Already selected child actions
            # still belong to this live branch and its original return boundary.
            # Suspension adds no action, observation or continuation decision.
            while step.stop:
                item = await workflow.next_branch_return(self.source, self._view(ctx, scope, records))
                if item is None:
                    break
                step = await self._acquire_unit_async(ctx, scope, records, item)
                if step is None:
                    raise WorkflowError('branch_return_requires_completed_original_action')
            if not step.stop:
                return scope, None
        return await super()._stop_end_async(ctx, scope, records, step)

    async def _acquire_unit_async(self, ctx, scope, records, item, *, unit_offset=0):
        try:
            self.source._selection_view = self._view(ctx, scope, records, unit_offset=unit_offset)
            if isinstance(item, ReportAcquisitionLeaf):
                self._redeliver_report(ctx, scope, records, item.report_delivery)
            return await super()._acquire_unit_async(ctx, scope, records, item,
                                                      unit_offset=unit_offset)
        except ActionFailure as error:
            if not isinstance(item, Leaf):
                raise
            self.source.feedback = error.feedback
            current = ctx.runtime.state(scope)
            # No new controller observation exists. Reuse its unchanged
            # continuation decision while returning actionable error feedback.
            return SimpleNamespace(stop=current.decision.stop, requests_transition=False)

REASONING_COMMIT_REQUIREMENT = (
    'A common scientific reason action needs at least one proposed commit row. '
    'A request with every commit section empty is rejected before acquisition '
    'and creates no completed-action observation. A return-form update alone '
    'does not make that request executable. Where the supplied action schema '
    'explicitly permits evidence_processing.kind=no_applicable_evidence, its '
    'source-grounded declaration is the existing exception. Keep current report '
    'references when the interpretation is unchanged; existing saved results '
    'require no empty reasoning action.'
)

INSTRUCTIONS = """You own an iterative scientific annotation improvement, not a tool itinerary.
Use the fixed caller material within the parent's fixed subject and optional original-coordinate
segments. Those bounds set this investigation's credit denominator; naming a new
candidate or interpretation cannot expand them. Consider the working
hypotheses, assumptions, prior results and biological/experimental context. Ask
what would usually support an explanation, when that cue could mislead, what
competing explanations remain, and which different outcomes would change your
interpretation. Revise your next useful work from actual outcomes.
Select one ordinary tool, one typed reasoning commitment based on available
existing evidence, or one substantive child improvement. A tool lookup alone is
not a child Episode. There are no biological departments or compulsory stages.
Reasoning owns scientific interpretation and selected work; only the numerical
controller owns scientific continuation. Do not emit a stop action or invent a
turn budget, approval review, quality gate, experiment, term or observation.
Text reading may produce typed extracted terms, source subjects, contexts and observations only with the
registered source, exact artifact byte span and quote, and actual source-subject
identity. An assay on a reference protein is not an assay on the input target.
image.view supplies actual selected pixels in visual_evidence to this reasoning
call. A plot or gel interpretation is a reasoned visual observation, not a
performed experiment or a literal text extraction. For that observation use
anchor=null and visual_anchor with the actual view_ref, image_artifact_ref and
pixel region (top-left x,y,width,height); source_ref is the view's display source.
The recorded origin distinguishes your interpretation. Preserve the actual
assayed source subjects and relevant text-anchored conditions. A selected image
alone establishes no biological role or target measurement.
For a scientific claim, examine the relevant primary methods, results and
qualifications to identify its actual subject, construct and conditions. A title,
search snippet or copied annotation label does not establish that claim. Use
source.read for the available pages; missing access is a limitation, not rejection.
When an outcome differs between relevant constructs or conditions, retain the
separate source-bound observations and conditions needed to interpret that
contrast. A reported negative with data not shown remains that reported result.
A global alignment's full coverage does not establish orthology, significance
or substrate specificity; consider what the actual comparison distinguishes.
A reasoned commitment can improve an annotation using existing evidence; a new
external measurement is not required. Private planning and report formatting are
not completed acquisitions. Retain alternatives and uncertainty rather than
copying a public target annotation or manufacturing precision.
current_evidence_vector contains the current projector's available component
values from the same projection as current_credit. Interpret these using the
recorded credit_binding; they describe the progress proxy, not biological truth.
When working_state.record_view is received_immutable_versions, its scientific
records are the versions delivered to this episode. received_revision_status
distinguishes their current revision membership; it does not assert their
scientific validity. Investigation-progress loss fields and episode.credit
provide current correction provenance. Ordinary state.query remains available
to discover or read other shared records explicitly.
For a received-scientific-finding progress binding, assessment.investigation_finding
records the actual source proposition and a typed qualification of its relevance
to the target hypothesis. Preserve the observed source subjects and conditions.
The selected observation must witness that source proposition. For example,
a sequence-identity alignment witnesses identity; it does not contain a family
annotation read in another source. Record that other source's actual assertion
as a source-bound observation and retain the alignment as supporting identity
evidence. Source annotations remain reported predictions, not measured target
function. Preserve the source's term category, including domain versus family.
A useful negative or nontransferability finding can remain retained information;
withdrawn means the finding itself is no longer valid, with its declared reason.
Repeated wording, quotations or opinion-only revisions do not make new findings.
An article table and its supplement can report the same underlying observation.
Keep each representation's actual source, subjects and quotation, but do not
count the same source proposition, target question and qualification again merely
because its source records or condition labels differ. When you establish that
two representations express the same source proposition, declare
same_source_claim_as_ref using the earlier assessment reference. That link shares
the source-claim identity only: an unchanged qualification must also retain its
established context_refs and assumption_refs. A new context record naming the
same condition is not by itself a new qualification. Preserve genuinely different
conditions, observations and qualifications; matching labels, rounded values or
a shared publication alone do not establish equivalence. Determining what is the
same remains part of your scientific reasoning. The host does not make that
judgment or require a separate review. Additional source reading is not a new
finding unless it adds or corrects information relevant to the target question.
When correcting an earlier finding's subject, partner, construct or other
reference binding, use replaces_refs to identify the earlier target assessment
being repaired. same_source_claim_as_ref shares source-claim identity; it does
not retire that earlier target finding. A different reference handle for the
same source-established role does not by itself make another biological question.
Keep the actual role/material identities and their witnesses distinct; declare
replacement when the corrected binding supersedes the earlier finding, rather
than retaining both representations as additional information. Preserve genuinely
different questions and unresolved identity instead of equating entities by name.
When annotation_score is supplied, it is a separate annotation-support measure
with its own annotation_score_binding and annotation_evidence_vector. Useful new
information can lower annotation support while advancing investigation progress.
When proposed_annotations is supplied, each proposed annotation and subject has
its own score and evidence vector. annotation_comparisons keeps best scored
alternatives, ties and unscored candidates for the same subject and question.
You retain the annotation decision and choose the next action.
The recorded task credit supplies this episode's numerical yield observations.
When current_credit.mode is annotation_axis_credit, controller.arms supplies
each proposed annotation/axis credit, forecast, cutoff and transfer status.
controller.annotation_credits totals received child credit per proposed annotation;
controller.root_score is the largest such total. This is investigation progress,
while proposed_annotations carries the separate signed functional-support scores.
Each forecast concerns another whole axis invocation; a child's internal next
action forecast is different. Choose an axis and its proposed_annotation_ref.
The root stops only when every pair's available upper bound is at or below its
own cutoff. Unknown scores or forecasts are not measured zeros. Coordinate
unresolved transfer dependencies through the existing shared-information tools.
Each child task must declare the credit calculation used for its own stopping decision.
For an A105, A106 or A108 whole-axis investigation, include context.evidence_task
with version evidence_axis_task_v1, kind whole_axis_findings, its evidence_axis,
and the credit_unit from that task's configured credit_definition. Its task key is
<axis>:whole_axis_findings. Do not copy another axis's unit or cutoff, or commission
a separate episode merely to calculate A106/A108 scores.
resource_tool_estimates, when supplied, describe expected execution time and
configured resources for the declared execution classes. Use these expectations
with your own yield estimate and prior outcomes to choose useful work. A timing
experiment earns monitoring credit for timing information learned and updates
execution expectations. Missing history means duration is unknown. Job elapsed
time and the duration of an own monitoring action are distinct measurements.
Define local rows with a bare alias, for example {"alias":"role"}, and use
"@role" to reference an earlier successful row within this same commit. Later
commits use the returned persistent IDs, not aliases from earlier commits.
Sections resolve in this order: structural_proposals, terms, source_subjects,
contexts, observations, hypotheses, assessments, interpretation_accounts,
annotation_updates. An interpretation_account records your coherent evidence
interpretation with runtime-bound episode ownership and assigned scope. It does
not replace the parent's annotation. A binding admitting these accounts uses
the same source-linked projection; copying an existing account adds no progress.
Parent annotation integration remains a separate reasoning decision. After a
partial result, read aliases and errors; independent successful rows persist.
context_refs permits context or hypothesis records, not sources, protein/profile
references or features. condition_refs permits context, hypothesis, observation
or term records. assumption_refs permits only hypotheses. Do not invent contexts
to make a source citation fit. Extracted labels and context names must occur
literally in the exact anchored quote; e.g. DUF8182 is different from the composed
label DUF8182 (Pfam PF26554). Retain identifiers and qualifications separately.
For applicability, distinguish what an observation measures directly from what
you infer for this particular hypothesis. Sequence identity establishes sequence
equivalence; a reference's predicted functional label remains a prediction when
transferred to that sequence. Preserve the source assertion and its dependencies.
Each assessment explicitly chooses extent_basis. observed_extent projects only
the observation's measured input/source extent; optional target_footprint can
restrict it. inferred_extent records a non-direct reasoned attribution to an
explicit bounded target_footprint independently of source coordinates. Preserve
the actual source subjects and measurements. Missing inferred target_footprint
keeps the assessment recorded but supplies no invented target extent; the
completed commit returns a notice naming that assessment and missing field.
direct applicability and inferred_extent are contradictory representations.
For a nonmolecular sample/handling/physiology interpretation, context_allocation
retains actual source subjects, observation kind and applicability while binding
its contribution to fixed original material positions. Supply nonempty immutable
context_account_scope for lineage identity, and context_scope for actual allocated
positions. The latter may be {"subject_refs":[]} to withdraw only that allocation;
missing allocation stays unlocalized with a notice. A context annotation uses
whole_input_context and the actual sample/context subject; it has no invented
physical sequence footprint. Frozen same-library read selections union in these
masks, not in Episode scopes. Each revision must own both prior and proposed
allocations; the immutable domain alone grants no edit permission. Reuse the same
account domain and expected_revision when correcting an existing allocation.
A commissioned child returns ONLY the parent's typed form. Fill report_update
inside this existing reasoning response. It describes your actual interpretation
of the supplied state BEFORE the selected next action. The result of a later tool
has not thereby been interpreted. At yielding, recorded fact fields describe
actual work, while interpretive fields retain their latest actual basis; prefer
actual assessment/annotation references where those express the requested meaning.
requested_report_purpose is the parent's actual information need. current_report_update
contains the latest admitted interpretation fields, initially the parent's supplied
initial values. Those initial values are not a new child judgment. Preserve their
declared meanings when revising the form; neither input chooses your scientific action.
As parent, request source-bound outcome and basis fields when needed to distinguish
new observations from prior interpretations. There is no separate report composer.
A report_delivery_failure is operational feedback about an already completed
child. You can select redeliver_report with a revised closed contract, using the
delivery_ref shown in report_deliveries or report_delivery_failure. It reuses
saved facts and exactly the child's existing interpretation fields; it performs
no new scientific work and cannot answer a new interpretive question. Do not
recommission the same investigation merely to fix its representation.
On a fresh provider conversation, restored_episode_history is a bounded index
of your own actual prior decisions, not a generated scientific summary. Use the
ordinary episode.history tool when an older selected action, exact outcome or
admitted direct-child form matters. Its indices belong only to this Episode;
another Episode's same index names different work. A failed saved outcome stays
failed. Where the journal retained a pre-execution rejection, its status is
rejected and view=records supplies the original rejection_feedback separately
from an executed outcome. Reading history does not execute that work again.
A selected history read is one ordinary action with its actual zero or changed progress, while
automatic context restoration creates no completed action. Current report
values retain their actual current_report_basis_refs, not a later tool result.
Do not execute native provider tools. The host executes your selected action.
"""

FACT_SOURCES = {"credit", "subject_refs", "committed_record_refs", "changed_record_refs",
                "changed_annotation_refs", "changed_assessment_refs", "changed_interpretation_account_refs", "last_outcome_refs",
                "interpretation_basis_refs", "observations_after_report_basis"}
FACT_MEANINGS = {
    "credit": "Projected credit at child completion for its fixed assigned scope; redelivery preserves that snapshot.",
    "subject_refs": "Original input subjects assigned by the parent.",
    "committed_record_refs": "Semantic records returned by completed own work and completed child investigations.",
    "changed_record_refs": "New or revised semantic records explicitly identified as changed by recorded work.",
    "changed_annotation_refs": "Actual changed annotation revision references from completed work, filtered by semantic record type.",
    "changed_assessment_refs": "Actual changed assessment revision references from completed work, filtered by semantic record type.",
    "changed_interpretation_account_refs": "Actual changed episode-owned coherent interpretation accounts; these are not parent annotation revisions.",
    "last_outcome_refs": "Semantic records returned by the last completed own ordinary action.",
    "interpretation_basis_refs": "Semantic references visible to the last admitted report interpretation response and available at this report boundary, including source-window custody and admitted typed forms. A visible handle does not establish that its full record or source body was read.",
    "observations_after_report_basis": "Last ordinary-action observations not supplied to that interpretation response.",
}


def common_fact_sources():
    """Exact host-owned common return types, available to every child role."""
    return {name: {'type': 'number' if name == 'credit' else 'array',
        'meaning': FACT_MEANINGS[name],
        'report_schema': ({'type': 'number', 'x-source': name} if name == 'credit' else
            {'type': 'array', 'items': {'type': 'string', 'format': 'reference'}, 'x-source': name})}
        for name in sorted(FACT_SOURCES)}


def _references_in(value, record_lookup, *, forms=(), reference_subset=None):
    """Index visible semantic handles without loading source/artifact contents.

    Working state and host outcomes use declared reference positions; full
    record projections also carry id/record_type. Native payloads' untyped id
    fields and ordinary text are not semantic declarations. Direct-child form
    fields have parent-chosen names, so their admitted schema supplies the type.
    Indexed record lookups establish identity; archived contexts and referenced
    source/artifact contents are not loaded. Only existing handles enter it.
    """
    found, seen, records = [], set(), {}
    def add(reference, record_type=None):
        if not isinstance(reference, str):
            return
        if reference not in records:
            try:
                records[reference] = record_lookup(reference)
            except (KeyError, ValueError):
                records[reference] = None
        record = records[reference]
        if (not isinstance(record, Mapping) or record.get("id") != reference
                or record.get("record_type") == "collection_member"
                or (record_type is not None and record.get("record_type") != record_type)):
            return
        if reference not in seen:
            found.append(reference)
            seen.add(reference)
    def walk(item):
        if isinstance(item, Mapping):
            if isinstance(item.get("record_type"), str):
                add(item.get("id"), item["record_type"])
            for key, child in item.items():
                if key == "ref" or key.endswith("_ref"):
                    add(child)
                elif key == "dependencies" or key.endswith("_refs"):
                    if isinstance(child, (tuple, list)):
                        for reference in child:
                            add(reference)
                walk(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                walk(child)
    def form_references(item, schema):
        if isinstance(item, Mapping):
            for key, child in item.items():
                node = schema.get("properties", {}).get(key)
                if node is not None:
                    form_references(child, node)
        elif isinstance(item, (tuple, list)):
            node = schema.get("items")
            if node is not None:
                for child in item:
                    form_references(child, node)
        elif schema.get("format") in REFERENCE_FORMATS:
            add(item)
    walk(value)
    for payload, schema in forms:
        form_references(payload, schema)
    if reference_subset is None:
        return found
    admitted = set(reference_subset(found))
    return [ref for ref in found if ref in admitted]


def _compile_form(text, extra_sources=None, *, include_runtime_sources=True):
    schema = validate_closed_schema(parse_json_object(text))
    extra_sources = (runtime_report_sources() if include_runtime_sources else {}) | (extra_sources or {})
    def check(node, top=False):
        if "x-source" in node and (not top or node["x-source"] not in FACT_SOURCES | extra_sources.keys()):
            raise ValueError("fact binding must name an available top-level source")
        if "x-source" in node:
            expected = (extra_sources[node["x-source"]]["type"] if node["x-source"] in extra_sources
                        else "number" if node["x-source"] == "credit" else "array")
            expected = expected if isinstance(expected, list) else [expected]
            kinds = node["type"] if isinstance(node["type"], list) else [node["type"]]
            if not set(expected) <= set(kinds):
                raise ValueError("fact binding has a different declared value type")
            if expected == ["array"] and node["x-source"] in FACT_SOURCES:
                item = node["items"]
                item_kinds = item["type"] if isinstance(item["type"], list) else [item["type"]]
                if "string" not in item_kinds:
                    raise ValueError("recorded reference arrays require string reference items")
        for child in node.get("properties", {}).values():
            check(child)
        if "items" in node:
            check(node["items"])
    for field in schema["properties"].values():
        check(field, top=True)
    return schema


class DecisionSource:
    def __init__(self, workflow, path, request, scope):
        self.workflow, self.path, self.request, self.scope = workflow, path, request, scope
        self.episode_id = Episode.identity(workflow.context, workflow.grains[path[-1][0]],
            path[-1][1], parent_path=path[:-1]).episode_id
        self.calls = 0
        self.feedback = None
        self.last_outcome = None
        self.last_outcome_index = None
        self.report_values = _plain(request.message.as_record()["initial_report"])
        self.report_basis = []
        self._restored = False
        self._unfinished_own_actions = []
        self._source_revision = None
        self._latest_effect_index = None
        self._restored_source_state = None
        self._model_snapshot = None
        self._presented_conversation_key = None
        self._selection_view = None
        self._delivery_resolution_ref = None
        self._execution_context = None
        self._suspension_condition = None
        self._inprocess_replay_ready = False
        self.interpret_schema = (interpretation_schema(request.report_contract.schema)
                                if request.report_contract else _object({}))

    def bind_execution_context(self, context):
        self._execution_context = context

    def suspension_changed(self, condition):
        self._suspension_condition = condition
        if self.workflow.execution_handle is not None:
            self.workflow.execution_backend.set_suspension(self.workflow.execution_handle,
                None if condition is None else {'episode_id': self.episode_id,
                    'dependency': condition})

    def record_execution_failure(self, error, *, unit=None):
        from .episode_source_failure import record_source_failure
        import traceback
        diagnostic = self.workflow.archive.store(Record({'exception_type': type(error).__name__,
            'traceback': traceback.format_exc()}))
        index = getattr(unit, 'decision_index', None)
        failure = record_source_failure(self.workflow.store, self.workflow.run_id,
            self.episode_id, index if index is not None else max(0, self.calls - 1), error,
            category='episode_execution', cause_code='selected_operation_failed')
        self.feedback = {**failure, 'diagnostic_ref': str(diagnostic.path)}
        action = (None if index is None else
            self.workflow.journal.row('runtime_actions', self.episode_id, index))
        if (action is not None and action['result'] is None
                and json.loads(action['action']).get('kind') in {'tool', 'reason'}):
            selection = json.loads(action['action'])
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
                'feedback': self.feedback}
            with self.workflow.store.transaction():
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id,
                    'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': None})
                credit = self.workflow.source_credit_view(self)['credit']
                value = self.workflow.controller_value(self, index, credit)
                self.workflow.journal.save('runtime_actions', {'episode_id': self.episode_id,
                    'decision_index': index, 'action': action['action'], 'result': _json(outcome), 'credit': credit})
                if self.workflow.execution_binding is not None:
                    self.workflow.completions.stage(self.episode_id, index,
                        label=f"{selection['kind']}:{index}", kind='own_action',
                        controller_input=value, child_return=None)
            self.last_outcome, self.last_outcome_index = outcome, index
            self.checkpoint()
            return ActionLeaf(selection, extract=lambda _: value, result=lambda _, result: result,
                label=f"{selection['kind']}:{index}", decision_index=index)
        self.checkpoint()

    async def call(self, context, schema):
        index, self.calls = self.calls, self.calls + 1
        journal = self.workflow.journal
        row = journal.row("runtime_model_calls", self.episode_id, index)
        if (row is None or row['response'] is None) and self.path[-1][0] == 'scientific_process':
            self.workflow.scientific_process_binding.validate_execution_context(
                self.workflow.binding_context(self))
        profile = self.workflow.contract_information_profile(self)
        if row:
            saved = json.loads(row["request"])
            if row["purpose"] != "decision":
                raise WorkflowError("saved decision contract differs from reconstruction")
            # Historical and interrupted decisions retain the actual contract
            # supplied at dispatch. Additions to today's tool catalog belong to
            # new decisions, not retrospective reconstruction of earlier ones.
            schema = saved["schema"]
            context = saved["context"]
            try:
                recorded_transport = _recorded_assignment_transport(saved)
            except ValueError as error:
                raise WorkflowError(str(error)) from error
            if (profile is None) != ('contract_information' not in saved):
                raise WorkflowError('original_contract_information_profile_changed')
            if profile is not None:
                self.workflow.validate_contract_information(saved)
            if literature_numerical_contracts.SAVED_MEMBER in saved:
                if profile is not None:
                    raise WorkflowError('original_literature_numerical_profile_mismatch')
                literature_numerical_contracts.validate_frozen_contracts(saved)
            if (self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL
                    and saved.get('decision_protocol') != DECISION_EXCHANGE_PROTOCOL):
                raise WorkflowError('pending_decision_requires_original_protocol')
            if row["response"] is not None:
                self._unproven_direct_response_index = (index if self.workflow.decision_protocol is None
                    and not recorded_transport else None)
                if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
                    if profile is not None:
                        self.validate_contract_exchange_history(saved, index)
                    context = self.interpretation_context(context,
                        self.workflow.decision_exchanges.rows(self.episode_id, index))
                return json.loads(row["response"]), index, context, schema
        else:
            # Selected manuals are exact immutable assignment operands. Supply
            # their bodies only to new calls; saved calls above keep the context
            # originally dispatched, including an interrupted request.
            resource_context = self.workflow.resource_context(self)
            if resource_context is not None:
                context = {**context, 'resource_context': resource_context}
            shared_context = self.workflow.shared_information_context(self)
            if shared_context is not None:
                context = {**context, 'shared_information_context': shared_context}
            from .component_axis_source_access import decision_context as source_access_context
            source_access = source_access_context(self.workflow, self.workflow.binding_context(self))
            if source_access is not None:
                context = {**context, 'component_axis_source_access': source_access}
            context = {**context,
                'launch_instruction_library': self.workflow.launch_instructions.context()}
            selected_instructions = self.workflow.launch_instructions.materialize(
                self.request.message.as_record().get('episode_assignment', {}).get('launch_instructions'))
            if selected_instructions is not None:
                context['selected_launch_instructions'] = selected_instructions
            if self.workflow.available_child_roles(self):
                context['child_options'] = child_option_information(self.workflow, self)['text']
            supplied_initial = self.workflow.episode_bindings.initial_decision_context(
                self.workflow.binding_context(self))
            if set(supplied_initial).intersection(context):
                raise ValueError('initial_binding_context_field_conflict')
            context = {**context, **supplied_initial}
            # Receiver-specific native views are supplied above. Build the
            # factual work/credit report only after those authorized results
            # are available; saved calls retain their original context.
            work_results = context.pop('_completed_work_axis_results', {})
            if ('literature_completed_work' not in context and not (
                    isinstance(context.get('current_credit'), Mapping)
                    and context['current_credit'].get('mode') == 'annotation_axis_credit')):
                from .episode_work_report import completed_action_reports
                context['completed_action_reports'] = completed_action_reports(
                    self.workflow, self, context, before=index,
                    received_axis_results=work_results)
            from .hpc_prompt import is_hpc_context
            if is_hpc_context(context):
                from .episode_work_report import requested_action_history
                context['requested_action_history'] = requested_action_history(
                    self.workflow, self, before=index)
            if 'pending_work' not in context:
                # Direct caller dispatches need the same authoritative
                # outstanding-work input as next(). Saved decisions above
                # retain the exact original context instead.
                context = {**context, 'pending_work': self.workflow.pending_work(self)}
            binding = self.workflow.execution_expectations
            if binding is not None and binding.applies(self.path[-1][0]):
                planning_scopes = ()
                if (self.path[-1][0] in binding.planning_roles
                        and self.workflow.job_episodes is not None):
                    jobs = self.workflow.job_episodes
                    if 'search_modes' in jobs.jobs.config:
                        options = jobs.prospective_execution_options(self.workflow.store, self.scope)
                        planning_scopes = list({value['execution_class'].ref: value['execution_class']
                                                for value in options}.values())
                        context = {**context, 'job_execution_options': [
                            {key: value[key] for key in ('query_ref', 'cpu', 'search_mode')}
                            | {'execution_class_ref': value['execution_class'].ref}
                            for value in options]}
                    else:
                        planning_scopes = jobs.prospective_execution_classes(self.workflow.store, self.scope)
                context = {**context, "execution_expectations": binding.capture(self.path[-1][0],
                    assignment=self.request.message.as_record().get("job_assignment"),
                    planning_scopes=planning_scopes)}
            if self.workflow.resource_estimator is not None:
                if self.workflow.is_job_source(self):
                    estimates = self.workflow.resource_estimator.estimate(
                        context.get("execution_expectations"),
                        job_ref=self.workflow.job_episodes.assignment(self)["job_ref"],
                        sample=self.workflow.job_episodes.latest_sample(self, include_inherited=True))
                elif "execution_expectations" in context:
                    # Supply expected execution costs before the owning episode
                    # chooses work. These classes describe proposed execution.
                    estimates = self.workflow.resource_estimator.estimate_context(
                        context["execution_expectations"])
                else:
                    estimates = None
                if estimates is not None:
                    context = {**context, "resource_tool_estimates": estimates}
            native_expectations = self.workflow.native_estimation_context(self, context)
            if native_expectations is not None:
                context = {**context, 'native_execution_expectations': native_expectations}
                if self.workflow.resource_estimator is not None:
                    native_estimates = self.workflow.resource_estimator.estimate_context(native_expectations)
                    context['resource_tool_estimates'] = [*context.get('resource_tool_estimates', []), *native_estimates]
            if self.workflow.native_event_information is not None:
                context['native_event_targets'] = self.workflow.native_event_information.read(
                    self.workflow.binding_context(self))
            if self.workflow.permits_common_action(self, 'wait'):
                context['waiting_support'] = self.workflow.waiting_support(self, context)
            if profile is not None:
                context = {**context, 'contract_information_profile': profile}
            saved = {"context": context, "schema": schema}
            if profile is None:
                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)
                if frozen is not None:
                    saved[literature_numerical_contracts.SAVED_MEMBER] = frozen
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            if row is None:
                saved = {**saved, 'decision_protocol': DECISION_EXCHANGE_PROTOCOL}
                if profile is not None:
                    saved['contract_information'] = self.workflow.freeze_contract_information(self, context, schema)
                    self.workflow.validate_contract_information(saved)
                if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                        and not self.workflow.uses_received_record_context(self)):
                    self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                        kind='decision_input', source_index=index)
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved), 'response': None})
            return await self.exchange_decision(context, schema, index, saved)
        has_session = getattr(self.workflow.provider, "has_session", lambda *_: False)
        if (not has_session(self.episode_id, "REASONING")
                and "restored_episode_history" not in context):
            # Restore the authoritative scientific/runtime state through the
            # existing replay path, not by rehydrating all archived contexts.
            # The fresh native conversation receives only a bounded metadata
            # index; exact older selections/outcomes are an ordinary own read.
            context = {**context, "restored_episode_history":
                self.workflow.history_preview(self, before=index)}
        context = instructional_model_context(context)
        # Save the exact supplied context, including its bounded operational
        # index, before dispatch. Completed historical calls are returned above
        # unchanged. Metadata contains no old contexts, so it cannot nest them.
        transport = (saved.get('assignment_transport') if row is not None else
            {'version': _ASSIGNMENT_TRANSPORT, 'action_schema_sha256': _digest(schema)})
        saved = {"context": context, "schema": schema,
            **({literature_numerical_contracts.SAVED_MEMBER: saved[literature_numerical_contracts.SAVED_MEMBER]}
                if literature_numerical_contracts.SAVED_MEMBER in saved else {})}
        if transport is not None:
            saved['assignment_transport'] = transport
        if (self.workflow.receipts is not None and not self.workflow.is_job_source(self)
                and not self.workflow.uses_received_record_context(self)):
            # Scientific information is admitted through explicit inputs,
            # own outcomes and requested returns, independently of the scalar
            # credit callable. Other role inputs retain their existing delivery.
            self.workflow.receipts.receive(self.episode_id, context['visible_record_refs'],
                kind='decision_input', source_index=index)
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": None})
        with journal.measure("runtime_model_calls", self.episode_id, index):
            instructions = self.instructions(context)
            response = await self.workflow.provider.complete(self.episode_id, "REASONING", instructions,
                                                              context, _action_generation_schema(schema))
        journal.save("runtime_model_calls", {"episode_id": self.episode_id,
            "call_index": index, "purpose": "decision", "request": _json(saved), "response": _json(response)})
        return response, index, saved["context"], schema

    def instructions(self, context):
        instructions = (self.workflow.job_episodes.instructions(self.path[-1][0])
                        if self.workflow.is_job_source(self) else INSTRUCTIONS)
        specialist = self.workflow.specialist(self)
        if specialist is not None:
            specialized = specialist.instructions(self.workflow.binding_context(self))
            instructions = (specialized if getattr(specialist, 'replaces_default_instructions', False)
                            else instructions + '\n' + specialized)
        if self.workflow.permits_common_action(self, 'reason'):
            instructions += '\n' + REASONING_COMMIT_REQUIREMENT
        if 'tool_knowledge' in context:
            instructions += KNOWLEDGE_INSTRUCTIONS
        if 'launch_instruction_library' in context:
            instructions += LAUNCH_INSTRUCTIONS
        instructions += ('\nWhen pending_child_delivery is supplied, the selected child has finished '
            'its work but its typed return has not been delivered. Complete that existing '
            'acquisition by selecting redeliver_report with a corrected form. Use only the '
            'saved child facts and interpretations for this repair and preserve '
            'current_report_update. The supplied selection schema describes the available '
            'communication operation; this repair does not select new scientific work.')
        if self.workflow.permits_common_action(self, 'wait'):
            instructions += ('\nA pending_child_ handle names your original in-process child, '
                'not an external event-provider target. To give its existing scheduler time '
                'to collect owned work, select wait with that handle, event returned, '
                'after_cursor 0 and reconsider_at null. An earlier ready owned sibling may '
                'wake this wait first; its original return is then collected before another '
                'decision. Waiting only reports readiness and earns no scientific credit. '
                'In-process state_changed/progress_committed events and mixed external '
                'wait conditions are not supported by this collection channel.')
        if (self.workflow.native_event_information is not None
                and self.workflow.permits_common_action(self, 'wait')):
            instructions += ('\nThe separate native_event_targets input names native notification '
                'targets assigned or actually received by this episode. A target is registration '
                'metadata, not proof that submission succeeded. Its state_changed event means '
                'the original service exit receipt was committed; the service may still be '
                'closing, so this does not establish result readiness or a child episode return. '
                'after_cursor records an event cursor actually received, initially zero. Select '
                'your own wait condition and subsequent status/monitor/result work. Request the '
                'native_event_targets source in original child forms when that handoff is needed. '
                'No event probability, gain or scientific credit follows from registration or '
                'passing time alone.')
        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            old_history_guidance = INSTRUCTIONS[INSTRUCTIONS.index('On a fresh provider conversation,'):
                INSTRUCTIONS.index('Do not execute native provider tools.')]
            instructions = instructions.replace(old_history_guidance,
                'Use request_context exchanges for your own attempt metadata and selected inputs; '
                'these create no completed action or observation. Read exact previously received '
                'outcomes with the ordinary episode.history tool, view=records and selected '
                'decision_indices. That read supplies its own ordinary action observation and '
                'does not execute or credit the historical work again.\n')
        return instructions

    def conversation_key(self):
        callback = getattr(self.workflow.provider, 'conversation_key', None)
        return None if callback is None else callback(self.episode_id, 'REASONING')

    def interpretation_context(self, context, exchanges):
        subset = getattr(self.workflow.store, 'reference_subset', None)
        # Inspect only the public received lookup replies. A model's malformed
        # response does not deliver the records it happens to name.
        received = [row['lookup_result'] for row in exchanges
            if row.get('lookup_result_recorded', row.get('lookup_result') is not None)]
        publications = []
        for result in received:
            if isinstance(result, Mapping):
                for record in result.get('records', []):
                    if isinstance(record, Mapping):
                        publications.extend(record.get('published_references', {}).get('values', []))
        references = _references_in({'record_refs': publications}, self.workflow.store.get,
            reference_subset=(lambda refs: subset(refs, self.scope)) if subset is not None else None)
        return {**context, 'visible_record_refs': list(dict.fromkeys([
            *context.get('visible_record_refs', []), *references]))}

    def exchange_schema(self, schema):
        return _object({'response': {'anyOf': [
            _object({'response_type': {'type': 'string', 'const': 'request_context'},
                'lookup': composition_lookup_schema(self.workflow, self)}),
            _object({'response_type': {'type': 'string', 'const': 'select_action'},
                **schema['properties']})]}})

    def exchange_response(self, response, *, lookup_contract=None):
        """Validate the exchange envelope; ordinary action admission stays intact.

        The existing action path deliberately admits independent valid reasoning
        rows and preserves scientific work when report values need repair. Do
        not replace those rules with a whole-action schema gate here.
        """
        if not isinstance(response, dict) or set(response) != {'response'}:
            raise ValueError('decision_response_envelope_required')
        body = response['response']
        if not isinstance(body, dict):
            raise ValueError('decision_response_object_required')
        kind = body.get('response_type')
        if kind == 'request_context':
            if set(body) != {'response_type', 'lookup'}:
                raise ValueError('invalid_request_context_response')
            Draft202012Validator(lookup_contract if lookup_contract is not None else
                composition_lookup_schema(self.workflow, self)).validate(body['lookup'])
        elif kind == 'select_action':
            if set(body) != {'response_type', 'selection', 'report_update'}:
                raise ValueError('invalid_select_action_response')
        else:
            raise ValueError('unknown_decision_response_type')
        return body

    def validate_contract_exchange_request(self, request, saved, index, snapshot, public):
        """Authenticate a new-profile frame against its original host records."""
        record = self.workflow.validate_contract_information(saved)
        if (request.get('instructions') != record['instructions']
                or not _recorded_action_generation_schema(request.get('output_schema'), record['exchange_schema'])
                or request.get('restoration') != {'snapshot': snapshot, 'pending_public_exchanges': public}):
            raise WorkflowError('original_contract_exchange_request_mismatch')
        frame = request.get('context', {})
        try:
            if frame.get('kind') == 'decision_lookup_result':
                if not public:
                    raise ValueError('lookup_requires_received_information')
                expected = {'version': DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result',
                    'decision_index': index, 'exchange_index': public[-1]['exchange_index'],
                    'result': public[-1]['lookup_result'],
                    'pending_contract_information': requested_contract_information(public)}
                if frame != expected:
                    raise ValueError('lookup_frame_differs')
            else:
                previous = None
                if frame.get('kind') == 'decision_update':
                    older = self.workflow.decision_exchanges.rows(self.episode_id, index - 1) if index else []
                    if not older:
                        raise ValueError('original_update_base_unavailable')
                    previous = older[0]['request']['restoration']['snapshot']
                if _json(apply_state_frame(previous, frame)) != _json(snapshot):
                    raise ValueError('frame_differs_from_original_snapshot')
                restored = frame.get('restored_public_exchanges')
                if restored is not None and (restored != public
                        or frame.get('restored_pending_decision_index') != index):
                    raise ValueError('restored_information_differs')
                if public and restored is None:
                    raise ValueError('restored_information_missing')
        except (ValueError, TypeError, KeyError) as error:
            raise WorkflowError('original_contract_exchange_frame_mismatch') from error

    def validate_contract_exchange_history(self, saved, index):
        """Validate saved exchanges without dispatch, state writes or factories."""
        record = self.workflow.validate_contract_information(saved)
        rows = self.workflow.decision_exchanges.rows(self.episode_id, index)
        if not rows:
            return
        snapshot = rows[0]['request']['restoration']['snapshot']
        expected = infernal_receiver_context(instructional_model_context(
            model_snapshot(saved['context'], snapshot['action_yields'])))
        if _json(expected) != _json(snapshot):
            raise WorkflowError('original_contract_decision_snapshot_mismatch')
        lookup = record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
        public = []
        for position, row in enumerate(rows):
            self.validate_contract_exchange_request(row['request'], saved, index, snapshot, public)
            if not row['response_recorded']:
                if position + 1 < len(rows) and rows[position + 1]['request'].get('retry_of_exchange_index') != row['exchange_index']:
                    raise WorkflowError('original_contract_exchange_retry_mismatch')
                continue
            try:
                body = self.exchange_response(row['response'], lookup_contract=lookup)
            except (ValueError, TypeError, ValidationError):
                body = None
            if body is not None and body['response_type'] == 'select_action':
                if position != len(rows) - 1:
                    raise WorkflowError('original_contract_exchange_after_selection')
                original = self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
                selected = {key: body[key] for key in ('selection', 'report_update')}
                if original['response'] is not None and _json(json.loads(original['response'])) != _json(selected):
                    raise WorkflowError('original_contract_selected_response_mismatch')
                return
            if row['lookup_result_recorded']:
                query = (body['lookup'] if body is not None
                    and body['response_type'] == 'request_context' else None)
                contract_query = (query is not None and query.get('view') == 'composition_information'
                    and query.get('operation') in CONTRACT_INFORMATION_OPERATIONS)
                if is_contract_information(row['lookup_result']) and not contract_query:
                    raise WorkflowError('original_contract_information_query_mismatch')
                if contract_query:
                    result = self.workflow.contract_information_reply(saved, record, query['operation'], query['arguments'])
                    if _json(row['lookup_result']) != _json(result):
                        raise WorkflowError('original_contract_information_reply_mismatch')
                public.append({'exchange_index': row['exchange_index'], 'response': row['response'],
                               'lookup_result': row['lookup_result']})
            elif position + 1 < len(rows):
                raise WorkflowError('original_contract_information_reply_missing')

    async def exchange_decision(self, context, schema, index, saved):
        """Retrieve own received information while this one decision is pending.

        This loop services the explicit model exchange protocol. It never
        selects/executes work, changes interpretations or invokes a controller.
        Every actual model dispatch has its own immutable request and timing.
        """
        exchanges, journal = self.workflow.decision_exchanges, self.workflow.journal
        rows = exchanges.rows(self.episode_id, index)
        contract_record = (self.workflow.validate_contract_information(saved)
            if 'contract_information' in saved else None)
        lookup_contract = (contract_record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
            if contract_record is not None else None)
        if contract_record is not None:
            self.validate_contract_exchange_history(saved, index)
        if rows:
            # Presentation and statistical exposure were frozen before the
            # original dispatch. Reconstruction does not refresh either.
            snapshot = rows[0]['request']['restoration']['snapshot']
            instructions = rows[0]['request']['instructions']
            output_schema = rows[0]['request']['output_schema']
        else:
            parameters = _category_yield_parameters(self.workflow.controller_binding)
            if isinstance(context.get('current_credit'), Mapping) and context['current_credit'].get('mode') == 'annotation_axis_credit':
                table = {'version': 'annotation_axis_yield_table_v1',
                    'rows': context['controller']['arms'],
                    'forecast_unit': 'another_whole_axis_invocation',
                    'source': 'actual_root_controller'}
            else:
                table = yield_table(journal, self.episode_id, before=index, parameters=parameters)
            snapshot = model_snapshot(context, table)
            instructions = (contract_record['instructions'] if contract_record is not None else
                self.instructions(context) + '\n' + DECISION_EXCHANGE_INSTRUCTIONS)
            output_schema = _action_generation_schema(contract_record['exchange_schema']
                if contract_record is not None else self.exchange_schema(schema))

        # A resumed unfinished decision may retain an older full axis sheet or
        # automatic native observation expansion. Project its new delivery
        # before frame revisions are computed; never change the saved prior
        # request or hash one view and send another. The original calculation
        # context and explicitly requested child/lookup values stay intact.
        snapshot = infernal_receiver_context(instructional_model_context(snapshot))
        public = []
        cursor = 0
        while True:
            if (cursor + 1 < len(rows) and not rows[cursor]['response_recorded']
                    and rows[cursor + 1]['request'].get('retry_of_exchange_index') == cursor):
                cursor += 1
                continue
            if cursor < len(rows) and rows[cursor]['response_recorded']:
                current = rows[cursor]
            else:
                retry = rows[cursor] if cursor < len(rows) else None
                exchange_index = len(rows)
                key = self.conversation_key()
                continuing = (key is not None and key == self._presented_conversation_key
                    and self._model_snapshot is not None and retry is None)
                if continuing and public:
                    frame = {'version': DECISION_CONTEXT_VERSION, 'kind': 'decision_lookup_result',
                        'decision_index': index, 'exchange_index': public[-1]['exchange_index'],
                        'result': public[-1]['lookup_result']}
                    if contract_record is not None:
                        frame['pending_contract_information'] = requested_contract_information(public)
                else:
                    frame = state_frame(snapshot, self._model_snapshot if continuing else None)
                    if not continuing and (public or retry is not None):
                        frame['restored_public_exchanges'] = _plain(public)
                        frame['restored_pending_decision_index'] = index
                request = {'context': instructional_model_context(frame), 'output_schema': output_schema,
                    'instructions': instructions, 'restoration': {'snapshot': snapshot,
                        'pending_public_exchanges': public},
                    'conversation_key': _plain(key)}
                if retry is not None:
                    request['retry_of_exchange_index'] = retry['exchange_index']
                if contract_record is not None:
                    self.validate_contract_exchange_request(request, saved, index, snapshot, public)
                current = exchanges.prepare(self.episode_id, index, exchange_index, request)
                rows.append(current)
                cursor = exchange_index
                # Propagate transport failures. A later reconstruction appends
                # an explicit retry row, preserving this exact failed input.
                with journal.measure('runtime_model_calls', self.episode_id, index):
                    with exchanges.measure(self.episode_id, index, exchange_index):
                        response = await self.workflow.provider.complete(self.episode_id, 'REASONING',
                            request['instructions'], request['context'], request['output_schema'])
                current = exchanges.respond(self.episode_id, index, exchange_index, response)
                rows[cursor] = current
                self._model_snapshot = snapshot
                after_key = self.conversation_key()
                # An initial dispatch creates a native thread. Compaction of
                # an existing thread invalidates the next incremental base.
                self._presented_conversation_key = (after_key if key is None
                    and (after_key is None or after_key[1] == 0) else key)
            try:
                body = self.exchange_response(current['response'], lookup_contract=lookup_contract)
            except (ValueError, TypeError, ValidationError) as error:
                body = None
                result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange',
                    'code': 'invalid_decision_response', 'detail':
                        schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
            if body is not None and body['response_type'] == 'select_action':
                response = {key: body[key] for key in ('selection', 'report_update')}
                journal.save('runtime_model_calls', {'episode_id': self.episode_id,
                    'call_index': index, 'purpose': 'decision', 'request': _json(saved),
                    'response': _json(response)})
                # A requested own-attempt page can expose an older published
                # reference absent from the bounded initial working-state view.
                # Keep that actual interpretation basis separate from the full
                # original estimation context saved in runtime_model_calls.
                return response, index, self.interpretation_context(context, public), schema
            if current['lookup_result_recorded']:
                result = current['lookup_result']
            else:
                if body is not None:
                    try:
                        query = body['lookup']
                        if query['view'] == 'child_options':
                            result = child_option_information(self.workflow, self, query['role'])
                        elif query['view'] == 'composition_information':
                            result = await self.workflow.execute(self, query['operation'], query['arguments'],
                                decision_index=index,
                                operation_key=f'{self.workflow.run_id}:{self.episode_id}:decision:{index}:'
                                    f'exchange:{current["exchange_index"]}:composition',
                                _composition_lookup=True)
                        else:
                            result = lookup_attempts(journal, self.episode_id, before=index, query=query)
                    except (ValueError, TypeError, ValidationError) as error:
                        result = {'status': 'invalid', 'feedback': {'category': 'decision_exchange',
                            'code': 'invalid_own_attempt_lookup', 'detail':
                                schema_failure_diagnostic(error) if isinstance(error, ValidationError) else str(error)}}
                    except (OSError, sqlite3.Error) as error:
                        result = {'status': 'failed', 'feedback': {'category': 'decision_exchange',
                            'code': 'own_attempt_lookup_failed', 'exception_type': type(error).__name__}}
                current = exchanges.resolve_lookup(self.episode_id, index,
                    current['exchange_index'], result)
                rows[cursor] = current
            public.append({'exchange_index': current['exchange_index'],
                'response': current['response'], 'lookup_result': result})
            cursor += 1

    async def next(self, view, *, delivery_ref=None):
        if delivery_ref is None:
            self._selection_view = view
            closed = self.workflow.journal.row('runtime_episodes', self.episode_id)
            if closed is not None and closed['state'] == 'yielded' and closed['completion'] is not None:
                completion = json.loads(closed['completion'])
                if (completion['ended_by'] == 'source_failed'
                        and view.units_consumed == completion['actions']):
                    # Replaying a finalized partial result must not retry the
                    # already-failed source or select new scientific work.
                    return SourceEnd('source_failed')
        if self.workflow.inprocess_replay is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.inprocess_replay.unit(self, view.units_consumed)
            if ready is not None:
                return ready
            self.restore_checkpoint()
            self._inprocess_replay_ready = True
            with self.workflow.store.transaction():
                self.workflow.inprocess_replay.capture(self)
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
        if self.workflow.execution_binding is not None and delivery_ref is None:
            if not self._restored:
                self.restore()
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            self.restore_checkpoint()
            if self._unfinished_own_actions:
                index = self._unfinished_own_actions.pop(0)
                action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
                return self.workflow.selected(self, json.loads(action['action']), index)
            ready = self.workflow.next_return(self)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
            await self.workflow.resolve_pending_deliveries(self, view)
            ready = self.workflow.completions.slot(self.episode_id, view.units_consumed)
            if ready is not None:
                return self.workflow.completed_unit(self, ready)
        while True:
            original_call = self.workflow.journal.row('runtime_model_calls', self.episode_id, self.calls)
            if (delivery_ref is None and original_call is None
                    and self._execution_context is not None):
                # A rejected selection stays inside this source loop. Collect
                # an original child that finished meanwhile before asking for
                # another decision. Saved calls and delivery repairs retain
                # their original ordering and journal context.
                ready = self._execution_context._ready_owned_child(self.path)
                if ready is not None:
                    return ready
            original_request = json.loads(original_call['request']) if original_call is not None else None
            if original_request is not None and (original_call['response'] is not None
                    or 'contract_information' in original_request
                    or literature_numerical_contracts.SAVED_MEMBER in original_request):
                # Answered decisions already have their supplied context and
                # contracts. Rebuilding them can reopen old native payloads.
                # Opted-in pending decisions also retain their original input.
                context, schema = original_request['context'], original_request['schema']
            else:
                with self.workflow.store.read_snapshot():
                    state = self.workflow.working_state(self)
                    # The last local tool outcome can remain visible while a child
                    # runs. Select pixels from the authoritative most recent own
                    # action instead: a completed child must not reattach an older
                    # image or expose one of its private selections to its parent.
                    row = self.workflow.journal.db.execute("""SELECT CASE
                        WHEN json_extract(action,'$.kind')='tool'
                         AND json_extract(action,'$.tool')='image.view'
                         AND json_extract(result,'$.status')='completed'
                        THEN json_extract(result,'$.visual_inputs') ELSE NULL END
                        FROM runtime_actions WHERE run_id=? AND episode_id=?
                        AND result IS NOT NULL ORDER BY decision_index DESC LIMIT 1""",
                        (self.workflow.run_id, self.episode_id)).fetchone()
                    visual_evidence = json.loads(row[0]) if row and row[0] is not None else []
                    subset = getattr(self.workflow.store, "reference_subset", None)
                    presented_outcome = self.workflow.local_outcome_preview(
                        self.last_outcome, decision_index=self.last_outcome_index)
                    presented_feedback = self.feedback
                    if (isinstance(self.last_outcome, Mapping)
                            and self.feedback is self.last_outcome.get("feedback")
                            and isinstance(presented_outcome, Mapping)):
                        presented_feedback = presented_outcome.get("feedback")
                    credit_view = self.workflow.source_credit_view(self)
                    annotation_axes = (isinstance(credit_view['credit'], Mapping)
                        and credit_view['credit'].get('mode') == 'annotation_axis_credit')
                    forms = [(self.report_values, self.interpret_schema)]
                    if not annotation_axes:
                        forms.extend((report.as_record(), _plain(report.contract.measurements["schema"]))
                                     for report in view.child_reports)
                    controller_state = _plain(view.controller_state)
                    if annotation_axes:
                        state = {}
                        controller_state = {key: controller_state[key] for key in
                            ('arms', 'annotation_credits', 'root_score', 'decision')}
                        if presented_outcome is not None and self.last_outcome_index is not None:
                            prior = self.workflow.journal.row('runtime_actions', self.episode_id,
                                self.last_outcome_index)
                            if prior is not None and json.loads(prior['action']).get('kind') in {
                                    'child', 'episode_child', 'job_child'}:
                                presented_outcome = {
                                    'status': presented_outcome.get('status'),
                                    'record_ref_count': len(presented_outcome.get('record_refs') or ()),
                                    'changed_record_ref_count': len(presented_outcome.get('changed_record_refs') or ())}
                                presented_feedback = None
                    basis = _references_in({"working_state": state, "last_local_outcome": presented_outcome,
                                            "visual_evidence": visual_evidence}, self.workflow.store.get,
                                           forms=forms, reference_subset=(lambda refs: subset(refs, self.scope))
                                           if subset is not None else None)
                    context = view.model_inputs({"goal": self.request.goal.as_record(), "scope": self.scope,
                        "working_state": state, "visible_record_refs": basis,
                        "current_credit": ({'mode': 'annotation_axis_credit',
                            'root_score': controller_state['root_score']}
                            if annotation_axes else credit_view["credit"]),
                        "current_evidence_vector": credit_view.get("axis_components"),
                        **({'investigation_progress': {key: credit_view[key] for key in
                            ('retained_finding_count', 'inactive_dependencies', 'detail_pages')
                            if key in credit_view}} if self.workflow.receipt_projection(self) else {}),
                        "credit_binding": self.workflow.source_credit_binding(self),
                        "time_accounting": self.workflow.journal.elapsed_view(self.episode_id),
                        "pending_work": self.workflow.pending_work(self),
                        "last_local_outcome": presented_outcome, "feedback": presented_feedback,
                        "visual_evidence": visual_evidence,
                        "report_deliveries": self.workflow.delivery_status(self.episode_id),
                        "controller": controller_state,
                        "controller_binding": self.workflow.controller_binding,
                        "tools": self.workflow.catalog(self.scope, source=self),
                        "tool_knowledge": self.workflow.knowledge.context(),
                        "job_episode_options": self.workflow.job_episode_options(self),
                        "available_report_facts": {name: {"type": "number" if name == "credit" else "reference_array",
                                                           "meaning": FACT_MEANINGS[name]}
                                                   for name in sorted(FACT_SOURCES)} | self.workflow.extra_report_sources(self),
                        "requested_report_purpose": (self.request.report_contract.decision
                            if self.request.report_contract else None),
                        "requested_form": self.request.report_contract.schema if self.request.report_contract else None,
                        "current_report_update": self.report_values,
                        "current_report_basis_refs": self.report_basis,
                        "report_lifecycle": "Interpretations are the last actual reasoning basis; later tool outcomes are facts, not a new judgment."},
                        reports=() if annotation_axes else view.child_reports)
                    if self.workflow.is_scientific_source(self):
                        if annotation_axes:
                            context.update(proposed_annotations=[{key: row[key] for key in
                                ('proposed_annotation_ref', 'subject_ref', 'predicate', 'value',
                                 'context_refs', 'scope', 'score', 'support', 'opposition', 'status')}
                                for row in credit_view['proposed_annotations']],
                                annotation_comparisons=credit_view['comparisons'])
                        else:
                            context.update(self.workflow.annotation_context(self.scope, source=self))
                    if 'monitoring_information_credit' in credit_view:
                        context.update({key: credit_view[key] for key in
                            ('monitoring_information_credit', 'monitoring_information_binding')})
                    specialist = self.workflow.specialist(self)
                    if specialist is not None:
                        context.update(specialist.decision_context(self.workflow.binding_context(self), view))
                    context['_completed_work_axis_results'] = {
                        key: credit_view[key] for key in (
                            'a101_sheet', 'a102_sheet', 'a103_sheet', 'a104_sheet',
                            'target_sheets', 'tool_attachments', 'source_contributions')
                        if key in credit_view}
                    contract_catalog = getattr(self.workflow.tools, 'model_contract_catalog', None)
                    if callable(contract_catalog):
                        context['available_report_facts'] = contract_catalog(context)
                schema = self.workflow.action_schema(self)
                if delivery_ref is not None:
                    context, schema = self.workflow.delivery_resolution_inputs(
                        self, delivery_ref, context)
            if (delivery_ref is not None and
                    context.get('pending_child_delivery', {}).get('delivery_ref') != delivery_ref):
                raise WorkflowError('restored_delivery_resolution_identity_conflict')
            from .providers import ModelCallError
            try:
                response, index, actual_context, schema = await self.call(context, schema)
            except ModelCallError as error:
                from .episode_source_failure import record_source_failure
                record_source_failure(self.workflow.store, self.workflow.run_id,
                    self.episode_id, self.calls - 1, error)
                self.feedback = {'status': 'failed', 'category': 'decision_source',
                    'exception_type': type(error).__name__, 'detail': str(error)}
                self.checkpoint()
                if delivery_ref is not None:
                    raise
                return SourceEnd('source_failed')
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None
                    or self.workflow.inprocess_replay is not None else nullcontext()):
                unit = self.apply_response(response, index, actual_context, schema)
            if unit is not None:
                return unit

    def restore_checkpoint(self):
        """Restore latest source state after replay, before receiving new work."""
        if self._restored_source_state is not None:
            saved = self._restored_source_state
            self._restored_source_state = None
            self.last_outcome_index = saved['last_outcome_index']
            self.last_outcome = (None if self.last_outcome_index is None else json.loads(
                self.workflow.journal.row('runtime_actions', self.episode_id,
                    self.last_outcome_index)['result']))
            self.feedback = saved['feedback']

    def restore(self):
        restored = self.workflow.completions.restore_source(self.episode_id)
        self.calls = restored['next_call_index']
        effect = restored['latest_effect']
        if effect is not None:
            self.report_values = effect['report_values']
            self.report_basis = effect['report_basis_refs']
            self.feedback = effect['feedback']
        index = restored['last_completed_decision_index']
        if index is not None:
            action = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            self.last_outcome = json.loads(action['result'])
            self.last_outcome_index = index
        self._unfinished_own_actions = (self.workflow.inprocess_replay.unfinished(self)
            if self.workflow.inprocess_replay is not None else restored['unfinished_own_action_indices'])
        self._latest_effect_index = restored['latest_effect_index']
        self._restored_source_state = restored['source_state']
        if self._restored_source_state is not None:
            self._source_revision = self._restored_source_state['revision']
        if self.workflow.execution_binding is not None:
            self.workflow.recover_commissions(self)
        if self.workflow.progress_provider is not None:
            self.workflow.progress_provider.flush_notifications()
        self._restored = True

    def record_effect(self, index, state):
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            self.workflow.completions.record_decision_effect(self.episode_id, index, {
                'version': EFFECT_VERSION, 'state': state, 'report_values': self.report_values,
                'report_basis_refs': self.report_basis, 'feedback': self.feedback})
            self._latest_effect_index = index
            self.checkpoint()

    def checkpoint(self):
        if self.workflow.inprocess_replay is not None and not self._inprocess_replay_ready:
            # Rebuilding a prefix must not replace the original latest source
            # checkpoint with a partially reconstructed transient state.
            return
        if self.workflow.execution_binding is not None or self.workflow.inprocess_replay is not None:
            if self.workflow.inprocess_replay is not None and self._inprocess_replay_ready:
                self.workflow.inprocess_replay.capture(self)
            saved = self.workflow.completions.checkpoint_source(self.episode_id,
                expected_revision=self._source_revision, latest_effect_index=self._latest_effect_index,
                last_outcome_index=self.last_outcome_index, feedback=self.feedback)
            self._source_revision = saved['revision']

    def apply_response(self, response, index, actual_context, schema):
        selection = None
        try:
            original = self.workflow.journal.row('runtime_actions', self.episode_id, index)
            call = (self.workflow.journal.row('runtime_model_calls', self.episode_id, index)
                if original is None and self.workflow.decision_exchanges is not None else None)
            saved = {} if call is None else json.loads(call['request'])
            response = _decode_recorded_action_response(response, schema,
                recorded_selection=None if original is None else json.loads(original['action']),
                exchanges=() if original is not None or self.workflow.decision_exchanges is None else
                    self.workflow.decision_exchanges.rows(self.episode_id, index),
                exchange_schema=saved.get('contract_information', {}).get('exchange_schema'),
                unproven_replay=getattr(self, '_unproven_direct_response_index', None) == index)
            # Validate selection independently: report formatting must not
            # reject a valid scientific contribution or alter its credit.
            selection = response["selection"]
            if self._delivery_resolution_ref is not None:
                Draft202012Validator(schema).validate(response)
                if response['report_update'] != self.report_values:
                    raise ValueError('delivery_resolution_must_preserve_current_interpretation')
            if (self.workflow.permits_common_action(self, 'reason') and isinstance(selection, Mapping)
                    and selection.get("kind") == "reason"):
                # Store owns row-level admission and preserves independent
                # valid rows. Checking its full scientific payload here
                # would prevent its partial-result path from ever running.
                envelope = self.workflow.reasoning_action_schema(self, {"type": "object"},
                    _accept_legacy_quotes=True)
                Draft202012Validator(envelope).validate(selection)
                payload = selection["commit"]
                commit_schema = self.workflow.store.reasoning_schema()
                if (set(commit_schema.get("required", commit_schema["properties"]))
                        <= set(payload) <= set(commit_schema["properties"])
                        and all(value == [] for value in payload.values())
                        and selection.get('evidence_processing', {}).get('kind') != 'no_applicable_evidence'):
                    owner = self.workflow.specialist(self)
                    has_task_content = getattr(owner, 'reasoning_has_task_content', None)
                    if has_task_content is None or not has_task_content(
                            self.workflow.binding_context(self), selection):
                        raise ValueError("empty_reasoning_commit")
            else:
                Draft202012Validator(schema["properties"]["selection"]).validate(selection)
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
                unit = self.workflow.selected(self, selection, index)
        except EventTargetError as error:
            self.feedback = _wait_target_feedback(error, status='invalid')
            self.record_effect(index, 'rejected')
            return None
        except (OSError, sqlite3.Error, subprocess.SubprocessError, AcquisitionError) as error:
            if not isinstance(selection, Mapping) or selection.get('kind') != 'job_child':
                raise
            # Receiving-interface failure is operational feedback about
            # this commission, not a malformed contract, completed child
            # action, numerical observation or reason to stop the parent.
            handoff = selection.get('handoff') or {}
            self.feedback = {'status': 'failed', 'category': 'job_assignment',
                'code': (error.code if isinstance(error, AcquisitionError)
                    else 'job_storage_failed' if isinstance(error, sqlite3.Error)
                    else 'job_control_failed' if isinstance(error, subprocess.SubprocessError)
                    else 'job_operation_failed'),
                'exception_type': type(error).__name__, 'role': selection['role'],
                'job_ref': selection.get('existing_job_ref', handoff.get('job_ref'))}
            self.record_effect(index, 'rejected')
            return None
        except (ValueError, KeyError, TypeError, ValidationError) as error:
            self.feedback = {"status": "invalid", "category": "action_contract",
                "detail": (schema_failure_diagnostic(error)
                           if isinstance(error, ValidationError) else str(error))}
            if isinstance(error, ContractInformationError):
                self.feedback['contract_error'] = {'code': error.code, 'field': error.field}
                if error.code == 'closed_top_level_form_required':
                    self.feedback['repair'] = (
                        'schema_json must encode a JSON Schema object with the explicit top-level '
                        'field "type": "object" and a properties object. Keep the intended properties, '
                        'declare every field in required, and set additionalProperties to false. '
                        'A properties object alone does not declare the required outer type.')
                if isinstance(error.__cause__, ReportBoundaryError):
                    self.feedback['schema_reason'] = str(error.__cause__)
            if (isinstance(error, ContractError)
                    and str(error) == 'component_native_return_channels_required'):
                self.feedback['contract_error'] = {'code': str(error),
                    'field': error.detail['field']}
                self.feedback['required_fact_sources'] = error.detail['missing_fact_sources']
                self.feedback['repair'] = error.detail['repair']
            assignment = selection.get('assignment') if isinstance(selection, Mapping) else None
            selector = assignment.get('selector') if isinstance(assignment, Mapping) else None
            if (isinstance(error, ContractError) and isinstance(error.detail, Mapping)
                    and isinstance(selection, Mapping) and isinstance(assignment, Mapping)
                    and selection.get('kind') == 'episode_child' and selection.get('role') == 'results'
                    and assignment.get('version') == 'execution_results_assignment_v1'
                    and isinstance(selector, Mapping)
                    and selector.get('version') == 'bvbrc_minhash_result_selector_v2'):
                # Preserve the validator's affected input locations so the
                # selecting parent can repair this commission. Do not copy the
                # whole assignment or manufacture a completed-action outcome.
                affected = {key: _plain(error.detail[key]) for key in (
                    'source_ref', 'artifact_ref', 'handoff_ref', 'pair_metadata_index',
                    'row_index', 'genome_id', 'field', 'record_path') if key in error.detail}
                if affected:
                    self.feedback['input_detail'] = affected
            if (isinstance(error, ValidationError) and isinstance(selection, Mapping)
                    and selection.get("kind") == "tool" and selection.get("tool") == "reads.map"):
                from .read_mapping import parameter_schema_failure
                branches = schema["properties"]["selection"]["anyOf"]
                for branch_error in error.context:
                    branch_path = list(branch_error.schema_path)
                    if not branch_path or not isinstance(branch_path[0], int):
                        continue
                    branch = branches[branch_path[0]]
                    if branch.get("properties", {}).get("tool", {}).get("const") != "reads.map":
                        continue
                    feedback = parameter_schema_failure(branch_error, path_prefix=("arguments",))
                    if feedback is not None:
                        self.feedback.update(feedback)
                        break
            self.record_effect(index, 'rejected')
            return None
        try:
            resolve_report_reference = self.workflow.resolver(self.scope, source=self)
            admitted = validate_form(response["report_update"], self.interpret_schema,
                resolve_report_reference)
            self.workflow.validate_report(admitted, self.scope,
                assignment=self.request.message.as_record().get("job_assignment"), grain=self.path[-1][0],
                schema=self.interpret_schema, source=self)
            self.report_values = admitted
            # Source metadata can expose private request/capture identifiers.
            # The host-filled report basis has the same ownership rules as
            # model-selected report references; visibility alone is no grant.
            self.report_basis = [ref for ref in actual_context["visible_record_refs"]
                if resolve_report_reference(ref)]
            self.feedback = None
        except (ValueError, KeyError, TypeError) as error:
            self.feedback = {"status": "invalid", "category": "report_format",
                             "detail": getattr(error, "diagnostic", {"code": "invalid_report_update"})}
        if isinstance(unit, ReportRedelivery):
            self.feedback = None if unit.failure is None else unit.failure.as_record()
        self.record_effect(index, 'redelivery' if isinstance(unit, ReportRedelivery) else 'selected')
        return unit

    async def execute(self, selection, index):
        journal = self.workflow.journal
        old = journal.row("runtime_actions", self.episode_id, index)
        if old and json.loads(old["action"]) != selection:
            raise WorkflowError("reconstructed selected work changed")
        if old and old["result"] is not None:
            result, credit = json.loads(old["result"]), old["credit"]
        else:
            if self.path[-1][0] == 'scientific_process':
                self.workflow.scientific_process_binding.validate_execution_context(
                    self.workflow.binding_context(self))
            journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                "action": _json(selection), "result": None, "credit": None})
            key = f"{self.workflow.run_id}:{self.episode_id}:{index}"
            with journal.measure("runtime_actions", self.episode_id, index):
                if selection["kind"] == "reason":
                    payload = selection['commit']
                    ownership = ({'account_owner': (self.workflow.run_id, self.episode_id)}
                                 if payload.get('interpretation_accounts') else {})
                    specialist = self.workflow.specialist(self)
                    execute_reasoning = getattr(specialist, 'execute_reasoning', None)
                    result = (execute_reasoning(self.workflow.binding_context(self), selection, key)
                              if execute_reasoning is not None else None)
                    if result is None:
                        result = self.workflow.store.commit_reasoning(payload, self.scope, key, **ownership)
                elif selection['kind'] == 'wait':
                    try:
                        result = await self.workflow.perform_selected_wait(self, selection['condition'], index)
                    except EventTargetError as error:
                        # An original unfinished selection (including restore)
                        # must return to the ordinary failed-action repair path.
                        # Its immutable wait request/timing remain unchanged.
                        result = {'status': 'failed', 'record_refs': [],
                            'changed_record_refs': [], 'result': None,
                            'feedback': _wait_target_feedback(error, status='failed')}
                else:
                    result = self.workflow.execute(self, selection["tool"], selection["arguments"],
                        decision_index=index, operation_key=key)
                if inspect.isawaitable(result):
                    result = await result
            if (self.workflow.execution_binding is not None
                    or self.workflow.wait_inputs_version == 'wait_inputs_binding_v2'
                    or self.workflow.completed_action_inputs_version is not None):
                result = {**result, 'pending_work_after_action': self.workflow.pending_work(self)}
            with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _json(selection), "result": _json(result), "credit": None})
                self.last_outcome, self.last_outcome_index = result, index
                if result['status'] not in ('completed', 'partial'):
                    self.feedback = result.get('feedback') or {'status': result['status'],
                        'category': result.get('error_code', 'work_failed')}
                self.checkpoint()
            credit = None
        # Project from the recorded outcome. A crash between result publication
        # and projection resumes here without repeating the native operation.
        observed_outcome = observes_action_outcome(selection['kind'], result['status'])
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
            self.workflow.receive_native_outcome(self, result, index)
            if credit is None and observed_outcome:
                self.workflow.receive_outcome(self, selection, result, index)
        if credit is None and observed_outcome and selection['kind'] != 'wait':
            # Native publication and its received inputs are committed before
            # an owner requests a one-shot scientific judgment. The judgment is
            # part of this same selected action, with no new episode or yield.
            result = await self.workflow.automatic_score_updates(self, index, result)
        with (self.workflow.store.transaction() if self.workflow.execution_binding is not None else nullcontext()):
            if credit is None and observed_outcome:
                if selection['kind'] == 'wait':
                    credit = self.workflow.last_observed_credit(self)
                else:
                    credit_view = self.workflow.source_credit_view(self)
                    credit = credit_view['credit']
                    if selection.get('kind') == 'tool' and selection.get('tool') == 'shared.read_information':
                        self.workflow.retain_shared_grading_results(self, result, credit_view)
                journal.save("runtime_actions", {"episode_id": self.episode_id, "decision_index": index,
                    "action": _json(selection), "result": _json(result), "credit": credit})
            if self.workflow.execution_binding is not None and observed_outcome:
                self.workflow.completions.stage(self.episode_id, index, label=f"{selection['kind']}:{index}",
                    kind='own_action', controller_input=self.workflow.controller_value(self, index, credit),
                    child_return=None)
                self.last_outcome, self.last_outcome_index = result, index
                self.checkpoint()
        # Tools own query bounds; never reclip a selected evidence page here.
        self.last_outcome = result
        self.last_outcome_index = index
        if not observed_outcome:
            raise ActionFailure(result.get("feedback") or {"status": result["status"],
                "category": result.get("error_code", "work_failed")})
        return self.workflow.controller_value(self, index, credit)

    async def finish(self, record):
        if self.request.report_contract is None:
            result = {"credit": self.workflow.source_credit_view(self)["credit"],
                'pending_handles': self.workflow.pending_handles(self)}
            result.update(self.workflow.episode_bindings.current_report_facts(
                self.workflow.binding_context(self)))
            await self.workflow.release(self.episode_id)
            return Record(result)
        saved = self.workflow.journal.row("runtime_forms", self.episode_id)
        if saved and saved["form"] is not None:
            form = json.loads(saved["form"])
        else:
            facts = self.workflow.facts(self, completion_record=record)
            form = form_with_facts(self.report_values, self.request.report_contract.schema, facts)
            self.workflow.journal.save("runtime_forms", {"episode_id": self.episode_id,
                "facts": _json({**facts, "interpretations": self.report_values}), "form": _json(form)})
        # This is the recorded candidate, not an admitted parent report.
        # The parent's separate report projection/admission can fail without
        # undoing completed science or losing the child's acquisition trace.
        await self.workflow.release(self.episode_id)
        return Record({"form": form})


class Workflow:
    grain_names = ("annotation", "improvement")

    @classmethod
    def validate_expectations(cls, binding, job_episodes=None, *, episode_roles=()):
        scientific = ('annotation',) if 'scientific_process' in episode_roles else cls.grain_names
        names = (*scientific, *(() if job_episodes is None else job_episodes.roles), *episode_roles)
        if binding is not None and set(binding.episode_types) - set(names):
            raise ValueError("execution_expectations_name_unavailable_episode_type")

    def __init__(self, store, tools, provider, directory, run_id, controller_factory, project_credit,
                 credit_binding=None, restoration_settings=None, execution_expectations=None,
                 job_episodes=None, controller_binding=None, project_child_credit=None,
                 child_credit_binding=None, resource_estimator=None,
                 project_annotation_score=None, annotation_score_binding=None,
                 initial_known_record_refs=None, native_timing_information=None,
                 episode_binding_factories=None, episode_binding_descriptors=None,
                 role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                 episode_service_factory=None, episode_service_binding=None,
                 progress_receipt_order='received_progress_order_v1',
                 episode_record_receipts=False, wait_inputs_version='wait_inputs_binding_v2',
                 completed_action_inputs_version='completed_action_inputs_binding_v1',
                 native_job_events=None, episode_service_inputs=None,
                 annotation_child_roles=None, root_role='annotation', decision_protocol=None,
                 root_action_boundary=ROOT_BOUNDARY_VERSION,
                 episode_branch_lifecycle=EPISODE_BRANCH_LIFECYCLE,
                 inprocess_completion_order=None):
        from .inprocess_replay import VERSION as INPROCESS_COMPLETION_ORDER
        if inprocess_completion_order not in (None, INPROCESS_COMPLETION_ORDER):
            raise ValueError('unsupported_inprocess_completion_order')
        if inprocess_completion_order is not None and execution_binding is not None:
            raise ValueError('durable_execution_already_owns_completion_order')
        self.inprocess_completion_order = inprocess_completion_order
        self.root_role = root_role
        if episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE:
            raise ValueError('original_episode_lifecycle_requires_its_pinned_implementation')
        self.episode_branch_lifecycle = episode_branch_lifecycle
        if root_action_boundary not in (None, ROOT_BOUNDARY_VERSION):
            raise ValueError('unsupported_root_action_boundary')
        self.root_action_boundary = root_action_boundary
        self.decision_protocol = _decision_protocol(decision_protocol)
        self.annotation_child_roles = _annotation_child_roles(annotation_child_roles)
        native_job_events = native_job_event_configuration(native_job_events)
        if native_job_events is not None:
            if job_episodes is None:
                raise ValueError('native_job_events_requires_job_binding')
            statistics = getattr(job_episodes, 'statistics', None)
            if statistics is not None and statistics.resource_id != native_job_events['resource_id']:
                raise ValueError('native_event_resource_binding_mismatch')
        self.native_job_events = native_job_events
        if type(episode_record_receipts) is not bool:
            raise TypeError('episode_record_receipts_must_be_bool')
        if episode_record_receipts and (not isinstance(initial_known_record_refs, (list, tuple))
                or any(not isinstance(ref, str) or not ref for ref in initial_known_record_refs)):
            raise ValueError('receipt_binding_requires_explicit_initial_known_record_refs')
        self.episode_record_receipts = episode_record_receipts
        if wait_inputs_version not in {'wait_inputs_binding_v1', 'wait_inputs_binding_v2'}:
            raise ValueError('unsupported_wait_inputs_binding')
        self.wait_inputs_version = wait_inputs_version
        if completed_action_inputs_version not in {None, 'completed_action_inputs_binding_v1'}:
            raise ValueError('unsupported_completed_action_inputs_binding')
        self.completed_action_inputs_version = completed_action_inputs_version
        self.episode_application_services_binding = service_binding(
            episode_service_factory, episode_service_binding, inputs=episode_service_inputs)
        if self.episode_application_services_binding is not None and any(value is not None for value in
                (episode_binding_factories, episode_binding_descriptors, role_credit_bindings, job_progress_provider)):
            raise ValueError('episode_service_factory_and_direct_services_are_exclusive')
        if progress_receipt_order not in {'received_progress_order_v1', 'legacy_grouped_v1'}:
            raise ValueError('unsupported_progress_receipt_order')
        self.progress_receipt_order = progress_receipt_order
        self.store, self.tools, self.provider = store, tools, provider
        self.directory, self.run_id = Path(directory), run_id
        self.knowledge = ToolKnowledge.freeze(self.directory/'tool-knowledge',
            source=getattr(tools, 'knowledge_library_directory', None))
        self.launch_instructions = LaunchInstructions.freeze(self.directory/'launch-instructions',
            source=getattr(tools, 'launch_instruction_library_directory', None))
        self.controller_factory, self.project_credit = controller_factory, project_credit
        self.project_child_credit = project_child_credit
        self.project_annotation_score = project_annotation_score
        self.annotation_score_binding = _plain(annotation_score_binding)
        self.child_credit_binding = (_plain(child_credit_binding) if child_credit_binding is not None else
            {"kind": "custom", "projector": _binding_name(project_child_credit, "caller_injected"),
             "meaning": "Available finding calculation; each scientific owner selects its task credit."}
            if project_child_credit is not None else None)
        self.controller_binding = (_plain(controller_binding) if controller_binding is not None else
            {"kind": "custom", "factory": _binding_name(controller_factory, "caller_injected")})
        self.job_episodes = job_episodes
        if job_episodes is not None:
            job_episodes.recover_statistics()
        self.execution_expectations = execution_expectations
        self.resource_estimator = resource_estimator
        self.native_timing_information = native_timing_information
        self.restoration_settings = _effective_restoration_configuration(base=restoration_settings)
        self.credit_binding = (_plain(credit_binding) if credit_binding is not None else {
            "kind": "custom", "projector": _binding_name(project_credit, "caller_injected"),
            "meaning": "Caller-injected projector; no default scientific policy or denominator is inferred."})
        self.journal = Journal(store, run_id)
        self.decision_exchanges = (DecisionExchanges(self.journal)
            if self.decision_protocol == DECISION_EXCHANGE_PROTOCOL else None)
        self.execution_backend = DurableExecutionStore(self.directory / 'episode-execution')
        self.native_event_information = None
        self.native_event_recovery = None
        if native_job_events is not None:
            from .native_events import NativeEventProvider
            from .native_event_information import NativeEventInformation
            native_provider = NativeEventProvider(self.execution_backend.root_directory,
                run_id=run_id, resource_id=native_job_events['resource_id'])
            job_episodes = job_episodes.with_native_events(native_provider)
            self.job_episodes = job_episodes
            self.native_event_information = NativeEventInformation(store, self.journal,
                self.execution_backend, jobs=job_episodes.jobs,
                resource_id=native_job_events['resource_id'])
            self.native_event_recovery = job_episodes.recover_native_events()
        self.execution_binding = _plain(execution_binding)
        self.execution_handle = None
        self.commissions = CommissionCoordinator(store, self.journal, self.execution_backend)
        self.completions = CompletionLedger(store, self.journal)
        self.wait_store = WaitStore(store, run_id)
        self.local_return_history = LocalReturnHistory(store, self.journal, self.execution_backend)
        self.progress_provider = None
        self.role_credit_projectors = {}
        self.role_credit_definitions = {}
        self.resource_capabilities = ()
        self.receipts = (EpisodeReceipts(store, run_id) if episode_record_receipts or native_timing_information is not None or any(
            getattr(projector, 'requires_episode_receipts', False)
            for projector in (project_credit, project_child_credit)) else None)
        self.initial_known_record_refs = (tuple(initial_known_record_refs)
            if isinstance(initial_known_record_refs, (list, tuple)) else initial_known_record_refs)
        self.archive = JsonArchive(self.directory / "archive")
        if self.inprocess_completion_order is not None:
            from .inprocess_replay import InProcessReplay
            if self.receipts is None:
                raise ValueError('inprocess_completion_replay_requires_original_receipts')
            self.inprocess_replay = InProcessReplay(self)
        else:
            self.inprocess_replay = None
        self.services = WorkflowServices(self)
        self.episode_job_progress_provider_binding = None
        if episode_service_factory is not None:
            setup_inputs = ({} if episode_service_inputs is None else
                {'tool_catalog': json.loads(canonical(self.tools.catalog()))})
            if episode_service_inputs == 'actual_tool_registry_v1':
                setup_inputs['tool_registry'] = self.tools
            application = episode_service_factory(store, run_id=run_id, directory=self.directory,
                job_episodes=job_episodes, resource_estimator=resource_estimator, **setup_inputs)
            if type(application) is not EpisodeApplicationServices:
                raise TypeError('episode_service_factory_must_return_EpisodeApplicationServices')
            episode_binding_descriptors = application.episode_binding_descriptors
            role_credit_bindings = application.role_credit_bindings
            job_progress_provider = application.job_progress_provider
            self.episode_job_progress_provider_binding = job_progress_binding(job_progress_provider)
        if episode_binding_descriptors is not None:
            if episode_binding_factories is not None:
                raise ValueError('episode_descriptors_and_factories_are_exclusive')
            from .episode_composition import compose_episode_bindings
            composition = compose_episode_bindings(self.services, store=store, journal=self.journal,
                execution_backend=self.execution_backend, descriptors=episode_binding_descriptors,
                job_episodes=job_episodes, resource_estimator=resource_estimator,
                role_credit_bindings=role_credit_bindings or {}, job_progress_provider=job_progress_provider,
                directory=self.directory, tool_registry=self.tools)
            self.progress_provider = composition.progress_provider
            self.resource_capabilities = composition.resource_capabilities
            self.role_credit_projectors = composition.role_credit_projectors
            self.role_credit_definitions = composition.role_credit_definitions
            self.episode_bindings = EpisodeBindingRegistry(composition.bindings)
        else:
            if role_credit_bindings is not None or job_progress_provider is not None:
                raise ValueError('explicit_specialist_services_require_episode_descriptors')
            if episode_binding_factories is None:
                from .literature_episodes import LiteratureEpisodes
                episode_binding_factories = (LiteratureEpisodes,)
            self.episode_bindings = EpisodeBindingRegistry(
                factory(self.services) for factory in episode_binding_factories)
        for profile in self.episode_bindings.contract_information_configurations():
            self.validate_contract_information_configuration(profile)
        self.validate_expectations(execution_expectations, job_episodes,
            episode_roles=self.episode_bindings.roles)
        self.scientific_process_binding = (self.episode_bindings.for_role('scientific_process')
            if 'scientific_process' in self.episode_bindings.roles else None)
        self.scientific_provenance = None
        self.scientific_tool_retriever = None
        if self.scientific_process_binding is not None:
            from .scientific_process_provenance import ScientificProcessProvenance
            self.scientific_provenance = ScientificProcessProvenance(store, self.journal,
                library=self.scientific_process_binding.library,
                tool_library=self.scientific_process_binding.tool_library)
            retrieval = self.scientific_process_binding.tool_retrieval
            if retrieval is not None and retrieval['mode'] == 'semantic_fast_v1':
                from .scientific_tool_retrieval import ScientificToolRetriever
                self.scientific_tool_retriever = ScientificToolRetriever(store, run_id=run_id,
                    provider=provider, library=self.scientific_process_binding.tool_library,
                    configuration=retrieval)
        if self.receipts is None and any(getattr(projector, 'requires_episode_receipts', False)
                for projector in self.role_credit_projectors.values()):
            raise ValueError('role_credit_requires_episode_record_receipts')
        self.wait_inputs = WaitInputs(store, self.journal, self.progress_provider)
        names = (self.grain_names + (() if job_episodes is None else job_episodes.roles)
                 + self.episode_bindings.roles)
        self.grains = {name: Grain(name, "One completed selected improvement action",
            "Committed semantic work and a parent-defined form", self.controller)
            for name in names}
        if root_role not in self.grains:
            raise ValueError('root_episode_role_not_bound')
        available_entries = self._default_scientific_child_roles()
        if (self.annotation_child_roles is not None
                and not set(self.annotation_child_roles) <= set(available_entries)):
            raise ValueError('annotation_child_role_not_an_entry_role')
        children = {self.grains['annotation']: tuple(self.grains[name] for name in
            self.declared_child_roles('annotation'))}
        for role in (() if job_episodes is None else job_episodes.roles):
            children[self.grains[role]] = ()
        if self.scientific_process_binding is None:
            children[self.grains['improvement']] = tuple(self.grains[name] for name in
                self.declared_child_roles('improvement'))
        for role in self.episode_bindings.roles:
            children[self.grains[role]] = tuple(self.grains[name] for name in
                self.declared_child_roles(role))
        if self.annotation_child_roles is not None or root_role != 'annotation':
            # Keep excluded legacy implementations bound for their adapters,
            # without declaring unreachable root alternatives in this tree.
            reachable, frontier = set(), [self.grains[root_role]]
            while frontier:
                grain = frontier.pop()
                if grain not in reachable:
                    reachable.add(grain)
                    frontier.extend(children.get(grain, ()))
            children = {grain: values for grain, values in children.items() if grain in reachable}
        # Declare actual type cycles; this metadata does not choose an action
        # or instantiate a child. Every episode instance still owns its loop.
        adjacency = {parent.name: {child.name for child in values}
                     for parent, values in children.items()}
        def reaches(start, target):
            frontier, seen = [start], set()
            while frontier:
                value = frontier.pop()
                if value == target:
                    return True
                if value not in seen:
                    seen.add(value)
                    frontier.extend(adjacency.get(value, ()))
            return False
        recursive = tuple((parent, child) for parent, values in adjacency.items()
                          for child in values if reaches(child, parent))
        self.tree = EpisodeTree(self.grains[root_role], children,
            self_nesting=tuple(name for name, values in adjacency.items() if name in values),
            recursive_edges=recursive)
        self.context = ReleasingContext(tree=self.tree, run_id=run_id)
        self.configure_execution(execution_binding)

    def configure_execution(self, binding, *, execution_handle=None):
        if self.execution_binding is not None and _plain(binding) != self.execution_binding:
            raise WorkflowError('execution_binding_is_immutable')
        self.execution_binding = _plain(binding)
        self.execution_handle = execution_handle
        if binding is not None and self.progress_provider is None:
            from .episode_monitoring import ProgressProvider
            self.progress_provider = ProgressProvider(self.store, self.execution_backend, run_id=self.run_id)
            self.wait_inputs = WaitInputs(self.store, self.journal, self.progress_provider)

    def commission_child(self, source, child, selection, index):
        self.validate_child_choice(source, child.source.path[-1][0], selection=selection, original=True)
        message = child.request.message.as_record()
        assignment = message.get('episode_assignment', message.get('job_assignment', {}))
        references = _references_in({'scope': child.source.scope, 'assignment': assignment}, self.store.get,
            forms=[(message['initial_report'], interpretation_schema(child.request.report_contract.schema))],
            reference_subset=lambda refs: self.store.reference_subset(refs, child.source.scope))
        from .episode_input_versions import pin_commission_inputs
        resource_versions = assignment.get('immutable_input_versions',
            assignment.get('handoff', {}).get('submitted_input_versions', ()))
        pinned = pin_commission_inputs(self.store, references, resource_input_versions=resource_versions)
        original = json.loads(self.journal.row('runtime_model_calls', source.episode_id, index)['request'])['context']
        expectation_refs = list(dict.fromkeys(snapshot['ref'] for name in
            ('execution_expectations', 'native_execution_expectations')
            for snapshot in (original.get(name) or {}).get('snapshots', [])))
        resources = self.tools.resource_binding() if callable(getattr(self.tools, 'resource_binding', None)) else {}
        constraints = _plain(assignment.get('constraints', {'local_jobs': resources.get('local_jobs')}))
        spec = self.commissions.select(parent={'episode_id': source.episode_id,
            'goal_id': source.request.goal.goal_id, 'path': _plain(source.path)},
            child={'episode_id': child.source.episode_id, 'role': child.source.path[-1][0],
                'key': child.key, 'path': _plain(child.source.path), 'request': _plain(child.request.as_record()),
                'scope': _plain(child.source.scope)}, original_decision_index=index, selection=selection,
            runtime_binding=self.execution_binding, input_versions=pinned, constraints=constraints,
            resource_selection=assignment.get('resource_selection'),
            expectation_snapshot_refs=expectation_refs, selected_at=_now())
        return self.deferred_unit(source, index, spec)

    def deferred_unit(self, source, index, spec):
        def dispatch(context):
            self.dispatch_commission(source, index, spec)
            return spec['handle']
        async def collect(context, handle):
            status = await self.execution_backend.await_return_or_suspension(handle)
            if not status['return_available']:
                self.settle_unclaimed_child_failures(source)
                return PendingAction(handle)
            slot = self.next_return(source, only_handle=handle)
            if slot is None:
                delivery_ref = 'delivery_' + _digest({
                    'run': self.run_id, 'parent': source.episode_id, 'index': index})[:24]
                await self.resolve_pending_deliveries(source, source._selection_view,
                    only_delivery_ref=delivery_ref)
                row = self.store.db.execute('SELECT slot FROM runtime_completion_slots '
                    'WHERE run_id=? AND episode_id=? AND original_decision_index=?',
                    (self.run_id, source.episode_id, index)).fetchone()
                slot = None if row is None else json.loads(row[0])
            if slot is None:
                raise WorkflowError('owned_return_requires_accounted_original_action')
            return await self.completed_unit(source, slot).acquire_async(context)
        return OwnedChildActionUnit(spec['child']['key'], dispatch,
            decision_index=index, collect=collect)

    def dispatch_commission(self, source, index, spec):
        self.validate_child_choice(source, spec['child']['role'], original=True)
        if self.annotation_child_roles is not None and (
                spec['run_id'] != self.run_id
                or spec['parent']['episode_id'] != source.episode_id
                or _plain(spec['parent']['path']) != _plain(source.path)):
            raise ValueError('commission_parent_identity_mismatch')
        if self.annotation_child_roles is not None:
            original = self.store.db.execute('SELECT spec FROM runtime_commission_intents '
                'WHERE run_id=? AND parent_episode_id=? AND handle=?',
                (self.run_id, source.episode_id, spec['handle'])).fetchone()
            if original is None or json.loads(original[0]) != _plain(spec):
                raise ValueError('commission_intent_identity_mismatch')
        with self.journal.measure('runtime_actions', source.episode_id, index):
            status = self.commissions.dispatch(spec['handle'])
        if self.execution_handle is not None and self.progress_provider is not None:
            action = self.journal.row('runtime_actions', source.episode_id, index)
            selected_at = json.loads(action['result'])['selected_at']
            self.progress_provider.expose(self.execution_handle, operation_key=spec['operation_key'],
                dependencies=[{'handle': spec['handle'], 'kind': 'episode', 'relation_ref': _digest(spec),
                    'observed_at': selected_at, 'state': 'pending'}])
            self.progress_provider.flush_notifications()
        if status.get('failure') is not None:
            source.feedback = status['failure']
        return status

    def recover_commissions(self, source):
        by_handle = {item['handle'] for item in self.commissions.pending(source.episode_id)['items']}
        for spec in self.commissions.recover_selected(source.episode_id):
            if spec['handle'] in by_handle:
                if self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE:
                    try:
                        status = self.execution_backend.status(spec['handle'])
                    except KeyError:
                        pass  # An unpublished original intent still needs dispatch.
                    else:
                        if (status['failure'] is not None
                                and status['execution_identity'] is None
                                and not status['return_available']):
                            # A recorded bootstrap failure is not permission to
                            # retry work. Deliver it after source-state replay.
                            continue
                # This restores an already selected invocation. C2 inspects its
                # original process incarnation and never repeats claimed work.
                action = self.store.db.execute("SELECT decision_index FROM runtime_actions WHERE run_id=? "
                    "AND episode_id=? AND json_extract(result,'$.pending_handle')=?",
                    (self.run_id, source.episode_id, spec['handle'])).fetchone()
                self.dispatch_commission(source, action[0], spec)

    def settle_unclaimed_child_failures(self, source):
        """Account for an attempted bootstrap without inventing child science."""
        if (self.episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE
                or self.journal.row('runtime_episodes', source.episode_id)['state'] != 'active'):
            return
        rows = self.store.db.execute("SELECT decision_index,result FROM runtime_actions "
            "WHERE run_id=? AND episode_id=? AND json_extract(result,'$.status')='pending' "
            "AND json_extract(result,'$.pending_handle') IS NOT NULL ORDER BY decision_index",
            (self.run_id, source.episode_id)).fetchall()
        for row in rows:
            handle = json.loads(row['result'])['pending_handle']
            try:
                status = self.execution_backend.status(handle)
            except KeyError:
                continue  # Recovery publishes original intents before collection.
            if (status['failure'] is None or status['execution_identity'] is not None
                    or status['return_available']):
                continue
            index = row['decision_index']
            with self.store.transaction():
                original = self.journal.row('runtime_actions', source.episode_id, index)
                if original['result'] != row['result'] or original['credit'] is not None:
                    raise WorkflowError('unclaimed_child_failure_action_changed')
                outcome = {'status': 'failed', 'execution_handle': handle,
                    'record_refs': [], 'changed_record_refs': [], 'feedback': status['failure']}
                self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                    'decision_index': index, 'action': original['action'],
                    'result': _json(outcome), 'credit': None})
                credit = self.source_credit_view(source)['credit']
                self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                    'decision_index': index, 'action': original['action'],
                    'result': _json(outcome), 'credit': credit})
                self.completions.stage(source.episode_id, index, label=f'child_{index}',
                    kind='own_action', controller_input=self.controller_value(source, index, credit),
                    child_return=None)
                source.last_outcome, source.last_outcome_index = outcome, index
                source.feedback = status['failure']
                source.checkpoint()

    def pending_delivery(self, source, delivery_ref=None):
        if self.episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE:
            return None
        rows = self.store.db.execute('SELECT a.* FROM runtime_report_attempts a '
            'JOIN runtime_actions work ON work.run_id=a.run_id '
            'AND work.episode_id=a.parent_episode_id AND work.decision_index=a.decision_index '
            'WHERE a.run_id=? AND a.parent_episode_id=? AND a.failure IS NOT NULL '
            'AND (work.result IS NULL OR json_extract(work.result,\'$.status\')=\'pending\') '
            'ORDER BY a.decision_index', (self.run_id, source.episode_id)).fetchall()
        for original in rows:
            if delivery_ref is None or original['delivery_ref'] == delivery_ref:
                return original
        return None

    def delivery_resolution_inputs(self, source, delivery_ref, context):
        original = self.pending_delivery(source, delivery_ref)
        if original is None:
            raise WorkflowError('delivery_resolution_requires_owned_unfinished_child')
        latest = self.store.db.execute('SELECT * FROM runtime_report_attempts WHERE run_id=? '
            'AND parent_episode_id=? AND delivery_ref=? ORDER BY decision_index DESC LIMIT 1',
            (self.run_id, source.episode_id, delivery_ref)).fetchone()
        pending = {'delivery_ref': delivery_ref,
            'original_decision_index': original['decision_index'],
            'original_contract': json.loads(original['contract']),
            'latest_contract': json.loads(latest['contract']),
            'failure': None if latest['failure'] is None else json.loads(latest['failure'])}
        schema = _object({'selection': {'anyOf': [_object({
            'kind': {'type': 'string', 'const': 'redeliver_report'},
            'delivery_ref': {'type': 'string', 'const': delivery_ref},
            'purpose': {'type': 'string'}, 'schema_json': {'type': 'string'}})]},
            # Enforce the frozen interpretation in apply_response. Encoding
            # the entire object as const becomes an object-valued enum in
            # the provider wire schema, which its structured output rejects.
            'report_update': source.interpret_schema})
        return {**context, 'pending_child_delivery': pending, 'tools': [],
            'job_episode_options': []}, schema

    async def resolve_pending_deliveries(self, source, view, *, only_delivery_ref=None):
        original = self.pending_delivery(source, only_delivery_ref)
        if original is None:
            return
        delivery_ref = original['delivery_ref']
        source._delivery_resolution_ref = delivery_ref
        try:
            while True:
                result = await source.next(view, delivery_ref=delivery_ref)
                if not isinstance(result, ReportRedelivery):
                    raise WorkflowError('delivery_resolution_requires_report_operation')
                latest = self.store.db.execute('SELECT failure FROM runtime_report_attempts '
                    'WHERE run_id=? AND parent_episode_id=? AND delivery_ref=? '
                    'ORDER BY decision_index DESC LIMIT 1',
                    (self.run_id, source.episode_id, delivery_ref)).fetchone()
                if latest is not None and latest['failure'] is None:
                    return
        finally:
            source._delivery_resolution_ref = None

    async def next_branch_return(self, source, view):
        """Complete existing owned work while selection is numerically yielded.

        Keep the same active parent and receipt boundary. Durable notifications
        release execution until a return exists; they are not episode actions.
        This does not recreate an exited parent process or reopen closed history.
        """
        while True:
            with self.execution_backend._connect() as events:
                cursor = events.execute('SELECT coalesce(max(cursor),0) FROM events').fetchone()[0]
            # A receipt may already be committed/acknowledged, including after
            # interruption before its controller observation. Replay it first.
            slot = self.completions.slot(source.episode_id, view.units_consumed)
            if slot is not None:
                return self.completed_unit(source, slot)
            # Saved source state follows the old completed history. Applying it
            # after a fresh admission would overwrite that return's feedback.
            source.restore_checkpoint()
            slot = self.next_return(source)
            if slot is not None:
                return self.completed_unit(source, slot)
            await self.resolve_pending_deliveries(source, view)
            slot = self.completions.slot(source.episode_id, view.units_consumed)
            if slot is not None:
                return self.completed_unit(source, slot)
            # Collection can consume failed/interrupted child returns without a
            # completed unit. Inspect the remaining commitments after admission.
            pending = self.commissions.pending(source.episode_id)['items']
            if not pending:
                return None
            conditions = [item.get('suspension') for item in pending]
            state = source._execution_context._suspension
            state.update({'kind': 'owned_child_return', 'handles': [item['handle'] for item in pending]}
                if all(condition is not None for condition in conditions) else None)
            try:
                await self.execution_backend.wait_events({'version': 'event_condition_v1',
                    'events': [{'handle': item['handle'], 'event': event, 'after_cursor': cursor}
                        for item in pending for event in ('returned', 'state_changed')], 'reconsider_at': None})
            finally:
                state.update(None)

    def returned_request(self, spec):
        child, recorded = spec['child'], spec['child']['request']
        message, scope = recorded['message'], child['scope']
        role, schema = child['role'], recorded['report_contract']['measurements']['schema']
        declaration = message.get('report_contract_declaration')
        if declaration is not None:
            validate_saved_fact_form(child_role=role, submitted_schema_json=declaration['submitted_schema_json'],
                                     expanded_schema=schema, declaration=declaration)
        assignment = message.get('job_assignment')
        context = BindingContext(spec['run_id'], child['episode_id'], role, child['path'], scope,
            message.get('episode_assignment', {}), recorded)
        def validate(value):
            self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema,
                context=context)
        contract = TypedReportContract(recorded['report_contract']['decision'], schema,
            self.resolver(scope, assignment=assignment, grain=role, context=context), validate)
        if contract.as_record() != recorded['report_contract']:
            raise WorkflowError('original_return_contract_changed')
        return EpisodeRequest(EpisodeGoal.from_record(recorded['goal']), Record(message), contract)

    def next_return(self, source, *, only_handle=None):
        self.settle_unclaimed_child_failures(source)
        for pending in self.commissions.pending(source.episode_id)['items']:
            self.execution_backend.supervise_receiver(pending['handle'])
        cursor = 0
        while True:
            page = self.execution_backend.return_page(source.episode_id, cursor, 16)
            for item in page['items']:
                if only_handle is not None and item['handle'] != only_handle:
                    continue
                status = self.execution_backend.status(item['handle'])
                if status['acknowledgment_id'] is not None:
                    continue
                spec = self.execution_backend.load_commission(item['handle'])
                action = self.store.db.execute("SELECT decision_index FROM runtime_actions WHERE run_id=? "
                    "AND episode_id=? AND json_extract(result,'$.pending_handle')=?",
                    (self.run_id, source.episode_id, item['handle'])).fetchone()
                if action is None:
                    # Admission may have committed just before the backend ACK
                    # was lost. Restore the original committed admission only.
                    installed = self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                        "AND name='runtime_return_admissions'").fetchone()
                    saved = (self.store.db.execute('SELECT admission FROM runtime_return_admissions '
                        'WHERE run_id=? AND return_id=?', (self.run_id, item['return_id'])).fetchone()
                        if installed else None)
                    if saved is None:
                        raise WorkflowError('return_has_no_original_pending_action')
                    admission = load_return_admission(self.store, self.run_id, item['return_id'])
                    observed = self.store.db.execute('SELECT 1 FROM runtime_observations WHERE run_id=? '
                        'AND episode_id=? AND json_extract(observation,\'$.decision_index\')=?',
                        (self.run_id, source.episode_id, admission['original_decision_index'])).fetchone()
                    if observed is not None or admission['state'] == 'receiver_closed':
                        self.execution_backend.acknowledge(item['handle'], item['return_id'], admission['admission_id'])
                    continue
                index = action[0]
                request = self.returned_request(spec)
                returned = self.execution_backend.load_return(item['handle'], item['return_id'])
                receiver = ReceiverBindingV1(self.store, self.journal, index, request.report_contract,
                    lambda form: None,
                    lambda form: self.receive_form(source, form, request.report_contract.schema, index),
                    lambda: self.source_credit_view(source)['credit'],
                    lambda original_index, credit: self.controller_value(source, original_index, credit),
                    defer_failed_delivery=self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE)
                slot = None
                with self.store.transaction():
                    parent_open = self.journal.row('runtime_episodes', source.episode_id)['state'] == 'active'
                    with (self.journal.measure('runtime_actions', source.episode_id, index)
                          if parent_open else nullcontext()):
                        admission = admit_return(spec, returned, receiver)
                    if admission['controller_input'] is not None:
                        original_action = self.journal.row('runtime_actions', source.episode_id, index)
                        outcome = json.loads(original_action['result'])
                        outcome['pending_work_after_action'] = self.pending_work(source)
                        self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                            'decision_index': index, 'action': original_action['action'],
                            'credit': original_action['credit'], 'result': _json(outcome)})
                        slot = self.completions.stage(source.episode_id, index, label=spec['child']['key'],
                            kind='child_return', controller_input=Record(admission['controller_input']),
                            child_return={'handle': item['handle'], 'return_id': item['return_id'],
                                'admission_id': admission['admission_id']})
                    if admission['state'] == 'delivery_pending':
                        source.feedback = admission['delivery_failure']
                        source.checkpoint()
                    elif admission['state'] != 'receiver_closed':
                        recorded = self.journal.row('runtime_actions', source.episode_id, index)
                        source.last_outcome, source.last_outcome_index = json.loads(recorded['result']), index
                        if source.last_outcome.get('feedback') is not None:
                            source.feedback = source.last_outcome['feedback']
                        source.checkpoint()
                if admission['state'] == 'receiver_closed':
                    self.execution_backend.acknowledge(item['handle'], item['return_id'], admission['admission_id'])
                if admission['state'] == 'receiver_closed':
                    # The return stays durable without promoting an old
                    # pending action into a closed parent's live source state.
                    continue
                if slot is not None:
                    return slot
                source.feedback = admission['delivery_failure']
            if not page['items']:
                return None
            cursor = page['next_cursor']

    def archive_reference(self, descriptor):
        return ArchivedRecord(self.archive.path / descriptor['file'], descriptor['sha256'], descriptor['index_sha256'])

    def publish_outcome(self, source, index):
        if self.execution_handle is None or self.progress_provider is None:
            return
        row = self.journal.row('runtime_actions', source.episode_id, index)
        result = json.loads(row['result'])
        dependency = getattr(self.progress_provider.job_provider, 'dependency_from_outcome', None)
        if dependency is not None and result.get('status') in {'completed', 'partial'}:
            key = f'{self.run_id}:{source.episode_id}:{index}'
            relationship = dependency(self.binding_context(source), result, operation_key=key)
            if relationship is not None:
                self.progress_provider.expose(self.execution_handle, operation_key=key+':physical_target',
                    dependencies=[relationship])
        references = result.get('record_refs', [])
        if references:
            self.progress_provider.expose(self.execution_handle,
                operation_key=f'{self.run_id}:{source.episode_id}:{index}:committed_outcome',
                committed_record_refs=references)
        self.progress_provider.flush_notifications()

    def expose_assigned_job(self, source):
        if self.execution_handle is None or self.progress_provider is None:
            return
        provider = self.progress_provider.job_provider
        dependency = getattr(provider, 'dependency', None)
        if dependency is None:
            return
        spec = self.execution_backend.load_commission(self.execution_handle)
        if spec['child']['episode_id'] != source.episode_id:
            # Preparing a prospective child does not assign that child's job
            # relationship to the currently executing parent.
            return
        operation_key = spec['operation_key'] + ':assigned_job'
        with self.store.transaction():
            relationship = dependency(spec, operation_key=operation_key)
            if relationship is not None:
                self.progress_provider.expose(self.execution_handle,
                    operation_key=operation_key, dependencies=[relationship])
        if not self.store.db.in_transaction:
            self.progress_provider.flush_notifications()

    def completed_unit(self, source, slot):
        index = slot['original_decision_index']
        action = self.journal.row('runtime_actions', source.episode_id, index)
        source.last_outcome, source.last_outcome_index = json.loads(action['result']), index
        if slot['kind'] == 'own_action':
            if json.loads(action['action']).get('kind') == 'redeliver_report':
                attempt = self.store.db.execute('SELECT * FROM runtime_report_attempts '
                    'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                    (self.run_id, source.episode_id, index)).fetchone()
                contract = self.saved_delivery_contract(attempt['child_episode_id'],
                    json.loads(attempt['contract']))
                report = contract.admit(json.loads(attempt['form']), audit_identifiers=())
                return ReportAcquisitionLeaf(slot, extract=lambda value: Record(value['controller_input']),
                    result=lambda _, value: value, label=slot['label'], decision_index=index,
                    report_delivery=ReportRedelivery(attempt['child_episode_id'], report=report))
            return ActionLeaf(slot, extract=lambda value: Record(value['controller_input']),
                result=lambda _, value: value, label=slot['label'], decision_index=index)
        reference = slot['child_return']
        spec = self.execution_backend.load_commission(reference['handle'])
        returned = self.execution_backend.load_return(reference['handle'], reference['return_id'])
        admission = load_return_admission(self.store, self.run_id, reference['return_id'])
        # Ownership ends only after on_unit records this original observation.
        # Replaying a staged receipt must not acknowledge unobserved credit.
        if admission['state'] == 'execution_failed':
            source.feedback = admission['delivery_failure']
            return ActionLeaf(slot, extract=lambda value: Record(value['controller_input']),
                result=lambda _, value: value, label=slot['label'], decision_index=index)
        request = self.returned_request(spec)
        child, completion = spec['child'], returned['completion']
        record = EpisodeRecord(child['role'], child['key'], completion['units_consumed'], completion['ended_by'],
            (), None, request, path=tuple(tuple(part) for part in child['path']),
            end_reason=completion['end_reason'], episode_ref=EpisodeRef(self.run_id, child['path']),
            archived_record=self.archive_reference(returned['episode_archive']))
        result = Record(self.archive_reference(returned['result_archive']).load())
        def report(*_):
            if admission['report'] is None:
                failure = self.store.db.execute('SELECT failure FROM runtime_report_attempts WHERE run_id=? '
                    'AND parent_episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                raise ReportDeliveryError(Record(json.loads(failure[0])))
            return admission['report']
        delivery_contract = (request.report_contract if 'delivery_contract' not in admission else
            self.saved_delivery_contract(child['episode_id'], admission['delivery_contract']))
        return ReturnedActionUnit(slot['label'], record, result, request,
            lambda *_: Record(slot['controller_input']), report, decision_index=index,
            delivery_contract=lambda: delivery_contract)

    def _closed_child_commission(self, source, selection, index):
        """Replay one wholly closed in-process commission from its real archives.

        This is not admission for another child. The original action, observed
        input, successful return and both closed records must agree before any
        assignment preparation, initialization or receipt delivery is skipped.
        """
        if (self.execution_binding is not None or self.receipts is None
                or self.native_timing_information is not None
                or selection.get('kind') != 'episode_child'):
            return None

        def require(condition, code):
            if not condition:
                raise WorkflowError('closed_commission_' + code)

        def same(left, right):
            return _json(left) == _json(right)

        def archived(row):
            descriptor = json.loads(row['archive'])
            require(type(descriptor) is dict
                and set(descriptor) == {'file', 'sha256', 'index_sha256'}
                and type(descriptor['file']) is str
                and Path(descriptor['file']).name == descriptor['file']
                and descriptor['file'].endswith('.json')
                and all(type(descriptor[key]) is str and len(descriptor[key]) == 64
                    and all(char in '0123456789abcdef' for char in descriptor[key])
                    for key in ('sha256', 'index_sha256')), 'archive_invalid')
            reference = self.archive_reference(descriptor)
            try:
                value = reference.load()
            except (OSError, ValueError) as error:
                raise WorkflowError('closed_commission_archive_invalid') from error
            completion = json.loads(row['completion'])
            path = json.loads(row['path'])
            request = json.loads(row['request'])
            episode_ref = EpisodeRef(self.run_id, path)
            require(type(completion) is dict and set(completion) == {'ended_by', 'actions'}
                and type(completion['actions']) is int and completion['actions'] >= 0
                and type(value) is dict and type(value.get('units')) is list
                and type(value.get('units_consumed')) is int
                and value['units_consumed'] == len(value['units']) == completion['actions']
                and value.get('ended_by') == completion['ended_by']
                and same(value.get('request'), request)
                and same(value.get('goal'), request['goal'])
                and same(value.get('path'), path)
                and same(value.get('episode_ref'), episode_ref.as_record())
                and value.get('episode_id') == episode_ref.episode_id == row['episode_id']
                and value.get('run_id') == self.run_id == row['run_id']
                and value.get('scope_level') == path[-1][0]
                and value.get('scope_key') == path[-1][1], 'archive_conflict')
            return reference, value

        with self.store.read_snapshot():
            parent = self.journal.row('runtime_episodes', source.episode_id)
            if (parent is None or parent['state'] != 'yielded'
                    or parent['completion'] is None or parent['archive'] is None):
                return None
            require(type(index) is int and index >= 0, 'action_index_invalid')
            action = self.journal.row('runtime_actions', source.episode_id, index)
            require(action is not None, 'original_action_required')
            require(same(json.loads(action['action']), selection), 'selection_conflict')
            if action['result'] is None:
                return None
            outcome = json.loads(action['result'])
            if type(outcome) is not dict or outcome.get('status') != 'completed':
                return None
            call = self.journal.row('runtime_model_calls', source.episode_id, index)
            require(call is not None and call['purpose'] == 'decision'
                and call['response'] is not None, 'original_call_required')
            try:
                original_call = json.loads(call['request'])
                response = _decode_recorded_action_response(json.loads(call['response']),
                    original_call['schema'], recorded_selection=selection)
            except (ValueError, KeyError, TypeError) as error:
                raise WorkflowError('closed_commission_call_conflict') from error
            require(same(response.get('selection'), selection), 'call_conflict')
            role = selection['role']
            require(role in self.grains and role in self.episode_bindings.roles, 'role_conflict')
            identity = Episode.identity(self.context, self.grains[role], f'child_{index}',
                parent_path=source.path)
            child_row = self.journal.row('runtime_episodes', identity.episode_id)
            require(child_row is not None, 'original_child_required')
            if (child_row['state'] != 'yielded' or child_row['completion'] is None
                    or child_row['archive'] is None):
                return None
            specialist = self.specialist(source)
            allowed = (self.available_child_roles(source) if self.annotation_child_roles is not None else
                specialist.allowed_children(self.binding_context(source), self.services.capabilities())
                if specialist is not None else self.episode_bindings.entry_roles)
            require(role in allowed, 'role_not_available')
            scope = self.store.validate_scope(selection['scope'], parent_scope=source.scope)
            from .episode_return_records import EpisodeReturnRecords
            records = EpisodeReturnRecords(self.store, self.run_id, failure_prefix='closed_commission_')
            context = self.binding_context(source)
            records.authenticate(context)
            attempt = self.store.db.execute('SELECT failure FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (self.run_id, source.episode_id, index)).fetchone()
            if attempt is not None and attempt['failure'] is not None:
                # Replay the original failed boundary through its ordinary
                # cached child path before any later report redelivery.
                return None
            child, form, schema = records._attempt(context, index)
            require(child.episode_id == identity.episode_id and child.role == role
                and same(child.scope, scope), 'child_identity_conflict')
            assignment = _plain(child.assignment)
            if role == 'scientific_process':
                from .scientific_process_records import selector_selection
                binding = self.scientific_process_binding
                require(binding is not None and binding.restore_closed_process(child) is not None,
                    'scientific_request_conflict')
                binding.validate_context(child)
                selected_assignment = {**assignment,
                    'selection': selector_selection(assignment['selection'])}
                require(same(selection['assignment'], assignment)
                    or same(selection['assignment'], selected_assignment), 'assignment_conflict')
            # Other owners may materialize their public selection. The original
            # action/call above pins the raw representation; the request and
            # matching parent/child archives below pin its actual materialization.
            compiled, declaration = self.expanded_contract_form(source, selection, index, role)
            request_value = _plain(child.request)
            require(same(compiled, schema)
                and same(request_value['message'].get('report_contract_declaration'), declaration)
                and same(request_value['message'].get('initial_report'),
                    parse_json_object(self.child_initial_report_input(source, selection, role)))
                and request_value['report_contract']['decision'] == selection['purpose']
                and same(EpisodeGoal.child(source.request.goal, objective=selection['goal'],
                    result_contract=schema).as_record(), request_value['goal']), 'request_conflict')
            for current in (context, child):
                require(same(current.request['message'].get('knowledge_inheritance'),
                    self.receipts.manifest(current.episode_id)), 'inheritance_conflict')
            references = records.recorded_admission_references(context, form, schema, index)
            if references is None:
                # Paged members and old outcomes without a recorded ordinary
                # receipt projection retain their existing delivery path.
                return None
            projected, unsupported = [], []
            def reference_projection(reference, namespace):
                if namespace == 'hpc_model' and child.role in {'hpc', 'hpc_prediction', 'hpc_execution'}:
                    owner = self.episode_bindings.for_role(child.role)
                    return owner.frozen_reference(child, reference, namespace)
                if namespace == 'restriction_enzyme' and child.role == 'scientific_process':
                    from .restriction_mapping_references import RestrictionMappingReferences
                    return RestrictionMappingReferences(self.store, self.run_id).frozen_reference(
                        child, reference, namespace)
                if (isinstance(namespace, str)
                        and namespace.startswith('native_hmmer_preparation_')):
                    from .native_hmmer_preparation_returns import IDENTIFIER_NAMESPACES
                    if namespace in IDENTIFIER_NAMESPACES:
                        owner = (self.episode_bindings.for_role('results')
                            if 'results' in self.episode_bindings.roles else None)
                        reader = getattr(owner, 'native_hmmer_preparation_returns', None)
                        return (False if reader is None else
                            reader.frozen_reference(child, reference, namespace))
                if namespace == 'bvbrc_minhash_genome':
                    owner = (self.episode_bindings.for_role('results')
                        if 'results' in self.episode_bindings.roles else None)
                    execution = getattr(owner, 'api_execution', None)
                    reader = getattr(execution, 'minhash', None)
                    return (False if reader is None else
                        reader.frozen_reference(child, reference, namespace))
                from .domain import RECORD_SCHEMAS
                if reference not in references:
                    return False
                record = self.store.get(reference)
                if (not isinstance(record, Mapping) or record.get('id') != reference
                        or not isinstance(record.get('record_type'), str)):
                    return False
                kind = record['record_type']
                scoped = reference in self.store.reference_subset([reference], scope)
                if (not scoped and kind == 'artifact' and namespace == 'artifact'
                        and child.role == 'results'):
                    # Selected Addgene sequence Files have their original rich
                    # typed-return owner rather than a semantic record root.
                    # The child is closed; this owner authenticates its frozen
                    # acquisition/receipt bindings without reopening native data.
                    owner = (self.episode_bindings.for_role('results')
                        if 'results' in self.episode_bindings.roles else None)
                    execution = getattr(owner, 'api_execution', None)
                    reader = getattr(execution, 'addgene_returns', None)
                    scoped = reader is not None and reader.resolve_own(child, reference, namespace) is True
                if not scoped:
                    return False
                execution_alias = {'execution_result': {'source', 'artifact'},
                    'execution_handoff': {'source'}}.get(namespace)
                if (namespace in RECORD_SCHEMAS and namespace != kind
                        or execution_alias is not None and kind not in execution_alias
                        or namespace == 'subject'
                            and kind not in {'input', 'feature', 'product', 'read_subject'}):
                    return False
                if (kind == 'collection_member' or namespace not in {None, 'record', kind}
                        and execution_alias is None
                        and not (namespace == 'subject'
                            and kind in {'input', 'feature', 'product', 'read_subject'})):
                    unsupported.append(reference)
                projected.append(reference)
                return True
            try:
                # The shared semantic validator handles local native $defs and
                # conditional branches. Declared preparation identifiers resolve
                # against frozen facts without adding record grants. Live
                # admission hooks can reopen private producers
                # or write custody, so they are never called during this replay.
                validate_form(form, schema, reference_projection)
            except (ValueError, KeyError, TypeError) as error:
                raise WorkflowError('closed_commission_reference_projection_conflict') from error
            if unsupported:
                return None
            receiver_evidence = None
            if set(references) != set(projected):
                # The receiving host can derive a tool-specific attribution
                # after admitting the typed form. These records belong to the
                # original completed action, not to the child's form. Replay
                # their frozen receipt evidence without calling producers or
                # granting any new reference.
                require(set(projected) <= set(references), 'reference_projection_conflict')
                saved = self.store.db.execute('SELECT data FROM runtime_estimation_contexts WHERE run_id=? '
                    'AND episode_id=? AND decision_index=?', (self.run_id, source.episode_id, index)).fetchone()
                receiver_evidence = (json.loads(saved['data']).get('current_completion_evidence')
                                     if saved is not None else None)
                require(isinstance(receiver_evidence, dict)
                    and receiver_evidence.get('run_id') == self.run_id
                    and receiver_evidence.get('episode_id') == source.episode_id
                    and receiver_evidence.get('original_decision_index') == index
                    and receiver_evidence.get('action_kind') == 'episode_child'
                    and type(receiver_evidence.get('received_record_refs')) is list
                    and set(receiver_evidence['received_record_refs']) == set(references),
                    'receiver_attribution_evidence_conflict')
                for reference in set(references)-set(projected):
                    record = self.store.get(reference)
                    require(record.get('origin') == 'tool'
                        and reference_projection(reference, record['record_type']),
                        'receiver_attribution_reference_conflict')
            # Canonical form storage can reorder object properties. Validate
            # exact reference membership, then retain the original admission
            # order in the recorded boundary below.
            require(set(references) == set(projected), 'reference_projection_conflict')
            require(type(outcome.get('changed_record_refs')) is list
                and set(outcome['changed_record_refs']) <= set(references), 'changed_references_conflict')
            frozen = self.journal.row('runtime_forms', child.episode_id)
            require(frozen is not None and same(json.loads(frozen['form']), form), 'frozen_form_conflict')
            _, parent_archive = archived(parent)
            child_reference, child_archive = archived(child_row)
            observed = list(self.store.db.execute('SELECT unit_index,observation FROM runtime_observations '
                "WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?",
                (self.run_id, source.episode_id, index)))
            require(len(observed) == 1, 'original_observation_required')
            sequence = observed[0]['unit_index']
            require(type(sequence) is int and 0 <= sequence < len(parent_archive['units']),
                'observation_index_conflict')
            unit = parent_archive['units'][sequence]
            unit_ref = UnitRef(EpisodeRef(self.run_id, source.path).episode_id, sequence)
            require(receiver_evidence is None or same(receiver_evidence.get('unit_ref'), unit_ref.as_record()),
                'receiver_attribution_unit_conflict')
            require(same(unit.get('unit_ref'), unit_ref.as_record())
                and unit.get('unit_id') == unit_ref.unit_id
                and unit.get('unit_label') == f'child_{index}'
                and same(unit.get('child'), child_archive)
                and same(unit.get('child_result'), {'form': form})
                and same(json.loads(observed[0]['observation']), {
                    'label': unit['unit_label'], 'credit': unit['controller_input'],
                    'step': unit['controller_step'], 'unit_ref': unit['unit_ref'],
                    'decision_index': index}), 'observation_conflict')
            controller_input = unit['controller_input']
            from .episode_journal import decode_credit
            from .numerical import validate_task_credit
            require(type(controller_input) is dict, 'credit_conflict')
            validate_task_credit(controller_input.get('credit'))
            require(controller_input['credit'] == decode_credit(action['credit'])
                and type(controller_input.get('estimation_action_index', index)) is int
                and controller_input.get('estimation_action_index', index) == index, 'credit_conflict')
            expected_update = dict(record_id=child.episode_id, goal=request_value['goal'],
                completion={key: child_archive[key] for key in ('ended_by', 'end_reason', 'units_consumed')},
                controller_input=controller_input, report=form,
                report_contract=request_value['report_contract'], delivery_failures=[])
            require(same(unit.get('episode_update'), expected_update), 'delivered_report_conflict')

            def admitted(value):
                require(same(value, form), 'form_conflict')
                return references

            contract = TypedReportContract(selection['purpose'], schema, lambda *_: False,
                recorded_admission=admitted)
            require(same(contract.as_record(), request_value['report_contract']), 'contract_conflict')
            request = EpisodeRequest(EpisodeGoal.from_record(request_value['goal']),
                Record(request_value['message']), contract)
            record = EpisodeRecord(role, f'child_{index}', child_archive['units_consumed'],
                child_archive['ended_by'], (), child_archive['controller_state'], request,
                path=child.path, end_reason=child_archive['end_reason'],
                episode_ref=EpisodeRef(self.run_id, child.path), archived_record=child_reference)
            source.last_outcome, source.last_outcome_index = outcome, index
            return ReturnedActionUnit(unit['unit_label'], record, Record({'form': form}), request,
                lambda *_: Record(controller_input), lambda *_: form, decision_index=index)

    def specialist(self, source):
        path = getattr(source, 'path', ())
        if not path:
            return None
        role = path[-1][0]
        return (self.episode_bindings.for_role(role)
                if role in self.episode_bindings.roles else None)

    def validate_contract_information_configuration(self, profile):
        if profile is not None and (profile != CONTRACT_INFORMATION_PROFILE
                or self.decision_protocol != DECISION_EXCHANGE_PROTOCOL):
            raise ContractInformationError('contract_information_requires_pending_decision_protocol',
                                           'decision_protocol')
        return profile

    def contract_information_profile(self, source):
        if source is None:
            return None
        profile = self.episode_bindings.contract_information_profile(self.binding_context(source))
        return self.validate_contract_information_configuration(profile)

    def freeze_contract_information(self, source, context, schema):
        """Freeze declared instruction contracts, never source facts or work."""
        roles = list(self.available_child_roles(source))
        facts = {role: _plain(self.return_contract_sources(role)) for role in roles}
        return {'version': CONTRACT_INFORMATION_PROFILE, 'permitted_child_roles': roles,
            'fact_sources_by_role': facts, 'fact_sources_sha256': _digest(facts),
            'catalog_sha256': _digest(context.get('tools', [])), 'action_schema_sha256': _digest(schema),
            'exchange_schema': json.loads(_json(source.exchange_schema(schema))),
            'instructions': source.instructions(context) + '\n' + DECISION_EXCHANGE_INSTRUCTIONS}

    def validate_contract_information(self, saved):
        """Check original host schema/catalog associations without a factory."""
        record, context, schema = saved.get('contract_information'), saved['context'], saved['schema']
        keys = {'version', 'permitted_child_roles', 'fact_sources_by_role', 'fact_sources_sha256',
                'catalog_sha256', 'action_schema_sha256', 'exchange_schema', 'instructions'}
        if (not isinstance(record, dict) or set(record) != keys or record['version'] != CONTRACT_INFORMATION_PROFILE
                or context.get('contract_information_profile') != CONTRACT_INFORMATION_PROFILE
                or type(record['instructions']) is not str
                or record['fact_sources_sha256'] != _digest(record['fact_sources_by_role'])
                or record['catalog_sha256'] != _digest(context.get('tools', []))
                or record['action_schema_sha256'] != _digest(schema)):
            raise WorkflowError('original_contract_information_mismatch')
        roles = record['permitted_child_roles']
        if (not isinstance(roles, list) or any(type(role) is not str or not role for role in roles)
                or len(set(roles)) != len(roles)
                or not isinstance(record['fact_sources_by_role'], dict)
                or any(not isinstance(rows, dict) for rows in record['fact_sources_by_role'].values())
                or set(record['fact_sources_by_role']) != set(roles)):
            raise WorkflowError('original_return_contract_roles_mismatch')
        catalog = context.get('tools', [])
        if (not isinstance(catalog, list)
                or any(not isinstance(row, dict) or not {'name', 'input_schema', 'description'} <= row.keys()
                    or type(row['name']) is not str or type(row['description']) is not str for row in catalog)
                or len({row['name'] for row in catalog}) != len(catalog)):
            raise WorkflowError('original_operation_catalog_mismatch')
        branches = schema['properties']['selection']['anyOf']
        tools = [row for row in branches if row.get('properties', {}).get('kind', {}).get('const') == 'tool']
        by_name = {row['properties']['tool']['const']: row for row in tools}
        if len(by_name) != len(tools) or set(by_name) != {row['name'] for row in catalog}:
            raise WorkflowError('original_operation_catalog_mismatch')
        for entry in catalog:
            branch = by_name[entry['name']]
            expected = _object({'kind': {'type': 'string', 'const': 'tool'},
                'tool': {'type': 'string', 'const': entry['name']},
                'arguments': _embedded_tool_schema(entry['input_schema'])})
            if 'argument_transport' in entry:
                if entry['argument_transport'] != CONTRACT_ARGUMENT_TRANSPORT:
                    raise WorkflowError('original_operation_transport_mismatch')
                expected['x-argument-transport'] = CONTRACT_ARGUMENT_TRANSPORT
            if _json(branch) != _json(expected):
                raise WorkflowError('original_operation_contract_mismatch')
        exchange = record['exchange_schema']
        try:
            alternatives = exchange['properties']['response']['anyOf']
            selected = _object({'response_type': {'type': 'string', 'const': 'select_action'}, **schema['properties']})
            selected['required'] = ['response_type', *schema['required']]
            lookups = alternatives[0]['properties']['lookup']['anyOf']
            child = next(row for row in lookups if row['properties'].get('view', {}).get('const') == 'child_options')
            names = {row['properties'].get('operation', {}).get('const') for row in lookups}
            if (alternatives[1] != selected or child['properties']['role']['enum'] != [None, *roles]
                    or not set(CONTRACT_INFORMATION_OPERATIONS) <= names):
                raise WorkflowError('original_contract_lookup_schema_mismatch')
        except (KeyError, TypeError, IndexError, StopIteration) as error:
            raise WorkflowError('original_contract_lookup_schema_mismatch') from error
        return record

    def pending_contract_information(self, source, decision_index):
        row = self.journal.row('runtime_model_calls', source.episode_id, decision_index)
        if row is None or row['purpose'] != 'decision':
            raise WorkflowError('original_contract_decision_unavailable')
        saved = json.loads(row['request'])
        return saved, self.validate_contract_information(saved)

    def contract_information_reply(self, saved, record, name, arguments):
        """Resolve only ORIGINAL declared information; this executes no tool."""
        if name == CONTRACT_INFORMATION_OPERATIONS[0]:
            return operation_contract_information(catalog=saved['context'].get('tools', []),
                                                  operation=arguments['operation'])
        facts = {role: {source: row for source, row in rows.items() if 'report_schema' in row}
                 for role, rows in record['fact_sources_by_role'].items()}
        return return_contract_information(facts_by_role=facts,
            permitted_child_roles=record['permitted_child_roles'], role=arguments['role'], source=arguments['source'])

    def freeze_literature_numerical_contracts(self, source, context, schema):
        """Freeze a bounded declaration surface only for fresh literature tasks."""
        from .literature_experimental_prompt import is_literature_experimental_context
        if not is_literature_experimental_context(context):
            return None
        roles = list(self.available_child_roles(source))
        builtins = {name: {'type': 'number' if name == 'credit' else 'array',
            'meaning': FACT_MEANINGS[name]} for name in FACT_SOURCES}
        facts = {role: builtins | _plain(self.report_sources(role)) for role in roles}
        return literature_numerical_contracts.freeze_contracts(facts_by_role=facts,
            permitted_child_roles=roles, action_schema=schema)

    def root_child_return_sources(self, source, role):
        """Ask this root's own binding what it needs from its child."""
        if not restricted_root(self, source):
            return ()
        bound = getattr(self.project_credit, 'child_return_sources', None)
        return tuple(bound(self.binding_context(source), role)) if bound is not None else ()

    def child_form_input(self, source, selection, role):
        if 'schema_json' in selection:
            return selection['schema_json']  # Preserve an original saved decision.
        sources = self.root_child_return_sources(source, role)
        if not sources:
            raise ContractError('child_return_form_required')
        return _json(self.project_credit.child_return_form(self.binding_context(source), role))

    def child_initial_report_input(self, source, selection, role):
        if 'initial_report_json' in selection:
            return selection['initial_report_json']  # Preserve an original saved decision.
        if not self.root_child_return_sources(source, role):
            raise ContractError('child_initial_report_required')
        return '{}'

    def expanded_contract_form(self, source, selection, index, role, *, original_child=True):
        """Resolve a chosen form from original pending or saved child records."""
        schema_json = self.child_form_input(source, selection, role)
        if self.contract_information_profile(source) is None:
            submitted = parse_json_object(schema_json)
            if not literature_numerical_contracts.uses_fact_references(submitted):
                # Existing literal legacy forms retain their original compiler,
                # declaration=None and registration semantics, including local
                # references inside existing exact native documents.
                return _compile_form(schema_json, self.report_sources(role)), None
            if original_child:
                identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
                child = self.journal.row('runtime_episodes', identity.episode_id)
                if child is not None:
                    request = json.loads(child['request'])
                    declaration = request['message'].get('report_contract_declaration')
                    if declaration is None:
                        raise WorkflowError('original_report_contract_declaration_unavailable')
                    schema = validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json,
                        expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
                    return schema, declaration
            row = self.journal.row('runtime_model_calls', source.episode_id, index)
            saved = json.loads(row['request']) if row is not None and row['purpose'] == 'decision' else {}
            if literature_numerical_contracts.SAVED_MEMBER not in saved:
                # Never manufacture a declaration snapshot for an old saved
                # decision. Its original literal-only route stays unchanged.
                return _compile_form(schema_json, self.report_sources(role)), None
            record = literature_numerical_contracts.validate_frozen_contracts(saved)
            result = literature_numerical_contracts.expand_numerical_form(schema_json,
                child_role=role, saved=saved)
            schema = _compile_form(_json(result['expanded_schema']), record['source_types_by_role'][role],
                include_runtime_sources=False)
            validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json,
                expanded_schema=schema, declaration=result['declaration'])
            return schema, result['declaration']
        if original_child:
            identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
            row = self.journal.row('runtime_episodes', identity.episode_id)
            if row is not None:
                request = json.loads(row['request'])
                declaration = request['message'].get('report_contract_declaration')
                if declaration is None:
                    raise WorkflowError('original_report_contract_declaration_unavailable')
                schema = validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json,
                    expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
                return schema, declaration
        _, record = self.pending_contract_information(source, index)
        full = record['fact_sources_by_role']
        typed = {key: {name: row for name, row in rows.items() if 'report_schema' in row}
                 for key, rows in full.items()}
        result = expand_fact_form(schema_json, child_role=role, facts_by_role=typed,
                                  permitted_child_roles=record['permitted_child_roles'])
        # Existing fact-name/value-type checks remain authoritative. Only the
        # explicitly selected reference representation has been expanded.
        schema = _compile_form(_json(result['expanded_schema']), full[role])
        validate_saved_fact_form(child_role=role, submitted_schema_json=schema_json,
            expanded_schema=schema, declaration=result['declaration'])
        return schema, result['declaration']

    def _default_scientific_child_roles(self):
        return ((*(() if self.scientific_process_binding is not None else ('improvement',)),
            *(() if self.job_episodes is None else self.job_episodes.roles),
            *self.episode_bindings.entry_roles))

    def declared_child_roles(self, role):
        """Literal type edges; availability never creates additional roles."""
        if role in self.episode_bindings.roles:
            return tuple(self.episode_bindings.for_role(role).child_roles(role))
        if role == 'annotation' and self.annotation_child_roles is not None:
            return self.annotation_child_roles
        if role in self.grain_names:
            return self._default_scientific_child_roles()
        return ()

    def available_child_roles(self, source):
        declared = self.declared_child_roles(source.path[-1][0])
        specialist = self.specialist(source)
        roles = (tuple(specialist.allowed_children(self.binding_context(source),
            self.services.capabilities())) if specialist is not None else declared)
        if not set(roles) <= set(declared):
            raise WorkflowError('available_child_outside_declared_type_edges')
        if len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False):
            roles = tuple(role for role in roles if role == 'scientific_process')
        return roles

    def validate_child_choice(self, source, role, *, selection=None, original=False):
        """Enforce an explicit caller graph before commissioning side effects.

        Absent-marker runs retain their original selection/recovery semantics.
        These are role and ownership checks, not scientific suitability checks.
        """
        annotation_axes = len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False)
        if annotation_axes and role != 'scientific_process':
            raise ValueError('annotation_root_commissions_evidence_axes')
        if annotation_axes and selection is not None and not original:
            from .scientific_process_records import selection_fields
            assignment = selection.get('assignment', {})
            process = assignment.get('selection', {})
            axis = process[selection_fields(process)[0]]['option_id']
            ref = assignment.get('proposed_annotation_ref')
            scope = self.store.validate_scope(selection['scope'], source.scope)
            arms = self.source_credit_view(source)['credit']['arms']
            if sum(arm['proposed_annotation_ref'] == ref and arm['axis'] == axis
                    and arm['scope'] == scope for arm in arms) != 1:
                raise ValueError('axis_assignment_requires_one_received_annotation_subject_scope')
        if self.annotation_child_roles is None:
            return
        roles = (self.declared_child_roles(source.path[-1][0]) if original else
            self.available_child_roles(source))
        if role not in roles:
            raise ValueError('child_role_not_available_to_parent')
        if selection is not None:
            kind = selection.get('kind')
            selected_role = selection.get('role', 'improvement')
            if selected_role != role or kind == 'child' and role != 'improvement':
                raise ValueError('child_role_selection_mismatch')
            if (kind == 'job_child' and (self.job_episodes is None
                    or role not in self.job_episodes.roles or self.specialist(source) is not None)
                    or kind == 'episode_child' and role not in self.episode_bindings.roles):
                raise ValueError('child_kind_not_available_to_parent')

    def job_episode_options(self, source):
        if self.job_episodes is None or self.is_job_source(source):
            return None
        if self.annotation_child_roles is None:
            return self.job_episodes.describe()
        permitted = set(self.available_child_roles(source))
        options = {role: value for role, value in self.job_episodes.describe().items()
            if role in permitted and self.specialist(source) is None}
        return options or None

    def binding_context(self, source):
        return BindingContext(self.run_id, source.episode_id, source.path[-1][0],
            source.path, source.scope,
            source.request.message.as_record().get('episode_assignment', {}),
            source.request.as_record(), received_record_refs=(
                tuple(self.receipts.known(source.episode_id)) if self.receipts is not None else ()))

    def is_scientific_source(self, source):
        binding = self.specialist(source)
        return (binding.credit_kind(source.path[-1][0]) == 'scientific' if binding
                else not self.is_job_source(source))

    def permits_common_action(self, source, action):
        if (action == 'wait' and len(source.path) == 1
                and source.path[0][0] == 'annotation'
                and self.annotation_child_roles == ('literature',)
                and 'literature' in self.episode_bindings.roles
                and not getattr(self.episode_bindings.for_role('literature'), 'supports_wait', True)):
            # A literature-only root follows the same explicit wait capability
            # as its bound children; A106 retains its separate analysis use.
            return False
        if restricted_root(self, source) and action == 'tool':
            return self.receipts is not None
        binding = self.specialist(source)
        if binding is not None:
            return action in binding.permitted_common_actions(self.binding_context(source))
        return action in {'tool', 'wait'} or not self.is_job_source(source)

    def pending_work(self, source):
        from .pending_assignment import original_assignment
        if self.execution_binding is not None:
            return self.commissions.pending(source.episode_id)
        if source._execution_context is not None:
            invocations = source._execution_context._pending_children(source.path)
            if invocations:
                from .inprocess_waiting import public_child_handle
                return {'version': 'pending_work_v2', 'captured_at': _now(), 'items': [
                    # The scheduler's invocation ID is a child audit identity.
                    # Keep the operational model view separate so admitting
                    # that child's report does not poison the next input.
                    {'handle': public_child_handle(source.episode_id, item.handle), 'role': item.role,
                        'original_assignment': original_assignment(getattr(item, '_request', None),
                            getattr(item, 'decision_index', None)),
                        'lifecycle_state': 'returned' if item._task.done() else 'executing',
                        # The monitor's private correlation embeds the child
                        # audit ID. Its job and wake time remain useful here.
                        'suspension': ({key: value for key, value in item._suspension.condition.items()
                                if key != 'schedule_ref'}
                            if isinstance(item._suspension.condition, Mapping)
                            else item._suspension.condition),
                        'event_target': False,
                        'return_available': item._task.done(), 'selected_at': item.selected_at,
                        'observed_at': _now(), 'resource_selection': None,
                        'expectation_snapshot_refs': [], 'latest_progress_ref': None}
                        for item in invocations]}
        rows = self.store.db.execute("SELECT decision_index,json_extract(result,'$.pending_handle') AS handle, "
            "json_extract(result,'$.selected_at') AS selected_at FROM runtime_actions "
            "WHERE run_id=? AND episode_id=? AND json_extract(result,'$.status')='pending' "
            "AND json_extract(result,'$.pending_handle') IS NOT NULL ORDER BY decision_index",
            (self.run_id, source.episode_id))
        items = []
        for row in rows:
            status = self.execution_backend.status(row['handle'])
            spec = self.execution_backend.load_commission(row['handle'])
            items.append({'handle': row['handle'], 'role': spec['child']['role'],
                'original_assignment': original_assignment(spec['child']['request'], row['decision_index']),
                'lifecycle_state': status['lifecycle_state'], 'selected_at': row['selected_at'],
                'observed_at': status['observed_at'], 'resource_selection': spec['resource_selection'],
                'expectation_snapshot_refs': spec['expectation_snapshot_refs'],
                'latest_progress_ref': None, 'return_available': status['return_available'],
                'suspension': status.get('suspension'), 'event_target': True})
        return {'version': 'pending_work_v2', 'captured_at': _now(), 'items': items}

    def pending_handles(self, source):
        return [item['handle'] for item in self.pending_work(source)['items']]

    def last_observed_credit(self, source):
        row = self.store.db.execute("SELECT json_extract(observation,'$.credit.credit') "
            "FROM runtime_observations WHERE run_id=? AND episode_id=? "
            'ORDER BY unit_index DESC LIMIT 1', (self.run_id, source.episode_id)).fetchone()
        return (row[0] if row is not None else
                self.journal.row('runtime_episodes', source.episode_id)['initial_credit'])

    def wait_estimate(self, source, condition, context):
        support = context.get('waiting_support')
        if support is None:
            support = self.waiting_support(source, context)
        return estimate_wait(condition, context['pending_work'], support['progress_records'],
            support['duration_expectations'], support['own_completed_action_history'])

    def validate_wait_selection(self, source, condition):
        condition = validate_condition(_plain(condition))
        if not condition['events']:
            raise EventTargetError('wait_target_unavailable',
                affected_refs=[self.binding_context(source).episode_id],
                detail='selected_wait_requires_actual_outstanding_dependency')
        from .inprocess_waiting import selected_owned_children
        if selected_owned_children(self, source, condition) is not None:
            return condition
        if self.native_event_information is not None:
            condition = self.native_event_information.validate_wait(self.binding_context(source), condition)
        else:
            for event in condition['events']:
                if event['handle'].startswith('native_event_target_'):
                    raise EventTargetError('wait_target_unavailable', affected_refs=[event['handle']],
                        detail='native_event_target_unavailable')
        return self.execution_backend.validate_event_targets(condition)

    def waiting_support(self, source, context):
        captures = [context[key] for key in ('execution_expectations', 'native_execution_expectations')
                    if context.get(key) is not None]
        with self.store.read_snapshot():
            arguments = {}
            metadata = None
            if self.wait_inputs_version == 'wait_inputs_binding_v2':
                arguments['include_identities'] = True
                metadata = self.source_controller_credit(source)
                if metadata is not None:
                    arguments['local_return_history'] = self.local_return_history.capture(
                        source.episode_id, **metadata)
            support = self.wait_inputs.capture(source.episode_id, pending=context['pending_work'],
                known_progress_refs=self.progress_selection(source)['known_progress_refs'],
                current_duration_expectations=captures, **arguments)
            if self.wait_inputs_version == 'wait_inputs_binding_v2' and metadata is None:
                support['local_return_history_unavailable_reason'] = 'controller_credit_binding_unavailable'
            if self.native_event_information is not None:
                support['native_event_targets'] = _plain(context.get('native_event_targets', []))
            return support

    async def perform_selected_wait(self, source, condition, index):
        from .inprocess_waiting import selected_owned_children, await_owned_return
        if selected_owned_children(self, source, condition) is not None:
            condition = self.validate_wait_selection(source, condition)
            call = self.journal.row('runtime_model_calls', source.episode_id, index)
            context = json.loads(call['request'])['context']
            estimate = self.wait_estimate(source, condition, context)
            outcome = await await_owned_return(self, source, condition)
            # execute() retains this original wait action and its measured
            # interval. Its ordinary zero-gain wait projection stays unchanged;
            # the ready child's original invocation still owns typed receipt.
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                'result': outcome, 'wait_estimate': estimate,
                'pending_work_after_action': self.pending_work(source)}
        wait_id = 'wait_' + _digest({'run': self.run_id, 'episode': source.episode_id, 'decision': index})
        saved = self.wait_store.get(wait_id)
        if saved is not None:
            request = saved['request']
            if saved['outcome'] is None:
                self.validate_wait_selection(source, request['condition'])
        else:
            condition = self.validate_wait_selection(source, condition)
            call = self.journal.row('runtime_model_calls', source.episode_id, index)
            context = json.loads(call['request'])['context']
            request = {'version': 'wait_request_v1', 'wait_id': wait_id,
                'parent_episode_id': source.episode_id, 'original_decision_index': index,
                'condition': condition, 'estimate_snapshot': self.wait_estimate(source, condition, context)}
            with self.store.transaction():
                self.wait_store.select(request)
        from method_loop.suspension import external_wait
        outcome = await external_wait(self.wait_store.perform_wait(request, self.execution_backend),
            {'kind': 'selected_external_event', 'wait_id': wait_id,
                'condition': request['condition']})
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
            'result': outcome, 'wait_outcome': outcome, 'wait_estimate': request['estimate_snapshot'],
            'pending_work_after_action': self.pending_work(source)}

    def is_job_source(self, source):
        return self.job_episodes is not None and source.path[-1][0] in self.job_episodes.roles

    def child_credit_arguments(self, source):
        """Only the original commission, never another child's private history.

        Fresh JSON values keep a caller projector from mutating the assignment
        used by the runtime and communication guard. The scalar is projected
        from recorded contributions, not from newly generated reporting prose.
        """
        contract = source.request.report_contract
        message = source.request.message.as_record()
        selected = message.get('episode_assignment', {})
        if not isinstance(selected, Mapping):
            raise ValueError('original_child_episode_assignment_required')
        assignment = {"goal": source.request.goal.as_record(),
            "scope": source.scope, "purpose": contract.decision, "schema": contract.schema,
            "initial_report": message["initial_report"]}
        assignment.update(_plain(selected))
        return {"assignment": _plain(assignment),
            "episode_id": source.episode_id, "run_id": self.run_id}

    def working_state(self, source):
        if self.is_job_source(source):
            return self.job_episodes.working_state(source)
        if not self.is_scientific_source(source):
            return {'assignment': source.request.message.as_record().get('episode_assignment', {})}
        arguments = ({'record_selection': self.receipts.selection(source.episode_id)}
                     if self.uses_received_record_context(source) else {})
        return self.store.reasoning_view(source.scope, limit=24, **arguments)

    def resource_context(self, source):
        """Fresh host capacity for parents and children before each new choice.

        Saved decisions retain their original snapshot. Capacity is checked
        atomically again at native dispatch; a planning view grants no slot.
        """
        resources = getattr(self.tools, 'local_resources', None)
        if resources is None:
            return None
        capabilities = []
        if 'launch' in self.episode_bindings.roles:
            read = getattr(self.episode_bindings.for_role('launch'), 'capabilities', None)
            if callable(read):
                capabilities = list(read())
        from .workflow_budget import active_budget
        budget=active_budget()
        whole={key:budget[key] for key in ('version', 'window_id', 'run_directory', 'environment_bounds') if key in budget}
        whole.update(coverage='Python coordinator, provider, native workers, and all descendants',
            ownership='One workflow per Codex window; other windows have independent slots.')
        local_snapshot = resources.snapshot()
        from .execution_planning import planning_context
        import sqlite3
        try:
            shared_planning = planning_context(self, local_snapshot)
        except (OSError, sqlite3.Error) as error:
            shared_planning = {'state': 'unavailable', 'reason': type(error).__name__,
                'planning': 'Shared observations are unavailable. Do not infer remote availability.'}
        return {'version': 'episode_resource_context_v1', 'local': local_snapshot,
            'execution_planning': shared_planning,
            'whole_workflow':whole,
            'ordinary_tool_job_limits': self.tools.local_job_policy.to_dict(),
            **({'operation_limits': self.tools.operation_resource_limits()}
               if callable(getattr(self.tools, 'operation_resource_limits', None)) else {}),
            'execution_capabilities': capabilities,
            'planning': 'Account for Python, providers and native workers when estimating local capacity. '
                'One workflow may run locally in this Codex window; other windows have independent slots. '
                'Use observed capacity and the actual configured execution contract. '
                'A busy result preserves prepared work for a later retry. Only host admission reserves capacity.'}

    def shared_information_repository(self):
        if self.receipts is None or not hasattr(self.store, 'db'):
            return None
        if not hasattr(self, '_shared_information'):
            from .shared_information import SharedInformation
            self._shared_information = SharedInformation(self.store, self.run_id)
        return self._shared_information

    def shared_information_context(self, source):
        from .shared_information import PARTICIPANT_ROLES
        if source.path[-1][0] not in PARTICIPANT_ROLES:
            return None
        repository = self.shared_information_repository()
        if repository is None:
            return None
        view = repository.context_view(self.binding_context(source))
        if (view['upward_recipient'] is None
                and not any(view[name] for name in ('needs', 'information_available', 'dispositions'))):
            return None
        return view

    def shared_information_catalog(self, source):
        from .shared_information import PARTICIPANT_ROLES
        if source is None or source.path[-1][0] not in PARTICIPANT_ROLES:
            return []
        repository = self.shared_information_repository()
        return [] if repository is None else repository.catalog(self.binding_context(source))

    def retain_shared_grading_results(self, source, outcome, credit_view):
        """Retain existing saved grading after this original shared read's receipt.

        Normal receipt, attribution and credit projection have already run.
        This copies their authorized results; it neither grades again nor adds
        a credit event or a separate decision. Later versions cannot replace
        this original action's saved numerical payload.
        """
        body = outcome.get('result')
        if (outcome.get('status') not in {'completed', 'partial'} or not isinstance(body, Mapping)
                or body.get('kind') not in {'information', 'disposition'}
                or 'saved_grading_results' in body):
            return
        context = self.binding_context(source)
        selected = [ref for ref in body.get('evidence_refs', ()) if ref in context.received_record_refs]
        if not selected:
            return
        from .shared_information_results import saved_grading_results
        from .literature_sheet_updates import current_scoring_sheets
        grading_context = self.episode_bindings.initial_decision_context(context)
        delivered_cells = self.episode_bindings.received_report_facts(context)
        literature_sheets = current_scoring_sheets(self.store, context)
        details = credit_view
        # Native __call__ projections may intentionally omit their detail rows.
        # Use the existing saved-grading reader so a presentation page cannot
        # turn a selected graded record into an apparently ungraded one.
        total = credit_view.get('detail_pages', {}).get('source_contributions_total')
        projector = self.scientific_projector_for_context(context)
        reader = getattr(projector, 'read_details', None)
        arguments = self.projector_receipt_arguments(projector, context.episode_id)
        if (callable(reader) and 'known_record_refs' in arguments and type(total) is int
                and total > len(credit_view.get('source_contributions', []))):
            details = reader(self.store, _plain(context.scope), **arguments,
                details_limit=total, details_offset=0)
        saved = saved_grading_results(selected, details, grading_context, delivered_cells,
            {'literature_current_scoring_sheets': literature_sheets})
        body['saved_grading_results'] = saved
        body['grading_delivery'] = ('Exact saved results from the received grading or scoring sheets.'
            if saved else 'No saved grading was delivered for these selected records; this message supplies material only.')

    def uses_received_record_context(self, source):
        """Scientific visibility follows custody, not the chosen credit scalar."""
        return self.receipts is not None and self.is_scientific_source(source)

    def receipt_projection(self, source):
        if not self.is_scientific_source(source):
            return False
        projector = self.scientific_projector_for_context(self.binding_context(source))
        return bool(getattr(projector, 'requires_episode_receipts', False))

    def scientific_projector_for_context(self, context):
        if len(context.path) == 1:
            return self.project_credit
        binding = (self.episode_bindings.for_role(context.role)
            if context.role in self.episode_bindings.roles else None)
        select = getattr(binding, 'credit_projector', None)
        declared = select(context) if select is not None else None
        if declared is None:
            raise ValueError('scientific_task_credit_not_declared:' + context.role)
        return declared

    def projector_receipt_arguments(self, projector, episode_id):
        if not getattr(projector, 'requires_episode_receipts', False):
            return {}
        if self.receipts is None:
            raise ValueError('numerical_credit_requires_episode_receipts')
        arguments = ({'known_record_refs': self.receipts.known(episode_id)}
            if getattr(projector, 'requires_known_record_refs', False) else
            {'known_assessment_refs': self.receipts.known(episode_id, record_type='assessment')})
        if getattr(projector, 'requires_receiver_context', False):
            arguments.update(run_id=self.run_id, episode_id=episode_id)
        return arguments

    def projection_arguments(self, source):
        arguments = self.child_credit_arguments(source) if len(source.path) > 1 else {}
        projector = self.scientific_projector_for_context(self.binding_context(source))
        arguments.update(self.projector_receipt_arguments(projector, source.episode_id))
        return arguments

    def receive_outcome(self, source, selection, result, index):
        if self.progress_provider is not None and self.progress_receipt_order == 'received_progress_order_v1':
            self.progress_provider.receive_outcome(source.episode_id, result, source.scope,
                f'{self.run_id}:{source.episode_id}:{index}:own_progress')
        if self.receipts is not None and not self.is_job_source(source):
            references = list(result.get('record_refs', []))
            if selection.get('kind') == 'tool' and selection.get('tool') == 'state.query':
                # This read returns existing records, not newly published refs.
                # Detail/provenance tools do not thereby deliver the scientific
                # content of every witness mentioned in their diagnostics.
                references.extend(row['id'] for row in (result.get('result') or {}).get('records', []))
            self.receipts.receive(source.episode_id, references,
                                  kind='own_action', source_index=index)
            projection_read = selection.get('kind') == 'tool' and selection.get('tool') in {
                'episode.credit', 'episode.annotation_score', 'episode.monitoring_information'}
            derived = [] if projection_read else self.receive_tool_attributions(source, index, kind='own_action')
            if derived:
                result['record_refs'] = list(dict.fromkeys([*result.get('record_refs', []), *derived]))
                references.extend(ref for ref in derived if ref not in references)

    async def automatic_score_updates(self, source, index, result):
        """Run owner-declared score judgments once, outside a write transaction."""
        binding = self.specialist(source)
        prepare = getattr(binding, 'automatic_score_judgments', None)
        if prepare is None:
            return result
        complete = getattr(binding, 'complete_score_judgment', None)
        if complete is None:
            raise ValueError('automatic_score_judgment_completion_owner_required')
        if self.store.db.in_transaction:
            raise ValueError('automatic_score_judgment_requires_committed_inputs')
        context = self.binding_context(source)
        judgments = prepare(context)
        if not judgments:
            return result
        updated = _plain(result)
        for judgment in judgments:
            if 'completed_outcome' in judgment:
                outcome = judgment['completed_outcome']
                original = judgment.get('completed_provenance', {})
                if (original.get('episode_id') == source.episode_id
                        and original.get('decision_index') != index
                        and set(outcome.get('record_refs', [])) <= set(context.received_record_refs)):
                    # Replay must recover the original action's exact result;
                    # a later action must not publish that old change again.
                    continue
            else:
                judgment_ref = judgment['judgment_ref']
                if self.store.db.in_transaction:
                    raise ValueError('automatic_score_judgment_requires_committed_inputs')
                provenance = {'version': 'automatic_score_judgment_call_v1',
                    'episode_id': source.episode_id, 'decision_index': index,
                    'session_key': judgment_ref, 'phase': 'REASONING',
                    'provider': type(self.provider).__module__ + '.' + type(self.provider).__qualname__}
                model = getattr(self.provider, 'roles', {}).get('REASONING')
                if isinstance(getattr(model, 'model', None), str):
                    provenance['model'] = model.model
                if isinstance(getattr(model, 'reasoning_effort', None), str):
                    provenance['reasoning_effort'] = model.reasoning_effort
                try:
                    response = await self.provider.complete(judgment_ref, 'REASONING',
                        judgment['instructions'], judgment['context'], judgment['output_schema'])
                except Exception as error:
                    outcome = complete(context, judgment_ref, provenance=provenance,
                        failure={'code': 'automatic_score_judgment_call_failed',
                            'exception_type': type(error).__name__})
                else:
                    outcome = complete(context, judgment_ref, response, provenance=provenance)
            for field in ('record_refs', 'changed_record_refs'):
                updated[field] = list(dict.fromkeys([*updated.get(field, []), *outcome.get(field, [])]))
            if self.receipts is not None:
                self.receipts.receive(source.episode_id, outcome.get('record_refs', []),
                    kind='own_action', source_index=index)
        return updated

    def receive_tool_attributions(self, source, index, *, kind):
        """Derive tool-specific numeric/trait evidence from actual receipts.

        This runs before projection, including after a late sibling delivery.
        It neither widens the child's typed form nor reads unreceived evidence.
        The receiver's host derivations are recorded in its action outcome.
        """
        callback = getattr(self.tools, 'received_attributions', None)
        if callback is None or self.receipts is None or source.path[-1][0] not in {'annotation','scientific_process','improvement'}:
            return []
        context = self.binding_context(source)
        known = set(self.receipts.known(source.episode_id))
        structural = getattr(self.tools, 'received_structural_attributions', None)
        generated, needs = (structural(context, known,
            input_authority=self.services.protein_structure_input_authority(),
            hpc_result_reader=self.services.read_received_hpc_result)
            if callable(structural) else ([], []))
        hpc = getattr(self.tools, 'received_hpc_attributions', None)
        if callable(hpc):
            received, pending = hpc(context, known | set(generated),
                hpc_result_reader=self.services.read_received_hpc_result)
            generated.extend(received)
            needs.extend(pending)
        attributed, attribution_needs = callback(context, known | set(generated))
        generated.extend(attributed)
        needs.extend(attribution_needs)
        generated = [ref for ref in generated if ref not in known]
        repository = self.shared_information_repository()
        if (context.role == 'scientific_process' and repository is not None
                and repository.parent(context, require_active=True) is not None):
            for request_ref, need in needs:
                args = {'target_ref':need['target_ref'],
                    'question':'Supply the specific attribution inputs for this measurement or local trait.',
                    'required_information':canonical({'measurement_or_request_ref':request_ref,
                        'policy':need['policy'],'physical_feature_key':need.get('physical_feature_key'),
                        'missing':need['missing'],
                        **({'required_operands':need['required_operands']}
                            if need.get('required_operands') else {})}),
                    'reason':'Only this measurement/use is unresolved; native evidence and other traits retain their own scores.',
                    'blocking':False,'available_record_refs':[request_ref]}
                published = repository.execute(context,'shared.request_information',args,
                    known_record_refs=known,operation_key=f'{self.run_id}:{source.episode_id}:tool_attribution_need:{_digest(args)}')
                generated.extend(ref for ref in published['record_refs'] if ref not in known)
        generated = list(dict.fromkeys(generated))
        if generated:self.receipts.receive(source.episode_id,generated,kind=kind,source_index=index)
        return generated

    def receive_native_outcome(self, source, result, index):
        if self.native_timing_information is not None:
            # A failed scientific operation can still return a real measured
            # execution. Receiving that receipt does not complete the action.
            references = list(result.get('native_execution_refs', []))
            references.extend(row['id'] for row in (result.get('result') or {}).get('records', [])
                if row.get('record_type') == 'native_execution' and 'measurement' in row)
            self.receipts.receive(source.episode_id, references, kind='own_action', source_index=index)

    def native_timing_arguments(self, source):
        return {'known_execution_refs': self.receipts.known(source.episode_id, record_type='native_execution'),
                'initial_execution_refs': self.receipts.known(source.episode_id,
                    record_type='native_execution', baseline=True)}

    def native_estimation_context(self, source, context):
        binding = getattr(self.tools, 'native_statistics', None)
        available = {item['name'] for item in context.get('tools', [])}
        if binding is None:
            return None
        scopes = {}
        if self.receipts is not None:
            for reference in self.receipts.known(source.episode_id, record_type='native_execution'):
                scope = read_measurement(self.store, reference).execution_class
                scopes[scope.ref] = scope
        previous = context.get('last_local_outcome') or {}
        for value in (previous.get('native_execution_expectations') or {}).get('execution_classes', []):
            scope = ExecutionClass(**value)
            scopes[scope.ref] = scope
        # An explicit primary expectation binding already supplies its classes.
        # Do not repeat that same forecast through the ordinary-tool route.
        supplied = {ExecutionClass(**value).ref for value in
                    (context.get('execution_expectations') or {}).get('execution_classes', [])}
        scopes = [scope for ref, scope in scopes.items() if ref not in supplied
                  and binding.available_phase(scope.phase, available) and scope.resource_id == binding.resource_id]
        if not scopes:
            return None
        recovery = binding.recover_pending_statistics()
        return {**capture_execution_scopes(binding.history_path, scopes), 'statistics_recovery': recovery}

    def receive_form(self, source, admitted, schema, index, *, redelivery=False):
        with self.store.transaction():
            return self._receive_form(source, admitted, schema, index, redelivery=redelivery)

    def _receive_form(self, source, admitted, schema, index, *, redelivery=False):
        if self.receipts is not None and not redelivery and not self.is_job_source(source):
            from .episode_return_records import EpisodeReturnRecords
            references = EpisodeReturnRecords(self.store, self.run_id,
                failure_prefix='recorded_admission_').recorded_admission_references(
                    self.binding_context(source), admitted, schema, index)
            if references is not None:
                return references
        # A typed progress delivery remains real received information even when
        # the caller has no scientific receipt projection. C4 supplies the
        # surrounding admission transaction; legacy callers use this boundary.
        if self.progress_provider is not None:
            self.progress_provider.receive_form(source.episode_id, admitted, schema, source.scope,
                f'{self.run_id}:{source.episode_id}:{index}:typed_form')
        if self.receipts is None or self.is_job_source(source):
            return []
        references = _references_in({}, self.store.get, forms=[(admitted, schema)],
            reference_subset=lambda refs: self.store.reference_subset(refs, source.scope))
        references.extend(self.episode_bindings.received_form_references(
            self.binding_context(source), admitted, schema,
            f'{self.run_id}:{source.episode_id}:{index}:typed_form'))
        references = list(dict.fromkeys(references))
        if self.native_timing_information is not None and self.job_episodes is not None:
            # A requested job status can deliver a real completed duration
            # without naming a Store receipt. Normalize that exact admitted
            # fact through its original host measurement. Persist this attempt's
            # projection so reconstruction cannot silently retry/reprice it.
            with self.store.transaction():
                key = (self.run_id, source.episode_id, index)
                row = self.store.db.execute('SELECT timing_receipts FROM runtime_report_attempts '
                    'WHERE run_id=? AND parent_episode_id=? AND decision_index=?', key).fetchone()
                if row is None:
                    raise WorkflowError('received_form_requires_recorded_attempt')
                if row[0] is None:
                    received = self.job_episodes.received_timing_records(self.store, admitted, schema, source.scope)
                    self.store.db.execute('UPDATE runtime_report_attempts SET timing_receipts=? '
                        'WHERE run_id=? AND parent_episode_id=? AND decision_index=?', (_json(received), *key))
                else:
                    received = json.loads(row[0])
            references.extend(ref for ref in received['native_execution_refs'] if ref not in references)
        self.receipts.receive(source.episode_id, references,
            kind='report_redelivery' if redelivery else 'child_form', source_index=index)
        references.extend(ref for ref in self.receive_tool_attributions(source,index,
            kind='report_redelivery' if redelivery else 'child_form') if ref not in references)
        return references

    def source_credit_view(self, source, *, binding_snapshot=None):
        if binding_snapshot is not None and type(binding_snapshot) is not dict:
            raise TypeError('credit_binding_snapshot_must_be_dict')
        if self.is_job_source(source):
            result = self.job_episodes.credit_view(source)
        elif self.specialist(source) is not None:
            selection = {**self.record_selection(source.episode_id),
                **self.progress_selection(source)}
            result = self.specialist(source).credit_view(self.binding_context(source), selection)
            if binding_snapshot is not None:
                # Retain this exact projection before Runtime adds separately
                # bound native timing information. Capture is not another call.
                binding_snapshot.update(view=json.loads(canonical(_plain(result))),
                    selection=json.loads(canonical(_plain(selection))))
        else:
            projector = self.scientific_projector_for_context(self.binding_context(source))
            result = self.projection_view(projector, source.scope,
                **self.projection_arguments(source))
        if self.native_timing_information is not None:
            native = self.native_timing_information(self.store, source.scope, **self.native_timing_arguments(source))
            previous = result.get('monitoring_information_credit')
            previous_binding = result.get('monitoring_information_binding')
            if previous is None and self.is_job_source(source) and source.path[-1][0] == 'job_monitor':
                # A caller's sample-only binding already names this scalar as
                # monitoring information even when it has no supplemental view.
                previous = result['credit']
                previous_binding = self.job_episodes.binding_for('job_monitor')
            binding = native['monitoring_information_binding']
            if previous is not None:
                binding = {'kind': 'execution_information_components',
                    'selected_observations': previous_binding,
                    'received_native_durations': binding}
            result.update(monitoring_information_credit=(previous or 0)+native['monitoring_information_credit'],
                          monitoring_information_binding=binding)
            # Monitoring still optimizes monitoring information. Scientific and
            # launch/results controller scalars remain independently bound.
            if self.is_job_source(source) and source.path[-1][0] == 'job_monitor':
                result['credit'] += native['monitoring_information_credit']
        return result

    def record_selection(self, episode_id):
        return {'run_id': self.run_id, 'episode_id': episode_id,
            'known_record_refs': ([] if self.receipts is None else
                                  list(self.receipts.known(episode_id))),
            'initial_known_record_refs': ([] if self.receipts is None else
                                         list(self.receipts.known(episode_id, baseline=True)))}

    def progress_selection(self, source):
        message = (source.request['message'] if isinstance(source.request, Mapping)
                   else source.request.message.as_record())
        initial = list(message.get('episode_assignment', {}).get('known_progress_refs', []))
        references = [*initial, *self.services.received_progress_refs(source.episode_id)]
        if self.progress_receipt_order == 'received_progress_order_v1':
            return {'known_progress_refs': list(dict.fromkeys(references)),
                    'initial_progress_refs': list(initial)}
        rows = self.store.db.execute("SELECT refs.value FROM runtime_actions actions "
            "JOIN json_each(actions.result,'$.progress_refs') refs "
            "WHERE actions.run_id=? AND actions.episode_id=? "
            "AND (json_extract(actions.result,'$.status') IN ('completed','partial') "
            "OR (json_extract(actions.action,'$.kind') IN ('tool','reason') "
            "AND json_extract(actions.result,'$.status') IN ('failed','unavailable'))) "
            "ORDER BY actions.decision_index, refs.key", (self.run_id, source.episode_id))
        references.extend(row[0] for row in rows)
        return {'known_progress_refs': list(dict.fromkeys(references)),
                'initial_progress_refs': list(initial)}

    def source_credit_binding(self, source):
        specialist = self.specialist(source)
        if specialist is not None and specialist.credit_kind(source.path[-1][0]) != 'scientific':
            return _plain(self.role_credit_definitions.get(source.path[-1][0]))
        if self.is_job_source(source):
            binding = self.job_episodes.binding_for(source.path[-1][0])
            if source.path[-1][0] == 'job_monitor' and self.native_timing_information is not None:
                return {'kind': 'monitoring_information_components', 'selected_observations': binding,
                        'received_native_durations': self.native_timing_information.as_record()}
            return binding
        if specialist is not None:
            context = source if isinstance(source, BindingContext) else self.binding_context(source)
            return _plain(self.scientific_projector_for_context(context).as_record())
        if len(source.path) == 1:
            return self.credit_binding
        raise ValueError('scientific_task_credit_not_declared:' + source.path[-1][0])

    def source_controller_credit(self, source):
        """Declare the actual local scalar's meaning without projecting it."""
        role = source.path[-1][0]
        specialist = self.specialist(source)
        if specialist is not None:
            kind = specialist.credit_kind(role)
        elif self.is_job_source(source):
            kind = self.job_episodes.credit_kind(role)
        else:
            kind = 'scientific'
        binding = self.source_credit_binding(source)
        if not isinstance(binding, Mapping) or not binding:
            return None
        context = source if isinstance(source, BindingContext) else self.binding_context(source)
        annotation = self.services.proposed_annotation_for(context)
        if annotation is not None:
            binding = {**_plain(binding), 'proposed_annotation_ref': annotation}
        return {'credit_kind': kind, 'credit_binding': _plain(binding)}

    def extra_report_sources(self, source):
        return self.report_sources(source.path[-1][0])

    def return_contract_sources(self, grain):
        """Include common evidence-reference contracts in child discovery."""
        return common_fact_sources() | self.report_sources(grain)

    def report_sources(self, grain):
        sources = runtime_report_sources() | (self.job_episodes.fact_sources(grain) if self.job_episodes else {})
        if self.native_event_information is not None:
            from .native_event_information import report_sources
            sources.update(report_sources())
        sources['pending_handles'] = {'type': 'array', 'meaning':
            ('Original selected child executions awaiting their outcome and parent receipt. Numerical yield suspends new selection while these owned returns remain; normal branch closure follows their settlement and does not establish scientific completion.'
                if self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE else
                'Original selected child executions still pending when this episode closed. These handles survive parent closure; closure does not cancel them or establish scientific completion.'),
            'report_schema': {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference',
                    'x-reference-namespace': 'execution_handle'}, 'x-source': 'pending_handles'}}
        if grain in self.episode_bindings.roles:
            sources.update(self.episode_bindings.for_role(grain).fact_sources(grain))
        received_sources = self.episode_bindings.received_report_sources(grain)
        if set(received_sources).intersection(sources):
            raise ValueError('received_report_source_conflict')
        sources.update(received_sources)
        if self.native_timing_information is not None:
            native_sources = self.native_timing_information.report_sources()
            # Existing job-specific form fields retain their own meanings.
            sources = native_sources | sources
        if (self.project_annotation_score is not None
                and not (self.job_episodes and grain in self.job_episodes.roles)):
            if getattr(self.project_annotation_score, 'provides_single_annotation_score', True):
                sources['annotation_score'] = {'type': 'number', 'meaning':
                    'Annotation support for the fixed scope at child closure, separately bound from investigation progress and numerical yield. Redelivery preserves this snapshot.'}
            else:
                sources['proposed_annotations'] = {'type': 'array', 'meaning':
                    'Received proposed annotations and their separate evidence scores at child closure; unknown scores remain null.'}
                sources['annotation_comparisons'] = {'type': 'array', 'meaning':
                    'Best scored alternatives and ties for the same subject, region and question at child closure; the episode owns the annotation decision.'}
        if self.resource_estimator is not None:
            sources['resource_tool_estimates'] = resource_report_source()
        return sources

    def validate_report(self, value, scope, *, assignment=None, grain=None, schema=None, source=None,
                        context=None):
        """Validate recorded forecast relationships for any episode's form."""
        if (self.native_event_information is not None and schema is not None
                and any(node.get('x-source') == 'native_event_targets'
                        for node in schema.get('properties', {}).values())):
            native_context = self.binding_context(source) if source is not None else context
            if native_context is None:
                raise ValueError('native_event_report_context_required')
            self.native_event_information.validate_report(native_context, value, schema)
        if assignment is not None:
            self.job_episodes.validate_report(value, assignment, store=self.store, schema=schema)
        elif self.resource_estimator is not None:
            validate_recorded_estimates(self.store, value, schema=schema,
                reference_resolver=self.resolver(scope, source=source, grain=grain, context=context))
        if self.native_timing_information is not None and schema is not None:
            validate_native_measurements(self.store, value, schema=schema)
        received_context = self.binding_context(source) if source is not None else context
        if received_context is not None and schema is not None:
            self.episode_bindings.validate_received_report(received_context, value, schema)
        if source is not None and self.specialist(source) is not None:
            self.specialist(source).validate_report(self.binding_context(source), value, schema)
        elif context is not None and context.role in self.episode_bindings.roles:
            self.episode_bindings.for_role(context.role).validate_report(context, value, schema)

    def credit_view(self, scope):
        """Return the scalar and available components from ONE actual projection.

        Components inform the scientific episode; the numerical controller still
        receives the same scalar. No history/source payload or extra observation
        is materialized, and custom projectors acquire no invented default axes.
        """
        return self.projection_view(self.project_credit, scope)

    def projection_view(self, projector, scope, *, annotation_collection=False, **arguments):
        with self.store.read_snapshot():
            projected = projector(self.store, _plain(scope), **arguments)
        if (isinstance(projected, Mapping) and isinstance(projected.get('credit'), Mapping)
                and projected['credit'].get('mode') == 'annotation_axis_credit'):
            from .numerical import validate_task_credit
            return {**_plain(projected), 'credit': validate_task_credit(projected['credit'])}
        if (annotation_collection and isinstance(projected, Mapping)
                and projected.get('mode') == 'proposed_annotation_collection'
                and 'credit' not in projected):
            return {key: _plain(projected[key]) for key in ('mode', 'proposed_annotations',
                'comparisons', 'scalar_mapping_version', 'aggregation_version')}
        if hasattr(projected, "credit"):
            value, axes = float(projected.credit), getattr(projected, "axis_components", None)
        elif isinstance(projected, Mapping):
            value, axes = float(projected["credit"]), projected.get("axis_components")
        else:
            value, axes = float(projected), None
        if not math.isfinite(value):
            raise ValueError("finite_scientific_credit_required")
        result = {"credit": value}
        if isinstance(axes, Mapping):
            result["axis_components"] = _plain(axes)
        if isinstance(projected, Mapping):
            for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages', 'a101_sheet',
                        'interpretation', 'axis_status', 'scalar_mapping_version',
                        'support', 'opposition', 'aggregation_version'):
                if key in projected:
                    result[key] = _plain(projected[key])
        return result

    def credit(self, scope):
        return self.credit_view(scope)["credit"]

    def annotation_context(self, scope, *, source=None):
        """Separately bound annotation support; never a controller observation."""
        if self.project_annotation_score is None:
            return {}
        arguments = {}
        if getattr(self.project_annotation_score, 'requires_episode_receipts', False):
            if source is None:
                raise ValueError('annotation_support_actual_receiver_required')
            arguments = self.projector_receipt_arguments(self.project_annotation_score, source.episode_id)
        view = self.projection_view(self.project_annotation_score, scope, annotation_collection=True, **arguments)
        if view.get('mode') == 'proposed_annotation_collection':
            return {'proposed_annotations': view['proposed_annotations'],
                'annotation_comparisons': view['comparisons'],
                'annotation_score_binding': self.annotation_score_binding}
        return {'annotation_score': view['credit'],
            'annotation_evidence_vector': view.get('axis_components'),
            **({'annotation_evidence_status': view['axis_status']} if 'axis_status' in view else {}),
            **({'annotation_support': view['support']} if 'support' in view else {}),
            **({'annotation_opposition': view['opposition']} if 'opposition' in view else {}),
            'annotation_score_binding': self.annotation_score_binding}

    def local_outcome_preview(self, outcome, *, decision_index=None):
        """Present host-declared generated batches at this one boundary.

        The saved outcome, fact arrays, exact reads and admitted child forms
        remain complete. Fixed publication/failure fields are presentation,
        never work bounds or recursively inferred payload instructions.
        """
        if not isinstance(outcome, Mapping):
            return outcome
        from .shared_information_results import outcome_view as shared_outcome_view
        outcome = shared_outcome_view(outcome)
        from .hpc_prompt import plan_outcome_view
        outcome = plan_outcome_view(outcome)
        from .ensembl_acquisition import ensembl_outcome_view
        ensembl_view = ensembl_outcome_view(outcome)
        if ensembl_view is not None:
            return ensembl_view
        batch = outcome.get("published_batch")
        if not isinstance(batch, Mapping) or batch.get("representation") != "native_publications_v1":
            return outcome
        size = self.restoration_settings["preview_size"]
        def counts(total, included):
            return {"total": total, "included": included,
                    "truncated": included < total if total is not None else None}
        refs = outcome.get("record_refs", [])
        shown = {**outcome, "record_refs": refs[:size]}
        preview = {"kind": "native_publication_batch", "preview_size": size,
            "record_refs": counts(len(refs), len(shown["record_refs"])),
            "complete_result_preserved": True}
        body = outcome.get("result")
        if isinstance(body, Mapping):
            body = dict(body)
            if isinstance(body.get("records"), list):
                body["records"] = body["records"][:size]
            preview["rows"] = counts(batch["published_rows_total"], len(body.get("records", [])))
            if isinstance(body.get("retained_record_refs"), list):
                retained = body["retained_record_refs"]
                body["retained_record_refs"] = retained[:size]
                preview["retained_record_refs"] = counts(len(retained), len(body["retained_record_refs"]))
            body["record_refs_are_preview"] = len(shown["record_refs"]) < len(refs)
            if batch["failure_rows_total"] is not None:
                # Error diagnostics are returned whole, even when successful
                # publication rows use the ordinary presentation preview.
                included = max((len(body[field]) for field in ("errors", "projection_errors")
                    if isinstance(body.get(field), list)), default=0)
                preview["failures"] = counts(batch["failure_rows_total"], included)
            shown["result"] = body
        feedback = outcome.get("feedback")
        if (batch["failure_rows_total"] is not None and isinstance(feedback, Mapping)
                and isinstance(feedback.get("rows"), list)):
            shown["feedback"] = feedback
            preview["failures"] = counts(batch["failure_rows_total"], len(shown["feedback"]["rows"]))
        if batch.get("observation_query") is not None:
            preview["observation_query"] = {**batch["observation_query"], "limit": max(1, size)}
        if decision_index is not None:
            preview["publication_query"] = {"view": "publications", "decision_index": decision_index,
                                            "offset": 0, "limit": max(1, size)}
        shown["automatic_preview"] = preview
        return shown

    def controller(self, path):
        identity = Episode.identity(self.context, self.grains[path[-1][0]], path[-1][1], parent_path=path[:-1])
        row = self.journal.row("runtime_episodes", identity.episode_id)
        role = path[-1][0]
        binding = self.episode_bindings.for_role(role) if role in self.episode_bindings.roles else None
        bound = None
        owner_controller = (getattr(binding, 'yield_controller', None)
            if getattr(binding, 'private_yield_binding', False) else None)
        if owner_controller is not None:
            request = json.loads(row['request'])
            bound = BindingContext(self.run_id, identity.episode_id, role, path,
                request['message']['scope'], request['message'].get('episode_assignment', {}), request,
                tuple(self.receipts.known(identity.episode_id)) if self.receipts is not None else ())
            epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
            controller = owner_controller(bound, row['initial_credit'], epoch)
        elif getattr(self.controller_factory, 'requires_original_task', False):
            request = json.loads(row['request'])
            bound = BindingContext(self.run_id, identity.episode_id, role, path,
                request['message']['scope'], request['message'].get('episode_assignment', {}), request,
                tuple(self.receipts.known(identity.episode_id)) if self.receipts is not None else ())
            task_key = credit_definition = None
            scientific_child = len(path) > 1 and (role == 'improvement'
                or binding is not None and binding.credit_kind(role) == 'scientific')
            if scientific_child:
                choose_task = getattr(binding, 'continuation_task', None)
                if choose_task is None:
                    raise ValueError('scientific_continuation_task_not_declared:' + role)
                task_key = choose_task(bound)
                if not isinstance(task_key, str) or not task_key:
                    raise ValueError('scientific_continuation_task_not_declared:' + role)
                credit_definition = _plain(self.scientific_projector_for_context(bound).as_record())
            controller = self.controller_factory(path, row['initial_credit'], context=bound,
                task_key=task_key, credit_definition=credit_definition)
        else:
            # A saved historical factory keeps its original executable contract.
            # Fresh task-aware factories declare the inputs above explicitly.
            controller = self.controller_factory(path, row['initial_credit'])
        if binding is not None and owner_controller is None:
            estimator = getattr(binding, 'practical_estimator', None)
            if estimator is not None:
                if bound is None:
                    request = json.loads(row['request'])
                    bound = BindingContext(self.run_id, identity.episode_id, role, path,
                        request['message']['scope'], request['message']['episode_assignment'], request)
                callback = estimator(bound)
                if callback is not None:
                    from .numerical import YieldController
                    if type(controller) is not YieldController:
                        raise ValueError('practical_binding_requires_explicit_yield_controller')
                    bind_cost = getattr(callback, 'with_continuation_cost', None)
                    if bind_cost is not None:
                        callback = bind_cost(controller.cost)
                    controller = YieldController(controller.epoch, row['initial_credit'],
                        controller.cost, controller.settings, estimate_with_context=callback)
        native = self.has_native_estimation()
        episode_id = identity.episode_id
        capture = (None if self.completed_action_inputs_version is None else
            lambda unit_ref, index, value: self.capture_completion_evidence(episode_id,
                original_decision_index=index, unit_ref=unit_ref, controller_input=value))
        return ExecutionContextController(controller, self.journal, episode_id,
            include_native=native, capture_current_completion=capture)

    def capture_completion_evidence(self, episode_id, *, original_decision_index,
                                    unit_ref, controller_input):
        from .completion_evidence import CompletionEvidence
        return CompletionEvidence(self.store, self.journal, self.execution_backend,
            self.progress_provider).capture(episode_id,
                original_decision_index=original_decision_index, unit_ref=unit_ref,
                controller_input=controller_input)

    def has_native_estimation(self):
        return getattr(self.tools, 'native_statistics', None) is not None and self.resource_estimator is not None

    def controller_value(self, source, index, credit):
        observed = self.store.db.execute('SELECT observation FROM runtime_observations '
            'WHERE run_id=? AND episode_id=? AND json_extract(observation,\'$.decision_index\')=?',
            (self.run_id, source.episode_id, index)).fetchone()
        if observed is not None:
            # SQLite REAL is not the original JSON representation (3 becomes
            # 3.0). Replay the one recorded completed-action input, including
            # its original completion fields, instead of changing closed
            # archive identities or rebuilding historical forecast inputs.
            original = json.loads(observed['observation'])['credit']
            if (not isinstance(original, dict) or 'credit' not in original
                    or original.get('estimation_action_index', index) != index):
                raise WorkflowError('recorded controller input does not match its action')
            return Record(original)
        # Real-time fitting is part of the default iterator, independent of
        # optional native estimates, waits or specialized receipt bindings.
        # Every newly observed action supplies its existing original identity;
        # the wrapper freezes its clock at observation, after work has returned.
        value = {"credit": credit, "estimation_action_index": index}
        if isinstance(credit, Mapping) and credit.get('mode') == 'annotation_axis_credit':
            value.update(self.episode_bindings.annotation_axis_yield_context(
                self.binding_context(source), credit))
            action = self.journal.row('runtime_actions', source.episode_id, index)
            selected = json.loads(action['action'])
            if selected.get('kind') == 'episode_child' and selected.get('role') == 'scientific_process':
                assignment = selected['assignment']
                from .scientific_process_records import selection_fields
                process = assignment['selection']
                axis = process[selection_fields(process)[0]]['option_id']
                ref = assignment.get('proposed_annotation_ref')
                arms = [arm for arm in credit['arms']
                    if arm['proposed_annotation_ref'] == ref and arm['axis'] == axis
                    and arm['scope'] == selected['scope']]
                if len(arms) != 1:
                    raise WorkflowError('completed_axis_requires_one_original_annotation_subject_scope')
                value['completed_annotation_axis'] = {name: arms[0][name] for name in
                    ('proposed_annotation_ref', 'subject_ref', 'scope', 'axis')}
        binding = self.specialist(source)
        continuation = getattr(binding, 'continuation_for_action', None)
        if continuation is not None:
            pending_value = continuation(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
            if pending_value is not None:
                value['hpc_continuation'] = pending_value
                value['estimation_action_index'] = index
        completion = getattr(binding, 'completion_for_action', None)
        if completion is not None:
            proof = completion(self.binding_context(source), f'{self.run_id}:{source.episode_id}:{index}')
            if proof is not None:
                value['practical_completion'] = proof
                value['estimation_action_index'] = index
        return Record(value)

    def resolver(self, scope, source=None, assignment=None, grain=None, *, context=None):
        if context is not None and type(context) is not BindingContext:
            raise TypeError('typed_report_binding_context_required')
        if source is not None:
            actual = self.binding_context(source)
            if context is not None and context.as_record() != actual.as_record():
                raise ValueError('report_binding_context_source_mismatch')
            context = actual
        specialist = None
        if context is not None:
            message = context.request.get('message', {})
            if (context.run_id != self.run_id or context.role not in self.grains
                    or _plain(context.scope) != _plain(scope)
                    or _plain(message.get('scope')) != _plain(scope)
                    or _plain(context.assignment) != _plain(message.get('episode_assignment', {}))
                    or grain is not None and grain != context.role
                    or assignment is not None and _plain(assignment) != _plain(message.get('job_assignment'))):
                raise ValueError('report_binding_context_identity_mismatch')
            identity = Episode.identity(self.context, self.grains[context.role], context.path[-1][1],
                parent_path=context.path[:-1])
            if identity.episode_id != context.episode_id:
                raise ValueError('report_binding_context_identity_mismatch')
            recorded = self.journal.row('runtime_episodes', context.episode_id)
            if recorded is not None and (json.loads(recorded['path']) != _plain(context.path)
                    or json.loads(recorded['request']) != _plain(context.request)):
                raise ValueError('report_binding_context_original_request_mismatch')
            assignment, grain = message.get('job_assignment'), context.role
            if grain in self.episode_bindings.roles:
                specialist = self.episode_bindings.for_role(grain)
        def resolve(reference, namespace=None):
            molecular = getattr(self.tools, 'retained_molecular_reference_access', None)
            if callable(molecular):
                verdict = molecular(context, reference, namespace,
                    initial_record_refs=getattr(self, 'initial_known_record_refs', None) or ())
                if verdict is not None:
                    return verdict
            if context is not None:
                protein = self.services.protein_structure_reference_access(context, reference, namespace)
                if protein is not None:
                    return protein
            if namespace == 'native_event_target':
                return bool(self.native_event_information is not None and context is not None
                    and self.native_event_information.resolve(context, reference, namespace))
            if (self.native_event_information is not None and context is not None
                    and self.native_event_information.resolve(context, reference, namespace)):
                return True
            if (self.scientific_provenance is not None and context is not None
                    and namespace in {'scientific_invocation', 'scientific_preparation',
                        'scientific_process_library', 'scientific_option_digest',
                        'scientific_credit_binding'}):
                return self.services.scientific_reference(context, reference, namespace)
            if context is not None:
                received = self.episode_bindings.resolve_received_reference(context, reference, namespace)
                if received is not None:
                    return received
            if specialist is not None and specialist.resolve(context, reference, namespace):
                return True
            if specialist is None and namespace in {'execution_handle', 'execution'}:
                return bool(self.progress_provider is not None and
                    self.progress_provider.resolve(reference, scope, namespace))
            # Use the same ownership/scope projection as the full registry,
            # limited to this actual form value. Resolving one reference must
            # not hydrate every scientific record or artifact owner.
            if not self.store.reference_subset([reference], scope):
                # A specialist can require that a runtime observation was
                # actually received. Do not bypass that guard with the broader
                # provider's scope-only lookup.
                if specialist is None and self.progress_provider is not None and self.progress_provider.resolve(
                        reference, scope, namespace):
                    return True
                if namespace in FORECAST_REFERENCE_FIELDS and assignment is None:
                    estimate = recorded_estimate(self.store, reference, namespace=namespace)
                    if estimate is None:
                        return False
                    native = getattr(self.tools, 'native_statistics', None)
                    if native is not None and native.recorded_class(self.store, estimate['execution_class_ref']) is not None:
                        return True
                    # Static caller-bound classes also support ordinary
                    # scientific episodes without any homology job binding.
                    binding = self.execution_expectations
                    if binding is not None and (estimate['job_ref'] is None or namespace != 'job_execution_estimate'):
                        names = (grain,) if grain is not None else binding.by_grain
                        refs = {item.ref for name in names for item in binding.by_grain.get(name, ())}
                        if estimate['execution_class_ref'] in refs:
                            return True
                return bool(self.job_episodes and self.job_episodes.resolve(
                    self.store, scope, reference, namespace,
                    assignment=assignment))
            kind = self.store.get(reference)["record_type"]
            return (not namespace or namespace == kind or
                    namespace == "subject" and kind in {"input", "feature", "product", "read_subject"})
        return resolve

    def scientific_library_available(self, source):
        if self.scientific_process_binding is None:
            return False
        if source is None:
            return True
        if self.is_job_source(source):
            return False
        binding = self.specialist(source)
        return (binding is None or 'scientific_process' in binding.allowed_children(
            self.binding_context(source), self.services.capabilities()))

    def scientific_retriever_catalog(self):
        from .scientific_tool_library import catalog
        configuration = self.scientific_process_binding.tool_retrieval
        return catalog(retrieval_mode=None if configuration is None else configuration['mode'],
            tool_info=self.scientific_process_binding.tool_library.supports_tool_info)

    def catalog(self, scope, source=None):
        if restricted_root(self, source):
            entries = self.shared_information_catalog(source)
            if self.receipts is not None and source is not None and self.permits_common_action(source, 'wait'):
                entries.append(_wait_estimate_operation())
            return entries
        catalog = (self.job_episodes.catalog(source) if source is not None and self.is_job_source(source)
                   else self.specialist(source).catalog(self.binding_context(source))
                   if source is not None and self.specialist(source) is not None
                   else self.tools.catalog(scope=scope))
        entries = ([{"name": name, **definition} for name, definition in catalog.items()]
                   if isinstance(catalog, Mapping) else list(catalog))
        knowledge_tools = knowledge_catalog()
        launch_tools = launch_instruction_catalog()
        from .shared_information import catalog as shared_catalog
        shared_tools = self.shared_information_catalog(source)
        process_tools = []
        if self.scientific_process_binding is not None:
            from .scientific_process_library import catalog as scientific_catalog
            process_tools = scientific_catalog() + self.scientific_retriever_catalog()
        reserved = {'episode.history', 'episode.credit', 'episode.annotation_score', 'episode.estimate_wait',
                    'episode.monitoring_information', *(item['name'] for item in knowledge_tools),
                    *(item['name'] for item in launch_tools),
                    *(item['name'] for item in shared_catalog()),
                    *(item['name'] for item in process_tools)}
        if any(item['name'] in reserved for item in entries):
            raise WorkflowError("Episode inspection tools are owned by the current Episode runtime")
        for entry in entries:
            guides = self.knowledge.entries_for_tool(entry['name'])
            if guides:
                entry['knowledge_entry_ids'] = guides
        entries.extend(knowledge_tools)
        entries.extend(launch_tools)
        entries.extend(shared_tools)
        if self.scientific_library_available(source):
            entries.extend(process_tools)
        if source is not None and self.permits_common_action(source, 'wait'):
            entries.append(_wait_estimate_operation())
        entries.append({"name": "episode.history", "description":
            "Read only this Episode's prior decisions: metadata index, exact selected actions/outcomes and admitted direct-child forms, or a bounded publication-ID page from one prior own action. Prior history-read bodies are represented by references to their original decision indices; read those indices directly rather than recursively copying history responses. Original scientific outcomes remain exact. Failed outcomes remain failed. In view=records, a saved rejected selection retains its exact rejection_feedback without becoming an executed outcome. This ordinary read never executes old work or reads child-private conversations.",
            "input_schema": {"anyOf": [{"type": "object", "additionalProperties": False,
                "required": ["view"], "properties": {
                    "view": {"type": "string", "enum": ["index", "records"]},
                    "offset": {"type": "integer", "minimum": 0,
                        "description": "Position in this Episode's ordered prior-decision page; omit when selecting decision_indices."},
                    "limit": {"type": "integer", "minimum": 1,
                        "description": "Requested page size; defaults to max(1, restoration preview_size), so disabling automatic previews still permits an ordinary page to advance. Omit when selecting decision_indices."},
                    "decision_indices": {"type": "array", "minItems": 1, "uniqueItems": True,
                        "items": {"type": "integer", "minimum": 0}}}},
                {"type": "object", "additionalProperties": False,
                 "required": ["view", "decision_index"], "properties": {
                    "view": {"type": "string", "const": "publications"},
                    "decision_index": {"type": "integer", "minimum": 0},
                    "offset": {"type": "integer", "minimum": 0,
                        "description": "Position in the actual saved publication-ID array for this one prior own action."},
                    "limit": {"type": "integer", "minimum": 1,
                        "description": "Requested publication-ID page size; defaults to max(1, restoration preview_size)."}}}]}})
        projector = self.credit_detail_projector(source)
        if callable(getattr(projector, "read_details", None)):
            entries.append({"name": "episode.credit", "description":
                "Read the current credit projection for this Episode's fixed scope using this run's actual frozen projector and policy. The explicit limit and offset page source contributions and inactive dependencies independently; each includes its own total and next_offset. Zero limit requests metadata only. These are current source-bound operands, not biological accuracy or newly performed work.",
                "input_schema": _object({
                    "limit": {"type": "integer", "minimum": 0},
                    "offset": {"type": "integer", "minimum": 0}})})
        if (not (source is not None and self.is_job_source(source))
                and callable(getattr(self.project_annotation_score, 'read_details', None))):
            entries.append({'name': 'episode.annotation_score', 'description':
                'Inspect the separately bound score for each proposed annotation and its actual evidence operands for this fixed scope. This uses the same projector and policy as the annotation scores in your decision context. Explicit limit and offset page its source contributions and inactive dependencies; limit zero requests metadata only. The result does not award investigation progress or establish biological correctness.',
                'input_schema': _object({
                    'limit': {'type': 'integer', 'minimum': 0},
                    'offset': {'type': 'integer', 'minimum': 0}})})
        if self.native_timing_information is not None:
            entries.append({'name': 'episode.monitoring_information', 'description':
                'Read this episode\'s separately bound monitoring credit for received native durations. Explicit limit/offset page actual measurements beyond the inherited/original baseline. This read changes no scientific state, timer, job or continuation rule.',
                'input_schema': _object({'limit': {'type': 'integer', 'minimum': 0},
                                         'offset': {'type': 'integer', 'minimum': 0}})})
        binding = self.specialist(source) if source is not None else None
        if self.decision_protocol == DECISION_EXCHANGE_PROTOCOL:
            # The pending-decision lookup covers metadata and selected inputs
            # only. Keep the existing ordinary reader for exact own outcomes;
            # otherwise a fresh provider can see only its last source read.
            # Metadata inspection stays in request_context, while a selected
            # outcome read retains the original action/observation semantics.
            for entry in entries:
                if entry['name'] == 'episode.history':
                    entry['input_schema']['anyOf'][0]['properties']['view'] = {
                        'type': 'string', 'const': 'records'}
        names = getattr(binding, 'common_tool_names', None)
        if names is not None:
            permitted = set(names(self.binding_context(source)))
            instruction_tools = {entry['name'] for entry in launch_tools}
            entries = [entry for entry in entries if entry['name'] in permitted | instruction_tools]
        return entries

    def credit_detail_projector(self, source):
        """The Store/scope detail port belongs to the actual scientific binding.

        Operational specialist projections use their own context/receipt port.
        They do not acquire a scientific detail reader from the root projector.
        """
        if source is not None:
            if self.is_job_source(source):
                return None
            specialist = self.specialist(source)
            if specialist is not None and specialist.credit_kind(source.path[-1][0]) != 'scientific':
                return None
        return (self.scientific_projector_for_context(self.binding_context(source))
                if source is not None else self.project_credit)

    def credit_read(self, source, arguments):
        """Read declared projection details without choosing another score binding.

        A caller-injected projector must explicitly declare this capability;
        the runtime cannot replace it with the application's default policy.
        Scientific state is unchanged and ordinary action accounting remains
        in DecisionSource.execute, rather than inside this read helper.
        """
        projector = self.credit_detail_projector(source)
        return self.projection_read(source, arguments, projector,
            projector_arguments=self.projection_arguments(source) if projector is not None else {})

    def annotation_score_read(self, source, arguments):
        projector_arguments = (self.projector_receipt_arguments(self.project_annotation_score, source.episode_id)
            if self.project_annotation_score is not None else {})
        result = self.projection_read(source, arguments, self.project_annotation_score,
                                      channel='annotation_score', projector_arguments=projector_arguments)
        if result['status'] == 'completed':
            details = result['result']
            if 'credit' in details:
                details['annotation_score'] = details.pop('credit')
            details['interpretation'] = 'annotation_support_not_investigation_progress'
            details['annotation_score_binding'] = _plain(self.annotation_score_binding)
        return result

    def projection_read(self, source, arguments, projector, *, channel='credit', projector_arguments=None):
        """One detail-read path for a declared projector, with no score fallback."""
        reader = getattr(projector, 'read_details', None)
        if not callable(reader):
            return {"status": "unavailable", "record_refs": [], "changed_record_refs": [],
                "result": None, "feedback": {"code": channel+'_details_not_declared'}}
        try:
            with self.store.read_snapshot():
                result = _plain(reader(self.store, source.scope,
                    details_limit=arguments["limit"], details_offset=arguments["offset"],
                    **(projector_arguments or {})))
            collection = (channel == 'annotation_score' and isinstance(result, dict)
                and result.get('mode') == 'proposed_annotation_collection'
                and isinstance(result.get('proposed_annotations'), list)
                and isinstance(result.get('comparisons'), list) and 'credit' not in result)
            if not isinstance(result, dict) or ("credit" not in result and not collection):
                raise ValueError(channel+'_details_record_required')
        except Exception as error:
            return {"status": "failed", "record_refs": [], "changed_record_refs": [],
                "result": None, "feedback": {"code": channel+'_details_read_failed',
                    "exception_type": type(error).__name__, "detail": str(error)}}
        return {"status": "completed", "record_refs": [], "changed_record_refs": [],
                "result": result, "feedback": None}

    def _decision_rejection(self, source, index, *, include_feedback=False):
        """Read an actual own rejection; older journals may have no effects table."""
        if self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_decision_effects'").fetchone() is None:
            return None
        projection = "json_extract(effect,'$.feedback')" if include_feedback else "NULL"
        row = self.store.db.execute("SELECT " + projection + " AS feedback "
            "FROM runtime_decision_effects WHERE run_id=? AND episode_id=? "
            "AND decision_index=? AND json_extract(effect,'$.version')=? "
            "AND json_extract(effect,'$.state')='rejected'",
            (self.run_id, source.episode_id, index, EFFECT_VERSION)).fetchone()
        if row is None:
            return None
        result = {"state": "rejected"}
        if include_feedback:
            result["feedback"] = json.loads(row["feedback"]) if row["feedback"] is not None else None
        return result

    def _history_rows(self, source, before, *, offset=0, limit=None, indices=None, newest=False):
        # json_extract projects metadata in SQLite: archived source bodies,
        # scientific payloads, old contexts and repeated schemas stay on disk.
        child_roles = (*(() if self.job_episodes is None else self.job_episodes.roles),
                       *self.episode_bindings.roles)
        clauses = ["calls.run_id=?", "calls.episode_id=?", "calls.call_index<?", "calls.response IS NOT NULL"]
        parameters = [self.run_id, source.episode_id, before]
        if indices is not None:
            clauses.append("calls.call_index IN (" + ",".join("?" for _ in indices) + ")")
            parameters.extend(indices)
        query = ("SELECT calls.call_index AS decision_index, "
            "CASE WHEN json_extract(calls.response,'$.selection.kind') IN "
            "('tool','reason','child','job_child','episode_child','wait','redeliver_report') THEN "
            "json_extract(calls.response,'$.selection.kind') ELSE 'unrecognized' END AS kind, "
            "CASE WHEN json_extract(calls.response,'$.selection.role') IN ("
            + ",".join("?" for _ in child_roles) + ") THEN "
            "json_extract(calls.response,'$.selection.role') ELSE NULL END AS child_role, "
            "CASE WHEN EXISTS (SELECT 1 FROM json_each(calls.request,'$.context.tools') saved_tool "
            "WHERE json_extract(saved_tool.value,'$.name')="
            "json_extract(calls.response,'$.selection.tool')) THEN "
            "json_extract(calls.response,'$.selection.tool') ELSE NULL END AS tool, "
            "actions.decision_index AS action_index, actions.credit, "
            "actions.result IS NOT NULL AS result_recorded, "
            "CASE WHEN json_extract(actions.result,'$.status') IN "
            "('completed','partial','failed','invalid','unavailable') THEN "
            "json_extract(actions.result,'$.status') ELSE 'unrecognized' END AS status, "
            "attempts.decision_index AS attempt_index, attempts.form IS NOT NULL AS report_admitted, "
            "attempts.failure IS NOT NULL AS report_failed "
            "FROM runtime_model_calls calls LEFT JOIN runtime_actions actions "
            "ON actions.run_id=calls.run_id AND actions.episode_id=calls.episode_id "
            "AND actions.decision_index=calls.call_index LEFT JOIN runtime_report_attempts attempts "
            "ON attempts.run_id=calls.run_id AND attempts.parent_episode_id=calls.episode_id "
            "AND attempts.decision_index=calls.call_index WHERE " + " AND ".join(clauses)
            + " ORDER BY calls.call_index " + ("DESC" if newest else "ASC"))
        parameters = [*child_roles, *parameters]
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            parameters.extend([limit, offset])
        rows = list(self.store.db.execute(query, parameters))
        if newest:
            rows.reverse()
        result = []
        for row in rows:
            kind = row["kind"]
            if row["result_recorded"]:
                status = row["status"]
            elif row["action_index"] is not None:
                status = "pending"
            elif row["attempt_index"] is not None:
                status = "report_delivered" if row["report_admitted"] else "report_delivery_failed"
            elif self._decision_rejection(source, row["decision_index"]) is not None:
                status = "rejected"
            elif (kind in {"child", "job_child", "episode_child"}
                    and ("improvement" if kind == "child" else row["child_role"]) in self.grains
                    and self.store.db.execute(
                    "SELECT 1 FROM runtime_episodes WHERE run_id=? AND episode_id=?", (self.run_id,
                    Episode.identity(self.context, self.grains[
                        "improvement" if kind == "child" else row["child_role"]], f"child_{row['decision_index']}",
                    parent_path=source.path).episode_id)).fetchone() is not None):
                status = "pending"
            else:
                status = "unexecuted"
            result.append({"decision_index": row["decision_index"], "kind": kind,
                "tool": row["tool"] if kind == "tool" else None,
                "status": status, "credit": row["credit"]})
        return result

    def history_preview(self, source, *, before):
        total = self.store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index<? AND response IS NOT NULL",
            (self.run_id, source.episode_id, before)).fetchone()[0]
        size = self.restoration_settings["preview_size"]
        entries = self._history_rows(source, before, limit=size, newest=True)
        return {"total_prior_decisions": total, "preview_size": size,
                "omitted_prior_decisions": total-len(entries), "entries": entries,
                "exact_read_tool": "episode.history"}

    @staticmethod
    def _history_outcome_view(action):
        if action is None or action['result'] is None:
            return None
        outcome = json.loads(action['result'])
        selection = json.loads(action['action'])
        body = outcome.get('result')
        if (selection.get('kind') == 'tool' and selection.get('tool') == 'episode.history'
                and isinstance(body, dict) and body.get('view') == 'records'
                and isinstance(body.get('records'), list)
                and body['records']):
            # Keep the original journal result intact. A history result points
            # to earlier decisions; copying its copies again adds no evidence.
            indices = [record['decision_index'] for record in body['records']]
            shown = {key: value for key, value in body.items() if key != 'records'}
            shown['records_reference'] = {'tool': 'episode.history',
                'arguments': {'view': 'records', 'decision_indices': indices}}
            outcome = {**outcome, 'result': shown}
        return outcome

    def history_read(self, source, args, *, before):
        if args["view"] == "publications":
            return self.publication_history_read(source, args, before=before)
        if "decision_indices" in args and ("offset" in args or "limit" in args):
            return {"status": "invalid", "record_refs": [], "changed_record_refs": [],
                "feedback": {"code": "history_selection_conflict"}}
        indices = args.get("decision_indices")
        if indices is not None:
            present = {row[0] for row in self.store.db.execute("SELECT call_index FROM runtime_model_calls "
                "WHERE run_id=? AND episode_id=? AND call_index<? AND response IS NOT NULL "
                "AND call_index IN (" + ",".join("?" for _ in indices) + ")",
                [self.run_id, source.episode_id, before, *indices])}
            if present != set(indices):
                return {"status": "invalid", "record_refs": [], "changed_record_refs": [],
                    "feedback": {"code": "history_decision_not_available", "decision_indices":
                                 [index for index in indices if index not in present]}}
        offset = args.get("offset", 0)
        # Zero disables automatic previews, not an explicitly selected read.
        # The positive page fallback matches the ordinary tool's limit contract.
        limit = None if indices is not None else args.get("limit", max(1, self.restoration_settings["preview_size"]))
        entries = self._history_rows(source, before, offset=offset, limit=limit, indices=indices)
        total = self.store.db.execute("SELECT count(*) FROM runtime_model_calls WHERE run_id=? "
            "AND episode_id=? AND call_index<? AND response IS NOT NULL",
            (self.run_id, source.episode_id, before)).fetchone()[0]
        result = {"view": args["view"], "total_prior_decisions": total,
            "offset": offset, "limit": limit,
            "next_offset": (offset+len(entries) if indices is None and offset+len(entries)<total else None)}
        if args["view"] == "index":
            result["entries"] = entries
        else:
            records = []
            for entry in entries:
                index = entry["decision_index"]
                row = self.store.db.execute("SELECT response -> '$.selection' FROM runtime_model_calls "
                    "WHERE run_id=? AND episode_id=? AND call_index=?",
                    (self.run_id, source.episode_id, index)).fetchone()
                action = self.journal.row("runtime_actions", source.episode_id, index)
                progress = self.store.db.execute("SELECT observation FROM runtime_observations "
                    "WHERE run_id=? AND episode_id=? AND json_extract(observation,'$.decision_index')=?",
                    (self.run_id, source.episode_id, index)).fetchone()
                attempt = self.store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
                    "AND parent_episode_id=? AND decision_index=?", (self.run_id, source.episode_id, index)).fetchone()
                admitted = None
                if attempt is not None and attempt["form"] is not None:
                    child_row = self.journal.row("runtime_episodes", attempt["child_episode_id"])
                    request = json.loads(child_row["request"])
                    contract = json.loads(attempt["contract"])
                    scope, path = request['message']['scope'], json.loads(child_row['path'])
                    role = path[-1][0]
                    assignment = request['message'].get('job_assignment')
                    binding_context = BindingContext(self.run_id, attempt['child_episode_id'], role,
                        path, scope, request['message'].get('episode_assignment', {}), request)
                    saved_schema = contract['measurements']['schema']
                    admitted = TypedReportContract(contract["decision"], contract["measurements"]["schema"],
                        self.resolver(scope, assignment=assignment, grain=role, context=binding_context),
                        lambda value: self.validate_report(value, scope, assignment=assignment,
                            grain=role, schema=saved_schema, context=binding_context)).admit(json.loads(attempt["form"]),
                        audit_identifiers=(attempt["child_episode_id"], request["goal"]["goal_id"])).as_record()
                rejection = (self._decision_rejection(source, index, include_feedback=True)
                    if entry["status"] == "rejected" else None)
                records.append({**entry, "selection": json.loads(row[0]) if row[0] is not None else None,
                    "outcome": self._history_outcome_view(action),
                    **({"rejection_feedback": rejection["feedback"]} if rejection is not None else {}),
                    "admitted_report": admitted,
                    "report_delivery_failure": json.loads(attempt["failure"]) if attempt and attempt["failure"] else None,
                    "execution_timing": {
                        "decision": execution_timing.snapshot(self.journal.row("runtime_model_calls", source.episode_id, index)["timing"]),
                        "work": execution_timing.snapshot(action["timing"]) if action else None},
                    "controller_observation": json.loads(progress[0]) if progress else None})
            result["records"] = records
        return {"status": "completed", "record_refs": [], "changed_record_refs": [], "result": result}

    def publication_history_read(self, source, args, *, before):
        """Page one own prior action's recorded IDs without decoding its body."""
        index = args.get("decision_index")
        offset = args.get("offset", 0)
        limit = args.get("limit", max(1, self.restoration_settings["preview_size"]))
        if (set(args) - {"view", "decision_index", "offset", "limit"}
                or type(index) is not int or index < 0 or type(offset) is not int or offset < 0
                or type(limit) is not int or limit < 1):
            return {"status": "invalid", "record_refs": [], "changed_record_refs": [],
                    "feedback": {"code": "invalid_publication_history_selection"}}
        with self.store.read_snapshot():
            entries = self._history_rows(source, before, indices=[index])
            if not entries:
                return {"status": "invalid", "record_refs": [], "changed_record_refs": [],
                    "feedback": {"code": "history_decision_not_available", "decision_indices": [index]}}
            entry = entries[0]
            selected = self.store.db.execute("SELECT result IS NOT NULL AS recorded, "
                "json_array_length(result,'$.record_refs') AS total FROM runtime_actions "
                "WHERE run_id=? AND episode_id=? AND decision_index=?",
                (self.run_id, source.episode_id, index)).fetchone()
            recorded = bool(selected and selected["recorded"])
            total = selected["total"] if recorded else None
            rows = self.store.db.execute("SELECT CAST(ids.key AS INTEGER) AS publication_index, "
                "ids.value AS record_ref FROM runtime_actions actions "
                "JOIN json_each(actions.result,'$.record_refs') ids "
                "WHERE actions.run_id=? AND actions.episode_id=? AND actions.decision_index=? "
                "ORDER BY CAST(ids.key AS INTEGER) LIMIT ? OFFSET ?",
                (self.run_id, source.episode_id, index, limit, offset)) if recorded else ()
            records = [dict(row) for row in rows]
        next_offset = (offset + len(records)
                       if total is not None and offset + len(records) < total else None)
        result = {"view": "publications", "decision_index": index, "action_status": entry["status"],
            "result_recorded": recorded, "total": total, "offset": offset, "limit": limit,
            "records": records, "next_offset": next_offset,
            "next_query": {"view": "publications", "decision_index": index,
                "offset": next_offset, "limit": limit} if next_offset is not None else None}
        return {"status": "completed", "record_refs": [], "changed_record_refs": [], "result": result}

    async def execute(self, source, name, arguments, *, decision_index, operation_key,
                      _composition_lookup=False):
        if restricted_root(self, source) and not _composition_lookup:
            from .shared_information import TOOLS as shared_tools
            waiting_operation = name == 'episode.estimate_wait' and self.permits_common_action(source, 'wait')
            if self.receipts is None or (name not in shared_tools and not waiting_operation):
                return {'status':'invalid','record_refs':[],'changed_record_refs':[],'result':None,
                    'feedback':{'code':'root_tool_requires_shared_coordination_operation'}}
        if source.path[-1][0] == 'scientific_process':
            self.scientific_process_binding.validate_execution_context(self.binding_context(source))
        if _composition_lookup and name in CONTRACT_INFORMATION_OPERATIONS:
            saved, record = self.pending_contract_information(source, decision_index)
            lookup = record['exchange_schema']['properties']['response']['anyOf'][0]['properties']['lookup']
            entry = next((row for row in lookup['anyOf']
                if row.get('properties', {}).get('operation', {}).get('const') == name), None)
            if entry is None:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'decision_exchange', 'code': 'composition_operation_not_available'}}
            try:
                Draft202012Validator(entry['properties']['arguments']).validate(arguments)
                return self.contract_information_reply(saved, record, name, arguments)
            except (ValueError, TypeError, ValidationError):
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'decision_exchange', 'code': 'composition_arguments_invalid'}}
        if _composition_lookup:
            entry = next((entry for entry in composition_catalog(self, source)
                          if entry['name'] == name), None)
            if entry is None:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'decision_exchange', 'code': 'composition_operation_not_available'}}
            try:
                Draft202012Validator(entry['input_schema']).validate(arguments)
            except ValidationError:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'decision_exchange', 'code': 'composition_arguments_invalid'}}
        elif not self.permits_common_action(source, 'tool'):
            return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_or_reference', 'code': 'tool_not_available_to_episode'}}
        binding = self.specialist(source)
        if not _composition_lookup and binding is not None and callable(getattr(binding, 'common_tool_names', None)):
            entry = next((entry for entry in self.catalog(source.scope, source=source)
                          if entry['name'] == name), None)
            try:
                if entry is None:
                    raise ValueError('tool_not_available_to_episode')
                Draft202012Validator(entry['input_schema']).validate(arguments)
            except (ValueError, ValidationError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference',
                        'code': ('tool_arguments_invalid' if isinstance(error, ValidationError)
                                 else str(error))}}
        if self.scientific_process_binding is not None:
            from .scientific_process_library import catalog as scientific_catalog
            retriever_catalog = self.scientific_retriever_catalog()
            if name in {item['name'] for item in scientific_catalog() + retriever_catalog}:
                if not self.scientific_library_available(source):
                    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                        'feedback': {'category': 'arguments_or_reference',
                                     'code': 'tool_not_available_to_episode'}}
                if name == 'process.tools':
                    try:
                        Draft202012Validator(retriever_catalog[0]['input_schema']).validate(arguments)
                        tools = self.scientific_process_binding.tool_library
                        available = (self.services.tool_information_catalog(source.scope)
                            if tools.supports_tool_info else self.services.tool_catalog(source.scope))
                        # Legacy name-only selections keep their original direct
                        # map. Resource information never extends that map.
                        if not tools.supports_tool_info:
                            tools.resolve([entry['name'] for entry in tools.catalog()], available)
                        if self.scientific_tool_retriever is not None:
                            return await self.scientific_tool_retriever.retrieve(arguments['investigation'],
                                episode_id=source.episode_id, operation_key=operation_key,
                                available_catalog=available)
                        result = tools.retrieve_literal_test(arguments['investigation'],
                            available_catalog=available)
                        return {'status': 'completed', 'record_refs': [],
                            'changed_record_refs': [], 'result': result, 'feedback': None}
                    except (ValueError, ValidationError) as error:
                        return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                            'result': None, 'feedback': {'code': str(error)}}
                outcome = self.scientific_process_binding.library.execute(name, arguments)
                if name == 'process.entry' and outcome['status'] == 'completed':
                    from .scientific_support_metadata import (SUPPORT_ENTRY_VERSION,
                        support_observation_kinds)
                    result = outcome['result']
                    if result['entry'].get('entry_version') == SUPPORT_ENTRY_VERSION:
                        outcome = {**outcome, 'result': {**result,
                            'annotation_support_routes': self.services.scientific_support_routes(
                                self.binding_context(source),
                                observation_kinds=support_observation_kinds(result['entry']))}}
                return outcome
        if name == 'episode.estimate_wait':
            if not self.permits_common_action(source, 'wait'):
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                    'result': None, 'feedback': {'category': 'arguments_or_reference',
                                               'code': 'tool_not_available_to_episode'}}
            call = self.journal.row('runtime_model_calls', source.episode_id, decision_index)
            original_context = json.loads(call['request'])['context']
            return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [],
                'result': self.wait_estimate(source, arguments['condition'], original_context)}
        if name in {item['name'] for item in knowledge_catalog()}:
            return self.knowledge.execute(name, arguments)
        if name in {item['name'] for item in launch_instruction_catalog()}:
            return self.launch_instructions.execute(name, arguments)
        if _composition_lookup:
            raise WorkflowError('composition_lookup_has_no_instruction_handler')
        if name == "episode.history":
            return self.history_read(source, arguments, before=decision_index)
        if name == "episode.credit":
            return self.credit_read(source, arguments)
        from .shared_information import TOOLS as shared_tools
        if name in shared_tools:
            try:
                repository = self.shared_information_repository()
                if repository is None:
                    raise ContractError('shared_information_receipt_binding_required')
                return repository.execute(self.binding_context(source), name, arguments,
                    known_record_refs=self.receipts.known(source.episode_id), operation_key=operation_key)
            except (ValueError, ValidationError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                    'result': None, 'feedback': {'code': str(error)}}
        if name == 'episode.annotation_score':
            return self.annotation_score_read(source, arguments)
        if name == 'episode.monitoring_information':
            return self.projection_read(source, arguments, self.native_timing_information,
                channel='native_timing_information', projector_arguments=self.native_timing_arguments(source))
        if self.is_job_source(source):
            result = await self.job_episodes.execute(source, name, arguments, operation_key=operation_key)
            if self.resource_estimator is not None:
                call = self.journal.row("runtime_model_calls", source.episode_id, decision_index)
                context = json.loads(call["request"])["context"]
                sample = (result.get("result") if result.get("operational_sample_ref") else
                          self.job_episodes.latest_sample(source, include_inherited=True))
                result["resource_tool_estimates"] = self.resource_estimator.estimate(
                    context.get("execution_expectations"), job_ref=self.job_episodes.assignment(source)["job_ref"],
                    sample=sample)
            return result
        specialist = self.specialist(source)
        invocation = getattr(self.tools, 'current_invocation', None)
        protein_invocation = getattr(self.tools, 'protein_structure_invocation', None)
        with (invocation(self.binding_context(source),
                read_received=(self.services.read_received_molecular_file_metadata
                    if name == 'public.ncbi.sra.file' else self.services.read_received_molecular_input),
                tool_name=name, arguments=arguments, operation_key=operation_key)
                if callable(invocation) else nullcontext()), (
                protein_invocation(self.services.protein_structure_input_authority())
                if callable(protein_invocation) else nullcontext()):
            if specialist is not None:
                result = specialist.execute(self.binding_context(source), name, arguments, operation_key)
                result = await result if inspect.isawaitable(result) else result
            else:
                execute = getattr(self.tools, "execute_async", self.tools.execute)
                result = execute(name, arguments, scope=source.scope, operation_key=operation_key)
                result = await result if inspect.isawaitable(result) else result
        if self.resource_estimator is not None:
            if name == 'execution.estimate' and result.get('status') == 'completed':
                original = result['result']['execution_expectations']
                result['native_execution_expectations'] = original
                result['resource_tool_estimates'] = self.resource_estimator.estimate_context(original)
            elif result.get('native_execution_refs'):
                call = self.journal.row('runtime_model_calls', source.episode_id, decision_index)
                context = json.loads(call['request'])['context']
                classes = {read_measurement(self.store, ref).execution_class.ref
                           for ref in result['native_execution_refs']}
                # Retain the predictions that actually preceded this work.
                # Do not substitute the newly completed duration for a forecast.
                estimates = [item for item in context.get('resource_tool_estimates', [])
                             if item['execution_class_ref'] in classes]
                if estimates:
                    result['resource_tool_estimates'] = estimates
                if context.get('native_execution_expectations') is not None:
                    result['native_execution_expectations'] = context['native_execution_expectations']
        return result

    def reasoning_action_schema(self, source, commit_schema=None, *, _accept_legacy_quotes=False):
        commit_schema = self.store.reasoning_schema() if commit_schema is None else commit_schema
        specialist = self.specialist(source)
        schema = (getattr(specialist, 'accept_reasoning_action_schema', None)
                  if _accept_legacy_quotes else None)
        if schema is None:
            schema = getattr(specialist, 'reasoning_action_schema', None)
        selected = schema(self.binding_context(source), commit_schema) if schema is not None else None
        result = selected if selected is not None else _object({
            'kind': {'type': 'string', 'const': 'reason'}, 'commit': commit_schema})
        # Describe the existing pre-acquisition check without changing the
        # payload, row-level partial admission or optional processing contract.
        return {**result, 'description': '\n\n'.join(value for value in
            (result.get('description'), REASONING_COMMIT_REQUIREMENT) if value)}

    def action_schema(self, source):
        # API documentation only. The parent still supplies its own contract
        # and initial values; this example is never selected or installed by
        # the runtime, and has no scientific/controller effect.
        form_example = _object({
            "changed_annotation_refs": {"type": "array", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "annotation"},
                "x-source": "changed_annotation_refs",
                "description": "Actual annotation revisions changed during this investigation; these references are not a claim that every revision is still current."},
            "changed_assessment_refs": {"type": "array", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "assessment"},
                "x-source": "changed_assessment_refs",
                "description": "Actual changed source-linked assessment revisions, retaining their hypotheses, observations, relations and applicability."},
            "changed_interpretation_account_refs": {"type": "array", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "interpretation_account"},
                "x-source": "changed_interpretation_account_refs",
                "description": FACT_MEANINGS['changed_interpretation_account_refs']},
            "scoped_credit": {"type": "number", "x-source": "credit",
                "description": "Credit projected for the fixed child scope at completion, not an accuracy verdict or a stopping instruction."},
        })
        interpretive_example = _object({
            "interpreted_assessment_refs": _array({"type": "string", "format": "reference",
                "x-reference-namespace": "assessment",
                "description": "Assessments the child selects as bearing on the assigned distinction. Each resolves to its actual hypothesis, observation, relation, conditions and assumptions; a non-discriminating result remains useful information."}),
            "unresolved_hypothesis_refs": _array({"type": "string", "format": "reference",
                "x-reference-namespace": "hypothesis",
                "description": "In-scope alternatives the child currently considers unresolved; an empty array makes no claim that every possible explanation was tested."}),
            "changed_annotation_refs": form_example["properties"]["changed_annotation_refs"],
            "interpretation_basis_refs": {"type": "array", "items": {
                "type": "string", "format": "reference"}, "x-source": "interpretation_basis_refs",
                "description": FACT_MEANINGS["interpretation_basis_refs"]},
            "observations_after_report_basis": {"type": "array", "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "observation"},
                "x-source": "observations_after_report_basis",
                "description": FACT_MEANINGS["observations_after_report_basis"]},
        })
        scope_schema = {"type": "object", "additionalProperties": False,
            "required": ["subject_refs"], "properties": {
                "subject_refs": _array({"type": "string"}),
                "read_selection_refs": _array({"type": "string"}),
                "segments": _array({"type": "object", "additionalProperties": False,
                    "required": ["target_ref", "start", "end", "unit"], "properties": {
                    "target_ref": {"type": "string"}, "member_ref": {"type": "string"},
                    "start": {"type": "integer", "minimum": 0},
                    "end": {"type": "integer", "minimum": 1},
                    "unit": {"type": "string", "enum": ["nt", "aa", "symbol"]}}})}}
        specialist = self.specialist(source)
        common_actions = (specialist.permitted_common_actions(self.binding_context(source))
                          if specialist is not None else ('tool', 'reason', 'child', 'wait', 'redeliver_report'))
        if not self.permits_common_action(source, 'wait'):
            common_actions = tuple(action for action in common_actions if action != 'wait')
        if restricted_root(self, source):
            if self.receipts is None:
                common_actions = tuple(action for action in common_actions if action != 'tool')
        options = ([] if self.is_job_source(source) or 'reason' not in common_actions else [
            self.reasoning_action_schema(source)])
        if 'wait' in common_actions:
            options.append(_object({'kind': {'type': 'string', 'const': 'wait'},
                                    'condition': _wait_condition_schema()}))
        for item in (self.catalog(source.scope, source=source) if 'tool' in common_actions else ()):
            branch = _object({"kind": {"type": "string", "const": "tool"},
                "tool": {"type": "string", "const": item["name"]},
                "arguments": _embedded_tool_schema(item["input_schema"])})
            if item.get('argument_transport') is not None:
                if item['argument_transport'] != CONTRACT_ARGUMENT_TRANSPORT:
                    raise ValueError('unsupported_tool_argument_transport')
                branch['x-argument-transport'] = CONTRACT_ARGUMENT_TRANSPORT
            options.append(branch)
        scientific_child = _object({"kind": {"type": "string", "const": "child"},
            "goal": {"type": "string", "description": "A substantive improvement the child can pursue iteratively and revise from outcomes. A fully specified one-off lookup/calculation belongs to an ordinary tool. Numerical yield controls the child's continuation."},
            "scope": scope_schema,
            "purpose": {"type": "string", "description": "Explain what information you need for your later scientific decision and what your selected form fields mean."},
            "schema_json": {"type": "string", "description": "JSON encoding of your parent-defined closed return form: explicit required fields, additionalProperties false, typed arrays, and strings restricted to enum codes or declared semantic formats. A reference can declare format reference and x-reference-namespace. Optional top-level x-source selectors bind recorded facts named in available_report_facts; do not ask a model to invent those facts. These examples are optional API guidance; choose fields and meanings for your actual later decision. Fact-only example: " + _json(form_example) + " Interpretive example, selecting actual assessment records rather than a findings paragraph: " + _json(interpretive_example)},
            "initial_report_json": {"type": "string", "description": "JSON containing exactly the interpretation fields you chose (those without x-source), with parent-supplied initial values. Use {} for the fact-only example; for the interpretive example use {\"interpreted_assessment_refs\":[],\"unresolved_hypothesis_refs\":[]}. Those initial arrays are not new child judgments. If you request other interpreted fields, define their allowed meanings and initialize them explicitly. The runtime does not choose fields or unknown values for you."}})
        if not self.is_job_source(source):
            explicit_roles = (None if self.annotation_child_roles is None
                and not (len(source.path) == 1 and getattr(self.project_credit, 'task_credit', False)) else
                self.available_child_roles(source))
            if (specialist is None and self.scientific_process_binding is None and 'child' in common_actions
                    and (explicit_roles is None or 'improvement' in explicit_roles)):
                options.append(scientific_child)
            if self.job_episodes is not None and specialist is None:
                options.extend(option for option in self.job_episodes.commission_schemas(scientific_child)
                    if explicit_roles is None or option['properties']['role']['const'] in explicit_roles)
            if 'child' in common_actions:
                roles = (tuple(role for role in explicit_roles if role in self.episode_bindings.roles)
                    if explicit_roles is not None else
                    specialist.allowed_children(self.binding_context(source), self.services.capabilities())
                    if specialist is not None else self.episode_bindings.entry_roles)
                declared = set(specialist.child_roles(source.path[-1][0])) if specialist else set(roles)
                if not set(roles) <= declared:
                    raise WorkflowError('available_child_outside_declared_type_edges')
                for role in roles:
                    binding = self.episode_bindings.for_role(role)
                    child_schema = getattr(binding, 'child_assignment_schema', None)
                    properties = {**scientific_child['properties'],
                        'kind': {'type': 'string', 'const': 'episode_child'},
                        'role': {'type': 'string', 'const': role},
                        'assignment': (child_schema(self.binding_context(source), role)
                            if child_schema is not None else binding.assignment_schema(role))}
                    if self.root_child_return_sources(source, role):
                        # This edge returns the binding's declared facts. The
                        # parent chooses the work, not the wire format.
                        properties.pop('schema_json')
                        properties.pop('initial_report_json')
                    options.append(_object(properties))
        if not self.is_job_source(source) and 'redeliver_report' in common_actions:
            options.append(_object({"kind": {"type": "string", "const": "redeliver_report"},
            "delivery_ref": {"type": "string", "description":
                "Copy the delivery_ref from report_deliveries or report_delivery_failure for the saved child report."},
            "purpose": {"type": "string"},
            "schema_json": {"type": "string"}}))
        return _object({"selection": {"anyOf": options}, "report_update": source.interpret_schema})

    def selected(self, source, selection, index):
        if selection['kind'] in {'child', 'job_child', 'episode_child'}:
            if source.path[-1][0] == 'scientific_process':
                saved = self.journal.row('runtime_actions', source.episode_id, index)
                if saved is None or saved['result'] is None:
                    self.scientific_process_binding.validate_execution_context(self.binding_context(source))
            old = (self.journal.row('runtime_actions', source.episode_id, index)
                if self.annotation_child_roles is not None else None)
            original = old is not None and json.loads(old['action']) == selection
            self.validate_child_choice(source, selection.get('role', 'improvement'),
                selection=selection, original=original)
        common_action = ('child' if selection['kind'] in {'child', 'job_child', 'episode_child'}
                         else selection['kind'])
        resolving = (selection['kind'] == 'redeliver_report'
            and selection.get('delivery_ref') == source._delivery_resolution_ref
            and self.pending_delivery(source, selection.get('delivery_ref')) is not None)
        if not resolving and not self.permits_common_action(source, common_action):
            raise ValueError('action_not_available_to_episode')
        if restricted_root(self, source) and selection['kind'] == 'tool':
            recorded = self.journal.row('runtime_actions', source.episode_id, index)
            replay = (recorded is not None and recorded['result'] is not None
                and json.loads(recorded['action']) == selection)
            if not replay and selection.get('tool') not in {
                    item['name'] for item in self.catalog(source.scope, source=source)}:
                raise ValueError('action_not_available_to_episode')
        closed = self._closed_child_commission(source, selection, index)
        if closed is not None:
            return closed
        if self.execution_binding is None and selection['kind'] in {'child', 'job_child', 'episode_child'}:
            original = self.journal.row('runtime_actions', source.episode_id, index)
            if original is not None and original['result'] is not None:
                outcome = json.loads(original['result'])
                if outcome.get('status') == 'failed' and outcome.get('feedback', {}).get('category') == 'child_execution':
                    if json.loads(original['action']) != selection or original['credit'] is None:
                        raise WorkflowError('original_child_failure_replay_conflict')
                    def failed_result(_):
                        source.last_outcome, source.last_outcome_index = outcome, index
                        source.feedback = outcome['feedback']
                        return self.controller_value(source, index, original['credit'])
                    return ActionLeaf(selection, extract=failed_result, result=lambda _, result: result,
                        label=f'child_{index}', decision_index=index)
        if selection['kind'] == 'wait':
            original = self.journal.row('runtime_actions', source.episode_id, index)
            recorded = original is not None and json.loads(original['action']) == selection
            # Exact completed replay needs no new validation. An incomplete
            # recorded choice is revalidated at dispatch so a declared failure
            # is saved through execute(), including restore outside apply_response.
            if not recorded:
                self.validate_wait_selection(source, selection['condition'])
        if selection['kind'] == 'child' and self.scientific_process_binding is not None:
            raise ValueError('scientific_child_requires_filled_process')
        if selection["kind"] == "redeliver_report":
            return self.redeliver(source, selection, index)
        if selection["kind"] not in {"child", "job_child", "episode_child"}:
            if self.execution_binding is not None or self.inprocess_replay is not None:
                old = self.journal.row('runtime_actions', source.episode_id, index)
                if old is not None and json.loads(old['action']) != selection:
                    raise WorkflowError('reconstructed selected work changed')
                if old is None:
                    self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                        'decision_index': index, 'action': _json(selection), 'result': None, 'credit': None})
            return ActionLeaf(selection, extract=lambda action: source.execute(action, index),
                result=lambda action, result: result, label=f"{selection['kind']}:{index}", decision_index=index)
        if self.execution_binding is not None:
            old = self.journal.row('runtime_actions', source.episode_id, index)
            if old is not None:
                if json.loads(old['action']) != selection:
                    raise WorkflowError('reconstructed selected work changed')
                result = json.loads(old['result']) if old['result'] is not None else {}
                handle = result.get('pending_handle')
                if handle is not None:
                    original = next((spec for spec in self.commissions.recover_selected(source.episode_id)
                                     if spec['handle'] == handle), None)
                    if original is None:
                        raise WorkflowError('pending_commission_intent_unavailable')
                    return self.deferred_unit(source, index, original)
        scope = self.store.validate_scope(selection["scope"], parent_scope=source.scope)
        role = selection.get("role", "improvement")
        episode_assignment = None
        scientific_process = None
        schema, report_declaration = self.expanded_contract_form(source, selection, index, role)
        if selection['kind'] == 'episode_child':
            binding = self.episode_bindings.for_role(role)
            required = getattr(binding, 'required_return_sources', lambda _parent, _role: ())(
                self.binding_context(source), role)
            sources = [node.get('x-source') for node in schema.get('properties', {}).values()]
            for fact_source in required:
                if sources.count(fact_source) != 1:
                    raise ContractError('child_return_requires_' + fact_source)
        # A planned HPC launch must return its actual endpoint receipt. Reject
        # a form which cannot carry it before any submission; never widen the
        # caller's form or recreate an original submitted job to repair a form.
        hpc_launch = (role == 'launch' and source.path[-1][0] in {'hpc', 'hpc_execution'}
                      or role == 'launch_hpc' and any(part[0] == 'hpc' for part in source.path))
        if hpc_launch and not any(node.get('x-source') == 'execution_handoff_refs'
                                  for node in schema.get('properties', {}).values()):
            raise ContractError('hpc_launch_requires_original_handoff_fact_in_return_form')
        initial = parse_json_object(self.child_initial_report_input(source, selection, role))
        if selection['kind'] == 'episode_child':
            # Assignment-specific references need the child's original request.
            # Check shape now; build validates them before credit or publication.
            validate_form(initial, interpretation_schema(schema), lambda *_: True)
        else:
            validate_form(initial, interpretation_schema(schema), self.resolver(scope, grain=role))
            self.validate_report(initial, scope, grain=role, schema=interpretation_schema(schema))
        if selection['kind'] == 'episode_child':
            specialist = self.specialist(source)
            allowed = (self.available_child_roles(source) if self.annotation_child_roles is not None else
                specialist.allowed_children(self.binding_context(source), self.services.capabilities())
                if specialist is not None else self.episode_bindings.entry_roles)
            if role not in allowed:
                raise ValueError('child_role_not_available_to_parent')
            binding = self.episode_bindings.for_role(role)
            # Some bindings prepare durable native work while preparing the
            # assignment. Reject stale or fabricated instruction pins first.
            self.launch_instructions.materialize(selection['assignment'].get('launch_instructions'))
            if binding is self.scientific_process_binding:
                closed = {}
                recorded = self.journal.row('runtime_actions', source.episode_id, index)
                if (recorded is not None and recorded['result'] is not None
                        and _json(json.loads(recorded['action'])) == _json(selection)
                        and json.loads(recorded['result']).get('status') == 'completed'):
                    from .episode_return_records import EpisodeReturnRecords
                    child_id = Episode.identity(self.context, self.grains[role], f'child_{index}',
                        parent_path=source.path).episode_id
                    if self.journal.row('runtime_episodes', child_id) is not None:
                        records = EpisodeReturnRecords(self.store, self.run_id,
                            failure_prefix='scientific_closed_')
                        candidate = records.context(child_id)
                        read_closed = getattr(self.services, 'scientific_closed_request', None)
                        if callable(read_closed) and read_closed(candidate) is not None:
                            closed['closed_context'] = candidate
                prepared = binding.prepare_invocation(self.binding_context(source), role,
                    selection['assignment'], scope, f'{self.run_id}:{source.episode_id}:{index}',
                    invocation={'objective': selection['goal'], 'purpose': selection['purpose'],
                        'report_schema': schema, 'initial_report': initial}, **closed)
                episode_assignment = prepared['assignment']
                scientific_process = prepared['scientific_process']
            else:
                episode_assignment = binding.prepare_assignment(
                    self.binding_context(source), role, selection['assignment'], scope,
                    f'{self.run_id}:{source.episode_id}:{index}')
        assignment = (self.job_episodes.assign(self.store, role, selection, scope,
            operation_key=f"{self.run_id}:{source.episode_id}:{index}")
            if selection["kind"] == "job_child" else None)
        # Only detached immutable context remains in the report callbacks.
        # Retaining child.source here would keep its controller/tree alive.
        contract_binding = {}
        def validator(value):
            self.validate_report(value, scope, assignment=assignment, grain=role, schema=schema,
                context=contract_binding['context'])
        def resolve(reference, namespace=None):
            return contract_binding['resolver'](reference, namespace)
        def recorded_admission(value):
            if self.receipts is None or self.is_job_source(source):
                return None
            from .episode_return_records import EpisodeReturnRecords
            return EpisodeReturnRecords(self.store, self.run_id,
                failure_prefix='recorded_admission_').recorded_admission_references(
                    self.binding_context(source), value, schema, index)
        contract = TypedReportContract(selection["purpose"], schema,
            resolve, validator, recorded_admission=recorded_admission)
        # Initial references need the actual selected commission as well as
        # the child's saved request. Publish neither if construction fails.
        with self.store.transaction():
            old = self.journal.row("runtime_actions", source.episode_id, index)
            if old is None:
                self.journal.save("runtime_actions", {"episode_id": source.episode_id, "decision_index": index,
                    "action": _json(selection), "result": None, "credit": None})
            elif json.loads(old["action"]) != selection:
                raise WorkflowError("reconstructed selected work changed")
            child = self.build(role, f"child_{index}", selection["goal"], scope,
                               parent=source.request.goal, parent_path=source.path, contract=contract,
                               initial=initial, job_assignment=assignment,
                               episode_assignment=episode_assignment, scientific_process=scientific_process,
                               **({'report_contract_declaration': report_declaration}
                                  if report_declaration is not None else {}))
            contract_binding['context'] = self.binding_context(child.source)
            contract_binding['resolver'] = self.resolver(scope, assignment=assignment, grain=role,
                context=contract_binding['context'])
            allow_suspension = self.permits_common_action(child.source, 'wait')
            if self.execution_binding is not None:
                return self.commission_child(source, child, selection, index)
        def admitted_report(result, request):
            delivery_ref = "delivery_" + _digest({"run": self.run_id, "parent": source.episode_id, "index": index})[:24]
            owned = self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
            action = self.journal.row('runtime_actions', source.episode_id, index)
            frozen_index = (None if action['result'] is None else
                json.loads(action['result']).get('delivery_resolution_index'))
            saved = self.store.db.execute('SELECT * FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND '
                + ('decision_index=?' if frozen_index is not None or not owned else
                    'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'),
                (self.run_id, source.episode_id,
                    frozen_index if frozen_index is not None else delivery_ref if owned else index)).fetchone()
            if saved is not None:
                if saved['failure'] is not None:
                    raise ReportDeliveryError(Record(json.loads(saved['failure'])))
                admitted = json.loads(saved['form'])
            else:
                try:
                    admitted = contract.admit(result.as_record()["form"], audit_identifiers=(
                        child.source.episode_id, request.goal.goal_id)).as_record()
                except ReportBoundaryError as error:
                    feedback = self.delivery_feedback(delivery_ref, error)
                    self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                                      contract, failure=feedback)
                    raise ReportDeliveryError(Record(feedback)) from error
                self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                                  contract, form=admitted)
            delivery_index = index if saved is None else saved['decision_index']
            delivery_schema = schema if saved is None else json.loads(saved['contract'])['measurements']['schema']
            references = self.receive_form(source, admitted, delivery_schema, delivery_index,
                redelivery=delivery_index != index)
            return admitted, references

        def credit(result, completion, request):
            old = self.journal.row("runtime_actions", source.episode_id, index)
            if old["result"] is None:
                facts = self.facts(child.source)
                if (self.receipts is not None
                        or self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE):
                    # Typed delivery has succeeded before this credit callback.
                    # Reuse that original admitted form; a failed delivery is
                    # never a completed acquisition with an empty receipt.
                    _, returned = admitted_report(result, request)
                    changed = set(facts['changed_record_refs'])
                    facts = {'committed_record_refs': returned,
                             'changed_record_refs': [ref for ref in returned if ref in changed]}
                outcome = {"status": "completed", "record_refs": facts["committed_record_refs"],
                    "changed_record_refs": facts["changed_record_refs"]}
                original_delivery = self.store.db.execute('SELECT MAX(decision_index) '
                    'FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? '
                    'AND delivery_ref=?', (self.run_id, source.episode_id,
                        'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id,
                            'index': index})[:24])).fetchone()[0]
                outcome['delivery_resolution_index'] = original_delivery
                from .episode_source_failure import child_completion_status
                outcome['child_completion'] = child_completion_status(self.store, self.run_id,
                    child.source.episode_id, completion.as_record(), delivery='admitted')
                if (self.wait_inputs_version == 'wait_inputs_binding_v2'
                        or self.completed_action_inputs_version is not None):
                    outcome['pending_work_after_action'] = self.pending_work(source)
                self.journal.save("runtime_actions", {"episode_id": source.episode_id,
                    "decision_index": index, "action": _json(selection),
                    "result": _json(outcome), "credit": None})
                old = self.journal.row("runtime_actions", source.episode_id, index)
            value = old["credit"]
            if value is None:
                # The parent projector must see the same returned work its
                # action record describes. A lost process here recovers that
                # outcome before projecting; it does not repeat the child.
                value = self.source_credit_view(source)["credit"]
                self.journal.save("runtime_actions", {"episode_id": source.episode_id,
                    "decision_index": index, "action": old["action"],
                    "result": old["result"], "credit": value})
            # Successful typed delivery may still carry a partial child whose
            # source failed. Present this actual completed own action to the
            # assigning parent, just as for an ordinary tool or failed child.
            source.last_outcome, source.last_outcome_index = json.loads(old['result']), index
            source.checkpoint()
            return self.controller_value(source, index, value)
        async def report(result, completion, request):
            if self.receipts is not None or self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE:
                try:
                    return admitted_report(result, request)[0]
                except ReportDeliveryError as error:
                    source.feedback = error.feedback.as_record()
                    await self.resolve_pending_deliveries(source, source._selection_view,
                        only_delivery_ref=source.feedback['delivery_ref'])
                    return admitted_report(result, request)[0]
            delivery_ref = "delivery_" + _digest({"run": self.run_id, "parent": source.episode_id, "index": index})[:24]
            try:
                admitted = contract.admit(result.as_record()["form"], audit_identifiers=(
                    child.source.episode_id, request.goal.goal_id)).as_record()
            except ReportBoundaryError as error:
                feedback = self.delivery_feedback(delivery_ref, error)
                self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                                  contract, failure=feedback)
                raise ReportDeliveryError(Record(feedback)) from error
            self.save_attempt(source.episode_id, index, delivery_ref, child.source.episode_id,
                              contract, form=admitted)
            self.receive_form(source, admitted, schema, index)
            return admitted
        scheduled = 'delay_seconds' in selection
        if scheduled:
            self.journal.schedule_child(source.episode_id, index, selection, child.source.episode_id)
        async def resolved_credit(result, completion, request):
            # The child is closed; this selected acquisition is not complete
            # until its typed return has reached its assigning parent.
            try:
                admitted_report(result, request)
            except ReportDeliveryError as error:
                source.feedback = error.feedback.as_record()
                await self.resolve_pending_deliveries(source, source._selection_view,
                    only_delivery_ref=source.feedback['delivery_ref'])
                admitted_report(result, request)
            value = credit(result, completion, request)
            original = self.journal.row('runtime_actions', source.episode_id, index)
            resolved_index = json.loads(original['result']).get('delivery_resolution_index')
            # Recovery consumes the saved communication within this original
            # acquisition, rather than replaying it as a new selected action.
            if resolved_index is not None:
                source.calls = max(source.calls, resolved_index + 1)
            return value
        def delivery_contract():
            action = self.journal.row('runtime_actions', source.episode_id, index)
            resolved_index = (None if action['result'] is None else
                json.loads(action['result']).get('delivery_resolution_index'))
            latest = self.store.db.execute('SELECT contract FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND '
                + ('decision_index=?' if resolved_index is not None else
                    'delivery_ref=? ORDER BY decision_index DESC LIMIT 1'),
                (self.run_id, source.episode_id, resolved_index if resolved_index is not None else
                    'delivery_' + _digest({'run': self.run_id, 'parent': source.episode_id,
                        'index': index})[:24])).fetchone()
            return contract if latest is None else self.saved_delivery_contract(
                child.source.episode_id, json.loads(latest['contract']))
        owned = self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
        def failed_child(error):
            outcome = {'status': 'failed', 'record_refs': [], 'changed_record_refs': [],
                'feedback': {'category': 'child_execution', 'exception_type': type(error).__name__}}
            from .communication import ReportBoundaryError
            if isinstance(error, ReportBoundaryError):
                outcome['feedback']['report_boundary'] = dict(error.diagnostic)
            self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': None})
            value = self.source_credit_view(source)['credit']
            self.journal.save('runtime_actions', {'episode_id': source.episode_id,
                'decision_index': index, 'action': _json(selection), 'result': _json(outcome), 'credit': value})
            source.last_outcome, source.last_outcome_index = outcome, index
            source.feedback = outcome['feedback']
            return self.controller_value(source, index, value)
        return TimedChildUnit(child, resolved_credit if owned else credit, report,
            self.journal, source.episode_id, index, scheduled=scheduled,
            delivery_contract=delivery_contract if owned else None, receive_failure=failed_child,
            allow_suspension=allow_suspension)

    @staticmethod
    def delivery_feedback(delivery_ref, error):
        diagnostic = error.diagnostic
        feedback = {"kind": "report_delivery_failure", "delivery_ref": delivery_ref,
                "reason": diagnostic["code"], "field": diagnostic.get("field")}
        if diagnostic["code"] == "literature_reaction_projection_version_mismatch":
            from .literature_reaction_storage import reaction_return_view_requirements
            feedback.update(reaction_return_view_requirements())
        return feedback

    def save_attempt(self, parent_id, index, delivery_ref, child_id, contract, *, form=None, failure=None,
                     report_contract_declaration=None):
        values = {"parent_episode_id": parent_id, "decision_index": index,
            "delivery_ref": delivery_ref, "child_episode_id": child_id,
            "contract": _json(contract.as_record()), "form": None if form is None else _json(form),
            "failure": None if failure is None else _json(failure),
            "report_contract_declaration": (None if report_contract_declaration is None
                                             else _json(report_contract_declaration))}
        old = self.store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND decision_index=?", (self.run_id, parent_id, index)).fetchone()
        if old is not None:
            if any(old[key] != value for key, value in values.items()):
                raise WorkflowError("reconstructed report delivery differs from its recorded attempt")
        else:
            self.journal.save("runtime_report_attempts", values)

    def delivery_status(self, parent_id):
        rows = self.store.db.execute("SELECT a.delivery_ref,a.failure,a.timing_receipts FROM runtime_report_attempts a "
            "WHERE a.run_id=? AND a.parent_episode_id=? AND a.decision_index=(SELECT MAX(b.decision_index) "
            "FROM runtime_report_attempts b WHERE b.run_id=a.run_id AND b.delivery_ref=a.delivery_ref) "
            "ORDER BY a.decision_index", (self.run_id, parent_id)).fetchall()
        return [{"delivery_ref": row["delivery_ref"], "status": "pending" if row["failure"] else "delivered",
                 **({'timing_receipt_issues': json.loads(row['timing_receipts'])['issues']}
                    if row['timing_receipts'] is not None and json.loads(row['timing_receipts'])['issues'] else {})}
                for row in rows]

    def saved_delivery_contract(self, child_id, saved):
        child = self.journal.row('runtime_episodes', child_id)
        request, path = json.loads(child['request']), json.loads(child['path'])
        scope, role = request['message']['scope'], path[-1][0]
        assignment = request['message'].get('job_assignment')
        context = BindingContext(self.run_id, child_id, role, path, scope,
            request['message'].get('episode_assignment', {}), request)
        schema = saved['measurements']['schema']
        contract = TypedReportContract(saved['decision'], schema,
            self.resolver(scope, assignment=assignment, grain=role, context=context),
            lambda value: self.validate_report(value, scope, assignment=assignment,
                grain=role, schema=schema, context=context))
        if contract.as_record() != saved:
            raise WorkflowError('recorded_delivery_contract_changed')
        return contract

    def redeliver(self, source, selection, index):
        prior = self.store.db.execute("SELECT * FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND delivery_ref=? ORDER BY decision_index LIMIT 1",
            (self.run_id, source.episode_id, selection["delivery_ref"])).fetchone()
        if prior is None:
            raise ValueError("unknown_report_delivery_for_parent")
        child_id = prior["child_episode_id"]
        child_row = self.journal.row("runtime_episodes", child_id)
        request = json.loads(child_row["request"])
        scope = request["message"]["scope"]
        role = json.loads(child_row["path"])[-1][0]
        assignment = request["message"].get("job_assignment")
        binding_context = BindingContext(self.run_id, child_id, role, json.loads(child_row['path']),
            scope, request['message'].get('episode_assignment', {}), request)
        schema, declaration = self.expanded_contract_form(source, selection, index, role, original_child=False)
        validator = lambda value: self.validate_report(value, scope, assignment=assignment, grain=role,
            schema=schema, context=binding_context)
        contract = TypedReportContract(selection["purpose"], schema,
            self.resolver(scope, assignment=assignment, grain=role, context=binding_context), validator)
        saved = self.journal.row("runtime_forms", child_id)
        facts = json.loads(saved["facts"])
        old_interpretations = facts.pop("interpretations")
        original_schema = request["report_contract"]["measurements"]["schema"]
        original_fields = interpretation_schema(original_schema)["properties"]
        try:
            requested = interpretation_schema(schema)["properties"]
            for name, node in requested.items():
                if name not in old_interpretations or node != original_fields.get(name):
                    raise ReportBoundaryError("Saved child interpretation does not answer the revised field",
                                              code="recorded_interpretation_unavailable", field=name)
            values = {name: old_interpretations[name] for name in requested}
            candidate = form_with_facts(values, schema, facts)
            admitted = contract.admit(candidate, audit_identifiers=(child_id, request["goal"]["goal_id"]))
        except ReportBoundaryError as error:
            feedback = self.delivery_feedback(selection["delivery_ref"], error)
            self.save_attempt(source.episode_id, index, selection["delivery_ref"], child_id,
                              contract, failure=feedback, report_contract_declaration=declaration)
            return ReportRedelivery(child_id, failure=Record(feedback))
        self.save_attempt(source.episode_id, index, selection["delivery_ref"], child_id,
                          contract, form=admitted.as_record(), report_contract_declaration=declaration)
        pending = self.pending_delivery(source, selection['delivery_ref'])
        if pending is not None and self.execution_binding is not None:
            original_index = pending['decision_index']
            row = self.store.db.execute('SELECT admission FROM runtime_return_admissions '
                'WHERE run_id=? AND parent_episode_id=? AND original_decision_index=?',
                (self.run_id, source.episode_id, original_index)).fetchone()
            if row is None:
                raise WorkflowError('pending_delivery_missing_original_admission')
            original = json.loads(row[0])
            spec = self.execution_backend.load_commission(original['handle'])
            returned = self.execution_backend.load_return(original['handle'], original['return_id'])
            original_request = self.returned_request(spec)
            receiver = ReceiverBindingV1(self.store, self.journal, original_index,
                original_request.report_contract, lambda form: None,
                lambda form: self.receive_form(source, form, schema, index, redelivery=True),
                lambda: self.source_credit_view(source)['credit'],
                lambda original_index, credit: self.controller_value(source, original_index, credit),
                defer_failed_delivery=True)
            resolve_return_delivery(spec, returned, receiver,
                repair_decision_index=index, delivery_contract=contract)
            action = self.journal.row('runtime_actions', source.episode_id, original_index)
            source.last_outcome, source.last_outcome_index = json.loads(action['result']), original_index
            source.feedback = None
        elif pending is not None or self.episode_branch_lifecycle != EPISODE_BRANCH_LIFECYCLE:
            self.receive_form(source, admitted.as_record(), schema, index, redelivery=True)
        else:
            from .episode_report_acquisition import acquire_report_evidence
            controller_input = acquire_report_evidence(self, source, selection, index,
                original_attempt=prior, admitted=admitted, schema=schema)
            if controller_input is not None:
                return ReportAcquisitionLeaf(selection, extract=lambda _: controller_input,
                    result=lambda _, value: value, label=f'redeliver_report:{index}',
                    decision_index=index, report_delivery=ReportRedelivery(child_id, report=admitted))
        return ReportRedelivery(child_id, report=admitted)

    def facts(self, source, *, completion_record=None):
        saved = self.journal.row("runtime_forms", source.episode_id)
        if saved is not None:
            facts = json.loads(saved["facts"])
            facts.pop("interpretations", None)
            # Archived forms remain immutable. Bindings may expose a separate
            # current view over the receiver's actual saved scientific sheets;
            # reading it must not require another interpretive/finalize action.
            facts.update(self.episode_bindings.current_report_facts(self.binding_context(source)))
            return facts
        with self.store.read_snapshot():
            def ordered_refs(field):
                # Project only references inside SQLite. Old source.read/tool
                # bodies stay on disk; neither rows nor a Python JSON decoder
                # materialize completed action payloads to close a small form.
                rows = self.store.db.execute("SELECT refs.value FROM runtime_actions actions "
                    "JOIN json_each(actions.result, ?) refs "
                    "WHERE actions.run_id=? AND actions.episode_id=? AND actions.result IS NOT NULL "
                    "ORDER BY actions.decision_index, refs.key",
                    ("$." + field, self.run_id, source.episode_id))
                return list(dict.fromkeys(row[0] for row in rows))
            committed = ordered_refs("record_refs")
            changed = ordered_refs("changed_record_refs")
            changed_types = {ref: self.store.get(ref)["record_type"] for ref in changed}
            last = (source.last_outcome or {}).get("record_refs", [])
            unseen = []
            for ref in last:
                if ref not in source.report_basis:
                    record = self.store.get(ref)
                    if record.get("record_type") == "observation":
                        unseen.append(ref)
            specialist = self.specialist(source)
            credit_snapshot = ({} if callable(getattr(specialist, '_closed_credit_facts', None)) else None)
            credit_view = (self.source_credit_view(source) if credit_snapshot is None else
                self.source_credit_view(source, binding_snapshot=credit_snapshot))
            facts = {"credit": credit_view["credit"], "subject_refs": source.scope["subject_refs"],
                "committed_record_refs": committed, "changed_record_refs": changed,
                "changed_annotation_refs": [ref for ref in changed if changed_types[ref] == "annotation"],
                "changed_assessment_refs": [ref for ref in changed if changed_types[ref] == "assessment"],
                "changed_interpretation_account_refs": [ref for ref in changed if changed_types[ref] == "interpretation_account"],
                "last_outcome_refs": last, "interpretation_basis_refs": source.report_basis,
                "observations_after_report_basis": unseen, "episode_yield": closing_yield(completion_record),
                'pending_handles': self.pending_handles(source)}
            if self.native_event_information is not None:
                facts.update(self.native_event_information.facts(self.binding_context(source)))
            if self.is_job_source(source):
                facts.update(self.job_episodes.facts(source, credit_view=credit_view))
            else:
                if self.project_annotation_score is not None:
                    annotation = self.annotation_context(source.scope, source=source)
                    for key in ('annotation_score', 'proposed_annotations', 'annotation_comparisons'):
                        if key in annotation:
                            facts[key] = annotation[key]
                if self.resource_estimator is not None:
                    facts['resource_tool_estimates'] = recorded_forecasts(self.store,
                        run_id=self.run_id, episode_id=source.episode_id)
            if self.native_timing_information is not None:
                native = self.native_timing_information.read_details(self.store, source.scope,
                    details_limit=None, details_offset=0, **self.native_timing_arguments(source))
                facts['monitoring_information_credit'] = credit_view['monitoring_information_credit']
                facts['native_execution_measurements'] = native['native_execution_measurements']
            snapshot = {
                'completion': (None if completion_record is None else
                    {'ended_by': completion_record.ended_by, 'end_reason': completion_record.end_reason,
                     'units_consumed': completion_record.units_consumed}),
                'own_action_count': (None if completion_record is None else completion_record.units_consumed),
                'last_outcome_refs': last, 'committed_record_refs': committed,
                'changed_record_refs': changed, 'report_basis_refs': source.report_basis}
            if specialist is not None:
                if credit_snapshot is not None:
                    snapshot['operational_credit_snapshot'] = credit_snapshot
                context = self.binding_context(source)
                if specialist is self.scientific_process_binding:
                    snapshot.update(
                        initial_credit=self.journal.row('runtime_episodes', source.episode_id)['initial_credit'],
                        credit=facts['credit'], controller_credit=self.source_controller_credit(source),
                        episode_yield=facts['episode_yield'],
                        parent_invocation_ref=self.services.scientific_parent_invocation(context))
                facts.update(specialist.facts(context, snapshot))
            received_facts = self.episode_bindings.received_report_facts(self.binding_context(source),
                completion_snapshot=snapshot)
            if set(received_facts).intersection(facts):
                raise ValueError('received_report_fact_conflict')
            facts.update(received_facts)
            return facts

    def build(self, name, key, goal_text, scope, *, parent=None, parent_path=(), contract=None, initial=None,
              job_assignment=None, episode_assignment=None, scientific_process=None,
              report_contract_declaration=None):
        path = (*parent_path, (name, key))
        goal = (EpisodeGoal.root(objective=goal_text, result_contract={"role": name}) if parent is None else
                EpisodeGoal.child(parent, objective=goal_text, result_contract=contract.schema))
        message = {"scope": scope, "initial_report": initial or {}}
        if self.inprocess_completion_order is not None:
            message['inprocess_completion_order'] = {'version': self.inprocess_completion_order}
        if report_contract_declaration is not None:
            if contract is None:
                raise ContractInformationError('report_contract_required_for_declaration')
            validate_saved_fact_form(child_role=name,
                submitted_schema_json=report_contract_declaration['submitted_schema_json'],
                expanded_schema=contract.schema, declaration=report_contract_declaration)
            message['report_contract_declaration'] = _plain(report_contract_declaration)
        if job_assignment is not None:
            message["job_assignment"] = job_assignment
        if episode_assignment is not None:
            # Root practical initialization can inspect a resource. Validate
            # the selected identities before initialization or any native work.
            self.launch_instructions.materialize(episode_assignment.get('launch_instructions'))
            message['episode_assignment'] = _plain(episode_assignment)
        if scientific_process is not None:
            message['scientific_process'] = _plain(scientific_process)
        identity = Episode.identity(self.context, self.grains[name], key, parent_path=parent_path)
        if self.scientific_process_binding is not None and name in {'annotation', 'scientific_process'}:
            from .scientific_process_records import scientific_invocation_ref
            message['scientific_invocation_ref'] = scientific_invocation_ref(self.run_id, path)
        if self.receipts is not None:
            parent_id = (Episode.identity(self.context, self.grains[parent_path[-1][0]],
                parent_path[-1][1], parent_path=parent_path[:-1]).episode_id if parent_path else None)
            message['knowledge_inheritance'] = self.receipts.bind(identity.episode_id, parent_id)
        request = EpisodeRequest(goal, Record(message), contract)
        source = DecisionSource(self, path, request, scope)
        self.contract_information_profile(source)
        if name == 'scientific_process':
            restored = self.scientific_process_binding.restore_closed_process(self.binding_context(source))
            if restored is not None:
                message['scientific_process'] = restored
                request = EpisodeRequest(goal, Record(message), contract)
                source = DecisionSource(self, path, request, scope)
        row = self.journal.row("runtime_episodes", identity.episode_id)
        restore_active = getattr(self.scientific_process_binding, 'restore_saved_process', None)
        if (name == 'scientific_process' and callable(restore_active)
                and row is not None and row['state'] == 'active'
                and row['completion'] is None and row['archive'] is None):
            restored = restore_active(
                self.binding_context(source), original_request=json.loads(row['request']))
            if restored is not None:
                message['scientific_process'] = restored
                request = EpisodeRequest(goal, Record(message), contract)
                source = DecisionSource(self, path, request, scope)
        if row is not None and json.loads(row['request']) != _plain(request.as_record()):
            raise WorkflowError('reconstructed immutable assignment differs')
        if name == 'scientific_process':
            self.scientific_process_binding.validate_context(self.binding_context(source))
        elif scientific_process is not None:
            raise ValueError('scientific_process_role_mismatch')
        specialist = self.specialist(source)
        initialize = getattr(specialist, 'initialize', None)
        if initialize is not None:
            initialize(self.binding_context(source))
        with self.store.transaction():
            if self.receipts is not None and not parent_path:
                self.receipts.receive(identity.episode_id,
                    [*scope['subject_refs'], *self.initial_known_record_refs], kind='initial')
            if self.receipts is not None and contract is not None and not self.is_job_source(source):
                initial_refs = _references_in({}, self.store.get,
                    forms=[(message['initial_report'], interpretation_schema(contract.schema))],
                    reference_subset=lambda refs: self.store.reference_subset(refs, scope))
                self.receipts.receive(identity.episode_id, initial_refs, kind='initial')
            if self.receipts is not None and not self.is_job_source(source):
                initial_refs = self.episode_bindings.initial_references(self.binding_context(source))
                self.receipts.receive(identity.episode_id, initial_refs, kind='initial')
            if row is None:
                self.journal.save("runtime_episodes", {"episode_id": identity.episode_id, "path": _json(path),
                    "request": _json(request.as_record()), "initial_credit": 0.,
                    "state": "active",
                    "completion": None, "archive": None})
                # Initial received science is graded at delivery, before its
                # inherited credit is fixed or any model can inspect credit.
                # Save the original request first to authenticate the callback.
                self.receive_tool_attributions(source, None, kind='initial')
                from .episode_journal import encode_credit
                self.store.db.execute('UPDATE runtime_episodes SET initial_credit=? WHERE run_id=? AND episode_id=?',
                    (encode_credit(self.source_credit_view(source)['credit']), self.run_id, identity.episode_id))
            if contract is not None and self.specialist(source) is not None:
                initial_schema = interpretation_schema(contract.schema)
                admitted = validate_form(message['initial_report'], initial_schema,
                    self.resolver(scope, source=source))
                self.validate_report(admitted, scope, grain=name, schema=initial_schema, source=source)
        self.expose_assigned_job(source)
        def on_unit(item, contribution, view):
            if view.episode_update is not None and view.episode_update.delivery_failures:
                source.feedback = view.episode_update.delivery_failures[-1].as_record()
            data = {"label": view.unit_label, "credit": _plain(view.controller_input),
                    "step": _plain(view.controller_step), "unit_ref": view.unit_ref.as_record(),
                    "decision_index": item.decision_index}
            if self.execution_binding is not None:
                self.completions.confirm_observed(identity.episode_id, view.unit_ref.unit_index, data)
                slot = self.completions.slot(identity.episode_id, view.unit_ref.unit_index)
                if slot['child_return'] is not None:
                    returned = slot['child_return']
                    self.execution_backend.acknowledge(returned['handle'], returned['return_id'],
                        returned['admission_id'])
                else:
                    action = self.journal.row('runtime_actions', identity.episode_id, item.decision_index)
                    outcome = json.loads(action['result'])
                    if (json.loads(action['action']).get('kind') in {'child', 'job_child', 'episode_child'}
                            and outcome.get('status') == 'failed' and outcome.get('execution_handle')):
                        spec = self.execution_backend.load_commission(outcome['execution_handle'])
                        self.execution_backend.acknowledge_failed_dispatch(outcome['execution_handle'],
                            parent_episode_id=identity.episode_id, operation_key=spec['operation_key'],
                            observation=data)
                self.publish_outcome(source, item.decision_index)
                return
            with (self.store.transaction() if self.inprocess_replay is not None else nullcontext()):
                old = self.journal.row("runtime_observations", identity.episode_id, view.unit_ref.unit_index)
                if old and json.loads(old["observation"]) != data:
                    raise WorkflowError("reconstructed controller observation differs")
                if not old:
                    self.journal.save("runtime_observations", {"episode_id": identity.episode_id,
                        "unit_index": view.unit_ref.unit_index, "observation": _json(data)})
                if self.inprocess_replay is not None:
                    self.inprocess_replay.capture(source)
                    source.checkpoint()
        def on_close(record):
            old = self.journal.row("runtime_episodes", identity.episode_id)
            if self.inprocess_replay is not None and old['state'] == 'yielded':
                if (json.loads(old['completion']) != {
                        'ended_by': record.ended_by, 'actions': record.units_consumed}
                        or json.loads(old['archive']) != self.archive.store(record).descriptor()):
                    raise WorkflowError('inprocess_closed_history_replay_differs')
                return
            if (self.episode_branch_lifecycle == EPISODE_BRANCH_LIFECYCLE
                    and old['state'] == 'active'):
                pending = self.store.db.execute('SELECT 1 FROM runtime_actions WHERE run_id=? '
                    'AND episode_id=? AND json_extract(action,\'$.kind\') IN '
                    '(\'child\',\'job_child\',\'episode_child\') '
                    'AND (result IS NULL OR json_extract(result,\'$.status\')=\'pending\') LIMIT 1',
                    (self.run_id, identity.episode_id)).fetchone()
                unobserved = self.store.db.execute('SELECT 1 FROM runtime_completion_slots s '
                    'LEFT JOIN runtime_observations o ON o.run_id=s.run_id AND o.episode_id=s.episode_id '
                    'AND o.unit_index=s.sequence WHERE s.run_id=? AND s.episode_id=? '
                    'AND o.unit_index IS NULL LIMIT 1', (self.run_id, identity.episode_id)).fetchone()
                unobserved_action = self.store.db.execute('SELECT 1 FROM runtime_actions a '
                    'WHERE a.run_id=? AND a.episode_id=? AND a.credit IS NOT NULL AND NOT EXISTS '
                    '(SELECT 1 FROM runtime_observations o WHERE o.run_id=a.run_id '
                    'AND o.episode_id=a.episode_id AND json_extract(o.observation,\'$.decision_index\')='
                    'a.decision_index) LIMIT 1', (self.run_id, identity.episode_id)).fetchone()
                if pending is not None or unobserved is not None or unobserved_action is not None:
                    raise WorkflowError('episode_cannot_close_with_unaccounted_owned_work')
            self.journal.save("runtime_episodes", {**{key: old[key] for key in
                ("episode_id", "path", "request", "initial_credit")}, "state": "yielded",
                "completion": _json({"ended_by": record.ended_by, "actions": record.units_consumed}),
                "archive": _json(self.archive.store(record).descriptor())})
        return FeedbackEpisode(self.grains[name], key, source, request, source.finish,
                               on_unit=on_unit, on_close=on_close, archive_record=self.archive.store)

    async def release(self, episode_id):
        callback = getattr(self.provider, "release", None)
        if callback:
            value = callback(episode_id)
            if inspect.isawaitable(value):
                await value


DEFAULT_GOAL = ("Improve the annotation and biological interpretation of the supplied material "
    "through evidence-linked, context-dependent reasoning. Retain competing explanations, "
    "investigate useful distinctions and revise actual annotation state.")


def _effective_restoration_configuration(provider_config=None, restoration_settings=None, *, base=None):
    """Caller-owned transport preview configuration, never a work budget."""
    if base is None:
        from .providers import default_config_path
        base = tomllib.loads(default_config_path().read_text())["restoration"]
    if not isinstance(base, Mapping):
        raise TypeError("restoration settings must be a mapping")
    effective = dict(base)
    supplied = {} if provider_config is None else provider_config
    configured = supplied.get("restoration", {})
    if not isinstance(configured, Mapping) or (restoration_settings is not None
            and not isinstance(restoration_settings, Mapping)):
        raise TypeError("restoration settings must be a mapping")
    effective.update(configured)
    if restoration_settings is not None:
        effective.update(restoration_settings)
    if set(effective) != {"preview_size"}:
        raise ValueError("restoration settings must declare only preview_size")
    if type(effective["preview_size"]) is not int or effective["preview_size"] < 0:
        raise ValueError("restoration preview_size must be a nonnegative integer")
    return effective


def _has_explicit_model_configuration(configuration):
    return "models" in configuration or any(key in configuration for key in
        ("FAST", "REASONING", "connection", "routing"))


def _effective_models(provider_config=None):
    from .providers import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    supplied = {} if provider_config is None else _plain(provider_config)
    if not isinstance(supplied, Mapping):
        raise TypeError("provider_config must be a mapping")
    models = supplied.get("models", supplied) if _has_explicit_model_configuration(supplied) else defaults["models"]
    for role in ("FAST", "REASONING"):
        if not isinstance(models.get(role), Mapping) or set(models[role]) != {"model", "reasoning_effort"}:
            raise ValueError(f"{role} must declare model and reasoning_effort")
    return _plain(models)


def _effective_configuration(provider_config=None, controller_settings=None):
    """Choose defaults once at the caller boundary, before an Episode exists."""
    from .providers import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    supplied = {} if provider_config is None else _plain(provider_config)
    models = _effective_models(provider_config)
    controller = dict(defaults["controller"])
    controller.update(supplied.get("controller", {}))
    if controller_settings is not None:
        controller.update(controller_settings)
    unknown = set(controller) - {"cost", "window_size", "subsample_size", "uncertainty_alpha"}
    if unknown:
        raise ValueError(f"unknown controller settings: {sorted(unknown)}")
    from .numerical import YieldParameters
    YieldParameters(**{key: value for key, value in controller.items() if key != "cost"})
    cost = controller["cost"]
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not 0 <= cost < float("inf"):
        raise ValueError("continuation cost must be finite and nonnegative")
    return _plain(models), controller


def _binding_name(callback, default):
    if callback is None:
        return default
    declared = callback if hasattr(callback, "__qualname__") else type(callback)
    return f"{declared.__module__}.{declared.__qualname__}"


def _credit_binding_from_settings(settings):
    """Expose the recorded score meaning without projecting state again."""
    versions = settings["binding_versions"]["credit"]
    binding = {"projector": settings["bindings"]["credit"], "versions": _plain(versions),
               "scope_source": "context.scope"}
    result = {**binding, "kind": "custom",
        "meaning": "Bound projector; its recorded definition declares the score, axes and denominator."}
    definition = settings.get("binding_definitions", {}).get("credit")
    if definition is not None:
        result["definition"] = _plain(definition)
    return result


def _run_location(store, run_dir, resume):
    if run_dir is None and resume:
        exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone()
        row = (store.db.execute("SELECT settings FROM runtime_runs ORDER BY started_at DESC,run_id DESC LIMIT 1").fetchone()
               if exists else None)
        if row is None:
            raise WorkflowError("no saved run exists to resume")
        run_dir = json.loads(row[0])["directory"]
    directory = Path(run_dir) if run_dir is not None else Path.cwd() / "runs" / uuid.uuid4().hex
    directory = directory.expanduser().resolve()
    marker = directory / "run.json"
    if resume:
        if not marker.is_file():
            raise WorkflowError("resume requires an existing run.json")
        manifest = parse_json_object(marker.read_text())
        return directory, manifest["run_id"]
    directory.mkdir(parents=True, exist_ok=True)
    if marker.exists():
        raise WorkflowError("run directory already contains a run; use resume")
    return directory, "run_" + uuid.uuid4().hex


def controller_from_settings(settings):
    """Restore the configured default controller without selecting new values."""
    from .numerical import YieldController
    control = settings.get('controller')
    if control is None:
        raise WorkflowError('original_caller_controller_factory_required')
    def factory(path, initial_credit):
        return YieldController(_digest(path), initial_credit, control['cost'],
            {key: value for key, value in control.items() if key != 'cost'})
    return factory


def assemble_workflow(store, tools, provider, directory, run_id, settings, *,
                      controller_factory, project_credit, project_child_credit=None,
                      project_annotation_score=None, job_episodes=None,
                      execution_expectations=None, resource_estimator=None,
                      native_timing_information=None, initial_known_record_refs=None,
                      episode_binding_factories=None, episode_binding_descriptors=None,
                      role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                      episode_service_factory=None, episode_service_binding=None,
                      episode_record_receipts=False, native_job_events=None,
                      episode_service_inputs=None, annotation_child_roles=None,
                      decision_protocol=_DEFAULT_DECISION_PROTOCOL):
    """Compose the same binding for a root or one independently placed child.

    Configuration validation belongs to the caller's recorded binding/factory.
    This function starts no episode, provider process, native job or controller.
    """
    bindings, versions = settings['bindings'], settings['binding_versions']
    saved_protocol = _decision_protocol(settings.get('decision_protocol'))
    if decision_protocol is _DEFAULT_DECISION_PROTOCOL:
        decision_protocol = saved_protocol
    elif _decision_protocol(decision_protocol) != saved_protocol:
        raise WorkflowError('resumption_requires_original_decision_protocol')
    annotation_child_roles = _annotation_child_roles(annotation_child_roles)
    if annotation_child_roles != _recorded_annotation_child_roles(settings):
        raise WorkflowError('resumption_requires_original_annotation_child_roles')
    saved_services = settings.get('episode_application_services')
    if (episode_service_inputs is not None or isinstance(saved_services, Mapping)
            and saved_services.get('version') == 'episode_application_services_v2') and service_binding(
            episode_service_factory, episode_service_binding, inputs=episode_service_inputs) != saved_services:
        raise WorkflowError('resumption_requires_original_episode_application_services')
    native_job_events = native_job_event_configuration(native_job_events)
    if settings.get('native_job_events') != native_job_events:
        raise WorkflowError('resumption_requires_original_native_job_events')
    if type(episode_record_receipts) is not bool:
        raise TypeError('episode_record_receipts_must_be_bool')
    expected_receipts = ({'version': 'explicit_store_record_receipts_v1', 'enabled': True}
                        if episode_record_receipts else None)
    if settings.get('episode_record_receipts') != expected_receipts:
        raise WorkflowError('resumption_requires_original_episode_record_receipts')
    wait_inputs_version = 'wait_inputs_binding_v1'
    if 'wait_inputs' in settings:
        recorded_wait_inputs = settings['wait_inputs']
        if recorded_wait_inputs not in ({'version': 'wait_inputs_binding_v1'},
                                        {'version': 'wait_inputs_binding_v2'}):
            raise WorkflowError('unsupported_wait_inputs_binding')
        wait_inputs_version = recorded_wait_inputs['version']
    completed_action_inputs_version = None
    if 'completed_action_inputs' in settings:
        recorded_completed_inputs = settings['completed_action_inputs']
        if recorded_completed_inputs != {'version': 'completed_action_inputs_binding_v1'}:
            raise WorkflowError('unsupported_completed_action_inputs_binding')
        completed_action_inputs_version = recorded_completed_inputs['version']
    episode_branch_lifecycle = None
    if 'episode_branch_lifecycle' in settings:
        if settings['episode_branch_lifecycle'] != {'version': EPISODE_BRANCH_LIFECYCLE}:
            raise WorkflowError('unsupported_episode_branch_lifecycle')
        episode_branch_lifecycle = EPISODE_BRANCH_LIFECYCLE
    return Workflow(store, tools, provider, directory, run_id, controller_factory, project_credit,
                        credit_binding=_credit_binding_from_settings(settings),
                        restoration_settings=settings["restoration"],
                        execution_expectations=execution_expectations, job_episodes=job_episodes,
                        resource_estimator=resource_estimator,
                        native_timing_information=native_timing_information,
                        initial_known_record_refs=initial_known_record_refs,
                        episode_binding_factories=episode_binding_factories,
                        episode_binding_descriptors=episode_binding_descriptors,
                        role_credit_bindings=role_credit_bindings,
                        job_progress_provider=job_progress_provider,
                        execution_binding=execution_binding,
                        episode_service_factory=episode_service_factory,
                        episode_service_binding=episode_service_binding,
                        episode_service_inputs=episode_service_inputs,
                        annotation_child_roles=annotation_child_roles,
                        decision_protocol=decision_protocol,
                        root_action_boundary=settings.get('root_action_boundary'),
                        episode_branch_lifecycle=episode_branch_lifecycle,
                        episode_record_receipts=episode_record_receipts,
                        native_job_events=native_job_events,
                        progress_receipt_order=settings.get('episode_progress_receipts', {}).get(
                            'version', 'legacy_grouped_v1'),
                        wait_inputs_version=wait_inputs_version,
                        completed_action_inputs_version=completed_action_inputs_version,
                        project_annotation_score=project_annotation_score,
                        annotation_score_binding=({'projector': bindings['annotation_score'],
                            'versions': versions['annotation_score'],
                            'definition': settings.get('binding_definitions', {}).get('annotation_score'),
                            'scope_source': 'context.scope',
                            'meaning': 'Annotation support, separately bound from investigation progress and numerical yield.'}
                            if project_annotation_score is not None else None),
                        project_child_credit=project_child_credit,
                        child_credit_binding=({"kind": "custom",
                            "projector": settings["bindings"]["scientific_child_credit"],
                            "versions": settings["binding_versions"]["scientific_child_credit"],
                            "definition": settings.get("binding_definitions", {}).get("scientific_child_credit"),
                            "scope_source": "context.scope", "assignment_source": "original_parent_commission",
                            "meaning": "Local scientific investigation credit; not an additive parent task score."}
                            if project_child_credit is not None else None),
                        controller_binding={"factory": settings["bindings"]["controller"],
                            "versions": settings["binding_versions"]["controller"],
                            "definition": (settings.get("binding_definitions", {}).get("controller")
                                if settings["controller"] is None else settings["controller"])})


async def run_workflow(store, tools, *, provider=None, provider_config=None,
                       run_dir=None, resume=False, controller_settings=None,
                       credit_policy=None, controller_factory=None, project_credit=None,
                       goal=None, restoration_settings=None, execution_expectations=None,
                       job_episodes=None, binding_definitions=None, project_child_credit=None,
                       resource_estimator=None, project_annotation_score=None,
                       initial_known_record_refs=None, native_timing_information=None,
                       episode_binding_factories=None, episode_binding_descriptors=None,
                       role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                       episode_service_factory=None, episode_service_binding=None,
                       episode_record_receipts=False, native_job_events=None,
                       episode_service_inputs=None, annotation_child_roles=None,
                       decision_protocol=_DEFAULT_DECISION_PROTOCOL):
    """Bind standard scientific channels or execute the caller's explicit policy.

    Standard continuation uses received investigation progress. Annotation
    scoring requires a separate explicit numerical projector; the retired
    categorical credit_policy configuration is not an annotation scorer.
    Both routes execute the same shared runtime below.
    """
    options = dict(provider=provider, provider_config=provider_config, run_dir=run_dir,
        resume=resume, controller_settings=controller_settings, credit_policy=credit_policy,
        controller_factory=controller_factory, project_credit=project_credit, goal=goal,
        restoration_settings=restoration_settings, execution_expectations=execution_expectations,
        job_episodes=job_episodes, binding_definitions=binding_definitions,
        project_child_credit=project_child_credit, resource_estimator=resource_estimator,
        project_annotation_score=project_annotation_score,
        initial_known_record_refs=initial_known_record_refs,
        native_timing_information=native_timing_information,
        episode_binding_factories=episode_binding_factories,
        episode_binding_descriptors=episode_binding_descriptors,
        role_credit_bindings=role_credit_bindings, job_progress_provider=job_progress_provider,
        execution_binding=execution_binding,
        episode_record_receipts=episode_record_receipts,
        native_job_events=native_job_events,
        episode_service_factory=episode_service_factory, episode_service_binding=episode_service_binding,
        episode_service_inputs=episode_service_inputs, annotation_child_roles=annotation_child_roles,
        decision_protocol=decision_protocol)
    if project_credit is None:
        from .default_scientific_binding import bind_default_science
        options.update(bind_default_science(store, run_dir=run_dir, resume=resume,
            provider_config=provider_config, credit_policy=credit_policy,
            initial_known_record_refs=initial_known_record_refs,
            project_child_credit=project_child_credit,
            project_annotation_score=project_annotation_score,
            binding_definitions=binding_definitions))
    return await _run_bound_workflow(store, tools, **options)


async def _run_bound_workflow(store, tools, *, provider=None, provider_config=None,
                       run_dir=None, resume=False, controller_settings=None,
                       credit_policy=None, controller_factory=None, project_credit=None,
                       goal=None, restoration_settings=None, execution_expectations=None,
                       job_episodes=None, binding_definitions=None, project_child_credit=None,
                       resource_estimator=None, project_annotation_score=None,
                       initial_known_record_refs=None, native_timing_information=None,
                       episode_binding_factories=None, episode_binding_descriptors=None,
                       role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                       episode_service_factory=None, episode_service_binding=None,
                       episode_record_receipts=False, native_job_events=None,
                       episode_service_inputs=None, annotation_child_roles=None,
                       decision_protocol=_DEFAULT_DECISION_PROTOCOL):
    """Run or reconstruct one durable method_loop investigation.

    Resumption replays saved selections and committed results through the same
    generic Episode tree. Work with an operation key is recovered idempotently
    if publication preceded the runtime response journal. Controller histories
    are reconstructed from those original cumulative scores, never from a
    freshly remeasured score for historical work.
    """
    if not callable(project_credit):
        raise TypeError('runtime_requires_bound_credit_projector')
    if type(episode_record_receipts) is not bool:
        raise TypeError('episode_record_receipts_must_be_bool')
    requested_receipts = ({'version': 'explicit_store_record_receipts_v1', 'enabled': True}
                          if episode_record_receipts else None)
    requested_native_events = native_job_event_configuration(native_job_events)
    if requested_native_events is not None and job_episodes is None:
        raise ValueError('native_job_events_requires_job_binding')
    annotation_child_roles = _annotation_child_roles(annotation_child_roles)
    requested_services = service_binding(episode_service_factory, episode_service_binding,
        inputs=episode_service_inputs)
    if requested_services is not None and any(value is not None for value in
            (episode_binding_factories, episode_binding_descriptors, role_credit_bindings, job_progress_provider)):
        raise ValueError('episode_service_factory_and_direct_services_are_exclusive')
    if episode_binding_descriptors is not None and episode_binding_factories is not None:
        raise ValueError('episode_descriptors_and_factories_are_exclusive')
    from .numerical import YieldController, ESTIMATOR_VERSION, SOURCE_SHA256
    from .providers import ModelConnection

    directory, run_id = _run_location(store, run_dir, resume)
    journal = Journal(store, run_id)
    old = journal.row("runtime_runs")
    if decision_protocol is _DEFAULT_DECISION_PROTOCOL:
        decision_protocol = (json.loads(old['settings']).get('decision_protocol') if old else
            DECISION_EXCHANGE_PROTOCOL if provider is None or isinstance(provider, ModelConnection) else None)
    decision_protocol = _decision_protocol(decision_protocol)
    if old and decision_protocol != json.loads(old['settings']).get('decision_protocol'):
        raise WorkflowError('resumption_requires_original_decision_protocol')
    if native_timing_information is not None and type(native_timing_information) is not NativeTimingInformation:
        raise TypeError('typed_native_timing_information_required')
    saved_native_information = (json.loads(old['settings']).get('native_timing_information') if old else None)
    if old and json.loads(old['settings']).get('episode_record_receipts') != requested_receipts:
        raise WorkflowError('resumption_requires_original_episode_record_receipts')
    if old and json.loads(old['settings']).get('native_job_events') != requested_native_events:
        raise WorkflowError('resumption_requires_original_native_job_events')
    uses_receipts = (episode_record_receipts or native_timing_information is not None or saved_native_information is not None or any(
        getattr(projector, 'requires_episode_receipts', False) for projector in (project_credit, project_child_credit)))
    if initial_known_record_refs is not None:
        if (not uses_receipts or not isinstance(initial_known_record_refs, (list, tuple))
                or not all(isinstance(ref, str) for ref in initial_known_record_refs)):
            raise ValueError('explicit_initial_known_record_references_require_receipt_binding')
        initial_known_record_refs = sorted(set(initial_known_record_refs))
        for reference in initial_known_record_refs:
            store.get(reference)
    if provider_config is not None and not isinstance(provider_config, Mapping):
        raise TypeError("provider_config must be a mapping")
    configured_controller = ({} if provider_config is None else provider_config).get("controller", {})
    if controller_factory is not None and (controller_settings is not None or configured_controller):
        raise ValueError("custom_controller_owns_its_configuration_use_binding_definitions")
    configured_credit = ({} if provider_config is None else provider_config).get("credit")
    if project_credit is not None and (credit_policy is not None or configured_credit is not None):
        raise ValueError("custom_projector_owns_its_configuration_use_binding_definitions")
    if project_child_credit is not None and not callable(project_child_credit):
        raise TypeError("scientific_child_credit_projector_must_be_callable")
    if project_annotation_score is not None and not callable(project_annotation_score):
        raise TypeError("annotation_score_projector_must_be_callable")
    if binding_definitions is not None:
        binding_definitions = _plain(binding_definitions)
        if not isinstance(binding_definitions, dict) or set(binding_definitions) - {"credit", "controller", "scientific_child_credit", "annotation_score"}:
            raise ValueError("invalid_custom_binding_definitions")
        if any(not isinstance(value, dict) or not value for value in binding_definitions.values()):
            raise ValueError("nonempty_binding_definition_required")
        if ("credit" in binding_definitions and project_credit is None or
                "controller" in binding_definitions and controller_factory is None or
                "scientific_child_credit" in binding_definitions and project_child_credit is None or
                "annotation_score" in binding_definitions and project_annotation_score is None):
            raise ValueError("binding_definition_requires_its_custom_executable")
        binding_definitions = json.loads(_json(binding_definitions))
    if job_episodes is not None:
        from .homology_episodes import HomologyEpisodes
        if type(job_episodes) is not HomologyEpisodes:
            raise TypeError("typed_homology_episode_binding_required")
        if controller_factory is None or project_credit is None:
            raise ValueError("job_episode_run_requires_explicit_controller_and_task_credit_bindings")
    if execution_expectations is not None and type(execution_expectations) is not ExecutionExpectations:
        raise TypeError("typed_execution_expectation_binding_required")
    if resource_estimator is not None and type(resource_estimator) is not ResourceToolEstimator:
        raise TypeError("typed_resource_tool_estimator_required")
    problem = _plain(store.problem())
    tool_resources = _plain(tools.resource_binding()) if callable(getattr(tools, "resource_binding", None)) else {}
    bindings = {"controller": _binding_name(controller_factory, "gene_annotation_episode.numerical.YieldController"),
                "credit": _binding_name(project_credit, "caller_injected")}
    versions = {
        "controller": ({"estimator_version": ESTIMATOR_VERSION, "template_sha256": SOURCE_SHA256}
                       if controller_factory is None else {"requirement": "same_caller_injected_executable"}),
        "credit": {"requirement": "same_caller_injected_executable"},
    }
    if project_child_credit is not None:
        bindings["scientific_child_credit"] = _binding_name(project_child_credit, "caller_injected")
        versions["scientific_child_credit"] = {"requirement": "same_caller_injected_executable"}
    if project_annotation_score is not None:
        bindings['annotation_score'] = _binding_name(project_annotation_score, 'caller_injected')
        versions['annotation_score'] = {'requirement': 'same_caller_injected_executable'}
    if resume:
        if old is None:
            raise WorkflowError("run manifest is not registered in this Store")
        settings = json.loads(old["settings"])
        if annotation_child_roles != _recorded_annotation_child_roles(settings):
            raise WorkflowError('resumption_requires_original_annotation_child_roles')
        if requested_services != settings.get('episode_application_services'):
            raise WorkflowError('resumption_requires_original_episode_application_services')
        if (native_timing_information is not None
                and native_timing_information.as_record() != settings.get('native_timing_information')):
            raise WorkflowError('resumption_cannot_replace_native_timing_information')
        native_timing_information = (NativeTimingInformation.from_record(settings['native_timing_information'])
            if settings.get('native_timing_information') is not None else None)
        saved_knowledge = settings.get('scientific_knowledge')
        if uses_receipts:
            if saved_knowledge is None or saved_knowledge['version'] != RECEIPT_VERSION:
                raise WorkflowError('resumption_requires_original_scientific_receipt_binding')
            if (initial_known_record_refs is not None
                    and initial_known_record_refs != saved_knowledge['initial_known_record_refs']):
                raise WorkflowError('resumption_cannot_change_initial_scientific_knowledge')
            initial_known_record_refs = saved_knowledge['initial_known_record_refs']
        elif saved_knowledge is not None:
            raise WorkflowError('resumption_cannot_remove_scientific_receipt_binding')
        if binding_definitions is not None and binding_definitions != settings.get("binding_definitions", {}):
            raise WorkflowError("resumption cannot replace the run's custom binding definitions")
        saved_jobs = settings.get("job_episodes")
        if (None if job_episodes is None else job_episodes.as_record()) != saved_jobs:
            raise WorkflowError("resumption requires the original job episode resources and scoring binding")
        saved_expectations = settings.get("execution_expectations")
        if execution_expectations is not None and execution_expectations.as_record() != saved_expectations:
            raise WorkflowError("resumption cannot replace the run's execution expectation binding")
        execution_expectations = (ExecutionExpectations.from_record(saved_expectations)
                                  if saved_expectations is not None else None)
        saved_resource_estimator = settings.get("resource_tool_estimator")
        if resource_estimator is not None and resource_estimator.as_record() != saved_resource_estimator:
            raise WorkflowError("resumption cannot replace the run's resource/tool estimator")
        resource_estimator = (ResourceToolEstimator.from_record(saved_resource_estimator)
                              if saved_resource_estimator is not None else None)
        if settings["problem"] != problem or settings["directory"] != str(directory):
            raise WorkflowError("saved run belongs to different immutable material or directory")
        if settings["bindings"] != bindings:
            raise WorkflowError("resumption requires the same controller and credit bindings")
        if settings["binding_versions"] != versions:
            raise WorkflowError("saved scientific score or estimator version differs; history cannot be mixed")
        if "restoration" not in settings:
            raise WorkflowError("saved run requires its original restoration binding and code snapshot")
        _effective_restoration_configuration(base=settings["restoration"])
        if restoration_settings is not None or (provider_config is not None and "restoration" in provider_config):
            requested = _effective_restoration_configuration(provider_config, restoration_settings,
                                                               base=settings["restoration"])
            if requested != settings["restoration"]:
                raise WorkflowError("resumption cannot replace the run's restoration settings")
        if provider_config is not None or controller_settings is not None:
            supplied = {} if provider_config is None else provider_config
            requested_controller = (None if controller_factory is not None else
                {**settings["controller"], **supplied.get("controller", {}),
                 **({} if controller_settings is None else controller_settings)})
            requested_config = settings["models"] if provider_config is None else provider_config
            if provider_config is not None and not _has_explicit_model_configuration(supplied):
                requested_config = {**supplied, "models": settings["models"]}
            if controller_factory is None:
                models, controller = _effective_configuration(requested_config, requested_controller)
            else:
                models, controller = _effective_models(requested_config), None
            if provider_config is not None and models != settings["models"]:
                raise WorkflowError("resumption cannot replace the run's model settings")
            if controller != settings["controller"]:
                raise WorkflowError("resumption cannot replace the run's controller settings")
        if goal is not None and goal != settings["goal"]:
            raise WorkflowError("resumption cannot replace the run's immutable goal")
        if old["state"] in ('yielded', 'yielded_with_pending_work') and old["summary"] is not None:
            # Resuming an already yielded run is inspection, not a new epoch.
            # Its historical score must not be rewritten from a later run's
            # modifications to the same scientific Store.
            return json.loads(old["summary"])
    else:
        if uses_receipts and initial_known_record_refs is None:
            raise ValueError('receipt_binding_requires_explicit_initial_known_record_refs')
        if controller_factory is None:
            models, controller = _effective_configuration(provider_config, controller_settings)
        else:
            models, controller = _effective_models(provider_config), None
        settings = {"schema_version": 1, "directory": str(directory), "problem": problem,
                    "models": models, "controller": controller,
                    "credit_policy": None,
                    "goal": DEFAULT_GOAL if goal is None else goal, "bindings": bindings,
                    "binding_versions": versions,
                    "initial_tool_resources": tool_resources,
                    "restoration": _effective_restoration_configuration(provider_config, restoration_settings)}
        settings['episode_progress_receipts'] = {'version': 'received_progress_order_v1'}
        settings['root_action_boundary'] = ROOT_BOUNDARY_VERSION
        settings['wait_inputs'] = {'version': 'wait_inputs_binding_v2'}
        settings['completed_action_inputs'] = {'version': 'completed_action_inputs_binding_v1'}
        settings['episode_branch_lifecycle'] = {'version': EPISODE_BRANCH_LIFECYCLE}
        if decision_protocol is not None:
            settings['decision_protocol'] = decision_protocol
        if requested_services is not None:
            settings['episode_application_services'] = requested_services
        if annotation_child_roles is not None:
            settings['annotation_child_roles'] = list(annotation_child_roles)
        if requested_receipts is not None:
            settings['episode_record_receipts'] = requested_receipts
        if requested_native_events is not None:
            settings['native_job_events'] = requested_native_events
        if binding_definitions is not None:
            settings["binding_definitions"] = binding_definitions
        if uses_receipts:
            settings['scientific_knowledge'] = {'version': RECEIPT_VERSION,
                'initial_known_record_refs': initial_known_record_refs}
        if execution_expectations is not None:
            settings["execution_expectations"] = execution_expectations.as_record()
        if resource_estimator is not None:
            settings["resource_tool_estimator"] = resource_estimator.as_record()
        if native_timing_information is not None:
            settings['native_timing_information'] = native_timing_information.as_record()
        if job_episodes is not None:
            settings["job_episodes"] = job_episodes.as_record()
        journal.save("runtime_runs", {"settings": _json(settings), "state": "created",
            "summary": None, "started_at": _now(), "updated_at": _now()})
        (directory / "run.json").write_text(_json({"run_id": run_id, **settings}) + "\n")

    if controller_factory is None:
        controller_factory = controller_from_settings(settings)

    # Validate against the actual registered roles during Workflow assembly,
    # including caller-constructed scientific processes. Assembly precedes
    # opening the provider transport below.
    owned_provider = provider is None
    if owned_provider:
        # Each resumption gets a separate transport audit directory. Scientific
        # action identities and the authoritative state remain the same.
        transports = directory / "providers"
        transports.mkdir(exist_ok=True)
        provider = ModelConnection(settings["models"], transports / uuid.uuid4().hex, directory,
            image_resolver=getattr(tools, "resolve_image_input", None))
    recover_service_publication = (resume and requested_services is not None
        and 'episode_bindings' not in settings and old['state'] == 'created'
        and old['summary'] is None and store.db.execute(
            'SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None)
    if resume and 'episode_bindings' not in settings:
        if not recover_service_publication and (episode_binding_factories is not None or episode_binding_descriptors is not None
                or episode_service_factory is not None):
            raise WorkflowError('resumption_cannot_add_episode_bindings')
        if not recover_service_publication:
            episode_binding_factories = ()
    elif resume and episode_binding_factories is None and episode_service_factory is None:
        saved_descriptors = settings['episode_bindings']
        if episode_binding_descriptors is not None and _plain(episode_binding_descriptors) != saved_descriptors:
            raise WorkflowError('resumption_requires_original_episode_bindings')
        episode_binding_descriptors = saved_descriptors
    workflow = assemble_workflow(store, tools, provider, directory, run_id, settings,
        controller_factory=controller_factory, project_credit=project_credit,
        project_child_credit=project_child_credit, project_annotation_score=project_annotation_score,
        job_episodes=job_episodes, execution_expectations=execution_expectations,
        resource_estimator=resource_estimator, native_timing_information=native_timing_information,
        initial_known_record_refs=initial_known_record_refs,
        episode_binding_factories=episode_binding_factories,
        episode_binding_descriptors=episode_binding_descriptors,
        role_credit_bindings=role_credit_bindings, job_progress_provider=job_progress_provider,
        episode_record_receipts=episode_record_receipts,
        native_job_events=requested_native_events,
        episode_service_factory=episode_service_factory, episode_service_binding=episode_service_binding,
        episode_service_inputs=episode_service_inputs, annotation_child_roles=annotation_child_roles,
        decision_protocol=decision_protocol)
    selected_bindings = workflow.episode_bindings.as_record()
    selected_role_bindings = {role: {'definition': _plain(definition),
        'projector': _binding_name(workflow.role_credit_projectors[role], 'caller_injected')}
        for role, definition in workflow.role_credit_definitions.items()}
    if resume and not recover_service_publication:
        if selected_bindings != settings.get('episode_bindings', []):
            raise WorkflowError('resumption_requires_original_episode_bindings')
        if selected_role_bindings != settings.get('episode_role_credit_bindings', {}):
            raise WorkflowError('resumption_requires_original_episode_role_credit_bindings')
        if (requested_services is not None and workflow.episode_job_progress_provider_binding
                != settings.get('episode_job_progress_provider')):
            raise WorkflowError('resumption_requires_original_episode_job_progress_provider')
    else:
        settings['episode_bindings'] = selected_bindings
        if selected_role_bindings:
            settings['episode_role_credit_bindings'] = selected_role_bindings
        if requested_services is not None:
            settings['episode_job_progress_provider'] = workflow.episode_job_progress_provider_binding
        previous = journal.row('runtime_runs')
        journal.save('runtime_runs', {'settings': _json(settings), 'state': previous['state'],
            'summary': previous['summary'], 'started_at': previous['started_at'],
            'updated_at': previous['updated_at']})
        (directory / 'run.json').write_text(_json({'run_id': run_id, **settings}) + '\n')
    from .application_execution_binding import bind_episode_execution
    # A model connection supplies decisions, not permission to place each
    # Episode in an independent worker. Ordinary children use the calling
    # process; separate placement requires the caller's execution binding.
    execution = bind_episode_execution(store, directory, settings=settings,
        requested_binding=execution_binding,
        use_saved_runtime=False,
        tool_configuration=getattr(tools, 'reconstruction_configuration', None), resume=resume)
    settings = execution.settings
    workflow.configure_execution(execution.runtime_binding)
    if owned_provider:
        await provider.__aenter__()
    scope = store.validate_scope({"subject_refs": problem["subject_refs"]})
    root = workflow.build("annotation", "root", settings["goal"], scope)
    def save_state(state, summary=None):
        prior = journal.row("runtime_runs")
        journal.save("runtime_runs", {"settings": prior["settings"], "state": state,
            "summary": None if summary is None else _json(summary),
            "started_at": prior["started_at"], "updated_at": _now()})
    save_state("running")
    try:
        record = await root.run_async(workflow.context)
        await root.build_result(record)
        final_credit_view = workflow.source_credit_view(root.source)
        pending_handles = workflow.pending_handles(root.source)
        if pending_handles:
            raise WorkflowError('workflow_cannot_finalize_with_unaccounted_owned_work')
        closed_state = 'yielded'
        summary = {"run_id": run_id, "directory": str(directory), "state": closed_state,
            'pending_handles': pending_handles,
            "ended_by": record.ended_by, "scientific_completion": "not_established_by_termination",
            "completed_actions": record.units_consumed, "credit": final_credit_view['credit'],
            "episode_count": store.db.execute("SELECT COUNT(*) FROM runtime_episodes WHERE run_id=?", (run_id,)).fetchone()[0],
            "pending_report_deliveries": store.db.execute("SELECT COUNT(*) FROM runtime_report_attempts a "
                "WHERE a.run_id=? AND a.failure IS NOT NULL AND a.decision_index=(SELECT MAX(b.decision_index) "
                "FROM runtime_report_attempts b WHERE b.run_id=a.run_id AND b.delivery_ref=a.delivery_ref)", (run_id,)).fetchone()[0]}
        if 'monitoring_information_credit' in final_credit_view:
            summary.update({key: final_credit_view[key] for key in
                ('monitoring_information_credit', 'monitoring_information_binding')})
        if project_annotation_score is not None:
            annotation = workflow.annotation_context(scope, source=root.source)
            for key in ('annotation_score', 'annotation_support', 'annotation_opposition',
                        'proposed_annotations', 'annotation_comparisons'):
                if key in annotation:
                    summary[key] = annotation[key]
        else:
            summary['annotation_score_status'] = 'unavailable_no_scorer_bound'
        save_state(closed_state, summary)
        (directory / "summary.json").write_text(_json(summary) + "\n")
        return summary
    except BaseException as error:
        state = "interrupted" if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else "operational_failure"
        save_state(state, {"error_type": type(error).__name__, "detail": str(error)})
        raise
    finally:
        # Retire every process/conversation including suspended parents when
        # an interruption unwinds the generic tree. Journals stay on disk.
        ids = [row[0] for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=?", (run_id,))]
        for episode_id in ids:
            await workflow.release(episode_id)
        if owned_provider:
            await provider.__aexit__(None, None, None)
