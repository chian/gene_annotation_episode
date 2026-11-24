"""Continuation: credit toward the commissioned requirements.

The old controller was a ``YieldController`` with an endpoint estimator that gave zero further gain once a recorded
completion proof verified (``PracticalYieldEstimator``). README 7b maps it to the completion controller. Its target
comes from ``parent_input``: the credit the commissioned requirements add up to (``read_from_parent``). The profile
(cost and parameters) is the old one of the request class, ``task_yield_profiles['launch_hpc:<class>']``, now from
the episode's settings."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch_hpc:' + parent_input['yield_class']
    profiles = settings['task_yield_profiles']
    if key not in profiles:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    profile = profiles[key]
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['credit_target'], profile['parameters'])
