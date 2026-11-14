"""Private allocation handoff for A107 hpc."""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import reference_in_context




class AllocationHandoff:
    async def _attach_original_handoff(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        plan = ledger.read(arguments['plan_ref'])
        if arguments['handoff_ref'] not in self._known(context) or not reference_in_context(self.services, context, arguments['handoff_ref'], None):
            raise ValueError('handoff_not_received')
        target = self.targets.read_target(arguments['handoff_ref'], context.scope)
        if target['assignment'] != plan['practical_assignment']:
            raise ValueError('handoff_does_not_match_frozen_portfolio')
        ledger.put('handoff', {'handoff_ref': arguments['handoff_ref'], 'job_id': target['execution_id'], 'plan_id': plan['plan_id']}, identity='handoff:' + plan['plan_id'])
        result = {'plan_id': plan['plan_id'], 'job_id': target['execution_id']}
        if 'monitoring' in commission:
            from gene_annotation_episode.episodic_workflow.root.a107.hpc_monitoring import MonitorCronController
            result['monitor_controller_ref'] = MonitorCronController(ledger).attach(plan, target['execution_id'], commission['monitoring'])
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)

    async def _work_on_original_allocation(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration):
        plan = ledger.read(arguments['plan_ref'])
        if not any((row['body']['plan_id'] == plan['plan_id'] for row in ledger.records('handoff'))):
            return ledger.save_action(operation_key, selection, {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': 'original_handoff_not_attached', 'recovery': 'If Launch already completed, redeliver_report using its existing hpc_launch_deliveries delivery_ref and hpc_launch_report_form. Then attach the returned reference with hpc.handoff. Do not launch replacement work.'}})
        target = self._target(context, ledger, plan)
        candidate = self._candidate(ledger, plan)
        if tool_name == 'hpc.monitor.wait':
            return await self._wait_for_original_observation(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate)
        elif tool_name == 'hpc.allocation.order':
            return await self._order_original_units(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate)
        else:
            return await self._observe_original_allocation(context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate)
