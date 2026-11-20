"""Credit: the operational credit of the selected API resource (old ``credit_view`` -> ``services.bound_role_credit``,
the credit view of the selected resource adapter over the records the episode holds).

Credit has no services. The tool that operates the resource (``resource_operation`` in ``task.py``) asks the
resource adapter for its credit view after the operation and returns the number in its outcome as
``adapter_credit``; the summary carries the latest one. A unit that does not touch the resource (a lookup, a
wait, the capability read) changes nothing in the summary, so its credit is the same. Credit is used exactly as the
adapter measures it: never bounded, clamped or rescaled."""


def credit(summary, records):
    value = summary['adapter_credit']
    return 0.0 if value is None else value
