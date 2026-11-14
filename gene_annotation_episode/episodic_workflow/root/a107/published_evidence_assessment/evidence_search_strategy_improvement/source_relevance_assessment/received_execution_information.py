"""This recipient selects its explicitly declared original A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment') if configuration_only else catalog.received('published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment', context)
