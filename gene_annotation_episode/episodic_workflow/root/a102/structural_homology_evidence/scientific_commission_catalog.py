"""A102 scientific owner's actual private commission declarations.

This describes registered direct child contracts. It grants no invocation,
received-input custody, resource reservation or scientific evidence authority.
"""
from importlib import import_module
from ..resource_tool_information import _contract, _RESOURCE_ROLES

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a102'
ENTRIES = {
    ('launch', 'structural_homology_evidence/execution_job_submission'): 'ExecutionEpisode',
    ('results', 'structural_homology_evidence/execution_result_acquisition'): 'ExecutionEpisode',
    ('launch', 'structural_homology_evidence/resource_work_submission'): 'ResourceEpisode',
    ('results', 'structural_homology_evidence/resource_result_acquisition'): 'ResourceEpisode',
}
NATIVE = {
    'launch_api': 'api_job_execution',
    'launch_local': 'local_job_execution',
    'launch_hpc': 'hpc_job_execution',
}


def _declarations(binding):
    # Original own-A102 declaration validation, before filtering any copied
    # foreign entry. Only the two same-binding ownership predicates move to
    # actual parent/child validation below; error literals stay own-A102.
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
                    or owner['resource_id'] not in binding.resources):
                raise ValueError('resource_tool_information_owner_invalid')
            if owner in routes:
                raise ValueError('resource_tool_information_route_duplicate')
            routes.append(owner)
        rows.append(row)
    return rows


def _private(registry, binding, home, parent, role, classname):
    if (registry.for_binding_path(home) is not binding
            or type(binding) is not getattr(import_module(PACKAGE+'.'+home.replace('/', '.')+'.episode'), classname)
            or binding.binding_path != home or binding.commissioning_parent != parent
            or binding.roles != (role,)):
        raise ValueError('resource_tool_information_owner_invalid')
    return binding


def resource_information_catalog(scientific, registry):
    """Only the original scientific owner's own declared direct portfolio."""
    _private(registry, scientific, 'structural_homology_evidence', 'legacy_annotation',
             'structural_homology_evidence', 'StructuralHomologyEvidenceEpisode')
    resources, declarations = [], {}
    for entry_role in scientific.child_roles('structural_homology_evidence'):
        if entry_role not in {'launch', 'results'}:
            continue
        if entry_role not in registry.roles:
            continue
        binding = registry._child_binding(scientific, entry_role)
        home = getattr(binding, 'binding_path', None)
        classname = ENTRIES.get((entry_role, home))
        if classname is None:
            raise ValueError('resource_tool_information_owner_invalid')
        _private(registry, binding, home, 'structural_homology_evidence', entry_role, classname)
        rows = _declarations(binding)
        declarations[home] = rows
        # Resource adapters currently declare no resource_tool_contracts hook.
        # An empty list stays empty; source-library entries cannot fill it.
        for row in rows:
            selected = []
            for route in row['invocation_route']['routes']:
                if route['entry_role'] != entry_role:
                    continue
                resource_id, resource_role = route['resource_id'], route['resource_role']
                child = binding
                if entry_role == 'launch':
                    if resource_role not in binding.child_roles(entry_role):
                        raise ValueError('resource_tool_information_owner_invalid')
                    if home != 'structural_homology_evidence/execution_job_submission':
                        raise ValueError('resource_tool_information_owner_invalid')
                    child_home = home+'/'+NATIVE[resource_role]
                    child = registry._child_binding(binding, resource_role)
                    _private(registry, child, child_home, home, resource_role, 'ExecutionEpisode')
                if (resource_role not in child.roles or resource_id not in child.resources
                        or child.resources[resource_id] != binding.resources[resource_id]):
                    raise ValueError('resource_tool_information_owner_invalid')
                if child is not binding:
                    if child_home not in declarations:
                        declarations[child_home] = _declarations(child)
                    matching = [value for value in declarations[child_home]
                        if (value['name'], value['resources']) == (row['name'], row['resources'])
                        and route in value['invocation_route']['routes']]
                    if (len(matching) != 1 or
                            {k:v for k,v in matching[0].items() if k!='invocation_route'}
                            != {k:v for k,v in row.items() if k!='invocation_route'}):
                        raise ValueError('resource_tool_information_owner_conflict:' + row['name'])
                selected.append(route)
            if selected:
                resources.append({**row, 'invocation_route': {'kind': 'commission', 'routes': selected}})
    return resources
