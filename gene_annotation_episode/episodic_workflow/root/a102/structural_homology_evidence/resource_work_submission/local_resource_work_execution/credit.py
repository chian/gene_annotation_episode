"""Credit: what the Episode holds of the launch, in the units of the commission. The handoff unit when it holds the
handoff row of the launched work; the check unit when it holds a receiving check row that found the job in a known
state. Both are read from the job ledger rows in custody (``internal_summary``). A reading of the resource, a
refused launch, a repeated check and a wait earn nothing here. The sum cannot pass the commission's target (the two
units); nothing is bounded or rescaled."""


def credit(summary, records):
    units = summary['credit_units']
    return float(units['handoff'] * summary['handoff_held'] + units['usable_check'] * summary['usable_check_held'])
