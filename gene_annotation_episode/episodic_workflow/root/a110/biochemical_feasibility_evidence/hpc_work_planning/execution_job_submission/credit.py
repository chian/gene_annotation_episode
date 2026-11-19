"""Credit: the handoff unit for each original request whose usable handoff this Episode obtained.

The old ``LaunchCredit._live_project_credit``: ``handoff_unit`` times the number of distinct resource_ids with a
usable received handoff that were not already handed off at the start (``credit_kind`` operational, binding
``execution_received_records_credit_v1``). The acquired-record part of the old formula was fixed at zero for a
launch and is not carried. Nothing bounds or rescales it. The usable handoffs are those the child units returned
(``internal_summary`` reads them from the unit outcomes); the old closed-credit snapshot machinery is the
system's now."""


def credit(summary, records):
    new = set(summary['handed_off_resource_ids']) - set(summary['initial_handed_off_resource_ids'])
    return summary['handoff_unit'] * len(new)
