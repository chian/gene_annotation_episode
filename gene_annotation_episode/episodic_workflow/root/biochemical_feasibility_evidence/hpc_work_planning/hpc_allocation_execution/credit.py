"""Credit: the owner ledger's credit view as the last tool outcome showed it (the old ``HPCEpisodeCredit``, kind
``operational``: ``credit_view`` read ``ledger.credit_view()`` as it stands and never recomputed it here).

The ledger's credit components are the accepted accomplishment (an obligation whose unit completed with return code
0 and whose result satisfies the caller's acceptance predicate), the model improvement and the fixed prospective
forecast validation. Polling, waiting and launching add nothing; launch-local credit is not added again, and a
child's returned credit is not summed in. ``credit`` has no services and no ledger: every tool of ``task.py`` returns
the credit view with its outcome (``ledger_view``), and ``internal_summary`` keeps the latest. Before any tool has
run the ledger has not been read, so the credit is zero. Never bounded, clamped or rescaled."""


def credit(summary, records):
    view = summary['ledger_view']
    return 0.0 if view is None else float(view['credit']['credit'])
