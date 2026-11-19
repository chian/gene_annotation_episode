"""Continuation: the credit of this episode counts the acquired results (one acquired-record unit per new result
identity; the handoff passed in the commission earns nothing), and the number of results a selector yields is not
known when the commission is made, so the controller is the accumulation controller with the cost of the old
profile.

Old: ``_results_yield_controller`` built ``YieldController(epoch, initial_credit, profile['cutoff'],
YieldParameters(**profile['parameters']), estimate_with_context=PracticalYieldEstimator(verify_completion))``,
the profile chosen by the key ``results:api_<service>[_<selector version>]``. The key is kept; the profile is read
from ``settings['task_yield_profiles']`` (``cutoff`` is the controller's cost). The old service came from the
original target read through the handoff (BLOCKED-ON-JOB-SERVICE), so the commission carries it (``service``).
The practical endpoint estimate (an exact zero forecast on a verified completion proof), ``require_private_yield``
and ``practical_estimator`` are not carried: the completion proof is not a controller input, and the target a
completion controller needs is not known from the commission. Only the controller stops the Episode."""
from yield_control import AccumulationYieldController


def yield_key(parent_input):
    selector = parent_input['selector']
    return 'results:api_' + parent_input['service'] + ('_' + selector['version'] if 'version' in selector else '')


def task_yield_profile(settings, key):
    binding = settings['task_yield_profiles'].get(key)
    if binding is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    profile = task_yield_profile(settings, yield_key(parent_input))
    return AccumulationYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                       profile['parameters'])
