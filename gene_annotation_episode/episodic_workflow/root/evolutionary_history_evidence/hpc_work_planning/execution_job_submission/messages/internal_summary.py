"""Where the launch stands, as a pure function of the view: the assignment and what the commissioner passed, the
capabilities lookup, the lookups into the libraries, the launches run (each launch child's report with the resource
it was commissioned on), the resources that have a usable handoff, and the controller's yield table.

Carried from the old ``internal_summary.py`` (``LaunchSummary.decision_context``: ``execution_assignment`` and
``execution_progress``, the live facts of the report; ``selected_execution_task`` needs the capabilities lookup and
the configured resources, so ``task.py`` builds it in ``decide``) and ``received_records.py`` (the received usable
handoffs, here the reports of the episode's own child units). The old generic decision state (working state, journal
reads, pending work, report deliveries, credit view, report lifecycle) is old-runner machinery; the controller's
yield table, which it showed as ``controller``, is ``view.controller_state`` here."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def internal_summary(view):
    parent = view.parent_input
    capabilities, lookups, launches, handoff_refs, handoff_resources = None, [], [], [], []
    for unit in view.outcomes:
        if unit['kind'] == 'tool':
            if unit['tool'] == 'execution_capabilities':
                capabilities = unit['outcome']
            else:
                lookups.append({'tool': unit['tool'], 'arguments': unit['arguments'], 'outcome': unit['outcome']})
            continue
        report = unit['report']
        resource_id = unit['arguments']['resource_id']
        launches.append({'slot': unit['slot'], 'resource_id': resource_id, **report})
        handoff_refs.extend(ref for ref in report['handoff_refs'] if ref not in handoff_refs)
        if report['completed'] and report['handoff_refs'] and resource_id not in handoff_resources:
            handoff_resources.append(resource_id)
    controller = view.controller_state
    return {'assignment': parent['assignment'], 'message': parent['message'], 'record_refs': parent['record_refs'],
            'handoff_unit': parent['handoff_unit'], 'acquired_record_unit': parent['acquired_record_unit'],
            'scientific_task': parent.get('scientific_task'),
            'received_handoff_resources': parent['received_handoff_resources'], 'permitted': parent['permitted'],
            'capabilities': capabilities, 'lookups': lookups, 'launches': launches, 'handoff_refs': handoff_refs,
            'handoff_resources': handoff_resources,
            'progress': {'execution_handoff_refs': sorted(handoff_refs),
                         'execution_completed': bool(handoff_resources), 'handoff_resources': handoff_resources},
            'controller': None if controller is None else yield_table(controller, forecast_unit='handoff credit'),
            'units_consumed': view.units_consumed}
