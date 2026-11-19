"""What the parent takes from the API job execution child's admitted return (carried from
``from_child_api_job_execution.receive_report``). The old receiver recorded admission references, progress-provider
receipts, timing receipts and tool attributions: old-runner machinery (the system receipts the records a child
returns). What is kept is what the parent's report and credit read: the child's handoff references, the support
references it was asked for, whether it verified completion and its own finding."""


def read_from_child(slot, result, summary, records):
    if slot != 'launch_api':
        raise ValueError('execution_job_submission_slot_unknown:' + slot)
    return {'slot': slot, 'handoff_refs': list(result['execution_handoff_refs']),
            'support_refs': list(result['bvbrc_appservice_support_refs']),
            'completed': result['execution_completed'], 'finding': result['finding']}
