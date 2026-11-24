"""Credit: the old operational credit of the HPC episode (``HPCEpisodeCredit.credit_kind`` 'operational' and
``credit_view`` = ``HPCLedger.credit_view()``): the signed measured credit of the commission's ledger (accepted actual
results, model improvement and fixed prospective forecast validation; repeated polling adds none). Unbounded, never
clamped and never rescaled.

``credit`` has no services, so it cannot open the ledger: every tool of the task returns the ledger's decision state
after its effect, and its ``hpc_credit`` is the credit view the tool read. The summary holds the latest state. Before
the first tool unit the ledger has not been read and the credit is 0.0 (see the blocked file: the old controller read
the ledger's credit at construction)."""


def credit(summary, records):
    state = summary['state']
    if state is None:
        return 0.0
    return state['hpc_credit']['credit']
