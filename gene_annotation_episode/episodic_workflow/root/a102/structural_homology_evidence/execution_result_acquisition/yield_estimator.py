"""Continuation, chosen by the selector of the assignment as ``read_from_parent`` produced it:

* a selector with a path of no fixed length: the profile ``native_unbounded_<kind>`` of
  ``results_yield_profiles`` and the accumulating controller -> ``AccumulationYieldController``;
* a selector whose intervals are all finite: the profile ``results:native_finite_<kind>`` of
  ``task_yield_profiles`` and a bounded credit with ``maximum_credit = acquired_record_unit`` (the credit of a
  fully new selector) -> ``BoundedQualityYieldController``. Credit counts only newly covered bytes, so when known
  results already hold requested bytes the maximum is not reached and the controller stops when units stop
  earning.

The ``<kind>`` is the resource kind of the handed-off job (``local`` or ``hpc``), which the commission names
(``resource_kind``): ``yield_controller`` is handed only the parent input and no record. A profile is
``{'cutoff': cost, 'parameters': {...}}``; the cutoff is the controller's cost. Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController, FIXED_CONTROL


def yield_controller(initial_credit, settings, parent_input):
    if any(length is None for _, length in parent_input['requested'].values()):
        return AccumulationYieldController('execution_result_acquisition', initial_credit, FIXED_CONTROL,
                                           items=None)
    key = 'results:native_finite_' + parent_input['resource_kind']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return BoundedQualityYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                         parent_input['acquired_record_unit'], profile['parameters'])
