"""Original caller-owned scientific credit for this actual legacy parent."""
from .from_parent import validate_path


def credit_projector(workflow, context):
    validate_path(context.path)
    if len(context.path) == 1:
        return workflow.project_credit
    raise ValueError('scientific_task_credit_not_declared:' + context.role)


def credit_binding(workflow, source):
    validate_path(source.path)
    if len(source.path) == 1:
        return workflow.credit_binding
    raise ValueError('scientific_task_credit_not_declared:' + source.path[-1][0])


def credit_view(workflow, source, *, binding_snapshot=None):
    validate_path(source.path)
    if binding_snapshot is not None and type(binding_snapshot) is not dict:
        raise TypeError('credit_binding_snapshot_must_be_dict')
    projector = credit_projector(workflow, workflow.binding_context(source))
    result = workflow.projection_view(projector, source.scope, **workflow.projection_arguments(source))
    if workflow.native_timing_information is not None:
        native = workflow.native_timing_information(workflow.store, source.scope, **workflow.native_timing_arguments(source))
        previous = result.get('monitoring_information_credit')
        previous_binding = result.get('monitoring_information_binding')
        binding = native['monitoring_information_binding']
        if previous is not None:
            binding = {'kind': 'execution_information_components', 'selected_observations': previous_binding, 'received_native_durations': binding}
        result.update(monitoring_information_credit=(previous or 0) + native['monitoring_information_credit'], monitoring_information_binding=binding)
    return result

