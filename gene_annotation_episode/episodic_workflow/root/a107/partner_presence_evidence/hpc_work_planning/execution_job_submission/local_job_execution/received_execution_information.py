"""This recipient selects its explicitly declared A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('partner_presence_evidence/hpc_work_planning/execution_job_submission/local_job_execution') if configuration_only else catalog.received('partner_presence_evidence/hpc_work_planning/execution_job_submission/local_job_execution', context)
