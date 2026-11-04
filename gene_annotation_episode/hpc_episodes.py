"""HPC parent and prediction specializations of the ordinary Episode loop.

Launch remains the existing launch -> launch_hpc iteration. Known monitoring
and result parsing are single tools of the HPC parent. This binding never calls
a model, polls in a loop, or decides to commission children itself.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import asyncio
import shlex
import subprocess
import time

from .communication import plain, validate_form
from .domain import validate_schema
from .episode_bindings import reference_in_context
from .execution_contracts import obj
from .hpc_campaign import accepts, build_plan, incorporate_progress, telemetry, timestamp, validate_commission
from .hpc_ledger import HPCLedger
from . import hpc_prediction as prediction
from . import hpc_queue


TEXT = {'type': 'string', 'minLength': 1}
STRINGS = {'type': 'array', 'uniqueItems': True, 'items': TEXT}


def authenticate_launch(parent, selection, operation_key, directory):
    """Only the exact planned launch may consume the original allocation slot."""
    ledger = HPCLedger.open_existing(Path(directory)/'hpc'/hpc_queue.digest([parent.run_id, parent.episode_id]))
    matching = [row for row in ledger.records('plan') if row['body']['launch_assignment'] == plain(selection)]
    if len(matching) != 1 or ledger.read('owner')['scope'] != plain(parent.scope):
        raise ValueError('hpc_launch_must_match_original_planned_portfolio')
    plan = matching[0]['body']
    identity = 'launch:'+plan['plan_id']
    reservation = {'operation_key': operation_key, 'plan_id': plan['plan_id']}
    if any(row['id'] == identity for row in ledger.records('launch_commission')):
        # Completed parent actions still reconstruct their original child after
        # result collection closes the allocation. Authenticate that exact
        # reservation; a different action cannot use it to launch again.
        ledger.put('launch_commission', reservation, identity=identity)
        return
    if any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
        raise ValueError('hpc_allocation_already_closed')
    ledger.put('launch_commission', reservation, identity=identity)


class HPCEpisodes:
    roles = ('hpc', 'hpc_prediction')
    entry_roles = ('hpc',)
    replaces_default_instructions = True

    def __init__(self, services, *, store, run_id, directory, resources, commissions):
        self.services, self.store, self.run_id = services, store, run_id
        self.directory = Path(directory)
        self.resources = plain(resources)
        self.commissions = {key: validate_commission(plain(value), self.resources)
                            for key, value in commissions.items()}
        if not self.commissions:
            raise ValueError('explicit_hpc_commissions_required')
        self._targets = None

    @property
    def targets(self):
        if self._targets is None:
            from .execution_progress import ExecutionTargetReader
            self._targets = ExecutionTargetReader(self.store, run_id=self.run_id, directory=self.directory,
                resources={key: value for key, value in self.resources.items() if value['kind'] == 'pbs_ssh'},
                api_execution=None)
        return self._targets

    def as_record(self):
        modules = ('hpc_episodes.py', 'hpc_campaign.py', 'hpc_ledger.py', 'hpc_prediction.py',
                   'hpc_queue.py', 'hpc_allocation.py', 'hpc_monitoring.py')
        hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in modules}
        return {'version': 'hpc_episodes_v1', 'binding_id': 'hpc',
            'implementation_sha256': hpc_queue.digest(hashes),
            'configuration': {'resources': deepcopy(self.resources), 'commissions': deepcopy(self.commissions)}}

    def credit_kind(self, role):
        if role not in self.roles:
            raise ValueError('unknown_hpc_role')
        return 'operational'

    def child_roles(self, role):
        self.credit_kind(role)
        return ('hpc_prediction', 'launch', 'monitor', 'results') if role == 'hpc' else ()

    def allowed_children(self, parent, caller_capabilities):
        return self.child_roles(parent.role)

    def assignment_schema(self, role):
        self.credit_kind(role)
        fields = {'commission_id': {'type': 'string', 'enum': list(self.commissions)}}
        if role == 'hpc_prediction':
            fields['owner_episode_id'] = TEXT
        return obj(fields)

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selection = plain(selection)
        validate_schema(selection, self.assignment_schema(role))
        if role == 'hpc_prediction' and (parent.role != 'hpc'
                or selection['owner_episode_id'] != parent.episode_id
                or selection['commission_id'] != parent.assignment['commission_id']):
            raise ValueError('prediction_must_belong_to_its_original_hpc_parent')
        return selection

    def permitted_common_actions(self, context):
        if context.role != 'hpc':
            return ('tool',)
        if 'monitoring' in self.commissions[context.assignment['commission_id']]:
            return ('tool', 'child', 'redeliver_report')
        return ('tool', 'child', 'wait', 'redeliver_report')

    def state(self, context):
        validate_schema(plain(context.assignment), self.assignment_schema(context.role))
        commission = self.commissions[context.assignment['commission_id']]
        owner = context.episode_id if context.role == 'hpc' else context.assignment['owner_episode_id']
        directory = self.directory/'hpc'/hpc_queue.digest([self.run_id, owner])
        ledger = HPCLedger(directory, commission)
        if context.role == 'hpc':
            ledger.put('owner', {'run_id': self.run_id, 'episode_id': owner,
                'scope': plain(context.scope), 'commission_id': context.assignment['commission_id']}, identity='owner')
        else:
            original = ledger.read('owner')
            if original['scope'] != plain(context.scope):
                raise ValueError('prediction_scope_must_equal_original_parent_scope')
        return ledger

    def initialize(self, context):
        ledger = self.state(context)
        prior = prediction.prior_model(ledger.commission['model'])
        ledger.put('model', prior, identity='reference_model')
        if context.role == 'hpc_prediction':
            current = self._current_model(ledger)
            ledger.put('model_entry', {'model_ref': current, 'quality': self._quality(ledger, ledger.read(current))},
                       identity='entry:'+context.episode_id)

    def initial_decision_context(self, context):
        """Pass concrete preparation bytes to the nested Launch iterations."""
        if context.role not in ('launch', 'launch_hpc'):
            return {}
        from method_loop.identities import EpisodeRef
        prefixes = [context.path[:i+1] for i, part in enumerate(context.path) if part[0] == 'hpc']
        if not prefixes:
            return {}
        # Runtime paths contain scope keys; compute the actual episode ID.
        owner = EpisodeRef(context.run_id, prefixes[-1]).episode_id
        ledger = HPCLedger.open_existing(self.directory/'hpc'/hpc_queue.digest([context.run_id, owner]))
        selected = plain(context.assignment)
        key = 'launch_assignment' if context.role == 'launch' else 'practical_assignment'
        plans = [row['body'] for row in ledger.records('plan') if row['body'][key] == selected]
        if len(plans) != 1 or ledger.read('owner')['scope'] != plain(context.scope):
            raise ValueError('hpc_launch_preparation_identity_conflict')
        plan = plans[0]
        return {'hpc_portfolio_preparation': {'plan_id': plan['plan_id'],
            'files_to_stage': plan['files_to_stage'], 'submission_arguments': plan['submission_arguments'],
            'workload_preparation': plan.get('preparation', ''),
            'instructions': 'Create the assigned workspace, write these exact files, verify their hashes, '
                'then submit the original requested job. Keep one physical allocation; recover its original '
                'handoff on interruption. Work units execute serially inside that allocation.'}}

    @staticmethod
    def _current_model(ledger):
        records = ledger.records('model_choice')
        return records[-1]['body']['model_ref'] if records else 'reference_model'

    @staticmethod
    def _quality(ledger, model):
        if not set(model['training_ids']) <= {row['id'] for row in ledger.commission['history']}:
            return None
        selected = [row for row in ledger.commission['history'] if row['id'] in ledger.commission['validation_ids']]
        return prediction.quality(model, selected) if selected else None

    @staticmethod
    def _history(ledger):
        rows = {row['id']: row for row in ledger.commission['history']}
        plans = {row['body']['plan_id']: row['body'] for row in ledger.records('plan')}
        closed = {row['body']['plan_id'] for row in ledger.records('closed')}
        # Keep one latest observation per actual allocation, not one training
        # example per poll. Failed unfinished work retains a censored duration.
        latest = {}
        for row in ledger.records('measured'):
            if row['body']['plan_id'] in closed:
                latest[row['body']['plan_id']] = row
        for plan_id, row in latest.items():
            body = row['body']
            rows['allocation:'+plan_id] = {'id': 'allocation:'+plan_id,
                'observed_at': body['observed_at'], 'features': plans[plan_id]['original_prediction']['features'],
                'metrics': body['metrics'], 'success': body['success'], 'provenance': [row['id']]}
        return rows

    def instructions(self, context):
        if context.role == 'hpc_prediction':
            return ('Iterate on a generalized time/resource model using measured historical cases. '
                'Inspect support and held-out quality, fit a disjoint training selection, and compare useful portfolios. '
                'The fixed reference and validation set cannot change. Model credit is modest measured improvement; '
                'the HPC parent later scores frozen predictions against real outcomes. Unknown inputs stay unknown. '
                'Return when further model improvement is less useful than running the next worthwhile portfolio.')
        return ('Iterate toward the original accomplishment while balancing expected credit against real elapsed time '
            'and node-hours. Queue/setup costs belong to an allocation, which should carry enough useful work. '
            'When candidates are absent, discover the remote environment and documentation with hpc.discovery.run, '
            'then design candidate portfolios with hpc.candidate.propose. Discover is for lightweight inspection; '
            'leave installation and file staging to Launch, and scientific computation to the actual allocation. '
            'You choose the real inputs, database, executable commands, resources, worker code and preparation instructions. '
            'Never fabricate inputs or receipts. Every work unit writes result.json in its current directory; '
            'its fields must satisfy the caller acceptance predicates. The environment contains HPC_UNIT_DIRECTORY. '
            'Candidate files use relative paths; {allocation_workspace} expands in files, argv, environment and '
            'preparation. Compute commands must run on allocated compute nodes using the facility launcher. '
            'Commission hpc_prediction only when model improvement warrants its own iteration. Compare portfolios '
            'using current queue features and measured history. A plan freezes its original forecast and supplies '
            'files and an exact launch assignment. Commission launch -> launch_hpc to prepare those files and '
            'obtain a usable original handoff. Attach that received handoff. Use hpc.monitor once when another '
            'observation can affect your decision; it revises conditional predictions and attainable credit. '
            'Use hpc.results directly for known parsing. Commission monitor/results children only for actual '
            'investigation. When hpc_monitor_controllers is present, select hpc.monitor.wait for a scheduled '
            'observation: its attached controller evaluates the conditional forecast, persists a wake time, '
            'and executes the original monitor at that time. This preserves pending accomplishment value '
            'across waits without credit for sleeping. The timer cannot turn into another unobserved wait. '
            'Do not poll for credit or launch overlapping allocations. Never replace an uncertain '
            'submission. Accepted accomplishment, model improvement, and fixed prospective forecast validation '
            'are the only parent credit components; launch-local credits are not added again.')

    def decision_context(self, context, current_view):
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        return {'hpc_commission': ledger.commission, 'hpc_owner_episode_id': ledger.read('owner')['episode_id'],
            'hpc_candidates': self._candidates(ledger),
            'hpc_resource': self.resources[ledger.commission['resource_id']],
            'hpc_model_ref': self._current_model(ledger), 'hpc_credit': self.credit_view(context, None),
            'hpc_plans': [{'plan_ref': row['id'], 'candidate_id': row['body']['candidate_id']}
                          for row in ledger.records('plan')],
            'hpc_latest_monitor': ledger.records('monitor')[-1:],
            'hpc_monitor_controllers': ledger.records('monitor_controller'),
            'hpc_activity_decision': self.decision_gate(context),
            'hpc_queue_refs': [row['id'] for row in ledger.records('queue')],
            'hpc_available_training_ids': sorted(set(self._history(ledger))-set(ledger.commission['validation_ids']))}

    def catalog(self, context):
        shared = [
            ('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': TEXT})),
            ('hpc.compare', 'Compare all approved portfolios; no work is selected or launched.',
                obj({'model_ref': TEXT, 'queue_ref': TEXT}))]
        if context.role == 'hpc_prediction':
            entries = shared+[('hpc.model.fit', 'Fit selected measured history; validate on the fixed disjoint cases.',
                               obj({'training_ids': STRINGS}))]
        else:
            entries = shared+[
                ('hpc.discovery.run', 'Run one lightweight remote inspection or documentation retrieval through the established SSH transport. No job submission, installation or scientific computation; those belong to Launch and the allocation.',
                    obj({'command': TEXT})),
                ('hpc.candidate.propose', 'Retain an executable portfolio selected by this episode within caller limits. candidate_json is JSON with id, queue, nodes, wall_seconds, features (numeric map), units (unit_id, obligation_id, argv, environment, effort, minimum_seconds, maximum_seconds, optional reports_progress), optional files [{path: relative path, text: exact contents}], and preparation instructions for Launch. Use {allocation_workspace} for the eventual directory. Existing candidate identities are immutable.',
                    obj({'candidate_json': TEXT})),
                ('hpc.queue.observe', 'Acquire PBS queue and ALCF score/status once and transform them.', obj({})),
                ('hpc.plan', 'Freeze one useful portfolio and its forecasts; return a concrete launch assignment.',
                    obj({'candidate_id': TEXT, 'model_ref': TEXT, 'queue_ref': TEXT})),
                ('hpc.handoff', 'Bind the original received PBS handoff to the exact frozen portfolio.',
                    obj({'plan_ref': TEXT, 'handoff_ref': TEXT})),
                ('hpc.monitor', 'Observe the original job and progress once; update and freeze conditional forecasts.',
                    obj({'plan_ref': TEXT, 'refresh_queue': {'type': 'boolean'}})),
                ('hpc.monitor.wait', 'Use the attached forecast-valued monitor controller: persist a timer, release the coordinator while waiting, then observe this original job exactly once when due. No earned credit for waiting.',
                    obj({'plan_ref': TEXT})),
                ('hpc.results', 'Parse compact results from the original allocation and apply original acceptance predicates.',
                    obj({'plan_ref': TEXT})),
                ('hpc.allocation.order', 'Reorder original pending units at the next unit boundary, retaining all unstarted work.',
                    obj({'plan_ref': TEXT, 'unit_ids': STRINGS}))]
        return [{'name': name, 'description': description, 'input_schema': schema}
                for name, description, schema in entries]

    def _queue(self, ledger, reference, *, require_fresh=False):
        observation = ledger.read(reference)['snapshot']
        if require_fresh and time.time()-observation['captured_at'] > ledger.commission['limits']['queue_max_age_seconds']:
            raise ValueError('fresh_queue_observation_required_before_planning')
        return observation

    @staticmethod
    def _candidates(ledger):
        return ledger.commission['candidates']+[row['body'] for row in ledger.records('candidate')]

    @staticmethod
    def _features(candidate, queue):
        return {**candidate['features'], 'nodes': candidate['nodes'], 'wall_seconds': candidate['wall_seconds'],
            **{key: value for key, value in queue.items() if type(value) in (int, float) or value is None}}

    def _comparisons(self, ledger, model_ref, queue_ref):
        model = ledger.read(model_ref)
        observed = self._queue(ledger, queue_ref)
        actual = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual']
        results = []
        for candidate in self._candidates(ledger):
            queue = hpc_queue.features(observed, candidate)
            forecast = prediction.predict(model, self._features(candidate, queue))
            row = prediction.compare(candidate, forecast, ledger.commission['obligations'],
                                     ledger.commission['preferences'], already_credited=actual)
            row['queue_features'] = queue
            results.append(row)
        return sorted(results, key=lambda row: row['net_expected_value'], reverse=True)

    def _freeze(self, ledger, plan, predicted, reference, current, phase, operation_key):
        elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
        slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
            if slot['phase'] == phase and elapsed[slot['metric']] >= slot['minimum_elapsed_seconds']
            and predicted['times'][slot['metric']] is not None]
        body = ledger.once('issued:'+operation_key, 'forecast_issue', lambda: {
            'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted,
            'reference': reference, 'phase': phase, 'elapsed': elapsed})
        return ledger.freeze(body, slots)

    def _candidate(self, ledger, plan):
        return next(row for row in self._candidates(ledger) if row['id'] == plan['candidate_id'])

    @staticmethod
    def _last_forecast(ledger, plan):
        monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
        if monitors:
            return monitors[-1]
        forecasts = [row for row in ledger.records('forecast') if row['body']['plan_id'] == plan['plan_id']]
        return {'conditional_prediction': plan['original_prediction'], 'forecast_ref': forecasts[0]['id']}

    def continuation_for_action(self, context, operation_key):
        if context.role != 'hpc':
            return None
        from .hpc_monitoring import choose_schedule
        ledger = self.state(context)
        reference = 'continuation:'+operation_key
        old = [row for row in ledger.records('continuation') if row['id'] == reference]
        if old:
            return {'reference': reference, 'evidence': old[0]['body']}
        credited = [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
                    if row['kind'] == 'actual']
        remaining = set(ledger.commission['obligations'])-set(credited)
        evidence = {'run_id': context.run_id, 'episode_id': context.episode_id,
                    'operation_key': operation_key, 'earned_wait_credit': 0.}
        if not remaining:
            evidence.update(expected_continuation_credit=0., active_credit_ceiling=0.,
                            reason='original_obligations_accepted')
        else:
            closed = {row['body']['plan_id'] for row in ledger.records('closed')}
            controllers = [row for row in ledger.records('monitor_controller') if row['body']['plan_id'] not in closed]
            if not controllers:
                return None
            controller = controllers[-1]
            plan = next(row['body'] for row in ledger.records('plan')
                        if row['body']['plan_id'] == controller['body']['plan_id'])
            monitor = self._last_forecast(ledger, plan)
            current = monitor['conditional_prediction']
            state = current.get('telemetry', {}).get('state')
            if state in ('complete', 'failed'):
                # Parsing is still required; completion alone is not acceptance.
                unresolved = remaining.intersection(unit['obligation_id']
                    for unit in self._candidate(ledger, plan)['units'])
                value = sum(ledger.commission['obligations'][key]['credit'] for key in unresolved)
                valuation = {'expected_continuation_credit': value,
                    'value_kind': 'unresolved_acceptance_upper_bound',
                    'reason': 'observed_outputs_await_acceptance'}
                evidence['pending_action'] = 'collect'
            else:
                valuation = choose_schedule(current, self._candidate(ledger, plan), ledger.commission,
                    controller['body']['policy'], credited=credited, now=time.time(),
                    deadline_at=controller['body']['deadline_at'])
            evidence.update(valuation=valuation, expected_continuation_credit=valuation['expected_continuation_credit'],
                            forecast_ref=monitor['forecast_ref'], controller_ref=controller['id'])
            covered = {unit['obligation_id'] for row in ledger.records('plan')
                       if row['body']['plan_id'] not in closed for unit in self._candidate(ledger, row['body'])['units']}
            untrained = set(self._history(ledger))-set(ledger.commission['validation_ids'])-set(
                ledger.read(self._current_model(ledger))['training_ids'])
            # A multi-unit portfolio can still offer useful reordering; do not
            # declare that active opportunity exhausted without evaluating it.
            fixed_single_unit = len(self._candidate(ledger, plan)['units']) == 1
            if not remaining-covered and not untrained and fixed_single_unit:
                evidence.update(active_credit_ceiling=0.,
                    active_exhaustion_reason='all_remaining_obligations_pending_and_no_new_training_cases')
        if self.store is not None:
            # Received delayed results and clock waits are not evidence of the
            # marginal yield of more active exploration/planning actions.
            passive = {'hpc.monitor', 'hpc.monitor.wait', 'hpc.results'}
            rows = self.store.db.execute('SELECT o.unit_index,a.action FROM runtime_observations o '
                'JOIN runtime_actions a ON a.run_id=o.run_id AND a.episode_id=o.episode_id '
                "AND a.decision_index=json_extract(o.observation,'$.decision_index') "
                'WHERE o.run_id=? AND o.episode_id=? ORDER BY o.unit_index', (context.run_id, context.episode_id)).fetchall()
            indices = [row[0] for row in rows if (action := json.loads(row[1])).get('kind') != 'wait'
                       and action.get('tool') not in passive]
            index = int(operation_key.rsplit(':', 1)[1])
            current = self.store.db.execute('SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? '
                'AND decision_index=?', (context.run_id, context.episode_id, index)).fetchone()
            if current is not None:
                action = json.loads(current[0])
                if action.get('kind') != 'wait' and action.get('tool') not in passive:
                    indices.append(len(rows))
            evidence['active_history_indices'] = indices
        ledger.put('continuation', evidence, identity=reference)
        return {'reference': reference, 'evidence': evidence}

    def decision_gate(self, context):
        if context.role != 'hpc' or self.store is None:
            return None
        row = self.store.db.execute('SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? '
            'ORDER BY unit_index DESC LIMIT 1', (context.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        diagnostic = json.loads(row[0])['step']['estimate']['diagnostics']
        mode = diagnostic.get('activity_mode')
        if mode not in ('wait', 'collect'):
            return None
        ledger = self.state(context)
        if not ledger.records('monitor_controller'):
            return None
        tool = ('hpc.results' if mode == 'collect' else
                'hpc.monitor.wait' if ledger.records('monitor') else 'hpc.monitor')
        return {'mode': mode, 'allowed_tools': [tool], 'common_actions': ['tool'],
                'active_next_gain': diagnostic['active_next_gain'],
                'pending_expected_credit': diagnostic['pending_expected_credit'],
                'pending_credit_upper_bound': diagnostic.get('pending_credit_upper_bound')}

    def practical_estimator(self, context):
        if context.role != 'hpc':
            return None
        from .hpc_monitoring import HPCContinuationEstimator
        ledger = self.state(context)
        def verify(packet):
            return ledger.read(packet['reference']) == packet['evidence']
        return HPCContinuationEstimator(verify)

    def _target(self, context, ledger, plan):
        handoff = ledger.read('handoff:'+plan['plan_id'])
        if (handoff['handoff_ref'] not in self._known(context)
                or not reference_in_context(self.services, context, handoff['handoff_ref'], None)):
            raise ValueError('original_handoff_not_received_by_this_parent')
        target = self.targets.read_target(handoff['handoff_ref'], context.scope)
        if target['assignment'] != plan['practical_assignment']:
            raise ValueError('handoff_does_not_match_frozen_portfolio')
        return target

    def _known(self, context):
        known = set(context.received_record_refs)
        selection = getattr(self.services, 'record_selection', None)
        if callable(selection):
            known.update(selection(context)['known_record_refs'])
        return known

    def resolve_received_reference(self, context, reference, namespace):
        try:
            source = self.store.get(reference)
        except (KeyError, ValueError):
            return None
        if source.get('provider') != 'episode.hpc_result':
            return None
        if namespace not in (None, 'source') or reference not in self._known(context):
            return False
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        if body['run_id'] != self.run_id:
            return False
        try:
            self.store.validate_scope(body['scope'], parent_scope=plain(context.scope))
        except ValueError:
            return False
        return True

    def read_evidence(self, context, ledger, reference):
        if not reference.startswith('source_'):
            return ledger.read(reference)
        # Results publish ordinary Store Sources as well as ledger receipts.
        # Resolve only a received Source owned by this original HPC ledger.
        rows = [row['body'] for row in ledger.records('result')
                if row['body'].get('source_ref') == reference]
        if len(rows) != 1 or self.resolve_received_reference(context, reference, 'source') is not True:
            raise ValueError('hpc_result_source_not_received_or_not_owned')
        source = self.store.get(reference)
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        expected = {key: value for key, value in rows[0].items() if key != 'source_ref'}
        if body != expected:
            raise ValueError('hpc_result_source_receipt_conflict')
        return rows[0]

    def _window(self, target, path, limit, operation_key):
        value = self.targets.read_file(target, path=path, offset=0, limit=limit+1, operation_key=operation_key)
        payload = base64.b64decode(value['bytes_base64'], validate=True)
        if len(payload) != value['size_bytes'] or len(payload) > limit:
            raise ValueError('compact_result_incomplete_or_too_large')
        return value, payload

    def _allocation(self, target, plan, operation_key):
        path = plan['manifest']['workspace']+'/allocation-status.json'
        try:
            window, payload = self._window(target, path, 512*1024, operation_key)
        except (FileNotFoundError, ValueError) as error:
            # Absence before the runner starts is normal; other failures remain
            # visible and do not manufacture a progress estimate.
            return None, {'path': path, 'failure': str(error)}
        value = json.loads(payload)
        if (value['plan_id'] != plan['plan_id'] or value['job_id'] != target['execution_id']
                or value['manifest_sha256'] != plan['manifest_sha256']):
            raise ValueError('allocation_receipt_identity_conflict')
        expected = {unit['unit_id'] for unit in plan['manifest']['units']}
        if len({row['unit_id'] for row in value['units']}) != len(value['units']) or not {row['unit_id'] for row in value['units']} <= expected:
            raise ValueError('allocation_receipt_units_conflict')
        return value, window

    def _measure(self, ledger, plan, observation, current, allocation):
        now = current['observed_at']
        metrics = {}
        if current['queued_at'] is not None:
            metrics['queue'] = {'seconds': current['queue_elapsed_seconds'],
                'censored': current['started_at'] is None, 'observed_at': current['started_at'] or now}
        receipt = observation['native'].get('exit_receipt')
        if receipt:
            metrics['work'] = {'seconds': receipt['duration_seconds'], 'censored': current['state'] == 'failed',
                               'observed_at': timestamp(receipt['finished_at'])}
        elif current['started_at'] is not None:
            metrics['work'] = {'seconds': current['work_elapsed_seconds'], 'censored': True, 'observed_at': now}
        if allocation and current['started_at'] is not None:
            metrics['setup'] = {'seconds': max(0., allocation['started_at']-current['started_at']),
                               'censored': False, 'observed_at': allocation['started_at']}
            if allocation.get('finished_at') is not None:
                metrics['work'] = {'seconds': allocation['finished_at']-allocation['started_at'],
                                  'censored': False, 'observed_at': allocation['finished_at']}
        measured = {'plan_id': plan['plan_id'], 'metrics': metrics, 'observed_at': now,
                    'success': False if current['state'] == 'failed' else None}
        reference = ledger.put('measured', measured)
        ledger.score(reference)
        return reference

    def _publish(self, context, body):
        artifact = self.store.artifact(hpc_queue.canonical(body), 'application/json')
        return self.store.put('source', {'provider': 'episode.hpc_result',
            'accession': 'hpc_'+hpc_queue.digest([self.run_id, context.episode_id, body]),
            'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': 'hpc_result_v1', 'retrieved_at': datetime.fromtimestamp(
                body['unit']['finished_at'], timezone.utc).isoformat()},
            origin='tool')['id']

    async def execute(self, context, tool_name, arguments, operation_key):
        entries = {row['name']: row for row in self.catalog(context)}
        if tool_name not in entries:
            raise ValueError('tool_not_available_to_hpc_role')
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]['input_schema'])
        ledger = self.state(context)
        if not ledger.records('model'):
            self.initialize(context)
        selection = {'tool': tool_name, 'arguments': arguments, 'episode_id': context.episode_id}
        old = ledger.cached(operation_key, selection)
        if old is not None:
            return old
        ledger.put('action_intent', selection, identity='action:'+operation_key)
        references = []
        commission = ledger.commission
        configuration = self.resources[commission['resource_id']]
        if tool_name == 'hpc.read':
            result = self.read_evidence(context, ledger, arguments['reference'])
        elif tool_name == 'hpc.discovery.run':
            # Read-only discovery can be repeated after interrupted observation;
            # all mutations and submissions use the durable Launch operations.
            command = ('cd '+shlex.quote('/lus/flare/projects/BioReason-Aurora-Test')+
                       ' && '+arguments['command'])
            def observe():
                completed = subprocess.run([*configuration['ssh_argv'], command],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
                return {'command': arguments['command'], 'returncode': completed.returncode,
                    'stdout': completed.stdout[:65536].decode('utf-8', 'replace'),
                    'stderr': completed.stderr[:8192].decode('utf-8', 'replace'),
                    'observed_at': time.time(), 'truncated': len(completed.stdout) > 65536}
            result = await asyncio.to_thread(ledger.once, 'discovery:'+operation_key, 'discovery', observe)
        elif tool_name == 'hpc.candidate.propose':
            candidate = json.loads(arguments['candidate_json'])
            candidates = self._candidates(ledger)
            prior = next((row for row in candidates if row['id'] == candidate['id']), None)
            if prior is not None and prior != candidate:
                raise ValueError('candidate_identity_is_immutable')
            validate_commission({**commission, 'candidates': candidates if prior else candidates+[candidate]}, self.resources)
            reference = ('caller_candidate:'+candidate['id'] if candidate in commission['candidates'] else
                         ledger.put('candidate', candidate, identity='candidate:'+candidate['id']))
            result = {'candidate_ref': reference, 'candidate_id': candidate['id']}
        elif tool_name == 'hpc.queue.observe':
            reference = 'queue:'+operation_key
            result = ledger.once(reference, 'queue', lambda: hpc_queue.observe(configuration))
            result = {'queue_ref': reference, 'features': [hpc_queue.features(result['snapshot'], candidate)
                                                         for candidate in self._candidates(ledger)],
                      'snapshot': result['snapshot']}
        elif tool_name == 'hpc.model.fit':
            selected = set(arguments['training_ids'])
            cases = self._history(ledger)
            if not selected <= set(cases) or selected.intersection(commission['validation_ids']):
                raise ValueError('training_ids_must_be_original_nonvalidation_cases')
            heldout = [cases[key] for key in commission['validation_ids']]
            historical_selected = selected.intersection(row['id'] for row in commission['history'])
            if historical_selected and heldout and max(cases[key]['observed_at'] for key in historical_selected) >= min(row['observed_at'] for row in heldout):
                raise ValueError('training_must_precede_temporal_validation')
            model = prediction.fit(commission['model'], [cases[key] for key in selected])
            model_ref = ledger.put('model', model)
            # Fixed historical validation cannot measure a model trained on
            # later completed allocations. Those updates earn prospective
            # credit when the next real outcomes arrive, not retrospective Q.
            later_training = selected-set(row['id'] for row in commission['history'])
            quality = None if later_training else self._quality(ledger, model)
            baseline = self._quality(ledger, ledger.read('reference_model'))
            ledger.put('model_choice', {'operation_key': operation_key, 'model_ref': model_ref})
            if quality is not None:
                ledger.model_credit(model_ref, quality-baseline)
            else:
                ledger.model_credit(model_ref, 0.)
            result = {'model_ref': model_ref, 'validation_quality': quality,
                      'reference_quality': baseline, 'credit': ledger.credit_view()}
        elif tool_name == 'hpc.compare':
            result = {'comparisons': self._comparisons(ledger, arguments['model_ref'], arguments['queue_ref'])}
        elif tool_name == 'hpc.plan':
            existing = ledger.records('plan')
            own = next((row for row in existing if row['body'].get('operation_key') == operation_key), None)
            if own is not None:
                plan = own['body']
                forecast_ref = self._freeze(ledger, plan, plan['original_prediction'], plan['original_reference'], {}, 'planned', operation_key)
                return ledger.save_action(operation_key, selection, {'status': 'completed', 'record_refs': [],
                    'changed_record_refs': [], 'result': {'plan_ref': own['id'], 'forecast_ref': forecast_ref, **plan}})
            closed = {row['body']['plan_id'] for row in ledger.records('closed')}
            if any(row['body']['plan_id'] not in closed for row in existing):
                raise ValueError('one_active_allocation_per_hpc_parent; retain_original_plan')
            observed = self._queue(ledger, arguments['queue_ref'], require_fresh=True)
            candidate = next(row for row in self._candidates(ledger) if row['id'] == arguments['candidate_id'])
            queue = hpc_queue.features(observed, candidate)
            rules = queue['queue_rules']
            if not rules or not rules['enabled'] or not rules['started'] or rules['type'] != 'Execution':
                raise ValueError('choose_an_observed_enabled_execution_queue')
            for key, value in (('nodes', candidate['nodes']), ('wall_seconds', candidate['wall_seconds'])):
                if rules['min_'+key] is not None and value < rules['min_'+key] or rules['max_'+key] is not None and value > rules['max_'+key]:
                    raise ValueError('candidate_violates_observed_queue_limits')
            used = sum(self._candidate(ledger, row['body'])['nodes']*self._candidate(ledger, row['body'])['wall_seconds']/3600 for row in existing)
            if used+candidate['nodes']*candidate['wall_seconds']/3600 > commission['limits']['max_node_hours']:
                raise ValueError('commission_node_hour_budget_exhausted')
            plan = build_plan(commission, candidate, configuration, ledger.read('owner'), len(existing))
            features = self._features(candidate, queue)
            predicted = prediction.predict(ledger.read(arguments['model_ref']), features)
            reference = prediction.predict(ledger.read('reference_model'), features)
            plan.update(model_ref=arguments['model_ref'], queue_ref=arguments['queue_ref'],
                        original_prediction=predicted, original_reference=reference, operation_key=operation_key)
            plan_ref = ledger.put('plan', plan)
            forecast_ref = self._freeze(ledger, plan, predicted, reference, {}, 'planned', operation_key)
            result = {'plan_ref': plan_ref, 'forecast_ref': forecast_ref, **plan}
        elif tool_name == 'hpc.handoff':
            plan = ledger.read(arguments['plan_ref'])
            if (arguments['handoff_ref'] not in self._known(context)
                    or not reference_in_context(self.services, context, arguments['handoff_ref'], None)):
                raise ValueError('handoff_not_received')
            target = self.targets.read_target(arguments['handoff_ref'], context.scope)
            if target['assignment'] != plan['practical_assignment']:
                raise ValueError('handoff_does_not_match_frozen_portfolio')
            ledger.put('handoff', {'handoff_ref': arguments['handoff_ref'], 'job_id': target['execution_id'],
                'plan_id': plan['plan_id']}, identity='handoff:'+plan['plan_id'])
            result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
            if 'monitoring' in commission:
                from .hpc_monitoring import MonitorCronController
                result['monitor_controller_ref'] = MonitorCronController(ledger).attach(
                    plan, target['execution_id'], commission['monitoring'])
        else:
            plan = ledger.read(arguments['plan_ref'])
            target = self._target(context, ledger, plan)
            candidate = self._candidate(ledger, plan)
            if tool_name == 'hpc.monitor.wait':
                from .hpc_monitoring import MonitorCronController
                controller = MonitorCronController(ledger)
                schedule = controller.reserve(plan, candidate, self._last_forecast(ledger, plan), operation_key)
                if schedule['job_id'] != target['execution_id']:
                    raise ValueError('monitor_schedule_original_job_conflict')
                if schedule['valuation']['schedule']:
                    await controller.wait(schedule)
                    observed = await self.execute(context, 'hpc.monitor',
                        {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, operation_key+':monitor')
                    ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'],
                        'job_id': target['execution_id'], 'observed': observed}, identity='wake:'+operation_key)
                    result = {'schedule': schedule, 'monitor': observed['result']}
                else:
                    result = {'schedule': schedule, 'monitor': None}
            elif tool_name == 'hpc.allocation.order':
                allowed = {unit['unit_id'] for unit in candidate['units']}
                if not set(arguments['unit_ids']) <= allowed:
                    raise ValueError('only_original_work_units_can_be_selected')
                result = self.targets.operations[target['resource_id']].write_allocation_control(
                    target['assignment'], target['execution_id'], **self.targets._native_identity(target),
                    unit_ids=arguments['unit_ids'], operation_key=operation_key)
                ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': operation_key,
                                                'unit_ids': arguments['unit_ids'], 'receipt': result})
            else:
                observation = ledger.once('status:'+operation_key, 'native_status',
                    lambda: self.targets.observe_target(target, operation_key=operation_key))
                allocation, allocation_window = ledger.once('allocation:'+operation_key, 'allocation_snapshot',
                    lambda: list(self._allocation(target, plan, operation_key+':allocation')))
                observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                    'allocation': allocation, 'allocation_window': allocation_window})
                current = telemetry(observation, allocation, candidate)
                if current.get('current_unit_id') is not None:
                    unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
                    if unit.get('reports_progress', False):
                        progress_path = plan['manifest']['workspace']+'/units/'+unit['unit_id']+'/progress.json'
                        try:
                            progress_window = ledger.once('unit-progress:'+operation_key, 'unit_progress',
                                lambda: self._window(target, progress_path, 16384, operation_key+':progress')[0])
                            progress = json.loads(base64.b64decode(progress_window['bytes_base64'], validate=True))
                            if progress['plan_id'] != plan['plan_id']:
                                raise ValueError('unit_progress_plan_identity_conflict')
                            current = incorporate_progress(current, progress, candidate)
                        except (OSError, ValueError) as error:
                            current['progress_failure'] = str(error)
                prior_monitors = [row['body'] for row in ledger.records('monitor')
                                  if row['body']['plan_id'] == plan['plan_id']]
                if prior_monitors:
                    previous = prior_monitors[-1]['conditional_prediction']['telemetry']
                    current['phase_changed'] = (previous.get('phase'), previous.get('current_unit_id')) != (
                        current.get('phase'), current.get('current_unit_id'))
                    dt = current['observed_at']-previous['observed_at']
                    if dt > 0 and 'completed_fraction' in current and 'completed_fraction' in previous:
                        current['recent_fraction_per_second'] = max(0., current['completed_fraction']-previous['completed_fraction'])/dt
                measured_ref = self._measure(ledger, plan, observation, current, allocation)
                if tool_name == 'hpc.monitor':
                    refreshed = None
                    queue_ref = plan['queue_ref']
                    if arguments['refresh_queue']:
                        queue_ref = 'queue:'+operation_key
                        queue_value = ledger.once(queue_ref, 'queue', lambda: hpc_queue.observe(configuration))
                        queue = hpc_queue.features(queue_value['snapshot'], candidate, job_id=target['execution_id'])
                        refreshed = prediction.predict(ledger.read(self._current_model(ledger)),
                            self._features(candidate, queue))['times']['queue']
                    predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
                    reference = prediction.update(plan['original_reference'], current)
                    forecast_ref = self._freeze(ledger, plan, predicted, reference, current, current['state'], operation_key)
                    orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
                    ordered_candidate = deepcopy(candidate)
                    if orders:
                        units = {row['unit_id']: row for row in candidate['units']}
                        first = [current['current_unit_id']] if current.get('current_unit_id') else []
                        ids = list(dict.fromkeys([*first, *orders[-1]['unit_ids'], *units]))
                        ordered_candidate['units'] = [units[identity] for identity in ids]
                    result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref,
                        'measured_ref': measured_ref, 'forecast_ref': forecast_ref, 'queue_ref': queue_ref,
                        'conditional_prediction': predicted, 'remaining_work': prediction.compare(ordered_candidate,
                            predicted, commission['obligations'], commission['preferences']),
                        'next_observation': 'Choose an event/elapsed threshold where changed evidence could alter a decision.'}
                    ledger.put('monitor', result)
                else:
                    accepted, failures = [], []
                    for row in (allocation or {}).get('units', []):
                        if row['state'] != 'complete' or row.get('returncode') != 0 or not row.get('result_path'):
                            continue
                        unit = next(unit for unit in candidate['units'] if unit['unit_id'] == row['unit_id'])
                        expected_path = plan['manifest']['workspace']+'/units/'+unit['unit_id']+'/result.json'
                        if row['result_path'] != expected_path or row['obligation_id'] != unit['obligation_id']:
                            raise ValueError('result_not_owned_by_original_work_unit')
                        window = ledger.once('result-window:'+operation_key+':'+unit['unit_id'], 'result_window',
                            lambda: self._window(target, expected_path, commission['limits']['result_limit_bytes'],
                                                operation_key+':'+unit['unit_id'])[0])
                        payload = base64.b64decode(window['bytes_base64'], validate=True)
                        if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
                            raise ValueError('result_changed_since_unit_completion')
                        document = json.loads(payload)
                        receipt = {'run_id': self.run_id, 'episode_id': context.episode_id, 'scope': plain(context.scope),
                            'plan_id': plan['plan_id'], 'job_id': target['execution_id'], 'unit': row,
                            'document': document, 'window': window, 'observation_ref': observation_ref}
                        source_ref = self._publish(context, receipt)
                        references.append(source_ref)
                        result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
                        if accepts(document, commission['obligations'][unit['obligation_id']]):
                            ledger.accept(unit['obligation_id'], result_ref)
                            accepted.append({'obligation_id': unit['obligation_id'], 'result_ref': result_ref})
                        else:
                            failures.append({'unit_id': unit['unit_id'], 'reason': 'original_acceptance_predicate_not_met'})
                    if current['state'] in ('complete', 'failed'):
                        measured = ledger.read(measured_ref)
                        if allocation is not None:
                            measured['success'] = len(accepted) == len(candidate['units'])
                            measured['observed_at'] = max(measured['observed_at'], time.time())
                            ledger.put('measured', measured)
                        ledger.put('closed', {'plan_id': plan['plan_id'], 'observation_ref': observation_ref})
                    result = {'accepted': accepted, 'rejected': failures, 'observation_ref': observation_ref,
                              'credit': ledger.credit_view()}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)

    def fact_sources(self, role):
        self.credit_kind(role)
        return {'hpc_credit': {'type': 'number', 'meaning': 'Signed measured credit; repeated polling adds none.'},
                'hpc_model_ref': {'type': 'string', 'meaning': 'Immutable selected prediction model identity.'},
                'hpc_accepted_obligations': {'type': 'array', 'meaning': 'Original obligations with accepted actual results.'},
                'hpc_result_refs': {'type': 'array', 'meaning': 'Sources containing original result bytes and attempt custody.',
                    'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {
                        'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'},
                        'x-source': 'hpc_result_refs'}}}

    def facts(self, context, completion_snapshot):
        ledger = self.state(context)
        return {'hpc_credit': self.credit_view(context, None)['credit'], 'hpc_model_ref': self._current_model(ledger),
            'hpc_accepted_obligations': [row['slot'].removeprefix('actual:') for row in ledger.credit_view()['contributions']
                                         if row['kind'] == 'actual'],
            'hpc_result_refs': [ledger.read(row['evidence_id'])['source_ref']
                               for row in ledger.credit_view()['contributions'] if row['kind'] == 'actual']}

    def resolve(self, context, reference, namespace):
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda ref, namespace: self.resolve(context, ref, namespace))
        facts = self.facts(context, {})
        for field, schema in original_schema.get('properties', {}).items():
            source = schema.get('x-source')
            if source in facts and form[field] != facts[source]:
                raise ValueError('hpc_report_disagrees_with_recorded_evidence')

    def credit_view(self, context, receiver_selection):
        ledger = self.state(context)
        if context.role == 'hpc':
            return ledger.credit_view()
        entries = ledger.records('model_entry')
        entry = next((row['body'] for row in entries if row['id'] == 'entry:'+context.episode_id), None)
        current = self._quality(ledger, ledger.read(self._current_model(ledger)))
        gain = current-entry['quality'] if entry and current is not None and entry['quality'] is not None else 0.
        return {'credit': ledger.commission['credit']['model_scale']*gain,
                'model_quality_improvement': gain, 'actual_job_credit_counted_here': False}
