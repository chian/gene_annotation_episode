"""Reconstruct the current A107 execution, HPC and monitor owners.

The composer admits the complete saved counterpart set before calling this
helper. Every catalog row names one existing parent-specific implementation.
Every descriptor has exactly binding_id, version and configuration.
No historical aliases, replacement roles or inferred credit are accepted.
"""
from __future__ import annotations

from importlib import import_module

from .private_reconstruction_protocol import _failure, _json_object, verify_owner


CATALOG = {
    'execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'legacy_annotation',
        'roles': ('launch',), 'entry_roles': ('launch',),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'legacy_annotation',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'legacy_annotation',
        'roles': ('results',), 'entry_roles': ('results',),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'legacy_annotation',
        'roles': ('hpc',), 'entry_roles': ('hpc',),
        'owner_class': 'HPCEpisode',
    },
    'hpc_work_planning/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'hpc_work_planning',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'hpc_work_planning/execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'hpc_work_planning',
        'roles': ('hpc_execution',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'hpc_work_planning/hpc_allocation_execution',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'hpc_work_planning/hpc_resource_prediction': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'hpc_work_planning',
        'roles': ('hpc_prediction',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'partner_presence_evidence/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence',
        'roles': ('launch',), 'entry_roles': ('launch',),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'partner_presence_evidence',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'partner_presence_evidence/execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence',
        'roles': ('results',), 'entry_roles': ('results',),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'partner_presence_evidence',
        'roles': ('hpc',), 'entry_roles': ('hpc',),
        'owner_class': 'HPCEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'partner_presence_evidence/hpc_work_planning',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'partner_presence_evidence/hpc_work_planning',
        'roles': ('hpc_execution',), 'entry_roles': (),
        'owner_class': 'HPCEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_api',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution',
        'roles': ('launch',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_hpc',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/local_job_execution': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission',
        'roles': ('launch_local',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_progress_assessment': {
        'version': 'monitor_episode_binding_v1',
        'required': ('outcome_page_size',),
        'optional': ('information_unit', 'yield_settings'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution',
        'roles': ('monitor',), 'entry_roles': ('monitor',),
        'owner_class': 'MonitorEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution/execution_result_acquisition': {
        'version': 'execution_episode_v1',
        'required': ('resources', 'initial_information', 'handoff_unit', 'acquired_record_unit', 'log_window_bytes', 'log_roles'),
        'optional': ('require_private_yield', 'results_yield_profiles', 'task_yield_profiles'),
        'parent': 'partner_presence_evidence/hpc_work_planning/hpc_allocation_execution',
        'roles': ('results',), 'entry_roles': (),
        'owner_class': 'ExecutionEpisode',
    },
    'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction': {
        'version': 'hpc_episode_v1',
        'required': ('resources', 'commissions'),
        'optional': ('shared_execution_memory', 'require_commission_yield'),
        'parent': 'partner_presence_evidence/hpc_work_planning',
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
    if set(record) != {'version', 'binding_id', 'configuration'} or record['version'] != declaration['version']:
        raise _failure('unavailable_binding', name)
    configuration = record['configuration']
    required, optional = set(declaration['required']), set(declaration['optional'])
    if (not isinstance(configuration, dict) or not required <= configuration.keys()
            or configuration.keys() - required - optional):
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
