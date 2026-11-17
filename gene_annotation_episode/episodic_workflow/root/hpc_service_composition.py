"""Authenticate concrete HPC families beneath each original Root parent."""
from gene_annotation_episode.execution_contracts import canonical

PARENTS = ('annotation', 'scientific_process')
VERSION = 'root_hpc_private_v1'
FAMILIES = {
    'annotation': (
        ('hpc', 'hpc_coordination', 'hpc'),
        ('hpc_prediction', 'hpc_coordination/hpc_resource_prediction', 'hpc_prediction'),
        ('hpc_execution', 'hpc_coordination/hpc_allocation_execution', 'hpc_execution'),
    ),
    'scientific_process': (
        ('hpc', 'scientific_process/hpc_coordination', 'root_scientific_process_hpc_coordination'),
        ('hpc_prediction', 'scientific_process/hpc_coordination/hpc_resource_prediction', 'root_scientific_process_hpc_coordination_hpc_resource_prediction'),
        ('hpc_execution', 'scientific_process/hpc_coordination/hpc_allocation_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution'),
    ),
}
ENTRIES = tuple((role, path) for role, path, _ in FAMILIES['annotation'])
IDENTIFIERS = tuple(row[2] for parent in PARENTS for row in FAMILIES[parent])


def binding_types(parent='annotation'):
    if parent == 'annotation':
        from .hpc_coordination.episode import HPCCoordinationEpisodes
        from .hpc_coordination.hpc_resource_prediction.episode import HPCResourcePredictionEpisodes
        from .hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes
        return (HPCCoordinationEpisodes, HPCResourcePredictionEpisodes, HPCAllocationExecutionEpisodes)
    if parent == 'scientific_process':
        from .scientific_process.hpc_coordination.episode import HPCCoordinationEpisodes
        from .scientific_process.hpc_coordination.hpc_resource_prediction.episode import HPCResourcePredictionEpisodes
        from .scientific_process.hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes
        return (HPCCoordinationEpisodes, HPCResourcePredictionEpisodes, HPCAllocationExecutionEpisodes)
    raise ValueError('root_hpc_unknown_commissioning_parent')


def family_entries(parent='annotation'):
    try:
        return FAMILIES[parent]
    except KeyError as error:
        raise ValueError('root_hpc_unknown_commissioning_parent') from error


def validate_family(bindings):
    bindings = tuple(bindings)
    declarations = {path: (parent, role, identifier, cls)
                    for parent in PARENTS
                    for (role, path, identifier), cls in zip(family_entries(parent), binding_types(parent))}
    paths = tuple(getattr(binding, 'binding_path', None) for binding in bindings)
    if (not bindings or len(set(paths)) != len(paths)
            or any(path not in declarations for path in paths)
            or any(type(binding) is not declarations[path][3] for binding, path in zip(bindings, paths))):
        raise ValueError('root_hpc_complete_fixed_family_required')
    parents = tuple(parent for parent in PARENTS
                    if any(path in paths for _, path, _ in family_entries(parent)))
    if paths != tuple(path for parent in parents for _, path, _ in family_entries(parent)):
        raise ValueError('root_hpc_complete_fixed_family_required')
    first = bindings[0]
    configuration = first.as_record()['configuration']
    for binding, path in zip(bindings, paths):
        parent, role, identifier, cls = declarations[path]
        record = binding.as_record()
        entries = ('hpc',) if parent == 'annotation' and role == 'hpc' else ()
        parent_path = parent if role == 'hpc' else family_entries(parent)[0][1]
        if (binding.roles != (role,) or binding.entry_roles != entries
                or binding.commissioning_parent != parent_path
                or record.get('binding_id') != identifier or record.get('version') != VERSION
                or canonical(record.get('configuration')) != canonical(configuration)
                or binding.services is not first.services or binding.store is not first.store
                or binding.run_id != first.run_id or binding.directory != first.directory):
            raise ValueError('root_hpc_fixed_family_conflict')
    return first


def hpc_bindings(services, *, store, run_id, directory, resources, commissions,
                 shared_execution_memory=None, require_commission_yield=False,
                 parents=('annotation',)):
    parents = tuple(parents)
    if not parents or parents != tuple(parent for parent in PARENTS if parent in parents):
        raise ValueError('root_hpc_complete_fixed_family_required')
    bindings = tuple(cls(services, store=store, run_id=run_id, directory=directory,
        resources=resources, commissions=commissions,
        shared_execution_memory=shared_execution_memory,
        require_commission_yield=require_commission_yield)
        for parent in parents for cls in binding_types(parent))
    validate_family(bindings)
    return bindings


def construct_family(descriptors, services, *, store, run_id, directory):
    selected = [value for value in descriptors if value.get('binding_id') in IDENTIFIERS]
    if not selected:
        return ()
    parents = tuple(parent for parent in PARENTS
                    if any(value.get('binding_id') in {row[2] for row in family_entries(parent)}
                           for value in selected))
    entries = tuple(row for parent in parents for row in family_entries(parent))
    if len(selected) != len(entries):
        raise ValueError('root_hpc_complete_descriptor_family_required')
    configuration = selected[0].get('configuration')
    if type(configuration) is not dict:
        raise ValueError('root_hpc_configuration_required')
    for descriptor, (_, _, identifier) in zip(selected, entries):
        if (descriptor.get('binding_id') != identifier or descriptor.get('version') != VERSION
                or canonical(descriptor.get('configuration')) != canonical(configuration)):
            raise ValueError('root_hpc_descriptor_family_conflict')
    bindings = hpc_bindings(services, store=store, run_id=run_id,
        directory=directory, parents=parents, **configuration)
    if canonical([binding.as_record() for binding in bindings]) != canonical(selected):
        raise ValueError('root_hpc_reconstructed_descriptor_conflict')
    return bindings


def project_credit(bindings, context, receiver_selection):
    from .predefined_parent_routes import binding_for_context
    binding = binding_for_context(bindings, context)
    if binding is None:
        raise ValueError('root_hpc_context_not_bound')
    return binding.credit_view(context, receiver_selection)


def descriptor_parents(descriptors):
    """Select complete literal groups from existing descriptors, without expansion."""
    selected = [value for value in descriptors if value.get('binding_id') in IDENTIFIERS]
    if not selected:
        return ()
    parents = tuple(parent for parent in PARENTS
                    if any(value.get('binding_id') in {row[2] for row in family_entries(parent)}
                           for value in selected))
    entries = tuple(row for parent in parents for row in family_entries(parent))
    if [value.get('binding_id') for value in selected] != [entry[2] for entry in entries]:
        raise ValueError('root_hpc_complete_descriptor_family_required')
    return parents


