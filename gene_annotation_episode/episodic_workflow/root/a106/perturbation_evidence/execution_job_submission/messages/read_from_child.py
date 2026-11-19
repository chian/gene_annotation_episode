"""What the parent takes from the API launch child's return: the original handoff records it returned, whether its
requested endpoint was verified, the AppService receipts and application outcomes it reported, and its own credit and
finding as information for the summary.

The old ``receive_report`` (``from_child_api_job_execution.py``) only passed the admitted form to the progress
provider, the receipts ledger and the timing-receipt table; all three are system custody now. A handoff counted as
usable when the old receipts ledger's record was re-read through ``job_progress_provider.targets.usable_handoff``;
here the child's report of an established handoff (``execution_completed`` with handoff references) is the count
(BLOCKED-ON-JOB-SERVICE: handoff record kind)."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'support_refs': list(result['bvbrc_appservice_support_refs']),
            'outcomes': list(result['bvbrc_application_outcomes']),
            'credit': result['credit'], 'finding': result['finding']}
