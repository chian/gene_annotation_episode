"""Credit: the old operational credit (``LaunchCredit._live_project_credit``, ``credit_kind`` 'operational', binding
``execution_received_records_credit_v1``): ``handoff_unit`` for each distinct resource whose original request got a
usable handoff in this Episode and had none when it began, plus ``acquired_record_unit`` times the number of acquired
records (a launch acquires no result, as the old acquired fraction was fixed at 0). It is unbounded and never
clamped or rescaled.

The usable handoffs are in the summary: each launch child's report says whether its handoff was established and names
the handoff records it returned (the old provider test ``targets.usable_handoff`` of a received record is not asked of
a service here: credit has no services). The old ``_closed_credit_*`` snapshot (the view frozen at closure and
re-checked against ``runtime_forms``, ``runtime_episodes``, ``runtime_observations`` and the receipt-inheritance
tables) is old-runner machinery: the system hands the credit its controller last saw to ``final_to_parent``."""


def credit(summary, records):
    handoff_count = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    acquired_count = 0
    return summary['handoff_unit'] * handoff_count + summary['acquired_record_unit'] * acquired_count
