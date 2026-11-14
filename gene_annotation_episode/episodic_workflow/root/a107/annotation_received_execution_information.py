"""Annotation selects its separately declared original received result readers."""

def received_execution_information(context, catalog, *, configuration_only=False):
    return catalog.configured('@annotation') if configuration_only else catalog.received('@annotation', context)
