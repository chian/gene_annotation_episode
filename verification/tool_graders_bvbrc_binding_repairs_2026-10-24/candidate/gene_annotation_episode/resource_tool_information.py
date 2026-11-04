"""Selectable operation contracts from explicitly configured episode owners.

These declarations grant no direct invocation. Reading them never creates an
assignment, probes a resource, or executes work. The launch/results assignment
schemas remain the only way to commission the declared resource operations.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from jsonschema import Draft202012Validator

from .communication import plain
from .tool_information import RESOURCE_KINDS, comparable_contract, resource_kind


_RESOURCE_ROLES = {'api': 'launch_api', 'local': 'launch_local', 'hpc': 'launch_hpc'}


def _contract(value):
    if (not isinstance(value, Mapping)
            or any(not isinstance(value.get(field), str) or not value[field].strip()
                   for field in ('name', 'description'))
            or value.get('resources') not in RESOURCE_KINDS
            or not isinstance(value.get('input_schema'), Mapping)):
        raise ValueError('resource_tool_information_contract_invalid')
    row = plain(value)
    Draft202012Validator.check_schema(row['input_schema'])
    return row


def bound_resource_tool_contracts(binding) -> list[dict]:
    """Read the owner's pure declarations, never its assignment-based catalog.

    A binding without this declaration hook supplies no resource operations.
    In particular, source-library entries and generic transport capabilities
    cannot establish a scientific deployment.
    """
    declare = getattr(binding, 'resource_tool_contracts', None)
    if not callable(declare):
        return []
    declared = declare()
    if not isinstance(declared, (list, tuple)):
        raise ValueError('resource_tool_information_contracts_required')
    rows, seen = [], set()
    for supplied in declared:
        row = _contract(supplied)
        key = row['name'], row['resources']
        if key in seen:
            raise ValueError('resource_tool_information_variant_duplicate')
        seen.add(key)
        route = row.get('invocation_route')
        if (not isinstance(route, dict) or set(route) != {'kind', 'routes'}
                or route['kind'] != 'commission' or not isinstance(route['routes'], list)
                or not route['routes']):
            raise ValueError('resource_tool_information_commission_route_required')
        routes = []
        for owner in route['routes']:
            if (not isinstance(owner, dict)
                    or set(owner) != {'entry_role', 'resource_id', 'resource_role'}
                    or owner['entry_role'] not in {'launch', 'results'}
                    or not isinstance(owner['resource_id'], str) or not owner['resource_id']
                    or owner['resource_role'] != ('results' if owner['entry_role'] == 'results'
                                                 else _RESOURCE_ROLES[row['resources']])
                    or owner['entry_role'] not in binding.entry_roles
                    or owner['resource_role'] not in binding.roles
                    or owner['resource_id'] not in binding.resources):
                raise ValueError('resource_tool_information_owner_invalid')
            if owner in routes:
                raise ValueError('resource_tool_information_route_duplicate')
            routes.append(owner)
        rows.append(row)
    return rows


def tool_information_contracts(direct_catalog, resource_catalog=()) -> list[dict]:
    """Join actual direct contracts with separately owned commission contracts."""
    if isinstance(direct_catalog, Mapping):
        direct_catalog = [{'name': name, **plain(row)} for name, row in direct_catalog.items()]
    result = {}
    for supplied in direct_catalog:
        row = plain(supplied)
        row['resources'] = row.get('resources') or resource_kind(row['name'])
        row['invocation_route'] = {'kind': 'direct'}
        row = _contract(row)
        key = row['name'], row['resources']
        if key in result:
            raise ValueError('resource_tool_information_variant_duplicate')
        result[key] = row
    for supplied in resource_catalog:
        row = _contract(supplied)
        key = row['name'], row['resources']
        previous = result.get(key)
        if previous is None:
            result[key] = row
        elif (previous['invocation_route']['kind'] != 'commission'
                or comparable_contract(previous) != comparable_contract(row)
                or previous['description'] != row['description']):
            raise ValueError('resource_tool_information_owner_conflict:' + row['name'])
        else:
            for route in row['invocation_route']['routes']:
                if route not in previous['invocation_route']['routes']:
                    previous['invocation_route']['routes'].append(deepcopy(route))
    return [result[key] for key in sorted(result)]


__all__ = ['bound_resource_tool_contracts', 'tool_information_contracts']
