from gene_annotation_episode.episodic_workflow.root.tests.hpc_calculation_behavior import HpcCalculationConnectionChecks


class TestCalculationConnections(HpcCalculationConnectionChecks):
    axis = 'a104'
    binding_path = 'evolutionary_history_evidence/hpc_work_planning/hpc_resource_prediction'
    role = 'hpc_prediction'
