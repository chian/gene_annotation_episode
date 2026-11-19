"""What the parent takes from a child's admitted result (carried from ``from_child_execution_job_submission.py`` and
``from_child_execution_progress_assessment.py``; the results child had no receiver of its own).

Not carried: the old ``LaunchReceiptCustody.original_launch_handoff`` (it recovered the plan's handoff from the old
runner's committed outcome tables across a report repair: the launch child's admitted result names its handoff
records, the system receipts them, and the unit outcome is in ``view.outcomes``) and the old ``receive_progress``
(it admitted the monitor's ``episode_progress`` references into the old progress provider's received view: the
monitor returns its progress observations in typed fields and records, read here and in the summary)."""


def read_from_child(slot, result, summary, records):
    if slot == 'launch':
        return {'slot': slot, 'child_credit': result['credit'],
                'handoff_refs': list(result['execution_handoff_refs']),
                'artifact_refs': list(result['execution_handoff_artifact_refs']),
                'completed': result['execution_completed']}
    if slot == 'monitor':
        return {'slot': slot, 'child_credit': result['credit'],
                'progress_refs': list(result['monitoring_progress_refs']),
                'execution_state': result['monitoring_execution_state']['value'],
                'result_available': result['monitoring_result_available']['value'],
                'observed_at_unix_seconds': result['monitoring_observed_at_unix_seconds']['value'],
                'committed_record_refs': list(result['monitoring_committed_record_refs']),
                'progress_snapshots': result['monitoring_progress_snapshots']}
    if slot == 'results':
        return {'slot': slot, 'child_credit': result['credit'],
                'result_refs': list(result['execution_result_refs']), 'completed': result['execution_completed']}
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
