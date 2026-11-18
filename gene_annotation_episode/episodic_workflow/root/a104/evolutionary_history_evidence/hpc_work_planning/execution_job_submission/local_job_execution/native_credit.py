"""Private original A104 LocalExecution service native_credit."""
from __future__ import annotations

class LocalExecutionNativeCredit:

    def credit_kind(self, role):
        return 'operational'

    def credit_view(self, context, receiver_selection):
        return self.state(context).credit_view()
