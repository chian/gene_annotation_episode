"""Private allocation observations for A107 hpc."""
from __future__ import annotations
import base64
from gene_annotation_episode.episodic_workflow.root.a107.hpc_campaign import bind_progress
from gene_annotation_episode.episodic_workflow.root.a107.hpc_campaign import incorporate_progress
import json
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context
from gene_annotation_episode.episodic_workflow.root.a107.hpc_campaign import telemetry




class AllocationObservations:
    @property
    def targets(self):
        if self._targets is None:
            from gene_annotation_episode.episodic_workflow.root.a107.execution_progress import ExecutionTargetReader
            self._targets = ExecutionTargetReader(self.store, run_id=self.run_id, directory=self.directory,
                resources={key: value for key, value in self.resources.items() if value['kind'] == 'pbs_ssh'},
                api_execution=None)
        return self._targets

    def _target(self, context, ledger, plan):
        handoff = ledger.read('handoff:'+plan['plan_id'])
        if (handoff['handoff_ref'] not in self._known(context)
                or not reference_in_context(self.services, context, handoff['handoff_ref'], None)):
            raise ValueError('original_handoff_not_received_by_this_parent')
        target = self.targets.read_target(handoff['handoff_ref'], context.scope)
        if target['assignment'] != plan['practical_assignment']:
            raise ValueError('handoff_does_not_match_frozen_portfolio')
        return target

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

    async def _observe_original_allocation(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate):
        observation = ledger.once('status:' + operation_key, 'native_status', lambda: self.targets.observe_target(target, operation_key=operation_key))
        allocation, allocation_window = ledger.once('allocation:' + operation_key, 'allocation_snapshot', lambda: list(self._allocation(target, plan, operation_key + ':allocation')))
        observation_ref = ledger.put('observation', {'plan_id': plan['plan_id'], 'observation': observation, 'allocation': allocation, 'allocation_window': allocation_window})
        current = telemetry(observation, allocation, candidate)
        if current.get('current_unit_id') is not None:
            unit = next((row for row in candidate['units'] if row['unit_id'] == current['current_unit_id']))
            if unit.get('reports_progress', False):
                progress_path = plan['manifest']['workspace'] + '/units/' + unit['unit_id'] + '/progress.json'
                try:
                    progress_window = ledger.once('unit-progress:' + operation_key, 'unit_progress', lambda: self._window(target, progress_path, 16384, operation_key + ':progress')[0])
                    progress = bind_progress(json.loads(base64.b64decode(progress_window['bytes_base64'], validate=True)), plan['plan_id'])
                    current = incorporate_progress(current, progress, candidate)
                except (OSError, ValueError, KeyError, TypeError) as error:
                    current['progress_failure'] = str(error)
        prior_monitors = [row['body'] for row in ledger.records('monitor') if row['body']['plan_id'] == plan['plan_id']]
        if prior_monitors:
            previous = prior_monitors[-1]['conditional_prediction']['telemetry']
            current['phase_changed'] = (previous.get('phase'), previous.get('current_unit_id')) != (current.get('phase'), current.get('current_unit_id'))
            dt = current['observed_at'] - previous['observed_at']
            if dt > 0 and 'completed_fraction' in current and ('completed_fraction' in previous):
                current['recent_fraction_per_second'] = max(0.0, current['completed_fraction'] - previous['completed_fraction']) / dt
        measured_ref = self._measure(ledger, plan, observation, current, allocation)
        if tool_name == 'hpc.monitor':
            return await self._update_conditional_forecast(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate, observation, allocation, allocation_window, observation_ref, current, measured_ref)
        else:
            return await self._collect_original_results(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate, observation, allocation, allocation_window, observation_ref, current, measured_ref)
