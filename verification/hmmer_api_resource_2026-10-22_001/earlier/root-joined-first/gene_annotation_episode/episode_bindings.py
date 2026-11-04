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

    def __post_init__(self):
        for name in ('run_id', 'episode_id', 'role'):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f'nonempty_{name}_required')
        path = tuple(tuple(part) for part in self.path)
        if (not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                for item in part) for part in path) or path[-1][0] != self.role):
            raise ValueError('binding_context_path_must_match_role')
        object.__setattr__(self, 'path', path)
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


@runtime_checkable
class EpisodeServices(Protocol):
    def tool_catalog(self, scope): ...
    async def execute_tool(self, name, arguments, *, scope, operation_key): ...
    def read_record(self, reference): ...
    def reference_in_scope(self, reference, scope, namespace): ...
    def reference_in_context(self, context, reference, namespace): ...
    def scientific_credit(self, context, receiver_selection): ...
    def scientific_support_routes(self, context, *, observation_kinds): ...
    def bound_role_credit(self, context, receiver_selection): ...
    def capabilities(self): ...
    def public_search_ports(self, registry): ...
    async def observe_progress(self, target_handle, requested_fields, scope, *,
                         permitted_committed_record_types=(), operation_key=None): ...
    def read_progress(self, reference, scope): ...
    def received_progress_refs(self, episode_id): ...
    def progress_selection(self, context): ...
    def record_selection(self, context): ...
    def scientific_preparation(self, context, preparation_ref, *, owner='self'): ...
    def scientific_received_results(self, context): ...
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

    @property
    def entry_roles(self):
        return tuple(role for binding in self._bindings for role in binding.entry_roles)


__all__ = ['BindingContext', 'EpisodeBinding', 'EpisodeServices', 'EpisodeBindingRegistry',
           'native_job_event_configuration', 'reference_in_context']
