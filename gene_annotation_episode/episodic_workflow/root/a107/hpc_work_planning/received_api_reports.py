"""This recipient selects its separately declared A107 API reader authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('hpc_work_planning') if configuration_only else catalog.received('hpc_work_planning', context)
