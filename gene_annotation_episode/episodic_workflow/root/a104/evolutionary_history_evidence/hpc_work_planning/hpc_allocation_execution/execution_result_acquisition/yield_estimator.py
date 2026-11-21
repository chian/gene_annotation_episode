"""Continuation of a generic native acquisition, from the profile of its resource kind in the episode's settings
(old ``ExecutionEpisodeYield._results_yield_controller``).

A selector with any unbounded window credits without a declared limit: accumulation (the old plain
``YieldController`` with ``results_yield_profiles['native_unbounded_<kind>']``). A selector of finite windows
credits at most the acquired-record unit: bounded quality with that maximum (the old estimate was bounded by the
unit times the fraction the earlier results left uncovered, which needs the held results and so cannot be read
here; the unit is the bound). The old exact-zero forecast, the practical-endpoint estimate and the typed and API
profiles (a completion with the verified completion proof as target) are not carried: only the controller stops the
Episode, and this episode acquires plain file results only."""
from yield_control import AccumulationYieldController, BoundedQualityYieldController


def _profile(table, key):
    profile = table.get(key)
    if profile is None:
        raise ValueError('results_original_task_yield_profile_required:' + key)
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
