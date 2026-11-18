"""Private A110 reaction records."""
from __future__ import annotations

class LiteratureReactionRecords:

    def literature_reaction_repository(self):
        """Access selected reported-reaction constraints and resource budgets."""
        from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionRepository
        if not hasattr(self, '_literature_reaction_repository'):
            self._literature_reaction_repository = LiteratureReactionRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_reaction_repository

    def _population_routes(self, context=None):
        from gene_annotation_episode.episodic_workflow.root.a110.library.literature_component_binding import population_routes
        return population_routes(self.services)
