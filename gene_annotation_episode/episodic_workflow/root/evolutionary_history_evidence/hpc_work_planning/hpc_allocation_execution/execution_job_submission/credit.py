"""Credit: the old operational credit (``credit_kind`` 'operational', binding
``execution_received_records_credit``). ``handoff_unit`` for each resource whose original request got a usable
handoff in this Episode and had none when it began, plus ``acquired_record_unit`` for each acquired result (the old
acquired fraction was fixed at 0: a launch acquires no results). It is unbounded, never clamped and never rescaled.

The handoffs are in the summary (each launch child's report says whether its handoff was established and names the
handoff records it returned); the old provider test ``targets.usable_handoff`` of a received record has no
counterpart, so no service or provider is read."""


def credit(summary, records):
    handoff_count = len(set(summary['handoff_resources']) - set(summary['received_handoff_resources']))
    acquired_count = 0
    return summary['handoff_unit'] * handoff_count + summary['acquired_record_unit'] * acquired_count
