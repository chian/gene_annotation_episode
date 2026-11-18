"""This recipient selects its separately declared A107 API reader authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('partner_presence_evidence/hpc_work_planning/execution_progress_assessment') if configuration_only else catalog.received('partner_presence_evidence/hpc_work_planning/execution_progress_assessment', context)
