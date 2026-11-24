"""Where the execution stands: the assignment, the command receipts its tool returned, the working context after
the last receipt, the practical credit view and the completion proof (the old ``PracticalState``, as a pure
function of the view), and the controller's forecast.

A completed command's outcome is ``{'status': 'completed', 'record_refs': [receipt ref], 'changed_record_refs',
'operation_ref', 'result': <receipt>}``; an invalid one carries ``'result': None`` and its feedback."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.biochemical_feasibility_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.biochemical_feasibility_evidence.practical_execution_records import (
    COMPLETION_VERSION, digest)
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table


def completion_proof(assignment, credit_view, receipts):
    """The old ``PracticalState._completion``: the recorded proof that the requested endpoint is validated, or
    ``None``. A library candidate (it is in the library only as a method of the file-backed state)."""
    if not receipts:
        return None
    keys = set(assignment['completion_keys'])
    if not keys <= set(credit_view['satisfied_keys']):
        return None
    endpoint_kind = ('requested_job_handoff' if assignment['endpoint'] == 'usable_handoff'
                     else 'requested_job_outputs')
    last = receipts[-1]
    if not any(item['key'] in keys and item['satisfied'] and item['predicate']['kind'] == endpoint_kind
               for item in last['validations']):
        return None
    return {'version': COMPLETION_VERSION, 'run_id': last['run_id'], 'episode_id': last['episode_id'],
            'assignment_sha256': digest(assignment), 'endpoint': assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}


def internal_summary(view):
    parent_input = view.parent_input
    assignment = parent_input['assignment']
    done = [outcome['outcome'] for outcome in view.outcomes if outcome['kind'] == 'tool']
    completed = [outcome for outcome in done if outcome['status'] == 'completed']
    receipts = [outcome['result'] for outcome in completed]
    progress = project_practical_credit(assignment, parent_input['initial_validations'], receipts)
    last = done[-1] if done else None
    return {**parent_input,
            'receipts': receipts,
            'receipt_refs': [outcome['record_refs'][0] for outcome in completed],
            'context': receipts[-1]['context_after'] if receipts else assignment['initial_context'],
            'progress': {key: progress[key] for key in ('credit', 'satisfied_keys', 'requirements')},
            'completion': completion_proof(assignment, progress, receipts),
            'last_outcome': last,
            'controller': yield_table(view.controller_state, forecast_unit='one command')}
