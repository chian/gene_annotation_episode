"""Execution recipes for the actual tool catalog, not a second tool registry."""
from pathlib import Path


ROOT = Path(__file__).with_name('execution_instruction_library')


def recipe(name, resource):
    if resource not in ('api', 'local', 'hpc'):
        raise ValueError('actual_execution_resource_kind_required')
    sections = ['planning', resource]
    # All catalog entries get the common recipe. Native homology has additional
    # result and workload operands; this does not manufacture an HPC callable.
    if any(word in name.lower() for word in ('blast', 'hmmer', 'phmmer', 'hmmsearch', 'hmmscan', 'homology')):
        sections.append('homology')
    return 'Execution recipe for '+name+' ('+resource+')\n\n' + '\n\n'.join(
        (ROOT/(section+'.md')).read_text().strip() for section in sections)


def resource_identity(resource_id, configuration):
    """Workspace-independent identity; Aurora uses its established account."""
    if configuration['kind'] == 'pbs_ssh':
        return 'aurora:'+configuration['account']
    return resource_id


def compare_routes(local, remote, *, requirements):
    """A transparent local-first recommendation, not admission or dispatch.

    Each route has fresh capacity and a separately justified total-time upper
    estimate (queue+setup+work+return). Unknown capacity cannot grant a slot.
    Estimates inform the episode's decision; there is no elapsed-time cutoff.
    """
    def evaluate(route):
        reasons = []
        if route is None:
            return {'eligible': False, 'reasons': ['not_configured']}
        if not route.get('binding_available', False):
            reasons.append('execution_binding_unavailable')
        if route.get('capacity_state') != 'fresh':
            reasons.append('refresh_capacity')
        if route.get('available', {}).get('job_slots') == 0:
            reasons.append('no_job_slot')
        for field in ('memory_bytes', 'scratch_bytes', 'cpu_threads'):
            need = requirements.get(field)
            available = route.get('available', {}).get(field)
            if need is not None and (available is None or available < need):
                reasons.append('insufficient_or_unknown_'+field)
        estimate = route.get('total_seconds_upper')
        return {'eligible': not reasons, 'reasons': reasons,
                'total_seconds_upper': estimate, 'provenance': route.get('provenance', [])}
    choices = {'local': evaluate(local), 'hpc': evaluate(remote)}
    selected = 'local' if choices['local']['eligible'] else 'hpc' if choices['hpc']['eligible'] else None
    return {'preferred': selected, 'routes': choices, 'admission_reserved': False,
            'rule': 'Prefer sufficient available local compute; otherwise use a supported HPC route.'}
