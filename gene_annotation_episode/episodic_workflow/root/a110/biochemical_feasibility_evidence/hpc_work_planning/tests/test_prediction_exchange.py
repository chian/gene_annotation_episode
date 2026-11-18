from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_parent_exchange import PredictionParentExchangeChecks


class TestPredictionExchange(PredictionParentExchangeChecks):
    axis = 'a110'
    parent_path = 'biochemical_feasibility_evidence/hpc_work_planning'
