"""Private A102 literature_table structural sheet operations."""
from __future__ import annotations

class SourceStructuralSheetOperations:

    def literature_structure_repository(self):
        """Access selected source-model geometry and local-fit components."""
        from gene_annotation_episode.episodic_workflow.root.a102.literature_structure_storage import LiteratureStructureRepository
        if not hasattr(self, '_literature_structure_repository'):
            self._literature_structure_repository = LiteratureStructureRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._literature_structure_repository

    def _population_routes(self, context=None):
        if not self.structure_population:
            return ()
        from gene_annotation_episode.episodic_workflow.root.a102.a102_literature_bindings import population_route
        return (population_route(self),)
