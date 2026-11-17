"""Construct and authenticate concrete Resource families for each original parent."""
from gene_annotation_episode.execution_contracts import canonical

PARENTS = (
    'annotation',
    'scientific_process',
    'hpc_coordination',
    'hpc_coordination/hpc_allocation_execution',
    'scientific_process/hpc_coordination',
    'scientific_process/hpc_coordination/hpc_allocation_execution',
)
FAMILIES = {
    'annotation': (
        ('launch', 'resource_job_submission', 'root_resource_job_submission'),
        ('launch_api', 'resource_job_submission/api_resource_execution', 'root_resource_job_submission_api_resource_execution'),
        ('launch_local', 'resource_job_submission/local_resource_execution', 'root_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'resource_job_submission/hpc_resource_execution', 'root_resource_job_submission_hpc_resource_execution'),
        ('results', 'resource_result_acquisition', 'root_resource_result_acquisition'),
    ),
    'scientific_process': (
        ('launch', 'scientific_process/resource_job_submission', 'root_scientific_process_resource_job_submission'),
        ('launch_api', 'scientific_process/resource_job_submission/api_resource_execution', 'root_scientific_process_resource_job_submission_api_resource_execution'),
        ('launch_local', 'scientific_process/resource_job_submission/local_resource_execution', 'root_scientific_process_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'scientific_process/resource_job_submission/hpc_resource_execution', 'root_scientific_process_resource_job_submission_hpc_resource_execution'),
        ('results', 'scientific_process/resource_result_acquisition', 'root_scientific_process_resource_result_acquisition'),
    ),
    'hpc_coordination': (
        ('launch', 'hpc_coordination/resource_job_submission', 'root_hpc_coordination_resource_job_submission'),
        ('launch_api', 'hpc_coordination/resource_job_submission/api_resource_execution', 'root_hpc_coordination_resource_job_submission_api_resource_execution'),
        ('launch_local', 'hpc_coordination/resource_job_submission/local_resource_execution', 'root_hpc_coordination_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'hpc_coordination/resource_job_submission/hpc_resource_execution', 'root_hpc_coordination_resource_job_submission_hpc_resource_execution'),
        ('results', 'hpc_coordination/resource_result_acquisition', 'root_hpc_coordination_resource_result_acquisition'),
    ),
    'hpc_coordination/hpc_allocation_execution': (
        ('launch', 'hpc_coordination/hpc_allocation_execution/resource_job_submission', 'root_hpc_coordination_hpc_allocation_execution_resource_job_submission'),
        ('launch_api', 'hpc_coordination/hpc_allocation_execution/resource_job_submission/api_resource_execution', 'root_hpc_coordination_hpc_allocation_execution_resource_job_submission_api_resource_execution'),
        ('launch_local', 'hpc_coordination/hpc_allocation_execution/resource_job_submission/local_resource_execution', 'root_hpc_coordination_hpc_allocation_execution_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'hpc_coordination/hpc_allocation_execution/resource_job_submission/hpc_resource_execution', 'root_hpc_coordination_hpc_allocation_execution_resource_job_submission_hpc_resource_execution'),
        ('results', 'hpc_coordination/hpc_allocation_execution/resource_result_acquisition', 'root_hpc_coordination_hpc_allocation_execution_resource_result_acquisition'),
    ),
    'scientific_process/hpc_coordination': (
        ('launch', 'scientific_process/hpc_coordination/resource_job_submission', 'root_scientific_process_hpc_coordination_resource_job_submission'),
        ('launch_api', 'scientific_process/hpc_coordination/resource_job_submission/api_resource_execution', 'root_scientific_process_hpc_coordination_resource_job_submission_api_resource_execution'),
        ('launch_local', 'scientific_process/hpc_coordination/resource_job_submission/local_resource_execution', 'root_scientific_process_hpc_coordination_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'scientific_process/hpc_coordination/resource_job_submission/hpc_resource_execution', 'root_scientific_process_hpc_coordination_resource_job_submission_hpc_resource_execution'),
        ('results', 'scientific_process/hpc_coordination/resource_result_acquisition', 'root_scientific_process_hpc_coordination_resource_result_acquisition'),
    ),
    'scientific_process/hpc_coordination/hpc_allocation_execution': (
        ('launch', 'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission'),
        ('launch_api', 'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/api_resource_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission_api_resource_execution'),
        ('launch_local', 'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/local_resource_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission_local_resource_execution'),
        ('launch_hpc', 'scientific_process/hpc_coordination/hpc_allocation_execution/resource_job_submission/hpc_resource_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission_hpc_resource_execution'),
        ('results', 'scientific_process/hpc_coordination/hpc_allocation_execution/resource_result_acquisition', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_resource_result_acquisition'),
    ),
}
ENTRIES = FAMILIES['annotation']
IDENTIFIERS = tuple(row[2] for parent in PARENTS for row in FAMILIES[parent])


def binding_types(parent='annotation'):
    if parent == 'annotation':
        from .resource_job_submission.episode import ResourceSubmissionBinding
        from .resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    if parent == 'scientific_process':
        from .scientific_process.resource_job_submission.episode import ResourceSubmissionBinding
        from .scientific_process.resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .scientific_process.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .scientific_process.resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .scientific_process.resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    if parent == 'hpc_coordination':
        from .hpc_coordination.resource_job_submission.episode import ResourceSubmissionBinding
        from .hpc_coordination.resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .hpc_coordination.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .hpc_coordination.resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .hpc_coordination.resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    if parent == 'hpc_coordination/hpc_allocation_execution':
        from .hpc_coordination.hpc_allocation_execution.resource_job_submission.episode import ResourceSubmissionBinding
        from .hpc_coordination.hpc_allocation_execution.resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .hpc_coordination.hpc_allocation_execution.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .hpc_coordination.hpc_allocation_execution.resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .hpc_coordination.hpc_allocation_execution.resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    if parent == 'scientific_process/hpc_coordination':
        from .scientific_process.hpc_coordination.resource_job_submission.episode import ResourceSubmissionBinding
        from .scientific_process.hpc_coordination.resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .scientific_process.hpc_coordination.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .scientific_process.hpc_coordination.resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .scientific_process.hpc_coordination.resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    if parent == 'scientific_process/hpc_coordination/hpc_allocation_execution':
        from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_job_submission.episode import ResourceSubmissionBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_job_submission.api_resource_execution.episode import APIResourceBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_job_submission.local_resource_execution.episode import LocalResourceBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_job_submission.hpc_resource_execution.episode import HPCResourceBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_result_acquisition.episode import ResourceAcquisitionBinding
        return (ResourceSubmissionBinding, APIResourceBinding, LocalResourceBinding, HPCResourceBinding, ResourceAcquisitionBinding)
    raise ValueError('resource_unknown_commissioning_parent')


class ResourceDescriptorMismatch(ValueError):
    """The genuine reconstructed family differs from its supplied saved record."""
    def __init__(self, message, reference):
        super().__init__(message)
        self.reference = reference


def family_entries(parent='annotation'):
    try:
        return FAMILIES[parent]
    except KeyError as error:
        raise ValueError('resource_unknown_commissioning_parent') from error


def resource_bindings(owner, *, parents=('annotation',)):
    parents = tuple(parents)
    if not parents or parents != tuple(parent for parent in PARENTS if parent in parents):
        raise ValueError('resource_complete_fixed_family_required')
    bindings = tuple(cls(owner) for parent in parents for cls in binding_types(parent))
    validate_family(bindings)
    return bindings


def _validate_members(bindings, *, complete):
    from .resource_episodes import ResourceEpisodes
    bindings = tuple(bindings)
    declarations = {path: (parent, role, identifier, cls)
                    for parent in PARENTS
                    for (role, path, identifier), cls in zip(family_entries(parent), binding_types(parent))}
    paths = tuple(getattr(binding, 'binding_path', None) for binding in bindings)
    if (not bindings or len(set(paths)) != len(paths)
            or any(path not in declarations for path in paths)
            or any(type(binding) is not declarations[path][3] for binding, path in zip(bindings, paths))):
        raise ValueError('resource_complete_fixed_family_required')
    parents = tuple(parent for parent in PARENTS
                    if any(path in paths for _, path, _ in family_entries(parent)))
    if complete and paths != tuple(path for parent in parents for _, path, _ in family_entries(parent)):
        raise ValueError('resource_complete_fixed_family_required')
    owner = bindings[0].owner
    if type(owner) is not ResourceEpisodes:
        raise ValueError('resource_genuine_custody_required')
    configuration = owner.configuration()
    for binding, path in zip(bindings, paths):
        parent, role, identifier, cls = declarations[path]
        entries = (role,) if parent == 'annotation' and role in ('launch', 'results') else ()
        parent_path = parent if role in ('launch', 'results') else family_entries(parent)[0][1]
        if (binding.owner is not owner or binding.adapters is not owner.adapters
                or binding.services is not owner.services
                or binding._contract_information_profile != owner._contract_information_profile
                or binding.roles != (role,) or binding.entry_roles != entries
                or binding.commissioning_parent != parent_path):
            raise ValueError('resource_fixed_family_identity_conflict')
        record = binding.as_record()
        if (record['binding_id'] != identifier or record['version'] != identifier + '_v1'
                or canonical(record['configuration']) != canonical(configuration)):
            raise ValueError('resource_fixed_descriptor_conflict')
    return owner


def validate_family(bindings):
    return _validate_members(bindings, complete=True)


def saved_family(descriptors):
    selected = [value for value in descriptors if value.get('binding_id') in IDENTIFIERS]
    if not selected:
        return ()
    parents = tuple(parent for parent in PARENTS
                    if any(value.get('binding_id') in {row[2] for row in family_entries(parent)}
                           for value in selected))
    entries = tuple(row for parent in parents for row in family_entries(parent))
    if len(selected) != len(entries):
        raise ValueError('resource_complete_saved_family_required')
    configuration = selected[0].get('configuration')
    if (type(configuration) is not dict or not {'resource_adapters'} <= set(configuration) <=
            {'resource_adapters', 'contract_information_profile'}
            or not isinstance(configuration['resource_adapters'], list)):
        raise ValueError('resource_saved_configuration_required')
    for record, (_, _, identifier) in zip(selected, entries):
        expected = {'binding_id': identifier, 'version': identifier + '_v1', 'configuration': configuration}
        if canonical(record) != canonical(expected):
            raise ResourceDescriptorMismatch('resource_saved_family_conflict', identifier)
    return tuple(selected)


def construct_family(descriptors, services, *, resource_adapters):
    selected = saved_family(descriptors)
    if not selected:
        return ()
    from .resource_episodes import ResourceEpisodes
    configuration = selected[0]['configuration']
    adapters = tuple(resource_adapters)
    if canonical([adapter.as_record() for adapter in adapters]) != canonical(configuration['resource_adapters']):
        raise ValueError('resource_saved_adapter_identity_conflict')
    owner = ResourceEpisodes(services, resource_adapters=adapters,
        contract_information_profile=configuration.get('contract_information_profile'))
    parents = tuple(parent for parent in PARENTS
                    if any(value['binding_id'] in {row[2] for row in family_entries(parent)}
                           for value in selected))
    bindings = resource_bindings(owner, parents=parents)
    for binding, descriptor in zip(bindings, selected):
        if canonical(binding.as_record()) != canonical(descriptor):
            raise ResourceDescriptorMismatch('resource_reconstructed_descriptor_conflict', descriptor['binding_id'])
    return bindings


def is_resource_binding(binding):
    """Recognize literal Root classes; equal axis-relative paths are unrelated."""
    return any(type(binding) is cls for parent in PARENTS for cls in binding_types(parent))


def custody_bindings(bindings):
    bindings = tuple(bindings)
    selected = [binding for binding in bindings if is_resource_binding(binding)]
    if not selected:
        return bindings
    owner = _validate_members(selected, complete=False)
    result, emitted = [], False
    for binding in bindings:
        if any(binding is item for item in selected):
            if not emitted:
                result.append(owner)
                emitted = True
        else:
            result.append(binding)
    return tuple(result)


