"""Continuation, by the old ``ExecutionEpisodeYield._results_yield_controller`` (README 7b).

- A native byte selector with an unbounded requested length: the old plain ``YieldController`` over
  ``results_yield_profiles['native_unbounded_<local|hpc>']`` is the accumulation controller.
- A native finite byte selector: the old ``task_yield_profiles['results:native_finite_<kind>']`` with
  ``finite_result_yield`` (a bounded credit with ``maximum_credit = acquired_record_unit * (1 - original fraction)``)
  is the bounded quality controller. Its maximum is the credit unit from the parent input: the original fraction
  needs the initial results, which only held records give and ``yield_controller`` is handed none, so the maximum is
  the whole unit (credit counts only newly covered bytes, so it cannot pass it).
- The API target (``results:api_<service>[_<version>]``) and the typed native families
  (``results:typed_<kind>_<version>``) used the verified completion proof as their estimate
  (``PracticalYieldEstimator(verify_completion)``): the completion controller, with the credit the verified completion
  earns as its target. That credit belongs to classes that are in no place now, so these raise where the target would
  be taken.

The old settings are the episode's ``settings``; the old cutoff is the controller's cost. The old exact-zero forecast
when no uncredited requested bytes remain (``finite_result_selector_exhaustion_v1``) and the endpoint-proof forecast
are not controller inputs and are not carried: nothing but the controller stops the Episode. The old
``private_yield_binding`` switch (``execution_private_yield_binding_not_enabled``) is the existence of this file."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController

EPOCH = 'execution_result_acquisition'


def _profile(profiles, key, code):
    binding = profiles.get(key)
    if binding is None:
        raise ValueError(code + ':' + key)
    return binding


def yield_controller(initial_credit, settings, parent_input):
    family, target = parent_input['family'], parent_input['target']
    if family != 'native_bytes':
        # old: results:api_<service>[_<version>] / results:typed_<kind>_<version> with PracticalYieldEstimator
        raise NotImplementedError('unplaced:' + family + '.credit_view: the completion target of the typed family')
    requested = parent_input['requested']
    if not requested:
        raise ValueError('results_original_selector_has_no_requested_bytes')
    if any(length is None for _, length in requested.values()):
        key = 'native_unbounded_' + target['resource_kind']
        profile = _profile(settings['results_yield_profiles'], key, 'results_original_task_yield_profile_required')
        return AccumulationYieldController(EPOCH, initial_credit, profile['cutoff'], profile['parameters'])
    profile = _profile(settings['task_yield_profiles'], 'results:native_finite_' + target['resource_kind'],
                       'execution_original_task_yield_profile_required')
    return BoundedQualityYieldController(EPOCH, initial_credit, profile['cutoff'], parent_input['acquired_record_unit'],
                                         profile['parameters'])
