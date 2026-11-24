"""Credit (carried from ``credit.py``: ``project_credit`` / ``credit_view``; the old ``_api_operational_credit``, ``operational_credit_from_identities`` over new handoff and result identities).

The old live credit of this role was the one the API service executor's credit view gave
(``api_execution.credit_view``, built with the positive units ``handoff_unit`` and ``acquired_record_unit``). The
tool that ran the operation passes those units to the ``job_access`` service and returns the executor's credit in
its outcome (``task.service_operation``), so ``credit`` reads it from the summary and has no service. A wait, a
capabilities read, a lookup and a failed operation report none and keep the credit the last unit that reported one
gave. Never bounded, clamped or rescaled. The old frozen closed view (``_closed_*``) is old-journal bookkeeping and
is not carried: the system's closure credit is the credit the controller last saw.
"""
import math


def credit(summary, records):
    value = summary['credit']
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('api_job_credit_must_be_a_finite_number')
    return value
