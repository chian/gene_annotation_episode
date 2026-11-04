"""Commission a real autonomous HPC episode; no caller-selected BLAST commands."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone
import uuid

from gene_annotation_episode.workflow_budget import active_budget

active_budget()

from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.runtime import Workflow, controller_from_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.hpc_monitoring import MonitorCheckpoint, DEFAULT_POLICY
from gene_annotation_episode.hpc_scheduler import register_resume


class TimedCheckpoint(Exception):
    def __init__(self, request):
        self.request = request


def schedule_resume(directory, root, args, request):
    """Wake only for the episode's recorded time; never retry a failed run."""
    command = [sys.executable, '-B', str(Path(__file__).resolve()), '--run-directory', str(directory)]
    if args.model_config:
        command.extend(['--model-config', str(Path(args.model_config).resolve())])
    resume = register_resume(directory, root, command, request)
    print(json.dumps({key: resume[key] for key in ('event', 'resume_at', 'timer', 'controller_run_directory')}), flush=True)


OBJECTIVE = """Run a meaningful real BLAST protein search against a real public protein database on Aurora.
You own discovery, workload design, environment/software setup, database acquisition and preparation,
resource/queue selection, launch, monitoring, prediction updates and result interpretation. Choose
traceable real protein queries and a useful public database, not synthetic sequences or a toy self-search.
Search at least 128 queries against at least 10,000 database sequences; choose a larger useful workload
when appropriate to amortize queue/setup costs. Use the existing HPC parent, prediction sister and
Launch -> launch_hpc episodes. Monitoring and known parsing are parent tools. Read Aurora documentation
yourself when needed. No caller has prepared a worker script, installed BLAST or selected job commands.

Use account BioReason-Aurora-Test. All workflow files, downloads, environments, temporary files,
database files and results belong beneath the supplied BioReason project run directory. Reuse only
the established SSH transport; do not authenticate, replace the master, or retry a lost transport.
Do not access A101 or resume A106. Run one allocation at a time. Do heavy database preparation and
BLAST on allocated compute nodes, not local hardware or login nodes. Plan useful work for the
allocation; release it when the useful work is complete. No tiny stand-alone environment-check job.

Use real command outputs to produce each unit's result.json. The credited search result must contain
program='blastp', returncode=0, completed=true, query_count, database_sequence_count, hit_count,
query_source, database_source, database_sha256, software_version, compute_hostname, pbs_job_id,
raw_results_path, and a compact best-hit summary. Preserve raw search output and provenance remotely.
Report the actual PBS identity, results, and forecast-versus-observation evidence. Unknowns stay unknown.
The supplied model is an explicitly uncalibrated starting prior, not measured history.
"""


def commission():
    predicates = [
        {'field': ['program'], 'operator': 'eq', 'value': 'blastp'},
        {'field': ['completed'], 'operator': 'eq', 'value': True},
        {'field': ['returncode'], 'operator': 'eq', 'value': 0},
        {'field': ['query_count'], 'operator': 'ge', 'value': 128},
        {'field': ['database_sequence_count'], 'operator': 'ge', 'value': 10000},
        {'field': ['hit_count'], 'operator': 'ge', 'value': 1},
    ]
    return {
        'objective': OBJECTIVE, 'resource_id': 'aurora',
        'monitoring': dict(DEFAULT_POLICY),
        'obligations': {'blast_search': {'credit': 10., 'acceptance': predicates}},
        'candidates': [],
        'model': {'features': [
            {'name': name, 'transform': 'log1p', 'scale': 1.}
            for name in ('nodes', 'wall_seconds', 'queued_node_hours', 'query_count', 'database_sequence_count')],
            'priors': {name: {'median_seconds': seconds, 'log_sigma': 2., 'coefficient_variance': 1.}
                       for name, seconds in {'queue': 1800, 'setup': 600, 'work': 1800, 'return': 30}.items()},
            'success_prior': [1., 1.]},
        'history': [], 'validation_ids': [],
        'credit': {'model_scale': .01, 'validation_scale': .1,
            'validation_slots': [
                {'id': 'planned_queue', 'metric': 'queue', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0},
                {'id': 'planned_work', 'metric': 'work', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0},
                {'id': 'queued_queue', 'metric': 'queue', 'phase': 'queued', 'weight': 1., 'minimum_elapsed_seconds': 60},
                {'id': 'running_work', 'metric': 'work', 'phase': 'running', 'weight': 1., 'minimum_elapsed_seconds': 60}]},
        'preferences': {'deadline_seconds': 14400, 'elapsed_cost_per_second': .00005, 'node_hour_cost': .01},
        'limits': {'max_nodes': 2, 'max_wall_seconds': 7200, 'max_node_hours': 4,
                   'shutdown_margin_seconds': 30, 'result_limit_bytes': 65536, 'queue_max_age_seconds': 900},
    }


