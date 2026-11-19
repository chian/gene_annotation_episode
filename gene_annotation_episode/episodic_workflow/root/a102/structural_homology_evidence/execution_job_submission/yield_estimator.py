"""Continuation, carried from the old ``yield_estimator.py`` (``_launch_yield_controller``, ``_task_yield_profile``,
``_request_yield_class``; README 7b: the old ``BoundedYieldController`` becomes the bounded-quality controller).

The old code took the profile ``launch:<sorted request classes joined by +>`` from the settings'
``task_yield_profiles`` (the key comes from the commission: ``read_from_parent`` derives it as ``task_yield_key``),
raised ``execution_original_task_yield_profile_required:<key>`` when it was missing, and capped one next handoff
by the original request slots still uncredited: ``remaining`` = (eligible requests not already handed off) times
the handoff unit (``read_from_parent``: ``remaining_credit``). The profile's ``cutoff`` is the controller's cost and
its ``parameters`` the controller's settings.

The old ``_launch`` checks against the run's configuration are made here, where the settings are: every request is
filed under a bound resource (``execution_resource_not_bound``) of the kind the request is for
(``execution_resource_kind_conflict``). When no request remains the old code built an exact-zero controller; that
estimator is not carried (README 7b, ``no_remaining_requests``) and nothing replaces it: a commission with no
uncredited request fails here. The old ``require_private_yield`` switch and ``practical_estimator`` are not
carried. Nothing else ends this Episode."""
from yield_control import BoundedQualityYieldController

# The old ``execution_contracts.KINDS``: the kind a configured resource's ``kind`` stands for.
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'api': 'api'}


def yield_controller(initial_credit, settings, parent_input):
    resources = settings['resources']
    for resource_id, kind in parent_input['request_kinds'].items():
        if resource_id not in resources:
            raise ValueError('execution_resource_not_bound')
        if KINDS[resources[resource_id]['kind']] != kind:
            raise ValueError('execution_resource_kind_conflict')
    if not parent_input['remaining_credit'] > 0:
        raise ValueError('launch_no_uncredited_original_request')
    key = parent_input['task_yield_key']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return BoundedQualityYieldController('execution_job_submission', initial_credit, profile['cutoff'],
                                         parent_input['remaining_credit'], profile['parameters'])
