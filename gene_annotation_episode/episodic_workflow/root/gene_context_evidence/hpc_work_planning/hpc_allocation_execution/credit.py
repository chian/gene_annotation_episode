"""Credit, carried from the old ``credit.py`` (``HPCEpisodeCredit``: credit kind ``operational``;
``credit_view`` = the HPC ledger's ``credit_view()``): the signed measured credit of the original ledger, that is
the accepted obligations' credit (each obligation's own ``credit``, counted once), the model improvement and the
fixed prospective forecast validation slots. Repeated polling adds none. Never bounded, clamped or rescaled.

``credit`` has no services and no ledger file, so it reads the credit view that the tool which last changed the
ledger returned in its outcome (``hpc_state['credit_view']``, carried in the summary); before any tool unit it is
the ledger credit the commission began with."""
import math


def credit(summary, records):
    value = summary['hpc']['credit_view']['credit']
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('finite_hpc_credit_required')
    return value
