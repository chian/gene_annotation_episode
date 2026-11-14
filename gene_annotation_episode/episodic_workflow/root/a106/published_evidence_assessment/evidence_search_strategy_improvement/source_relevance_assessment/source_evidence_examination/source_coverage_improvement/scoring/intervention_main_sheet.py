class InterventionMainSheet:

    def _a106_subscore_repository(self):
        from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
        if not hasattr(self, '_a106_subscore_repo'):
            self._a106_subscore_repo = LiteratureA106SubscoreRepository(self.services.workflow.store, self.services.workflow.run_id)
        return self._a106_subscore_repo

    def automatic_score_judgments(self, context):
        return self._a106_subscore_repository().prepare_judgments(context)

    def complete_score_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        return self._a106_subscore_repository().complete_judgment(context, judgment_ref, response, provenance=provenance, failure=failure)
