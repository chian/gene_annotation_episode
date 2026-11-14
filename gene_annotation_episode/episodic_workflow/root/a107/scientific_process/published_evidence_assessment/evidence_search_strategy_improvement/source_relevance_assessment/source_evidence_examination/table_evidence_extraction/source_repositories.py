"""Private A107 source repositories."""
from __future__ import annotations

class LiteratureRepositories:

    def literature_partner_repository(self):
        """Access selected condition-qualified experimental partner components."""
        from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
        if not hasattr(self, '_literature_partner_repository'):
            self._literature_partner_repository = LiteraturePartnerRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_partner_repository

    def _population_routes(self, context=None):
        from gene_annotation_episode.episodic_workflow.root.a107.library.partner_source_contracts import population_routes
        return population_routes(self.services)
