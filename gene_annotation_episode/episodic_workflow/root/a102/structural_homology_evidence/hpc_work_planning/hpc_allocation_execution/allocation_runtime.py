"""A102 HPC allocation execution on the generic runner (``episode_runtime``), role ``hpc_execution``.

One Episode executes one frozen plan of its owner's HPC ledger (``episode_support/jobs/hpc/structural_homology_evidence/hpc_ledger.py``): its
``role_assignment`` is exactly ``owner_episode_id`` (the ``hpc_work_planning`` Episode that owns the
ledger) and ``plan_ref`` (the frozen plan). Each unit is selected by the model collaborator from the
Episode's actual allocation state:

- ``hpc.read``: read retained HPC evidence by its exact identity;
- ``hpc.handoff``: bind the launch handoff this Episode received to its frozen plan. The handoff is the
  ``episode.practical_receipt`` source the HPC job execution published to the run's shared Store; its
  reference must appear in a launch child's admitted return. The receipt's run, scope and original
  assignment must equal this run, this scope and the plan's practical assignment, and its actual native
  job (the scheduler audit's ``actual_job``) must be the job its handoff names;
- ``hpc.monitor``: observe that PBS job once through the resource transport (``TerminalExecution``), read
  the allocation's ``allocation-status.json`` and the current unit's progress, measure the outcome
  (scoring frozen forecasts) and freeze an updated conditional forecast;
- ``hpc.results``: observe once, read each finished unit's ``result.json`` window, check it against the
  unit's completion hash, publish it to the Store as an ``episode.hpc_result`` source and accept the
  obligation when the caller's frozen acceptance predicates hold; close the allocation when the job is
  terminal (and export its measurement to the shared execution memory when one is configured);
- ``hpc.allocation.order``: write the selected ordering of the original pending units;
- a child commission: ``execution_job_submission`` (launch; its assignment must carry the plan's frozen
  launch or practical assignment, and only one launch per plan is admitted), the progress monitor or
  result acquisition, each with the child's own declared assignment.

Every executed outcome, including an invalid or failed one, is recorded (``outcome.<position>``) and
enters the iterator with the credit measured after it and the Episode's progress receipt. A response that
fails admission creates no unit; the model decides again with that feedback.

Credit is this allocation's own ledger contributions, never bounded, clamped or rescaled: the accepted
obligations whose result belongs to this plan and the prospective validation scores of this plan's
frozen forecasts. Continuation is one ``AccumulationYieldController`` from the commission's own
``yield_bindings['hpc_execution']``.

Runtime collaborators (each required): ``model_provider`` and ``store`` (standard) and ``a102_hpc``
(``hpc_runtime.HPCServices``).

A parent's per-commission typed report form (C5) may add any of this Episode's recorded finding facts
(``FINDING_FACTS``); each added field is filled from them and a field with no fact raises when the Episode
is built.
"""
from __future__ import annotations

import asyncio
import base64
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import time

from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import Commission
from method_loop import ChildEpisodeUnit, Episode, EpisodeGoal, EpisodeRequest, Leaf, ReportContract

from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc import hpc_queue
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_campaign import accepts, bind_progress, incorporate_progress, telemetry, timestamp
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_ledger import HPCLedger
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence import hpc_prediction as prediction
from gene_annotation_episode.episodic_workflow.episode_support.tools.commissioned_report import added_fields
from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_resource_prediction import pbs_resource_metrics
from ..hpc_runtime import (AXIS, FINDING, MODEL_ROLE, REPORT, ROLE_FIELD, SERVICES, HPCRecord, HPCRuntimeError,
                           _STRINGS, _TEXT, _candidates, _current_model, _features, _ledger_directory,
                           _observe_queue, _validate, obj, plain, result_record, services_of)

EXECUTION = 'hpc_execution'
LAUNCH_HOME = 'execution_job_submission'
RECEIPT_PROVIDER = 'episode.practical_receipt'
RECEIPT_VERSION = 'practical_receipt_information_v1'
RESULT_PROVIDER = 'episode.hpc_result'
# The recorded finding facts a commissioned report form (C5) may add: (field type, may be unknown).
FINDING_FACTS = {'scope': ('record', False), 'hpc_role': ('text', False), 'hpc_plan_ref': ('text', False),
                 'hpc_plan_id': ('text', False), 'hpc_credit': ('record', False), 'hpc_job_id': ('text', True),
                 'hpc_handoff_ref': ('text', True), 'hpc_result_refs': ('list', False),
                 'hpc_result_source_refs': ('list', False), 'hpc_monitor_refs': ('list', False),
                 'hpc_closed': ('boolean', False), 'hpc_ledger': ('text', False), 'ended_by': ('text', False),
                 'units': ('integer', False)}


