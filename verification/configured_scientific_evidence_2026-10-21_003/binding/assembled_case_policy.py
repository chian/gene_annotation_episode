"""Opt-in fixed-case policy using the existing scientific and numeric policies.

Parameters are explicit caller inputs. This factory binds setup; it neither
adopts a production profile nor starts an episode, model call or native job.
Absolute imports preserve the ordinary fixed-case source snapshot loader.
"""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from gene_annotation_episode.assembled_service_setup import bind_assembled_services
from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_monitoring import MonitorEpisodes
from gene_annotation_episode.investigation_policy import create_policy as investigation_policy
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.resource_episodes import ResourceEpisodes
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_tool_retrieval import configuration as retrieval_configuration


VERSION = 'assembled_case_services_v1'
_ROOT_ROLES = ('scientific_process', 'literature', 'launch', 'monitor', 'results')
_SPECIALIST_ROLES = (*ScientificProcessEpisodes.roles, *LiteratureEpisodes.roles,
                     *ResourceEpisodes.roles, *MonitorEpisodes.roles)
_SERVICE_FIELDS = {'version', 'source_directory', 'tool_retrieval',
    'scientific_child_roles', 'annotation_child_roles', 'execution_planning_roles',
    'handoff_unit', 'acquired_record_unit', 'monitoring_information_unit',
    'literature_outcome_page_size', 'monitor_outcome_page_size',
    'log_window_bytes', 'log_roles'}


def _roles(value):
    if (not isinstance(value, list) or not value
            or any(not isinstance(role, str) or not role for role in value)
            or len(set(value)) != len(value)):
        raise ValueError('explicit_unique_assembled_episode_roles_required')
    return tuple(value)


def create_policy(parameters: dict) -> PolicyBindings:
    """Retain original scientific/controller operands and bind explicit setup."""
    if not isinstance(parameters, dict) or set(parameters) != {'policy', 'services'}:
        raise ValueError('explicit_assembled_policy_sections_required')
    supplied = parameters['services']
    if (not isinstance(supplied, dict) or set(supplied) != _SERVICE_FIELDS
            or supplied.get('version') != VERSION):
        raise ValueError('explicit_assembled_services_configuration_required')
    services = json.loads(canonical(supplied))
    if not isinstance(services['source_directory'], str) or not services['source_directory']:
        raise ValueError('explicit_scientific_publication_directory_required')
    if not isinstance(services['tool_retrieval'], dict):
        raise TypeError('explicit_scientific_tool_retrieval_configuration_required')
    retrieval_configuration(services['tool_retrieval'])
    scientific_roles = _roles(services['scientific_child_roles'])
    root_roles = _roles(services['annotation_child_roles'])
    if scientific_roles != _ROOT_ROLES or root_roles != scientific_roles:
        raise ValueError('assembled_scientific_and_root_entry_roles_must_match')
    planning_roles = _roles(services['execution_planning_roles'])
    if not {'annotation', 'scientific_process'} <= set(planning_roles):
        raise ValueError('assembled_scientific_planning_roles_required')
    if (not isinstance(services['log_roles'], list)
            or any(not isinstance(role, str) for role in services['log_roles'])):
        raise ValueError('explicit_assembled_log_roles_required')
    original = parameters['policy']
    if not isinstance(original, dict) or original.get('scientific_child') != 'received_findings':
        raise ValueError('assembled_policy_requires_explicit_received_findings')
    policy = investigation_policy(original, episode_roles=_SPECIALIST_ROLES)

    def setup(store, *, run_id, directory, job_episodes, resource_estimator, tool_catalog):
        return bind_assembled_services(store, run_id=run_id, directory=directory,
            job_episodes=job_episodes, resource_estimator=resource_estimator,
            source_directory=Path(services['source_directory']), tool_catalog=tool_catalog,
            tool_retrieval=json.loads(canonical(services['tool_retrieval'])),
            scientific_child_roles=scientific_roles,
            handoff_unit=services['handoff_unit'],
            acquired_record_unit=services['acquired_record_unit'],
            monitoring_information_unit=services['monitoring_information_unit'],
            literature_outcome_page_size=services['literature_outcome_page_size'],
            monitor_outcome_page_size=services['monitor_outcome_page_size'],
            log_window_bytes=services['log_window_bytes'],
            log_roles=tuple(services['log_roles']))

    return replace(policy, episode_service_factory=setup,
        episode_service_binding=json.loads(canonical(services)),
        episode_service_inputs='actual_tool_catalog_v1', annotation_child_roles=root_roles,
        episode_record_receipts=True, execution_planning_roles=planning_roles)


__all__ = ['create_policy']
