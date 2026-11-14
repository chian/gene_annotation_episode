"""This recipient selects its explicitly declared original A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('scientific_process/hpc_work_planning/execution_progress_assessment') if configuration_only else catalog.received('scientific_process/hpc_work_planning/execution_progress_assessment', context)
