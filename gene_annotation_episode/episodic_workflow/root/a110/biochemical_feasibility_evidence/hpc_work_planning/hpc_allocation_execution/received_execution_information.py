"""This recipient selects its explicitly declared A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution') if configuration_only else catalog.received('biochemical_feasibility_evidence/hpc_work_planning/hpc_allocation_execution', context)
