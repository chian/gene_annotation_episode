"""Credit: the operational credit of the API job. A usable original handoff earns the handoff unit once, and each
record the service operations acquired earns the acquired-record unit (the two positive units of the old
configuration, ``handoff_unit`` and ``acquired_record_unit``; old ``_api_operational_credit`` ->
``operational_credit_from_identities``, which counted new handoff identities and new result identities against
those the episode started with; the episode starts with none passed, so the counts are the handoffs and results
its own operations produced). The units and the counts come from the tools' outcomes through the summary: the
episode's credit has no services and no settings.

Credit is not bounded here. The controller is the accumulation controller, so credit beyond the handoff is not an error."""


def credit(summary, records):
    units = summary['credit_units']
    if units is None:
        return 0.0
    handoff = units['handoff_unit'] if summary['handoff_established'] else 0.0
    return handoff + units['acquired_record_unit'] * summary['acquired_record_count']
