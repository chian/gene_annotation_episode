"""Continuation, carried from the old ``yield_estimator.py`` (``yield_controller`` -> ``_launch_hpc_yield_controller``;
README 7b: the old ``PracticalYieldEstimator(verify_completion)`` becomes the completion controller).

The old code picked the profile ``launch_hpc:<class>`` from the settings' ``task_yield_profiles`` (the class comes
from the assignment, read by ``read_from_parent`` as ``task_yield_class``), raised
``execution_original_task_yield_profile_required:<key>`` when it was missing, and opened a controller from the
profile's ``cutoff`` and ``parameters``. The cutoff is the controller's cost. The target is the credit the
commissioned requirements can earn, the sum of all their credits (``read_from_parent``): the old code had no number,
only the completion proof.
Nothing else ends this Episode."""
from yield_control import CompletionYieldController


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch_hpc:' + parent_input['task_yield_class']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return CompletionYieldController('hpc_job_execution', initial_credit, profile['cutoff'],
                                     parent_input['completion_target'], profile['parameters'])
