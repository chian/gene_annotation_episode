"""What the parent takes from a launch child's return: the original handoff records it returned, whether its
requested endpoint was verified, and its own credit and finding as information for the summary.

The old ``receive_report`` (three copies, ``from_child_<role>_job_execution.py``) only passed the admitted form to
the progress provider, the receipts ledger and the timing-receipt table; all three are system custody now. A handoff
counted as usable when the old receipts ledger's record was re-read through ``job_progress_provider.targets
.usable_handoff``; here a launch child's report of an established handoff (``execution_completed`` with handoff
references) is the count (BLOCKED-ON-JOB-SERVICE: handoff record kind). All three children declare
``execution_handoff_refs`` and ``execution_completed`` selectable and ``msg_to_child`` selects both."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'credit': result['credit'], 'finding': result['finding']}
