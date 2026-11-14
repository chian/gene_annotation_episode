"""Shared execution memory and host/resource observations used by the workflow."""
import os
from pathlib import Path
import time

from .execution_memory import ExecutionMemory


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
    return {'version': 'shared_execution_planning_v1', 'memory': memory.as_record(),
        'host': {**host, 'reference': reference}, 'remote': remote,
        'local_pending': local_snapshot.get('jobs', []),
        'policy': 'Prefer available sufficient local compute. Use Aurora when local capacity or the '
            'expected turnaround is insufficient. Compare queue + setup + work + return and uncertainty. '
            'Local and HPC resource contracts are separate. Long local jobs use detached Launch, '
            'then the parent can do useful work in the same owned workflow. '
            'Use process.execution for selected-tool recipes and compatible timing history.'}
