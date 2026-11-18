from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_task_behavior import PlanningAllocationTaskBehavior


class TestPlanningAllocationTaskBehavior(PlanningAllocationTaskBehavior):
    axis = 'a102'
    binding_path = 'structural_homology_evidence/hpc_work_planning'
    role = 'hpc'
