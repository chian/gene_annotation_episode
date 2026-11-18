from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class TestPlanningAllocationTaskBehavior(PlanningAllocationTaskBehavior):
    axis = 'a104'
    binding_path = 'evolutionary_history_evidence/hpc_work_planning'
    role = 'hpc'
