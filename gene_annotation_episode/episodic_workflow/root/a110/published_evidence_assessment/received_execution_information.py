"""This recipient selects its explicitly declared original A110 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('published_evidence_assessment') if configuration_only else catalog.received('published_evidence_assessment', context)
