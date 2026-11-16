"""Reopen saved specialist bindings against explicit application resources.

This module composes the existing C7 bindings; it starts no episode, model
session, transport or job. Saved descriptors identify implementations and
configuration, while executable credit projections and resources remain owned
by the caller. Unknown factories require that caller's explicit C1 factory.
"""
from __future__ import annotations
from .resource_reconstruction import (RESOURCE_BINDINGS, RESOURCE_RECONSTRUCTION,
    reopen_resource_binding, validate_resource_portfolio)

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import import_module
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from gene_annotation_episode.episodic_workflow.root.a103.method_loop.durable import DurableExecutionError, canonical

from .domain import validate_schema
from .episode_bindings import EpisodeBinding, EpisodeBindingRegistry
from .episode_monitoring import ProgressProvider
from .resource_records import CAPABILITY_SCHEMA
from .a103_homology_resource_adapter import HomologyResourceAdapter


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


def reopen_scientific_binding(services, *, descriptor, directory):
    """Reopen this exact private scientific implementation from its saved libraries."""
    from .scientific_process.episode import ScientificProcessEpisode
    from .scientific_process_library import ScientificProcessLibrary
    from .scientific_tool_library import ScientificToolLibrary
    reference = 'scientific_process'
    if directory is None:
        raise _failure('unavailable_binding', reference)
    descriptor = _json_object(descriptor, reference)
    if (set(descriptor) != {'version', 'binding_id', 'implementation_sha256', 'configuration'}
            or descriptor.get('version') != 'scientific_process_episode_v10'
            or descriptor.get('binding_id') != reference):
        raise _failure('unavailable_binding', reference)
    configuration = descriptor['configuration']
    required = {'library', 'tool_library', 'child_roles'}
    optional = {'tool_retrieval', 'contract_information_profile', 'yield_bindings'}
    if (not isinstance(configuration, dict) or not required <= set(configuration)
            or set(configuration) - required - optional):
        raise _failure('unavailable_binding', reference)
    try:
        library = ScientificProcessLibrary(Path(directory) / 'scientific-process-library')
        _same_record(library.as_record(), configuration['library'], reference)
        tools = ScientificToolLibrary(Path(directory) / 'scientific-tool-library')
        _same_record(tools.as_record(), configuration['tool_library'], reference)
        binding = ScientificProcessEpisode(services, library=library, tool_library=tools,
            child_roles=configuration['child_roles'],
            tool_retrieval=configuration.get('tool_retrieval'),
            contract_information_profile=configuration.get('contract_information_profile'),
            yield_bindings=configuration.get('yield_bindings'))
    except (OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', reference) from error
    _same_record(binding.as_record(), descriptor, reference)
    return binding


@dataclass(frozen=True)
class EpisodeComposition:
    bindings: tuple[EpisodeBinding, ...]
    progress_provider: ProgressProvider | None
    resource_capabilities: tuple[Mapping[str, Any], ...]
    role_credit_projectors: Mapping[str, Callable]
    role_credit_definitions: Mapping[str, Mapping[str, Any]]


_PRIVATE_RECONSTRUCTION = {'scientific_process': ('scientific_process_episode_v10', ('library', 'tool_library', 'child_roles'), ('tool_retrieval', 'contract_information_profile', 'yield_bindings'), True), 'execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/hpc_allocation_execution/execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': ('execution_episode_v1', ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'), ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'), False), 'execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'scientific_process/execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'hpc_work_planning/execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'scientific_process/hpc_work_planning/execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': ('monitor_episode_binding_v1', ('outcome_page_size',), ('information_unit', 'yield_settings'), True), 'hpc_work_planning': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True), 'hpc_work_planning/hpc_allocation_execution': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True), 'hpc_work_planning/hpc_resource_prediction': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True), 'scientific_process/hpc_work_planning': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True), 'scientific_process/hpc_work_planning/hpc_allocation_execution': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True), 'scientific_process/hpc_work_planning/hpc_resource_prediction': ('hpc_episode_v1', ('resources', 'commissions'), ('shared_execution_memory', 'require_commission_yield'), True)}

_PRIVATE_RECONSTRUCTION.update(RESOURCE_RECONSTRUCTION)

def compose_episode_bindings(services, *, store, journal, execution_backend,
                             descriptors, job_episodes, resource_estimator,
                             role_credit_bindings, job_progress_provider=None,
                             directory=None, tool_registry=None) -> EpisodeComposition:
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

    admitted = []
    seen = set()
    for descriptor in saved:
        name = descriptor.get('binding_id')
        reference = name if isinstance(name, str) and name else 'episode_bindings'
        if not isinstance(name, str) or name not in _PRIVATE_RECONSTRUCTION:
            raise _failure('unavailable_binding', reference)
        if name in seen:
            raise _failure('identity_conflict', reference)
        seen.add(name)
        version, required, optional, fingerprinted = _PRIVATE_RECONSTRUCTION[name]
        fields = {'binding_id', 'version', 'configuration'}
        if fingerprinted:
            fields.add('implementation_sha256')
        if set(descriptor) != fields or descriptor['version'] != version:
            raise _failure('unavailable_binding', reference)
        configuration = descriptor['configuration']
        if (not isinstance(configuration, dict) or not set(required) <= set(configuration)
                or set(configuration) - set(required) - set(optional)):
            raise _failure('unavailable_binding', reference)
        if fingerprinted:
            fingerprint = descriptor['implementation_sha256']
            if (not isinstance(fingerprint, str) or len(fingerprint) != 64
                    or any(character not in '0123456789abcdef' for character in fingerprint)):
                raise _failure('unavailable_binding', reference)
        admitted.append((name, descriptor, configuration))
    # Complete identity/schema admission precedes any constructor.
    validate_resource_portfolio(seen, _failure)
    bindings, adapters = [], []
    resource_adapter_cache = {}
    for name, descriptor, configuration in admitted:
        try:
            if name in RESOURCE_BINDINGS:
                binding, added_adapters = reopen_resource_binding(name, configuration,
                    services=services, store=store, journal=journal, job_episodes=job_episodes,
                    resource_estimator=resource_estimator, adapter_cache=resource_adapter_cache,
                    failure=_failure, same_record=_same_record)
                adapters.extend(added_adapters)
            elif name == 'scientific_process':
                binding = reopen_scientific_binding(services, descriptor=descriptor, directory=directory)
            elif name == 'execution_job_submission':
                from .execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'execution_job_submission/api_job_execution':
                from .execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'execution_job_submission/local_job_execution':
                from .execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'execution_job_submission/hpc_job_execution':
                from .execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'execution_result_acquisition':
                from .execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/execution_job_submission':
                from .scientific_process.execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/execution_job_submission/api_job_execution':
                from .scientific_process.execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/execution_job_submission/local_job_execution':
                from .scientific_process.execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/execution_job_submission/hpc_job_execution':
                from .scientific_process.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/execution_result_acquisition':
                from .scientific_process.execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/execution_job_submission':
                from .hpc_work_planning.execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/execution_job_submission/api_job_execution':
                from .hpc_work_planning.execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/execution_job_submission/local_job_execution':
                from .hpc_work_planning.execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/execution_job_submission/hpc_job_execution':
                from .hpc_work_planning.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/execution_result_acquisition':
                from .hpc_work_planning.execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_job_submission':
                from .hpc_work_planning.hpc_allocation_execution.execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution':
                from .hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution':
                from .hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution':
                from .hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition':
                from .hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_job_submission':
                from .scientific_process.hpc_work_planning.execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution':
                from .scientific_process.hpc_work_planning.execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution':
                from .scientific_process.hpc_work_planning.execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution':
                from .scientific_process.hpc_work_planning.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_result_acquisition':
                from .scientific_process.hpc_work_planning.execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.api_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.local_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.episode import ExecutionEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, tool_registry=tool_registry, **configuration)
            elif name == 'execution_progress_assessment':
                from .execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'scientific_process/execution_progress_assessment':
                from .scientific_process.execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'hpc_work_planning/execution_progress_assessment':
                from .hpc_work_planning.execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment':
                from .hpc_work_planning.hpc_allocation_execution.execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'scientific_process/hpc_work_planning/execution_progress_assessment':
                from .scientific_process.hpc_work_planning.execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.execution_progress_assessment.episode import MonitorEpisode as PrivateBinding
                if execution_backend is None:
                    raise _failure('unavailable_binding', 'execution_backend')
                binding = PrivateBinding(services, **configuration)
            elif name == 'hpc_work_planning':
                from .hpc_work_planning.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
            elif name == 'hpc_work_planning/hpc_allocation_execution':
                from .hpc_work_planning.hpc_allocation_execution.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
            elif name == 'hpc_work_planning/hpc_resource_prediction':
                from .hpc_work_planning.hpc_resource_prediction.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
            elif name == 'scientific_process/hpc_work_planning':
                from .scientific_process.hpc_work_planning.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_allocation_execution':
                from .scientific_process.hpc_work_planning.hpc_allocation_execution.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
            elif name == 'scientific_process/hpc_work_planning/hpc_resource_prediction':
                from .scientific_process.hpc_work_planning.hpc_resource_prediction.episode import HPCEpisode as PrivateBinding
                if directory is None:
                    raise _failure('unavailable_binding', name)
                binding = PrivateBinding(services, store=store, directory=directory,
                    run_id=journal.run_id, **configuration)
        except (TypeError, ValueError, KeyError, AttributeError) as error:
            raise _failure('unavailable_binding', name) from error
        _same_record(binding.as_record(), descriptor, name)
        for role in binding.roles:
            if binding.credit_kind(role) != 'scientific' and role not in projectors:
                raise _failure('unavailable_binding', role)
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
