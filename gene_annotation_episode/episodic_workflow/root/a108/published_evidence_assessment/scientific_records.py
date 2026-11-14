from __future__ import annotations
'scientific records for this private A108 episode.'
from gene_annotation_episode.episodic_workflow.root.a108.published_evidence_assessment.source_contracts import ContractError

class LiteratureScientificRecords:

    def _population_routes(self):
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_grading_storage import PROVIDER as G_PROVIDER, NAMESPACE as G_NAMESPACE, REQUESTED as G_REQUESTED
        from gene_annotation_episode.episodic_workflow.root.a108.library.literature_a108_aggregation_storage import PROVIDER as A_PROVIDER, NAMESPACE as A_NAMESPACE, REQUESTED as A_REQUESTED
        return ((G_NAMESPACE, G_REQUESTED, G_PROVIDER, self._a108_grading_repository), (A_NAMESPACE, A_REQUESTED, A_PROVIDER, self._a108_aggregation_repository))

    def automatic_score_judgments(self, context):
        return []

    def complete_score_judgment(self, context, judgment_ref, response=None, *, provenance, failure=None):
        raise ContractError('a108_automatic_judgment_unavailable')
