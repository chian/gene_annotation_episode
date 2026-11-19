"""Where the execution stands, as a pure function of the view: the assignment, the receipts of the commands run so
far (each tool outcome carries its receipt, the reference of its saved copy and whether it is a handoff), the
practical credit view and the completion proof over them, the working context, the selected execution task (when
the parent supplied the scientific task), and the controller's yield table.

Old ``terminal_summary.decision_context``: execution_assignment, execution_resource, coordinator_workspace,
execution_progress, execution_completion. The resource, the coordinator workspace and the resource's launch
instructions come from the settings and are added by ``decide``; everything else is here."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest)

# The baseline is the assignment's frozen initial state, assessed before any action. A fixed time keeps the summary a
# pure function of the view; the baseline carries no observation time of its own.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'
NATIVE_JOB = 'native_protein_structure'


def _completion(assignment, initial_validations, receipts):
    """The verified completion of the assignment's endpoint, or None (the old ``PracticalState._completion`` over
    the receipts; library candidate)."""
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


def _selected_execution_task(parent_input):
    """The old ``_with_selected_execution_task``: for a local native protein-structure request with a scientific
    parent task, the task's question, the selected tool information and the request."""
    task = parent_input.get('scientific_task')
    assignment = parent_input['assignment']
    job = assignment['requested_job']
    if task is None or not isinstance(job.get(NATIVE_JOB), dict):
        return None
    return {'version': 'selected_execution_task_v1', 'scientific_question': task['scientific_question'],
            'selected_tool_info': task['selected_tool_info'],
            'requests': [{'resource_id': assignment['resource_id'], 'resource_kind': 'local',
                          'endpoint': assignment['endpoint'], 'constraints': deepcopy(assignment['constraints']),
                          'job': deepcopy(job[NATIVE_JOB])}],
            'constraints': deepcopy(assignment['constraints']), 'selector': None}


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    initial_validations = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                             checked_at=BASELINE_CHECKED_AT)
    receipts, receipt_refs, handoff_refs, commands = [], [], [], []
    context = deepcopy(assignment['initial_context'])
    for unit in view.outcomes:
        outcome = unit['outcome']
        receipts.append(outcome['receipt'])
        receipt_refs.append(outcome['receipt_ref'])
        if outcome['handoff']:
            handoff_refs.append(outcome['receipt_ref'])
        context = outcome['receipt']['context_after']
        commands.append({'operation_ref': outcome['operation_ref'], 'receipt_ref': outcome['receipt_ref'],
                         'status': outcome['status'], 'arguments': unit['arguments']['arguments'],
                         'failure': (outcome['receipt']['outcome'].get('native_outcome') or {}).get('failure')})
    progress = project_practical_credit(assignment, initial_validations, receipts)
    completion = _completion(assignment, initial_validations, receipts)
    controller = view.controller_state
    return {'assignment': assignment, 'completion_target': parent['completion_target'],
            'initial_validations': initial_validations, 'receipts': receipts, 'receipt_refs': receipt_refs,
            'handoff_refs': handoff_refs, 'commands': commands, 'execution_context': context,
            'execution_progress': progress, 'execution_completion': completion,
            'selected_execution_task': _selected_execution_task(parent),
            'controller': None if controller is None else yield_table(controller, forecast_unit='practical credit'),
            'units_consumed': view.units_consumed}
