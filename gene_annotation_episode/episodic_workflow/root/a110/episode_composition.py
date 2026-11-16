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

from gene_annotation_episode.episodic_workflow.root.a110.method_loop.durable import DurableExecutionError, canonical

from .domain import validate_schema
from .episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from .episode_monitoring import ProgressProvider
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
        actual_text, recorded_text = canonical(actual), canonical(recorded)
        actual = json.loads(actual_text)
        recorded = json.loads(recorded_text)
    except (TypeError, ValueError, OverflowError):
        return False
    fields = {'version', 'binding_id', 'configuration'}
    if (type(actual) is not dict or type(recorded) is not dict
            or set(actual) != fields or set(recorded) != fields
            or any(type(value['version']) is not str
                or value['version'] != 'scientific_process_episode_v10'
                or value['binding_id'] != 'scientific_process'
                or type(value['configuration']) is not dict
                for value in (actual, recorded))):
        return False
    return actual_text == recorded_text


def reopen_scientific_binding(services, *, descriptor, directory):
    from .private_scientific_literature_reconstruction import CATALOG, reconstruct
    from .private_reconstruction_protocol import admit_descriptors, verify_owner
    record = _json_object(descriptor, 'scientific_process')
    if record.get('binding_id') != 'scientific_process':
        raise _failure('unavailable_binding', 'scientific_process')
    record, = admit_descriptors([record], CATALOG)
    binding = reconstruct(services, record, store=None, journal=None,
        directory=directory, tool_registry=None)
    verify_owner(binding, record, CATALOG['scientific_process'], axis_package=__package__)
    return binding


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
                             directory=None, tool_registry=None) -> EpisodeComposition:
    """Reconstruct literal current private descriptors without selecting work.

    Execution and HPC owners retain their own credit implementation and explicit
    configuration. Monitor credit uses the caller's supplied definition/project
    pair. Saved identities and counterpart declarations are checked before
    construction; exact source/configuration equality is then required.

    Descriptor checks precede capability reads and progress-table creation.
    The host installs the returned services before using a binding.
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

    bindings, adapters = [], []
    from .private_scientific_literature_reconstruction import (
        CATALOG as scientific_catalog, reconstruct as reconstruct_scientific)
    from .private_execution_hpc_reconstruction import (
        CATALOG as execution_catalog, reconstruct as reconstruct_execution)
    from .private_reconstruction_protocol import admit_descriptors, verify_owner
    if scientific_catalog.keys() & execution_catalog.keys():
        raise _failure('identity_conflict', 'private_reconstruction_catalog')
    catalog = {**scientific_catalog, **execution_catalog}
    admitted = admit_descriptors(saved, catalog)
    # Only monitor owners delegate their credit measurement to caller projectors.
    # Execution and HPC owners keep the credit_view defined by their own source.
    for descriptor in admitted:
        declaration = catalog[descriptor['binding_id']]
        if declaration['owner_class'] == 'MonitorEpisode':
            if execution_backend is None:
                raise _failure('unavailable_binding', 'execution_backend')
            for role in declaration['roles']:
                if role not in projectors:
                    raise _failure('unavailable_binding', role)
    for descriptor in admitted:
        name = descriptor['binding_id']
        constructor = reconstruct_scientific if name in scientific_catalog else reconstruct_execution
        binding = constructor(services, descriptor, store=store, journal=journal,
            directory=directory, tool_registry=tool_registry, execution_backend=execution_backend)
        verify_owner(binding, descriptor, catalog[name], axis_package=__package__)
        bindings.append(binding)

    # Registration validates the complete existing C7 port and role uniqueness;
    # no child/source/controller is constructed by the registry.
    try:
        EpisodeBindingRegistry(bindings)
    except (TypeError, ValueError) as error:
        raise _failure('identity_conflict', 'episode_bindings') from error

    capabilities = []
    for binding in bindings:
        if binding.as_record().get('binding_id') == 'execution_episode':
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
    progress = (ProgressProvider(store, execution_backend, run_id=journal.run_id,
                                job_provider=job_progress_provider)
                if execution_backend is not None else None)
    return EpisodeComposition(tuple(bindings), progress, tuple(capabilities),
                              MappingProxyType(projectors), MappingProxyType(definitions))


__all__ = ['EpisodeComposition', 'compose_episode_bindings', 'reopen_scientific_binding']
