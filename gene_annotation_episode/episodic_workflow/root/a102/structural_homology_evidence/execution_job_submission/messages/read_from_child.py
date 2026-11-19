"""What the parent takes from a resource child's admitted return (carried from ``from_child_api_job_execution``,
``from_child_local_job_execution`` and ``from_child_hpc_job_execution`` (``receive_report``: the same text in the
three files)). The old receiver recorded admission references, progress-provider receipts, timing receipts and tool
attributions: old-runner machinery (the system receipts the records a child returns). What is kept is what the
parent's report and credit read: the child's handoff references, whether it verified completion, its own credit
and its finding."""

SLOTS = ('launch_api', 'launch_local', 'launch_hpc')


def read_from_child(slot, result, summary, records):
    if slot not in SLOTS:
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    return {'slot': slot, 'handoff_refs': list(result['execution_handoff_refs']),
            'completed': result['execution_completed'], 'child_credit': result['credit'],
            'finding': result['finding']}
