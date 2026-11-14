from gene_annotation_episode.episodic_workflow.root.tests.hpc_calculation_behavior import HpcCalculationConnectionChecks


class TestCalculationConnections(HpcCalculationConnectionChecks):
    axis = 'a104'
    binding_path = 'scientific_process/hpc_work_planning/hpc_allocation_execution'
    role = 'hpc_execution'
