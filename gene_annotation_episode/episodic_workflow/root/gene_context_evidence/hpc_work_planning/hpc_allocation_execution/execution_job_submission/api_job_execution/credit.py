"""Credit: the operational credit of the API job. A usable original handoff earns the handoff unit once, and each
record the service operations acquired earns the acquired-record unit (the two positive units of the old
configuration, ``handoff_unit`` and ``acquired_record_unit``). The units and the counts come from the tools'
outcomes through the summary: the episode's credit has no services and no settings.

Credit is not bounded here. It may pass the commissioned target when the operations acquire records beyond the
handoff (the completion controller then raises)."""


def credit(summary, records):
    units = summary['credit_units']
    if units is None:
        return 0.0
    handoff = units['handoff_unit'] if summary['handoff_established'] else 0.0
    return handoff + units['acquired_record_unit'] * summary['acquired_record_count']
