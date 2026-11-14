"""Mechanical selection of the existing private Homology operation body.

No episode, admission, resources, controller, result or action is constructed
here. The actual source, binding/configuration and operation key are unchanged.
"""


async def operation_for_role(binding, source, name, arguments, *, operation_key):
    from ..homology_job_submission.tool_actions import execute_assigned_operation as launch
    from ..homology_job_monitoring.tool_actions import execute_assigned_operation as monitor
    from ..homology_result_acquisition.tool_actions import execute_assigned_operation as results
    operations = {'job_launch': launch, 'job_monitor': monitor, 'job_results': results}
    return await operations[source.path[-1][0]](binding, source, name, arguments, operation_key=operation_key)
