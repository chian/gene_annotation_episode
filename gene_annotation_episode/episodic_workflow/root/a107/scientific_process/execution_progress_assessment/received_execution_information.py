"""This recipient selects its explicitly declared original A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('scientific_process/execution_progress_assessment') if configuration_only else catalog.received('scientific_process/execution_progress_assessment', context)
