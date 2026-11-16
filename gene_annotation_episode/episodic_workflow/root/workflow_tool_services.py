"""Root host ports defined by WorkflowToolServices."""
from __future__ import annotations
import inspect
from .communication import plain

class WorkflowToolServices:

    def tool_catalog(self, scope):
        catalog = self.workflow.tools.catalog(scope=plain(scope))
        return [{'name': name, **item} for name, item in catalog.items()] if isinstance(catalog, dict) else list(catalog)

    def tool_information_catalog(self, scope) -> list[dict]:
        """Describe direct tools and resource operations the child can commission.

        The direct registry remains unchanged. Only explicitly bound owners
        declare resource contracts; source-library information is not a route.
        """
        from .resource_tool_information import (bound_resource_tool_contracts,
            bound_execution_tool_contracts, tool_information_contracts)
        from .execution_family_composition import is_execution_binding, validate_family
        registry = self.workflow.episode_bindings
        scientific = self.workflow.scientific_process_binding
        child_roles = () if scientific is None else scientific.child_roles('scientific_process')
        resources, seen = ([], set())
        registered = tuple(registry._bindings)
        for binding in registered:
            if is_execution_binding(binding):
                owner = binding.owner
                if id(owner) in seen:
                    continue
                members = tuple(value for value in registered
                    if is_execution_binding(value)
                    and getattr(value, 'owner', None) is owner)
                if validate_family(members) is not owner:
                    raise ValueError('resource_tool_information_owner_invalid')
                seen.add(id(owner))
                for row in bound_execution_tool_contracts(members):
                    routes = []
                    for route in row['invocation_route']['routes']:
                        if route['entry_role'] not in child_roles:
                            continue
                        try:
                            entry = registry._child_binding(scientific, route['entry_role'])
                            actual = (entry if route['resource_role'] == route['entry_role'] else
                                      registry._child_binding(entry, route['resource_role']))
                        except LookupError:
                            continue
                        if (any(entry is value for value in members)
                                and any(actual is value for value in members)):
                            routes.append(route)
                    if routes:
                        resources.append({**row, 'invocation_route': {'kind': 'commission', 'routes': routes}})
                continue
            if id(binding) in seen:
                continue
            seen.add(id(binding))
            for row in bound_resource_tool_contracts(binding):
                routes = [route for route in row['invocation_route']['routes'] if route['entry_role'] in child_roles and registry.for_role(route['entry_role']) is binding and (registry.for_role(route['resource_role']) is binding)]
                if routes:
                    resources.append({**row, 'invocation_route': {'kind': 'commission', 'routes': routes}})
        return tool_information_contracts(self.tool_catalog(scope), resources)

    async def execute_tool(self, name, arguments, *, scope, operation_key, permitted_record_refs=None):
        tools = self.workflow.tools
        dispatch = getattr(tools, 'execute_async', tools.execute)
        authorization = {'permitted_record_refs': tuple(permitted_record_refs)} if permitted_record_refs is not None else {}
        result = dispatch(name, plain(arguments), scope=plain(scope), operation_key=operation_key, **authorization)
        return await result if inspect.isawaitable(result) else result

