"""This recipient selects its separately declared A107 API reader authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment') if configuration_only else catalog.received('hpc_work_planning/hpc_allocation_execution/execution_progress_assessment', context)
