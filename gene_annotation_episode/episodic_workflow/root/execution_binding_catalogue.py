"""Construct concrete Execution parent families and select their actual contexts."""
from .execution_job_submission.episode import ExecutionSubmissionBinding
from .execution_job_submission.api_job_execution.episode import APIExecutionBinding
from .execution_job_submission.local_job_execution.episode import LocalExecutionBinding
from .execution_job_submission.hpc_job_execution.episode import HPCExecutionBinding
from .execution_result_acquisition.episode import ResultAcquisitionBinding


def execution_bindings(owner, *, parents=('annotation',)):
    from .execution_family_composition import PARENTS, binding_types, validate_family
    parents = tuple(parents)
    if not parents or parents != tuple(parent for parent in PARENTS if parent in parents):
        raise ValueError('root_execution_complete_fixed_family_required')
    bindings = tuple(cls(owner) for parent in parents for cls in binding_types(parent))
    validate_family(bindings)
    owner._private_execution_bindings = bindings
    return bindings


def registered_binding_for_context(bindings, context):
    from .predefined_parent_routes import binding_for_context as selected_binding
    binding = selected_binding(bindings, context)
    if binding is None:
        raise ValueError('unknown_execution_episode_role')
    if context.run_id != binding.run_id:
        raise ValueError('execution_custody_run_conflict')
    return binding


def project_credit(bindings, context, receiver_selection):
    """Call the concrete saved/commissioned parent's original credit method."""
    return registered_binding_for_context(bindings, context).project_credit(context, receiver_selection)


def binding_for_context(owner, context):
    if context.run_id != owner.run_id:
        raise ValueError('execution_custody_run_conflict')
    bindings = getattr(owner, '_private_execution_bindings', None)
    if bindings is not None:
        return registered_binding_for_context(bindings, context)
    # Original direct construction of custody has no registered private family.
    # Preserve its original role adapter instead of claiming a new saved group.
    if context.role == 'launch':
        return ExecutionSubmissionBinding(owner)
    if context.role == 'launch_api':
        return APIExecutionBinding(owner)
    if context.role == 'launch_local':
        return LocalExecutionBinding(owner)
    if context.role == 'launch_hpc':
        return HPCExecutionBinding(owner)
    if context.role == 'results':
        return ResultAcquisitionBinding(owner)
    raise ValueError('unknown_execution_episode_role')


def native_resource_for_context(owner, context, resource_id, fallback):
    """Select actual registered Native policy; keep unregistered custody fallback.

    The caller already performed its original assignment validation and exact
    configured-resource lookup. This chooses code ownership only; no transport,
    cache, action identity, permission or resource configuration is created.
    """
    bindings = getattr(owner, '_private_execution_bindings', None)
    if bindings is None or context.role not in ('launch_local', 'launch_hpc'):
        return fallback
    from .predefined_parent_routes import binding_for_path
    binding = binding_for_path(bindings, context.path)
    if binding is None or binding.roles != (context.role,):
        return fallback
    return binding._native_resource_owners.get(resource_id, fallback)
