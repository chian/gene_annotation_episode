"""What the parent takes from each child's return (old ``from_child_execution_job_submission.receive_report``,
``from_child_execution_progress_assessment.receive_progress`` and ``from_child_execution_result_acquisition.
receive_report``). The old functions only passed the admitted form to the progress provider and the receipts ledger;
both are system custody now. What stays is what the parent reads of each return: the original handoff records of the
launch (to be bound to the frozen plan by ``hpc_handoff``), the delivered progress observations of the monitor, and
the retained result records of the results child. Each child's own credit and finding are information for the
summary: the credit of this episode is the ledger's."""


def read_from_child(slot, result, summary, records):
    if slot == 'launch':
        return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
                'credit': result['credit'], 'finding': result['finding']}
    if slot == 'monitor':
        return {'progress_refs': list(result['monitoring_progress_refs']),
                'target_handle': result['monitoring_target_handle'],
                'execution_state': result['monitoring_execution_state']['value'],
                'result_available': result['monitoring_result_available']['value'],
                'observed_at_unix_seconds': result['monitoring_observed_at_unix_seconds']['value'],
                'credit': result['credit'], 'finding': result['finding']}
    if slot == 'results':
        return {'result_refs': list(result['execution_result_refs']), 'completed': result['execution_completed'],
                'credit': result['credit'], 'finding': result['finding']}
    raise ValueError('hpc_child_slot_unknown:' + slot)
