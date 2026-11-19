"""Credit: ``completion_target`` (the credit of one usable execution handoff) for each distinct usable execution
handoff the Episode holds.

The old credit was ``services.bound_role_credit(context, receiver_selection)``: the ``operational`` credit of the
resource adapters, defined outside this folder. The tools and children of this Episode return what the adapters
recorded, so the number is read from the summary, which keeps the latest usable check of each handoff identity
(capability binding and execution handle; ``messages/internal_summary.py``). Credit has no services. A unit that
changes no handoff (a lookup, a capability read, a reasoning commit) leaves the credit as it was. Nothing here bounds,
clamps or rescales it."""


def credit(summary, records):
    return summary['completion_target'] * len(summary['execution_handoffs'])
