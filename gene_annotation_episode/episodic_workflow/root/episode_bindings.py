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
        return tuple((_freeze(item) for item in value))
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
    if not isinstance(value, Mapping) or set(value) != {'version', 'resource_id'} or value['version'] != 'native_job_events_v1' or (not isinstance(value['resource_id'], str)) or (not value['resource_id'].strip()):
        raise ValueError('invalid_native_job_events_binding')
    return json.loads(json.dumps(_plain(value), allow_nan=False))

def reference_in_context(services, context, reference, namespace):
    """Use contextual visibility without recursing through a binding resolver."""
    callback = getattr(services, 'reference_in_context', None)
    if callback is not None:
        return callback(context, reference, namespace)
    return services.reference_in_scope(reference, context.scope, namespace)
from .receiving_context import BindingContext

def native_observation_options(native_operation, observation_context):
    """Forward an explicit native choice with its internal selecting context.

    Omission preserves the old call and persisted-selection shapes. This is
    not custody authentication; the actual execution owner verifies the saved
    selection and original assignment before acquiring anything.
    """
    from gene_annotation_episode.domain import ContractError
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

    def tool_catalog(self, scope):
        ...

    def tool_information_catalog(self, scope):
        ...

    async def execute_tool(self, name, arguments, *, scope, operation_key, permitted_record_refs=None):
        ...

    def authenticate_structure_alignment_operands(self, context: BindingContext, arguments: dict) -> dict:
        ...

    def authenticate_source_byte_operands(self, context: BindingContext, tool_name: str, arguments: dict) -> None:
        ...

    def read_record(self, reference):
        ...

    def reference_in_scope(self, reference, scope, namespace):
        ...

    def reference_in_context(self, context, reference, namespace):
        ...

    def scientific_credit(self, context, receiver_selection):
        ...

    def scientific_support_routes(self, context, *, observation_kinds):
        ...

    def bound_role_credit(self, context, receiver_selection):
        ...

    def capabilities(self):
        ...

    def observe_progress(self, target_handle, requested_fields, scope, *, permitted_committed_record_types=(), operation_key=None, native_operation=None, observation_context=None):
        ...

    def describe_progress_target(self, target_handle, scope):
        ...

    def read_progress(self, reference, scope):
        ...

    def received_progress_refs(self, episode_id):
        ...

    def progress_selection(self, context):
        ...

    def record_selection(self, context):
        ...

    def scientific_preparation(self, context, preparation_ref, *, owner='self'):
        ...

    def scientific_parent_preparation(self, context, preparation_ref):
        ...

    def scientific_received_results(self, context):
        ...

    def scientific_frozen_results(self, context):
        ...

    def alignment_site_own_action_results(self, context, *, source, selection, after_decision_index, limit):
        ...

    def alignment_site_frozen_facts(self, context, *, sources):
        ...

    def scientific_parent_invocation(self, context):
        ...

    def scientific_reference(self, context, reference, namespace):
        ...

    def dependencies(self, target_handle, scope):
        ...

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        ...

@runtime_checkable
class EpisodeBinding(Protocol):
    roles: tuple[str, ...]
    entry_roles: tuple[str, ...]

    def child_roles(self, role):
        ...

    def as_record(self):
        ...

    def credit_kind(self, role):
        ...

    def assignment_schema(self, role):
        ...

    def permitted_common_actions(self, context):
        ...

    def allowed_children(self, parent, caller_capabilities):
        ...

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        ...

    def instructions(self, context):
        ...

    def decision_context(self, context, current_view):
        ...

    def catalog(self, context):
        ...

    def execute(self, context, tool_name, arguments, operation_key):
        ...

    def fact_sources(self, role):
        ...

    def facts(self, context, completion_snapshot):
        ...

    def resolve(self, context, reference, namespace):
        ...

    def validate_report(self, context, form, original_schema):
        ...

    def credit_view(self, context, receiver_selection):
        ...

