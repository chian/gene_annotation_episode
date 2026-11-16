"""This recipient selects its explicitly declared A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('scientific_process') if configuration_only else catalog.received('scientific_process', context)
