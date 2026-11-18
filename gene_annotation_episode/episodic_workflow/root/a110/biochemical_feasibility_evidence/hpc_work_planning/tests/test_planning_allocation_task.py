from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class TestPlanningAllocationTaskBehavior(PlanningAllocationTaskBehavior):
    axis = 'a110'
    binding_path = 'biochemical_feasibility_evidence/hpc_work_planning'
    role = 'hpc'
