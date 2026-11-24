"""What the parent takes from a child's admitted result (carried from ``from_child_execution_job_submission.py``,
``from_child_execution_progress_assessment.py``, ``from_child_execution_result_acquisition.py``,
``from_child_hpc_allocation_execution.py`` and ``from_child_hpc_resource_prediction.py``).

A sister returns controlled data: its ``credit`` (was it productive), its ``finding`` (counts and a boolean of what
the ledger holds after it) and, in custody, the ledger rows it holds (``hpc_ledger_refs``: the system receipts
them, and the summary reads the ledger with them from then on) and the result sources it was asked for. The report
keeps the credit and the counts for the next decision; the rows are not listed in it.

Not carried: the old ``LaunchReceiptCustody.original_launch_handoff``, ``receive_progress``, ``receive_report``,
``receive_allocation_report`` and ``receive_prediction_report`` (recorded admission, progress forms, receipts,
timing receipts and tool attributions: custody and the typed result replace them). A child's own ``credit`` is
information for the summary and is not added to this episode's credit: the ledger's credit already counts what the
sister recorded."""


def read_from_child(slot, result, summary, records):
    if slot == 'launch':
        return {'slot': slot, 'child_credit': result['credit'],
                'handoff_refs': list(result['execution_handoff_refs']),
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
                'result_refs': list(result['execution_result_refs']),
                'result_artifact_refs': list(result['execution_result_artifact_refs']),
                'completed': result['execution_completed']}
    if slot == 'hpc_prediction':
        return {'slot': slot, 'child_credit': result['credit'], **result['finding']}
    if slot == 'hpc_execution':
        return {'slot': slot, 'child_credit': result['credit'], **result['finding'],
                'result_refs': list(result['hpc_result_refs']),
                'result_artifact_refs': list(result['hpc_result_artifact_refs'])}
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
