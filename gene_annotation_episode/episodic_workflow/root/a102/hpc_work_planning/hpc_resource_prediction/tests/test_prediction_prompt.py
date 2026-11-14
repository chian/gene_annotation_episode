from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_prompt_behavior import PredictionPromptChecks


class TestPredictionPrompt(PredictionPromptChecks):
    axis = 'a102'
    binding_path = 'hpc_work_planning/hpc_resource_prediction'
