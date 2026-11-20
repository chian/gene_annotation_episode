"""Credit: ``handoff_unit`` for each distinct resource whose request got a usable handoff in this Episode and had
none when it began, plus ``acquired_record_unit`` times the acquired fraction, which is ``0.0`` for a launch (a
launch acquires no result). Nothing bounds, clamps or rescales it.

The usable handoffs are in the summary: each launch child's report says whether its handoff exists and names the
handoff records it returned, which this Episode then holds; the resource is the one the child was commissioned
on."""


def credit(summary, records):
    handoff_count = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    acquired_fraction = 0.0
    return summary['handoff_unit'] * handoff_count + summary['acquired_record_unit'] * acquired_fraction