def _transport(services, ledger):
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.local_execution.structural_homology_evidence.terminal_execution import TerminalExecution
    return TerminalExecution(services.resources[ledger.commission['resource_id']])


def _received_strings(value, found):
    """Every text value of an admitted child return: the references this Episode received."""
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            _received_strings(item, found)
    elif isinstance(value, list):
        for item in value:
            _received_strings(item, found)
    return found


def _contains(value, wanted):
    if value == wanted:
        return True
    if isinstance(value, Mapping):
        return any(_contains(item, wanted) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, wanted) for item in value)
    return False


# -- the commission's ledger and this Episode's plan ---------------------------------------------------------

def open_allocation(bound, services, store):
    """The owner's ledger and the frozen plan this Episode executes."""
    scope = plain(bound.assignment['scope'])
    if plain(store.validate_scope(scope)) != scope:
        raise HPCRuntimeError(AXIS + '_hpc_scope_must_be_store_admitted')
    value = _validate(plain(bound.assignment[ROLE_FIELD]), obj({'owner_episode_id': _TEXT, 'plan_ref': _TEXT}),
                      AXIS + '_hpc_execution_role_assignment_requires_exactly_owner_episode_id_and_plan_ref')
    ledger = HPCLedger.open_existing(_ledger_directory(services, bound.run_id, value['owner_episode_id']))
    owner = ledger.read('owner')
    if owner['run_id'] != bound.run_id or owner['episode_id'] != value['owner_episode_id'] or owner['scope'] != scope:
        raise HPCRuntimeError(AXIS + '_hpc_execution_must_share_its_owner_run_and_scope')
    if 'yield_bindings' not in ledger.commission:
        raise HPCRuntimeError(AXIS + '_hpc_commission_yield_bindings_required')
    plans = [row['body'] for row in ledger.records('plan') if row['id'] == value['plan_ref']]
    if len(plans) != 1:
        raise HPCRuntimeError(AXIS + '_hpc_execution_plan_ref_is_not_a_frozen_plan:' + value['plan_ref'])
    return ledger, scope, value['plan_ref'], plans[0]


def _candidate(ledger, plan):
    return next(row for row in _candidates(ledger) if row['id'] == plan['candidate_id'])


def credit_view(ledger, plan):
    """This allocation's own contributions: accepted obligations and validation scores of this plan."""
    contributions = []
    for row in ledger.credit_view()['contributions']:
        evidence = ledger.read(row['evidence_id'])
        if row['kind'] == 'actual' and evidence['plan_id'] == plan['plan_id']:
            contributions.append(row)
        elif row['kind'] == 'validation' and ledger.read(evidence['measured_ref'])['plan_id'] == plan['plan_id']:
            contributions.append(row)
    components = {kind: math.fsum(row['credit'] for row in contributions if row['kind'] == kind)
                  for kind in ('actual', 'validation')}
    return {'credit': math.fsum(components.values()), 'components': components, 'contributions': contributions}


def controller(bound, collaborators):
    from yield_control import AccumulationYieldController, YieldParameters
    ledger, _, _, plan = open_allocation(bound, services_of(collaborators), collaborators['store'])
    binding = ledger.commission['yield_bindings'][EXECUTION]
    initial = credit_view(ledger, plan)['credit']
    if not math.isfinite(initial):
        raise HPCRuntimeError(AXIS + '_hpc_initial_credit_not_finite')
    return AccumulationYieldController(EXECUTION, initial, binding['cutoff'], YieldParameters(**binding['parameters']))


# -- operations ----------------------------------------------------------------------------------------------

CATALOG = [
    ('hpc.read', 'Read retained HPC evidence by its exact identity.', obj({'reference': _TEXT})),
    ('hpc.handoff', 'Bind the launch handoff (the practical receipt reference a launch child returned) to this '
     "Episode's frozen plan.", obj({'handoff_ref': _TEXT})),
    ('hpc.monitor', 'Observe the original job and its progress once; measure it and freeze an updated conditional '
     'forecast. refresh_queue also observes the PBS queue once.', obj({'refresh_queue': {'type': 'boolean'}})),
    ('hpc.results', 'Parse compact results from the original allocation and apply the original acceptance '
     'predicates.', obj({})),
    ('hpc.allocation.order', 'Reorder the original pending units at the next unit boundary, retaining all '
     'unstarted work.', obj({'unit_ids': _STRINGS})),
]


def catalog():
    return [{'name': name, 'description': description, 'input_schema': schema}
            for name, description, schema in CATALOG]


