"""Private original A104 HPCExecution service native_credit."""
from __future__ import annotations

class HPCExecutionNativeCredit:

    def credit_kind(self, role):
        return 'operational'

    def credit_view(self, context, receiver_selection):
        return self.state(context).credit_view()
