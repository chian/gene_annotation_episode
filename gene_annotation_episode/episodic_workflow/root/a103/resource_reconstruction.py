"""Reopen only current own-A103 resource descriptors from actual caller operands.

No historical A101/shared descriptor conversion and no capability observation is
performed here. The original composer validates the complete portfolio first,
requires each role's actual credit projector and observes capabilities afterward.
"""
from __future__ import annotations

RESOURCE_BINDINGS = (
    'resource_work_submission',
    'resource_work_submission/api_resource_work_execution',
    'resource_work_submission/local_resource_work_execution',
    'resource_work_submission/hpc_resource_work_execution',
    'resource_result_acquisition',
    'scientific_process/resource_work_submission',
    'scientific_process/resource_work_submission/api_resource_work_execution',
    'scientific_process/resource_work_submission/local_resource_work_execution',
    'scientific_process/resource_work_submission/hpc_resource_work_execution',
    'scientific_process/resource_result_acquisition',
)
RESOURCE_RECONSTRUCTION = {
    name: ('resource_episode_binding_v1', ('resource_adapters',),
           ('contract_information_profile',), True)
    for name in RESOURCE_BINDINGS
}


def validate_resource_portfolio(names, failure):
    # These are alternative service-factory branches for the same parent/role.
    # Distinct source paths must not make an ambiguous mixed portfolio admissible.
    for prefix in ('', 'scientific_process/'):
        for resource, execution in (('resource_work_submission','execution_job_submission'),
                                     ('resource_result_acquisition','execution_result_acquisition')):
            if prefix+resource in names and prefix+execution in names:
                raise failure('identity_conflict', 'episode_bindings')


def reopen_resource_binding(name, configuration, *, services, store, journal,
                            job_episodes, resource_estimator, adapter_cache,
                            failure, same_record):
    # Literal imports preserve actual private class identity and constructor
    # behavior. Their modules load only after the composer and runtime exist.
    if name == 'resource_work_submission':
        from .resource_work_submission.episode import ResourceEpisode as Binding
    elif name == 'resource_work_submission/api_resource_work_execution':
        from .resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'resource_work_submission/local_resource_work_execution':
        from .resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'resource_work_submission/hpc_resource_work_execution':
        from .resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'resource_result_acquisition':
        from .resource_result_acquisition.episode import ResourceEpisode as Binding
    elif name == 'scientific_process/resource_work_submission':
        from .scientific_process.resource_work_submission.episode import ResourceEpisode as Binding
    elif name == 'scientific_process/resource_work_submission/api_resource_work_execution':
        from .scientific_process.resource_work_submission.api_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'scientific_process/resource_work_submission/local_resource_work_execution':
        from .scientific_process.resource_work_submission.local_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'scientific_process/resource_work_submission/hpc_resource_work_execution':
        from .scientific_process.resource_work_submission.hpc_resource_work_execution.episode import ResourceEpisode as Binding
    elif name == 'scientific_process/resource_result_acquisition':
        from .scientific_process.resource_result_acquisition.episode import ResourceEpisode as Binding
    else:
        raise failure('unavailable_binding', name)
    declared = configuration['resource_adapters']
    if not isinstance(declared, list):
        raise failure('unavailable_binding', name)
    selected, new = [], []
    from .a103_homology_resource_adapter import HomologyResourceAdapter
    for descriptor in declared:
        if not isinstance(descriptor, dict) or descriptor.get('version') != 'homology_resource_adapter_v2':
            raise failure('unavailable_binding', name)
        reference = descriptor.get('resource_id')
        reference = reference if isinstance(reference, str) and reference else name
        if job_episodes is None:
            raise failure('unavailable_binding', reference)
        adapter = adapter_cache.get(reference)
        if adapter is None:
            adapter = HomologyResourceAdapter(job_episodes, store, journal, resource_estimator)
            same_record(adapter.as_record(), descriptor, reference)
            adapter_cache[reference] = adapter
            new.append(adapter)
        else:
            same_record(adapter.as_record(), descriptor, reference)
        selected.append(adapter)
    binding = Binding(services, resource_adapters=selected,
        contract_information_profile=configuration.get('contract_information_profile'))
    return binding, new