class AllocationOperations:
    """The selected operations of one allocation Episode over its plan, ledger, Store and transport."""

    def __init__(self, services, ledger, store, bound, scope, plan):
        self.services, self.ledger, self.store, self.bound = services, ledger, store, bound
        self.scope, self.plan = scope, plan
        self.candidate = _candidate(ledger, plan)

    # The launch handoff and its native job identity.

    def handoff(self, handoff_ref, received):
        if handoff_ref not in received:
            raise ValueError('handoff_not_received_by_this_episode')
        source = self.store.get(handoff_ref)
        if source.get('record_type') != 'source' or source.get('provider') != RECEIPT_PROVIDER:
            raise ValueError('handoff_is_not_a_practical_receipt')
        body = json.loads(self.store.get_artifact(source['artifact_ref']))
        snapshot = json.loads(self.store.get_artifact(source['request_ref']))
        if (body.get('version') != RECEIPT_VERSION or body['run_id'] != self.bound.run_id
                or plain(body['scope']) != self.scope or snapshot['run_id'] != body['run_id']
                or snapshot['episode_id'] != body['episode_id']):
            raise ValueError('handoff_receipt_identity_conflict')
        if plain(snapshot['assignment']) != plain(self.plan['practical_assignment']):
            raise ValueError('handoff_does_not_match_frozen_portfolio')
        outcome = body['receipt']['outcome']
        actual = outcome.get('native_outcome', {}).get('actual_job')
        named = outcome.get('facts', {}).get('requested_job', {}).get('handoff', {}).get('execution_id')
        if not isinstance(actual, Mapping) or actual.get('job_id') != named:
            raise ValueError('handoff_receipt_names_no_actual_native_job')
        record = {'handoff_ref': handoff_ref, 'plan_id': self.plan['plan_id'], 'job_id': actual['job_id'],
                  'launch_run_id': body['run_id'], 'launch_episode_id': body['episode_id'], 'actual_job': actual}
        self.ledger.put('handoff', record, identity='handoff:' + self.plan['plan_id'])
        return {'plan_id': self.plan['plan_id'], 'job_id': actual['job_id']}

    def target(self):
        try:
            handoff = self.ledger.read('handoff:' + self.plan['plan_id'])
        except ValueError as error:
            raise ValueError('original_handoff_not_attached') from error
        return handoff

    def _identity(self, handoff):
        return {'run_id': handoff['launch_run_id'], 'episode_id': handoff['launch_episode_id'],
                'resource_id': self.ledger.commission['resource_id'], 'actual_job': handoff['actual_job']}

    def _window(self, handoff, path, limit):
        value = _transport(self.services, self.ledger).read_output(
            self.plan['practical_assignment'], handoff['job_id'], path=path, offset=0, limit=limit + 1,
            **self._identity(handoff))
        payload = base64.b64decode(value['bytes_base64'], validate=True)
        if len(payload) != value['size_bytes'] or len(payload) > limit:
            raise ValueError('compact_result_incomplete_or_too_large')
        return value, payload

    def _allocation(self, handoff):
        path = self.plan['manifest']['workspace'] + '/allocation-status.json'
        try:
            window, payload = self._window(handoff, path, 512 * 1024)
        except (FileNotFoundError, ValueError) as error:
            # Absence before the runner starts is normal; other failures stay visible and estimate nothing.
            return None, {'path': path, 'failure': str(error)}
        value = json.loads(payload)
        if (value['plan_id'] != self.plan['plan_id'] or value['job_id'] != handoff['job_id']
                or value['manifest_sha256'] != self.plan['manifest_sha256']):
            raise ValueError('allocation_receipt_identity_conflict')
        expected = {unit['unit_id'] for unit in self.plan['manifest']['units']}
        observed = [row['unit_id'] for row in value['units']]
        if len(set(observed)) != len(observed) or not set(observed) <= expected:
            raise ValueError('allocation_receipt_units_conflict')
        return value, window

    def observe(self, operation_key):
        """One authenticated observation of the job and its allocation, measured and scored."""
        handoff = self.target()
        ledger, plan, candidate = self.ledger, self.plan, self.candidate
        observation = ledger.once('status:' + operation_key, 'native_status', lambda: _transport(
            self.services, ledger).observe_execution(plan['practical_assignment'], handoff['job_id'],
                                                     **self._identity(handoff)))
        allocation, window = ledger.once('allocation:' + operation_key, 'allocation_snapshot',
                                         lambda: list(self._allocation(handoff)))
        observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation,
                                                     'allocation': allocation, 'allocation_window': window})
        current = telemetry(observation, allocation, candidate)
        if current.get('current_unit_id') is not None:
            unit = next(row for row in candidate['units'] if row['unit_id'] == current['current_unit_id'])
            if unit.get('reports_progress', False):
                path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
                try:
                    progress_window = ledger.once('unit-progress:' + operation_key, 'unit_progress',
                                                  lambda: self._window(handoff, path, 16384)[0])
                    progress = bind_progress(json.loads(base64.b64decode(progress_window['bytes_base64'],
                                                                         validate=True)), plan['plan_id'])
                    current = incorporate_progress(current, progress, candidate)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    current['progress_failure'] = str(error)
        prior = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
        if prior:
            previous = prior[-1]['conditional_prediction']['telemetry']
            current['phase_changed'] = ((previous.get('phase'), previous.get('current_unit_id'))
                                        != (current.get('phase'), current.get('current_unit_id')))
            elapsed = current['observed_at'] - previous['observed_at']
            if elapsed > 0 and 'completed_fraction' in current and 'completed_fraction' in previous:
                current['recent_fraction_per_second'] = max(
                    0., current['completed_fraction'] - previous['completed_fraction']) / elapsed
        measured_ref = self._measure(observation, current, allocation)
        return handoff, observation, allocation, observation_ref, current, measured_ref

    def _measure(self, observation, current, allocation):
        now = current['observed_at']
        metrics = pbs_resource_metrics(observation)
        if current['queued_at'] is not None:
            metrics['queue'] = {'seconds': current['queue_elapsed_seconds'], 'censored': current['started_at'] is None,
                                'observed_at': current['started_at'] or now}
        receipt = observation['native'].get('exit_receipt')
        if receipt:
            metrics['work'] = {'seconds': receipt['duration_seconds'], 'censored': current['state'] == 'failed',
                               'observed_at': timestamp(receipt['finished_at'])}
        elif current['started_at'] is not None:
            metrics['work'] = {'seconds': current['work_elapsed_seconds'], 'censored': True, 'observed_at': now}
        if allocation and current['started_at'] is not None:
            metrics['setup'] = {'seconds': max(0., allocation['started_at'] - current['started_at']),
                                'censored': False, 'observed_at': allocation['started_at']}
            if allocation.get('finished_at') is not None:
                metrics['work'] = {'seconds': allocation['finished_at'] - allocation['started_at'],
                                   'censored': False, 'observed_at': allocation['finished_at']}
        measured = {'plan_id': self.plan['plan_id'], 'metrics': metrics, 'observed_at': now,
                    'success': False if current['state'] == 'failed' else None}
        reference = self.ledger.put('measured', measured)
        self.ledger.score(reference)
        return reference

    def _freeze(self, predicted, reference, current, operation_key):
        ledger, plan = self.ledger, self.plan
        phase = current['state']
        elapsed = {'queue': current.get('queue_elapsed_seconds', 0.), 'work': current.get('work_elapsed_seconds', 0.)}
        slots = [slot['id'] for slot in ledger.commission['credit']['validation_slots']
                 if slot['phase'] == phase
                 and elapsed.get(slot['metric'], elapsed['work']) >= slot['minimum_elapsed_seconds']
                 and prediction.forecast_metric(predicted, slot['metric']) is not None]
        body = ledger.once('issued:' + operation_key, 'forecast_issue', lambda: {
            'plan_id': plan['plan_id'], 'issued_at': time.time(), 'prediction': predicted, 'reference': reference,
            'phase': phase, 'elapsed': elapsed, 'model_ref': plan.get('model_ref'),
            'prediction_episode_id': plan.get('prediction_episode_id')})
        return ledger.freeze(body, slots)

    def monitor(self, arguments, operation_key):
        ledger, plan, candidate = self.ledger, self.plan, self.candidate
        handoff, _, _, observation_ref, current, measured_ref = self.observe(operation_key)
        refreshed, queue_ref = None, plan['queue_ref']
        if arguments['refresh_queue']:
            queue_ref = 'queue:' + hpc_queue.digest(operation_key)
            configuration = self.services.resources[ledger.commission['resource_id']]
            observed = ledger.once(queue_ref, 'queue', lambda: _observe_queue(self.services, ledger, configuration))
            queue = hpc_queue.features(observed['snapshot'], candidate, job_id=handoff['job_id'])
            refreshed = prediction.predict(ledger.read(_current_model(ledger)),
                                           _features(candidate, queue))['times']['queue']
        predicted = prediction.update(plan['original_prediction'], current, refreshed_queue=refreshed)
        reference = prediction.update(plan['original_reference'], current)
        forecast_ref = self._freeze(predicted, reference, current, operation_key)
        orders = [row['body'] for row in ledger.records('allocation_order') if row['body']['plan_id'] == plan['plan_id']]
        ordered = deepcopy(candidate)
        if orders:
            units = {row['unit_id']: row for row in candidate['units']}
            first = [current['current_unit_id']] if current.get('current_unit_id') else []
            ordered['units'] = [units[key] for key in dict.fromkeys([*first, *orders[-1]['unit_ids'], *units])]
        result = {'plan_id': plan['plan_id'], 'observation_ref': observation_ref, 'measured_ref': measured_ref,
                  'forecast_ref': forecast_ref, 'queue_ref': queue_ref, 'conditional_prediction': predicted,
                  'remaining_work': prediction.compare(ordered, predicted, ledger.commission['obligations'],
                                                       ledger.commission['preferences'])}
        ledger.put('monitor', result)
        return result

    def _collected(self):
        return {row['body']['unit']['unit_id'] for row in self.ledger.records('result')
                if row['body']['plan_id'] == self.plan['plan_id']}

    def _publish(self, body):
        with self.store.transaction():
            artifact = self.store.artifact(hpc_queue.canonical(body), 'application/json')
            return self.store.put('source', {
                'provider': RESULT_PROVIDER, 'accession': 'hpc_' + hpc_queue.digest(
                    [self.bound.run_id, self.bound.episode_id, body]),
                'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                'version': 'hpc_result_v1', 'retrieved_at': datetime.fromtimestamp(
                    body['unit']['finished_at'], timezone.utc).isoformat()}, origin='tool')['id']

    def gather_results(self, operation_key):
        """The remote part of ``hpc.results``: one observation and each finished unit's verified result window."""
        ledger, plan, candidate = self.ledger, self.plan, self.candidate
        handoff, _, allocation, observation_ref, current, measured_ref = self.observe(operation_key)
        finished, rejected = [], []
        collected = self._collected()
        for row in (allocation or {}).get('units', []):
            if row['state'] not in ('complete', 'failed') or row['unit_id'] in collected:
                continue
            unit = next(unit for unit in candidate['units'] if unit['unit_id'] == row['unit_id'])
            path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/result.json'
            if not row.get('result_path'):
                rejected.append({'unit_id': unit['unit_id'], 'reason': 'missing_original_result_receipt',
                                 'expected_path': path})
                continue
            if row['result_path'] != path or row['obligation_id'] != unit['obligation_id']:
                raise ValueError('result_not_owned_by_original_work_unit')
            window = ledger.once('result-window:' + operation_key + ':' + unit['unit_id'], 'result_window',
                                 lambda: self._window(handoff, path,
                                                      ledger.commission['limits']['result_limit_bytes'])[0])
            payload = base64.b64decode(window['bytes_base64'], validate=True)
            if hashlib.sha256(payload).hexdigest() != row['result_sha256']:
                raise ValueError('result_changed_since_unit_completion')
            finished.append((row, unit, window, json.loads(payload)))
        return handoff, allocation, observation_ref, current, measured_ref, finished, rejected

    def conclude_results(self, gathered):
        """Publish each verified result to the Store, accept what meets its frozen predicates, close when terminal."""
        handoff, allocation, observation_ref, current, measured_ref, finished, rejected = gathered
        ledger, plan, candidate = self.ledger, self.plan, self.candidate
        accepted, references = [], []
        for row, unit, window, document in finished:
            receipt = {'run_id': self.bound.run_id, 'episode_id': self.bound.episode_id, 'scope': self.scope,
                       'plan_id': plan['plan_id'], 'job_id': handoff['job_id'], 'unit': row, 'document': document,
                       'window': window, 'observation_ref': observation_ref}
            source_ref = self._publish(receipt)
            references.append(source_ref)
            result_ref = ledger.put('result', {**receipt, 'source_ref': source_ref})
            if (row['state'] == 'complete' and row.get('returncode') == 0
                    and accepts(document, ledger.commission['obligations'][unit['obligation_id']])):
                ledger.accept(unit['obligation_id'], result_ref)
                accepted.append({'obligation_id': unit['obligation_id'], 'result_ref': result_ref})
            else:
                rejected.append({'unit_id': unit['unit_id'], 'reason': 'original_acceptance_predicate_not_met'})
        if current['state'] in ('complete', 'failed'):
            if allocation is not None:
                measured = ledger.read(measured_ref)
                own = {row['slot'].removeprefix('actual:') for row in credit_view(ledger, plan)['contributions']
                       if row['kind'] == 'actual'}
                measured['success'] = {unit['obligation_id'] for unit in candidate['units']} <= own
                measured['observed_at'] = max(measured['observed_at'], time.time())
                ledger.put('measured', measured)
            ledger.put('closed', {'plan_id': plan['plan_id'], 'observation_ref': observation_ref})
            self._export_closed(handoff)
        return {'accepted': accepted, 'rejected': rejected, 'observation_ref': observation_ref,
                'record_refs': references}

    def _export_closed(self, handoff):
        if self.services.memory is None:
            return
        from gene_annotation_episode.episodic_workflow.episode_support.jobs.hpc.structural_homology_evidence.hpc_history import closed_measurement
        plan = self.plan
        measured = self.ledger.once('export_measurement:' + plan['plan_id'], 'export_measurement', lambda: [
            row for row in self.ledger.records('measured') if row['body']['plan_id'] == plan['plan_id']][-1])
        self.services.memory.record(**closed_measurement(self.ledger.commission, plan, measured, handoff,
                                                         resources=self.services.resources,
                                                         ledger_path=self.ledger.path))

    def order(self, arguments, operation_key):
        handoff = self.target()
        if not set(arguments['unit_ids']) <= {unit['unit_id'] for unit in self.candidate['units']}:
            raise ValueError('only_original_work_units_can_be_selected')
        receipt = _transport(self.services, self.ledger).write_allocation_control(
            self.plan['practical_assignment'], handoff['job_id'], unit_ids=arguments['unit_ids'],
            operation_key=operation_key, **self._identity(handoff))
        self.ledger.put('allocation_order', {'plan_id': self.plan['plan_id'], 'operation_key': operation_key,
                                             'unit_ids': arguments['unit_ids'], 'receipt': receipt})
        return receipt

    async def execute(self, tool, arguments, operation_key, received):
        """Execute one selected operation; an argument, reference or transport failure is a returned invalid outcome."""
        if tool not in {name for name, _, _ in CATALOG}:
            raise HPCRuntimeError(AXIS + '_hpc_execution_tool_not_offered:' + tool)
        selection = {'tool': tool, 'arguments': arguments, 'episode_id': self.bound.episode_id}
        ledger = self.ledger
        old = ledger.cached(operation_key, selection)
        if old is not None:
            return old
        ledger.put('action_intent', selection, identity='action:' + operation_key)
        references = []
        try:
            if tool == 'hpc.read':
                result = ledger.read(arguments['reference'])
            elif tool == 'hpc.handoff':
                result = self.handoff(arguments['handoff_ref'], received)
                references = [arguments['handoff_ref']]
            elif tool == 'hpc.monitor':
                result = await asyncio.to_thread(self.monitor, arguments, operation_key)
            elif tool == 'hpc.results':
                # The transport work runs off the event loop; the Store is written on its own thread.
                result = self.conclude_results(await asyncio.to_thread(self.gather_results, operation_key))
                references = result.pop('record_refs')
            else:
                result = await asyncio.to_thread(self.order, arguments, operation_key)
        except (ValueError, KeyError, OSError) as error:
            return ledger.save_action(operation_key, selection, {
                'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                'feedback': {'category': 'arguments_reference_or_transport', 'code': str(error)}})
        return ledger.save_action(operation_key, selection, {
            'status': 'completed', 'record_refs': references, 'changed_record_refs': references,
            'result': plain(result)})


# -- the decision source -------------------------------------------------------------------------------------

INSTRUCTIONS = (
    'Execute the one frozen HPC plan of this Episode toward its original accepted accomplishment, balancing '
    'expected credit against real elapsed time and resource demand. Commission the launch child with the plan\'s '
    'frozen launch assignment when the plan has not been launched; only one launch per plan is admitted. Bind the '
    'practical receipt reference the launch child returned with hpc.handoff; never fabricate a handoff or receipt. '
    'Observe the original job with hpc.monitor, parse finished unit results with hpc.results and reorder pending '
    'units with hpc.allocation.order when evidence warrants it. Accepted obligations of this plan and prospective '
    'validation of its frozen forecasts are the only credit. The configured controller owns continuation.')


class AllocationSource:
    """Model-selected allocation units over ``bound``, its collaborators and the owner's ledger."""

    def __init__(self, binding, bound, collaborators, child_builders):
        self._binding, self._bound = binding, bound
        self._model = collaborators['model_provider']
        self._services = services_of(collaborators)
        self._store = collaborators['store']
        self._ledger, self._scope, self._plan_ref, self._plan = open_allocation(bound, self._services, self._store)
        self._operations = AllocationOperations(self._services, self._ledger, self._store, bound, self._scope,
                                                self._plan)
        self._builders = dict(child_builders)
        for slot, builder in self._builders.items():
            if not {'credit', FINDING} <= set(builder.return_form.fields):
                raise HPCRuntimeError(AXIS + '_hpc_child_return_form_lacks_credit_or_finding:' + slot)
        # The fields a commissioned report form (C5) adds, each one of this Episode's recorded finding facts.
        self.report_names = added_fields(bound.report_form, binding.return_form, FINDING_FACTS,
                                         AXIS + '_hpc_execution:' + binding.binding_path)
        self.catalog = catalog()
        self.applied, self.last_outcome, self.feedback, self.received = 0, None, None, set()

    def _apply(self, outcome):
        if outcome['kind'] == 'child':
            _received_strings(outcome['child_return'], self.received)
        self.feedback = outcome.get('feedback')
        self.last_outcome, self.applied = outcome, self.applied + 1

    def _catch_up(self, position):
        while self.applied < position:
            self._apply(self._bound.recorder.recall('outcome.' + str(self.applied)))

    def credit(self):
        return credit_view(self._ledger, self._plan)

    def _launch_slots(self):
        return {slot for slot, builder in self._builders.items() if builder.binding_path.endswith('/' + LAUNCH_HOME)}

    def action_schema(self):
        options = [obj({'kind': {'const': 'tool'}, 'tool': {'const': entry['name']}, 'arguments': entry['input_schema']})
                   for entry in self.catalog]
        options += [obj({'kind': {'const': 'child'}, 'slot': {'const': slot}, 'objective': _TEXT,
                         'assignment': {'type': 'string', 'description': 'JSON text of the child assignment (without '
                                        'scope) admitted by: ' + json.dumps(builder.assignment_form.as_record())}})
                    for slot, builder in sorted(self._builders.items())]
        return obj({'selection': {'anyOf': options}})

    def decision_context(self, view):
        ledger, plan = self._ledger, self._plan
        state = view.controller_state
        handoffs = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']]
        return {
            'goal': self._bound.request.goal.as_record(), 'scope': self._scope, 'hpc_role': EXECUTION,
            'hpc_plan_ref': self._plan_ref,
            'hpc_plan': {key: plan[key] for key in ('plan_id', 'candidate_id', 'manifest', 'launch_assignment',
                                                     'practical_assignment', 'preparation')},
            'hpc_obligations': ledger.commission['obligations'],
            'hpc_launched': any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('launch_commission')),
            'hpc_handoff': handoffs[-1] if handoffs else None,
            'hpc_latest_monitor': [row['body'] for row in ledger.records('monitor')
                                   if row['body']['plan_id'] == plan['plan_id']][-1:],
            'hpc_collected_unit_ids': sorted(self._operations._collected()),
            'hpc_closed': any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')),
            'hpc_credit': self.credit(), 'received_references': sorted(self.received),
            'tools': [{key: value for key, value in entry.items() if key != 'input_schema'} for entry in self.catalog],
            'child_options': {slot: {'binding_path': builder.binding_path,
                                     'assignment_form': builder.assignment_form.as_record()}
                              for slot, builder in sorted(self._builders.items())},
            'controller': state.as_record(),
            'units_consumed': view.units_consumed, 'last_local_outcome': self.last_outcome, 'feedback': self.feedback}

    async def next(self, view):
        position = view.units_consumed
        self._catch_up(position)
        attempt = 0
        while True:
            schema, context = self.action_schema(), self.decision_context(view)
            response = await self._bound.recorder.recorded_async(
                'decision.' + str(position) + '.' + str(attempt),
                lambda: self._model.complete(self._bound.episode_id, MODEL_ROLE, INSTRUCTIONS, context, schema))
            try:
                if not isinstance(response, Mapping) or set(response) != {'selection'}:
                    raise ValueError(AXIS + '_hpc_decision_response_must_be_exactly_selection')
                selection = plain(response['selection'])
                Draft202012Validator(schema['properties']['selection']).validate(selection)
                if selection['kind'] == 'child':
                    commission = self._commission(position, selection)
            except (ValueError, TypeError, KeyError, ValidationError) as error:
                # Rejected before acquisition: no unit and no observation; decide again with this feedback.
                self.feedback = {'status': 'invalid', 'category': 'action_contract',
                                 'detail': error.message if isinstance(error, ValidationError) else str(error)}
                attempt += 1
                continue
            if selection['kind'] == 'child':
                return self._child(position, selection, commission)
            return Leaf(selection, lambda chosen: self._tool(position, chosen),
                        lambda chosen, outcome: self._controller_input(position, outcome),
                        selection['tool'] + ':' + str(position))

    def _controller_input(self, position, outcome):
        return HPCRecord({'credit': self.credit()['credit'],
                          'estimation_context': {'progress_time': self._bound.progress.receipt(position)},
                          'unit': {'position': position, 'kind': outcome['kind'], 'status': outcome['status']}})

    async def _tool(self, position, selection):
        key = self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position)

        async def run():
            result = await self._operations.execute(selection['tool'], selection['arguments'], key, self.received)
            return {'kind': 'tool', 'tool': selection['tool'], **plain(result)}
        outcome = await self._bound.recorder.recorded_async('outcome.' + str(position), run)
        self._apply(outcome)
        return outcome

    def _commission(self, position, selection):
        """The admitted child commission; a launch must carry this plan's frozen assignment and reserve its slot."""
        slot = selection['slot']
        builder = self._builders[slot]
        assignment = json.loads(selection['assignment'])
        if not isinstance(assignment, dict) or 'scope' in assignment:
            raise ValueError(AXIS + '_hpc_child_assignment_must_be_a_record_without_scope')
        assignment = {'scope': self._scope, **assignment, **builder.assignment_form.declared}
        builder.assignment_form.admit(assignment, AXIS + '_hpc_execution_child_assignment:' + slot)
        if slot in self._launch_slots():
            plan, ledger = self._plan, self._ledger
            if not (_contains(assignment, plan['launch_assignment'])
                    or _contains(assignment, plan['practical_assignment'])):
                raise ValueError('hpc_launch_must_carry_the_frozen_plan_assignment')
            if any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')):
                raise ValueError('hpc_allocation_already_closed')
            reservation = {'operation_key': self._bound.run_id + ':' + self._bound.episode_id + ':' + str(position),
                           'plan_id': plan['plan_id']}
            # Immutable: a different launch of the same plan conflicts and is refused.
            ledger.put('launch_commission', reservation, identity='launch:' + plan['plan_id'])
        goal = EpisodeGoal.child(self._bound.request.goal, objective=selection['objective'],
                                 result_contract=dict(REPORT))
        return Commission(EpisodeRequest(goal, HPCRecord({'scope': self._scope, 'plan_ref': self._plan_ref}),
                                         ReportContract(**REPORT)), assignment)

    def _child(self, position, selection, commission):
        slot = selection['slot']
        builder = self._builders[slot]
        child = builder(slot + '_' + str(position), commission)
        information = tuple(commission.request.report_contract.information)

        def receive(result, completion, request):
            admitted = builder.admit(result)
            outcome = self._bound.recorder.recorded('outcome.' + str(position), lambda: {
                'kind': 'child', 'status': 'completed', 'slot': slot, 'child_credit': admitted['credit'],
                'child_return': plain(admitted), 'child_completion': completion.as_record()})
            self._apply(outcome)
            return self._controller_input(position, outcome)

        def report_of(result, completion, request):
            admitted = builder.admit(result)
            return {name: admitted[name] for name in information}
        return ChildEpisodeUnit(child, receive, report_of)

    def build_result(self, record):
        self._catch_up(record.units_consumed)
        view = self.credit()
        if isinstance(view['credit'], bool) or not math.isfinite(view['credit']):
            raise HPCRuntimeError(AXIS + '_hpc_credit_must_be_finite')
        ledger, plan = self._ledger, self._plan
        handoffs = [row['body'] for row in ledger.records('handoff') if row['body']['plan_id'] == plan['plan_id']]
        results = [row for row in ledger.records('result') if row['body']['plan_id'] == plan['plan_id']]
        finding = {'scope': self._scope, 'hpc_role': EXECUTION, 'hpc_plan_ref': self._plan_ref,
                   'hpc_plan_id': plan['plan_id'], 'hpc_credit': view,
                   'hpc_job_id': handoffs[-1]['job_id'] if handoffs else None,
                   'hpc_handoff_ref': handoffs[-1]['handoff_ref'] if handoffs else None,
                   'hpc_result_refs': [row['id'] for row in results],
                   'hpc_result_source_refs': [row['body']['source_ref'] for row in results],
                   'hpc_monitor_refs': [row['id'] for row in ledger.records('monitor')
                                        if row['body']['plan_id'] == plan['plan_id']],
                   'hpc_closed': any(row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('closed')),
                   'hpc_ledger': str(ledger.path), 'ended_by': record.ended_by, 'units': record.units_consumed}
        return result_record(view['credit'], plain(finding), self.report_names)


class AllocationRuntime:
    """The ``episode_runtime`` hooks of an A102 HPC allocation execution binding (mixed in before its contract)."""

    required_collaborators = ('model_provider', 'store', SERVICES)

    def build_controller(self, bound, collaborators):
        return controller(bound, collaborators)

    def build_episode(self, grain, bound, collaborators, child_builders):
        source = AllocationSource(self, bound, collaborators, child_builders)
        return Episode(grain, bound.key, source, bound.request, source.build_result)

    def restore_controller_input(self, record):
        return HPCRecord(dict(record))


__all__ = ['AllocationOperations', 'AllocationRuntime', 'AllocationSource', 'EXECUTION', 'FINDING_FACTS', 'catalog',
           'controller', 'credit_view', 'open_allocation']
