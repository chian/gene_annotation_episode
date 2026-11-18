from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class TestPlanningAllocationTaskBehavior(PlanningAllocationTaskBehavior):
    axis = 'a107'
    binding_path = 'partner_presence_evidence/hpc_work_planning'
    role = 'hpc'
