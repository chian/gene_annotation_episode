"""Continuation: the credit accumulates (the handoff unit once, and the acquired-record unit per acquired record),
and acquired records may pass the handoff, so the controller is the accumulation controller (old: the plain
accumulating ``YieldController`` with ``PracticalYieldEstimator``, README 7b: ``'accumulation'``). The completion
controller is not used: this episode's credit has no finite target it reaches exactly.

The old profile selection is kept: the profile key is ``launch_api:`` plus the request's yield class, and the
episode's settings hold its ``task_yield_profiles`` (``cutoff`` is the controller's cost). The request is read
from the parent input only. The old ``require_private_yield`` switch, ``practical_estimator`` and the completion
proof plumbing (``completion_for_action``, ``verify_completion``, ``_proof_for_action``) are not carried."""
from yield_control import AccumulationYieldController


def request_yield_class(request):
    """Classify the original execution request without generated IDs (old ``_request_yield_class``)."""
    parts = ['api', request.get('service', 'unknown')]
    for field in ('algorithm', 'database'):
        if field in request:
            parts.append(request[field])
    return '_'.join(parts) + '_handoff'


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, 'launch_api:' + request_yield_class(parent_input))
    return AccumulationYieldController('api_job_execution', initial_credit, profile['cutoff'],
                                       profile['parameters'])
