"""What the parent takes from a launch child's return: the original handoff records it returned, whether its
requested endpoint was verified, and its own credit and finding as information for the summary.

The old ``receive_report`` (identical for the three children) only passed the admitted form to the progress
provider and the receipts ledger; both are system custody now. The handoff references counted as usable handoffs
through ``received_records._received`` (``targets.usable_handoff``); here a launch child's report of an established
handoff (``execution_completed`` with handoff references) is the count. All three children return
``execution_handoff_refs`` and ``execution_completed`` (the API child always, the other two when selected by
``msg_to_child``)."""


def read_from_child(slot, result, summary, records):
    return {'handoff_refs': list(result['execution_handoff_refs']), 'completed': result['execution_completed'],
            'credit': result['credit'], 'finding': result['finding']}
