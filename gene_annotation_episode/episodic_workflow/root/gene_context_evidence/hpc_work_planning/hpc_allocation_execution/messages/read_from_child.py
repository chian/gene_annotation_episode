"""What the parent takes from each child's return (carried from ``from_child_execution_job_submission.py``
(``LaunchReceiptCustody``), ``from_child_execution_progress_assessment.py`` (``receive_progress``) and, for the
results child, the generic child path).

``launch``: the handoff records the Launch child returned in custody (the old ``execution_handoff_refs``) and
whether its handoff is complete; ``hpc_handoff`` attaches one of them to the frozen plan. ``monitor``: the
progress observations the monitor delivered, each a readable observation (one the return carries a snapshot of;
the old provider read of each reference is the system's custody and the return form); the old recording of the
delivery under its operation key is the system's. ``results``: the retained result records. The children's
credits are returned for the summary and never added: "launch-local credits are not added again"."""


def read_from_child(slot, result, summary, records):
    if slot == 'launch':
        return {'slot': slot, 'handoff_refs': list(result['execution_handoff_refs']),
                'completed': result['execution_completed'], 'child_credit': result['credit'],
                'child_finding': result['finding']}
    if slot == 'monitor':
        refs = result['monitoring_progress_refs']
        snapshots = result['monitoring_progress_snapshots']
        missing = [ref for ref in refs if ref not in snapshots]
        if missing:
            raise ValueError('monitor_child_progress_not_a_readable_observation:' + missing[0])
        return {'slot': slot, 'progress_refs': list(dict.fromkeys(refs)), 'progress_snapshots': dict(snapshots),
                'child_credit': result['credit'], 'child_finding': result['finding']}
    if slot == 'results':
        return {'slot': slot, 'result_refs': list(result['execution_result_refs']),
                'completed': result['execution_completed'], 'child_credit': result['credit'],
                'child_finding': result['finding']}
    raise LookupError('hpc_allocation_execution_has_no_slot:' + slot)
