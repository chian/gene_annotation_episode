"""Credit: what the HPC ledger of the commission gained while this episode worked on it (the old
``HPCEpisodeCredit``, kind ``operational``, read ``ledger.credit_view()``).

The ledger's credit components are the accepted accomplishment (an obligation whose unit completed with return code
0 and whose result satisfies the caller's acceptance predicate), the model improvement and the fixed prospective
forecast validation. Polling, waiting and launching add nothing; launch-local credit is not added again, and a
child's returned credit is not summed in. The ledger is shared: when this episode is commissioned it already holds
what the planner and the prediction sister earned, so the episode's credit is the ledger's credit now minus the
ledger's credit when this episode first read it (``entry_credit``: its first unit only reads). ``credit`` has no
services: every tool of ``task.py`` returns the ledger's credit view with its outcome (``ledger_view``) and
``internal_summary`` keeps the latest and the first. Before any tool has run the credit is zero. Never bounded,
clamped or rescaled."""


def credit(summary, records):
    view = summary['ledger_view']
    return 0.0 if view is None else float(view['credit']['credit'] - summary['entry_credit'])
