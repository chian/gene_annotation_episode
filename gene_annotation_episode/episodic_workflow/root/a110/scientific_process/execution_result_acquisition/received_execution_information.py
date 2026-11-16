"""This recipient selects its explicitly declared A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('scientific_process/execution_result_acquisition') if configuration_only else catalog.received('scientific_process/execution_result_acquisition', context)
