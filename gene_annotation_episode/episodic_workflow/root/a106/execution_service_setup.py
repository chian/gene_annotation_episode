"""Explicit, reconstructible caller operands for the wired execution family."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import json
import math
from types import MappingProxyType

from .communication import plain
from .episode_application_services import EpisodeApplicationServices
from .episode_monitoring import read_progress


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class _ProgressReader:
    store: object
    run_id: str

    def read_progress(self, reference, scope):
        return read_progress(self.store, self.run_id, reference, scope)


@dataclass(frozen=True)
class ExecutionServiceFactory:
    resources: dict
    initial_information: dict
    handoff_unit: float
    acquired_record_unit: float
    monitoring_information_unit: float
    log_window_bytes: int = 8192
    log_roles: tuple = ('stdout', 'stderr')
    monitor_outcome_page_size: int = 20
    monitor_yield_settings: dict | None = None
    require_private_execution_yield: bool = False
    task_yield_profiles: dict | None = None

    def __post_init__(self):
        if type(self.require_private_execution_yield) is not bool:
            raise TypeError('require_private_execution_yield_must_be_boolean')
        if self.task_yield_profiles is not None:
            profiles = plain(self.task_yield_profiles)
            if not isinstance(profiles, dict):
                raise ValueError('explicit_execution_task_yield_profiles_invalid')
            object.__setattr__(self, 'task_yield_profiles', _freeze(profiles))
        if self.monitor_yield_settings is not None:
            object.__setattr__(self, 'monitor_yield_settings', _freeze(plain(self.monitor_yield_settings)))
        for name in ('resources', 'initial_information'):
            value = json.loads(json.dumps(plain(getattr(self, name)), allow_nan=False))
            if not isinstance(value, dict) or name == 'resources' and not value:
                raise ValueError('explicit_execution_resources_required')
            object.__setattr__(self, name, _freeze(value))
        for name in ('handoff_unit', 'acquired_record_unit', 'monitoring_information_unit'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('explicit_positive_execution_information_units_required')
        for name in ('log_window_bytes', 'monitor_outcome_page_size'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError('explicit_positive_execution_window_required')
        roles = tuple(self.log_roles)
        if (not roles or any(not isinstance(role, str) or not role for role in roles)
                or len(set(roles)) != len(roles)):
            raise ValueError('explicit_execution_log_roles_required')
        object.__setattr__(self, 'log_roles', roles)

    def as_record(self):
        return {'version': 'execution_service_factory_v1',
            **{name: plain(getattr(self, name)) for name in (
                'resources', 'initial_information', 'handoff_unit', 'acquired_record_unit',
                'monitoring_information_unit', 'log_window_bytes', 'log_roles',
                'monitor_outcome_page_size')},
            **({'require_private_execution_yield': True} if self.require_private_execution_yield else {}),
            **({'task_yield_profiles': plain(self.task_yield_profiles)}
               if self.task_yield_profiles is not None else {}),
            **({'monitor_yield_settings': plain(self.monitor_yield_settings)}
               if self.monitor_yield_settings is not None else {})}

    @classmethod
    def from_record(cls, value):
        value = plain(value)
        if not isinstance(value, dict) or value.get('version') != 'execution_service_factory_v1':
            raise ValueError('invalid_execution_service_factory')
        return cls(**{key: item for key, item in value.items() if key != 'version'})

    def __call__(self, store, *, run_id, directory, job_episodes=None,
                 resource_estimator=None, tool_registry=None, tool_catalog=None):
        from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.execution_progress_assessment.episode import MonitorEpisode
        bindings = create_execution_bindings(None, store=store, run_id=run_id, directory=directory,
            resources=plain(self.resources), initial_information=plain(self.initial_information),
            tool_registry=tool_registry, handoff_unit=self.handoff_unit,
            acquired_record_unit=self.acquired_record_unit,
            log_window_bytes=self.log_window_bytes, log_roles=self.log_roles,
            require_private_yield=self.require_private_execution_yield,
            task_yield_profiles=(plain(self.task_yield_profiles)
                if self.task_yield_profiles is not None else None))
        from .perturbation_evidence.published_evidence_assessment.episode import create_execution_bindings as create_analysis_bindings
        analysis_bindings = create_analysis_bindings(None, store=store, run_id=run_id, directory=directory,
            tool_registry=tool_registry, **bindings[0].as_record()['configuration'])
        binding = bindings[0]
        monitor = MonitorEpisode(None, outcome_page_size=self.monitor_outcome_page_size,
            information_unit=self.monitoring_information_unit,
            yield_settings=plain(self.monitor_yield_settings) if self.monitor_yield_settings is not None else None)
        information = monitor.information_credit(_ProgressReader(store, run_id),
            information_unit=self.monitoring_information_unit)
        definition = {'version': 'execution_received_information_credit_v1',
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'practical_units': 'original_assignment_progress_requirements',
            'baseline': 'original_received_information', 'repeated_gain': 0}
        from .resource_tool_information import tool_information_contracts
        resource_rows = [row for item in bindings
            if item.roles in (('launch_api',), ('results',))
            for row in item.resource_tool_contracts()]
        resource_catalogs = {}
        for row in tool_information_contracts([], resource_rows):
            resource_catalogs.setdefault(row['resources'], []).append(row)
        descriptors = [*(item.as_record() for item in bindings), *(item.as_record() for item in analysis_bindings), monitor.as_record()]
        return EpisodeApplicationServices(tuple(descriptors), {
            **{role: {'definition': deepcopy(definition), 'project': item.project_credit}
               for item in bindings for role in item.roles},
            'monitor': {'definition': information.as_record(), 'project': information}},
            binding.job_progress_provider, resource_tool_catalogs=resource_catalogs)


__all__ = ['ExecutionServiceFactory']

from .perturbation_evidence.episode import create_execution_bindings
