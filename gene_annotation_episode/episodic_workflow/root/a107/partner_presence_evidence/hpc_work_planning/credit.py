"""Credit: what the HPC ledger of the commission gained while this episode owned the work (the old
``HPCEpisodeCredit``, kind ``operational``, read ``ledger.credit_view()``).

The ledger's credit components are the accepted accomplishment (an obligation whose unit completed with return code 0
and whose result satisfies the caller's acceptance predicate), the model improvement and the fixed prospective forecast
validation. Polling, waiting and launching add nothing; launch-local credit is not added again, and a child's returned
credit is not summed in: what a sister recorded is in the ledger, which the summary reads through custody
(``ledger_view``), so a sister's work is in the credit of the unit that commissioned it. A ledger that an earlier
episode of the commission left and the commissioner passed back already holds credit: this episode's credit is the
ledger's credit now minus the ledger's credit when this episode opened it (``entry_credit``, which ``hpc_open``
returned). Before the ledger is open the credit is zero. Never bounded, clamped or rescaled."""


def credit(summary, records):
    view = summary['ledger_view']
    return 0.0 if view is None else float(view['credit']['credit'] - summary['entry_credit'])
