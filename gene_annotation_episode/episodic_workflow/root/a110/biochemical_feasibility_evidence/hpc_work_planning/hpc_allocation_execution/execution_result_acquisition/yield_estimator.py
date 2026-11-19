"""Continuation, carried from the old ``yield_estimator.py`` (``ExecutionEpisodeYield.yield_controller`` and
``_results_yield_controller``; README 7b) and ``configuration.py`` (``results_yield_profiles``,
``task_yield_profiles``). ``settings`` is this episode's entry of the run's ``continuation`` collaborator:
``{'results_yield_profiles': {'native_unbounded_<local|hpc>': {'cutoff', 'parameters'}}, 'task_yield_profiles':
{'results:native_finite_<local|hpc>': {'cutoff', 'parameters'}}}`` (only the profile of this commission's key is
read). A profile's cutoff is the controller's ``cost``.

* a selector with an unbounded window (a path read to its end): accumulation (old plain ``YieldController``);
* a finite selector: bounded quality, its maximum the credit still uncredited by the selector,
  ``acquired_record_unit * (1 - original_fraction)`` (old ``estimate_bounded_credit_yield(maximum_credit=
  remaining)``). The original fraction is zero: the initial refs hold no result window.

The old exact-zero forecast of an exhausted selector (``finite_result_selector_exhaustion_v1``), the practical
completion estimator (``PracticalYieldEstimator(verify_completion)``) and the typed-selector controller
(``results:typed_<kind>_<version>``) are deleted (README 7b, 3d): a verified completion proof is not a controller
input. Nothing but this controller ends the Episode."""
import math

from yield_control import AccumulationYieldController, BoundedQualityYieldController


def _profile(settings, collection, key, code):
    profiles = settings.get(collection)
    if not isinstance(profiles, dict) or key not in profiles:
        raise ValueError(code + ':' + key)
    profile = profiles[key]
    cutoff = profile.get('cutoff') if isinstance(profile, dict) else None
    if (not isinstance(profile, dict) or set(profile) != {'cutoff', 'parameters'}
            or not isinstance(profile['parameters'], dict) or isinstance(cutoff, bool)
            or not isinstance(cutoff, (int, float)) or not math.isfinite(cutoff) or cutoff <= 0):
        raise ValueError('explicit_results_yield_profile_invalid:' + key)
    return profile


def yield_controller(initial_credit, settings, parent_input):
    kind = parent_input['resource_kind']
    if any(row['length'] is None for row in parent_input['windows']):
        profile = _profile(settings, 'results_yield_profiles', 'native_unbounded_' + kind,
                           'results_original_task_yield_profile_required')
        return AccumulationYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                           profile['parameters'])
    profile = _profile(settings, 'task_yield_profiles', 'results:native_finite_' + kind,
                       'execution_original_task_yield_profile_required')
    original_fraction = 0.0
    remaining = parent_input['acquired_record_unit'] * (1.0 - original_fraction)
    if remaining == 0 and initial_credit != 0:
        raise ValueError('results_no_uncredited_bytes_but_nonzero_initial_credit')
    return BoundedQualityYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                         remaining, profile['parameters'])
