"""Explicit, reconstructible caller operands for the wired execution family."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import json
import math
from types import MappingProxyType

from .communication import plain
from .episode_application_services import EpisodeApplicationServices
from .episode_monitoring import MonitorEpisodes, read_progress
from .episode_progress_credit import ProgressInformationCredit


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

    def __post_init__(self):
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
                'monitor_outcome_page_size')}}

    @classmethod
    def from_record(cls, value):
        value = plain(value)
        if not isinstance(value, dict) or value.get('version') != 'execution_service_factory_v1':
            raise ValueError('invalid_execution_service_factory')
        return cls(**{key: item for key, item in value.items() if key != 'version'})

    def __call__(self, store, *, run_id, directory, job_episodes=None,
                 resource_estimator=None, tool_registry=None, tool_catalog=None):
        from .execution_episodes import ExecutionEpisodes
        binding = ExecutionEpisodes(None, store=store, run_id=run_id, directory=directory,
            resources=plain(self.resources), initial_information=plain(self.initial_information),
            tool_registry=tool_registry, handoff_unit=self.handoff_unit,
            acquired_record_unit=self.acquired_record_unit,
            log_window_bytes=self.log_window_bytes, log_roles=self.log_roles)
        monitor = MonitorEpisodes(None, outcome_page_size=self.monitor_outcome_page_size)
        information = ProgressInformationCredit(_ProgressReader(store, run_id),
            information_unit=self.monitoring_information_unit)
        definition = {'version': 'execution_received_information_credit_v1',
            'handoff_unit': self.handoff_unit, 'acquired_record_unit': self.acquired_record_unit,
            'practical_units': 'original_assignment_progress_requirements',
            'baseline': 'original_received_information', 'repeated_gain': 0}
        resource_catalogs = {}
        for row in binding.resource_tool_contracts():
            resource_catalogs.setdefault(row['resources'], []).append(row)
        return EpisodeApplicationServices((binding.as_record(), monitor.as_record()), {
            **{role: {'definition': deepcopy(definition), 'project': binding.project_credit}
               for role in binding.roles},
            'monitor': {'definition': information.as_record(), 'project': information}},
            binding.job_progress_provider, resource_tool_catalogs=resource_catalogs)


__all__ = ['ExecutionServiceFactory']
