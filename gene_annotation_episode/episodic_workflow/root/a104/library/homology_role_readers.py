"""Select existing private Homology goal/tool-contract readers by their public role.

This compatibility interface performs no action, admission, task construction or
credit projection. The complete role-specific bodies live in their own homes.
"""


def goal_instructions(role, has_information_channel):
    from ..homology_job_submission.goal import compose_goal as launch
    from ..homology_job_monitoring.goal import compose_goal as monitor
    from ..homology_result_acquisition.goal import compose_goal as results
    readers = {'job_launch': launch, 'job_monitor': monitor, 'job_results': results}
    return readers[role](role, has_information_channel)


def tool_catalog(role):
    from ..homology_job_submission.tool_actions import tool_contracts as launch
    from ..homology_job_monitoring.tool_actions import tool_contracts as monitor
    from ..homology_result_acquisition.tool_actions import tool_contracts as results
    readers = {'job_launch': launch, 'job_monitor': monitor, 'job_results': results}
    return readers[role]()
