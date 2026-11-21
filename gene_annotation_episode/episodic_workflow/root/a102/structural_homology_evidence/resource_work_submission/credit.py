"""Credit: what the Episode holds of a usable execution handoff, in the two units the commission's completion
target is split into (``read_from_parent``): one when it holds the handoff row of the launched work, the other
when it holds a check row that found that job in a known state. Both are job ledger rows in custody (returned by a
resource child, passed back by the commissioner, or written by this episode's own receiving check) and
``internal_summary`` reads them. A reading of a resource, a library lookup, a commission that returns no handoff
and a repeated check add nothing. The sum cannot pass the completion target; nothing is bounded or rescaled."""


def credit(summary, records):
    units = summary['launch_units']
    return float(units['handoff_unit'] * summary['handoff_held']
                 + units['check_unit'] * summary['usable_handoff_held'])
