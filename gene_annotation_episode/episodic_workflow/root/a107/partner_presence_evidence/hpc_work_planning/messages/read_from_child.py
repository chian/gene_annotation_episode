"""What the parent takes from a child's admitted result (carried from ``from_child_execution_job_submission.py``,
``from_child_execution_progress_assessment.py``, ``from_child_execution_result_acquisition.py``,
``from_child_hpc_allocation_execution.py`` and ``from_child_hpc_resource_prediction.py``).

Not carried: the old ``LaunchReceiptCustody.original_launch_handoff`` (it recovered the plan's handoff from the old
runner's committed outcome tables across a report repair: the launch child's admitted result names its handoff records,
the system receipts them and the unit outcome is in ``view.outcomes``), the old ``receive_progress`` (it admitted the
monitor's ``episode_progress`` references into the old progress provider's received view: the monitor returns its
progress observations in typed fields and records, read here and in the summary), and the old ``receive_report``,
``receive_allocation_report`` and ``receive_prediction_report`` (the recorded admission, progress forms, receipts,
timing receipts and tool attributions: custody and the typed result replace them). A child's own ``credit`` is
information for the summary and is not added to this episode's credit."""


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
    if slot in ('hpc_prediction', 'hpc_execution'):
        return {'slot': slot, 'child_credit': result['credit'], 'hpc_credit': result['hpc_credit'],
                'model_ref': result['hpc_model_ref'], 'accepted_obligations': list(result['hpc_accepted_obligations']),
                'result_refs': list(result['hpc_result_refs']),
                **({'result_artifact_refs': list(result['hpc_result_artifact_refs'])}
                   if slot == 'hpc_execution' else {})}
    raise LookupError('hpc_work_planning_has_no_slot:' + slot)
