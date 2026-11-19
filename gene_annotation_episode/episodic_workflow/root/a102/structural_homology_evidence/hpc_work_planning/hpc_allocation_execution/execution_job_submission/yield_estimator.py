"""Continuation: a bounded-quality controller (the old ``BoundedYieldController``). Its maximum is
``handoff_unit`` times the eligible original requests not already handed off at the start (``read_from_parent``
derives it; when none remain the maximum is zero and any non-zero credit is an error of the controller). The cost
and the estimator parameters are those of the profile ``launch:<classes joined by +>`` of the episode's settings
(``task_yield_profiles``); a missing profile raises (the old ``execution_private_yield_binding_not_enabled``)."""
from yield_control import BoundedQualityYieldController


def yield_controller(initial_credit, settings, parent_input):
    key = 'launch:' + parent_input['yield_class']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_private_yield_binding_not_enabled:' + key)
    return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'],
                                         parent_input['maximum_credit'], profile['parameters'])
