"""Credit: the operational credit of the launch role (old ``ResourceCredit.credit_view`` ->
``services.bound_role_credit``, the credit view of the resource adapters over what the episode holds;
``credit_kind`` was ``operational`` for every resource role, and the episode has no scientific credit of its own).

Credit has no services. Each resource tool of ``task.py`` asks the resource adapter service for its credit view and
returns the number in its outcome as ``adapter_credit``; the summary carries the latest one. A unit that does not
touch the adapters (a lookup, a wait, a reasoning commitment, a child commission) changes nothing in the summary, so
its credit is the same as before it (the old wait took ``last_observed_credit``). Credit is used exactly as the
adapter measures it: never bounded, clamped or rescaled."""


def credit(summary, records):
    value = summary['adapter_credit']
    return 0.0 if value is None else value
