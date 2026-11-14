"""This recipient selects its explicitly declared original A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('execution_progress_assessment') if configuration_only else catalog.received('execution_progress_assessment', context)
