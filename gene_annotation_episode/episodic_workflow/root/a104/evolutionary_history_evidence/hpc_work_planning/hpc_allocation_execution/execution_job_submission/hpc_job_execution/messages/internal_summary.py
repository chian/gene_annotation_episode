"""Where the execution stands, as a pure function of the view: the assignment, the receipts of the commands run so
far (each tool outcome carries its receipt and the reference of its saved copy), the working context after the last
command, the practical credit view and the completion proof over them, and the controller's yield table.

Old ``native_internal_summary.decision_context``: execution_assignment, execution_resource, coordinator_workspace,
execution_progress, execution_completion. The resource, the coordinator workspace and the resource's launch
instructions come from the settings and are added by ``decide``; everything else is here. The old HPC episode
added no selected-execution-task view (its ``_with_selected_execution_task`` returned the value unchanged)."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# The baseline is the assignment's frozen initial state, assessed before any action. A fixed time keeps the summary
# a pure function of the view; the baseline carries no observation time of its own.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def _completion(assignment, initial_validations, receipts):
    """The verified completion of the assignment's endpoint, or None (copied from the old practical state's
    ``_completion``; library candidate)."""
    if not receipts:
        return None
    satisfied = set(project_practical_credit(assignment, initial_validations, receipts)['satisfied_keys'])
    keys = set(assignment['completion_keys'])
    if not keys <= satisfied:
        return None
    endpoint_kind = 'requested_job_handoff' if assignment['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    last = receipts[-1]
    if not any(item['key'] in keys and item['satisfied'] and item['predicate']['kind'] == endpoint_kind
               for item in last['validations']):
        return None
    return {'version': COMPLETION_VERSION, 'run_id': last['run_id'], 'episode_id': last['episode_id'],
            'assignment_sha256': digest(assignment), 'endpoint': assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    initial_validations = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                             checked_at=BASELINE_CHECKED_AT)
    receipts, receipt_refs, handoff_refs, commands = [], [], [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        receipts.append(outcome['receipt'])
        receipt_refs.append(outcome['receipt_ref'])
        if outcome['receipt']['outcome']['facts'].get('requested_job', {}).get('handoff') is not None:
            handoff_refs.append(outcome['receipt_ref'])
        commands.append({'operation_ref': outcome['operation_ref'], 'receipt_ref': outcome['receipt_ref'],
                         'arguments': unit['arguments']['arguments'],
                         'failure': (outcome['receipt']['outcome'].get('native_outcome') or {}).get('failure')})
    progress = project_practical_credit(assignment, initial_validations, receipts)
    completion = _completion(assignment, initial_validations, receipts)
    context = receipts[-1]['context_after'] if receipts else assignment['initial_context']
    controller = view.controller_state
    return {'assignment': assignment, 'completion_target': parent['completion_target'],
            'record_refs': parent['record_refs'], 'initial_validations': initial_validations,
            'context': context, 'receipts': receipts, 'receipt_refs': receipt_refs, 'handoff_refs': handoff_refs,
            'commands': commands, 'execution_progress': progress, 'execution_completion': completion,
            'controller': None if controller is None else yield_table(controller, forecast_unit='practical credit'),
            'units_consumed': view.units_consumed}
