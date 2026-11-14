"""Private monitor credit behavior for A106."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a106.library.progress_information_credit import ProgressInformationCredit

class MonitorEpisodeCredit:

    def credit_kind(self, role):
        self._role(role)
        return 'monitoring'

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.bound_role_credit(context, receiver_selection)

    def information_credit(self, progress_reader, *, information_unit):
        """Select this monitor's received-information calculation with caller operands.

        The unit remains explicit even when a separate private yield binding is
        configured. External projectors still enter through credit_view unchanged.
        """
        return ProgressInformationCredit(progress_reader, information_unit=information_unit)
