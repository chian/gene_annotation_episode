"""Explicit fixed-case caller using real public-search timing and prechoice.

This factory binds existing services and numerical policies. It performs no
custody, model call, search, scientific decision or controller observation.
Absolute imports retain the ordinary fixed-case source snapshot loader.
"""
from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path

from gene_annotation_episode import assembled_case_policy
from gene_annotation_episode.api_timing_records import ApiTimingBinding
from gene_annotation_episode.assembled_service_setup import (
    bind_assembled_services_with_public_search_timing_planning)
from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.resource_estimation import ResourceToolEstimator


VERSION = 'assembled_case_api_prechoice_v1'
_SERVICE_FIELDS = assembled_case_policy._SERVICE_FIELDS | {
    'public_search_registry', 'api_timing', 'api_execution_planning'}
_PLANNING = {'version': 'hmmer_api_execution_planning_v1',
    'callable': 'execution.estimate', 'target': 'public.hmmer.search'}
_UNITS = ('handoff_unit', 'acquired_record_unit', 'monitoring_information_unit')


def _json_copy(value):
    """Reject Python-only values before canonicalization can change them."""
    active = set()

    def validate(item):
        kind = type(item)
        if item is None or kind in (str, bool, int):
            return
        if kind is float:
            if not math.isfinite(item):
                raise ValueError
            return
        if kind not in (dict, list) or id(item) in active:
            raise ValueError
        active.add(id(item))
        try:
            if kind is dict:
                for key, child in item.items():
                    if type(key) is not str:
                        raise ValueError
                    validate(child)
            else:
                for child in item:
                    validate(child)
        finally:
            active.remove(id(item))

    try:
        validate(value)
        return json.loads(canonical(value))
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('finite_json_api_prechoice_parameters_required') from error


def create_policy(parameters: dict) -> PolicyBindings:
    """Preserve caller operands and opt into the actual registry-aware setup."""
    if type(parameters) is not dict or set(parameters) != {'policy', 'services'}:
        raise ValueError('explicit_api_prechoice_policy_sections_required')
    saved = _json_copy(parameters)
    services = saved['services']
    if (type(services) is not dict or set(services) != _SERVICE_FIELDS
            or services['version'] != VERSION):
        raise ValueError('explicit_api_prechoice_services_configuration_required')
    if services['api_execution_planning'] != _PLANNING:
        raise ValueError('unsupported_api_execution_planning_binding')
    for name in _UNITS:
        unit = services[name]
        try:
            valid = type(unit) in (int, float) and math.isfinite(unit) and unit > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('explicit_positive_api_prechoice_service_units_required')
    timing = ApiTimingBinding.from_record(services['api_timing'])
    base_services = {name: value for name, value in services.items()
                     if name not in {'api_timing', 'api_execution_planning'}}
    base_services['version'] = assembled_case_policy.API_VERSION
    base = assembled_case_policy.create_policy(
        {'policy': saved['policy'], 'services': base_services})
    if timing.resource_id != services['public_search_registry']['resource_id']:
        raise ValueError('api_prechoice_resource_identity_mismatch')
    if any(unit != timing.monitoring_information_unit for unit in (
            services['monitoring_information_unit'],
            saved['policy']['monitoring']['information_unit'],
            base.native_timing_information.information_unit)):
        raise ValueError('api_timing_information_unit_mismatch')
    estimator = ResourceToolEstimator.with_reported_results()

    def setup(store, *, run_id, directory, job_episodes, resource_estimator,
              tool_catalog, tool_registry):
        return bind_assembled_services_with_public_search_timing_planning(store,
            run_id=run_id, directory=directory, job_episodes=job_episodes,
            resource_estimator=resource_estimator, tool_catalog=tool_catalog,
            tool_registry=tool_registry,
            public_search_registry=json.loads(canonical(services['public_search_registry'])),
            api_timing=timing, native_timing_information=base.native_timing_information,
            source_directory=Path(services['source_directory']),
            tool_retrieval=json.loads(canonical(services['tool_retrieval'])),
            scientific_child_roles=tuple(services['scientific_child_roles']),
            handoff_unit=services['handoff_unit'],
            acquired_record_unit=services['acquired_record_unit'],
            monitoring_information_unit=services['monitoring_information_unit'],
            literature_outcome_page_size=services['literature_outcome_page_size'],
            monitor_outcome_page_size=services['monitor_outcome_page_size'],
            log_window_bytes=services['log_window_bytes'],
            log_roles=tuple(services['log_roles']))

    return replace(base, resource_estimator=estimator,
        episode_service_factory=setup,
        episode_service_binding=json.loads(canonical(services)),
        episode_service_inputs='actual_tool_registry_v1')


__all__ = ['create_policy']
