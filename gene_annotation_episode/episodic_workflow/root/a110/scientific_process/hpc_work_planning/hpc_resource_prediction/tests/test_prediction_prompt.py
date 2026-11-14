from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_prompt_behavior import PredictionPromptChecks


class TestPredictionPrompt(PredictionPromptChecks):
    axis = 'a110'
    binding_path = 'scientific_process/hpc_work_planning/hpc_resource_prediction'
