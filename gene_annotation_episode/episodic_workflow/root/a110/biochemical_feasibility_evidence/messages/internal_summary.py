"""Where the episode stands, as a pure function of the loop's view (carried from ``internal_summary.py``
(``ScientificInternalSummary.decision_context``, ``initial_decision_context``, ``ScientificDecisionSummary.
_decision_snapshot``), ``decision_delivery.py`` (``decision_completion``), ``task_state.py`` and ``presentation.py``).

The parent input (the assignment as ``read_from_parent`` produced it, with the scope, the proposed annotation, the
evidence, the selection and the continuation task), the objective, the two initial lookups (``entry``: the selected
evidence axis, thought pattern and tools; ``received``: the received component evidence; ``None`` until the unit that
ran them), the actions taken so far (the old ``requested_action_history``), the latest outcome, the latest completed
interpretation (``write_interpretation``), the records the reasoning commits produced and the children returned, what
each child returned (the old ``completed_action_reports``), the investigation progress of the held findings (the old
credit view fields ``retained_finding_count``, ``inactive_dependencies`` and ``detail_pages``, read through
``view.records``), the reasoning commit schema, and the controller's yield table.

Not carried: ``working_state`` (the old ``workflow.working_state(self)``: the held records are ``view.records``),
``visible_record_refs`` and ``_references_in`` (what the episode may name is what it holds: ``records.holds``),
``pending_work``, ``report_deliveries``, ``report_lifecycle``, ``delivery_status``, ``visual_evidence`` (a query of the
old ``runtime_actions`` table), ``job_episode_options``, ``available_report_facts`` (the parent selects the child's
declared fields), ``contract_information_profile`` and the other pieces of the old decision exchange."""
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

from ..credit import finding_progress


def _dedupe(values):
    return list(dict.fromkeys(values))


def internal_summary(view):
    parent = view.parent_input
    actions, children, committed = [], [], []
    entry, received, interpretation, last = None, None, None, None
    for index, unit in enumerate(view.outcomes):
        if unit['kind'] == 'tool':
            outcome = unit['outcome']
            actions.append({'index': index, 'kind': 'tool', 'name': unit['tool'], 'status': outcome['status'],
                            'arguments': unit['arguments']})
            last = {'index': index, 'name': unit['tool'], 'outcome': outcome}
            if unit['tool'] == 'process_entry':
                entry = outcome
            elif unit['tool'] == 'received_evidence':
                received = outcome
            elif unit['tool'] == 'write_interpretation' and outcome['status'] == 'completed':
                interpretation = outcome
            elif unit['tool'] == 'reason':
                committed.extend(outcome['record_refs'])
                committed.extend(outcome['changed_record_refs'])
            continue
        report = unit['report']
        actions.append({'index': index, 'kind': 'child', 'name': unit['slot'], 'status': 'completed',
                        'arguments': unit['arguments']})
        last = {'index': index, 'name': unit['slot'], 'outcome': report}
        children.append(report)
        committed.extend(report['facts'].get('committed_record_refs', []))
    state = view.controller_state
    source_held = {} if interpretation is None else {reference: view.records.holds(reference)
                                                     for reference in interpretation['source_refs']}
    return {**parent, 'goal': view.goal.as_record(), 'units_consumed': view.units_consumed,
            'record_refs': _dedupe([parent['proposed_annotation_ref'], *parent['evidence_refs'],
                                    *parent['received_record_refs']]),
            'entry': entry, 'received': received, 'actions': actions, 'last_outcome': last,
            'interpretation': interpretation, 'interpretation_source_held': source_held, 'children': children,
            'committed_record_refs': _dedupe(committed), 'reasoning_schema': view.records.reasoning_schema(),
            'investigation_progress': finding_progress(view.records, parent),
            'action_yields': None if state is None else yield_table(state, forecast_unit='credit')}
