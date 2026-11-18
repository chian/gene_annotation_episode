from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_parent_exchange import PredictionParentExchangeChecks


class TestPredictionExchange(PredictionParentExchangeChecks):
    axis = 'a103'
    parent_path = 'gene_context_evidence/hpc_work_planning'
