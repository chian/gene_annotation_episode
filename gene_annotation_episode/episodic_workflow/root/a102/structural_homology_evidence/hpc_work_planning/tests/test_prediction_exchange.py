from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_parent_exchange import PredictionParentExchangeChecks


class TestPredictionExchange(PredictionParentExchangeChecks):
    axis = 'a102'
    parent_path = 'structural_homology_evidence/hpc_work_planning'
