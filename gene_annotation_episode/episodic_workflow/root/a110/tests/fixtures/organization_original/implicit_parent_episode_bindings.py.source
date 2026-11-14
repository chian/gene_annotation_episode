"""Application ports for composing A110 specializations of its private Episode loop.

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
    not custody authentication; the actual execution binding verifies the saved
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
    def scientific_preparation(self, context, preparation_ref): ...
    def scientific_parent_preparation(self, context, preparation_ref): ...
    def scientific_received_results(self, context): ...
    def scientific_frozen_results(self, context): ...
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
        self._by_path = {}
        self._bindings = []
        for binding in bindings:
            self.register(binding)
        self._initial_information_catalog = None
        self._annotation_initial_information = None
        self._received_execution_catalog = None
        self._annotation_received_execution = None



    def register(self, binding):
        if not isinstance(binding, EpisodeBinding):
            raise TypeError('complete_episode_binding_required')
        roles = binding.roles
        if (not isinstance(roles, tuple) or not roles or len(set(roles)) != len(roles)
                or any(not isinstance(role, str) or not role for role in roles)):
            raise ValueError('unique_nonempty_episode_roles_required')
        path = getattr(binding, 'binding_path', None)
        if path is not None:
            parent = getattr(binding, 'commissioning_parent', None)
            if (not isinstance(path, str) or not path
                    or any(not part or part in {'.', '..'} for part in path.split('/'))
                    or not isinstance(parent, str) or not parent):
                raise ValueError('explicit_episode_binding_path_required')
            if path in self._by_path:
                raise ValueError('duplicate_episode_binding_path:' + path)
        conflicts = {role for role in roles if role in self._by_role
            and (path is None or any(getattr(other, 'binding_path', None) is None
                                    for other in self._by_role[role]))}
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
        for role in roles:
            self._by_role.setdefault(role, []).append(binding)
        if path is not None:
            self._by_path[path] = binding



    @property
    def roles(self):
        return tuple(self._by_role)

    def initial_decision_context(self, context):
        """Old strict aggregation plus one explicitly selected private recipient."""
        supplied = {}
        for binding in self._context_bindings(context):
            callback = getattr(binding, 'initial_decision_context', None)
            if callback is None:
                continue
            value = callback(context)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('initial_binding_context_field_conflict')
            supplied.update(_plain(value))
        value = self._recipient_initial_information(context)
        if set(value).intersection(supplied):
            raise ValueError('initial_binding_context_field_conflict')
        supplied.update(value)
        return supplied


    def annotation_axis_yield_context(self, context, credit):
        """Owner-declared unresolved work for the annotation root's local fit."""
        supplied = {}
        for binding in self._context_bindings(context):
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
        for binding in self._context_bindings(context):
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


    def _received_report_mapping(self, name, argument, *, context=None):
        supplied = {}
        if name in {'received_report_sources', 'received_report_facts', 'received_report_closure_facts'}:
            reader = self._recipient_received_execution_information(context if context is not None else argument,
                configuration_only=name == 'received_report_sources')
            if reader is not None:
                value = getattr(reader, name)(argument)
                if not isinstance(value, Mapping) or set(value).intersection(supplied):
                    raise ValueError('received_report_field_conflict:' + name)
                supplied.update(_plain(value))
        for binding in self._context_bindings(context if context is not None else argument):
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            value = callback(argument)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('received_report_field_conflict:' + name)
            supplied.update(_plain(value))
        return supplied


    def received_report_sources(self, role, *, path=None):
        """Typed facts another binding has actually delivered to this role."""
        from types import SimpleNamespace
        return self._received_report_mapping('received_report_sources', role,
            context=SimpleNamespace(path=path) if path is not None else None)


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
        reader = self._recipient_received_execution_information(context)
        general_result = None if reader is None else reader.resolve_received_reference(context, reference, namespace)
        if general_result is not None and type(general_result) is not bool:
            raise ValueError('received_report_reference_conflict')
        result = None
        if general_result is not None:
            if result is not None and result != general_result:
                raise ValueError('received_report_reference_conflict')
            result = general_result
        for binding in self._context_bindings(context):
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
        reader = self._recipient_received_execution_information(context)
        if reader is not None:
            reader.validate_received_report(context, form, schema)
        for binding in self._context_bindings(context):
            callback = getattr(binding, 'validate_received_report', None)
            if callback is not None:
                callback(context, form, schema)


    def for_role(self, role):
        """Retain unambiguous legacy lookup; never choose between private parents."""
        try:
            candidates = self._by_role[role]
        except KeyError as error:
            raise LookupError('episode_role_not_bound:' + str(role)) from error
        if len(candidates) != 1:
            raise LookupError('episode_role_requires_parent:' + str(role))
        return candidates[0]


    def declared_children(self, role):
        """Type-graph union only; invocation dispatch still checks its actual parent."""
        return tuple(dict.fromkeys(child for binding in self._by_role.get(role, ())
                                   for child in binding.child_roles(role)))


    def _recipient_initial_information(self, context):
        catalog = self._initial_information_catalog
        if catalog is None:
            if (self._annotation_initial_information is not None or any(
                    getattr(binding, 'initial_information_requires_authority', False) for binding in self._bindings)):
                raise ValueError('initial_information_recipient_provenance_missing')
            return {}
        path = tuple(context.path)
        # The one unbound annotation root is the existing registry convention.
        # Bound roots and all other invocations must replay the actual saved graph.
        if (len(path) == 1 and path[0][0] == 'annotation'
                and 'annotation' not in self._by_role):
            callback = self._annotation_initial_information
            if callback is None:
                return {}
        else:
            recipient = self.for_path(path)
            callback = getattr(recipient, 'initial_information', None)
            if callback is not None and not callable(callback) and getattr(recipient, 'initial_information_requires_authority', False):
                callback = getattr(recipient, 'initial_information_consumer', callback)
            if callback is None:
                return catalog.original_global_information(context)
        value = callback(context, catalog)
        if not isinstance(value, Mapping):
            raise ValueError('initial_binding_context_field_conflict')
        return _plain(value)

    def configure_initial_information(self, catalog, annotation_consumer=None):
        if catalog is None:
            if annotation_consumer is not None or any(
                    getattr(binding, 'initial_information_requires_authority', False) for binding in self._bindings):
                raise ValueError('initial_information_recipient_provenance_missing')
        else:
            catalog.validate_consumers(self, annotation_consumer=annotation_consumer)
        self._initial_information_catalog = catalog
        self._annotation_initial_information = annotation_consumer

    def _context_bindings(self, context):
        """Keep duplicate role hooks with the saved lineage and its direct children."""
        path = getattr(context, 'path', None)
        if path is None:
            # Role-only callers cannot safely select private counterparts.
            if any(len(bindings) != 1 for bindings in self._by_role.values()):
                raise LookupError('episode_binding_context_required')
            return self._bindings
        selected = set()
        for index, (role, _) in enumerate(path):
            if role in self._by_role:
                selected.add(id(self.for_path(path[:index + 1])))
        for role, candidates in self._by_role.items():
            if len(candidates) == 1:
                selected.add(id(candidates[0]))
            else:
                try:
                    selected.add(id(self.for_child(path, role)))
                except LookupError:
                    pass
        return [binding for binding in self._bindings if id(binding) in selected]



    def for_binding_path(self, path):
        """Resolve an explicit predefined implementation identity, without importing code."""
        try:
            return self._by_path[path]
        except KeyError as error:
            raise LookupError('episode_binding_path_not_bound:' + str(path)) from error



    def _child_binding(self, parent, role):
        candidates = self._by_role.get(role, ())
        if not candidates:
            raise LookupError('episode_role_not_bound:' + str(role))
        parent_path = getattr(parent, 'binding_path', None)
        if parent_path is not None:
            matches = [binding for binding in candidates
                if getattr(binding, 'commissioning_parent', None) == parent_path]
            # Recursive invocations reuse their existing source home. A declared
            # direct child takes precedence over recursion of the same role.
            if not matches and role in parent.roles and role in parent.child_roles(role):
                matches = [parent]
            # Older caller-supplied bindings have no private commissioning path.
            if not matches:
                matches = [binding for binding in candidates
                           if getattr(binding, 'binding_path', None) is None]
        elif parent is None:
            matches = [binding for binding in candidates if role in binding.entry_roles
                and getattr(binding, 'commissioning_parent', 'legacy_annotation')
                    in {'legacy_annotation', 'annotation'}]
        else:
            # A legacy parent has no path identity; only a unique role is safe.
            matches = list(candidates)
        if len(matches) != 1:
            raise LookupError('episode_child_not_bound:' + str(parent_path) + ':' + str(role))
        return matches[0]



    def for_path(self, path):
        """Replay the declared graph using saved roles; invocation keys select no code."""
        path = tuple(tuple(part) for part in path)
        if not path or any(len(part) != 2 or any(not isinstance(item, str) or not item
                                               for item in part) for part in path):
            raise ValueError('episode_binding_runtime_path_required')
        candidates = self._by_role.get(path[-1][0], ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
        parent = None
        for index, (role, _) in enumerate(path):
            if index == 0 and role == 'annotation' and role not in self._by_role:
                continue
            # Explicit standalone use of one bound episode remains supported,
            # including an episode normally commissioned by another binding.
            parent = self.for_role(role) if index == 0 else self._child_binding(parent, role)
        if parent is None:
            raise LookupError('episode_role_not_bound:' + path[-1][0])
        return parent



    def for_child(self, parent_path, role):
        """Select this parent's private child before preparing its assignment."""
        candidates = self._by_role.get(role, ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
        path = tuple(parent_path)
        parent = (None if len(path) == 1 and path[0][0] == 'annotation'
                  and 'annotation' not in self._by_role else self.for_path(path))
        return self._child_binding(parent, role)



    def as_record(self):
        return [binding.as_record() for binding in self._bindings]

    def _reference_hook(self, name, context, *arguments):
        references = []
        if name == 'received_form_references':
            reader = self._recipient_received_execution_information(context)
            if reader is not None:
                result = reader.received_form_references(context, *arguments)
                if (not isinstance(result, (tuple, list))
                        or any(not isinstance(reference, str) or not reference for reference in result)):
                    raise TypeError('binding_receipt_references_required:' + name)
                references.extend(result)
        for binding in self._context_bindings(context):
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

    def configure_received_execution_information(self, catalog, annotation_consumer=None):
        if catalog is None:
            if annotation_consumer is not None:
                raise ValueError('received_execution_original_factory_required')
        else:
            from .library.received_execution_information.received_configuration import ReceivedExecutionCatalog
            if type(catalog) is not ReceivedExecutionCatalog:
                raise TypeError('actual_a110_received_execution_catalog_required')
            catalog.validate_consumers(self, annotation_consumer)
        self._received_execution_catalog = catalog
        self._annotation_received_execution = annotation_consumer

    def _recipient_received_execution_information(self, context, *, configuration_only=False):
        catalog = self._received_execution_catalog
        if catalog is None:
            if any((getattr(binding, 'received_execution_requires_authority', False) for binding in self._bindings)):
                raise ValueError('received_execution_original_factory_required')
            return None
        path = getattr(context, 'path', None)
        if path is None:
            if configuration_only and catalog.configuration.original_global_authority is not None:
                self._context_bindings(context)
                return catalog.configured('@original-global-role-only-schema')
            raise LookupError('episode_binding_context_required')
        path = tuple(path)
        if len(path) == 1 and path[0][0] == 'annotation' and ('annotation' not in self._by_role):
            callback = self._annotation_received_execution
        else:
            callback = getattr(self.for_path(path), 'received_execution_information', None)
        if callback is not None:
            return callback(context, catalog, configuration_only=configuration_only)
        if catalog.configuration.original_global_authority is None:
            raise ValueError('received_execution_recipient_provenance_missing')
        return catalog.configured('@original-global-recipient') if configuration_only else catalog.received('@original-global-recipient', context)


__all__ = ['BindingContext', 'EpisodeBinding', 'EpisodeServices', 'EpisodeBindingRegistry',
           'reference_in_context', 'native_observation_options']
