"""This recipient selects its explicitly declared A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('execution_progress_assessment') if configuration_only else catalog.received('execution_progress_assessment', context)
