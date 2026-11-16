"""This recipient selects its explicitly declared A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('execution_job_submission/hpc_job_execution') if configuration_only else catalog.received('execution_job_submission/hpc_job_execution', context)
