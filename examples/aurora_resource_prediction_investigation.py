"""Real model-driven prediction/execution sisters, with retained PBS evidence.

The caller supplies an accomplishment and genuine previous observations. The
episodes choose executable portfolios, resource sizing, setup and monitor times.
No provider choices, scheduler responses or worker results are scripted here.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import sqlite3
import sys
import uuid

from gene_annotation_episode.workflow_budget import active_budget
active_budget()

from gene_annotation_episode.execution_memory import ExecutionMemory
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.hpc_monitoring import DEFAULT_POLICY, MonitorCheckpoint
from gene_annotation_episode.hpc_resource_prediction import pbs_resource_metrics
from gene_annotation_episode.hpc_scheduler import register_resume
from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.runtime import Workflow, controller_from_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


OBJECTIVE = '''Test and calibrate real job RESOURCE prediction through the prediction and
execution sister episodes. Your goal is to choose useful CPU parallelism/allocation size
and anticipate CPU time and memory demand, together with queue/setup/work time.
Use the original measured SHA-256 cases supplied in history; their source ledgers are
read-only evidence, not a calibration guarantee. Preserve failed output acceptance as
failure while learning from its actual resource measurements. Historical worker affinity
was not measured consistently. Keep that uncertainty explicit.

The useful engineering workload is a reproducible calibration of independent SHA-256
chains: start each chain with 32 zero bytes, then repeatedly hash the previous digest.
Complete at least 512,000,000 total hash iterations. Choose meaningful alternatives for
workers/chains and iteration counts, enough useful work to observe running progress.
This is resource-model calibration, not biological evidence. Do not idle an allocation
or repeat the same work just to generate polling events or credit.

As the hpc parent, commission hpc_prediction to inspect missing environment/capacity
facts, design at least two executable resource alternatives, obtain a real queue
snapshot, fit genuine training cases and compare those alternatives. Then
commission its SISTER hpc_execution to choose from the comparisons using the shared
learned model and complete the computation through Launch -> launch_hpc. Both sister
assignments carry this hpc parent's episode_id as owner_episode_id, and commission_id
'resource-calibration'. Use the supplied hpc_report_form for both returns. These are
real model-selected iterations; no hand-written substitute decisions. The execution
sister owns hpc.plan and the launch; this parent receives the sisters' results.
Do not bypass the prediction sister or launch from this parent in this test.

Each candidate's features must include iterations per chain, chains, worker_threads,
total_iterations; preserve those meanings in executed commands. Vary parallelism or
allocation size to compare actual resource choices. Discover node capacity before
declaring resource_capacity. Distinguish allocated cores from observed CPU usage.
Queue congestion and scheduling features are inputs to the model. Missing scores
remain missing. Normalize dimensions using the supplied model specification.

Use stdlib hashlib and concurrent.futures.ProcessPoolExecutor, with explicit worker
count. Establish a correct compute-node launcher/affinity for that worker count;
do not accidentally confine a process pool to one core. Discover documentation if
needed. Reuse the existing project environment when compatible. All heavy work runs
inside the PBS allocation. Write progress.json periodically while doing useful work,
with JSON keys plan_id (from the HPC_PLAN_ID environment variable), unit_id (from
HPC_UNIT_ID), observed_at (Unix seconds), and completed_fraction, and declare
reports_progress=true. Retain original output and measured usage. result.json must
contain algorithm='sha256_chain_v1', completed=true, total_iterations, iterations,
chains, worker_threads, digest_hex, compute_hostname, and pbs_job_id.
Write BOTH result.json and progress.json under pathlib.Path(os.environ['HPC_UNIT_DIRECTORY']).
The allocation workspace is for staged source files, not these unit outputs. Do not
pass the allocation workspace as an output-directory argument. The runner records
the unit output's hash when the command finishes; files elsewhere cannot satisfy it.

The execution sister freezes its chosen trained model before submission, attaches the
original handoff, observes the job, revises conditional forecasts, and uses
hpc.monitor.wait when further active actions have low value. Use the explicit calendar
controller; no sleep/poll loops. Monitor and parse with single existing tools when
the contracts are known. An earlier completion is a result to collect, never a reason
to submit replacement work. Waiting/model fitting alone earns no credit.

Use Aurora account BioReason-Aurora-Test and the supplied project run directory.
Reuse only the existing SSH master; never authenticate, replace it or retry a lost
transport. No application runtime cutoff, token/turn budget or cumulative usage cap.
PBS walltime is the scheduler allocation request, not a second application timer.
After the real result is accepted, report the recorded prediction/measurement/credit
comparison. Unknown capacity, utilization and accuracy remain explicit.
'''


def previous_case(path):
    """Read a closed SHA-256 allocation, preserving failed result acceptance."""
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True) as db:
        rows = [(kind, json.loads(body)) for kind, body in
                db.execute('SELECT kind,body FROM evidence ORDER BY recorded,id')]
    def values(kind):
        return [body for name, body in rows if name == kind]
    exports = values('export_measurement')
    if len(exports) != 1:
        raise ValueError('one_original_exported_allocation_required')
    measured = exports[0]['body']
    if measured['plan_id'] not in {row['plan_id'] for row in values('closed')}:
        raise ValueError('original_allocation_must_be_closed')
    plan = next(row for row in values('plan') if row['plan_id'] == measured['plan_id'])
    receipts = [row for row in values('result') if row['plan_id'] == plan['plan_id']]
    if receipts and (len(receipts) != 1 or receipts[0]['document']['algorithm'] != 'sha256_chain_v1'):
        raise ValueError('original_sha256_receipt_required')
    if not receipts and values('commission')[0].get('execution_profile', {}).get('tool') != 'engineering.sha256_chain_pool':
        raise ValueError('original_sha256_profile_required')
    handoff = next(row for row in values('handoff') if row['plan_id'] == plan['plan_id'])
    native = next(row for row in reversed(values('native_status'))
                  if row['native']['pbs_job_id'] == handoff['job_id'])
    features = dict(plan['original_prediction']['features'])
    if receipts:
        document = receipts[0]['document']
        features.update(worker_threads=document.get('worker_threads', document['chains']),
                        total_iterations=document['chains']*document['iterations'])
    return {'id': 'original:'+handoff['job_id'], 'observed_at': measured['observed_at'],
        'features': features, 'metrics': {**measured['metrics'], **pbs_resource_metrics(native)},
        'success': measured['success'], 'provenance': [str(Path(path).resolve()), handoff['job_id'], exports[0]['id']]}


def commission(history, minimum_iterations=512_000_000, elapsed_cost_per_second=.00005):
    if type(minimum_iterations) is not int or minimum_iterations <= 0:
        raise ValueError('positive_calibration_work_size_required')
    if not math.isfinite(elapsed_cost_per_second) or elapsed_cost_per_second < 0:
        raise ValueError('nonnegative_elapsed_credit_cost_required')
    # Feature scaling keeps prior coefficient uncertainty meaningful across
    # byte/iteration counts and queue counts; these are declared priors.
    scales = {'nodes': 1., 'wall_seconds': 600., 'iterations': 2_000_000.,
        'chains': 16., 'worker_threads': 16., 'total_iterations': 32_000_000.,
        'queued_jobs': 10., 'queued_node_hours': 10., 'running_nodes': 64.,
        'queue_assigned_nodes': 64., 'comparable_jobs': 5.,
        'higher_score_jobs': 10., 'scheduler_score': 1000., 'queue:debug': 1.}
    return {'objective': OBJECTIVE.replace('512,000,000', f'{minimum_iterations:,}'),
        'resource_id': 'aurora', 'monitoring': dict(DEFAULT_POLICY),
        'execution_profile': {'resource_id': 'aurora:BioReason-Aurora-Test', 'backend': 'hpc',
            'tool': 'engineering.sha256_chain_pool', 'implementation': 'python-stdlib-sha256-chain-pool-v1',
            'parameters': 'independent-chain-rounds-v1', 'hardware': 'aurora-cpu-pbs-accounting-v1'},
        'obligations': {'resource_calibration': {'credit': 10., 'acceptance': [
            {'field': ['algorithm'], 'operator': 'eq', 'value': 'sha256_chain_v1'},
            {'field': ['completed'], 'operator': 'eq', 'value': True},
            {'field': ['total_iterations'], 'operator': 'ge', 'value': minimum_iterations}]}},
        'candidates': [], 'history': history if isinstance(history, list) else [history], 'validation_ids': [],
        'model': {'features': [{'name': name, 'transform': 'log1p', 'center': math.log1p(scale),
                                'scale': 2.} for name, scale in scales.items()],
            'priors': {name: {'median_seconds': seconds, 'log_sigma': 1., 'coefficient_variance': .2}
                for name, seconds in {'queue': 300, 'setup': 10, 'work': 120, 'return': 10}.items()},
            'resource_priors': {
                'cpu_seconds': {'median': 600, 'unit': 'cpu_seconds', 'log_sigma': 1., 'coefficient_variance': .2},
                'memory_bytes': {'median': 512*1024**2, 'unit': 'bytes', 'log_sigma': 1., 'coefficient_variance': .2}},
            'success_prior': [1., 1.]},
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'planned_'+metric, 'metric': metric, 'phase': 'planned',
             'weight': 1., 'minimum_elapsed_seconds': 0.} for metric in
            ('queue', 'work', 'cpu_seconds', 'memory_bytes')] + [
            {'id': 'running_work', 'metric': 'work', 'phase': 'running', 'weight': 1., 'minimum_elapsed_seconds': 0.}]},
        'preferences': {'elapsed_cost_per_second': elapsed_cost_per_second, 'node_hour_cost': .01},
        'limits': {'result_limit_bytes': 65536, 'queue_max_age_seconds': 900}}


class TraceProvider:
    def __init__(self, connection, directory):
        self.connection, self.directory = connection, directory

    def __getattr__(self, key):
        return getattr(self.connection, key)

    async def complete(self, episode_id, role, instructions, context, output_schema):
        result = await self.connection.complete(episode_id, role, instructions, context, output_schema)
        selected = result.get('selection', {})
        event = {'episode_id': episode_id, 'role': role, 'selection': selected}
        with (self.directory/'decisions.jsonl').open('a') as output:
            output.write(json.dumps(event)+'\n')
        print(json.dumps({'event': 'model_decision', 'episode_id': episode_id,
            'selection': {key: selected.get(key) for key in ('kind', 'role', 'tool')}}), flush=True)
        return result


async def run(args):
    root = Path(__file__).resolve().parents[1]
    directory = Path(args.run_directory).resolve()
    if not directory.is_relative_to(root/'runs'):
        raise ValueError('run_directory_must_be_under_runs')
    directory.mkdir(parents=True, exist_ok=True)
    original = directory/'original-commission.json'
    if not original.exists():
        if not args.history_ledger:
            raise ValueError('original_history_ledger_required_for_new_calibration')
        original.write_text(json.dumps(commission([previous_case(path) for path in args.history_ledger],
            args.minimum_iterations, args.elapsed_cost_per_second), indent=2))
    assigned = json.loads(original.read_text())
    resources = json.loads((root/'examples'/'aurora_execution_resources.json').read_text())
    resources['aurora']['workspace'] = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/'+directory.name
    factory = ExecutionServiceFactory(resources, {}, 1., 1., .01,
        hpc_commissions={'resource-calibration': assigned},
        shared_execution_memory=ExecutionMemory.configured().as_record())
    checkpoint = None
    with Store(directory/'state') as store:
        if store.db.execute('SELECT 1 FROM problem').fetchone() is None:
            manifest = directory/'caller-inputs.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
            store.create_problem(manifest_path=manifest, caller_context=assigned['objective'])
        async with ModelConnection(load_config(args.model_config), directory/'provider'/uuid.uuid4().hex, directory) as connection:
            workflow = Workflow(store, ToolRegistry(store), TraceProvider(connection, directory),
                directory/'episode', directory.name, controller_factory=controller_from_settings({'controller': {
                    'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}),
                project_credit=lambda *_: 0., episode_service_factory=factory,
                episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
                episode_record_receipts=True, initial_known_record_refs=[], root_role='hpc')
            episode = workflow.build('hpc', 'root', assigned['objective'], {'subject_refs': []},
                episode_assignment={'commission_id': 'resource-calibration'})
            print(json.dumps({'event': 'prediction_test_started', 'run_directory': str(directory)}), flush=True)
            try:
                record = await episode.run_async(workflow.context)
                result = await episode.build_result(record)
                (directory/'result.txt').write_text(str(result))
                from gene_annotation_episode.hpc_prediction_audit import audit
                verification = audit(directory)
                (directory/'prediction-audit.json').write_text(json.dumps(verification, indent=2))
                print(json.dumps({'event': 'prediction_audit', 'passed': verification['passed'],
                                  'checks': verification.get('checks')}), flush=True)
                print(json.dumps({'event': 'prediction_episode_returned', 'units': record.units_consumed}), flush=True)
            except MonitorCheckpoint as pending:
                checkpoint = pending.schedule
    if checkpoint is not None:
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--run-directory', str(directory)]
        if args.model_config:
            command += ['--model-config', str(Path(args.model_config).resolve())]
        resume = register_resume(directory, root, command, checkpoint)
        print(json.dumps({key: resume[key] for key in ('event', 'resume_at', 'timer', 'controller_run_directory')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory', required=True)
    parser.add_argument('--history-ledger', action='append', help='Original closed SHA-256 ledger; repeat for distinct cases, required only on first start.')
    parser.add_argument('--minimum-iterations', type=int, default=512_000_000,
        help='Useful calibration work requested in a new commission, not a runtime limit.')
    parser.add_argument('--elapsed-cost-per-second', type=float, default=.00005,
        help='Caller valuation of delayed completion in credit units; it never stops work at a deadline.')
    parser.add_argument('--model-config')
    asyncio.run(run(parser.parse_args()))
