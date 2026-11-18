from gene_annotation_episode.episodic_workflow.root.tests.hpc_planning_allocation_behavior import PlanningAllocationBehavior


class TestPlanningAllocationBehavior(PlanningAllocationBehavior):
    axis = 'a107'
    binding_path = 'partner_presence_evidence/hpc_work_planning'
    role = 'hpc'
