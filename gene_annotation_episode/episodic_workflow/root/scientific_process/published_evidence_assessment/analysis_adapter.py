"""Read the explicitly configured scientific adapter; choose or acquire nothing."""

def selected_adapter(service, selection):
    if selection is None:
        return None
    return service.scientific_adapters.get((selection['adapter_id'], selection['adapter_version']))

