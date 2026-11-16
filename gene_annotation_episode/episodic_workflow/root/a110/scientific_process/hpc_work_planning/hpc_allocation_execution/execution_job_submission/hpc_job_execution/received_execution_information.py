"""This recipient selects its explicitly declared A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution') if configuration_only else catalog.received('scientific_process/hpc_work_planning/hpc_allocation_execution/execution_job_submission/hpc_job_execution', context)
