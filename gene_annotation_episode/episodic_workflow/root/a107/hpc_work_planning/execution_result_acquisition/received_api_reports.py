"""This recipient selects its separately declared A107 API reader authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('hpc_work_planning/execution_result_acquisition') if configuration_only else catalog.received('hpc_work_planning/execution_result_acquisition', context)
