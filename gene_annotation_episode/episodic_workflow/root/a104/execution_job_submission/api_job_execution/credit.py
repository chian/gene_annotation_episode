"""Private A104 API credit."""
from __future__ import annotations

class APICredit:

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_execution_episode_role')
        return 'operational'

    def project_credit(self, context, receiver_selection):
        closed = self._closed_operational_credit_view(context, receiver_selection)
        return self._live_project_credit(context, receiver_selection) if closed is None else closed

    def _live_project_credit(self, context, receiver_selection):
        self.native_blast_masking_results.applies(context)
        self.native_blast_utility_results.applies(context)
        self.native_blast_standard_database_results is not None and self.native_blast_standard_database_results.applies(context)
        self.native_blast_database_results is not None and self.native_blast_database_results.applies(context)
        self.native_hmmer_preparation_results is not None and self.native_hmmer_preparation_results.applies(context)
        self.native_blast_results is not None and self.native_blast_results.applies(context)
        self.native_hmmer_results.applies(context)
        return self.api_execution.credit_view(context, receiver_selection)

    def credit_view(self, context, receiver_selection):
        return self.project_credit(context, receiver_selection)
