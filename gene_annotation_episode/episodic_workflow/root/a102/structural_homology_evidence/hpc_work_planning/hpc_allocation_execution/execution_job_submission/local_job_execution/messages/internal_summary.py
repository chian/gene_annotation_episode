"""Where the job execution stands, as a pure function of the loop's view: the assignment and what it declares, the
command receipts of the units so far, the practical credit view they give, the completion proof, the working
context the next command starts from, the last outcome and, for a local native protein-structure job, the
selected execution task."""
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import (
    COMPLETION_VERSION, digest)


def completion_proof(assignment, initial_validations, receipts):
    """The completion proof: every completion key is satisfied by the saved, validated receipts and the last
    receipt satisfies the endpoint predicate; ``None`` otherwise (private copy of the pure part of the library's
    ``PracticalState._completion``; library candidate)."""
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


def selected_execution_task(parent):
    """The selected execution task of a local native protein-structure request (the ancestor's scientific question
    and selected tool, the request, its constraints and selector), or ``None`` for any other request."""
    assignment = parent['assignment']
    job = assignment['requested_job'].get('native_protein_structure')
    if not isinstance(job, dict) or parent['scientific_task'] is None:
        return None
    return {'version': 'selected_execution_task_v1',
            'scientific_question': parent['scientific_task']['scientific_question'],
            'selected_tool_info': parent['scientific_task']['selected_tool_info'],
            'requests': [{'resource_id': assignment['resource_id'], 'resource_kind': assignment['resource_kind'],
                          'endpoint': assignment['endpoint'], 'constraints': deepcopy(assignment['constraints']),
                          'job': deepcopy(job)}],
            'constraints': deepcopy(assignment['constraints']), 'selector': None,
            'result_description': None}


def internal_summary(view):
    parent = view.parent_input
    assignment = parent['assignment']
    outcomes = [unit['outcome'] for unit in view.outcomes]
    receipts = [outcome['receipt'] for outcome in outcomes]
    progress = project_practical_credit(assignment, parent['initial_validations'], receipts)
    completion = completion_proof(assignment, parent['initial_validations'], receipts)
    job = next((receipt['outcome']['facts']['requested_job'] for receipt in reversed(receipts)
                if 'requested_job' in receipt['outcome'].get('facts', {})), None)
    receipt_refs = [outcome['receipt_ref'] for outcome in outcomes]
    last = None if not outcomes else {key: outcomes[-1][key] for key in ('status', 'receipt_ref', 'receipt_sha256')}
    return {
        'objective': view.goal.objective,
        'assignment': assignment,
        'scope': parent['scope'],
        'input_refs': parent['input_refs'],
        'completion_target': parent['completion_target'],
        'initial_validations': parent['initial_validations'],
        'execution_context': deepcopy(receipts[-1]['context_after'] if receipts else assignment['initial_context']),
        'execution_progress': progress,
        'execution_completion': completion,
        'receipts': receipts,
        'receipt_refs': receipt_refs,
        'receipt_artifact_refs': [ref for outcome in outcomes for ref in outcome['artifact_refs']],
        'requested_job': job,
        'last_local_outcome': last,
        'selected_execution_task': selected_execution_task(parent),
        'action_yields': (None if view.controller_state is None
                          else yield_table(view.controller_state, forecast_unit='credit')),
        'units_consumed': view.units_consumed,
    }
