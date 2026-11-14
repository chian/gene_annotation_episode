"""Shared execution memory and host/resource observations used by the workflow."""
import os
from pathlib import Path
import time

from .execution_memory import ExecutionMemory
from .execution_guidance import resource_identity


def memory_for(workflow):
    memory = getattr(workflow.tools, 'execution_memory', None)
    return memory if memory is not None else ExecutionMemory.configured()


def host_capacity():
    """Cheap host-wide observations, distinct from a window's ownership."""
    memory = {}
    try:
        memory = {line.split(':')[0]: int(line.split()[1])*1024
                  for line in Path('/proc/meminfo').read_text().splitlines()
                  if line.startswith(('MemTotal:', 'MemAvailable:'))}
        host = Path('/etc/machine-id').read_text().strip()
    except (OSError, ValueError):
        host = os.uname().nodename
    return {'resource_id': 'local:'+host, 'observed_at': time.time(),
            'available_memory_bytes': memory.get('MemAvailable'),
            'total_memory_bytes': memory.get('MemTotal'), 'logical_cpus': os.cpu_count(),
            'load_average': list(os.getloadavg()),
            'meaning': 'Host observation across windows; does not reserve capacity or grant a workflow slot.'}


def planning_context(workflow, local_snapshot):
    memory = memory_for(workflow)
    host = host_capacity()
    reference = memory.observe(host['resource_id'], 'capacity', host,
        observed_at=host['observed_at'], provenance=['/proc/meminfo', 'getloadavg'])
    remote = {}
    if 'launch' in workflow.episode_bindings.roles:
        binding = workflow.episode_bindings.for_role('launch')
        for name, configuration in getattr(binding, 'resources', {}).items():
            if configuration['kind'] != 'pbs_ssh':
                continue
            identity = resource_identity(name, configuration)
            view = memory.latest(identity, 'queue')
            # Bound prompt size. The HPC queue tool retrieves and transforms the
            # full cached snapshot for a proposed candidate when needed.
            if view['data'] is not None:
                snapshot = view['data']['snapshot']
                jobs = snapshot['jobs']
                view['data'] = {'job_count': len(jobs), 'queues': snapshot.get('queues'),
                    'reservations': snapshot.get('reservations'),
                    'detailed_observation': view['reference']}
            remote[name] = {'resource_id': identity, 'account': configuration['account'],
                'workspace': configuration['workspace'], 'queue': view,
                'inventory': memory.latest(identity, 'inventory'),
                'authentication': 'Configured reuse-only transport; current liveness is not asserted.'}
    return {'version': 'shared_execution_planning_v1', 'memory': memory.as_record(),
        'host': {**host, 'reference': reference}, 'remote': remote,
        'local_pending': local_snapshot.get('jobs', []),
        'policy': 'Prefer available sufficient local compute. Use Aurora when local capacity or the '
            'expected turnaround is insufficient. Compare queue + setup + work + return and uncertainty. '
            'Local and HPC resource contracts are separate. Long local jobs use detached Launch, '
            'then the parent can do useful work in the same owned workflow. '
            'Use process.execution for selected-tool recipes and compatible timing history.'}
