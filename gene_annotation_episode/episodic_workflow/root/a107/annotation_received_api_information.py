"""Annotation selects its separately declared original received API authority."""

def received_api_reports(context, catalog, *, configuration_only=False):
    return catalog.configured('@annotation') if configuration_only else catalog.received('@annotation', context)