class EpisodeBindingRegistry:
    """Address explicitly supplied bindings; never instantiate child episodes."""

    def __init__(self, bindings=(), *, owners=None, owner_for_path=None, terminal_configuration=None):
        self._terminal_configuration = None
        self._terminal_bindings = ()
        if terminal_configuration is not None:
            from .terminal_binding_catalogue import OWNER, validate_fixed_group
            bindings = tuple(bindings)
            owners = None if owners is None else tuple(owners)
            if owners is not None and owners != (OWNER,) * len(bindings):
                raise ValueError('root_terminal_declared_owner_required')
            self._terminal_configuration = validate_fixed_group(bindings, terminal_configuration)
            self._terminal_bindings = bindings
        self._owner_groups = None
        self._owner_for_path = owner_for_path
        if owners is not None:
            from .private_episode_selection import PrivateBindingOwners
            bindings, owners = tuple(bindings), tuple(owners)
            if len(bindings) != len(owners) or not owners:
                raise ValueError('root_binding_owner_per_binding_required')
            grouped = {}
            for owner, binding in zip(owners, bindings):
                if type(owner) is not str or not owner:
                    raise ValueError('root_binding_owner_required')
                grouped.setdefault(owner, []).append(binding)
            groups = {}
            for owner, values in grouped.items():
                group_terminal_configuration = None
                if owner == 'root.terminal_execution':
                    from .terminal_binding_catalogue import validate_fixed_group
                    group_terminal_configuration = validate_fixed_group(values,
                        values[0].as_record()['configuration'])
                groups[owner] = EpisodeBindingRegistry(values,
                    terminal_configuration=group_terminal_configuration)
            index = PrivateBindingOwners(owners=tuple(grouped), entries=zip(owners, bindings))
            self._private_index = index
            self._owner_groups = groups
            self._bindings = list(bindings)
            self._by_path = {}
            self._by_role = {}
            for binding in bindings:
                for role in binding.roles:
                    self._by_role.setdefault(role, []).append(binding)
            return

        self._by_role = {}
        self._by_path = {}
        self._bindings = []
        for binding in bindings:
            self.register(binding)

    @property
    def private_owners(self):
        return () if self._owner_groups is None else tuple(self._owner_groups)

    def private_selection(self, owner, path):
        return self._private_index.selection(owner, path)

    def restore_private_selection(self, record, **expected):
        return self._private_index.restore_selection(record, **expected)

    def owner_records(self):
        return None if self._owner_groups is None else self._private_index.as_record()

    def _selected_group(self, *, owner=None, path=None, child_role=None):
        if self._owner_groups is None:
            if owner is not None:
                raise LookupError('root_binding_owner_not_registered:' + str(owner))
            return self
        if path is not None:
            selected = self._owner_for_path(path) if self._owner_for_path is not None else None
            if owner is not None and selected is not None and owner != selected:
                permitted = False
                if owner == 'root.terminal_execution' and child_role in {'launch_local', 'launch_hpc'}:
                    from .scientific_process.episode import ScientificProcessEpisodes
                    from .predefined_parent_routes import binding_for_child
                    parent_group = self._owner_groups[selected]
                    terminal_group = self._owner_groups.get(owner)
                    if (type(parent_group.for_path(path)) is ScientificProcessEpisodes
                            and terminal_group is not None
                            and terminal_group._terminal_configuration is not None):
                        permitted = binding_for_child(terminal_group._terminal_bindings,
                            path, child_role) is not None
                if not permitted:
                    raise ValueError('root_binding_path_owner_conflict')
            owner = selected if owner is None else owner
        if owner is None:
            if len(self._owner_groups) != 1:
                raise LookupError('root_binding_owner_required')
            owner = next(iter(self._owner_groups))
        try:
            return self._owner_groups[owner]
        except KeyError as error:
            raise LookupError('root_binding_owner_not_registered:' + str(owner)) from error

    def register(self, binding):
        if self._owner_groups is not None:
            raise ValueError('root_binding_owner_registration_is_immutable')

        if not isinstance(binding, EpisodeBinding):
            raise TypeError('complete_episode_binding_required')
        roles = binding.roles
        if not isinstance(roles, tuple) or not roles or len(set(roles)) != len(roles) or any((not isinstance(role, str) or not role for role in roles)):
            raise ValueError('unique_nonempty_episode_roles_required')
        path = getattr(binding, 'binding_path', None)
        if path is not None:
            parent = getattr(binding, 'commissioning_parent', None)
            if not isinstance(path, str) or not path or any((not part or part in {'.', '..'} for part in path.split('/'))) or (not isinstance(parent, str)) or (not parent):
                raise ValueError('explicit_episode_binding_path_required')
            if path in self._by_path:
                raise ValueError('duplicate_episode_binding_path:' + path)
        conflicts = {role for role in roles if role in self._by_role and (path is None or any((getattr(other, 'binding_path', None) is None for other in self._by_role[role])))}
        if conflicts:
            raise ValueError('duplicate_episode_role:' + ','.join(sorted(conflicts)))
        for role in roles:
            if binding.credit_kind(role) not in {'scientific', 'operational', 'monitoring'}:
                raise ValueError('declared_credit_kind_required:' + role)
        if not isinstance(binding.entry_roles, tuple) or not set(binding.entry_roles) <= set(roles):
            raise ValueError('entry_roles_must_be_declared_roles')
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
        """Already recorded caller information before an episode's first choice."""
        if self._terminal_configuration is not None:
            from .terminal_binding_catalogue import authenticated_initial_information
            return authenticated_initial_information(self._terminal_bindings,
                self._terminal_configuration, context)
        if self._owner_groups is not None and getattr(context, 'path', None) is not None:
            selected = self._owner_for_path(context.path) if self._owner_for_path is not None else None
            if selected is not None:
                group = self._selected_group(owner=selected)
                if group._terminal_configuration is not None:
                    return group.initial_decision_context(context)
        supplied = {}
        for binding in self._context_bindings(context):
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
        from .literature_families import configuration_bindings
        for binding in configuration_bindings(self._bindings):
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
            if not isinstance(value, str) or not value or (selected is not None and selected != value):
                raise ValueError('contract_information_profile_conflict')
            selected = value
        return selected

    def _received_report_mapping(self, name, argument, *, bindings=None):
        supplied = {}
        for binding in self._context_bindings(argument) if bindings is None else bindings:
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            value = callback(argument)
            if not isinstance(value, Mapping) or set(value).intersection(supplied):
                raise ValueError('received_report_field_conflict:' + name)
            supplied.update(_plain(value))
        return supplied

    def received_report_sources(self, role, *, path=None, parent_path=None, owner=None):
        """Declared typed facts, with prospective ownership explicit and no fake key."""
        return self._received_report_mapping('received_report_sources', role, bindings=self._report_source_bindings(role, path=path, parent_path=parent_path, owner=owner))

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
        for binding in self._context_bindings(context):
            callback = getattr(binding, 'resolve_received_reference', None)
            if callback is None:
                continue
            value = callback(context, reference, namespace)
            if value is None:
                continue
            if type(value) is not bool or (result is not None and result != value):
                raise ValueError('received_report_reference_conflict')
            result = value
        return result

    def validate_received_report(self, context, form, schema):
        for binding in self._context_bindings(context):
            callback = getattr(binding, 'validate_received_report', None)
            if callback is not None:
                callback(context, form, schema)

    def for_role(self, role, *, owner=None):
        if self._owner_groups is not None or owner is not None:
            return self._selected_group(owner=owner).for_role(role)

        try:
            candidates = self._by_role[role]
        except KeyError as error:
            raise LookupError('episode_role_not_bound:' + str(role)) from error
        if len(candidates) != 1:
            raise LookupError('episode_role_requires_parent:' + str(role))
        return candidates[0]

    def as_record(self):
        from .published_evidence_assessment.aggregate_records import registry_records
        return registry_records(self._bindings)

    def _reference_hook(self, name, context, *arguments):
        references = []
        for binding in self._context_bindings(context):
            callback = getattr(binding, name, None)
            if callback is None:
                continue
            result = callback(context, *arguments)
            if not isinstance(result, (list, tuple)) or any((not isinstance(ref, str) or not ref for ref in result)):
                raise TypeError('binding_receipt_references_required:' + name)
            references.extend(result)
        return list(dict.fromkeys(references))

    def initial_references(self, context):
        return self._reference_hook('initial_references', context)

    def received_form_references(self, context, form, schema, operation_key):
        return self._reference_hook('received_form_references', context, form, schema, operation_key)

    def received_evidence_tokens(self, context):
        """Immutable evidence actually held beyond ordinary record references."""
        return self._reference_hook('received_evidence_tokens', context)

    @property
    def entry_roles(self):
        if self._owner_groups is not None:
            return tuple(dict.fromkeys(role for binding in self._bindings for role in binding.entry_roles))

        return tuple((role for binding in self._bindings for role in binding.entry_roles))

    def for_binding_path(self, path, *, owner=None):
        if self._owner_groups is not None:
            return self._private_index.resolve(path, owner=owner)
        if owner is not None:
            raise LookupError('root_binding_owner_not_registered:' + str(owner))

        try:
            return self._by_path[path]
        except KeyError as error:
            raise LookupError('episode_binding_path_not_bound:' + str(path)) from error

    def declared_children(self, role):
        return tuple(dict.fromkeys((child for binding in self._by_role.get(role, ()) for child in binding.child_roles(role))))

    def _child_binding(self, parent, role):
        candidates = self._by_role.get(role, ())
        if not candidates:
            raise LookupError('episode_role_not_bound:' + str(role))
        parent_path = parent if type(parent) is str else getattr(parent, 'binding_path', None)
        if parent_path is not None:
            matches = [binding for binding in candidates if getattr(binding, 'commissioning_parent', None) == parent_path]
            if not matches and type(parent) is not str and role in parent.roles and (role in parent.child_roles(role)):
                matches = [parent]
            if not matches:
                matches = [binding for binding in candidates if getattr(binding, 'binding_path', None) is None]
        elif parent is None:
            matches = [binding for binding in candidates if role in binding.entry_roles and getattr(binding, 'commissioning_parent', None) == 'annotation']
        else:
            matches = [binding for binding in candidates if getattr(binding, 'binding_path', None) is None]
        if len(matches) != 1:
            raise LookupError('episode_child_not_bound:' + str(parent_path) + ':' + str(role))
        return matches[0]

    def _structural_path(self, path):
        from .method_loop.identities import normalize_structural_path
        return normalize_structural_path(path)

    def for_path(self, path, *, owner=None):
        if self._owner_groups is not None or owner is not None:
            return self._selected_group(owner=owner, path=path).for_path(path)

        path = self._structural_path(path)
        if self._terminal_configuration is not None:
            from .predefined_parent_routes import binding_for_path
            selected = binding_for_path(self._terminal_bindings, path)
            if selected is not None:
                return selected
        candidates = self._by_role.get(path[-1][0], ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
        parent = None
        for index, (role, _) in enumerate(path):
            if index == 0 and role == 'annotation' and (role not in self._by_role):
                continue
            if index == 0 and len(self._by_role.get(role, ())) > 1:
                entries = [candidate for candidate in self._by_role[role] if role in candidate.entry_roles]
                if len(entries) != 1:
                    raise LookupError('episode_role_requires_parent:' + str(role))
                parent = entries[0]
            else:
                parent = self.for_role(role) if index == 0 else self._child_binding(parent, role)
        if parent is None:
            raise LookupError('episode_role_not_bound:' + path[-1][0])
        return parent

    def for_child(self, parent_path, role, *, owner=None):
        if self._owner_groups is not None or owner is not None:
            return self._selected_group(owner=owner, path=parent_path, child_role=role).for_child(parent_path, role)

        path = self._structural_path(parent_path)
        if self._terminal_configuration is not None:
            from .predefined_parent_routes import binding_for_child
            selected = binding_for_child(self._terminal_bindings, path, role)
            if selected is not None:
                return selected
        candidates = self._by_role.get(role, ())
        if len(candidates) == 1 and getattr(candidates[0], 'binding_path', None) is None:
            return candidates[0]
        parent = None if len(path) == 1 and path[0][0] == 'annotation' and ('annotation' not in self._by_role) else self.for_path(path)
        return self._child_binding(parent, role)

    def _lineage_bindings(self, path, *, prospective_role=None, owner=None):
        if self._owner_groups is not None:
            selected = self._owner_for_path(path) if self._owner_for_path is not None else None
            if selected is None and owner is None and prospective_role is None and len(path) == 1 and path[0][0] == 'annotation' and len(self._owner_groups) > 1:
                return []
            return self._selected_group(owner=owner, path=path, child_role=prospective_role)._lineage_bindings(path, prospective_role=prospective_role)

        path = self._structural_path(path)
        selected = set()
        current = None
        for index, (role, _) in enumerate(path):
            if role in self._by_role:
                current = self.for_path(path[:index + 1])
                selected.add(id(current))
        if prospective_role in self._by_role:
            current = self.for_child(path, prospective_role)
            selected.add(id(current))
        for role, candidates in self._by_role.items():
            if len(candidates) == 1:
                selected.add(id(candidates[0]))
            else:
                try:
                    child = self._child_binding(current, role)
                except LookupError:
                    continue
                selected.add(id(child))
        from .literature_families import context_bindings
        values = context_bindings([binding for binding in self._bindings if id(binding) in selected],
                                  path[-1][0] if prospective_role is None else prospective_role, selected_owner=current)
        return self._custody_bindings(values)

    @staticmethod
    def _custody_bindings(bindings):
        from .execution_family_composition import custody_bindings as execution_custody
        from .resource_binding_catalogue import custody_bindings as resource_custody
        return resource_custody(execution_custody(bindings))

    def _context_bindings(self, context):
        if self._owner_groups is not None and getattr(context, 'path', None) is None:
            return self._selected_group()._context_bindings(context)

        path = getattr(context, 'path', None)
        if path is None:
            from .literature_families import role_only_context_permitted
            if any((len(bindings) != 1 for bindings in self._by_role.values())) and not role_only_context_permitted(self._by_role):
                raise LookupError('episode_binding_context_required')
            from .literature_families import context_bindings
            return self._custody_bindings(context_bindings(self._bindings, context, use_context=True))
        return self._lineage_bindings(path)

    def _report_source_bindings(self, role, *, path=None, parent_path=None, owner=None):
        if path is not None and parent_path is not None:
            raise ValueError('one_report_source_lineage_required')
        if path is not None:
            path = self._structural_path(path)
            if path[-1][0] != role:
                raise ValueError('report_source_role_path_mismatch')
            return self._lineage_bindings(path, owner=owner)
        if parent_path is not None:
            return self._lineage_bindings(parent_path, prospective_role=role, owner=owner)
        if owner is not None:
            return self._selected_group(owner=owner)._context_bindings(role)
        return self._context_bindings(role)
__all__ = ['BindingContext', 'EpisodeBinding', 'EpisodeServices', 'EpisodeBindingRegistry', 'native_job_event_configuration', 'reference_in_context', 'native_observation_options']
