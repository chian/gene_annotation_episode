"""Continuation: a completion controller. The episode is complete exactly when the requirement credit the
assignment declares is reached (the old estimator gave exact zero expected future gain once the completion proof
verified; the number it had no longer exists, so the target is the assignment's total requirement credit, from
``read_from_parent``). The cost and the estimator parameters are those of this request's own profile
``launch_local:<class>`` in the episode's settings; a missing profile raises."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch_local:' + parent_input['yield_class']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return CompletionYieldController('local_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
