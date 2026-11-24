"""Where the execution stands, as a pure function of the view: the working context after the last command, every
command's receipt (returned in its outcome by the tool), the practical credit view and the completion proof
(old ``PracticalState.credit_view`` and ``completion_proof``, rebuilt from the receipts the units returned)."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    COMPLETION_VERSION, assess_validations, digest)

# The fixed time of the baseline validations: the summary is rebuilt on resume and must be the same each time.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def completion_proof(assignment, credit_view, receipts):
    """The proof that the original endpoint predicates are satisfied by the latest command (old
    ``PracticalState._completion``; library candidate)."""
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
            'assignment_sha256': last['assignment_sha256'], 'endpoint': assignment['endpoint'],
            'operation_key': last['operation_key'], 'receipt_sha256': digest(last),
            'validation_keys': sorted(keys)}


def internal_summary(view):
    assignment = view.parent_input['assignment']
    outcomes = [unit['outcome'] for unit in view.outcomes]
    receipts = [outcome['receipt'] for outcome in outcomes]
    initial = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                 checked_at=BASELINE_CHECKED_AT)
    progress = project_practical_credit(assignment, initial, receipts)
    summary = {'assignment': assignment, 'yield_class': view.parent_input['yield_class'],
               'initial_validations': initial,
               'context': receipts[-1]['context_after'] if receipts else assignment['initial_context'],
               'receipts': receipts, 'receipt_refs': [outcome['receipt_ref'] for outcome in outcomes],
               'execution_progress': progress,
               'execution_completion': completion_proof(assignment, progress, receipts)}
    if view.controller_state is not None:
        summary['controller'] = view.controller_state.as_record()
    return summary
