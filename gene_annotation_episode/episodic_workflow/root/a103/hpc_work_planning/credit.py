"""Private credit for A103 hpc."""
from __future__ import annotations





class HPCEpisodeCredit:
    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_hpc_role')
        return 'operational'

    def credit_view(self, context, receiver_selection):
        ledger = self.state(context)
        return ledger.credit_view()
