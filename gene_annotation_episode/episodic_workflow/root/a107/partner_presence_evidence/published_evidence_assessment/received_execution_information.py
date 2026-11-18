"""This recipient selects its explicitly declared A107 result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('partner_presence_evidence/published_evidence_assessment') if configuration_only else catalog.received('partner_presence_evidence/published_evidence_assessment', context)
