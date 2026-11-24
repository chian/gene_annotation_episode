"""Continuation: a bounded-quality controller (the old ``BoundedYieldController`` of ``_launch_yield_controller``,
README 7b). Its maximum is ``handoff_unit`` times the permitted original requests not already handed off when the
commission began; ``read_from_parent`` derives it. The cost and the estimator parameters are those of the profile
``launch:<request classes joined by +>`` of the episode's settings (``task_yield_profiles``; ``cutoff`` is the
controller's cost); a missing profile raises, as the old ``_task_yield_profile`` did.

The old exact-zero estimator for a commission with nothing left to hand off, and the completion proof of
``PracticalYieldEstimator``, are not carried: when no request remains the maximum is zero and the controller's own
error is the failure. Nothing else stops this episode."""
from yield_control import BoundedQualityYieldController


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, 'launch:' + parent_input['yield_class'])
    return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'],
                                         parent_input['maximum_credit'], profile['parameters'])
