"""What the parent takes from a launch child's return: the original handoff records it returned, whether its
requested endpoint was verified, and its own credit and finding as information for the summary.

The old ``receive_report`` (``from_child_local_job_execution``, ``from_child_hpc_job_execution``, identical) only
passed the admitted form to the progress provider and the receipts ledger; both are system custody now. The
handoff references counted as usable handoffs through ``_received`` (``targets.usable_handoff``); here a launch
child's report of an established handoff (``execution_completed`` with handoff references) is the count. Both
children return ``execution_handoff_refs`` and ``execution_completed`` (selected by ``msg_to_child``)."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'credit': result['credit'], 'finding': result['finding']}
