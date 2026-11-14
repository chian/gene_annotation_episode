from gene_annotation_episode.episodic_workflow.root.tests.hpc_allocation_parent_exchange import AllocationParentExchangeChecks


class TestAllocationParentExchange(AllocationParentExchangeChecks):
    axis = 'a110'
    parent_path = 'hpc_work_planning'
