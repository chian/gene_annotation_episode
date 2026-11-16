"""This recipient selects its explicitly declared A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment') if configuration_only else catalog.received('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', context)
