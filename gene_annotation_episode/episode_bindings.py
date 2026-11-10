"""Application ports for composing specializations of the shared Episode loop.

Bindings describe available work and project actual outcomes. They neither call
the model nor implement an investigation loop. See docs/IMPLEMENTATION_PLAN.md
C7 for the persisted handoffs and the separation from runtime episode nesting.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def native_job_event_configuration(value):
    """Copy an explicit caller notification binding; infer no resource."""
    if value is None:
        return None
    if (not isinstance(value, Mapping) or set(value) != {'version', 'resource_id'}
            or value['version'] != 'native_job_events_v1'
            or not isinstance(value['resource_id'], str) or not value['resource_id'].strip()):
        raise ValueError('invalid_native_job_events_binding')
    return json.loads(json.dumps(_plain(value), allow_nan=False))


def reference_in_context(services, context, reference, namespace):
    """Use contextual visibility without recursing through a binding resolver."""
    callback = getattr(services, 'reference_in_context', None)
    if callback is not None:
        return callback(context, reference, namespace)
    return services.reference_in_scope(reference, context.scope, namespace)


@dataclass(frozen=True)
class BindingContext:
    """Immutable identity/assignment view; no Workflow, source or child trace."""

    run_id: str
    episode_id: str
    role: str
    path: tuple[tuple[str, str], ...]
    scope: Mapping[str, Any]
    assignment: Mapping[str, Any]
    request: Mapping[str, Any]
    received_record_refs: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ('run_id', 'episode_id', 'role'):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f'nonempty_{name}_required')
        path = tuple(tuple(part) for part in self.path)
        if (not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                for item in part) for part in path) or path[-1][0] != self.role):
            raise ValueError('binding_context_path_must_match_role')
        object.__setattr__(self, 'path', path)
        if (not isinstance(self.received_record_refs, (tuple, list))
                or any(not isinstance(ref, str) or not ref for ref in self.received_record_refs)):
            raise ValueError('received_record_refs_must_be_explicit_references')
        object.__setattr__(self, 'received_record_refs', tuple(self.received_record_refs))
        for name in ('scope', 'assignment', 'request'):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise TypeError(f'{name}_must_be_mapping')
            # Preserve JSON values while preventing bindings from changing the
            # original assignment through a borrowed mutable dictionary.
            normalized = json.loads(json.dumps(_plain(value), allow_nan=False))
            object.__setattr__(self, name, _freeze(normalized))

    def as_record(self):
        return {name: _plain(getattr(self, name)) for name in
                ('run_id', 'episode_id', 'role', 'path', 'scope', 'assignment', 'request')}


def native_observation_options(native_operation, observation_context):
    """Forward an explicit native choice with its internal selecting context.

    Omission preserves the old call and persisted-selection shapes. This is
    not custody authentication; the actual execution owner verifies the saved
    selection and original assignment before acquiring anything.
    """
    from .domain import ContractError
    if native_operation is None:
        if observation_context is not None:
            raise ContractError('progress_observation_context_requires_native_operation')
        return {}
    if not isinstance(native_operation, str) or not native_operation:
        raise ContractError('progress_native_operation_invalid')
    if not isinstance(observation_context, BindingContext):
        raise ContractError('progress_observation_context_required')
    return {'native_operation': native_operation, 'observation_context': observation_context}


@runtime_checkable
class EpisodeServices(Protocol):
    def tool_catalog(self, scope): ...
    def tool_information_catalog(self, scope): ...
    async def execute_tool(self, name, arguments, *, scope, operation_key,
                           permitted_record_refs=None): ...
    def authenticate_structure_alignment_operands(self, context: BindingContext,
                                                 arguments: dict) -> dict: ...
    def authenticate_source_byte_operands(self, context: BindingContext,
                                         tool_name: str, arguments: dict) -> None: ...
    def read_record(self, reference): ...
    def reference_in_scope(self, reference, scope, namespace): ...
    def reference_in_context(self, context, reference, namespace): ...
    def scientific_credit(self, context, receiver_selection): ...
    def scientific_support_routes(self, context, *, observation_kinds): ...
    def bound_role_credit(self, context, receiver_selection): ...
    def capabilities(self): ...
    def observe_progress(self, target_handle, requested_fields, scope, *,
                         permitted_committed_record_types=(), operation_key=None,
                         native_operation=None, observation_context=None): ...
    def describe_progress_target(self, target_handle, scope): ...
    def read_progress(self, reference, scope): ...
    def received_progress_refs(self, episode_id): ...
    def progress_selection(self, context): ...
    def record_selection(self, context): ...
    def scientific_preparation(self, context, preparation_ref, *, owner='self'): ...
    def scientific_received_results(self, context): ...
    def scientific_frozen_results(self, context): ...
    def alignment_site_own_action_results(self, context, *, source, selection,
                                         after_decision_index, limit): ...
    def alignment_site_frozen_facts(self, context, *, sources): ...
    def scientific_parent_invocation(self, context): ...
    def scientific_reference(self, context, reference, namespace): ...
    def dependencies(self, target_handle, scope): ...
    def own_outcomes(self, episode_id, *, tools, offset, limit): ...


@runtime_checkable
class EpisodeBinding(Protocol):
    roles: tuple[str, ...]
    entry_roles: tuple[str, ...]

    def child_roles(self, role): ...
    def as_record(self): ...
    def credit_kind(self, role): ...
    def assignment_schema(self, role): ...
    def permitted_common_actions(self, context): ...
    def allowed_children(self, parent, caller_capabilities): ...
    def prepare_assignment(self, parent, role, selection, scope, operation_key): ...
    def instructions(self, context): ...
    def decision_context(self, context, current_view): ...
    def catalog(self, context): ...
    def execute(self, context, tool_name, arguments, operation_key): ...
    def fact_sources(self, role): ...
    def facts(self, context, completion_snapshot): ...
    def resolve(self, context, reference, namespace): ...
    def validate_report(self, context, form, original_schema): ...
    def credit_view(self, context, receiver_selection): ...


class EpisodeBindingRegistry:
    """Address explicitly supplied bindings; never instantiate child episodes."""

    def __init__(self, bindings=()):
        self._by_role = {}
        self._bindings = []
        for binding in bindings:
            self.register(binding)

    def register(self, binding):
        if not isinstance(binding, EpisodeBinding):
            raise TypeError('complete_episode_binding_required')
        roles = binding.roles
        if (not isinstance(roles, tuple) or not roles or len(set(roles)) != len(roles)
                or any(not isinstance(role, str) or not role for role in roles)):
            raise ValueError('unique_nonempty_episode_roles_required')
        conflicts = set(roles).intersection(self._by_role)
        if conflicts:
            raise ValueError('duplicate_episode_role:' + ','.join(sorted(conflicts)))
        for role in roles:
            if binding.credit_kind(role) not in {'scientific', 'operational', 'monitoring'}:
                raise ValueError('declared_credit_kind_required:' + role)
        if (not isinstance(binding.entry_roles, tuple)
                or not set(binding.entry_roles) <= set(roles)):
            raise ValueError('entry_roles_must_be_declared_roles')
        # A recorded definition must be serializable; executable configuration
        # belongs to the caller's reconstruction factory, not this descriptor.
        json.dumps(binding.as_record(), allow_nan=False)
        self._bindings.append(binding)
        self._by_role.update({role: binding for role in roles})

    @property
    def roles(self):
        return tuple(self._by_role)

    def initial_decision_context(self, context):
        """Already recorded caller information before an episode's first choice."""
        supplied = {}
        for binding in self._bindings:
            callback = getattr(binding, 'initial_decision_context', None)
            if callback is None:
                continue
            value = callback(context)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('initial_binding_context_field_conflict')
            supplied.update(_plain(value))
        return supplied

    def annotation_axis_yield_context(self, context, credit):
        """Owner-declared unresolved work for the annotation root's local fit."""
        supplied = {}
        for binding in self._bindings:
            callback = getattr(binding, 'annotation_axis_yield_context', None)
            if callback is None:
                continue
            value = callback(context, credit)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('annotation_axis_yield_context_conflict')
            supplied.update(_plain(value))
        return supplied

    def contract_information_configurations(self):
        """Read explicit bound configuration before any provider is entered."""
        profiles = []
        for binding in self._bindings:
            callback = getattr(binding, 'contract_information_configuration', None)
            if callback is None:
                continue
            profile = callback()
            if profile is not None:
                if not isinstance(profile, str) or not profile:
                    raise ValueError('invalid_contract_information_configuration')
                profiles.append(profile)
        return tuple(profiles)

    def contract_information_profile(self, context):
        """Read an optional bound presentation declaration, selecting no work."""
        selected = None
        for binding in self._bindings:
            callback = getattr(binding, 'contract_information_profile', None)
            if callback is None:
                continue
            value = callback(context)
            if value is None:
                continue
            if not isinstance(value, str) or not value or selected is not None and selected != value:
                raise ValueError('contract_information_profile_conflict')
            selected = value
        return selected

    def _received_report_mapping(self, name, argument):
        supplied = {}
        for binding in self._bindings:
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            value = callback(argument)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('received_report_field_conflict:' + name)
            supplied.update(_plain(value))
        return supplied

    def received_report_sources(self, role):
        """Typed facts another binding has actually delivered to this role."""
        return self._received_report_mapping('received_report_sources', role)

    def received_report_facts(self, context, *, completion_snapshot=None):
        """Copy public facts, adding optional private facts only at closure."""
        supplied = self._received_report_mapping('received_report_facts', context)
        if completion_snapshot is not None and completion_snapshot.get('completion') is not None:
            closed = self._received_report_mapping('received_report_closure_facts', context)
            if set(closed).intersection(supplied):
                raise ValueError('received_report_field_conflict:received_report_closure_facts')
            supplied.update(closed)
        return supplied

    def current_report_facts(self, context):
        """Current receipt-scoped views, separate from an archived return."""
        return self._received_report_mapping('current_report_facts', context)

    def resolve_received_reference(self, context, reference, namespace):
        result = None
        for binding in self._bindings:
            callback = getattr(binding, 'resolve_received_reference', None)
            if callback is None:
                continue
            value = callback(context, reference, namespace)
            if value is None:
                continue
            if type(value) is not bool or result is not None and result != value:
                raise ValueError('received_report_reference_conflict')
            result = value
        return result

    def validate_received_report(self, context, form, schema):
        for binding in self._bindings:
            callback = getattr(binding, 'validate_received_report', None)
            if callback is not None:
                callback(context, form, schema)

    def for_role(self, role):
        try:
            return self._by_role[role]
        except KeyError as error:
            raise LookupError('episode_role_not_bound:' + str(role)) from error

    def as_record(self):
        return [binding.as_record() for binding in self._bindings]

    def _reference_hook(self, name, context, *arguments):
        references = []
        for binding in self._bindings:
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            result = callback(context, *arguments)
            if (not isinstance(result, (list, tuple))
                    or any(not isinstance(ref, str) or not ref for ref in result)):
                raise TypeError('binding_receipt_references_required:' + name)
            references.extend(result)
        return list(dict.fromkeys(references))

    def initial_references(self, context):
        return self._reference_hook('initial_references', context)

    def received_form_references(self, context, form, schema, operation_key):
        return self._reference_hook('received_form_references', context,
                                    form, schema, operation_key)

    def received_evidence_tokens(self, context):
        """Immutable evidence actually held beyond ordinary record references."""
        return self._reference_hook('received_evidence_tokens', context)

    @property
    def entry_roles(self):
        return tuple(role for binding in self._bindings for role in binding.entry_roles)


__all__ = ['BindingContext', 'EpisodeBinding', 'EpisodeServices', 'EpisodeBindingRegistry',
           'native_job_event_configuration', 'reference_in_context', 'native_observation_options']
