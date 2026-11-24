"""Credit: the owner ledger's credit view as the units last showed it (the old ``HPCEpisodeCredit``, kind
``operational``: ``credit_view`` read ``ledger.credit_view()`` as it stands and never recomputed it here).

The ledger's credit components are the accepted accomplishment (an obligation whose unit completed with return code 0
and whose result satisfies the caller's acceptance predicate), the model improvement and the fixed prospective
forecast validation. Polling, waiting and launching add nothing; launch-local credit is not added again, and no
child's returned credit is summed in. ``credit`` has no services and no ledger file: every tool of ``task.py`` returns
the ledger's credit view with its outcome, and ``internal_summary`` keeps the latest (``ledger_credit``), taking the
ledger-wide credit the execution sister returned (its credit is that same ledger view) after a commission of it.
Before any unit has run the ledger has not been opened, so the credit is zero. Never bounded, clamped or rescaled."""


def credit(summary, records):
    return float(summary['ledger_credit'])
