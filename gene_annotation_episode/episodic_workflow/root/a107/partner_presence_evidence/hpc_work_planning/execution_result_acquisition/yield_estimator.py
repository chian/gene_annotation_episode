"""Continuation, carried from the old ``yield_estimator.py`` (``ExecutionEpisodeYield._results_yield_controller``;
README 7b), chosen by the selector read from the parent input.

* a native selector with a path of no fixed length: the profile ``native_unbounded_<kind>`` of
  ``results_yield_profiles`` with the plain accumulating controller -> ``AccumulationYieldController``;
* a native selector whose intervals are all finite: the profile ``results:native_finite_<kind>`` of
  ``task_yield_profiles`` with a bounded credit estimate -> ``BoundedQualityYieldController``. The old maximum was
  ``acquired_record_unit`` times the fraction the earlier results left uncovered, which needs the held results;
  ``yield_controller`` is handed none, so the maximum is the unit (credit counts only new positions, so it never
  passes the old maximum; only the forecast bound is looser);
* a typed or API selector: the practical completion estimate (``PracticalYieldEstimator`` on a verified completion
  proof). This episode acquires plain file results only, so no completion controller is built.

The old ``require_private_yield`` switch, the exact-zero forecast when nothing remained and the switch to the
completion estimator on a proof are not carried: nothing but this controller stops the Episode. The ``<kind>`` is the
resource kind of the target behind the handoff, which the commission names (``resource_kind``). A profile is
``{'cutoff': cost, 'parameters': {...}}`` as in the old settings; the cutoff is the controller's cost."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController


def _profile(table, key):
    profile = table.get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return profile


def yield_controller(initial_credit, settings, parent_input):
    kind = parent_input['assignment']['resource_kind']
    requested = parent_input['requested']
    if not requested:
        raise ValueError('results_original_selector_has_no_requested_bytes')
    if any(length is None for _, length in requested.values()):
        profile = _profile(settings.get('results_yield_profiles', {}), 'native_unbounded_' + kind)
        return AccumulationYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                           profile['parameters'])
    profile = _profile(settings.get('task_yield_profiles', {}), 'results:native_finite_' + kind)
    return BoundedQualityYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                         parent_input['acquired_record_unit'], profile['parameters'])
