from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_behavior import PlanningAllocationBehavior


class TestPlanningAllocationBehavior(PlanningAllocationBehavior):
    axis = 'a110'
    binding_path = 'hpc_work_planning/hpc_allocation_execution'
    role = 'hpc_execution'
