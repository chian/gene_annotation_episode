"""Credit (carried from ``credit.py`` and ``closed_credit.py``).

The credit is the one the API service executor's credit view gave after the last unit that reported one (the
executor is built with the positive units ``handoff_unit`` and ``acquired_record_unit`` of this episode's
settings; the tool passes them and returns the executor's credit in its outcome, so ``credit`` has no service).
Never bounded, clamped or rescaled. The old frozen closed view (``closed_credit.py``) was a check against the old
journal tables and is not carried.
"""
import math


def credit(summary, records):
    value = summary['credit']
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('api_job_credit_must_be_a_finite_number')
    return value
