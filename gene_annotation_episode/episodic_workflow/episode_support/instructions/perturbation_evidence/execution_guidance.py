"""Execution recipes for the actual tool catalog, not a second tool registry."""
from pathlib import Path


ROOT = Path(__file__).parents[1] / 'execution'


def recipe(name, resource):
    if resource not in ('api', 'local', 'hpc'):
        raise ValueError('actual_execution_resource_kind_required')
    sections = ['planning', resource]
    return 'Execution recipe for '+name+' ('+resource+')\n\n' + '\n\n'.join(
        (ROOT/(section+'.md')).read_text().strip() for section in sections)


def resource_identity(resource_id, configuration):
    """Workspace-independent identity; Aurora uses its established account."""
    if configuration['kind'] == 'pbs_ssh':
        return 'aurora:'+configuration['account']
    return resource_id
