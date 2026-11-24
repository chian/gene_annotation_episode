"""Where the execution stands, as a pure function of the loop's view: the assignment, the receipts of the commands
run so far (each unit's outcome), the credit they earn, and whether the commissioned endpoint is verified."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.practical_execution_credit import (
    project_practical_credit)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.practical_execution_records import (
    assess_validations, digest)

# The baseline validations of the initial context are assessed once from the assignment; the summary is a pure
# function of the view, so the baseline carries this fixed time and not a clock reading.
BASELINE_CHECKED_AT = '1970-01-01T00:00:00+00:00'


def baseline_validations(assignment):
    """The immutable initial validations: the assignment's requirements assessed against its initial context."""
    return assess_validations(assignment, {'facts': {}}, assignment['initial_context'], checked_at=BASELINE_CHECKED_AT)


def completion_of(assignment, baseline, receipts):
    """Library candidate: the verified completion of the endpoint (the old practical state's completion proof).

    The commissioned requirement keys are all satisfied and the last command's own validations satisfy the endpoint
    predicate."""
    if not receipts:
        return None
    satisfied = set(project_practical_credit(assignment, baseline, receipts)['satisfied_keys'])
    keys = set(assignment['completion_keys'])
    if not keys <= satisfied:
        return None
    endpoint_kind = 'requested_job_handoff' if assignment['endpoint'] == 'usable_handoff' else 'requested_job_outputs'
    last = receipts[-1]
    if not any(item['key'] in keys and item['satisfied'] and item['predicate']['kind'] == endpoint_kind
               for item in last['validations']):
        return None
    return {'endpoint': assignment['endpoint'], 'operation_key': last['operation_key'],
            'receipt_sha256': digest(last), 'validation_keys': sorted(keys)}


def internal_summary(view):
    assignment = view.parent_input['assignment']
    baseline = baseline_validations(assignment)
    receipts, receipt_refs, handoff_refs, actions = [], [], [], []
    for unit in view.outcomes:
        outcome = unit['outcome']
        command = unit['arguments']['command']
        if outcome['status'] != 'completed':
            actions.append({'command': command, 'status': outcome['status'], 'feedback': outcome['feedback']})
            continue
        receipt = outcome['result']
        receipts.append(receipt)
        receipt_refs.extend(outcome['record_refs'])
        job = receipt['outcome']['facts'].get('requested_job')
        if job is not None and job['handoff'] is not None:
            handoff_refs.extend(outcome['record_refs'])
        actions.append({'command': command, 'status': 'completed', 'receipt_ref': outcome['record_refs'][0],
                        'operation_ref': outcome['operation_ref'],
                        'context_after': receipt['context_after'],
                        'satisfied': sorted(item['key'] for item in receipt['validations'] if item['satisfied'])})
    progress = project_practical_credit(assignment, baseline, receipts)
    summary = {'assignment': assignment, 'input_refs': view.parent_input['input_refs'], 'baseline': baseline,
               'receipts': receipts, 'receipt_refs': receipt_refs, 'handoff_refs': list(dict.fromkeys(handoff_refs)),
               'context': receipts[-1]['context_after'] if receipts else assignment['initial_context'],
               'progress': progress, 'credit': progress['credit'],
               'completion': completion_of(assignment, baseline, receipts), 'actions': actions,
               'last_receipt': receipts[-1] if receipts else None}
    if view.controller_state is not None:
        summary['controller'] = view.controller_state.as_record()
    return summary
