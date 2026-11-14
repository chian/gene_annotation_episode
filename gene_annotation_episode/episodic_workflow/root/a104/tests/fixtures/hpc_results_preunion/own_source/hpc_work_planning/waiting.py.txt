"""Private waiting for A104 hpc."""
from __future__ import annotations
import json




class HPCActivityAdvice:
    def activity_advice(self, context):
        if self.store is None:
            return None
        row = self.store.db.execute('SELECT observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index DESC LIMIT 1', (context.run_id, context.episode_id)).fetchone()
        if row is None:
            return None
        diagnostic = json.loads(row[0])['step']['estimate']['diagnostics']
        mode = diagnostic.get('activity_mode')
        if mode not in ('wait', 'collect'):
            return None
        ledger = self.state(context)
        if not ledger.records('monitor_controller'):
            return None
        tool = 'hpc.results' if mode == 'collect' else 'hpc.monitor.wait' if ledger.records('monitor') else 'hpc.monitor'
        return {'mode': mode, 'suggested_tool': tool, 'active_next_gain': diagnostic['active_next_gain'], 'pending_expected_credit': diagnostic['pending_expected_credit'], 'pending_credit_upper_bound': diagnostic.get('pending_credit_upper_bound')}

    async def _wait_for_original_observation(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate):
        from gene_annotation_episode.episodic_workflow.root.a104.hpc_monitoring import MonitorCronController
        if not any((row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor_controller'))):
            return ledger.save_action(operation_key, selection, {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': 'hpc_monitor_controller_not_attached', 'next_step': 'This original commission has no attached monitor controller. Use hpc.monitor on the original plan, then hpc.results when its outputs are ready. Retain the original submitted job; do not launch replacement work.'}})
        if not any((row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('monitor'))):
            await self.execute(context, 'hpc.monitor', {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, operation_key + ':initial-monitor')
        monitor = self._last_forecast(ledger, plan)
        ready = self._uncollected_completed_unit_ids(ledger, plan, monitor['conditional_prediction'])
        if monitor['conditional_prediction']['telemetry']['state'] in ('complete', 'failed'):
            result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_terminal_job_collect_now'}
        elif ready:
            result = {'schedule': None, 'monitor': monitor, 'reason': 'observed_unit_outputs_collect_now', 'ready_unit_ids': sorted(ready)}
        else:
            controller = MonitorCronController(ledger)
            schedule = controller.reserve(plan, candidate, monitor, operation_key)
            if schedule['job_id'] != target['execution_id']:
                raise ValueError('monitor_schedule_original_job_conflict')
            if schedule['valuation']['schedule']:
                await controller.wait(schedule)
                observed = await self.execute(context, 'hpc.monitor', {'plan_ref': arguments['plan_ref'], 'refresh_queue': True}, operation_key + ':monitor')
                ledger.put('monitor_wake', {'schedule_ref': schedule['schedule_ref'], 'job_id': target['execution_id'], 'observed': observed}, identity='wake:' + operation_key)
                result = {'schedule': schedule, 'monitor': observed['result']}
            else:
                result = {'schedule': schedule, 'monitor': None}
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