async def run(args):
    directory = Path(args.run_directory).resolve()
    root = Path(__file__).resolve().parents[1]
    if not directory.is_relative_to(root/'runs'):
        raise ValueError('run_directory_must_be_under_repository_runs')
    directory.mkdir(parents=True, exist_ok=True)
    resources = json.loads((root/'examples'/'aurora_execution_resources.json').read_text())
    resources['aurora']['workspace'] = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/'+directory.name
    retained_commissions = list((directory/'episode'/'hpc').glob('*/hpc.sqlite'))
    if retained_commissions:
        if len(retained_commissions) != 1:
            raise ValueError('single_original_hpc_commission_required')
        with sqlite3.connect(retained_commissions[0].resolve().as_uri()+'?mode=ro', uri=True) as db:
            original_commission = json.loads(db.execute("SELECT body FROM evidence WHERE id='commission'").fetchone()[0])
    else:
        original_commission = commission()
    factory = ExecutionServiceFactory(resources, {}, 1., 1., .01,
        hpc_commissions={'blast': original_commission})
    checkpoint = None
    with Store(directory/'state') as store:
        if store.db.execute('SELECT 1 FROM problem').fetchone() is None:
            # This operational commission has no caller-supplied sequences.
            manifest = directory/'caller-inputs.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
            store.create_problem(manifest_path=manifest, caller_context=OBJECTIVE)
        async with ModelConnection(load_config(args.model_config), directory/'provider'/uuid.uuid4().hex, directory) as provider:
            workflow = Workflow(store, ToolRegistry(store), provider, directory/'episode', directory.name,
                controller_factory=controller_from_settings({'controller': {
                    'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}),
                project_credit=lambda *_: 0., episode_service_factory=factory,
                episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
                episode_record_receipts=True, initial_known_record_refs=[], root_role='hpc')
            original_wait = workflow.wait_store.perform_wait

            async def checkpoint_wait(request, backend):
                condition = request['condition']
                if not condition['events'] and condition['reconsider_at'] is not None:
                    when = datetime.fromisoformat(condition['reconsider_at'].replace('Z', '+00:00'))
                    if (when-datetime.now(timezone.utc)).total_seconds() > 45:
                        # The runtime has already retained the selected wait,
                        # its original action identity and estimate snapshot.
                        raise TimedCheckpoint(request)
                return await original_wait(request, backend)

            workflow.wait_store.perform_wait = checkpoint_wait
            episode = workflow.build('hpc', 'root', OBJECTIVE, {'subject_refs': []},
                episode_assignment={'commission_id': 'blast'})
            print(json.dumps({'event': 'episode_started', 'run_directory': str(directory),
                'remote_workspace': resources['aurora']['workspace']}), flush=True)
            try:
                record = await episode.run_async(workflow.context)
                result = await episode.build_result(record)
                (directory/'result.txt').write_text(str(result))
                print(json.dumps({'event': 'episode_returned', 'units': record.units_consumed,
                                  'result_path': str(directory/'result.txt')}), flush=True)
            except TimedCheckpoint as pending:
                checkpoint = pending.request
            except MonitorCheckpoint as pending:
                checkpoint = pending.schedule
    if checkpoint is not None:
        schedule_resume(directory, root, args, checkpoint)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--model-config')
    asyncio.run(run(parser.parse_args()))
