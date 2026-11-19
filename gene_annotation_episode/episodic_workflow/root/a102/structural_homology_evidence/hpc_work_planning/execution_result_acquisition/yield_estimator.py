"""Continuation, carried from the old ``yield_estimator.py`` (``_results_yield_controller``; README 7b).

The old code chose by the selector of the assignment, read here from the parent input (``read_from_parent``):

* a native selector with a path of no fixed length: the profile ``native_unbounded_<kind>`` of
  ``results_yield_profiles`` and the plain accumulating controller -> ``AccumulationYieldController``;
* a native selector whose intervals are all finite: the profile ``results:native_finite_<kind>`` of
  ``task_yield_profiles`` and a bounded credit estimate with ``maximum_credit = acquired_record_unit * (1 - the
  fraction already received)`` -> ``BoundedQualityYieldController``;
* an API or typed selector: the completion-target estimate (``PracticalYieldEstimator``) -> completion. Those
  selectors are not carried (``messages/read_from_parent.py``), so no completion controller is built.

The ``<kind>`` is the resource kind of the original target (``local`` or ``hpc``), which the old code read from the
target behind the handoff. That read is BLOCKED-ON-JOB-SERVICE and ``yield_controller`` is handed only the parent
input, so the commission names the kind (``resource_kind``, a new field; ``messages/read_from_parent.py``). A profile is
``{'cutoff': cost, 'parameters': {...}}`` as in the old settings; the cutoff is the controller's cost. The maximum
of the finite case is ``acquired_record_unit`` (the credit of a fully new selector): the old maximum subtracted the
fraction the known results already held, which needs those records read (``yield_controller`` is handed none), so
when known bytes exist the maximum is not reached and the controller stops when units stop earning (see
contract_misfits). The old exact-zero forecast and the practical endpoint estimate on a verified completion proof
are not carried: a completion proof is not a controller input. Nothing else ends this Episode."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController


def yield_controller(initial_credit, settings, parent_input):
    if any(length is None for _, length in parent_input['requested'].values()):
        key = 'native_unbounded_' + parent_input['resource_kind']
        profile = settings['results_yield_profiles'].get(key)
        if profile is None:
            raise ValueError('results_original_task_yield_profile_required:' + key)
        return AccumulationYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                           profile['parameters'])
    key = 'results:native_finite_' + parent_input['resource_kind']
    profile = settings['task_yield_profiles'].get(key)
    if profile is None:
        raise ValueError('execution_original_task_yield_profile_required:' + key)
    return BoundedQualityYieldController('execution_result_acquisition', initial_credit, profile['cutoff'],
                                         parent_input['acquired_record_unit'], profile['parameters'])
