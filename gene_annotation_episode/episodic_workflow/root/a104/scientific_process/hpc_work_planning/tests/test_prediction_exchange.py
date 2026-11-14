from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_parent_exchange import PredictionParentExchangeChecks


class TestPredictionExchange(PredictionParentExchangeChecks):
    axis = 'a104'
    parent_path = 'scientific_process/hpc_work_planning'
