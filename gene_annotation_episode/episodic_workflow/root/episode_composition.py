"""Reopen saved specialist bindings against explicit application resources.

This module composes the existing C7 bindings; it starts no episode, model
session, transport or job. Saved descriptors identify implementations and
configuration, while executable credit projections and resources remain owned
by the caller. Unknown factories require that caller's explicit C1 factory.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from gene_annotation_episode.episodic_workflow.root.method_loop.durable import DurableExecutionError, canonical

from gene_annotation_episode.domain import validate_schema
from .episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from .progress_observations import ProgressProvider
from .resource_records import CAPABILITY_SCHEMA


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _failure(code, reference):
    return DurableExecutionError(code, affected_refs=[reference])


def _json_object(value, reference):
    if not isinstance(value, Mapping):
        raise _failure('unavailable_binding', reference)
    try:
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError) as error:
        raise _failure('unavailable_binding', reference) from error


def _same_record(actual, saved, reference):
    if canonical(actual) != canonical(saved):
        raise _failure('identity_conflict', reference)




def scientific_binding_compatible(actual, recorded):
    """Accept only the exact recorded descriptor."""
    try:
        return canonical(actual) == canonical(recorded)
    except (TypeError, ValueError, OverflowError):
        return False


def reopen_scientific_binding(services, *, descriptor, directory):
    """Restore the caller's pinned three-slot construction from this run only."""
    from .scientific_process.episode import ScientificProcessEpisodes
    from .scientific_process_library import ScientificProcessLibrary
    from .scientific_tool_library import ScientificToolLibrary
    reference = 'scientific_process'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    try:
        if descriptor.get('version') != 'scientific_process_episodes_v10':
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        expected = {'library', 'tool_library', 'child_roles'}
        if 'tool_retrieval' in configuration:
            expected.add('tool_retrieval')
        if 'contract_information_profile' in configuration:
            expected.add('contract_information_profile')
        if 'yield_bindings' in configuration:
            expected.add('yield_bindings')
        if set(configuration) != expected:
            raise _failure('unavailable_binding', reference)
        library = ScientificProcessLibrary(Path(directory)/'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory)/'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = ScientificProcessEpisodes(services, library=library, tool_library=tools,
            child_roles=configuration['child_roles'],
            tool_retrieval=configuration.get('tool_retrieval'),
            contract_information_profile=configuration.get('contract_information_profile'),
            yield_bindings=configuration.get('yield_bindings'))
        if not scientific_binding_compatible(binding.as_record(), descriptor):
            raise _failure('identity_conflict', reference)
        return binding
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error


@dataclass(frozen=True)
class EpisodeComposition:
    bindings: tuple[EpisodeBinding, ...]
    progress_provider: ProgressProvider | None
    resource_capabilities: tuple[Mapping[str, Any], ...]
    role_credit_projectors: Mapping[str, Callable]
    role_credit_definitions: Mapping[str, Mapping[str, Any]]


def compose_episode_bindings(services, *, store, journal, execution_backend,
                             descriptors, job_episodes, resource_estimator,
                             role_credit_bindings, job_progress_provider=None,
                             directory=None, tool_registry=None, terminal_configuration=None) -> EpisodeComposition:
    """Reconstruct literal saved C7 descriptors without selecting any work.

    Every operational/monitoring role needs its caller's explicit ``definition``
    and ``project`` pair. Literature continues to use the separately supplied
    scientific service. No callable, monitoring unit, operational weight or
    external-resource availability is inferred from a descriptor.

    Descriptor checks precede capability reads and progress-table creation.
    ``ProgressProvider`` is composed whenever a backend is supplied, including
    runs with no monitor role, so common typed admission can receive requested
    progress references. The host installs the returned services on its own
    application instance before using a binding.
    """
    if getattr(journal, 'store', None) is not store:
        raise _failure('identity_conflict', 'journal.store')
    if not isinstance(getattr(journal, 'run_id', None), str) or not journal.run_id:
        raise _failure('unavailable_binding', 'journal.run_id')
    if not isinstance(descriptors, (tuple, list)):
        raise _failure('unavailable_binding', 'episode_bindings')
    if job_progress_provider is not None and execution_backend is None:
        raise _failure('unavailable_binding', 'execution_backend')
    saved = [_json_object(value, 'episode_bindings') for value in descriptors]
    if not isinstance(role_credit_bindings, Mapping):
        raise _failure('unavailable_binding', 'role_credit_bindings')

    projectors, definitions = {}, {}
    for role, binding in role_credit_bindings.items():
        if not isinstance(role, str) or not role:
            raise _failure('unavailable_binding', 'role_credit_bindings')
        if (not isinstance(binding, Mapping) or set(binding) != {'definition', 'project'}
                or not callable(binding['project'])):
            raise _failure('unavailable_binding', role)
        definitions[role] = _freeze(_json_object(binding['definition'], role))
        projectors[role] = binding['project']

    terminal_identifiers = ()
    if terminal_configuration is not None:
        from .terminal_binding_catalogue import PARENT_ENTRIES, descriptor_parents
        descriptor_parents(terminal_configuration, saved)
        terminal_identifiers = tuple(entry[4] for entry in PARENT_ENTRIES)
    from .execution_family_composition import (IDENTIFIERS as EXECUTION_IDENTIFIERS,
        construct_family as construct_execution_family, validate_family as validate_execution_family)
    from .hpc_service_composition import IDENTIFIERS as HPC_IDENTIFIERS, construct_family as construct_hpc_family
    from .resource_binding_catalogue import (IDENTIFIERS as RESOURCE_IDENTIFIERS,
        saved_family as saved_resource_family, construct_family as construct_resource_family,
        ResourceDescriptorMismatch)
    from .monitor_binding_catalogue import (construct_family as construct_monitor_family,
        binding_for_descriptor as monitor_for_descriptor, MonitorDescriptorMismatch)
    execution_family, fixed_execution = (), {}
    hpc_family, fixed_hpc = (), {}
    resource_family, fixed_resource = (), {}
    monitor_family = ()
    bindings, adapters = [], []
    for descriptor in saved:
        name = descriptor.get('binding_id')
        reference = name if isinstance(name, str) and name else 'episode_bindings'
        configuration = descriptor.get('configuration')
        if not isinstance(configuration, dict):
            raise _failure('unavailable_binding', reference)
        try:
            if name == 'literature':
                from .literature_families import construct
                binding = construct(services, **configuration)
            elif name == 'scientific_process':
                binding = reopen_scientific_binding(services, descriptor=descriptor, directory=directory)
            elif name == 'monitor':
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                if not monitor_family:
                    monitor_family = construct_monitor_family(saved, services)
                binding = monitor_for_descriptor(monitor_family, descriptor)
            elif name in terminal_identifiers:
                if directory is None:
                    raise _failure('unavailable_binding', reference)
                from .terminal_binding_catalogue import construct_fixed_binding
                binding = construct_fixed_binding(descriptor, services, store=store,
                    directory=directory, configuration=terminal_configuration)
            elif name in HPC_IDENTIFIERS:
                if directory is None:
                    raise _failure('unavailable_binding', reference)
                if not hpc_family:
                    hpc_family = construct_hpc_family(saved, services, store=store,
                        run_id=journal.run_id, directory=directory)
                    fixed_hpc = {member.as_record()['binding_id']: member for member in hpc_family}
                binding = fixed_hpc[name]
            elif name in EXECUTION_IDENTIFIERS:
                if directory is None:
                    raise _failure('unavailable_binding', reference)
                if not execution_family:
                    execution_family = construct_execution_family(saved, services, store=store,
                        run_id=journal.run_id, directory=directory, tool_registry=tool_registry)
                    fixed_execution = {member.as_record()['binding_id']: member for member in execution_family}
                binding = fixed_execution[name]
            elif name in RESOURCE_IDENTIFIERS:
                if not resource_family:
                    resource_saved = saved_resource_family(saved)
                    resource_configuration = resource_saved[0]['configuration']
                    resource_adapters = []
                    for adapter_descriptor in resource_configuration['resource_adapters']:
                        if isinstance(adapter_descriptor, dict) and adapter_descriptor.get('version') == 'a102_structural_resource_adapter_v1':
                            raise _failure('unavailable_binding', 'a102_structural_resource_adapter_v1')
                        if (not isinstance(adapter_descriptor, dict) or
                                adapter_descriptor.get('version') != 'root_homology_resource_adapter_v1'):
                            raise _failure('unavailable_binding', reference)
                        adapter_ref = adapter_descriptor.get('resource_id')
                        adapter_ref = adapter_ref if isinstance(adapter_ref, str) and adapter_ref else reference
                        if job_episodes is None:
                            raise _failure('unavailable_binding', adapter_ref)
                        from .homology_resource_adapter import HomologyResourceAdapter
                        adapter = HomologyResourceAdapter(job_episodes, store, journal, resource_estimator)
                        _same_record(adapter.as_record(), adapter_descriptor, adapter_ref)
                        resource_adapters.append(adapter)
                    resource_family = construct_resource_family(saved, services,
                        resource_adapters=resource_adapters)
                    fixed_resource = {member.as_record()['binding_id']: member for member in resource_family}
                    adapters.extend(resource_adapters)
                binding = fixed_resource[name]
            else:
                raise _failure('unavailable_binding', reference)
        except (ResourceDescriptorMismatch, MonitorDescriptorMismatch) as error:
            raise _failure('identity_conflict', error.reference) from error
        except (TypeError, ValueError, KeyError, AttributeError) as error:
            raise _failure('unavailable_binding', reference) from error
        if name == 'scientific_process':
            if not scientific_binding_compatible(binding.as_record(), descriptor):
                raise _failure('identity_conflict', reference)
        elif name == 'literature':
            from .published_evidence_assessment.aggregate_records import family_record
            _same_record(family_record(binding), descriptor, reference)
        else:
            _same_record(binding.as_record(), descriptor, reference)
        for member in binding if name == 'literature' else (binding,):
            for role in member.roles:
                if member.credit_kind(role) != 'scientific' and role not in projectors:
                    raise _failure('unavailable_binding', role)
            bindings.append(member)

    # Registration validates the complete existing C7 port and role uniqueness;
    # no child/source/controller is constructed by the registry.
    try:
        EpisodeBindingRegistry(bindings)
    except (TypeError, ValueError) as error:
        raise _failure('identity_conflict', 'episode_bindings') from error

    capabilities = []
    if execution_family:
        execution_owner = validate_execution_family(execution_family)
        for declared in execution_owner.capabilities():
            capability = _json_object(declared, 'execution_episodes')
            validate_schema(capability, CAPABILITY_SCHEMA)
            capabilities.append(_freeze(capability))
    from .published_evidence_assessment.aggregate_records import binding_record_pairs
    for binding, record in binding_record_pairs(bindings):
        if record.get('binding_id') == 'execution_episodes':
            for declared in binding.capabilities():
                capability = _json_object(declared, 'execution_episodes')
                validate_schema(capability, CAPABILITY_SCHEMA)
                capabilities.append(_freeze(capability))
    for adapter in adapters:
        try:
            capability = _json_object(adapter.capability(), adapter.resource_id)
            validate_schema(capability, CAPABILITY_SCHEMA)
        except (TypeError, ValueError) as error:
            raise _failure('unavailable_binding', adapter.resource_id) from error
        if capability['resource_id'] != adapter.resource_id:
            raise _failure('identity_conflict', adapter.resource_id)
        capabilities.append(_freeze(capability))
    progress = (ProgressProvider(store, execution_backend, run_id=journal.run_id,
                                job_provider=job_progress_provider)
                if execution_backend is not None else None)
    return EpisodeComposition(tuple(bindings), progress, tuple(capabilities),
                              MappingProxyType(projectors), MappingProxyType(definitions))


__all__ = ['EpisodeComposition', 'compose_episode_bindings', 'reopen_scientific_binding']
