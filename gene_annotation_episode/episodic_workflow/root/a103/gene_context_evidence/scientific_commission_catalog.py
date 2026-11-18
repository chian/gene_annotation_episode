"""Scientific owner's declared private commission operations; no invocation grant.

No source-library entry, inferred capability or global role identifies a route.
Only registered direct entry owners and their declared native children do so.
"""
from ..resource_tool_information import _contract, _RESOURCE_ROLES
from importlib import import_module

PACKAGE='gene_annotation_episode.episodic_workflow.root.a103'
OWNERS={
    'gene_context_evidence':('legacy_annotation','gene_context_evidence','GeneContextEvidenceEpisode'),
    'gene_context_evidence/resource_work_submission':('gene_context_evidence','launch','ResourceEpisode'),
    'gene_context_evidence/resource_result_acquisition':('gene_context_evidence','results','ResourceEpisode'),
    'gene_context_evidence/execution_job_submission':('gene_context_evidence','launch','ExecutionEpisode'),
    'gene_context_evidence/execution_result_acquisition':('gene_context_evidence','results','ExecutionEpisode'),
    'gene_context_evidence/execution_job_submission/api_job_execution':('gene_context_evidence/execution_job_submission','launch_api','ExecutionEpisode'),
    'gene_context_evidence/execution_job_submission/local_job_execution':('gene_context_evidence/execution_job_submission','launch_local','ExecutionEpisode'),
    'gene_context_evidence/execution_job_submission/hpc_job_execution':('gene_context_evidence/execution_job_submission','launch_hpc','ExecutionEpisode'),
}


def _declarations(binding):
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
        for binding_route in route['routes']:
            if (not isinstance(binding_route, dict)
                    or set(binding_route) != {'entry_role', 'resource_id', 'resource_role'}
                    or binding_route['entry_role'] not in {'launch', 'results'}
                    or not isinstance(binding_route['resource_id'], str) or not binding_route['resource_id']
                    or binding_route['resource_role'] != ('results' if binding_route['entry_role'] == 'results'
                                                 else _RESOURCE_ROLES[row['resources']])
                    or binding_route['resource_id'] not in binding.resources):
                raise ValueError('resource_tool_information_binding_invalid')
            if binding_route in routes:
                raise ValueError('resource_tool_information_route_duplicate')
            routes.append(binding_route)
        rows.append(row)
    return rows


def _registered(registry, binding):
    path = getattr(binding, 'binding_path', None)
    if not isinstance(path, str) or path not in OWNERS or registry.for_binding_path(path) is not binding:
        raise ValueError('resource_tool_information_binding_invalid')
    parent,role,classname=OWNERS[path]
    if (type(binding) is not getattr(import_module(PACKAGE+'.'+path.replace('/','.')+'.episode'),classname)
            or binding.commissioning_parent!=parent or binding.roles!=(role,)):
        raise ValueError('resource_tool_information_binding_invalid')


def resource_information_catalog(scientific, registry):
    """Describe only the actual scientific owner's registered commission edges.

    This intentionally filters well-formed copied foreign entry routes. It
    retains every original schema/duplicate/malformed-route check before that
    filter. Native routes additionally require the actual separate child's own
    matching declaration and exact selected resource configuration.
    """
    _registered(registry, scientific)
    resources, declarations = [], {}
    children = scientific.child_roles('gene_context_evidence')
    # The original catalogue ultimately sorts names/resources. Direct entry
    # order follows this owner's original declared child-role order.
    for entry_role in children:
        if entry_role not in {'launch', 'results'}:
            continue
        if entry_role not in registry.roles:
            continue
        binding = registry._child_binding(scientific, entry_role)
        _registered(registry, binding)
        # A direct private child need not advertise itself as a root entry.
        # The actual scientific parent's declared edge selected this owner.
        if entry_role not in binding.roles:
            raise ValueError('resource_tool_information_binding_invalid')
        if id(binding) not in declarations:
            declarations[id(binding)] = _declarations(binding)
        rows = declarations[id(binding)]
        for row in rows:
            selected = []
            for route in row['invocation_route']['routes']:
                if route['entry_role'] != entry_role:
                    continue
                resource_id, resource_role = route['resource_id'], route['resource_role']
                if entry_role == 'results':
                    child = binding
                else:
                    if resource_role not in binding.child_roles(entry_role):
                        raise ValueError('resource_tool_information_binding_invalid')
                    child = registry._child_binding(binding, resource_role)
                    _registered(registry, child)
                if (resource_role not in child.roles or resource_id not in child.resources
                        or child.resources[resource_id] != binding.resources[resource_id]):
                    raise ValueError('resource_tool_information_binding_invalid')
                if child is not binding:
                    if id(child) not in declarations:
                        declarations[id(child)] = _declarations(child)
                    matching = [candidate for candidate in declarations[id(child)]
                        if (candidate['name'], candidate['resources']) == (row['name'], row['resources'])
                        and route in candidate['invocation_route']['routes']]
                    if (len(matching) != 1
                            or {k:v for k,v in matching[0].items() if k!='invocation_route'}
                            != {k:v for k,v in row.items() if k!='invocation_route'}):
                        raise ValueError('resource_tool_information_binding_conflict:' + row['name'])
                selected.append(route)
            if selected:
                resources.append({**row, 'invocation_route': {'kind': 'commission', 'routes': selected}})
    return resources
