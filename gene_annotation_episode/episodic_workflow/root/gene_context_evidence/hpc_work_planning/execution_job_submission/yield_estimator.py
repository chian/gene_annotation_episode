"""Continuation, carried from the old ``yield_estimator.py`` (``_launch_yield_controller``; README 7b: the old
``BoundedYieldController`` becomes the bounded-quality controller).

The old code took the profile ``launch:<sorted request classes joined by +>`` from the configuration's
``task_yield_profiles`` (the key comes from the commission, read by ``read_from_parent`` as ``task_yield_key``),
raised ``execution_original_task_yield_profile_required:<key>`` when it was missing, and capped one next handoff by
the original request slots still uncredited: ``remaining`` = (eligible requests not already handed off) times the
handoff unit (``read_from_parent``: ``remaining_credit``). The profile's ``cutoff`` is the controller's cost and its
``parameters`` the controller's settings. When no request remained the old code built an exact-zero estimator;
that estimator is not carried (README 7b) and nothing replaces it: a commission with no uncredited request fails
here, as the old code failed on a non-zero initial credit. Nothing else ends this Episode."""
from yield_control import BoundedQualityYieldController


def yield_controller(initial_credit, settings, parent_input):
    if not parent_input['remaining_credit'] > 0:
        raise ValueError('launch_no_uncredited_original_request')
    key = parent_input['task_yield_key']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'],
                                         parent_input['remaining_credit'], profile['parameters'])
