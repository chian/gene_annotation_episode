"""Continuation: a completion controller toward the credit of the commissioned job.

The target is the total credit of the assignment's progress requirements (read by ``read_from_parent``): the
practical credit sums the currently satisfied requirement keys, so it can never pass that total. The profile (cost
and estimator parameters) is the episode's own entry of ``settings['task_yield_profiles']`` under
``'launch_hpc:' + <request class>``; the request class is classified from the assignment by ``read_from_parent``."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch_hpc:' + parent_input['yield_class']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
