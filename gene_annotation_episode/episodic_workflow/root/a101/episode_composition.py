"""Reopen saved specialist bindings against explicit application resources.

This module composes the existing C7 bindings; it starts no episode, model
session, transport or job. Saved descriptors identify implementations and
configuration, while executable credit projections and resources remain owned
by the caller. Unknown factories require that caller's explicit C1 factory.
"""
from __future__ import annotations
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any
from gene_annotation_episode.episodic_workflow.root.a101.method_loop.durable import DurableExecutionError, canonical
from .domain import validate_schema
from .episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from .episode_monitoring import ProgressProvider
from .resource_records import CAPABILITY_SCHEMA
from .a101_homology_resource_adapter import HomologyResourceAdapter

def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple((_freeze(item) for item in value))
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
    """Accept exact private implementation descriptors.

    This does not relabel the executing implementation or change a saved
    request. Library, callable, role and configuration identities stay exact.
    """
    try:
        actual_text, recorded_text = (canonical(actual), canonical(recorded))
        actual = json.loads(actual_text)
        recorded = json.loads(recorded_text)
    except (TypeError, ValueError, OverflowError):
        return False
    fields = {'version', 'binding_id', 'implementation_sha256', 'configuration'}
    if type(actual) is not dict or type(recorded) is not dict or set(actual) != fields or (set(recorded) != fields) or any((type(value['version']) is not str or value['version'] != 'scientific_process_episode_v10' or value['binding_id'] != 'scientific_process' or (type(value['configuration']) is not dict) or (type(value['implementation_sha256']) is not str) or (len(value['implementation_sha256']) != 64) or any((c not in '0123456789abcdef' for c in value['implementation_sha256'])) for value in (actual, recorded))):
        return False
    return actual_text == recorded_text

def reopen_scientific_binding(services, *, descriptor, directory):
    """Restore the caller's pinned three-slot construction from this run only."""
    from .scientific_process.episode import ScientificProcessEpisode as ScientificProcessEpisodes
    from .scientific_process_library import ScientificProcessLibrary
    from .scientific_tool_library import ScientificToolLibrary
    reference = 'scientific_process'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    try:
        if descriptor.get('version') != 'scientific_process_episode_v10':
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
        library = ScientificProcessLibrary(Path(directory) / 'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory) / 'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = ScientificProcessEpisodes(services, library=library, tool_library=tools, child_roles=configuration['child_roles'], tool_retrieval=configuration.get('tool_retrieval'), contract_information_profile=configuration.get('contract_information_profile'), yield_bindings=configuration.get('yield_bindings'))
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

def compose_episode_bindings(services, *, store, journal, execution_backend, descriptors, job_episodes, resource_estimator, role_credit_bindings, job_progress_provider=None, directory=None, tool_registry=None) -> EpisodeComposition:
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
    projectors, definitions = ({}, {})
    for role, binding in role_credit_bindings.items():
        if not isinstance(role, str) or not role:
            raise _failure('unavailable_binding', 'role_credit_bindings')
        if not isinstance(binding, Mapping) or set(binding) != {'definition', 'project'} or (not callable(binding['project'])):
            raise _failure('unavailable_binding', role)
        definitions[role] = _freeze(_json_object(binding['definition'], role))
        projectors[role] = binding['project']
    bindings, adapters = ([], [])
    from .private_binding_factories import private_binding_type
    for descriptor in saved:
        name = descriptor.get('binding_id')
        reference = name if isinstance(name, str) and name else 'episode_bindings'
        configuration = descriptor.get('configuration')
        if not isinstance(configuration, dict):
            raise _failure('unavailable_binding', reference)
        try:
            binding_type, family = private_binding_type(name)
            if family == 'scientific':
                binding = reopen_scientific_binding(services, descriptor=descriptor, directory=directory)
            elif family == 'literature':
                binding = binding_type(services, **configuration)
            elif family == 'monitor':
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = binding_type(services, **configuration)
            elif family == 'execution':
                if directory is None:
                    raise _failure('unavailable_binding', reference)
                binding = binding_type(services, store=store, directory=directory, run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif family == 'resource':
                if not {'resource_adapters'} <= set(configuration) <= {'resource_adapters', 'contract_information_profile'} or not isinstance(configuration['resource_adapters'], list):
                    raise _failure('unavailable_binding', reference)
                resource_adapters = []
                for adapter_descriptor in configuration['resource_adapters']:
                    if not isinstance(adapter_descriptor, dict) or adapter_descriptor.get('version') not in {'homology_resource_adapter_v1', 'homology_resource_adapter_v2'}:
                        raise _failure('unavailable_binding', reference)
                    adapter_ref = adapter_descriptor.get('resource_id')
                    adapter_ref = adapter_ref if isinstance(adapter_ref, str) and adapter_ref else reference
                    if job_episodes is None:
                        raise _failure('unavailable_binding', adapter_ref)
                    adapter = HomologyResourceAdapter(job_episodes, store, journal, resource_estimator)
                    _same_record(adapter.as_record(), adapter_descriptor, adapter_ref)
                    resource_adapters.append(adapter)
                binding = binding_type(services, resource_adapters=resource_adapters, contract_information_profile=configuration.get('contract_information_profile'))
                if binding.roles == ('launch',):
                    adapters.extend(resource_adapters)
            else:
                raise _failure('unavailable_binding', reference)
        except (TypeError, ValueError, KeyError, AttributeError, LookupError) as error:
            raise _failure('unavailable_binding', reference) from error
        if family == 'scientific':
            if not scientific_binding_compatible(binding.as_record(), descriptor):
                raise _failure('identity_conflict', reference)
        else:
            _same_record(binding.as_record(), descriptor, reference)
        for role in binding.roles:
            if binding.credit_kind(role) != 'scientific' and role not in projectors:
                raise _failure('unavailable_binding', role)
        bindings.append(binding)
    try:
        EpisodeBindingRegistry(bindings)
    except (TypeError, ValueError) as error:
        raise _failure('identity_conflict', 'episode_bindings') from error
    capabilities = []
    for binding in bindings:
        if private_binding_type(binding.binding_path)[1] == 'execution' and binding.roles == ('launch',):
            for declared in binding.capabilities():
                capability = _json_object(declared, 'execution_episode')
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
    progress = ProgressProvider(store, execution_backend, run_id=journal.run_id, job_provider=job_progress_provider) if execution_backend is not None else None
    return EpisodeComposition(tuple(bindings), progress, tuple(capabilities), MappingProxyType(projectors), MappingProxyType(definitions))
__all__ = ['EpisodeComposition', 'compose_episode_bindings', 'reopen_scientific_binding']
