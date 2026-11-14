"""This recipient selects its explicitly declared original A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('hpc_work_planning/execution_progress_assessment') if configuration_only else catalog.received('hpc_work_planning/execution_progress_assessment', context)
