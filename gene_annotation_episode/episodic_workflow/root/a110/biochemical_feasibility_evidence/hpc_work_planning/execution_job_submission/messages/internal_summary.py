"""Where the launch stands: the commissioner's launch assignment, what each commissioned route child returned,
the resources whose usable handoff is held and the controller's forecast (the old ``LaunchDecisionState`` and
``LaunchInternalSummary.decision_context``, as a pure function of the view).

A child unit's outcome is ``{'kind': 'child', 'slot', 'arguments': {'resource_id'}, 'report', ...}`` with the
report ``read_from_child`` made; a tool unit's outcome is ``{'kind': 'tool', 'tool', 'outcome', ...}``."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def selected_execution_task(parent_input):
    """The old ``_with_selected_execution_task``: the scientific task and the native flux-balance jobs of the
    requests, presented for a launch whose requests are all native flux-balance requests.

    The presentation of one job (``scientific_job_view`` of the old ``flux_balance_request_binding``) and of one
    resource (``resource_information_for_id`` of the old ``library.execution_resource_information``) are in
    the old shared root and not placed: the use raises."""
    requests = parent_input['requests']
    if 'scientific_task' not in parent_input or any(
            not isinstance(request['requested_job'].get('native_flux_balance'), dict) for request in requests.values()):
        return None
    raise NotImplementedError('library_not_placed:flux_balance_request_binding.scientific_job_view and '
                              'library.execution_resource_information.resource_information_for_id')


def internal_summary(view):
    parent_input = view.parent_input
    commissioned, handed_off, handoff_refs, lookups = [], [], [], []
    for outcome in view.outcomes:
        if outcome['kind'] == 'child':
            report = outcome['report']
            commissioned.append({'resource_id': outcome['arguments']['resource_id'], 'slot': outcome['slot'],
                                 'handoff_refs': report['handoff_refs'], 'completed': report['completed'],
                                 'child_credit': report['child_credit'], 'child_finding': report['child_finding']})
            if report['handoff_refs']:
                handed_off.append(outcome['arguments']['resource_id'])
                handoff_refs.extend(report['handoff_refs'])
        else:
            lookups.append({'tool': outcome['tool'], 'outcome': outcome['outcome']})
    initial = list(parent_input['handed_off_resource_ids'])
    summary = {**parent_input,
               'initial_handed_off_resource_ids': initial,
               'handed_off_resource_ids': list(dict.fromkeys([*initial, *handed_off])),
               'commissioned': commissioned,
               'handoff_refs': sorted(dict.fromkeys(handoff_refs)),
               'lookups': lookups,
               'controller': yield_table(view.controller_state, forecast_unit='one commissioned job request')}
    task = selected_execution_task(parent_input)
    if task is not None:
        summary['selected_execution_task'] = task
    return summary
