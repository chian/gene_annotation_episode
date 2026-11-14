"""Private resource discovery for A110 hpc."""
from __future__ import annotations
import asyncio
from gene_annotation_episode.episodic_workflow.root.a110 import hpc_queue
import shlex
import subprocess
import time




class ResourceDiscovery:
    async def _discover_resource(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        command = 'cd ' + shlex.quote('/lus/flare/projects/BioReason-Aurora-Test') + ' && ' + arguments['command']

        def observe():
            from gene_annotation_episode.episodic_workflow.root.a110.execution_guidance import resource_identity
            cache_key = resource_identity(commission['resource_id'], configuration) + ':' + hpc_queue.digest(command)
            if self.memory:
                cached = self.memory.latest(cache_key, 'inventory')
                if cached['state'] == 'fresh':
                    return cached['data']
            completed = subprocess.run([*configuration['ssh_argv'], command], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            value = {'command': arguments['command'], 'returncode': completed.returncode, 'stdout': completed.stdout[:65536].decode('utf-8', 'replace'), 'stderr': completed.stderr[:8192].decode('utf-8', 'replace'), 'observed_at': time.time(), 'truncated': len(completed.stdout) > 65536}
            if self.memory and completed.returncode == 0:
                self.memory.observe(cache_key, 'inventory', value, observed_at=value['observed_at'], provenance=[str(ledger.path), 'discovery:' + operation_key])
            return value
        result = await asyncio.to_thread(ledger.once, 'discovery:' + operation_key, 'discovery', observe)
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
