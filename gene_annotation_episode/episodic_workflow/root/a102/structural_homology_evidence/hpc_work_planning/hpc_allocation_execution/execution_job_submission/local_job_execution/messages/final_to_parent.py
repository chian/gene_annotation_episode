"""The return. Always returned: the Episode's credit (handed in ``completion``), the handoff finding (the job's
completion, requirement states, requested job facts and receipt digests), and the saved command receipts: their
completion state, digests and the records that hold them, returned in custody. The facts the parent may select are
the optional fields."""
from method_loop import Field, RecordForm

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.practical_execution_records import digest

REQUIREMENT_FORM = RecordForm({
    'key': Field('text', 'The requirement key'),
    'credit': Field('number', 'The credit the requirement is worth'),
    'satisfied': Field('boolean', 'Whether the saved receipts currently satisfy the requirement'),
})
FINDING_FORM = RecordForm({
    'assignment_id': Field('text', 'The identity of the executed assignment'),
    'assignment_sha256': Field('text', 'The digest of the executed assignment'),
    'endpoint': Field('text', 'The endpoint the assignment asked for'),
    'completion_target': Field('number', 'The total requirement credit of the assignment'),
    'completed': Field('boolean', 'Whether the assigned endpoint has a verified completion proof'),
    'completion_proof': Field('record', 'The completion proof, when completed', required=False),
    'requested_job': Field('record', 'The requested job as the latest receipt that observed it recorded it, '
                                     'when one did', required=False),
    'satisfied_keys': Field('list', 'The requirement keys the saved receipts satisfy'),
    'requirements': Field('list', 'Each requirement with its credit and state', items=REQUIREMENT_FORM),
    'receipt_sha256s': Field('list', 'The digests of the saved command receipts, in order'),
    'ended_by': Field('text', 'How the system ended the Episode'),
    'units': Field('integer', 'The number of commands run'),
})
RETURN_FORM = RecordForm({
    'credit': Field('number', "The Episode's credit when its controller stopped it"),
    'finding': Field('record', 'The job handoff finding', form=FINDING_FORM),
    'practical_completed': Field('boolean', 'Whether original requested endpoint predicates have a saved '
                                            'validated completion'),
    'practical_receipt_digests': Field('list', 'Host-recorded digests of the original selected command receipts'),
    'practical_receipt_refs': Field('record_refs', 'The original selected command receipts, published as source '
                                                   'records, returned in custody'),
    'practical_receipt_artifact_refs': Field('record_refs', 'The artifacts the receipt sources name (their body and '
                                                            'their assignment snapshot)'),
    'execution_handoff_refs': Field('record_refs', 'The command receipts that are returnable handoffs of this '
                                                   'exact assignment', required=False),
    'execution_result_refs': Field('record_refs', 'Actual requested result acquisitions available to this '
                                                  'episode (none: it acquires no result)', required=False),
    'execution_file_source_refs': Field('record_refs', 'Selected local file sources retained by this episode '
                                                       '(none: it captures no file)', required=False),
    'execution_file_capture_outcomes': Field('list', 'Selected file availability, status and custody '
                                                     'qualifications (none: it captures no file)', required=False),
    'execution_completed': Field('boolean', 'Whether the assigned endpoint has verified completion information',
                                 required=False),
    'execution_result_origin': Field('record', 'Acquisition semantics of a retained result (empty: this episode '
                                               'retains none; the form has no null)', required=False),
})


def facts(summary):
    """The facts this Episode recorded : completion, receipt digests, the receipt records, and
    the receipts that are returnable handoffs."""
    receipts = summary['receipts']
    handoffs = [ref for ref, receipt in zip(summary['receipt_refs'], receipts)
                if any(item['satisfied'] and item['predicate']['kind'] == 'requested_job_handoff'
                       for item in receipt['validations'])]
    completed = summary['execution_completion'] is not None
    return {'practical_completed': completed,
            'practical_receipt_digests': [digest(receipt) for receipt in receipts],
            'practical_receipt_refs': list(summary['receipt_refs']),
            'practical_receipt_artifact_refs': list(summary['receipt_artifact_refs']),
            'execution_handoff_refs': handoffs,
            'execution_result_refs': [], 'execution_file_source_refs': [], 'execution_file_capture_outcomes': [],
            'execution_completed': completed, 'execution_result_origin': {}}


def final_to_parent(summary, completion, selection):
    recorded = facts(summary)
    progress = summary['execution_progress']
    assignment = summary['assignment']
    finding = {'assignment_id': assignment['assignment_id'], 'assignment_sha256': digest(assignment),
               'endpoint': assignment['endpoint'], 'completion_target': summary['completion_target'],
               'completed': recorded['practical_completed'],
               'satisfied_keys': progress['satisfied_keys'],
               'requirements': [{name: row[name] for name in ('key', 'credit', 'satisfied')}
                                for row in progress['requirements']],
               'receipt_sha256s': recorded['practical_receipt_digests'],
               'ended_by': completion['ended_by'], 'units': completion['units_consumed']}
    if summary['execution_completion'] is not None:
        finding['completion_proof'] = summary['execution_completion']
    if summary['requested_job'] is not None:
        finding['requested_job'] = summary['requested_job']
    result = {'credit': completion['credit'], 'finding': finding}
    for name in ('practical_completed', 'practical_receipt_digests', 'practical_receipt_refs',
                 'practical_receipt_artifact_refs'):
        result[name] = recorded[name]
    for name in selection:
        result[name] = recorded[name]
    return result
