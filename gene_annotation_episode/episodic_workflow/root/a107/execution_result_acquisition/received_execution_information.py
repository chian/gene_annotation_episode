"""This recipient selects its explicitly declared A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('execution_result_acquisition') if configuration_only else catalog.received('execution_result_acquisition', context)
