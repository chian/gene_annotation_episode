"""Credit: the operational credit of the assigned resource, as the last unit that asked for it returned it.

Old ``credit.py``: ``credit_kind`` was ``operational`` for every resource role and ``credit_view(context,
receiver_selection)`` was ``services.bound_role_credit``. ``credit`` here has no services, so the tool that obtained
the value (every resource tool and every reasoning commit asks the resource service for its ``credit_view``)
returned it in its outcome and the summary holds the latest one. A wait carries the credit unchanged. Nothing is
bounded."""
import math


def credit(summary, records):
    view = summary['credit_view']
    if view is None:
        return 0.0
    value = view['credit']
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('resource_credit_view_credit_must_be_a_finite_number:' + repr(value)[:80])
    return value
