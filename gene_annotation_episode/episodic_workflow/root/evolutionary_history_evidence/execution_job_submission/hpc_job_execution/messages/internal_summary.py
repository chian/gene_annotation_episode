"""Where the job stands: the assignment, the receipts of the commands run so far, the working context after the
last, the requirement credit projected over them and the completion proof, from the loop's view.

``project_completion`` is the old ``PracticalState._completion`` over the summary's own receipts (library
candidate)."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.practical_execution_credit import project_practical_credit
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.practical_execution_records import COMPLETION_VERSION, assess_validations, digest
from gene_annotation_episode.episodic_workflow.episode_support.records.progress_views import yield_table

# The baseline validations assess the commissioned initial context before any command; they carry no time.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def project_completion(assignment, progress, receipts):
    """The completion proof of the assignment's endpoint, or ``None`` while it is not proven."""
    if not receipts:
        return None
    keys = set(assignment['completion_keys'])
    if not keys <= set(progress['satisfied_keys']):
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
    assignment = view.parent_input
    commands = [outcome['outcome'] for outcome in view.outcomes if outcome['kind'] == 'tool']
    receipts = [command['receipt'] for command in commands]
    baseline = assess_validations(assignment, {'facts': {}}, assignment['initial_context'],
                                  checked_at=BASELINE_CHECKED_AT)
    progress = project_practical_credit(assignment, baseline, receipts)
    return {'assignment': assignment, 'receipts': receipts,
            'receipt_refs': [command['receipt_ref'] for command in commands],
            'handoff_refs': [command['receipt_ref'] for command in commands if command['handoff']],
            'context': receipts[-1]['context_after'] if receipts else assignment['initial_context'],
            'progress': progress, 'completion': project_completion(assignment, progress, receipts),
            'yield_table': (None if view.controller_state is None
                            else yield_table(view.controller_state, forecast_unit='credit'))}
