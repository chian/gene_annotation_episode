from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_behavior import PredictionBehavior


class TestPrivatePrediction(PredictionBehavior):
    axis = 'a107'
    binding_path = 'partner_presence_evidence/hpc_work_planning/hpc_resource_prediction'
