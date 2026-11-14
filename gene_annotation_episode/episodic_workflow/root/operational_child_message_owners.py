"""Select actual predefined operational parent/child message owners."""


def _registered_child(registry, parent_source, role, owner):
    return _cached_child(registry, parent_source, role, owner)


def exchange_for_child(workflow, source, role, *, owner=None):
    _nominal = _selector_context(workflow, source, role, owner)
    if _nominal is None:
        return None
    registry, path = _nominal
    if role not in ('launch', 'launch_api', 'launch_local', 'launch_hpc', 'results', 'hpc', 'hpc_prediction', 'hpc_execution'):
        return None
    parent = _cached_parent(registry, source, path)
    from .execution_job_submission.episode import ExecutionSubmissionBinding as Parent_execution_job_submission
    from .hpc_coordination.episode import HPCCoordinationEpisodes as Parent_hpc_coordination
    from .hpc_coordination.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_hpc_coordination_execution_job_submission
    from .hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_hpc_coordination_hpc_allocation_execution
    from .hpc_coordination.hpc_allocation_execution.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_hpc_coordination_hpc_allocation_execution_execution_job_submission
    from .hpc_coordination.hpc_allocation_execution.resource_job_submission.episode import ResourceSubmissionBinding as Parent_hpc_coordination_hpc_allocation_execution_resource_job_submission
    from .hpc_coordination.resource_job_submission.episode import ResourceSubmissionBinding as Parent_hpc_coordination_resource_job_submission
    from .legacy_annotation.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_legacy_annotation_execution_job_submission
    from .legacy_annotation.hpc_coordination.episode import HPCCoordinationEpisodes as Parent_legacy_annotation_hpc_coordination
    from .legacy_annotation.hpc_coordination.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_legacy_annotation_hpc_coordination_execution_job_submission
    from .legacy_annotation.hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution
    from .legacy_annotation.hpc_coordination.hpc_allocation_execution.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution_execution_job_submission
    from .legacy_annotation.hpc_coordination.hpc_allocation_execution.resource_job_submission.episode import ResourceSubmissionBinding as Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution_resource_job_submission
    from .legacy_annotation.hpc_coordination.resource_job_submission.episode import ResourceSubmissionBinding as Parent_legacy_annotation_hpc_coordination_resource_job_submission
    from .legacy_annotation.resource_job_submission.episode import ResourceSubmissionBinding as Parent_legacy_annotation_resource_job_submission
    from .resource_job_submission.episode import ResourceSubmissionBinding as Parent_resource_job_submission
    from .scientific_process.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_scientific_process_execution_job_submission
    from .scientific_process.hpc_coordination.episode import HPCCoordinationEpisodes as Parent_scientific_process_hpc_coordination
    from .scientific_process.hpc_coordination.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_scientific_process_hpc_coordination_execution_job_submission
    from .scientific_process.hpc_coordination.hpc_allocation_execution.episode import HPCAllocationExecutionEpisodes as Parent_scientific_process_hpc_coordination_hpc_allocation_execution
    from .scientific_process.hpc_coordination.hpc_allocation_execution.execution_job_submission.episode import ExecutionSubmissionBinding as Parent_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission
    from .scientific_process.hpc_coordination.hpc_allocation_execution.resource_job_submission.episode import ResourceSubmissionBinding as Parent_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission
    from .scientific_process.hpc_coordination.resource_job_submission.episode import ResourceSubmissionBinding as Parent_scientific_process_hpc_coordination_resource_job_submission
    from .scientific_process.resource_job_submission.episode import ResourceSubmissionBinding as Parent_scientific_process_resource_job_submission
    if any((type(parent) is _expected_type for _expected_type in (Parent_execution_job_submission, Parent_hpc_coordination, Parent_hpc_coordination_execution_job_submission, Parent_hpc_coordination_hpc_allocation_execution, Parent_hpc_coordination_hpc_allocation_execution_execution_job_submission, Parent_hpc_coordination_hpc_allocation_execution_resource_job_submission, Parent_hpc_coordination_resource_job_submission, Parent_legacy_annotation_execution_job_submission, Parent_legacy_annotation_hpc_coordination, Parent_legacy_annotation_hpc_coordination_execution_job_submission, Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution, Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution_execution_job_submission, Parent_legacy_annotation_hpc_coordination_hpc_allocation_execution_resource_job_submission, Parent_legacy_annotation_hpc_coordination_resource_job_submission, Parent_legacy_annotation_resource_job_submission, Parent_resource_job_submission, Parent_scientific_process_execution_job_submission, Parent_scientific_process_hpc_coordination, Parent_scientific_process_hpc_coordination_execution_job_submission, Parent_scientific_process_hpc_coordination_hpc_allocation_execution, Parent_scientific_process_hpc_coordination_hpc_allocation_execution_execution_job_submission, Parent_scientific_process_hpc_coordination_hpc_allocation_execution_resource_job_submission, Parent_scientific_process_hpc_coordination_resource_job_submission, Parent_scientific_process_resource_job_submission))):
        child = _registered_child(registry, _plain_field(parent, 'binding_path'), role, owner)
        return _declared_exchange(parent, role, child_binding=child)
    if _implicit_parent(source, path) == 'annotation':
        child = _registered_child(registry, 'annotation', role, owner)
        if role == 'hpc':
            from .hpc_coordination.episode import HPCCoordinationEpisodes
            if type(child) is HPCCoordinationEpisodes:
                from .to_child_hpc_coordination import prepare_request
                from .from_child_hpc_coordination import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .execution_job_submission.episode import ExecutionSubmissionBinding
            if type(child) is ExecutionSubmissionBinding:
                from .to_child_execution_job_submission import prepare_request
                from .from_child_execution_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .execution_result_acquisition.episode import ResultAcquisitionBinding
            if type(child) is ResultAcquisitionBinding:
                from .to_child_execution_result_acquisition import prepare_request
                from .from_child_execution_result_acquisition import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .resource_job_submission.episode import ResourceSubmissionBinding
            if type(child) is ResourceSubmissionBinding:
                from .to_child_resource_job_submission import prepare_request
                from .from_child_resource_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .resource_result_acquisition.episode import ResourceAcquisitionBinding
            if type(child) is ResourceAcquisitionBinding:
                from .to_child_resource_result_acquisition import prepare_request
                from .from_child_resource_result_acquisition import admit_return
                return (prepare_request, admit_return)
        return None
    if _implicit_parent(source, path) == 'legacy_annotation' and 'improvement' not in _declared_roles(registry):
        child = _registered_child(registry, 'legacy_annotation', role, owner)
        if role == 'hpc':
            from .legacy_annotation.hpc_coordination.episode import HPCCoordinationEpisodes
            if type(child) is HPCCoordinationEpisodes:
                from .legacy_annotation.to_child_hpc_coordination import prepare_request
                from .legacy_annotation.from_child_hpc_coordination import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .legacy_annotation.execution_job_submission.episode import ExecutionSubmissionBinding
            if type(child) is ExecutionSubmissionBinding:
                from .legacy_annotation.to_child_execution_job_submission import prepare_request
                from .legacy_annotation.from_child_execution_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .legacy_annotation.execution_result_acquisition.episode import ResultAcquisitionBinding
            if type(child) is ResultAcquisitionBinding:
                from .legacy_annotation.to_child_execution_result_acquisition import prepare_request
                from .legacy_annotation.from_child_execution_result_acquisition import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .legacy_annotation.resource_job_submission.episode import ResourceSubmissionBinding
            if type(child) is ResourceSubmissionBinding:
                from .legacy_annotation.to_child_resource_job_submission import prepare_request
                from .legacy_annotation.from_child_resource_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .legacy_annotation.resource_result_acquisition.episode import ResourceAcquisitionBinding
            if type(child) is ResourceAcquisitionBinding:
                from .legacy_annotation.to_child_resource_result_acquisition import prepare_request
                from .legacy_annotation.from_child_resource_result_acquisition import admit_return
                return (prepare_request, admit_return)
        return None
    if path[-1][0] == 'scientific_process':
        from .scientific_process.episode import ScientificProcessEpisodes
        if type(parent) is not ScientificProcessEpisodes:
            return None
        child = _registered_child(registry, 'scientific_process', role, owner)
        if role == 'hpc':
            from .scientific_process.hpc_coordination.episode import HPCCoordinationEpisodes
            if type(child) is HPCCoordinationEpisodes:
                from .scientific_process.to_child_hpc_coordination import prepare_request
                from .scientific_process.from_child_hpc_coordination import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .scientific_process.execution_job_submission.episode import ExecutionSubmissionBinding
            if type(child) is ExecutionSubmissionBinding:
                from .scientific_process.to_child_execution_job_submission import prepare_request
                from .scientific_process.from_child_execution_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .scientific_process.execution_result_acquisition.episode import ResultAcquisitionBinding
            if type(child) is ResultAcquisitionBinding:
                from .scientific_process.to_child_execution_result_acquisition import prepare_request
                from .scientific_process.from_child_execution_result_acquisition import admit_return
                return (prepare_request, admit_return)
        if role == 'launch':
            from .scientific_process.resource_job_submission.episode import ResourceSubmissionBinding
            if type(child) is ResourceSubmissionBinding:
                from .scientific_process.to_child_resource_job_submission import prepare_request
                from .scientific_process.from_child_resource_job_submission import admit_return
                return (prepare_request, admit_return)
        if role == 'results':
            from .scientific_process.resource_result_acquisition.episode import ResourceAcquisitionBinding
            if type(child) is ResourceAcquisitionBinding:
                from .scientific_process.to_child_resource_result_acquisition import prepare_request
                from .scientific_process.from_child_resource_result_acquisition import admit_return
                return (prepare_request, admit_return)
        return None
    return None

from .library.nominal_child_messages import (selector_context as _selector_context, cached_parent as _cached_parent, registered_child as _cached_child, declared_roles as _declared_roles, declared_exchange as _declared_exchange, homology_child_path as _homology_child_path, implicit_parent as _implicit_parent, _plain_field, _static)
