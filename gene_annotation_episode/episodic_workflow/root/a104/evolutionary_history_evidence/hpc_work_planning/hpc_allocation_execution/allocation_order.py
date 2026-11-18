"""Private allocation order for A104 hpc_execution."""
from __future__ import annotations





class AllocationOrder:
    async def _order_original_units(self, context, tool_name, arguments, operation_key, ledger, selection, references, commission, configuration, plan, target, candidate):
        allowed = {unit['unit_id'] for unit in candidate['units']}
        if not set(arguments['unit_ids']) <= allowed:
            raise ValueError('only_original_work_units_can_be_selected')
        result = self.targets.operations[target['resource_id']].write_allocation_control(target['assignment'], target['execution_id'], **self.targets._native_identity(target), unit_ids=arguments['unit_ids'], operation_key=operation_key)
        ledger.put('allocation_order', {'plan_id': plan['plan_id'], 'operation_key': operation_key, 'unit_ids': arguments['unit_ids'], 'receipt': result})
        outcome = {'status': 'completed', 'record_refs': references, 'changed_record_refs': references, 'result': result}
        return ledger.save_action(operation_key, selection, outcome)
