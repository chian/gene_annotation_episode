"""Original operational resource identity; no admission or route selection."""

def resource_identity(resource_id, configuration):
    """Workspace-independent identity; Aurora uses its established account."""
    if configuration['kind'] == 'pbs_ssh':
        return 'aurora:'+configuration['account']
    return resource_id

