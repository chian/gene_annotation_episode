"""Authenticate the five concrete execution bindings and their shared custody.

This module constructs a literal family and groups its shared read callbacks.
It is not an episode binding, task, execution dispatcher or saved-source alias.
"""
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.communication import plain

FACTORY = 'gene_annotation_episode.episodic_workflow.root.execution_service_setup.ExecutionServiceFactory'
PARENTS = (
    'annotation',
    'scientific_process',
    'hpc_coordination',
    'hpc_coordination/hpc_allocation_execution',
    'scientific_process/hpc_coordination',
    'scientific_process/hpc_coordination/hpc_allocation_execution',
    'published_evidence_assessment',
    'scientific_process/published_evidence_assessment',
)
FAMILIES = {
    'annotation': (
        ('launch', 'execution_job_submission', 'root_execution_job_submission'),
        ('launch_api', 'execution_job_submission/api_job_execution', 'root_execution_job_submission_api_job_execution'),
        ('launch_local', 'execution_job_submission/local_job_execution', 'root_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'execution_job_submission/hpc_job_execution', 'root_execution_job_submission_hpc_job_execution'),
        ('results', 'execution_result_acquisition', 'root_execution_result_acquisition'),
    ),
    'scientific_process': (
        ('launch', 'scientific_process/execution_job_submission', 'root_scientific_process_execution_job_submission'),
        ('launch_api', 'scientific_process/execution_job_submission/api_job_execution', 'root_scientific_process_execution_job_submission_api_job_execution'),
        ('launch_local', 'scientific_process/execution_job_submission/local_job_execution', 'root_scientific_process_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'scientific_process/execution_job_submission/hpc_job_execution', 'root_scientific_process_execution_job_submission_hpc_job_execution'),
        ('results', 'scientific_process/execution_result_acquisition', 'root_scientific_process_execution_result_acquisition'),
    ),
    'hpc_coordination': (
        ('launch', 'hpc_coordination/execution_job_submission', 'root_hpc_coordination_execution_job_submission'),
        ('launch_api', 'hpc_coordination/execution_job_submission/api_job_execution', 'root_hpc_coordination_execution_job_submission_api_job_execution'),
        ('launch_local', 'hpc_coordination/execution_job_submission/local_job_execution', 'root_hpc_coordination_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'hpc_coordination/execution_job_submission/hpc_job_execution', 'root_hpc_coordination_execution_job_submission_hpc_job_execution'),
        ('results', 'hpc_coordination/execution_result_acquisition', 'root_hpc_coordination_execution_result_acquisition'),
    ),
    'hpc_coordination/hpc_allocation_execution': (
        ('launch', 'hpc_coordination/hpc_allocation_execution/execution_job_submission', 'root_hpc_coordination_hpc_allocation_execution_execution_job_submission'),
        ('launch_api', 'hpc_coordination/hpc_allocation_execution/execution_job_submission/api_job_execution', 'root_hpc_coordination_hpc_allocation_execution_execution_job_submission_api_job_execution'),
        ('launch_local', 'hpc_coordination/hpc_allocation_execution/execution_job_submission/local_job_execution', 'root_hpc_coordination_hpc_allocation_execution_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'hpc_coordination/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'root_hpc_coordination_hpc_allocation_execution_execution_job_submission_hpc_job_execution'),
        ('results', 'hpc_coordination/hpc_allocation_execution/execution_result_acquisition', 'root_hpc_coordination_hpc_allocation_execution_execution_result_acquisition'),
    ),
    'scientific_process/hpc_coordination': (
        ('launch', 'scientific_process/hpc_coordination/execution_job_submission', 'root_scientific_process_hpc_coordination_execution_job_submission'),
        ('launch_api', 'scientific_process/hpc_coordination/execution_job_submission/api_job_execution', 'root_scientific_process_hpc_coordination_execution_job_submission_api_job_execution'),
        ('launch_local', 'scientific_process/hpc_coordination/execution_job_submission/local_job_execution', 'root_scientific_process_hpc_coordination_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'scientific_process/hpc_coordination/execution_job_submission/hpc_job_execution', 'root_scientific_process_hpc_coordination_execution_job_submission_hpc_job_execution'),
        ('results', 'scientific_process/hpc_coordination/execution_result_acquisition', 'root_scientific_process_hpc_coordination_execution_result_acquisition'),
    ),
    'scientific_process/hpc_coordination/hpc_allocation_execution': (
        ('launch', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_job_submission', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission'),
        ('launch_api', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_job_submission/api_job_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission_api_job_execution'),
        ('launch_local', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_job_submission/local_job_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_job_submission/hpc_job_execution', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission_hpc_job_execution'),
        ('results', 'scientific_process/hpc_coordination/hpc_allocation_execution/execution_result_acquisition', 'root_scientific_process_hpc_coordination_hpc_allocation_execution_execution_result_acquisition'),
    ),
    'published_evidence_assessment': (
        ('launch', 'published_evidence_assessment/execution_job_submission', 'root_published_evidence_assessment_execution_job_submission'),
        ('launch_api', 'published_evidence_assessment/execution_job_submission/api_job_execution', 'root_published_evidence_assessment_execution_job_submission_api_job_execution'),
        ('launch_local', 'published_evidence_assessment/execution_job_submission/local_job_execution', 'root_published_evidence_assessment_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'published_evidence_assessment/execution_job_submission/hpc_job_execution', 'root_published_evidence_assessment_execution_job_submission_hpc_job_execution'),
        ('results', 'published_evidence_assessment/execution_result_acquisition', 'root_published_evidence_assessment_execution_result_acquisition'),
    ),
    'scientific_process/published_evidence_assessment': (
        ('launch', 'scientific_process/published_evidence_assessment/execution_job_submission', 'root_scientific_process_published_evidence_assessment_execution_job_submission'),
        ('launch_api', 'scientific_process/published_evidence_assessment/execution_job_submission/api_job_execution', 'root_scientific_process_published_evidence_assessment_execution_job_submission_api_job_execution'),
        ('launch_local', 'scientific_process/published_evidence_assessment/execution_job_submission/local_job_execution', 'root_scientific_process_published_evidence_assessment_execution_job_submission_local_job_execution'),
        ('launch_hpc', 'scientific_process/published_evidence_assessment/execution_job_submission/hpc_job_execution', 'root_scientific_process_published_evidence_assessment_execution_job_submission_hpc_job_execution'),
        ('results', 'scientific_process/published_evidence_assessment/execution_result_acquisition', 'root_scientific_process_published_evidence_assessment_execution_result_acquisition'),
    ),
}
ENTRIES = FAMILIES['annotation']
IDENTIFIERS = tuple(row[2] for parent in PARENTS for row in FAMILIES[parent])


def binding_types(parent='annotation'):
    if parent == 'annotation':
        from .execution_job_submission.episode import ExecutionSubmissionBinding
        from .execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'scientific_process':
        from .scientific_process.execution_job_submission.episode import ExecutionSubmissionBinding
        from .scientific_process.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .scientific_process.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .scientific_process.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .scientific_process.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'hpc_coordination':
        from .hpc_coordination.execution_job_submission.episode import ExecutionSubmissionBinding
        from .hpc_coordination.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .hpc_coordination.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .hpc_coordination.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .hpc_coordination.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'hpc_coordination/hpc_allocation_execution':
        from .hpc_coordination.hpc_allocation_execution.execution_job_submission.episode import ExecutionSubmissionBinding
        from .hpc_coordination.hpc_allocation_execution.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .hpc_coordination.hpc_allocation_execution.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .hpc_coordination.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .hpc_coordination.hpc_allocation_execution.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'scientific_process/hpc_coordination':
        from .scientific_process.hpc_coordination.execution_job_submission.episode import ExecutionSubmissionBinding
        from .scientific_process.hpc_coordination.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .scientific_process.hpc_coordination.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .scientific_process.hpc_coordination.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .scientific_process.hpc_coordination.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'scientific_process/hpc_coordination/hpc_allocation_execution':
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_job_submission.episode import ExecutionSubmissionBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'published_evidence_assessment':
        from .published_evidence_assessment.execution_job_submission.episode import ExecutionSubmissionBinding
        from .published_evidence_assessment.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .published_evidence_assessment.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .published_evidence_assessment.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .published_evidence_assessment.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    if parent == 'scientific_process/published_evidence_assessment':
        from .scientific_process.published_evidence_assessment.execution_job_submission.episode import ExecutionSubmissionBinding
        from .scientific_process.published_evidence_assessment.execution_job_submission.api_job_execution.episode import APIExecutionBinding
        from .scientific_process.published_evidence_assessment.execution_job_submission.local_job_execution.episode import LocalExecutionBinding
        from .scientific_process.published_evidence_assessment.execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
        from .scientific_process.published_evidence_assessment.execution_result_acquisition.episode import ResultAcquisitionBinding
        return (ExecutionSubmissionBinding, APIExecutionBinding, LocalExecutionBinding, HPCExecutionBinding, ResultAcquisitionBinding)
    raise ValueError('root_execution_unknown_commissioning_parent')


def family_entries(parent='annotation'):
    try:
        return FAMILIES[parent]
    except KeyError as error:
        raise ValueError('root_execution_unknown_commissioning_parent') from error


def _validate_members(bindings, *, complete):
    from .execution_episodes import ExecutionEpisodes
    bindings = tuple(bindings)
    if not bindings:
        raise ValueError('root_execution_complete_fixed_family_required')
    declarations = {path: (parent, role, identifier, cls)
                    for parent in PARENTS
                    for (role, path, identifier), cls in zip(family_entries(parent), binding_types(parent))}
    paths = tuple(getattr(binding, 'binding_path', None) for binding in bindings)
    if len(set(paths)) != len(paths) or any(path not in declarations for path in paths):
        raise ValueError('root_execution_complete_fixed_family_required')
    parents = tuple(parent for parent in PARENTS
                    if any(path in paths for _, path, _ in family_entries(parent)))
    if complete and paths != tuple(path for parent in parents for _, path, _ in family_entries(parent)):
        raise ValueError('root_execution_complete_fixed_family_required')
    if any(type(binding) is not declarations[path][3] for binding, path in zip(bindings, paths)):
        raise ValueError('root_execution_complete_fixed_family_required')
    owner = bindings[0].owner
    if type(owner) is not ExecutionEpisodes or any(binding.owner is not owner for binding in bindings):
        raise ValueError('root_execution_shared_owner_conflict')
    configuration = owner.as_record()['configuration']
    for binding, path in zip(bindings, paths):
        parent, role, identifier, cls = declarations[path]
        if (binding.services is not owner.services or binding.store is not owner.store
                or binding.tool_registry is not owner.tool_registry
                or binding.run_id != owner.run_id or binding.directory != owner.directory):
            raise ValueError('root_execution_binding_owner_ports_conflict')
        expected = {'binding_id': identifier, 'version': identifier + '_v1',
                    'configuration': configuration}
        entries = (role,) if parent == 'annotation' and role in {'launch', 'results'} else ()
        parent_path = parent if role in {'launch', 'results'} else family_entries(parent)[0][1]
        if (binding.roles != (role,) or binding.entry_roles != entries
                or binding.commissioning_parent != parent_path
                or canonical(binding.as_record()) != canonical(expected)):
            raise ValueError('root_execution_fixed_descriptor_conflict')
    return owner


def validate_family(bindings):
    """Authenticate complete selected parent groups with one genuine custody owner."""
    return _validate_members(bindings, complete=True)


def construct_family(descriptors, services, *, store, run_id, directory, tool_registry):
    """Reopen only the complete private parent groups actually saved."""
    selected = [value for value in descriptors if value.get('binding_id') in IDENTIFIERS]
    if not selected:
        return ()
    parents = tuple(parent for parent in PARENTS
                    if any(value.get('binding_id') in {row[2] for row in family_entries(parent)}
                           for value in selected))
    entries = tuple(row for parent in parents for row in family_entries(parent))
    if len(selected) != len(entries):
        raise ValueError('root_execution_complete_descriptor_family_required')
    configuration = selected[0].get('configuration')
    if type(configuration) is not dict:
        raise ValueError('root_execution_configuration_required')
    for descriptor, (_, _, identifier) in zip(selected, entries):
        expected = {'binding_id': identifier, 'version': identifier + '_v1',
                    'configuration': configuration}
        if canonical(descriptor) != canonical(expected):
            raise ValueError('root_execution_descriptor_family_conflict')
    from .execution_episodes import ExecutionEpisodes
    from .execution_binding_catalogue import execution_bindings
    owner = ExecutionEpisodes(services, store=store, run_id=run_id,
        directory=directory, tool_registry=tool_registry, **configuration)
    bindings = execution_bindings(owner, parents=parents)
    validate_family(bindings)
    if canonical([binding.as_record() for binding in bindings]) != canonical(selected):
        raise ValueError('root_execution_reconstructed_descriptor_conflict')
    return bindings


def is_execution_binding(binding):
    """Recognize literal Root classes; equal axis-relative paths are unrelated."""
    return any(type(binding) is cls for parent in PARENTS for cls in binding_types(parent))


def custody_bindings(bindings):
    """Keep one original custody callback for selected actual lineage members.

    A registry lineage is intentionally a subset of the registered family. Each
    selected member still has its exact concrete class, identity and owner ports
    checked; full family completeness is checked at construction/restoration.
    """
    bindings = tuple(bindings)
    selected = [binding for binding in bindings if is_execution_binding(binding)]
    if not selected:
        return bindings
    owner = _validate_members(selected, complete=False)
    result = []
    emitted = False
    for binding in bindings:
        if any(binding is item for item in selected):
            if not emitted:
                result.append(owner)
                emitted = True
        else:
            result.append(binding)
    return tuple(result)


def factory_execution_configuration(factory):
    """The complete original execution-constructor operands for saved reopening."""
    from .execution_service_setup import ExecutionServiceFactory
    if type(factory) is not ExecutionServiceFactory:
        raise TypeError('root_execution_factory_required')
    return {
        'resources': plain(factory.resources),
        'initial_information': plain(factory.initial_information),
        'handoff_unit': factory.handoff_unit,
        'acquired_record_unit': factory.acquired_record_unit,
        'log_window_bytes': factory.log_window_bytes,
        'log_roles': factory.log_roles,
        'require_private_yield': factory.require_private_execution_yield,
        'results_yield_profiles': (plain(factory.results_yield_profiles)
            if factory.results_yield_profiles is not None else None),
        'task_yield_profiles': (plain(factory.task_yield_profiles)
            if factory.task_yield_profiles is not None else None),
    }




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
        raise ValueError('root_execution_complete_descriptor_family_required')
    return parents


