from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class TestPlanningAllocationTaskBehavior(PlanningAllocationTaskBehavior):
    axis = 'a103'
    binding_path = 'hpc_work_planning/hpc_allocation_execution'
    role = 'hpc_execution'
