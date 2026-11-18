from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_prompt_behavior import PredictionPromptChecks


class TestPredictionPrompt(PredictionPromptChecks):
    axis = 'a110'
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning/hpc_resource_prediction'
