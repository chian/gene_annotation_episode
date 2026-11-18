from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_behavior import PlanningAllocationBehavior


class TestPlanningAllocationBehavior(PlanningAllocationBehavior):
    axis = 'a103'
    binding_path = 'gene_context_evidence/hpc_work_planning/hpc_allocation_execution'
    role = 'hpc_execution'
