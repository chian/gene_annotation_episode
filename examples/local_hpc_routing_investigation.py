"""Live model-selected local-to-Aurora routing with real native reservations."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import time
import uuid

from gene_annotation_episode.workflow_budget import active_budget

active_budget()

from gene_annotation_episode.execution_guidance import recipe
from gene_annotation_episode.execution_memory import ExecutionMemory
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.hpc_monitoring import DEFAULT_POLICY, MonitorCheckpoint
from gene_annotation_episode.hpc_scheduler import register_resume
from gene_annotation_episode.local_resources import LocalResources
from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.runtime import Workflow, controller_from_settings
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def local_request(directory, name, *, witness=None):
    workspace = directory/'local'/name
    workspace.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-B', str(Path(__file__).with_name('routing_compute.py').resolve()),
        '--directory', str(workspace), '--rounds', str(8_000_000 if witness else 131072)]
    if witness:
        command += ['--witness', str(witness)]
    return {'version': 'execution_launch_assignment_v1', 'requests': {'local': {
        'version': 'practical_assignment_v1', 'assignment_id': name, 'resource_id': 'local',
        'resource_kind': 'local', 'workspace': str(directory/'local'), 'endpoint': 'usable_handoff',
        'requested_job': {'argv': command, 'environment': {}},
        'progress_requirements': [{'key': 'handoff', 'credit': 1.,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {}}},
        'immutable_input_versions': [], 'constraints': {}}


def commission():
    return {'objective': '''Complete a real compute-node execution for a resource-routing test.
The parent has selected Aurora for a second independent CPU computation. Use the existing
authenticated transport, account BioReason-Aurora-Test and supplied project workspace.
The algorithm is an explicitly labeled engineering SHA-256 chain, not biological evidence.
Use hashlib.sha256 starting from bytes.fromhex('00'*32), repeatedly hashing the previous digest.
Choose a useful calibration batch (at least 1,000,000 iterations per chain); use the allocated
node sensibly and do not hold it idle. One allocation suffices. Reuse installed software.
Discover what you need, design the portfolio, prepare, launch, monitor with the explicit cron
controller, and parse the actual result. Keep preparation light on the login node; compute
on the allocation. Each accepted result.json must contain algorithm='sha256_chain_v1',
completed=true, iterations, chains, digest_hex, compute_hostname and pbs_job_id.
Do not fabricate results or SSH. Do not impose a work-unit time cutoff. Keep raw outputs.
''', 'resource_id': 'aurora', 'monitoring': dict(DEFAULT_POLICY),
        'obligations': {'second_computation': {'credit': 10., 'acceptance': [
            {'field': ['algorithm'], 'operator': 'eq', 'value': 'sha256_chain_v1'},
            {'field': ['completed'], 'operator': 'eq', 'value': True},
            {'field': ['iterations'], 'operator': 'ge', 'value': 1_000_000},
            {'field': ['chains'], 'operator': 'ge', 'value': 1}]}},
        'candidates': [], 'model': {'features': [
            {'name': name, 'transform': 'log1p', 'scale': 1.}
            for name in ('nodes', 'wall_seconds', 'iterations', 'chains')],
            'priors': {name: {'median_seconds': seconds, 'log_sigma': 2., 'coefficient_variance': 1.}
                for name, seconds in {'queue': 1800, 'setup': 30, 'work': 120, 'return': 10}.items()},
            'success_prior': [1., 1.]}, 'history': [], 'validation_ids': [],
        'credit': {'model_scale': .01, 'validation_scale': .1, 'validation_slots': [
            {'id': 'queue', 'metric': 'queue', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0},
            {'id': 'work', 'metric': 'work', 'phase': 'planned', 'weight': 1., 'minimum_elapsed_seconds': 0}]},
        'preferences': {'elapsed_cost_per_second': .00005, 'node_hour_cost': .01},
        'limits': {'result_limit_bytes': 65536, 'queue_max_age_seconds': 900}}


class ObservedProvider:
    """Record the real choice and capacity; never supply or rewrite a choice."""
    def __init__(self, connection, directory):
        self.connection, self.directory = connection, directory
        self.root_id = None

    def __getattr__(self, name):
        return getattr(self.connection, name)

    async def complete(self, episode_id, role, instructions, context, output_schema):
        before = LocalResources.configured().snapshot()
        # Entry into the actual initialized HPC episode proves its parent's
        # request passed the action/report contracts. A proposal alone does not.
        if 'hpc_commission' in context and self.root_id != episode_id:
            witness = self.directory/'routing-witness.json'
            if not witness.exists() and any(job['state'] == 'running' for job in before['jobs']):
                witness.write_text(json.dumps({'event': 'accepted_hpc_child_while_local_running',
                    'episode_id': episode_id, 'observed_at': time.time(),
                    'capacity': before}, indent=2))
                print(json.dumps({'event': 'accepted_hpc_child_while_local_running',
                    'episode_id': episode_id}), flush=True)
        result = await self.connection.complete(episode_id, role, instructions, context, output_schema)
        after = LocalResources.configured().snapshot()
        row = {'episode_id': episode_id, 'observed_at': time.time(), 'before': before,
               'after': after, 'response': result}
        with (self.directory/'routing-decisions.jsonl').open('a') as output:
            output.write(json.dumps(row)+'\n')
        choice = result.get('selection', {}) if isinstance(result, dict) else {}
        print(json.dumps({'event': 'model_decision', 'episode_id': episode_id,
            'selection': {key: choice.get(key) for key in ('kind', 'role', 'tool')},
            'local_state': after['state'], 'local_jobs': len(after['jobs'])}), flush=True)
        return result


class TimedCheckpoint(Exception):
    def __init__(self, request):
        self.request = request


async def collect_existing(directory, factory, resources, episode_id):
    """Recover monitoring of an original handoff without rerunning its parent.

    This explicitly selected recovery path calls only the existing monitor and
    result tools. It preserves original requests, forecasts, actions and receipts.
    It cannot prepare, plan, launch or submit work.
    """
    from gene_annotation_episode.episode_bindings import BindingContext
    retained = directory/'collection'
    retained.mkdir(exist_ok=True)
    pending = retained/(episode_id+'.json')
    with Store(directory/'state') as store:
        row = store.db.execute('SELECT path,request FROM runtime_episodes '
            'WHERE run_id=? AND episode_id=?', (directory.name, episode_id)).fetchone()
        if row is None:
            raise ValueError('original_hpc_episode_required')
        path, request = json.loads(row[0]), json.loads(row[1])
        if path[-1][0] != 'hpc':
            raise ValueError('original_hpc_episode_required')
        workflow = Workflow(store, ToolRegistry(store, job_limits=resources['local']['policy']), None,
            directory/'episode', directory.name,
            controller_factory=controller_from_settings({'controller': {'cost': .001}}),
            project_credit=lambda *_: 0., episode_service_factory=factory,
            episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1',
            episode_record_receipts=True, initial_known_record_refs=[])
        context = BindingContext(directory.name, episode_id, 'hpc', path,
            request['message']['scope'], request['message']['episode_assignment'], request,
            received_record_refs=tuple(workflow.receipts.known(episode_id)))
        binding = workflow.episode_bindings.for_role('hpc')
        ledger = binding.state(context)
        handed_off = {item['body']['plan_id'] for item in ledger.records('handoff')}
        plans = [item for item in ledger.records('plan') if item['body']['plan_id'] in handed_off]
        if len(plans) != 1:
            raise ValueError('recovery_requires_one_original_submitted_plan')
        plan_ref = plans[0]['id']
        def action(tool):
            arguments = {'plan_ref': plan_ref}
            if tool == 'hpc.monitor':
                arguments['refresh_queue'] = True
            value = {'tool': tool, 'arguments': arguments,
                     'operation_key': 'explicit-collection:'+uuid.uuid4().hex}
            pending.write_text(json.dumps(value, indent=2))
            return value
        selected = json.loads(pending.read_text()) if pending.exists() else action('hpc.monitor')
        while True:
            if (selected['tool'] not in ('hpc.monitor', 'hpc.monitor.wait', 'hpc.results')
                    or selected['arguments']['plan_ref'] != plan_ref):
                raise ValueError('recovery_may_only_observe_original_plan')
            try:
                outcome = await binding.execute(context, **{
                    'tool_name': selected['tool'], 'arguments': selected['arguments'],
                    'operation_key': selected['operation_key']})
            except MonitorCheckpoint as checkpoint:
                return checkpoint.schedule
            (retained/(selected['operation_key'].replace(':', '_')+'.json')).write_text(
                json.dumps({'action': selected, 'outcome': outcome}, indent=2))
            print(json.dumps({'event': 'original_job_collection', 'tool': selected['tool'],
                              'result': outcome['result']}), flush=True)
            if selected['tool'] == 'hpc.results':
                (directory/'original-collection.json').write_text(json.dumps(outcome, indent=2))
                return None
            observed = outcome['result']
            if selected['tool'] == 'hpc.monitor.wait':
                observed = observed['monitor']
                if observed is None:
                    raise ValueError('monitor_prediction_requests_reconsideration')
            state = observed['conditional_prediction']['telemetry']['state']
            selected = action('hpc.results' if state in ('complete', 'failed') else 'hpc.monitor.wait')


async def run(args):
    directory = Path(args.run_directory).resolve()
    root = Path(__file__).resolve().parents[1]
    if not directory.is_relative_to(root/'runs'):
        raise ValueError('run_directory_must_be_under_runs')
    directory.mkdir(parents=True, exist_ok=True)
    first = local_request(directory, 'first', witness=directory/'routing-witness.json')
    second = local_request(directory, 'second')
    resources = json.loads((root/'examples'/'aurora_execution_resources.json').read_text())
    resources['aurora']['workspace'] = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs/'+directory.name
    resources['local'] = {'kind': 'local', 'workspace': str(directory/'local'),
        'policy': {'memory_bytes': 64*1024**2, 'scratch_bytes': 8*1024**2}}
    memory = ExecutionMemory.configured()
    factory = ExecutionServiceFactory(resources, {}, 1., 1., .01,
        hpc_commissions={'second-computation': commission()}, shared_execution_memory=memory.as_record())
    if args.collect_existing:
        checkpoint = await collect_existing(directory, factory, resources, args.collect_existing)
        if checkpoint is not None:
            command = [sys.executable, '-B', str(Path(__file__).resolve()), '--run-directory', str(directory),
                       '--collect-existing', args.collect_existing]
            resume = register_resume(directory, root, command, checkpoint)
            print(json.dumps({key: resume[key] for key in ('event', 'resume_at', 'timer',
                                                          'controller_run_directory')}), flush=True)
        return
    objective = '''Investigate actual resource selection in this one workflow.
First establish the supplied FIRST local computation through Launch -> launch_local and
return its usable detached handoff. It is a small-memory engineering resource-occupancy
experiment. It computes real hashes and ends after the observer sees entry into an accepted
HPC child while local work is running, or after its finite requested work. An invalid
proposed commission does not end it. It has no runtime timer.
Then, while it runs, choose where to launch SECOND independent work using actual current
resource_context. Both computations fit the local worker policy when capacity is free.
Prefer available sufficient local compute; if local capacity is occupied, consider the
available Aurora HPC commission and its queue/setup/work tradeoffs. Do not fabricate busy
state, wait solely to hide a routing failure, oversubscribe the local worker slot, or rewrite
the FIRST command. Your decision is under test; you are not required to claim success.
For the local choice use SECOND below. For Aurora commission hpc with
commission_id='second-computation'; that episode owns discovery, preparation, launch and
monitoring. Preserve actual handles, PBS identity and returned evidence. Report whether
the choice happened while the first local worker was running. Complete/collect requested
work; do not claim that selecting a backend means a job was submitted. This is an engineering
execution test, not an A101 scientific result. No authentication fallback or fake SSH.
Use the supplied typed return form for an HPC child; its fact sources are registered by the
existing HPC template. If a proposed request is rejected, repair its report contract and
reconsider current capacity. Do not resubmit an already handed-off SECOND job.
'''+ '\nHPC_RETURN_FORM='+json.dumps({'type': 'object', 'additionalProperties': False,
        'properties': {'hpc_credit': {'type': 'number', 'x-source': 'hpc_credit'},
            'hpc_result_refs': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
                'format': 'reference', 'x-reference-namespace': 'source'}, 'x-source': 'hpc_result_refs'}},
        'required': ['hpc_credit', 'hpc_result_refs']})+'\nFIRST='+json.dumps(first)+'\nSECOND='+json.dumps(second)+'\n\n'+recipe('practical.job.start', 'local')
    checkpoint = None
    with Store(directory/'state') as store:
        if store.db.execute('SELECT 1 FROM problem').fetchone() is None:
            manifest = directory/'caller-inputs.json'
            manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
            store.create_problem(manifest_path=manifest, caller_context=objective)
        def progress(*_):
            # Original native preparation is verifiable operational progress;
            # provider calls and timer wakes have no value by themselves.
            started = (directory/'local'/'first'/'progress.json').exists()
            finished = (directory/'local'/'first'/'result.json').exists()
            return float(started)+float(finished)
        async with ModelConnection(load_config(args.model_config), directory/'provider'/uuid.uuid4().hex, directory) as connection:
            provider = ObservedProvider(connection, directory)
            workflow = Workflow(store, ToolRegistry(store, job_limits=resources['local']['policy']), provider,
                directory/'episode', directory.name,
                controller_factory=controller_from_settings({'controller': {
                    'cost': .001, 'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}),
                project_credit=progress, episode_service_factory=factory, episode_service_binding=factory.as_record(),
                episode_service_inputs='actual_tool_registry_v1', episode_record_receipts=True,
                initial_known_record_refs=[], annotation_child_roles=('launch', 'hpc', 'monitor', 'results'))
            episode = workflow.build('annotation', 'root', objective, {'subject_refs': []})
            provider.root_id = episode.source.episode_id
            print(json.dumps({'event': 'routing_episode_started', 'directory': str(directory)}), flush=True)
            try:
                record = await episode.run_async(workflow.context)
                result = await episode.build_result(record)
                (directory/'result.txt').write_text(str(result))
                print(json.dumps({'event': 'routing_episode_returned', 'units': record.units_consumed}), flush=True)
            except TimedCheckpoint as pending:
                checkpoint = pending.request
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
    parser.add_argument('--model-config')
    parser.add_argument('--collect-existing', metavar='EPISODE_ID',
        help='Explicitly recover monitor/result calls for one existing submitted HPC episode; never launch.')
    asyncio.run(run(parser.parse_args()))
