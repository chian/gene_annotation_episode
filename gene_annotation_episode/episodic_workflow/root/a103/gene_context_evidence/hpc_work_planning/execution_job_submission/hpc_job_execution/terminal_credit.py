"""Private native terminal credit."""
from __future__ import annotations

class TerminalCredit:

    def credit_view(self, context, receiver_selection):
        return self.state(context).credit_view()

    def completion_for_action(self, context, operation_key):
        proof = self.state(context).completion_proof()
        return proof if proof is not None and proof['operation_key'] == operation_key else None
