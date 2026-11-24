"""What the parent takes from a launch child's return: the original handoff records it returned, whether its
requested endpoint was verified, and its own credit and finding as information for the summary.

The old ``receive_report`` (three identical copies, ``from_child_<role>_job_execution.py``) only passed the admitted
form to the progress provider, the receipts ledger and the timing-receipt table; all three are system custody now. A
handoff counted as usable through ``received_records._received`` (``targets.usable_handoff``); here a launch child's
report of an established handoff (``execution_completed`` with handoff references) is the count. All three children
return ``execution_handoff_refs`` and ``execution_completed`` (the API child always, the other two because
``msg_to_child`` selects them)."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'credit': result['credit'], 'finding': result['finding']}
