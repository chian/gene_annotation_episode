"""Reconstruct the current A107 execution, HPC and monitor owners.

The composer admits the complete saved counterpart set before calling this
helper. Every catalog row names one existing parent-specific implementation.
Non-fingerprinted descriptors retain their original three-field shape.
No historical aliases, replacement roles or inferred credit are accepted.
"""
from __future__ import annotations

from importlib import import_module

from .private_reconstruction_protocol import _failure, _json_object, verify_owner


CATALOG = {
    'execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'legacy_annotation',
        'roles': ('launch',), 'entry_roles': ('launch',),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'legacy_annotation',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'legacy_annotation',
        'roles': ('results',), 'entry_roles': ('results',),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'legacy_annotation',
        'roles': ('hpc',), 'entry_roles': ('hpc',),
        'owner_class': 'HPCEpisode',
    },
    'hpc_work_planning/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'hpc_work_planning',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'hpc_work_planning/execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'hpc_work_planning',
        'roles': ('hpc_execution',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_resource_prediction': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'hpc_work_planning',
        'roles': ('hpc_prediction',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'scientific_process/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process',
        'roles': ('launch',), 'entry_roles': ('launch',),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'scientific_process',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'scientific_process/execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process',
        'roles': ('results',), 'entry_roles': ('results',),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'scientific_process',
        'roles': ('hpc',), 'entry_roles': ('hpc',),
        'owner_class': 'HPCEpisode',
    },
    'scientific_process/hpc_work_planning/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'scientific_process/hpc_work_planning',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'scientific_process/hpc_work_planning/execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'scientific_process/hpc_work_planning',
        'roles': ('hpc_execution',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1', 'fingerprinted': False,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1', 'fingerprinted': True,
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {
        'version': 'execution_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'scientific_process/hpc_work_planning/hpc_allocation_execution',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'scientific_process/hpc_work_planning/hpc_resource_prediction': {
        'version': 'hpc_episode_v1', 'fingerprinted': True,
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'scientific_process/hpc_work_planning',
        'roles': ('hpc_prediction',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
}


def reconstruct(services, descriptor, *, store, journal, directory,
                tool_registry, execution_backend=None):
    """Construct one admitted exact owner with the caller's original resources.

    The monitor's progress backend and bound_role_credit project/definition
    remain caller-owned. Execution and HPC retain their own original credit
    implementations. No constructor starts an episode or chooses work here.
    """
    record = _json_object(descriptor, 'episode_bindings')
    name = record.get('binding_id')
    if not isinstance(name, str) or name not in CATALOG:
        raise _failure('unavailable_binding', name if isinstance(name, str) else 'episode_bindings')
    declaration = CATALOG[name]
    fields = {'version', 'binding_id', 'configuration'}
    if declaration['fingerprinted']:
        fields.add('implementation_sha256')
    if set(record) != fields or record['version'] != declaration['version']:
        raise _failure('unavailable_binding', name)
    configuration = record['configuration']
    required, optional = set(declaration['required']), set(declaration['optional'])
    if (not isinstance(configuration, dict) or not required <= configuration.keys()
            or configuration.keys() - required - optional):
        raise _failure('unavailable_binding', name)
    if declaration['fingerprinted']:
        fingerprint = record['implementation_sha256']
        if (type(fingerprint) is not str or len(fingerprint) != 64
                or any(character not in '0123456789abcdef' for character in fingerprint)):
            raise _failure('unavailable_binding', name)
    try:
        module = import_module('.' + name.replace('/', '.') + '.episode', __package__)
        owner = getattr(module, declaration['owner_class'])
        if declaration['owner_class'] == 'ExecutionEpisode':
            if directory is None:
                raise _failure('unavailable_binding', name)
            binding = owner(services, store=store, directory=directory,
                run_id=journal.run_id, tool_registry=tool_registry, **configuration)
        elif declaration['owner_class'] == 'HPCEpisode':
            if directory is None:
                raise _failure('unavailable_binding', name)
            binding = owner(services, store=store, directory=directory,
                run_id=journal.run_id, **configuration)
        elif declaration['owner_class'] == 'MonitorEpisode':
            if execution_backend is None:
                raise _failure('unavailable_binding', 'execution_backend')
            binding = owner(services, **configuration)
        else:
            raise _failure('unavailable_binding', name)
        verify_owner(binding, record, declaration, axis_package=__package__)
        return binding
    except (ImportError, OSError, TypeError, ValueError, KeyError, AttributeError) as error:
        raise _failure('unavailable_binding', name) from error


__all__ = ['CATALOG', 'reconstruct']
