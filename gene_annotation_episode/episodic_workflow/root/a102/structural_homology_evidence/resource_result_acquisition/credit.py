"""Credit: one for each requested result file the Episode holds. The summary names the requested files a held
closure row of the job lists; a file counts when the Episode holds its artifact. A status check, a wait, a failed
fetch and a repeated fetch change nothing here and so earn nothing. Nothing is bounded or rescaled; the target of
the commission is the number of requested files (``yield_estimator.py``)."""


def credit(summary, records):
    return float(sum(1 for item in summary['acquired'] if records.holds(item['ref'])))
