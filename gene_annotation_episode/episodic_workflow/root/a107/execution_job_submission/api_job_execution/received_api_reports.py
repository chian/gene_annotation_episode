"""This recipient selects its separately declared A107 API reader authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('execution_job_submission/api_job_execution') if configuration_only else catalog.received('execution_job_submission/api_job_execution', context)
