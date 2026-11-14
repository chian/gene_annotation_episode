from gene_annotation_episode.episodic_workflow.root.tests.hpc_calculation_behavior import HpcCalculationConnectionChecks


class TestCalculationConnections(HpcCalculationConnectionChecks):
    axis = 'a110'
    binding_path = 'hpc_work_planning/hpc_resource_prediction'
    role = 'hpc_prediction'
