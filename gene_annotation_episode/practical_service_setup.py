"""Explicit caller configuration for practical resource episodes.

Constructing these services executes no command or discovery. Callers supply
the already recorded pre-decision inventory snapshot. A scientific caller can
merge these descriptors with its other bindings; no resource is selected here.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType

from .communication import plain
from .episode_application_services import EpisodeApplicationServices
from .terminal_execution_episodes import TerminalExecutionEpisodes


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class PracticalServiceFactory:
    resources: dict
    initial_information: dict

    def __post_init__(self):
        for field in ('resources', 'initial_information'):
            copied = json.loads(json.dumps(plain(getattr(self, field)), allow_nan=False))
            if not isinstance(copied, dict):
                raise ValueError('practical_service_configuration_object_required')
            object.__setattr__(self, field, _freeze(copied))

    def as_record(self):
        return {'version': 'practical_service_factory_v1', 'resources': plain(self.resources),
                'initial_information': plain(self.initial_information)}

    def __call__(self, store, *, run_id, directory, job_episodes=None, resource_estimator=None):
        binding = TerminalExecutionEpisodes(None, directory=Path(directory),
            resources=plain(self.resources), initial_information=plain(self.initial_information))
        # Common composition requires explicit operational bindings. Their
        # valuation operands are the original assignment's named requirements;
        # this descriptor never invents a numerical unit.
        def project(context, receiver_selection):
            return binding.state(context).credit_view()
        return EpisodeApplicationServices([binding.as_record()], {role: {
            'definition': {'version': 'practical_required_facts_credit_v1',
                'units': 'original_assignment_progress_requirement_credits',
                'baseline': 'original_initial_validations',
                'repeated_fact_gain': 0}, 'project': project} for role in binding.roles})


__all__ = ['PracticalServiceFactory']
