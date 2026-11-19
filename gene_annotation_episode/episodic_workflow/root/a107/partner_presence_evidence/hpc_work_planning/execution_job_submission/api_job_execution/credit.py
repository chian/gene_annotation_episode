"""Credit (carried from ``credit.py`` and ``closed_credit.py``).

The credit is the one the API service's operational credit view gave after the last unit that reported one: the
handoff and the acquired records, priced with the positive units ``handoff_unit`` and ``acquired_record_unit`` of
this episode's settings. The tool passes the units to the service and returns the credit in its outcome, so
``credit`` has no service and reads it from the summary. Never bounded, clamped or rescaled. The old frozen closed
view (``closed_credit.py``: "later delivery never reprices it") was a check against the old journal and receipt
tables and is not carried.
"""
import math


def credit(summary, records):
    value = summary['credit']
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('api_job_credit_must_be_a_finite_number')
    return value
