"""Run an original useful A104 work commission through the shared HPC episode."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

from gene_annotation_episode.workflow_budget import active_budget
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.execution_memory import ExecutionMemory
from gene_annotation_episode.hpc_monitoring import MonitorCheckpoint
from gene_annotation_episode.hpc_scheduler import register_resume
from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.runtime import Workflow, controller_from_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.a104_hpc import import_result


class CalendarCheckpoint(Exception):
    def __init__(self, request):
        self.request = request


async def run(args):
    active_budget()
    directory = args.case_directory.resolve()
    prepared = json.loads((directory/'PREPARED.json').read_text())
    factory = ExecutionServiceFactory(prepared['execution_resources'], {}, 1., 1., .01,
        hpc_commissions=prepared['hpc_commissions'],
        shared_execution_memory=prepared.get('shared_execution_memory') or ExecutionMemory.configured().as_record())
    run_id = 'a104-hpc-'+directory.parent.name
    pending = None
    with Store(directory/'state') as store:
        tools = ToolRegistry(store, job_limits={'memory_bytes': 128*1024**2, 'scratch_bytes': 32*1024**2})
        async with ModelConnection(load_config(args.model_config), directory/'provider'/uuid.uuid4().hex, directory) as provider:
            workflow = Workflow(store, tools, provider, directory/'workflow', run_id,
                controller_factory=controller_from_settings({'controller': {
                    'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}),
                project_credit=lambda *_: 0., episode_service_factory=factory,
                episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
                episode_record_receipts=True, initial_known_record_refs=prepared['known_record_refs'], root_role='hpc')
            episode = workflow.build('hpc', 'root', prepared['hpc_commissions']['a104-native']['objective'],
                prepared['scope'], episode_assignment={'commission_id': 'a104-native'})
            print(json.dumps({'event': 'a104_hpc_episode_started', 'run_id': run_id,
                'case_directory': str(directory), 'remote_workspace': prepared['execution_resources']['aurora']['workspace']}), flush=True)
            try:
                record = await episode.run_async(workflow.context)
                await episode.build_result(record)
                known = set(workflow.receipts.known(episode.source.episode_id))
                results = [ref for ref in known if store.get(ref).get('provider') == 'episode.hpc_result']
                admitted = []
                for reference in results:
                    admitted.append(import_result(store, request_ref=prepared['native_request_ref'],
                        hpc_result_ref=reference, known_record_refs=known, scope=prepared['scope'], run_id=run_id))
                summary = {'event': 'a104_hpc_episode_returned', 'run_id': run_id,
                    'native_phylogeny_refs': admitted, 'hpc_result_refs': results,
                    'scientific_credit_status': 'native_received; A104_measurements_and_attribution_follow',
                    'actual_model_decisions': True, 'completed_native_admission': bool(admitted)}
                (directory/'HPC_RESULT.json').write_text(json.dumps(summary, indent=2)+'\n')
                print(json.dumps(summary), flush=True)
            except CalendarCheckpoint as waiting:
                pending = waiting.request
            except MonitorCheckpoint as waiting:
                pending = waiting.schedule
    if pending is not None:
        snapshot = Path(__file__).resolve().parents[1]
        command = ['/usr/bin/env', 'PYTHONPATH='+str(snapshot), sys.executable, '-B', str(Path(__file__).resolve()),
                   '--case-directory', str(directory), '--repository-root', str(args.repository_root.resolve())]
        if args.model_config:
            command.extend(['--model-config', str(args.model_config.resolve())])
        spec = register_resume(directory, args.repository_root, command, pending)
        print(json.dumps({key: spec[key] for key in ('event', 'resume_at', 'timer', 'controller_run_directory')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    parser.add_argument('--repository-root', type=Path, required=True)
    parser.add_argument('--model-config', type=Path)
    asyncio.run(run(parser.parse_args()))
