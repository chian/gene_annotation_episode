"""Continuation, chosen by the selector of the assignment as ``read_from_parent`` produced it:

* a selector with a path of no fixed length: the profile ``native_unbounded_<kind>`` of
  ``results_yield_profiles`` must be present (its cutoff and parameters are not read) and the accumulating
  controller -> ``AccumulationYieldController`` with ``FIXED_CONTROL`` and ``items=None``. It takes no cost: after
  at least W = 8 units attempted and m = 4 observed it fits nano-graphrag's yield model; a unit is flat when the
  upper bound of the expected next marginal (hypervolume) credit is at or below gamma (``FIXED_CONTROL``: gamma
  0.06); it stops after 4 flat units in a row (``items=None``: no input list bounds it);
* a selector whose intervals are all finite: the profile ``results:native_finite_<kind>`` of
  ``task_yield_profiles`` and a bounded credit with ``maximum_credit = acquired_record_unit`` (the credit of a
  fully new selector) -> ``BoundedQualityYieldController``. Credit counts only newly covered bytes, so when known
  results already hold requested bytes the maximum is not reached and the controller stops when units stop
  earning.

The ``<kind>`` is ``hpc``: this episode is the result acquisition of the HPC allocation. A profile is
``{'cutoff': cost, 'parameters': {...}}``; the cutoff is the bounded-quality controller's cost (the accumulating
controller takes none). Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController, FIXED_CONTROL

KIND = 'hpc'


def yield_controller(initial_credit, settings, parent_input):
    if any(length is None for _, length in parent_input['requested'].values()):
        key = 'native_unbounded_' + KIND
        profile = settings['results_yield_profiles'].get(key)
        if profile is None:
            raise ValueError('results_original_task_yield_profile_required:' + key)
        return AccumulationYieldController('execution_result_acquisition', initial_credit, FIXED_CONTROL,
                                           items=None)
    key = 'results:native_finite_' + KIND
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return BoundedQualityYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                         parent_input['acquired_record_unit'], profile['parameters'])
